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

## V4 - 2026-11-21
### Changes

V4 aligns this spec with `.kiro/steering/database.md`, which is the source of truth. Each item shows the V3 state (Before) and the V4 state (After). V3 text is kept in `history/requirements-V3.md`, `history/design-V3.md` and `history/tasks-V3.md`.

Requirements (`requirements.md`, now V4, 14 requirements; V3 had 12):
- Req 1.1 (users). Before: name 1 to 255 characters, email 3 to 254 characters, password_hash text. After: `name` VARCHAR(100), `email` VARCHAR(255), `password_hash` VARCHAR(255), per DB-SCH-01.
- Req 1.7 (users constraints). Before: length ranges with CHECK. After: NOT NULL and VARCHAR maximum lengths only. The Schema does not enforce a minimum length (OD-3).
- Req 1.8 (new). After: no `role` column on `users` (DB-SCH-01).
- Req 2.1 (boards). Before: `owner_id` (RESTRICT), `name` 1 to 255, `deleted_at`. After: `name` VARCHAR(100), `is_public` BOOLEAN NOT NULL default true, `created_by` SET NULL, no `owner_id`, no `deleted_at`.
- Req 2.2 (board_members). Before: no `added_by`. After: `added_by` SET NULL, `created_at` only.
- Req 2.3 (membership key). Before: unique pair (`board_id`, `user_id`). After: composite primary key `pk_board_members`.
- Req 2.9 (board name). Before: 1 to 255 characters. After: up to 100 characters.
- Req 2.10 to 2.14 (new). Before: none. After: default `is_public` true (DB-VIS-01); boards hard-deleted (DB-CNV-05); Guest has no stored value (DB-MEM-01); last-admin lock in the backend service (DB-MEM-02).
- Req 3.1 (columns). Before: `title`, `order` column, `deleted_at`. After: `name` VARCHAR(100), `position` (exposed as `order`), `is_done`, `created_by` SET NULL, `UNIQUE (id, board_id)`, no `deleted_at`.
- Req 3.3 (column position). Before: CHECK `order > 0`. After: CHECK `position > 0`, constraint `ck_columns_position`.
- Req 3.5 (column name). Before: `title` 1 to 255 characters. After: `name`, up to 100 characters.
- Req 3.6 (column defaults). Before: `deleted_at` NULL on insert. After: no `deleted_at`; `created_at` and `updated_at` set to the UTC time.
- Req 3.7 and 3.8 (new). After: one Done_Column per board through `uq_columns_board_id_done` (DB-DON-01); `is_done` default false.
- Req 3.9 (new). After: column hard delete cascades to cards and their comments.
- Req 4.1 (cards). Before: no `board_id`; `title` 1 to 255; `description` up to 10,000; `created_by` NOT NULL. After: `board_id` NOT NULL, `title` VARCHAR(200), `description` up to 5,000, `due_date` DATE, `created_by` nullable with SET NULL.
- Req 4.2 and 4.3 (card position). Before: column `order`, CHECK `order > 0`. After: column `position`, exposed as `order`, CHECK `ck_cards_position`.
- Req 4.9 (card foreign keys). Before: `created_by` NOT NULL and enforced. After: `created_by` nullable (SET NULL). The composite FK on `(column_id, board_id)` is added in criterion 10.
- Req 4.10 to 4.14 (new). After: cross-board move rejected by composite FK (DB-SCH-03); `due_date` DATE; title and description limits; `Card.active()` helper (DB-SOFT-02).
- Req 5.1 (comments). Before: `body`, `user_id` (RESTRICT), `deleted_at`. After: `content` TEXT, `created_by` SET NULL, no `deleted_at`.
- Req 5.3 (comment owner). Before: `user_id`. After: `created_by`, set at insert only (DB-OWN-02).
- Req 5.4 (comment delete). Before: soft delete with `deleted_at`. After: hard delete (DB-CNV-05).
- Req 5.5 (comment content). Before: non-whitespace content, up to 5,000 characters. After: `content` length 1 to 2,000, check `ck_comments_content_length`. Whitespace-only content is accepted by the Schema and rejected by the backend.
- Req 6.1 (notifications). Before: `card_id` FK, `board_id` FK, `type` up to 50 characters. After: no `card_id`; `board_id` UUID with no foreign key (DB-NTF-01); `type` VARCHAR(30) with check `ck_notifications_type` (placeholder list, OD-1); `message` VARCHAR(500).
- Req 6.3 (notification index). Before: index on (`user_id`, `created_at`). After: `ix_notifications_user_id_created_at` on (`user_id`, `created_at` DESC) and partial `ix_notifications_user_id_unread` (DB-NTF-02).
- Req 6.5 (notification foreign keys). Before: FK checks on `user_id`, `board_id` and `card_id`. After: FK check on `user_id` only.
- Req 6.7 (new). After: a board delete keeps its notifications and their text.
- Req 7.1 (activity). Before: `activity_logs` table with three foreign keys. After: no activity table. Breaking change.
- Req 7.2 (cards per column). Before: join through `columns`, filter on `columns.deleted_at`. After: filter on `cards.board_id` and `cards.deleted_at IS NULL`. No column delete state.
- Req 7.3 (completed this week). Before: join through `columns`. After: filter on `cards.board_id`, using `ix_cards_board_id_completed_at` (DB-DON-02).
- Req 7.4 (member activity). Before: count of `activity_logs` rows per user. After: three counts for each current member: cards created (`cards.created_by`), comments written on live cards (`comments.created_by`), cards assigned (`cards.assignee_id`). The three-count definition is open decision OD-6.
- Req 7.5 (assigned cards). Before: join through `columns` to `boards` with `boards.deleted_at`. After: join through `cards.board_id` to `boards`.
- Req 7.7 (new). After: soft-deleted cards are excluded from every query in criteria 2 to 6.
- Req 8.1 (foreign keys). Before: every reference is a foreign key. After: every reference except `notifications.board_id`.
- Req 8.3 (board delete). Before: removes `board_members`, `columns`, `activity_logs` and `notifications`. After: removes `board_members` and `columns` (and through them cards and comments). Keeps `notifications`.
- Req 8.4 (column delete). Before: removes cards. After: removes cards and their comments.
- Req 8.5 (card delete). Before: a card hard delete removes its comments. After: comments are removed when a cascade removes the card. A direct card delete is a soft delete.
- Req 8.7 (user delete). Before: RESTRICT rejects the delete with a foreign-key violation. After: `SET NULL` on the reference columns and CASCADE on memberships and notifications. The user delete never fails.
- Req 8.8 to 8.11 (new). After: cascades are a safety net, not a permission (DB-CAS-02); explicit `ondelete` and `passive_deletes` (DB-CAS-03); nullable `created_by`, `added_by` and `assignee_id` with SET NULL (DB-OWN-01); `created_by` set once (DB-OWN-02).
- Req 9.1 to 9.7 (indexes). Before: seven index criteria, including `activity_logs`, full (not partial) `completed_at` and `(column_id, order)`. After: superseded. Criterion 9.6 (`activity_logs` index) is removed.
- Req 9.10 to 9.24 (new). After: the twelve rows of DB-IDX-01 as thirteen indexes, plus non-unique position indexes (DB-ORD-02). No other non-key index.
- Req 10.7 to 10.9 (new). After: review of autogenerated migrations and immutable applied migrations (DB-MIG-01); `downgrade()` and CI sequence (DB-MIG-02); separate data migrations (DB-MIG-03).
- Req 12.1 (seed). Before: 2 users, 1 board, 3 columns, 5 cards. After: 3 users (Admin, Member, Guest-only), 2 boards (one private), 3 demo columns (Done is `is_done`) plus 1 sandbox column, 6 cards, 2 comments (DB-SEED-01).
- Req 12.2 (seed idempotence). Before: five tables compared. After: comments also compared.
- Req 12.5 and 12.6 (new). After: the seed refuses `FLASK_ENV=production` without `--force`; demo passwords only. Replaces the V3 Railway guard in the seed command.
- Req 13 (new). After: constraint and cascade tests against PostgreSQL 18 (DB-TST-01).
- Req 14 (new). After: conventions DB-CNV-01 to 05 and text limits DB-SCH-02.
- Req 11 and Req 10.1 to 10.6. Unchanged.
- Glossary. Added: Guest, Done_Column, Position (exposed as `order`), Notification_Type. Changed: Soft_Delete (cards only). Superseded: Order_Value (by Position). Removed: Activity_Log.
- Introduction. Before: reference to `/guidelines/database.md`. After: `.kiro/steering/database.md`.

