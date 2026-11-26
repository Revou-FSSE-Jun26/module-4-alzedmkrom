# Implementation Plan: RevoTask Database Layer

> **Superseded in V4.** The task list below is the V3 list. It is kept for history (see also `history/tasks-V3.md`). Its checkbox states describe V3 work and do not describe the V4 branch. The V4 section at the end of this file replaces it. The V3 code in `backend/app/models` and `backend/migrations/versions/0001_initial_schema.py` is V3 output and is regenerated on the V4 branch.

## Overview

Implementation is in Python (Flask, Flask-SQLAlchemy, Flask-Migrate, PostgreSQL) under `/backend`. The order is: scaffolding and extensions, database configuration, mixins and app factory, one model per table (indexes and CHECK constraints are declared in each model), the initial migration with the `updated_at` trigger, reference queries, the seed command, then tests. Property-based tests use Hypothesis against a real PostgreSQL instance. Example, smoke and integration tests cover schema shape, indexes, migrations, performance and seed behavior.

All paths below are relative to `/backend`. Test files live in `tests/database/`.

## Tasks

- [x] 1. Set up project scaffolding and extensions *(SUPERSEDED in V4)*
  - [x] 1.1 Create the backend package structure, dependencies and extensions module
    - Create `app/__init__.py` (empty for now), `app/extensions.py`, `app/models/__init__.py` (empty for now), `tests/__init__.py`, `tests/database/__init__.py`
    - Create `requirements.txt` pinning Flask, Flask-SQLAlchemy (SQLAlchemy 2.x), Flask-Migrate (4.x, current Alembic), `psycopg2-binary`, `click`, `pytest`, `hypothesis`
    - Implement `app/extensions.py` with `NAMING_CONVENTION`, `db = SQLAlchemy(metadata=MetaData(naming_convention=...))` and `migrate = Migrate()`
    - Add `pytest.ini` (test paths, Hypothesis profile placeholder) and a `.env.example` listing `DATABASE_URL`, `DB_REQUIRE_SSL`, `SEED_PASSWORD` with no real credentials
    - _Requirements: 11.1, 11.2_

- [x] 2. Implement database configuration and connection handling *(SUPERSEDED in V4)*
  - [x] 2.1 Implement `app/db_config.py`
    - Add `DatabaseConfigError`, `DatabaseUnreachableError`, `CONNECT_TIMEOUT_S = 10`, `MAX_CONNECT_ATTEMPTS = 3`
    - Implement `normalize_database_url`, `running_on_railway`, `engine_options` (`pool_pre_ping`, `connect_timeout`, `sslmode=require` on Railway or when `DB_REQUIRE_SSL=1`) and `verify_connection` (3 attempts, injected `sleep`, password hidden, driver exception chain suppressed)
    - _Requirements: 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

  - [ ]* 2.2 Write property test for URL normalization
    - Create `tests/database/test_prop_url_normalization.py`
    - **Property 22: Only the leading `postgres://` scheme is rewritten**
    - **Validates: Requirements 11.3**

  - [ ]* 2.3 Write property test for bounded connection attempts
    - Create `tests/database/test_prop_connection_attempts.py` using a fake engine with scripted `OperationalError` and an injected `sleep`
    - **Property 24: Connection attempts are bounded at three**
    - **Validates: Requirements 11.6, 11.7**

  - [ ]* 2.4 Write property test for password redaction in errors
    - Create `tests/database/test_prop_password_redaction.py`
    - **Property 25: Unreachable-database errors never contain the password**
    - **Validates: Requirements 11.7**

  - [ ]* 2.5 Write unit tests for configuration
    - Create `tests/database/test_db_config.py`
    - Test `engine_options` with and without `RAILWAY_PROJECT_ID` / `RAILWAY_ENVIRONMENT_NAME` / `DB_REQUIRE_SSL`
    - Test a source scan that finds no connection strings or credentials in committed files
    - _Requirements: 11.2, 11.4_

- [x] 3. Implement mixins and the application factory *(SUPERSEDED in V4)*
  - [x] 3.1 Implement `app/models/mixins.py`
    - Add `UUIDPrimaryKeyMixin` (Python `uuid.uuid4` default plus `gen_random_uuid()` server default), `CreatedAtMixin`, `TimestampMixin` (`updated_at` with `server_onupdate=FetchedValue()`), `SoftDeleteMixin` (`deleted_at`, `soft_delete()`, `restore()`, `is_deleted`)
    - _Requirements: 1.5, 1.6, 3.6, 4.4, 4.5, 5.4_

  - [x] 3.2 Implement the app factory in `app/__init__.py`
    - `create_app(verify_db=True)` normalizes `DATABASE_URL` before `db.init_app`, sets `SQLALCHEMY_ENGINE_OPTIONS`, initializes `migrate` with `compare_type=True`, `render_as_batch=False`, `transaction_per_migration=True` and `process_revision_directives=skip_empty_revision`
    - Import `app.models` so tables register, and call `verify_connection(db.engine)` inside an app context when `verify_db` is true
    - Define `skip_empty_revision` (clears `script.upgrade_ops` when there are no operations)
    - Do not call `upgrade()` from the factory
    - _Requirements: 10.5, 10.6, 11.3, 11.4, 11.5, 11.6, 11.7_

  - [ ]* 3.3 Write property test for blank `DATABASE_URL`
    - Create `tests/database/test_prop_blank_database_url.py`; patch `init_app` to assert no engine is created
    - **Property 23: Blank `DATABASE_URL` is rejected before an engine exists**
    - **Validates: Requirements 11.5**

