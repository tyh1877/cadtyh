"""Validate the local GLM configuration, optionally with one live API call."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from glm_config import DEFAULT_GLM_CONFIG_PATH, GLMConfigError, load_glm


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_GLM_CONFIG_PATH)
    parser.add_argument("--live", action="store_true", help="make one small paid API request")
    args = parser.parse_args()
    try:
        config = load_glm(args.config)
    except GLMConfigError as error:
        raise SystemExit(f"CONFIG ERROR: {error}") from error

    print(json.dumps(config.redacted_dict(), ensure_ascii=False, indent=2))
    print("OFFLINE CHECK PASS: GLM configuration is valid; key is redacted")
    if not args.live:
        return
    response = config.create_client().chat.completions.create(
        model=config.model,
        messages=[{"role": "user", "content": "Reply with exactly: GLM_CONFIG_OK"}],
        temperature=config.temperature,
        top_p=config.top_p,
        # GLM may use part of the completion budget for reasoning before emitting
        # the short verification string, so 16 tokens can truncate valid output.
        max_tokens=128,
    )
    answer = (response.choices[0].message.content or "").strip()
    if "GLM_CONFIG_OK" not in answer:
        raise SystemExit(f"LIVE CHECK FAILED: unexpected response {answer!r}")
    print(f"LIVE CHECK PASS: model={response.model}, request_id={response.id}")


if __name__ == "__main__":
    main()