Design (`design.md`, now V4):
- Decision table, Status column added. V3 decisions: D1 Active; D2 Amended (VARCHAR for most columns); D3 Superseded (no Infinity bound; column named `position`); D4 Amended (five tables); D5 and D6 Active; D7 Amended (VARCHAR(10)); D8 Superseded (soft delete on cards only, no `restore()`); D9 Superseded (SET NULL, not RESTRICT); D10 Amended (queries updated); D11 Active. New: D12 to D20.
- Schema and table definitions: DB-SCH-01 verbatim. ER diagram without `activity_logs`.
- Foreign keys: DB-CAS-01 exactly. RESTRICT no longer used.
- Mixins: `SoftDeleteMixin` on cards only; `restore()` and `is_deleted` removed.
- Models: `activity_log.py` removed. Changed: `user.py`, `board.py`, `column.py`, `card.py`, `comment.py`, `notification.py`, `__init__.py`.
- Index summary: replaced (13 indexes from DB-IDX-01, plus DB-ORD-02 and DB-DON-02 items).
- Triggers: same five tables. Unchanged.
- Migration strategy: new initial revision (D19, OD-7).
- Seed: data set and `FLASK_ENV` guard. Reference queries: all eight rewritten.
- Correctness properties: 26 kept or changed (2, 3, 4, 7, 8, 10, 11, 12, 17, 19, 26) and 3 new (27, 28, 29). Properties 1, 5, 6, 9, 13 to 16, 18, 20 to 25 are unchanged in statement.
- Traceability table rebuilt. Open decisions OD-1 to OD-10 added.