- [x] 4. Implement models, one per table *(SUPERSEDED in V4)*
  - [x] 4.1 Implement `User` in `app/models/user.py`
    - Columns `name`, `email`, `password_hash`; checks `ck_users_name_length` (1 or more characters), `ck_users_email_length` (3 to 254) and `ck_users_password_hash_length` (1 or more characters), all per OD-3; unique functional index `uq_users_email_lower` on `lower(email)`; no plaintext password column
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.7_

  - [x] 4.2 Implement `Board` and `BoardMember` in `app/models/board.py`
    - `Board`: `name` check (1 to 255), `owner_id` FK `ON DELETE RESTRICT`, relationships with `passive_deletes=True`
    - `BoardMember`: composite PK (`board_id`, `user_id`), FKs `ON DELETE CASCADE`, `role` check `IN ('member', 'admin')`, index `ix_board_members_user_id`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 2.7, 2.8, 2.9, 8.3, 8.6, 9.5_

  - [x] 4.3 Implement `BoardColumn` in `app/models/column.py`
    - Table `columns`; `board_id` FK `CASCADE`; `title` check (1 to 255); `order = db.Column(db.Float, nullable=False)` with check `"order" > 0 AND "order" < 'Infinity'`; index `ix_columns_board_id_order`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 8.3, 9.3_

  - [x] 4.4 Implement `Card` in `app/models/card.py`
    - `column_id` FK `CASCADE`, `assignee_id` FK `SET NULL` nullable, `created_by` FK `RESTRICT` not null, `order` Float with the same positive-finite check, `completed_at` timestamptz, title and description length checks
    - Indexes `ix_cards_column_id_order`, `ix_cards_assignee_id`, `ix_cards_completed_at`
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6, 4.7, 4.8, 4.9, 8.4, 9.1, 9.2, 9.7_

  - [x] 4.5 Implement `Comment` in `app/models/comment.py`
    - `card_id` FK `CASCADE`, `user_id` FK `RESTRICT`, `body` check `body ~ '\S' AND char_length(body) <= 5000`, check `updated_at >= created_at`, index `ix_comments_card_id`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 8.5, 9.4_

  - [x] 4.6 Implement `Notification` in `app/models/notification.py`
    - `user_id` FK `CASCADE`, `board_id` FK `CASCADE`, `card_id` FK `SET NULL`, `type` (1 to 50) and `message` (1 to 500) checks, `is_read` Boolean with default and server default false, index `ix_notifications_user_id_created_at`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 8.3_

  - [x] 4.7 Implement `ActivityLog` in `app/models/activity_log.py`
    - `board_id` FK `CASCADE`, `user_id` FK `RESTRICT`, `card_id` FK `SET NULL`, `action` check (1 to 100), index `ix_activity_logs_board_id_created_at`
    - _Requirements: 7.1, 7.7, 8.3, 9.6_

  - [x] 4.8 Register all models in `app/models/__init__.py`
    - Import `User`, `Board`, `BoardMember`, `BoardColumn`, `Card`, `Comment`, `Notification`, `ActivityLog` so Alembic sees every table
    - _Requirements: 8.1, 10.2_

- [x] 5. Create migrations including triggers *(SUPERSEDED in V4)*
  - [x] 5.1 Initialize Flask-Migrate
    - Run `flask db init` to create `migrations/`; configure `migrations/env.py` for `compare_type`, `transaction_per_migration` and an optional `include_object` hook (kept as a fallback only if autogenerate reports a spurious diff for `uq_users_email_lower`)
    - _Requirements: 10.1, 10.5, 10.6_

  - [x] 5.2 Write the initial revision `0001_initial_schema`
    - Autogenerate, then review and hand-edit: all CHECK constraints, the `lower(email)` unique index, and `server_default=gen_random_uuid()` defaults
    - Create the `set_updated_at()` PL/pgSQL function (pins `created_at`, sets `updated_at := GREATEST(now(), OLD.updated_at)`) and `BEFORE UPDATE` triggers on `users`, `boards`, `columns`, `cards`, `comments`
    - Add the `_create_index` helper that wraps failures in `RuntimeError("Failed to create index <name>")`
    - Implement `downgrade()` that drops triggers, function, indexes and tables in reverse dependency order
    - Verify exactly one head with `flask db heads`
    - _Requirements: 1.6, 4.4, 5.7, 9.9, 10.1, 10.2, 10.3, 10.4, 10.6_

