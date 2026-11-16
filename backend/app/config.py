"""Environment-driven application settings."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

DEFAULT_CORS_ORIGINS: tuple[str, ...] = ("http://localhost:3000",)
DEFAULT_EXPIRES = 3600


@dataclass(frozen=True)
class Settings:
    jwt_secret_key: str
    jwt_access_token_expires: int  # seconds
    cors_origins: tuple[str, ...]
    swagger_enabled: bool


def parse_cors_origins(raw: str | None) -> tuple[str, ...]:
    """Split on ',', strip each entry, drop empty ones; default when none remain."""
    if raw is None:
        return DEFAULT_CORS_ORIGINS
    origins = tuple(p.strip() for p in raw.split(",") if p.strip())
    return origins or DEFAULT_CORS_ORIGINS


def parse_swagger_enabled(raw: str | None) -> bool:
    """False only when the trimmed value equals 'false' case-insensitively."""
    if raw is None:
        return True
    return raw.strip().casefold() != "false"


def parse_expires(raw: str | None) -> int:
    """3600 when unset or empty; otherwise a positive decimal integer."""
    if raw is None or raw == "":
        return DEFAULT_EXPIRES
    if re.fullmatch(r"[0-9]+", raw) is None or int(raw) <= 0:
        raise RuntimeError(
            "JWT_ACCESS_TOKEN_EXPIRES must be a positive integer number of seconds"
        )
    return int(raw)


def load_settings(env: Mapping[str, str]) -> Settings:
    secret = env.get("JWT_SECRET_KEY")
    if secret is None or not secret.strip():
        raise RuntimeError("JWT_SECRET_KEY is not set or is empty")
    return Settings(
        jwt_secret_key=secret,
        jwt_access_token_expires=parse_expires(env.get("JWT_ACCESS_TOKEN_EXPIRES")),
        cors_origins=parse_cors_origins(env.get("CORS_ORIGINS")),
        swagger_enabled=parse_swagger_enabled(env.get("SWAGGER_ENABLED")),
    )


def compile_origins(origins: Iterable[str]) -> list[re.Pattern]:
    """Anchored, case-sensitive exact-match patterns."""
    return [re.compile(re.escape(o) + r"\Z") for o in origins]