Reason
- The steering file `.kiro/steering/database.md` now defines the schema, constraints and rules by ID (DB-CNV, DB-SCH, DB-MEM, DB-VIS, DB-OWN, DB-CAS, DB-ORD, DB-DON, DB-SOFT, DB-NTF, DB-IDX, DB-MIG, DB-SEED, DB-TST). V3 diverged from it in column names and types, soft-delete scope, RESTRICT rules, the activity log, the index list and the seed. The user asked for V4 to match the steering file and to regenerate the database layer on a new branch.

Impact
- Requirements: 1.1, 1.7, 1.8 (new), 2.1, 2.2, 2.3, 2.9, 2.10 to 2.14 (new), 3.1, 3.3, 3.5, 3.6, 3.7 to 3.9 (new), 4.1, 4.2, 4.3, 4.9, 4.10 to 4.14 (new), 5.1, 5.3, 5.4, 5.5, 6.1, 6.3, 6.5, 6.7 (new), 7.1 to 7.7, 8.1, 8.3, 8.4, 8.5, 8.7, 8.8 to 8.11 (new), 9.1 to 9.7 (superseded), 9.10 to 9.24 (new), 10.7 to 10.9 (new), 12.1, 12.2, 12.5, 12.6 (new), 13 (new), 14 (new). Unchanged: 10.1 to 10.6, 11.1 to 11.7, 9.8, 9.9.
- Design: decision table (D1 to D20), schema, ER diagram, foreign keys, mixins, models, index summary, migration strategy, seed, reference queries, correctness properties 1 to 29, traceability, open decisions.
- Tasks: V3 tasks 1 to 12 kept and marked superseded. V4 section added (tasks 0 to 11), with a dependency graph. `tasks.meta.json` is not changed.
- Implementation: none in this revision. The V4 branch is not created yet. The V3 code in `backend/app/models` and `backend/migrations/versions/0001_initial_schema.py` is still on `main` and conflicts with V4 (see task 0.1).

### Backend impact

The backend spec (`.kiro/specs/backend/`) is not edited here. These backend requirements need a backend change request. Numbers come from the backend spec. Items marked (checked) were read in the backend file. Other items come from the V4 steering comparison.