- [x] 6. Set up test infrastructure *(SUPERSEDED in V4)*
  - [x] 6.1 Create `tests/database/conftest.py` and shared helpers
    - Session fixture that builds the schema with `flask db upgrade` against PostgreSQL 18 (never SQLite). Use `TEST_DATABASE_URL` if set; otherwise start a throwaway cluster from the locally installed PostgreSQL 18 binaries (`initdb` + `pg_ctl` in a temp directory, free localhost port) and remove it at session end
    - Per-example transaction fixture that rolls back, with `begin_nested()` helper for statements expected to fail
    - Hypothesis settings profile (`max_examples=100`, `deadline=None`)
    - Shared strategies: text with whitespace and non-BMP characters, floats with NaN and infinity, timezone-aware datetimes, composite board-graph strategy
    - Field registry `(table, column, min, max, nullable)` used by length tests and schema reflection
    - _Requirements: 10.2, 11.1_

- [x] 7. Implement reference queries *(SUPERSEDED in V4)*
  - [x] 7.1 Implement `app/models/queries.py`
    - `week_bounds_utc`, `card_counts_per_column`, `completed_this_week`, `member_activity`, `my_tasks`, `search_cards` (1 to 200 chars, `icontains(autoescape=True)`), `notifications_page` (limit 1 to 100, offset 0 to 1,000,000), `load_board` (three indexed queries)
    - Live cards exclude soft-deleted cards and cards under soft-deleted columns or boards
    - _Requirements: 6.3, 6.6, 7.2, 7.3, 7.4, 7.5, 7.6, 9.8_

  - [ ]* 7.2 Write property test for notification pages
    - Create `tests/database/test_prop_notification_pages.py`
    - **Property 16: Notification pages match the reference slice**
    - **Validates: Requirements 6.3, 6.6**

  - [ ]* 7.3 Write property test for card counts per column
    - Create `tests/database/test_prop_card_counts.py`
    - **Property 17: Card counts per column match the data**
    - **Validates: Requirements 7.2**

  - [ ]* 7.4 Write property test for weekly completion counts
    - Create `tests/database/test_prop_weekly_completion.py`, including instants at and one microsecond either side of the week boundaries
    - **Property 18: Weekly completion counts respect the week boundaries**
    - **Validates: Requirements 7.3**

  - [ ]* 7.5 Write property test for member activity
    - Create `tests/database/test_prop_member_activity.py`
    - **Property 19: Member activity counts match the logs**
    - **Validates: Requirements 7.4**

  - [ ]* 7.6 Write property test for my-tasks
    - Create `tests/database/test_prop_my_tasks.py`
    - **Property 20: My-tasks returns exactly the user's live assigned cards**
    - **Validates: Requirements 7.5**

  - [ ]* 7.7 Write property test for card search
    - Create `tests/database/test_prop_card_search.py`, including terms with `%`, `_` and mixed case
    - **Property 21: Search is a case-insensitive substring match on title or description**
    - **Validates: Requirements 7.6**

- [x] 8. Implement the seed command *(SUPERSEDED in V4)*
  - [x] 8.1 Implement `app/seed.py` and register it
    - `flask seed [--force]`: refuses on Railway without `--force`; deterministic `uuid5` ids; `postgresql.insert(...).on_conflict_do_nothing()`; one transaction
    - Rows: 2 users (`alice@revotask.test`, `bob@revotask.test`, password hash from `SEED_PASSWORD`), 1 board, memberships `admin` and `member`, 3 columns (orders 1.0, 2.0, 3.0), 5 cards (2, 2, 1)
    - Print `Seeding finished.` and exit 0 on success; roll back, print `Seeding failed: <cause>` and exit 1 on error
    - Register `seed_command` in `create_app` via `app.cli.add_command`
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

  - [ ]* 8.2 Write property test for seed idempotence
    - Create `tests/database/test_prop_seed_idempotent.py`
    - **Property 26: Seeding is idempotent**
    - **Validates: Requirements 12.2**

  - [ ]* 8.3 Write example tests for the seed command
    - Create `tests/database/test_seed.py` using `CliRunner`
    - Empty database yields the expected rows and counts, exit 0 and the success message
    - An injected failure rolls back everything, exits 1 and reports the cause
    - Railway guard refuses without `--force`
    - _Requirements: 12.1, 12.3, 12.4_

