from pathlib import Path
from urllib.parse import urlsplit
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CHANAKYA_",
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="forbid",
    )
    model_name: str = "qwen2.5:3b"
    ollama_base_url: str = "http://127.0.0.1:11434"
    expected_model_digest: str | None = None
    context_tokens: int = Field(default=4096, ge=2048, le=4096)
    output_tokens: int = Field(default=384, ge=128, le=512)
    request_timeout_seconds: float = Field(default=120, gt=0, le=180)
    status_timeout_seconds: float = Field(default=5, gt=0, le=10)
    max_model_attempts: int = Field(default=2, ge=1, le=2)
    max_request_bytes: int = Field(default=16384, ge=1024, le=65536)
    log_level: Literal["INFO", "WARNING", "ERROR"] = "INFO"
    allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"]
    database_path: Path = Path(__file__).resolve().parents[2] / "data" / "chanakya.sqlite3"

    @field_validator("database_path")
    @classmethod
    def local_database(cls, value: Path) -> Path:
        root = Path(__file__).resolve().parents[2]
        value = value if value.is_absolute() else root / value
        value = value.resolve()
        if value.suffix != ".sqlite3" or str(value).startswith(("//", "\\\\")):
            raise ValueError("Use a local .sqlite3 file, not a network share")
        return value

    @field_validator("ollama_base_url")
    @classmethod
    def local_endpoint(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"}):
            raise ValueError("Ollama must use an HTTP loopback endpoint without credentials or a path")
        try:
            parsed.port
        except ValueError as error:
            raise ValueError("Invalid Ollama port") from error
        return value.rstrip("/")

    @field_validator("model_name")
    @classmethod
    def local_model_name(cls, value: str) -> str:
        import re
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._/:-]{0,120}", value) or "cloud" in value.lower():
            raise ValueError("Use an installed local model tag, not a cloud model")
        return value

    @field_validator("expected_model_digest")
    @classmethod
    def digest(cls, value: str | None) -> str | None:
        import re
        if value is not None and not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("Use the full 64-character installed-model digest or omit this setting")
        return value

    @field_validator("allowed_origins")
    @classmethod
    def origins(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("At least one explicit frontend origin is required")
        for value in values:
            parsed = urlsplit(value)
            if (parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
                    or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password):
                raise ValueError("Allow explicit loopback frontend origins only")
        return values