- Req 1 (register and profile). Length limits: `name` 100 characters (V3 255) and `email` storage 255 characters. Email uniqueness on `lower(email)` is unchanged. There is no `role` column.
- Req 4 (boards). `name` limit 100 characters (was 255). New `is_public` field, default true (DB-VIS-01). The board's `created_by` becomes nullable.
- Req 5.5 (checked). Board delete sets `deleted_at` today. In V4 it is a hard delete, so the rule changes to delete the row. The 404 rule in Req 17.2 changes with it.
- Req 7 (columns). `title` maps to `columns.name`, limit 100 characters (was 255) (OD-5). Column delete is a hard delete (Req 7.4, checked). New `is_done` field: one Done_Column per board, a second one returns 409 from `uq_columns_board_id_done` (DB-DON-01). Req 7 is the owner of the `is_done` API rule.
- Req 9 (cards). `title` limit 200 characters (was 255). `description` limit 5,000 characters (was 10,000). `board_id` is set from the column on create and must match (DB-SCH-03). New `due_date` field. `created_by` is nullable (was RESTRICT). `assignee_id` is unchanged (SET NULL). The position route in Req 10 is not changed, but it must still reject NaN in the API because the Schema accepts it (OD-4).
- Req 12 (comments). Content limit 1 to 2,000 characters (was 5,000) (checked, Req 12.1 and 12.2). Whitespace-only rule stays in the backend. `user_id` becomes `created_by`. Delete is a hard delete (Req 12.5, checked), so the `deleted_at` rules and the "omit from list" rule change.
- Req 14.5 (checked). The one-activity-row-per-action rule is removed with the table. Req 6, 7, 9, 10 and 12 each have Activity_Action clauses that must be removed or redirected.
- Req 14.6 (checked). The rule that returns 500 when an Activity_Action write fails is removed with the table.
- Req 14.4 (checked). `card_id` is no longer set on Notifications. Req 13.2 (checked) shows `card_id` in the Notification response, and it must be removed.
- Req 15.5 (checked). `member_activity.actions` counted activity rows. The definition changes to the three counts in OD-6, and the response shape changes.
- Req 17.2 (checked). The 404 rule for a deleted Board or Column ancestor (`deleted_at`) no longer applies to boards and columns. Only card soft delete remains. Hard-deleted boards, columns and comments return 404 because they do not exist.
- Req 6 (member add, role change, remove). Member actions write Activity_Actions and `member_role_changed` (checked, Req 6.2 to 6.6). Those writes are removed. Any user delete path also changes: `created_by` and `assignee_id` become NULL, and no request fails with a foreign-key error (DB-CAS-01).

### Type of change
- Specification change: requirements, design and tasks (all V4 content).
- Design change: schema, foreign keys, indexes, models, seed and queries as listed above.
- Implementation change: none in this revision.
- Bug fixes: none. V3 had no bugs recorded.
- Breaking changes:
  - `activity_logs` table removed, with its model, index, foreign keys and the backend activity writes.
  - Column `order` renamed to `position` in `columns` and `cards`. The attribute `order` stays.
  - `columns.title` renamed to `columns.name` (API alias `title`).
  - `comments.body` renamed to `content`. `comments.user_id` renamed to `created_by`. Comment soft delete removed.
  - Soft delete limited to `cards`. `boards.deleted_at` and `columns.deleted_at` removed.
  - `RESTRICT` replaced by `SET NULL` for `created_by`, `added_by`, `assignee_id`. User delete no longer fails.
  - `notifications.card_id` removed. `notifications.board_id` has no foreign key.
  - Card description limit 5,000 characters (was 10,000), comment limit 2,000 characters (was 5,000).
  - Seed command refuses `FLASK_ENV=production` without `--force` (was a Railway check).

### Resolved open decisions (2026-11-21)
Each open decision in `design.md` (OD-1 to OD-10) is settled here, except OD-6. The V4 text above is kept as history. Where a resolution reverses it, the reversal is listed below.

Source key: **baseline** means the code at git tag `baseline-no-steering` (commit a31c87e). **steering** means `.kiro/steering/database.md`. **user** means the instruction given on 2026-11-21. **user pending** means no decision yet.