- [x] 9. Checkpoint - Ensure all tests pass *(SUPERSEDED in V4)*
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Write property tests for constraints, triggers and foreign keys *(SUPERSEDED in V4)*
  - [ ]* 10.1 Write property test for case-insensitive email uniqueness
    - Create `tests/database/test_prop_email_unique.py`
    - **Property 1: Email uniqueness is case-insensitive**
    - **Validates: Requirements 1.2, 1.4**

  - [ ]* 10.2 Write property test for bounded text fields
    - Create `tests/database/test_prop_text_bounds.py` driven by the field registry
    - **Property 2: Bounded text fields accept exactly their length range**
    - **Validates: Requirements 1.7, 2.9, 3.2, 3.5, 4.1, 5.5, 6.2, 7.1**

  - [ ]* 10.3 Write property test for comment bodies
    - Create `tests/database/test_prop_comment_body.py`
    - **Property 3: Comment bodies must contain a non-whitespace character**
    - **Validates: Requirements 5.5**

  - [ ]* 10.4 Write property test for order values
    - Create `tests/database/test_prop_order_values.py` for `columns` and `cards`, including `NaN` and infinities
    - **Property 4: Order values must be positive and finite**
    - **Validates: Requirements 3.3, 4.3**

  - [ ]* 10.5 Write property test for membership roles
    - Create `tests/database/test_prop_roles.py`
    - **Property 5: Membership roles are restricted to the allowed set**
    - **Validates: Requirements 2.4, 2.7**

  - [ ]* 10.6 Write property test for duplicate memberships
    - Create `tests/database/test_prop_membership_unique.py`
    - **Property 6: A user has at most one membership per board**
    - **Validates: Requirements 2.3, 2.8**

  - [ ]* 10.7 Write property test for orphan foreign keys
    - Create `tests/database/test_prop_orphan_fk.py`, iterating `db.metadata.tables` and their `ForeignKey` objects
    - **Property 7: Orphan foreign keys are rejected atomically**
    - **Validates: Requirements 3.4, 4.9, 5.6, 6.5, 7.7, 8.2**

  - [ ]* 10.8 Write property test for generated defaults
    - Create `tests/database/test_prop_defaults.py` using raw SQL inserts
    - **Property 8: Inserts without defaults get generated values**
    - **Validates: Requirements 1.5, 3.6, 6.1, 7.1**

  - [ ]* 10.9 Write property test for `updated_at` and `created_at`
    - Create `tests/database/test_prop_updated_at.py`, including updates that try to set `created_at` or move `updated_at` backwards
    - **Property 9: Updates advance `updated_at` and never change `created_at`**
    - **Validates: Requirements 1.6, 4.4, 5.7**

  - [ ]* 10.10 Write property test for soft delete and timestamps
    - Create `tests/database/test_prop_soft_delete.py`
    - **Property 10: Soft delete and timestamps keep the row intact**
    - **Validates: Requirements 4.5, 4.8, 5.4**

  - [ ]* 10.11 Write property test for cascading hard deletes
    - Create `tests/database/test_prop_cascade.py` using the board-graph strategy
    - **Property 11: Hard delete cascades to all dependents**
    - **Validates: Requirements 8.3, 8.4, 8.5**

  - [ ]* 10.12 Write property test for restricted deletes
    - Create `tests/database/test_prop_restrict.py`
    - **Property 12: Deleting a referenced parent without a cascade rule is rejected**
    - **Validates: Requirements 8.7**

  - [ ]* 10.13 Write property test for user removal and card assignment
    - Create `tests/database/test_prop_unassign.py`, including soft-deleted cards
    - **Property 13: Removing a user unassigns their cards but keeps them**
    - **Validates: Requirements 4.7**

  - [ ]* 10.14 Write property test for member removal
    - Create `tests/database/test_prop_member_removal.py`
    - **Property 14: Removing a member keeps their authored content**
    - **Validates: Requirements 2.6**

  - [ ]* 10.15 Write property test for marking notifications read
    - Create `tests/database/test_prop_mark_read.py`
    - **Property 15: Marking a notification read changes only `is_read`**
    - **Validates: Requirements 6.4**

