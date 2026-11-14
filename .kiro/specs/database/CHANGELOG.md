# Changelog

## V1 - Initial Release
- Initial requirements, design and tasks generated for the RevoTask database layer.
- Requirements: 12 requirements covering users, boards and membership roles, columns, cards, comments, notifications, activity log and analytics support, referential integrity, indexing, migrations, PostgreSQL configuration and seed data.
- Design: 8 tables, SQLAlchemy models with a float `order` column on `cards` and `columns`, FK delete rules, `updated_at` trigger, `db_config.py`, migration strategy, `flask seed` command, reference queries, 26 correctness properties.
- Tasks: 12 top-level tasks with optional test sub-tasks and a dependency graph.
- Implementation scope established. Nothing is implemented yet.

### Type of change
- Specification change.

## V2 - 2026-11-14
### Changes
- Requirement 11.6 split into two criteria. Criterion 6 now retries a failed startup connection attempt, each attempt bounded to 10 seconds, for up to 3 attempts in total. New criterion 7 raises the "database unreachable" error, without the password, only after all 3 attempts fail.
- Requirement 4.7 reviewed with no text change. It already nulls `assignee_id` for all cards, including soft-deleted ones.

### Reason
- Requirements analysis raised two questions. The user chose to nullify `assignee_id` for soft-deleted cards as well, and to retry the connection before failing. The retry count of 3 was chosen by the assistant because the user only said "one or more".

### Impact
- Requirements: 11.6 (changed), 11.7 (added), 4.7 (confirmed, unchanged).
- Design: `db_config.py` (`MAX_CONNECT_ATTEMPTS = 3`, `verify_connection`), Properties 24 and 25. The design was generated after this change and already matches it.
- Tasks: 2.1, 2.3, 2.4 and 3.2 already reference 11.6 and 11.7. No task changes.
- Implementation: none. Nothing is implemented.

### Type of change
- Specification change.
## V3 - 2026-11-14
### Changes
- Test database changed from PostgreSQL 16 to PostgreSQL 18. The `conftest.py` fixtures use `TEST_DATABASE_URL` if set. Otherwise they start a throwaway PostgreSQL 18 cluster (`initdb` + `pg_ctl` in a temp directory, localhost, free port) from the locally installed binaries and remove it at session end. SQLite is still never used.
- Design "Tools" no longer lists `pytest-postgresql`.
- Added steering file `.kiro/steering/database-testing.md` so new sessions use this setup.
### Reason
- PostgreSQL 18 is already installed on the user's machine and version 16 is not required.
### Impact
- Requirements: none (no version stated). Requirement 11.1 still holds.
- Design: Testing "Tools" section.
- Tasks: 6.1 text and the closing notes. No status changes.
### Type of change
- Specification change.
- Implementation change: `backend/tests/database/conftest.py` (version check 16 to 18, throwaway cluster fixture `database_url`).