| OD | Topic | Source | Result |
|---|---|---|---|
| OD-1 | Notification_Type list | baseline | Resolved. Keep `card_assigned`, `card_moved`, `comment_added`, `member_added` in `ck_notifications_type`. BE-NTF-03 in `backend.md` is still to be written and must match this list. |
| OD-2 | Demo users | baseline; steering for Carol | Resolved. Keep Alice (Admin) and Bob (Member) from the baseline seed. Carol (Guest-only, no `board_members` row) stays because DB-SEED-01 requires a Guest-only user. Carol is steering-required, not a decision. |
| OD-3 | Minimum lengths | baseline | Resolved. Reverses the V4 draft choice of option (a). Minimum-length CHECKs are reinstated (see changed lines). The `password_hash` minimum is the user's addition. The baseline `user.py` has no check on `password_hash`. The email CHECK (3 to 254) is one character stricter than VARCHAR(255). The `boards.name` and `columns.name` minimums follow the same rule as `name` and `title` in the user's list. |
| OD-4 | NaN in `position` | baseline | Resolved. Reverses the V4 draft choice of option (a). The check is `"position" > 0 AND "position" < 'Infinity'` on `columns` and `cards`, named `ck_columns_position` and `ck_cards_position`. Reason: baseline behavior, rejects NaN and Infinity. Deviation from DB-ORD-01, which lists only `position > 0`. |
| OD-5 | API alias for column name | steering (column name); baseline (API field) | Resolved. The database column is `columns.name`. The API field stays `title` and maps to it. |
| OD-6 | Member activity definition | user pending; baseline cannot apply | **Open: needs user decision, baseline cannot apply.** The baseline counts `activity_logs` rows, and the steering removes that table, so the baseline definition cannot be followed. The V4 three-count definition (cards created, live comments written, cards assigned) stays as a draft until the user decides. |
| OD-7 | Initial migration | baseline; DB-MIG-01 | Resolved. Reverses the V4 draft, which planned a new `0001`. `0001_initial_schema` is applied in `revotask_db` and is not edited. The V4 change is `0002_v4_schema` on `main`. |
| OD-8 | Branch | user | Resolved. Reverses the V4 draft, which planned `database-v4`. No branch. All work is committed directly on `main`. |
| OD-9 | `created_by` immutability | baseline | Resolved. No trigger, as in the baseline. The backend enforces DB-OWN-02. |
| OD-10 | Private board contents | steering (one private board is required) | Resolved. The contents keep the V4 text: one admin, one column and one card. |

### Changed lines for these resolutions
Line numbers are from the files after this edit.

**requirements.md**
- Line 26, glossary Position: positive and finite (OD-4).
- Line 31, glossary Notification_Type: baseline list, OD-1 resolved (OD-1).
- Line 50, Req 1.7: minimum-length checks for `name`, `email` and `password_hash` (OD-3).
- Line 67, Req 2.9: `boards.name` minimum of 1 character (OD-3).
- Line 82, Req 3.3: `position` bound for NaN and infinity; deviation from DB-ORD-01 (OD-4).
- Line 84, Req 3.5: `columns.name` minimum of 1 character; API `title` alias (OD-3, OD-5).
- Line 98, Req 4.3: `position` bound for NaN and infinity; deviation from DB-ORD-01 (OD-4).
- Line 107, Req 4.12: `cards.title` minimum of 1 character (OD-3).
- Line 131, Req 6.1: Notification_Type list fixed to the baseline list (OD-1).
- Line 148, Req 7.4: OD-6 stays open (OD-6).
- Line 288, appendix row 1.7 (OD-3).
- Line 292, appendix row 2.9 (OD-3).
- Line 295, appendix row 3.3 (OD-4).
- Line 296, appendix row 3.5 (OD-3).
- Line 300, appendix row 4.3 (OD-4).

