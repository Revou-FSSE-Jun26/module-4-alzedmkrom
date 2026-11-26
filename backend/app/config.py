"""Environment-driven application settings (BE-SEC-01, BE-SEC-02)."""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

DEFAULT_CORS_ORIGINS: tuple[str, ...] = ("http://localhost:3000",)
DEFAULT_EXPIRES_MINUTES = 60


@dataclass(frozen=True)
class Settings:
    jwt_secret_key: str
    jwt_expires_minutes: int
    cors_origins: tuple[str, ...]
    secret_key: str | None


def parse_cors_origins(raw: str | None) -> tuple[str, ...]:
    """Split on ',', strip each entry, drop empty ones; default when none remain."""
    if raw is None:
        return DEFAULT_CORS_ORIGINS
    origins = tuple(p.strip() for p in raw.split(",") if p.strip())
    return origins or DEFAULT_CORS_ORIGINS


def parse_expires_minutes(raw: str | None) -> int:
    """60 when unset or empty; otherwise a positive decimal integer of minutes."""
    if raw is None or raw.strip() == "":
        return DEFAULT_EXPIRES_MINUTES
    value = raw.strip()
    if re.fullmatch(r"[0-9]+", value) is None or int(value) <= 0:
        raise RuntimeError("JWT_EXPIRES_MINUTES must be a positive integer number of minutes")
    return int(value)


def load_settings(env: Mapping[str, str]) -> Settings:
    secret = env.get("JWT_SECRET_KEY")
    if secret is None or not secret.strip():
        raise RuntimeError("JWT_SECRET_KEY is not set or is empty")
    return Settings(
        jwt_secret_key=secret,
        jwt_expires_minutes=parse_expires_minutes(env.get("JWT_EXPIRES_MINUTES")),
        cors_origins=parse_cors_origins(env.get("CORS_ORIGINS")),
        secret_key=env.get("SECRET_KEY") or None,
    )


def compile_origins(origins: Iterable[str]) -> list[re.Pattern]:
    """Anchored, case-sensitive exact-match patterns."""
    return [re.compile(re.escape(o) + r"\Z") for o in origins]