- [ ] 11. Write example, smoke and integration tests *(SUPERSEDED in V4)*
  - [ ]* 11.1 Write schema-shape and NOT NULL tests
    - Create `tests/database/test_schema_shape.py`
    - Reflect the migrated database: tables, columns, types (`order` is `double precision` NOT NULL), NOT NULL flags, no `password` column, UUID primary keys, composite PK on `board_members`, every `*_id` column has an FK
    - Parametrized inserts with each required column set to NULL
    - Assert the CHECK constraints from the field registry exist in the reflected schema
    - _Requirements: 1.1, 1.3, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2, 5.3, 6.1, 7.1, 8.1, 8.6, 11.1_

  - [ ]* 11.2 Write board-creation and unassigned-card tests
    - Create `tests/database/test_board_flows.py`
    - Board plus `admin` membership stored in one transaction; card with NULL `assignee_id` is accepted
    - _Requirements: 2.5, 4.6_

  - [ ]* 11.3 Write index and query-plan tests
    - Create `tests/database/test_indexes.py`
    - Reflect indexes and assert names, columns and leading keys
    - `EXPLAIN` on cards-by-column, columns-by-board and the notifications page shows an index scan and no `Sort` node
    - _Requirements: 6.3, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

  - [ ]* 11.4 Write the board-load performance test
    - Create `tests/database/test_performance.py`
    - Seed 50 columns and 5,000 cards, run the three `load_board` queries 100 times and assert p95 at most 200 ms each
    - _Requirements: 9.8_

  - [ ]* 11.5 Write migration chain and upgrade/downgrade tests
    - Create `tests/database/test_migrations.py`
    - One head and a single linear chain; `upgrade` on an empty database exits 0 with current equal to head; a second `upgrade` is a no-op and rows are unchanged; `downgrade -1` returns to the previous revision; `flask db check` and `compare_metadata` report no differences (including `uq_users_email_lower`)
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]* 11.6 Write migration failure tests
    - Create `tests/database/test_migration_failure.py`
    - A temporary failing revision gives a non-zero exit, a message with the revision id, and the database stays at the previous revision
    - A forced index failure names the index and leaves no tables from that revision
    - _Requirements: 9.9, 10.6_

