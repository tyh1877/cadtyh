from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from glm_config import GLMConfigError, load_glm  # noqa: E402


VALID = '''
[provider]
name = "zhipu_bigmodel"
api_key = "unit-test-key"
base_url = "https://open.bigmodel.cn/api/paas/v4"
[generation]
model = "glm-5.3-flash"
temperature = 0.0
top_p = 1.0
max_output_tokens = 32768
timeout_seconds = 600.0
max_retries = 2
[capabilities]
input_modalities = ["text", "image"]
[experiment]
config_version = "1.0"
default_for_new_experiments = true
'''


class GLMConfigTests(unittest.TestCase):
    def write(self, text: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "glm.toml"
        path.write_text(text, encoding="utf-8")
        return path

    def test_valid_config_and_redaction(self) -> None:
        config = load_glm(self.write(VALID))
        self.assertEqual(config.model, "glm-5.3-flash")
        self.assertEqual(config.redacted_dict()["api_key"], "<configured>")
        self.assertNotIn("unit-test-key", str(config.redacted_dict()))

    def test_empty_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(GLMConfigError, "empty or a placeholder"):
            load_glm(self.write(VALID.replace("unit-test-key", "")))

    def test_model_drift_is_rejected(self) -> None:
        with self.assertRaisesRegex(GLMConfigError, "project default"):
            load_glm(self.write(VALID.replace("glm-5.3-flash", "glm-5.2")))

    def test_non_zhipu_endpoint_is_rejected(self) -> None:
        with self.assertRaisesRegex(GLMConfigError, "open.bigmodel.cn"):
            load_glm(self.write(VALID.replace("open.bigmodel.cn", "example.com")))


if __name__ == "__main__":
    unittest.main()
