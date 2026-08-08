"""Run CADSmith's execution workflow with Qwen and no LLM judge.

The official source stays external because it declares no license.  This
adapter imports the audited checkout, swaps only its model client boundary,
and keeps Planner -> Coder -> Executor -> Error-refiner.  Its LLM Validator
and geometry-refiner are intentionally excluded: Pilot evaluation is fully
deterministic.
"""

from __future__ import annotations

import argparse
import ast
import json
import shutil
import sys
import time
import types
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from llm_config import DEFAULT_CONFIG_PATH, load_shared_llm


ALLOWED_MODELS = ("qwen3.7-plus", "qwen3.7-max-2026-06-08")
CADSMITH_COMMIT = "a856517e4e9449eb71dd6f7f83aa9fffa40f5bbb"
ALLOWED_IMPORTS = {"cadquery", "math"}
FORBIDDEN_NAMES = {"open", "exec", "eval", "compile", "__import__", "input", "globals", "locals"}
FORBIDDEN_PREFIXES = ("os", "sys", "subprocess", "pathlib", "shutil", "socket", "requests", "http", "builtins")


class QwenMessages:
    def __init__(self, config: Any, max_total_tokens: int) -> None:
        self.client = config.create_client()
        self.config, self.max_total_tokens = config, max_total_tokens
        self.input_tokens = self.output_tokens = self.calls = 0
        self.case_input_tokens = self.case_output_tokens = self.case_calls = 0

    def reset_case_budget(self) -> None:
        self.case_input_tokens = self.case_output_tokens = self.case_calls = 0

    def create(self, *, model: str, max_tokens: int, system: str, messages: list[dict[str, Any]]) -> Any:
        if self.case_calls >= 3:
            raise RuntimeError("CADSmith-Qwen call budget exhausted")
        text_parts: list[str] = []
        for message in messages:
            content = message.get("content", "")
            if isinstance(content, str):
                text_parts.append(content)
            elif isinstance(content, list):
                for item in content:
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    else:
                        raise RuntimeError("LLM Validator image input is disabled by protocol")
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": "\n".join(text_parts)}],
            temperature=0.0, top_p=1.0, max_tokens=min(max_tokens, 16384),
        )
        usage = response.usage
        self.input_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
        self.output_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        self.calls += 1
        self.case_input_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
        self.case_output_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        self.case_calls += 1
        if self.case_input_tokens + self.case_output_tokens > self.max_total_tokens:
            raise RuntimeError("CADSmith-Qwen total-token budget exhausted")
        content = response.choices[0].message.content or ""
        return SimpleNamespace(content=[SimpleNamespace(text=content)], usage=SimpleNamespace(
            input_tokens=getattr(usage, "prompt_tokens", 0), output_tokens=getattr(usage, "completion_tokens", 0)))


