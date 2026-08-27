"""Load the local Zhipu GLM configuration for new paper experiments.

This module is intentionally separate from ``llm_config.py``: completed Qwen
experiments retain their frozen provenance, while new experiments can opt into
the project-wide GLM default without rewriting historical configurations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import tomllib

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GLM_CONFIG_PATH = ROOT / "config" / "glm.local.toml"
DEFAULT_GLM_MODEL = "glm-5.3-flash"
PLACEHOLDER_KEYS = {"", "PASTE_ZHIPU_API_KEY_HERE", "sk-xxx"}


class GLMConfigError(ValueError):
    """Raised when the local GLM configuration is unsafe or invalid."""


@dataclass(frozen=True)
class GLMConfig:
    provider: str
    api_key: str
    base_url: str
    model: str
    temperature: float
    top_p: float
    max_output_tokens: int
    timeout_seconds: float
    max_retries: int
    input_modalities: tuple[str, ...]
    config_version: str
    default_for_new_experiments: bool

    def redacted_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["api_key"] = "<configured>" if self.api_key else "<missing>"
        return value

    def create_client(self) -> OpenAI:
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            max_retries=self.max_retries,
        )


def _table(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise GLMConfigError(f"missing TOML table [{key}]")
    return value


def _required(table: dict[str, Any], key: str) -> Any:
    if key not in table:
        raise GLMConfigError(f"missing configuration value: {key}")
    return table[key]


def load_glm(path: Path = DEFAULT_GLM_CONFIG_PATH) -> GLMConfig:
    """Load and validate the user-selected default GLM configuration."""
    path = path.resolve()
    if not path.is_file():
        raise GLMConfigError(
            f"local GLM config not found: {path}. Copy config/glm.example.toml "
            "to config/glm.local.toml and paste the Zhipu API key there."
        )
    with path.open("rb") as handle:
        payload = tomllib.load(handle)

    provider = _table(payload, "provider")
    generation = _table(payload, "generation")
    capabilities = _table(payload, "capabilities")
    experiment = _table(payload, "experiment")
    config = GLMConfig(
        provider=str(_required(provider, "name")).strip(),
        api_key=str(_required(provider, "api_key")).strip(),
        base_url=str(_required(provider, "base_url")).strip().rstrip("/"),
        model=str(_required(generation, "model")).strip(),
        temperature=float(_required(generation, "temperature")),
        top_p=float(_required(generation, "top_p")),
        max_output_tokens=int(_required(generation, "max_output_tokens")),
        timeout_seconds=float(_required(generation, "timeout_seconds")),
        max_retries=int(_required(generation, "max_retries")),
        input_modalities=tuple(str(item) for item in _required(capabilities, "input_modalities")),
        config_version=str(_required(experiment, "config_version")).strip(),
        default_for_new_experiments=bool(_required(experiment, "default_for_new_experiments")),
    )
    validate_glm(config)
    return config


def validate_glm(config: GLMConfig) -> None:
    if config.provider != "zhipu_bigmodel":
        raise GLMConfigError("provider.name must be zhipu_bigmodel")
    if config.api_key in PLACEHOLDER_KEYS or config.api_key.startswith("PASTE_"):
        raise GLMConfigError("api_key is still empty or a placeholder")
    if config.model != DEFAULT_GLM_MODEL:
        raise GLMConfigError(
            f"model is frozen to the project default {DEFAULT_GLM_MODEL}, got {config.model!r}"
        )
    parsed = urlparse(config.base_url)
    if parsed.scheme != "https" or parsed.netloc != "open.bigmodel.cn":
        raise GLMConfigError("base_url must use HTTPS host open.bigmodel.cn")
    if not parsed.path.rstrip("/").endswith("api/paas/v4"):
        raise GLMConfigError("base_url must end with /api/paas/v4")
    if not 0.0 <= config.temperature <= 2.0:
        raise GLMConfigError("temperature must be in [0, 2]")
    if not 0.0 < config.top_p <= 1.0:
        raise GLMConfigError("top_p must be in (0, 1]")
    if config.max_output_tokens <= 0 or config.timeout_seconds <= 0:
        raise GLMConfigError("token and timeout limits must be positive")
    if not 0 <= config.max_retries <= 10:
        raise GLMConfigError("max_retries must be in [0, 10]")
    if config.input_modalities != ("text", "image"):
        raise GLMConfigError("input_modalities must be exactly [text, image]")
    if config.config_version != "1.0" or not config.default_for_new_experiments:
        raise GLMConfigError("unsupported experiment configuration")