- [ ] 12. Final checkpoint - Ensure all tests pass *(SUPERSEDED in V4)*
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP.
- Each task references specific requirements for traceability.
- Checkpoints ensure incremental validation.
- Property tests validate universal correctness properties and run against a real PostgreSQL 18 database, never SQLite.
- Unit and example tests validate specific examples, schema shape and tooling behavior.
- Alembic does not detect CHECK constraint or trigger changes, so those parts of revision `0001` are written by hand.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "3.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "2.5", "3.2", "4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7"] },
    { "id": 3, "tasks": ["3.3", "4.8"] },
    { "id": 4, "tasks": ["5.1", "7.1"] },
    { "id": 5, "tasks": ["5.2", "8.1"] },
    { "id": 6, "tasks": ["6.1"] },
    {
      "id": 7,
      "tasks": [
        "7.2", "7.3", "7.4", "7.5", "7.6", "7.7",
        "8.2", "8.3",
        "10.1", "10.2", "10.3", "10.4", "10.5", "10.6", "10.7", "10.8",
        "10.9", "10.10", "10.11", "10.12", "10.13", "10.14", "10.15",
        "11.1", "11.2", "11.3", "11.4", "11.5", "11.6"
      ]
    }
  ]
}
```

---

# V4 Implementation Plan: RevoTask Database Layer

Version: V4 (2026-11-21)

## V4 Overview

This section regenerates the database layer on `main`. No branch is created (OD-8, resolved). The source of truth is `.kiro/steering/database.md`. Requirements are in `requirements.md` (V4). Design is in `design.md` (V4). Changes are recorded in `CHANGELOG.md` (V4).

All work is committed directly on `main`. Do not create a branch (OD-8, resolved by the user). Do not reset or force-push the local `main`. Do not commit the unrelated change to `docs/violation_report.md`.

All paths are relative to `/backend`. Test files live in `tests/database/`. Test tasks are required, not optional, because DB-TST-01 requires them.

## V4 Tasks

- [ ] 0. Prepare the branch and settle open decisions
  - [ ] 0.1 OD-7 resolved from the baseline: `0001_initial_schema` is applied in the local database `revotask_db` and is not edited. Before task 3.2, confirm that `revotask_db` is at `0001_initial_schema` (`flask db current`). The V4 change is revision `0002_v4_schema` on `main`. This changes the V4 draft, which planned a new `0001`.
    - _Requirements: 10.1, 10.7_
  - [ ] 0.2 No branch (OD-8, resolved by the user). Commit directly on `main`. Record the HEAD commit hash at the start of V4 work in the CHANGELOG V4 entry.
    - _Requirements: 10.1_
  - [ ] 0.3 Record the open-decision resolutions in the CHANGELOG V4 entry before task 2. Resolved on 2026-11-21: OD-1, OD-2, OD-3, OD-4, OD-5, OD-7, OD-8, OD-9 and OD-10. OD-6 (member activity counts) is still open and needs a user decision before task 7.4.
    - _Requirements: 6.1, 1.7, 4.3, 14.6_

- [ ] 1. Carry over scaffolding and connection code from V3
  - [ ] 1.1 Keep `app/extensions.py`, `app/db_config.py`, `requirements.txt` and `pytest.ini` from V3 without behavior change. Update `.env.example` to list `DATABASE_URL`, `DB_REQUIRE_SSL`, `FLASK_ENV`, `SEED_PASSWORD` with no real credentials.
    - _Requirements: 11.1, 11.2, 11.3, 12.5, 12.6_
  - [ ] 1.2 Keep the V3 tests `test_prop_url_normalization.py`, `test_prop_connection_attempts.py`, `test_prop_password_redaction.py`, `test_prop_blank_database_url.py` and `test_db_config.py` unchanged, and run them.
    - _Requirements: 11.3, 11.5, 11.6, 11.7_

- [ ] 2. Regenerate mixins and models (one model per table)
  - [ ] 2.1 Rewrite `app/models/mixins.py`: `UUIDPrimaryKeyMixin`, `CreatedAtMixin`, `TimestampMixin`, and `SoftDeleteMixin` with `soft_delete()` only. Do not add `restore()` or `is_deleted`.
    - _Requirements: 1.5, 1.6, 3.6, 4.5, 14.3, 14.4_
  - [ ] 2.2 Rewrite `app/models/user.py`: `name` VARCHAR(100), `email` VARCHAR(255), `password_hash` VARCHAR(255), checks `ck_users_name_length` (1 or more characters), `ck_users_email_length` (3 to 254) and `ck_users_password_hash_length` (1 or more characters) per OD-3, index `uq_users_email_lower` on `lower(email)`. No `role` column.
    - _Requirements: 1.1, 1.2, 1.3, 1.7, 1.8, 14.1_
  - [ ] 2.3 Rewrite `app/models/board.py`: `Board` with `name` VARCHAR(100) and check `ck_boards_name_length` (1 or more characters, OD-3), `is_public` (default true, server default), `created_by` SET NULL, partial index `ix_boards_created_at_public`, no `deleted_at`. `BoardMember` with composite PK, `role` VARCHAR(10) and check `ck_board_members_role`, `added_by` SET NULL, `created_at` only, index `ix_board_members_user_id`.
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.10, 2.11, 2.12, 2.13, 9.11, 9.12_
  - [ ] 2.4 Rewrite `app/models/column.py`: table `columns`, `name` VARCHAR(100), `order = db.Column("position", db.Float(53))`, `is_done` default false, `created_by` SET NULL, `UNIQUE (id, board_id)`, check `ck_columns_position` (`"position" > 0 AND "position" < 'Infinity'`, OD-4), check `ck_columns_name_length` (1 or more characters, OD-3), partial unique index `uq_columns_board_id_done`, index `ix_columns_board_id_position`. No `deleted_at`.
    - _Requirements: 3.1, 3.2, 3.3, 3.5, 3.6, 3.7, 3.8, 3.9, 9.13, 9.14_
  - [ ] 2.5 Rewrite `app/models/card.py`: `board_id` NOT NULL, `column_id`, composite `ForeignKeyConstraint` to `columns (id, board_id)` with CASCADE, `title` VARCHAR(200), `description` with check `ck_cards_description_length` (5000), `due_date` DATE, `order` on `position` with check `ck_cards_position` (`"position" > 0 AND "position" < 'Infinity'`, OD-4), `completed_at`, `deleted_at` via `SoftDeleteMixin`, `created_by` SET NULL, `assignee_id` SET NULL. Add `Card.active()`. Add the four partial indexes. Add check `ck_cards_title_length` (1 or more characters, OD-3). The maximum comes from `VARCHAR(200)`.
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11, 4.12, 4.13, 4.14, 9.15, 9.16, 9.17, 9.18_
  - [ ] 2.6 Rewrite `app/models/comment.py`: `card_id` CASCADE, `content` TEXT with check `ck_comments_content_length` (1 to 2000), `created_by` SET NULL, check `ck_comments_updated_after_created`, indexes `ix_comments_card_id_created_at` and `ix_comments_created_by`. No `deleted_at`. Do not use a regex check.
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 9.19, 9.20_
  - [ ] 2.7 Rewrite `app/models/notification.py`: `user_id` CASCADE, `type` VARCHAR(30) with check `ck_notifications_type` (baseline list, OD-1), `message` VARCHAR(500), `board_id` UUID with no foreign key, `is_read` default false, `created_at` only. Indexes `ix_notifications_user_id_created_at` (DESC) and partial `ix_notifications_user_id_unread`.
    - _Requirements: 6.1, 6.2, 6.7, 9.21, 9.22_
  - [ ] 2.8 Delete `app/models/activity_log.py` and its export. This is a breaking change recorded in the CHANGELOG.
    - _Requirements: 7.1_
  - [ ] 2.9 Rewrite `app/models/__init__.py` to export `User`, `Board`, `BoardMember`, `BoardColumn`, `Card`, `Comment`, `Notification`.
    - _Requirements: 8.1, 14.1_

- [ ] 3. Regenerate migrations
  - [ ] 3.1 Check `migrations/env.py` for `compare_type=True`, `transaction_per_migration=True` and `process_revision_directives=skip_empty_revision`. Keep the optional `include_object` hook only if the zero-diff test (task 9.1) reports `uq_users_email_lower` as a spurious diff.
    - _Requirements: 10.1, 10.5, 10.6_
  - [ ] 3.2 Write revision `0002_v4_schema` on top of the applied `0001_initial_schema`. Do not edit `0001`. Start from autogenerate against the V3 schema, then review and hand-edit: the V3-to-V4 changes listed in the CHANGELOG V4 Breaking changes (drop `activity_logs` and the V3-only columns, rename `order`, `title`, `body` and `user_id`, add `cards.board_id` in three steps per DB-MIG-03, and move the foreign keys to the DB-CAS-01 rules), all CHECK constraints with their names, partial index predicates, server defaults, the composite FK, `UNIQUE (id, board_id)`, the `_create_index` helper, the `set_updated_at()` function and the five triggers on `users`, `boards`, `columns`, `cards` and `comments`. Do not edit an applied revision.
    - _Requirements: 1.6, 4.4, 5.7, 9.9, 10.2, 10.7_
  - [ ] 3.3 Implement `downgrade()` for `0002`: drop the triggers, the function and the V4 indexes and checks, then restore the V3 shape that `0001` creates (recreate `activity_logs` empty, rename the columns back). `downgrade -1` must return to `0001_initial_schema`. Rows dropped with `activity_logs` are not restored.
    - _Requirements: 10.4, 10.8_
  - [ ] 3.4 Run `flask db heads` and confirm exactly one head, and that the single revision has one parent.
    - _Requirements: 10.1_
  - [ ] 3.5 Add the CI sequence: `flask db upgrade` on an empty database, `flask db downgrade base`, `flask db upgrade`, `flask db heads` with a count of one, and `flask db check`. If the repository has no CI configuration, record this as a missing item and do not invent one.
    - _Requirements: 10.1, 10.5, 10.8_

- [ ] 4. Regenerate reference queries
  - [ ] 4.1 Rewrite `app/models/queries.py` for the V4 schema: `week_bounds_utc`, `card_counts_per_column` (no column deletion filter), `completed_this_week` (uses `cards.board_id`), `member_activity` (three counts for current members only), `my_tasks`, `search_cards` (uses `Card.active()`), `notifications_page` and `load_board`.
    - _Requirements: 6.3, 6.6, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 9.8_

- [ ] 5. Regenerate the seed command
  - [ ] 5.1 Rewrite `app/seed.py`: `flask seed [--force]`, the `FLASK_ENV=production` guard, deterministic `uuid5` ids, fixed `completed_at`, `ON CONFLICT DO NOTHING`, one transaction. Data: 3 users (Alice Admin, Bob Member, Carol Guest-only), demo board (public), sandbox board (private), memberships, 3 demo columns (Done is `is_done`) plus one sandbox column, 6 cards, 2 comments. Alice and Bob are from the baseline seed. Carol is required by DB-SEED-01 (OD-2). Register the command in `create_app`.
    - _Requirements: 2.5, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

- [ ] 6. Test infrastructure
  - [ ] 6.1 Reuse the V3 `database_url` fixture in `tests/database/conftest.py`. It must use PostgreSQL 18, `TEST_DATABASE_URL` when set, and `DEVNULL` for `pg_ctl` stdout and stderr. Build the schema with `flask db upgrade`. Add the field registry `(table, column, min_length, max_length, nullable)` and a per-example rollback fixture with a `begin_nested()` helper.
    - _Requirements: 13.1, 10.2_

- [ ] 7. Constraint, cascade and property tests
  - [ ] 7.1 Create `test_constraints.py` with named tests for duplicate email by case, second done column, position zero, negative, NaN or +Infinity, empty `name`, `title`, `email` and `password_hash` (OD-3), invalid role, duplicate membership, cross-board card move, and comment content length 0, 1, 2000 and 2001.
    - _Requirements: 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.12_
  - [ ] 7.2 Create `test_cascades.py`: board hard delete removes memberships, columns, cards (including soft-deleted) and comments but keeps notifications; user hard delete sets `created_by` and `assignee_id` to NULL and does not fail; soft-deleted card keeps its row and `Card.active()` excludes it.
    - _Requirements: 8.3, 8.4, 8.5, 8.7, 13.8, 13.9, 13.10, 13.11_
  - [ ] 7.3 Implement Properties 1 to 10, 12 to 15 and 27 to 29 as Hypothesis tests, with the comment tag format from the design.
    - _Requirements: 1.2, 1.4, 1.5, 1.6, 1.7, 2.3, 2.4, 2.6, 2.7, 2.8, 2.10, 3.3, 3.4, 3.6, 3.7, 3.8, 4.3, 4.4, 4.5, 4.7, 4.9, 4.10, 4.14, 5.4, 5.5, 5.6, 5.7, 6.4, 7.7, 8.2, 8.7_
  - [ ] 7.4 Implement Properties 16 to 21 (queries), using the three-count definition of Property 19. OD-6 is still open: do not implement the count until the user decides.
    - _Requirements: 6.3, 6.6, 7.2, 7.3, 7.4, 7.5, 7.6_
  - [ ] 7.5 Implement Property 26 (seed idempotence) and the example tests for seed contents, failure rollback and the production guard.
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ] 8. Schema, foreign key, index and naming tests
  - [ ] 8.1 Create `test_schema_shape.py`: tables, column types, NOT NULL flags, `position` as `double precision`, no `password` column, no `activity_logs`, `deleted_at` only on `cards`, UUID primary keys, composite PK on `board_members`, and the nullable and NOT NULL parametrized inserts.
    - _Requirements: 1.1, 1.8, 2.1, 2.2, 3.1, 3.2, 4.1, 5.1, 5.2, 6.1, 7.1, 8.6, 14.3, 14.5_
  - [ ] 8.2 Create `test_foreign_keys.py`: compare each `ondelete` with the DB-CAS-01 table, confirm `notifications.board_id` has no foreign key, and confirm `passive_deletes=True` on the parent relationships.
    - _Requirements: 8.1, 8.9, 8.10_
  - [ ] 8.3 Create `test_indexes.py`: assert the exact set of 13 indexes from Requirement 9 criteria 10 to 22 with names, columns, predicates and uniqueness, and assert no other non-key index. Run `EXPLAIN` on cards by column, columns by board, the notifications page and the weekly completion query, and assert index scans without a Sort node.
    - _Requirements: 6.3, 7.3, 9.10, 9.11, 9.12, 9.13, 9.14, 9.15, 9.16, 9.17, 9.18, 9.19, 9.20, 9.21, 9.22, 9.23, 9.24_
  - [ ] 8.4 Create `test_naming.py`: every index, unique, check, foreign key and primary key name starts with its prefix and follows the convention.
    - _Requirements: 14.2_
  - [ ] 8.5 Create `test_board_flows.py`: a board with its admin membership in one transaction, and a card with a NULL assignee.
    - _Requirements: 2.5, 4.6_
  - [ ] 8.6 Create `test_performance.py`: 50 columns and 5,000 cards, the three `load_board` queries run 100 times, p95 at most 200 ms each.
    - _Requirements: 9.8_

- [ ] 9. Migration tests
  - [ ] 9.1 Create `test_migrations.py`: one head; `upgrade` on an empty database exits 0 and reaches head; a second `upgrade` is a no-op; `downgrade -1` returns to the previous revision; `downgrade base` followed by `upgrade` works; `flask db check` and `compare_metadata` report no differences, including `uq_users_email_lower`.
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.8_
  - [ ] 9.2 Create `test_migration_failure.py`: a temporary failing revision gives a non-zero exit, a message with the revision id, and the database stays at the previous revision. A forced index failure names the index and leaves no tables from that revision.
    - _Requirements: 9.9, 10.6_

- [ ] 10. Checkpoint: run the suite
  - [ ] 10.1 Run `python -m pytest tests/database` from `backend/` against PostgreSQL 18. Record the result in the CHANGELOG V4 entry. Fix failures without changing the requirements.
    - _Requirements: 13.1_

- [ ] 11. Hand-off items outside this spec
  - [ ] 11.1 Raise a separate change request for the backend spec with the list in CHANGELOG V4 Impact. Do not edit `.kiro/specs/backend/` in this spec.
    - _Requirements: 14.5_
  - [ ] 11.2 Write `backend.md` BE-NTF-03 so that its Notification_Type list matches the baseline list in `ck_notifications_type`. OD-1 is already resolved.
    - _Requirements: 6.1_

## V4 Notes

- Tasks 2 to 5 replace the V3 models, migration, queries and seed. They are regenerated, not patched. Do not keep any V3 `activity_log` code.
- `tasks.meta.json` holds execution history for V3 task IDs. It is not updated for V4 task IDs.

## V4 Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["0.1", "0.2", "0.3"] },
    { "id": 1, "tasks": ["1.1"] },
    { "id": 2, "tasks": ["1.2", "2.1"] },
    { "id": 3, "tasks": ["2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8"] },
    { "id": 4, "tasks": ["2.9", "3.1"] },
    { "id": 5, "tasks": ["3.2", "5.1", "4.1"] },
    { "id": 6, "tasks": ["3.3", "3.4", "6.1"] },
    { "id": 7, "tasks": ["3.5", "7.1", "7.2", "7.3", "7.4", "7.5", "8.1", "8.2", "8.3", "8.4", "8.5", "8.6", "9.1", "9.2"] },
    { "id": 8, "tasks": ["10.1", "11.1", "11.2"] }
  ]
}
```