def safe_cadquery_code(code: str) -> None:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                    raise ValueError(f"disallowed import: {alias.name}")
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise ValueError(f"disallowed name: {node.id}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("dunder attribute access is disallowed")
        if isinstance(node, ast.Name) and node.id.startswith(FORBIDDEN_PREFIXES):
            raise ValueError(f"disallowed module name: {node.id}")


def import_cadsmith(cadsmith_root: Path, gateway: QwenMessages):
    if "anthropic" not in sys.modules:
        anthropic = types.ModuleType("anthropic")
        anthropic.Anthropic = object
        sys.modules["anthropic"] = anthropic
    if "dotenv" not in sys.modules:
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda: False
        sys.modules["dotenv"] = dotenv
    sys.path.insert(0, str(cadsmith_root.resolve()))
    from autofab import agents  # type: ignore
    from autofab.executor import Executor  # type: ignore
    agents._get_client = lambda: SimpleNamespace(messages=gateway)  # type: ignore[attr-defined]
    return agents, Executor


def strip_code_fence(code: str) -> str:
    code = code.strip()
    if code.startswith("```python"):
        code = code[len("```python"):].strip()
    elif code.startswith("```"):
        code = code[3:].strip()
    return code[:-3].strip() if code.endswith("```") else code


def run_case(case_dir: Path, run_dir: Path, agents: Any, executor_cls: Any) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt = (case_dir / "prompt.txt").read_text(encoding="utf-8")
    started, attempts = time.perf_counter(), []
    incompatible = ("articulated" in prompt.lower() and "assembly" in prompt.lower()
                    and ("urdf" in prompt.lower() or "joint" in prompt.lower()))
    if incompatible:
        return {"status": "UNSUPPORTED_INPUT", "case_id": case_dir.name,
                "latency_seconds": time.perf_counter() - started, "geometry": None, "step": None, "stl": None,
                "attempts": [{"attempt": 0, "stage": "capability_preflight", "success": False,
                              "error": "CADSmith-Qwen natively emits one CadQuery part/STEP/STL and accepts no articulated URDF target or reference-view input."}]}
    try:
        plan = agents.plan(prompt)
        code = strip_code_fence(agents.generate_code(plan, prompt))
    except Exception as exc:
        return {"status": "FAILURE", "case_id": case_dir.name, "latency_seconds": time.perf_counter() - started,
                "geometry": None, "step": None, "stl": None,
                "attempts": [{"attempt": 0, "stage": "planner_or_coder", "success": False,
                              "error": f"{type(exc).__name__}: {exc}"}]}
    executor = executor_cls(output_dir=str(run_dir), timeout_seconds=60)
    for attempt in range(2):
        try:
            safe_cadquery_code(code)
            result = executor.execute(code, name=f"{case_dir.name}_attempt_{attempt + 1}")
        except Exception as exc:
            result = SimpleNamespace(success=False, error=f"{type(exc).__name__}: {exc}", error_type=type(exc).__name__)
        attempts.append({"attempt": attempt + 1, "code": code, "success": bool(result.success), "error": getattr(result, "error", None)})
        if result.success:
            (run_dir / "design_plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
            (run_dir / "cadquery_code.py").write_text(code, encoding="utf-8")
            return {"status": "SUCCESS", "case_id": case_dir.name, "latency_seconds": time.perf_counter() - started,
                    "geometry": result.geometry_json, "step": result.step_path, "stl": result.stl_path, "attempts": attempts}
        if attempt == 0:
            code = strip_code_fence(agents.fix_error(code, getattr(result, "error", "unknown execution error"), plan))
    return {"status": "FAILURE", "case_id": case_dir.name, "latency_seconds": time.perf_counter() - started,
            "geometry": None, "step": None, "stl": None, "attempts": attempts}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("go_nogo2/data/pilot10"))
    parser.add_argument("--runs-root", type=Path, default=Path("go_nogo2/runs/final_validation/cadsmith_qwen"))
    parser.add_argument("--cadsmith-root", type=Path, default=Path("go_nogo2/external/CADSmith"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--model", choices=ALLOWED_MODELS, default="qwen3.7-max-2026-06-08")
    parser.add_argument("--case")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if not args.cadsmith_root.is_dir():
        raise SystemExit("CADSmith checkout is required at --cadsmith-root")
    config = replace(load_shared_llm(args.config), model=args.model)
    gateway = QwenMessages(config, max_total_tokens=100000)
    agents, executor_cls = import_cadsmith(args.cadsmith_root, gateway)
    cases = sorted(path for path in args.data_root.glob("case_*") if path.is_dir())
    if args.case:
        cases = [path for path in cases if path.name == args.case]
    for case_dir in cases:
        run_dir = args.runs_root / case_dir.name
        if run_dir.exists() and args.overwrite:
            shutil.rmtree(run_dir)
        if (run_dir / "cadsmith_manifest.json").is_file() and not args.overwrite:
            continue
        gateway.reset_case_budget()
        record = run_case(case_dir, run_dir, agents, executor_cls)
        record["provenance"] = {"source": "CADSmith-Qwen adaptation", "cadsmith_commit": CADSMITH_COMMIT,
                                "model": config.model, "llm_judge_used": False, "native_output": "single_part_step_stl"}
        record["budget"] = {"api_calls": gateway.case_calls, "input_tokens": gateway.case_input_tokens,
                            "output_tokens": gateway.case_output_tokens, "total_tokens": gateway.case_input_tokens + gateway.case_output_tokens,
                            "max_total_model_tokens": 100000, "max_calls": 3}
        (run_dir / "cadsmith_manifest.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{case_dir.name}: {record['status']}", flush=True)
    print(json.dumps({"calls": gateway.calls, "tokens": gateway.input_tokens + gateway.output_tokens}, indent=2))


if __name__ == "__main__":
    main()
