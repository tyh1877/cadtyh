"""Load the one frozen, secret-safe LLM configuration shared by both baselines."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import tomllib

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "config" / "llm.local.toml"
EXPECTED_MODEL = "qwen3.7-plus"
EXPECTED_METHODS = ("direct_frontier_mllm", "cadir_simplecad")
PLACEHOLDER_KEYS = {"", "PASTE_DASHSCOPE_API_KEY_HERE", "sk-xxx"}


class LLMConfigError(ValueError):
    """Raised when a local LLM configuration is unsafe or not reproducible."""


@dataclass(frozen=True)
class SharedLLMConfig:
    provider: str
    api_key: str
    base_url: str
    model: str
    temperature: float
    top_p: float
    max_output_tokens: int
    timeout_seconds: float
    max_retries: int
    config_version: str
    shared_by: tuple[str, ...]

    def redacted_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["api_key"] = "<configured>" if self.api_key else "<missing>"
        return payload

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
        raise LLMConfigError(f"missing TOML table [{key}]")
    return value


def _required(table: dict[str, Any], key: str) -> Any:
    if key not in table:
        raise LLMConfigError(f"missing configuration value: {key}")
    return table[key]


def load_shared_llm(path: Path = DEFAULT_CONFIG_PATH) -> SharedLLMConfig:
    """Load and strictly validate the frozen Qwen configuration.

    The API key is intentionally accepted only from the ignored local TOML file,
    so a run cannot unknowingly use a different shell credential.
    """
    path = path.resolve()
    if not path.is_file():
        raise LLMConfigError(
            f"local config not found: {path}. Copy config/llm.example.toml to "
            "config/llm.local.toml and paste the Model Studio API key there."
        )

    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    provider = _table(payload, "provider")
    generation = _table(payload, "generation")
    experiment = _table(payload, "experiment")

    config = SharedLLMConfig(
        provider=str(_required(provider, "name")).strip(),
        api_key=str(_required(provider, "api_key")).strip(),
        base_url=str(_required(provider, "base_url")).strip().rstrip("/"),
        model=str(_required(generation, "model")).strip(),
        temperature=float(_required(generation, "temperature")),
        top_p=float(_required(generation, "top_p")),
        max_output_tokens=int(_required(generation, "max_output_tokens")),
        timeout_seconds=float(_required(generation, "timeout_seconds")),
        max_retries=int(_required(generation, "max_retries")),
        config_version=str(_required(experiment, "config_version")).strip(),
        shared_by=tuple(str(item) for item in _required(experiment, "shared_by")),
    )
    validate_shared_llm(config)
    return config


def validate_shared_llm(config: SharedLLMConfig) -> None:
    if config.provider != "alibaba_model_studio":
        raise LLMConfigError("provider.name must be alibaba_model_studio")
    if config.api_key in PLACEHOLDER_KEYS or config.api_key.startswith("PASTE_"):
        raise LLMConfigError("api_key is still empty or a placeholder")
    if config.model != EXPECTED_MODEL:
        raise LLMConfigError(f"model is frozen to {EXPECTED_MODEL}, got {config.model!r}")
    parsed = urlparse(config.base_url)
    if parsed.scheme != "https" or not parsed.netloc.endswith("aliyuncs.com"):
        raise LLMConfigError("base_url must be an HTTPS aliyuncs.com endpoint")
    if not parsed.path.rstrip("/").endswith("compatible-mode/v1"):
        raise LLMConfigError("base_url must end with /compatible-mode/v1")
    if not 0.0 <= config.temperature <= 2.0:
        raise LLMConfigError("temperature must be in [0, 2]")
    if not 0.0 < config.top_p <= 1.0:
        raise LLMConfigError("top_p must be in (0, 1]")
    if config.max_output_tokens <= 0 or config.timeout_seconds <= 0:
        raise LLMConfigError("token and timeout limits must be positive")
    if not 0 <= config.max_retries <= 10:
        raise LLMConfigError("max_retries must be in [0, 10]")
    if config.config_version != "1.0":
        raise LLMConfigError("unsupported config_version")
    if config.shared_by != EXPECTED_METHODS:
        raise LLMConfigError(
            "shared_by must preserve the frozen baseline order: "
            + ", ".join(EXPECTED_METHODS)
        )