**design.md**
- Line 21, D3: `position` check with the Infinity bound. Status changed from Superseded to Amended (OD-4).
- Line 37, D19: `0002_v4_schema` on `main`. Replaces the V4 draft's `0001` on a branch (OD-7).
- Line 39, D21 (new): no branch (OD-8).
- Line 125, Migration strategy item 2: revision `0002_v4_schema` (OD-7).
- Line 131, Migration strategy item 2, new bullet: V3-to-V4 changes that `0002` makes (OD-7, with DB-MIG-03).
- Line 141, Migration strategy item 4: downgrade returns to `0001` (OD-7).
- Line 160, seed users row: baseline names and Carol (OD-2).
- Lines 360 and 374, ER diagram: `position` above zero and below Infinity (OD-4).
- Lines 471 to 473, User model checks `ck_users_name_length`, `ck_users_email_length`, `ck_users_password_hash_length` (OD-3).
- Line 496, Board model check `ck_boards_name_length` (OD-3).
- Lines 543 and 544, Column model checks `ck_columns_name_length` and `ck_columns_position` (OD-3, OD-4).
- Lines 577 and 578, Card model checks `ck_cards_position` and `ck_cards_title_length` (OD-4, OD-3).
- Line 597, title paragraph: maximum from VARCHAR(200), minimum from `ck_cards_title_length` (OD-3).
- Lines 660 to 662, users table rows (OD-3).
- Line 665, boards `name` row (OD-3).
- Lines 675 and 676, columns `name` and `position` rows (OD-3, OD-4).
- Line 683, cards `title` row (OD-3).
- Line 687, cards `position` row (OD-4).
- Line 725, trigger heading now refers to migration `0002` (OD-7).
- Line 751, Property 2: registry ranges with minimums (OD-3).
- Line 759, Property 4: `position` must be above zero and below Infinity (OD-4).
- Line 1041, Open Decisions intro: OD-6 is the only open item (OD-6 and all).
- Lines 1043 to 1052, OD-1 to OD-10: resolution and source under each item (all).
- Line 1058, Notes on V3 items: `title_length` replaced by a minimum-only check (OD-3).

**tasks.md** (V4 section only)
- Line 338, V4 overview: work on `main`, no branch (OD-8).
- Line 340, V4 overview: no branch (OD-8).
- Line 347, task 0.1: OD-7 resolved, `0001` applied (OD-7).
- Line 349, task 0.2: no branch (OD-8).
- Line 351, task 0.3: resolved list and OD-6 still open (all).
- Line 363, task 2.2: user checks (OD-3).
- Line 365, task 2.3: board name check (OD-3).
- Line 367, task 2.4: column checks (OD-3, OD-4).
- Line 369, task 2.5: card checks; the earlier "do not add a title_length check" is removed (OD-3, OD-4).
- Line 373, task 2.7: baseline list (OD-1).
- Line 383, task 3.2: revision `0002_v4_schema` on the applied `0001` (OD-7).
- Line 385, task 3.3: downgrade of `0002` (OD-7).
- Line 397, task 5.1: seed names (OD-2).
- Line 401, task 6.1: registry with minimum lengths (OD-3).
- Line 405, task 7.1: empty strings and NaN and Infinity tests (OD-3, OD-4).
- Line 411, task 7.4: OD-6 still open (OD-6).
- Line 443, task 11.2: OD-1 already resolved (OD-1).

### Reason
- The user asked to settle the open decisions. The resolution rule is: where the steering does not decide, follow the baseline. Where the steering decides, the steering wins. OD-8 is the user's own decision.

### Impact
- Requirements: 1.7, 2.9, 3.3, 3.5, 4.3, 4.12, 6.1, 7.4 and the appendix rows above.
- Design: D3, D19, D21, migration strategy, models, table rows, Properties 2 and 4, Open Decisions.
- Tasks: 0.1 to 0.3, 2.2 to 2.5, 2.7, 3.2, 3.3, 5.1, 6.1, 7.1, 7.4, 11.2. Task 7.4 cannot start until OD-6 is decided.
- Backend: no change to `.kiro/specs/backend/`. BE-NTF-03 is still to be written. The backend already rejects empty values with 422 (OD-3) and rejects NaN in position (OD-4). The backend `member_activity` change for OD-6 is still listed under V4 Impact.
- Deviations from steering: DB-ORD-01 for the position bound (OD-4). DB-SCH-01 defines maximum lengths only, so the minimum-length checks (OD-3) are added on top of it. The email CHECK (254) is one character stricter than the VARCHAR(255) type.
- Verification: `validate_spec_format` reported no format issues for `requirements.md`, `design.md` and `tasks.md`.

### Type of change
- Specification change: resolutions and the requirement and design text that records them.
- Design change: new CHECK constraints (minimum lengths, position bound), migration plan `0002_v4_schema`, and no branch.
- Implementation change: none.
- Bug fixes: none.
- Breaking changes: none added. The V3-to-V4 conversion in `0002` is the breaking change already listed above.