import os

# Must be set at import time, before any app/config import reads the environment.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-not-for-production-0123456789")
