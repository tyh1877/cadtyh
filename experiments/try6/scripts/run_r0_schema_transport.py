"""Real API schema transport audit. Stop at first failure; never repair response."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import httpx
import jsonschema
import openai
from jsonschema import Draft202012Validator

from experiments.try6.scripts.kfdg_v1_contract import validate as validate_kfdg_v1

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments" / "try6"
OUT = HERE / "results" / "try6_0_r0" / "schema_transport"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def save_text(path: Path, value: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    protocol = read_json(HERE / "protocol" / "r0_transport_protocol.json")
    levels = read_json(HERE / "protocol" / "r0_schema_levels.json")["levels"]
    local_config = tomllib.loads((ROOT / protocol["model_config"]).read_text(encoding="utf-8"))
    provider = local_config["provider"]
    generation = local_config["generation"]
    if generation["model"] != protocol["requested_model"]:
        raise RuntimeError("model ID differs from frozen protocol")
    if not provider["api_key"]:
        raise RuntimeError("API key absent")
    OUT.mkdir(parents=True, exist_ok=True)
    save(OUT / "sdk_config.json", {
        "model": generation["model"], "api_base_url": provider["base_url"],
        "api_key_present": True, "api_key_value_recorded": False,
        "openai_version": openai.__version__, "httpx_version": httpx.__version__,
        "jsonschema_version": getattr(jsonschema, "__version__", "unknown"),
        "python": sys.version, "platform": platform.platform(),
        "temperature": protocol["temperature"], "top_p": protocol["top_p"],
        "seed": protocol["seed"], "max_output_tokens": protocol["max_output_tokens_per_level"],
        "timeout_seconds": protocol["timeout_seconds"], "sdk_retries": 0,
        "technical_retries": 0, "request_payload_capture": "httpx request event hook before network send",
        "response_capture": "httpx response event hook reads raw HTTP JSON body",
    })
    records = []
    specs = levels + [{
        "level": 4,
        "prompt": "Return a synthetic TEST KFDG v1 object. Include one joint_port, one housing geometric feature, one housing_width parameter (40 mm, bounds 30 to 50 mm, SOLVER_ESTIMATED, MEDIUM), and one connected_to constraint. This is a transport smoke test, not reconstruction; do not use robot evidence.",
        "schema": read_json(HERE / "protocol" / "kfdg_v1.schema.json"),
    }]
    for spec in specs:
        level = spec["level"]
        schema = spec["schema"]
        Draft202012Validator.check_schema(schema)
        captured: dict = {}

        def capture_request(request: httpx.Request):
            try:
                captured["request"] = json.loads(request.content)
            except Exception as error:
                captured["request_capture_error"] = str(error)

        def capture_response(response: httpx.Response):
            response.read()
            captured["http_status"] = response.status_code
            captured["response_headers"] = {k: v for k, v in response.headers.items() if k.lower() in {"x-request-id", "content-type", "x-dashscope-request-id"}}
            try:
                captured["http_response"] = response.json()
            except Exception:
                captured["http_response_text"] = response.text

        name = f"r0_level_{level}"
        messages = [{"role": "system", "content": "Return only one JSON object matching the requested strict JSON Schema. No markdown."}, {"role": "user", "content": spec["prompt"]}]
        result = {"level": level, "schema_sha256": hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest(), "started_at_utc": datetime.now(timezone.utc).isoformat()}
        t0 = time.monotonic()
        try:
            with httpx.Client(timeout=protocol["timeout_seconds"], event_hooks={"request": [capture_request], "response": [capture_response]}) as http_client:
                client = openai.OpenAI(api_key=provider["api_key"], base_url=provider["base_url"], timeout=protocol["timeout_seconds"], max_retries=0, http_client=http_client)
                response = client.chat.completions.create(
                    model=generation["model"], messages=messages,
                    response_format={"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}},
                    temperature=protocol["temperature"], top_p=protocol["top_p"],
                    max_tokens=protocol["max_output_tokens_per_level"], seed=protocol["seed"],
                )
                sdk_data = response.model_dump(mode="json")
            result["latency_seconds"] = round(time.monotonic() - t0, 6)
            if "request" in captured:
                save(OUT / f"level{level}_request.json", captured["request"])
            else:
                result["classification"] = "SCHEMA_NOT_ACTUALLY_SENT"
                result["error"] = captured.get("request_capture_error", "no HTTP request observed")
                raise RuntimeError(result["error"])
            save(OUT / f"level{level}_http_response.json", captured.get("http_response", {"text": captured.get("http_response_text", "")}))
            save(OUT / f"level{level}_response.json", sdk_data)
            result["http_status"] = captured.get("http_status")
            result["response_headers"] = captured.get("response_headers", {})
            result["actual_model"] = sdk_data.get("model")
            result["usage"] = sdk_data.get("usage")
            sent = captured["request"].get("response_format", {}).get("json_schema", {})
            if sent.get("schema") != schema or sent.get("strict") is not True:
                result["classification"] = "SCHEMA_NOT_ACTUALLY_SENT"
                result["error"] = "captured request schema/strict mismatch"
            else:
                http_choices = captured.get("http_response", {}).get("choices", [])
                sdk_choices = sdk_data.get("choices", [])
                raw_http = http_choices[0].get("message", {}).get("content") if http_choices else None
                raw_sdk = sdk_choices[0].get("message", {}).get("content") if sdk_choices else None
                save_text(OUT / f"level{level}_raw_response.txt", raw_http if isinstance(raw_http, str) else "")
                result["raw_http_content_type"] = type(raw_http).__name__
                result["sdk_content_type"] = type(raw_sdk).__name__
                if raw_http != raw_sdk:
                    result["classification"] = "SDK_RESPONSE_WRAPPER_MODIFIED_OUTPUT"
                    result["error"] = "HTTP message content differs from SDK message content"
                elif not isinstance(raw_http, str):
                    result["classification"] = "API_ACCEPTED_RAW_RESPONSE_INVALID"
                    result["error"] = "message content is not a string"
                else:
                    try:
                        value = json.loads(raw_http)
                        Draft202012Validator(schema).validate(value)
                        if level == 4:
                            validate_kfdg_v1(value)
                        result["classification"] = "RAW_RESPONSE_VALID"
                        result["raw_response_valid"] = True
                    except Exception as error:
                        result["classification"] = "API_ACCEPTED_RAW_RESPONSE_INVALID"
                        result["error"] = f"{type(error).__name__}: {error}"
                        result["raw_response_valid"] = False
        except Exception as error:
            result.setdefault("latency_seconds", round(time.monotonic() - t0, 6))
            if "request" in captured:
                save(OUT / f"level{level}_request.json", captured["request"])
            if "http_response" in captured or "http_response_text" in captured:
                save(OUT / f"level{level}_http_response.json", captured.get("http_response", {"text": captured.get("http_response_text", "")}))
            result.setdefault("http_status", captured.get("http_status"))
            if "classification" not in result:
                result["classification"] = "API_REJECTED_SCHEMA" if captured.get("http_status", 0) >= 400 else "TRANSPORT_ERROR"
                result["error"] = f"{type(error).__name__}: {error}"
        save(OUT / f"level{level}_validation.json", result)
        records.append(result)
        if result["classification"] != "RAW_RESPONSE_VALID":
            break
    attempted = {item["level"] for item in records}
    for level in range(5):
        if level not in attempted:
            records.append({"level": level, "classification": "NOT_RUN_DUE_TO_PRIOR_FAILURE"})
    records.sort(key=lambda item: item["level"])
    report = {"schema_version": "robotcad_try6_r0_transport_report_v1", "levels": records,
              "all_pass": all(item["classification"] == "RAW_RESPONSE_VALID" for item in records),
              "frozen_c1_manifest_sha256": digest(ROOT / protocol["frozen_c1_v1_manifest"]),
              "gt_evaluations": 0, "formal_holdout_evaluations": 0,
              "completed_at_utc": datetime.now(timezone.utc).isoformat()}
    save(OUT / "transport_report.json", report)
    print(json.dumps({"all_pass": report["all_pass"], "levels": [{"level": x["level"], "classification": x["classification"]} for x in records]}, ensure_ascii=False))
    return report["all_pass"]


if __name__ == "__main__":
    sys.exit(0 if run() else 2)
