"""Offline validation and optional minimal live check for the shared LLM config."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from llm_config import DEFAULT_CONFIG_PATH, LLMConfigError, load_shared_llm


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--live",
        action="store_true",
        help="make one small paid request after offline validation",
    )
    args = parser.parse_args()

    try:
        config = load_shared_llm(args.config)
    except LLMConfigError as error:
        raise SystemExit(f"CONFIG ERROR: {error}") from error

    print(json.dumps(config.redacted_dict(), ensure_ascii=False, indent=2))
    print("OFFLINE CHECK PASS: shared Qwen configuration is valid; key is redacted")
    if not args.live:
        return

    response = config.create_client().chat.completions.create(
        model=config.model,
        messages=[{"role": "user", "content": "Reply with exactly: CONFIG_OK"}],
        temperature=config.temperature,
        top_p=config.top_p,
        max_tokens=16,
    )
    answer = (response.choices[0].message.content or "").strip()
    if "CONFIG_OK" not in answer:
        raise SystemExit(f"LIVE CHECK FAILED: unexpected response {answer!r}")
    print(f"LIVE CHECK PASS: model={response.model}, request_id={response.id}")


if __name__ == "__main__":
    main()
