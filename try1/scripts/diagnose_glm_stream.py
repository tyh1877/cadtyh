"""Record the public fields emitted by one minimal GLM multimodal stream."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "go_nogo2" / "scripts"), str(ROOT / "try1" / "scripts")]
from glm_config import load_glm  # noqa: E402
from run_try1 import content  # noqa: E402


def main() -> None:
    packet = json.loads((ROOT / "try1/inputs/image_text_v1/dev_arm-0573e1e127.json").read_text())
    config = load_glm(); counts = {"content": 0, "reasoning_content": 0, "empty": 0}; finish = None; usage = None; chunks = 0
    stream = config.create_client().chat.completions.create(
        model=config.model, messages=[{"role": "system", "content": "Return exactly JSON {\"ok\":true}."}, {"role": "user", "content": content(packet)}],
        temperature=0.0, top_p=1.0, max_tokens=1024, stream=True,
        extra_body={"reasoning_effort": "low"},
    )
    for chunk in stream:
        chunks += 1; usage = getattr(chunk, "usage", None) or usage
        if not chunk.choices: continue
        choice = chunk.choices[0]; delta = choice.delta
        counts["content"] += len(getattr(delta, "content", None) or "")
        counts["reasoning_content"] += len(getattr(delta, "reasoning_content", None) or "")
        counts["empty"] += int(not getattr(delta, "content", None) and not getattr(delta, "reasoning_content", None))
        finish = choice.finish_reason or finish
    print(json.dumps({"chunks": chunks, "counts": counts, "finish_reason": finish, "usage": str(usage)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
