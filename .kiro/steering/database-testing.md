# Database testing

- Database tests (`backend/tests/database/`) run against real PostgreSQL 18, never SQLite and never PostgreSQL 16.
- Do not install or download PostgreSQL, `pgserver` or other embedded packages. PostgreSQL 18 is installed at `C:\Program Files\PostgreSQL\18` (override with `PG_BIN_DIR`).
- Run `python -m pytest tests/database` from `backend/`. With `TEST_DATABASE_URL` unset, the `database_url` fixture in `conftest.py` starts a throwaway cluster (`initdb` + `pg_ctl` in a temp directory, 127.0.0.1, free port), runs `flask db upgrade`, and removes it at session end. Do not ask the user for a database URL.
- If `TEST_DATABASE_URL` is set, it is used as is (must be PostgreSQL 18).
- Start `pg_ctl` with stdout/stderr set to DEVNULL. Captured pipes are inherited by the server and make the run hang.
- Do not touch the `postgresql-x64-18` Windows service or its data.
