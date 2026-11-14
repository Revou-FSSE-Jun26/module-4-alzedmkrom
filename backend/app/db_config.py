"""Database configuration and connection handling (Requirement 11)."""
import os
import time

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

CONNECT_TIMEOUT_S = 10
MAX_CONNECT_ATTEMPTS = 3


class DatabaseConfigError(RuntimeError):
    """DATABASE_URL is missing or empty."""


class DatabaseUnreachableError(RuntimeError):
    """The database could not be reached after all attempts."""


def normalize_database_url(raw):
    """Req 11.2, 11.3, 11.5. Reads nothing but its argument."""
    if raw is None or not raw.strip():
        raise DatabaseConfigError("DATABASE_URL is not set or is empty")
    if raw.startswith("postgres://"):
        # Only the scheme changes.
        return "postgresql://" + raw[len("postgres://"):]
    return raw


def running_on_railway(env=os.environ):
    return bool(env.get("RAILWAY_PROJECT_ID") or env.get("RAILWAY_ENVIRONMENT_NAME"))


def engine_options(env=os.environ):
    """Req 11.4, 11.6. connect_timeout bounds each attempt to 10 s (libpq)."""
    connect_args = {"connect_timeout": CONNECT_TIMEOUT_S}
    if running_on_railway(env) or env.get("DB_REQUIRE_SSL") == "1":
        connect_args["sslmode"] = "require"
    return {"pool_pre_ping": True, "connect_args": connect_args}


def verify_connection(engine, *, attempts=MAX_CONNECT_ATTEMPTS, delay=1.0, sleep=time.sleep):
    """Req 11.6, 11.7. Up to `attempts` tries; error text never contains the password."""
    for n in range(1, attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError:
            if n < attempts:
                sleep(delay)
    safe_url = engine.url.render_as_string(hide_password=True)
    raise DatabaseUnreachableError(
        f"Database unreachable after {attempts} attempts: {safe_url}"
    ) from None  # drop the driver exception chain
