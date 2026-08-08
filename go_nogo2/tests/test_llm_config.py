from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from llm_config import LLMConfigError, load_shared_llm  # noqa: E402


VALID = """\
[provider]
name = "alibaba_model_studio"
api_key = "unit-test-placeholder-value"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
[generation]
model = "qwen3.7-plus"
temperature = 0.0
top_p = 1.0
max_output_tokens = 32768
timeout_seconds = 300.0
max_retries = 0
[experiment]
config_version = "1.0"
shared_by = ["direct_frontier_mllm", "cadir_simplecad"]
"""


class SharedLLMConfigTests(unittest.TestCase):
    def write(self, text: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "llm.toml"
        path.write_text(text, encoding="utf-8")
        return path

    def test_valid_config_and_redaction(self) -> None:
        config = load_shared_llm(self.write(VALID))
        self.assertEqual(config.model, "qwen3.7-plus")
        self.assertEqual(config.redacted_dict()["api_key"], "<configured>")
        self.assertNotIn("unit-test-placeholder", str(config.redacted_dict()))

    def test_placeholder_key_is_rejected(self) -> None:
        text = VALID.replace("unit-test-placeholder-value", "PASTE_DASHSCOPE_API_KEY_HERE")
        with self.assertRaisesRegex(LLMConfigError, "placeholder"):
            load_shared_llm(self.write(text))

    def test_model_drift_is_rejected(self) -> None:
        with self.assertRaisesRegex(LLMConfigError, "frozen"):
            load_shared_llm(self.write(VALID.replace("qwen3.7-plus", "qwen-plus")))

    def test_non_aliyun_endpoint_is_rejected(self) -> None:
        text = VALID.replace("dashscope.aliyuncs.com", "example.com")
        with self.assertRaisesRegex(LLMConfigError, "aliyuncs.com"):
            load_shared_llm(self.write(text))


if __name__ == "__main__":
    unittest.main()
