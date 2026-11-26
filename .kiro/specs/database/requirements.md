# Requirements Document

Version: V4

## Introduction

This spec covers the database layer of RevoTask, a Trello-like task manager. The layer uses PostgreSQL, SQLAlchemy models and Flask-Migrate migrations. It stores users, boards, board memberships with roles, columns, cards, comments and notifications. It also provides the data needed for per-board analytics, card search and the "assigned to me" view.

The source of truth for tables, columns, types, lengths, constraints, indexes, foreign keys, cascades, migrations and seed data is `.kiro/steering/database.md`, cited below by rule ID (for example DB-CAS-01). Where this spec and that steering file disagree, the steering file wins. V4 aligns this spec with the steering file. Earlier versions are kept in `history/requirements-V3.md` and the superseded items are listed in the appendix at the end of this document.

Routes, request validation, permissions and UI are out of scope. They belong to the backend spec (`.kiro/specs/backend/`) and the frontend spec. The backend rules that V4 affects are listed in `CHANGELOG.md`, V4 Impact. This spec does not edit the backend spec.

## Glossary

- **Database**: The PostgreSQL database that stores all RevoTask data.
- **Schema**: The set of tables, columns, constraints and indexes defined by the SQLAlchemy models and migrations.
- **Migration_System**: Flask-Migrate (Alembic), applied with `flask db upgrade`.
- **User**: A registered person who signs in to RevoTask.
- **Guest**: A User with no `board_members` row for a given Board. The Schema never stores a value for this state (DB-MEM-01).
- **Board**: A workspace that contains columns and cards. A Board has a public or private visibility flag.
- **Board_Member**: A User's membership of a Board, stored with a Role.
- **Role**: Either `member` or `admin`, stored on a Board_Member.
- **Column**: An ordered list of cards inside a Board. The name is stored in `columns.name`.
- **Done_Column**: The one Column of a Board whose `is_done` is true. A Board has at most one Done_Column (DB-DON-01).
- **Card**: A task inside a Column.
- **Position**: The positive, finite double-precision value that sets the order of a Column within a Board or of a Card within a Column. It is stored in the database column `position` and exposed in the models and the API as `order` (DB-ORD-01, with the bound on `NaN` and infinity from OD-4).
- **Soft_Delete**: Setting `cards.deleted_at` to a UTC timestamp so that the Card row stays in the table. Cards are the only soft-deleted records. Boards, columns, comments and all other rows are hard-deleted (DB-CNV-05).
- **Completed_Card**: A Card whose `completed_at` timestamp is not null.
- **Comment**: A text note written by a User on a Card.
- **Notification**: A message addressed to one User, with a read or unread state.
- **Notification_Type**: One value of the notification type list. The list is defined by `backend.md` BE-NTF-03. V4 uses the baseline list, which is resolved as OD-1 (see Requirement 6, criterion 1 and the resolved open decisions in `design.md`).
- **Seed_Command**: The command that loads demo data into the Database.
- **Order_Value**: The V3 term for a positive float that sets order. Superseded in V4 by Position. Kept here so that V3 criteria remain readable.
- **Activity_Log**: The V3 table of user actions. Removed in V4 (see Requirement 7 and the appendix).

## Requirements

### Requirement 1: Users and password storage

**User Story:** As a user, I want my account stored securely, so that I can register and log in.

#### Acceptance Criteria

1. THE Schema SHALL define a `users` table with a UUID primary key `id`, `name` (VARCHAR(100), NOT NULL), `email` (VARCHAR(255), NOT NULL), `password_hash` (VARCHAR(255), NOT NULL), `created_at` (TIMESTAMPTZ, NOT NULL) and `updated_at` (TIMESTAMPTZ, NOT NULL). (DB-SCH-01, DB-CNV-03, DB-CNV-04. V3 criterion 1.1 is superseded for the column types and lengths. See appendix.)
2. THE Schema SHALL enforce a unique index `uq_users_email_lower` on `lower(email)`, so that `A@x.com` and `a@x.com` are treated as duplicates. (DB-IDX-01)
3. THE Schema SHALL store only a salted hash of the password in `password_hash` and SHALL NOT define a plaintext password column.
4. IF an insert or update would duplicate an existing `lower(users.email)`, THEN THE Database SHALL reject the statement with a unique-violation error and SHALL leave the existing `users` rows unchanged.
5. WHEN a row is inserted into `users` without values for `id`, `created_at` or `updated_at`, THE Database SHALL generate a UUID for `id` and set `created_at` and `updated_at` to the current database time.
6. WHEN a row in `users` is updated, THE Database SHALL set `updated_at` to the current database time and SHALL leave `created_at` unchanged.
7. IF an insert or update sets `name`, `email` or `password_hash` to NULL, sets `name` or `password_hash` to an empty string, sets `name` to a value longer than 100 characters, sets `email` to a value shorter than 3 or longer than 254 characters, or sets `password_hash` to a value longer than 255 characters, THEN THE Database SHALL reject the statement with a constraint-violation error and SHALL leave the existing `users` rows unchanged. The minimums are the checks `ck_users_name_length`, `ck_users_email_length` and `ck_users_password_hash_length`. The email check is one character stricter than the VARCHAR(255) type. (Replaces the V3 length ranges. The minimums are reinstated from the baseline, OD-3. See appendix.)
8. THE Schema SHALL NOT define a `role` column on `users`. Roles exist only on `board_members`. (DB-SCH-01)

### Requirement 2: Boards and membership roles

**User Story:** As a board administrator, I want each board to record its members and their roles, so that I can manage access.

#### Acceptance Criteria

1. THE Schema SHALL define a `boards` table with a UUID primary key `id`, a `name` (VARCHAR(100), NOT NULL), `is_public` (BOOLEAN, NOT NULL), `created_by` (UUID, nullable, referencing `users`), `created_at` (TIMESTAMPTZ, NOT NULL) and `updated_at` (TIMESTAMPTZ, NOT NULL). The Schema SHALL NOT define `owner_id` or `deleted_at` on `boards`. (DB-SCH-01, DB-CNV-05. V3 criterion 2.1 is superseded. See appendix.)
2. THE Schema SHALL define a `board_members` table with a non-null `board_id` referencing `boards`, a non-null `user_id` referencing `users`, a non-null `role` (VARCHAR(10)), a nullable `added_by` referencing `users`, and a non-null `created_at`. The table SHALL NOT have `updated_at` or `deleted_at`. (DB-SCH-01, DB-CNV-04)
3. THE Schema SHALL make (`board_id`, `user_id`) the composite primary key of `board_members`, so that a User has at most one membership row per Board. (DB-MEM-01)
4. THE Schema SHALL restrict `board_members.role` to the values `member` and `admin` by the check constraint `ck_board_members_role`. (DB-MEM-01)
5. WHEN a Board is created, THE Schema SHALL allow a Board_Member row with role `admin` to be stored for the creating User, in the same transaction as the Board row. (Board creation is written by the backend. The Schema allows the rows.)
6. WHEN a User is removed from a Board, THE Database SHALL delete only that User's Board_Member row for that Board and SHALL retain every Card and Comment that User created on that Board, with `created_by` values unchanged.
7. IF an insert or update on `board_members` has a `role` other than `member` or `admin`, THEN THE Database SHALL reject the statement with a check-constraint violation and leave existing rows unchanged.
8. IF an insert on `board_members` repeats an existing (`board_id`, `user_id`) pair, THEN THE Database SHALL reject the statement with a unique-constraint violation (`pk_board_members`) and leave the existing row unchanged.
9. IF an insert or update on `boards` sets `name` to NULL, to an empty string, or to a value longer than 100 characters, THEN THE Database SHALL reject the statement with a constraint-violation error and store no row. The minimum is the check `ck_boards_name_length` (OD-3, reinstated from the baseline). (Replaces the V3 255-character limit. See appendix.)
10. WHEN a row is inserted into `boards` without a value for `is_public`, THE Schema SHALL store `is_public` as true, using a database-level default as well as the model default. (DB-VIS-01)
11. THE Schema SHALL support public board listing with the partial index defined in Requirement 9, criterion 3. (DB-VIS-01, DB-IDX-01)
12. WHEN a Board is deleted, THE Database SHALL hard-delete the `boards` row. The Schema SHALL NOT keep a soft-deleted Board. (DB-CNV-05, DB-CAS-01)
13. WHILE a Board has no `board_members` row for a User, THE Schema SHALL treat that User as a Guest of the Board and SHALL NOT store a `guest` value. (DB-MEM-01)
14. WHEN a Board_Admin demotes or removes an Admin, THE service that performs the change SHALL lock the board's admin rows with `SELECT ... FOR UPDATE` on `board_members` where `board_id` matches and `role` is `admin`, and SHALL count and change them in the same transaction. The Schema cannot express the rule "at least one Admin" as a constraint. (DB-MEM-02. Enforced by the backend service. Verified by a concurrency test in the backend spec.)

### Requirement 3: Columns with positions and one done column

**User Story:** As a board member, I want columns to keep a stable order and one done column, so that I can reorder work and measure completion.

#### Acceptance Criteria

1. THE Schema SHALL define a `columns` table with a UUID primary key `id`, a non-null `board_id` referencing `boards`, a non-null `name` (VARCHAR(100)), a non-null `position` (DOUBLE PRECISION), a non-null `is_done` (BOOLEAN, default false), a nullable `created_by` referencing `users`, a non-null `created_at` and `updated_at`, and a unique constraint on (`id`, `board_id`). The table SHALL NOT have `deleted_at`. (DB-SCH-01, DB-CNV-05. Replaces V3 criterion 3.1.)
2. THE Schema SHALL require `columns.board_id`, `columns.name`, `columns.position` and `columns.is_done` to be non-null. (DB-SCH-01)
3. IF a Column is stored with a `position` less than or equal to zero, NaN, or positive infinity, THEN THE Database SHALL reject the statement with a check-constraint violation (`ck_columns_position`, `"position" > 0 AND "position" < 'Infinity'`) and SHALL leave the existing rows unchanged. (DB-ORD-01, with the NaN and infinity bound from OD-4. This is a deviation from DB-ORD-01, which lists only `position > 0`. The bound follows the baseline.)
4. IF a Column is stored with a `board_id` that does not match an existing row in `boards`, THEN THE Database SHALL reject the statement with a foreign-key violation and SHALL leave the existing rows unchanged.
5. IF a Column is stored with a `name` that is NULL, empty, or longer than 100 characters, THEN THE Database SHALL reject the statement with a constraint-violation error and SHALL leave the existing rows unchanged. The minimum is the check `ck_columns_name_length` (OD-3, reinstated from the baseline). The API field stays `title` and maps to `columns.name` (OD-5). (Replaces V3 criterion 3.5, which used `title` and 255 characters. See appendix.)
6. WHEN a Column is inserted without explicit `created_at` and `updated_at` values, THE Schema SHALL set both to the current UTC time.
7. IF a Column with `is_done` true is inserted or updated on a Board that already has a Done_Column, THEN THE Database SHALL reject the statement with a unique-violation error naming `uq_columns_board_id_done` and SHALL leave the existing rows unchanged. (DB-DON-01)
8. THE Schema SHALL store `is_done` as false by default, so that a Column without an explicit value is not a Done_Column. (DB-SCH-01)
9. WHEN a Column is deleted, THE Database SHALL hard-delete the `columns` row and cascade to its cards and their comments (Requirement 8, criterion 4). (DB-CNV-05, DB-CAS-01)

### Requirement 4: Cards

**User Story:** As a board member, I want cards that can be soft-deleted, moved, assigned and dated, so that I can manage tasks without losing history.

#### Acceptance Criteria

1. THE Schema SHALL define a `cards` table with a UUID primary key `id`, a non-null `board_id`, a non-null `column_id`, a non-null `title` (VARCHAR(200)), a nullable `description` (TEXT), a nullable `assignee_id` referencing `users`, a nullable `due_date` (DATE), a non-null `position` (DOUBLE PRECISION), a nullable `completed_at` (TIMESTAMPTZ), a nullable `deleted_at` (TIMESTAMPTZ), a nullable `created_by` referencing `users`, and non-null `created_at` and `updated_at`. (DB-SCH-01. Replaces V3 criterion 4.1, which had `order`, no `board_id`, no `due_date` and a 10,000-character description limit.)
2. THE Schema SHALL store the Card Position in the column `position` and SHALL expose it in the models and the API as `order`. (DB-ORD-01. Replaces V3 criterion 4.2, which stored `order` as the column name.)
3. IF a Card is stored with a `position` less than or equal to zero, NaN, or positive infinity, THEN THE Database SHALL reject the statement with a check-constraint violation (`ck_cards_position`, `"position" > 0 AND "position" < 'Infinity'`) and SHALL leave the existing row data unchanged. (DB-ORD-01, with the NaN and infinity bound from OD-4. This is a deviation from DB-ORD-01. The bound follows the baseline.)
4. WHEN a Card row is updated, THE Schema SHALL set `updated_at` to the current UTC time, and the new `updated_at` value SHALL be greater than or equal to the previous `updated_at` value.
5. WHEN a Card is soft-deleted, THE Schema SHALL record the deletion time as a UTC timestamp in `deleted_at`, SHALL keep the row and all its other column values unchanged except `deleted_at` and `updated_at`, and SHALL keep its `column_id`, `board_id` and `position`. (DB-SOFT-01)
6. THE Schema SHALL allow `assignee_id` to be null, so that a Card can be unassigned.
7. WHEN a User account is removed, THE Database SHALL set `cards.assignee_id` to null for all Cards assigned to that User and SHALL keep those Card rows, including soft-deleted ones. (DB-CAS-01)
8. WHEN a Card is marked complete, THE Schema SHALL store the completion time as a UTC timestamp in `completed_at`. WHILE a Card is not in the Done_Column, THE Schema SHALL hold `completed_at` as null. The Schema cannot check the second statement against another table, so the backend service maintains it. (DB-DON-01)
9. IF a Card is stored with a non-null `column_id`, `assignee_id` or `created_by` that does not match an existing row in the referenced table, THEN THE Database SHALL reject the statement with a foreign-key violation and SHALL leave the existing row data unchanged. (`created_by` is now nullable. See criterion 10 and Requirement 8, criterion 10.)
10. IF a Card is inserted, or its `column_id` is updated, with a `board_id` that does not equal the `board_id` of the referenced Column, THEN THE Database SHALL reject the statement with a foreign-key violation on the composite foreign key (`column_id`, `board_id`) referencing `columns` (`id`, `board_id`), and SHALL leave the existing row data unchanged. (DB-SCH-03. New in V4.)
11. THE Schema SHALL allow `due_date` to be null, and SHALL store a value as a calendar `DATE` without a time zone. (DB-SCH-01. New in V4.)
12. IF a Card is stored with a `title` that is NULL, empty, or longer than 200 characters, THEN THE Database SHALL reject the statement with a constraint-violation error and SHALL leave the existing row data unchanged. The maximum comes from VARCHAR(200). The minimum is the check `ck_cards_title_length` (OD-3, reinstated from the baseline). (DB-SCH-01, DB-SCH-02. New in V4.)
13. IF a Card is stored with a `description` longer than 5,000 characters, THEN THE Database SHALL reject the statement with a check-constraint violation (`ck_cards_description_length`) and SHALL leave the existing row data unchanged. (DB-SCH-02. Replaces the 10,000-character limit in V3 criterion 4.1.)
14. THE Card model SHALL provide a class-level helper `Card.active()` that applies `deleted_at IS NULL`, and every backend query that reads cards SHALL use it. (DB-SOFT-02. New in V4.)

### Requirement 5: Comments

**User Story:** As a board member, I want to comment on cards, so that I can discuss tasks with other members.

#### Acceptance Criteria

1. THE Schema SHALL define a `comments` table with a UUID primary key `id`, a non-null `card_id` referencing `cards`, a non-null `content` (TEXT), a nullable `created_by` referencing `users`, and non-null `created_at` and `updated_at`. The table SHALL NOT have `deleted_at`. (DB-SCH-01, DB-CNV-05. Replaces V3 criterion 5.1, which had `body`, `user_id` and `deleted_at`.)
2. THE Schema SHALL require `comments.content`, `comments.card_id`, `comments.created_at` and `comments.updated_at` to be non-null, and SHALL allow `comments.created_by` to be null. (DB-SCH-01)
3. THE Schema SHALL store `comments.created_by` so that the author of each Comment can be identified, and SHALL set it at insert time only. (DB-OWN-01, DB-OWN-02. Replaces the V3 `user_id` column.)
4. WHEN a Comment is deleted, THE Database SHALL remove its row. The Schema SHALL NOT keep a soft-deleted Comment. (DB-CNV-05. Replaces V3 criterion 5.4, which soft-deleted comments.)
5. IF an insert or update sets `comments.content` to NULL, to an empty string, or to a value longer than 2,000 characters, THEN THE Database SHALL reject the statement with a check-constraint violation (`ck_comments_content_length`) and SHALL leave existing rows unchanged. The Schema accepts a whitespace-only value that has one or more characters. Rejecting whitespace-only content is a backend rule. (DB-SCH-01, DB-SCH-02. Replaces V3 criterion 5.5, which rejected whitespace and allowed 5,000 characters.)
6. IF an insert or update sets `comments.card_id` to a value that does not match an existing row in `cards`, or sets a non-null `comments.created_by` to a value that does not match an existing row in `users`, THEN THE Schema SHALL reject the operation with a foreign-key violation and SHALL leave existing rows unchanged.
7. WHEN a Comment row is updated, THE Schema SHALL set `comments.updated_at` to the time of the update, and `comments.updated_at` SHALL be greater than or equal to `comments.created_at`.

### Requirement 6: Notifications

**User Story:** As a user, I want notifications stored per user, so that I can page through them and mark them as read.

#### Acceptance Criteria

1. THE Schema SHALL define a `notifications` table with a UUID primary key `id`, a non-null `user_id` referencing `users`, a non-null `type` (VARCHAR(30)) with a check constraint `ck_notifications_type` that accepts only Notification_Type values, a non-null `message` (VARCHAR(500)), a nullable `board_id` (UUID) with no foreign key, a non-null `is_read` (BOOLEAN, default false) and a non-null `created_at` (TIMESTAMPTZ). The table SHALL NOT have `card_id`, `updated_at` or `deleted_at`. (DB-SCH-01, DB-NTF-01, DB-CNV-04. Replaces V3 criterion 6.1, which had `card_id`, a foreign key on `board_id` and a 50-character `type`.) The Notification_Type list is the baseline list: `card_assigned`, `card_moved`, `comment_added` and `member_added` (OD-1, resolved). `backend.md` BE-NTF-03 is not yet written and must match this list.
2. THE Schema SHALL require `notifications.user_id`, `notifications.type`, `notifications.message`, `notifications.is_read` and `notifications.created_at` to be non-null, SHALL limit `type` to 30 characters and `message` to 500 characters, and SHALL allow `board_id` to be null. (DB-SCH-01)
3. WHEN a query selects the Notifications of one User ordered by `created_at` descending with an offset (0 to 1,000,000) and a limit (1 to 100), THE Database SHALL return only that User's rows, at most the limit count, starting after the offset, using the index `ix_notifications_user_id_created_at` on (`user_id`, `created_at` DESC). (DB-NTF-02, DB-IDX-01)
4. WHEN `is_read` is set to true for a Notification, THE Database SHALL keep the row and leave every other column value unchanged.
5. IF an insert or update of a Notification sets `user_id` to a value that does not match an existing row in `users`, or violates a non-null constraint, the length limits in criterion 2, or the Notification_Type check, THEN THE Database SHALL reject the statement with a constraint violation error and leave the table unchanged. The Schema does not check `board_id` against `boards`. (DB-NTF-01. Replaces the V3 foreign-key checks on `board_id` and `card_id`.)
6. WHEN a query selects Notifications for a User who has no Notifications, THE Database SHALL return zero rows without error.
7. WHEN a Board is hard-deleted, THE Database SHALL keep every Notification whose `board_id` equals the deleted Board's id, and SHALL NOT change the Notification text or `board_id`. (DB-NTF-01. New in V4.)

### Requirement 7: Analytics support

**User Story:** As a board administrator, I want completion and member activity data, so that I can see board analytics.

#### Acceptance Criteria

1. THE Schema SHALL NOT define an `activity_logs` table or any other action-log table. Analytics are computed from `cards`, `comments` and `board_members`. (Removed in V4. This is a breaking change. See the appendix and the CHANGELOG.)
2. WHEN the total number of Cards per Column for a Board is requested, THE Schema SHALL allow one count per Column to be computed with a join of `cards` to `columns` filtered by `cards.board_id` and `cards.deleted_at IS NULL`, and a Column with zero live Cards SHALL be returned with a count of 0. (DB-SOFT-02. Replaces V3 criterion 7.2, which also filtered `columns.deleted_at`.)
3. WHEN the Cards completed in the current week for a Board are requested, THE Schema SHALL allow the count to be computed from `cards.completed_at`, filtered by `cards.board_id`, `cards.deleted_at IS NULL`, and `cards.completed_at` falling between 00:00:00 Monday (UTC) of the current week (inclusive) and 00:00:00 Monday (UTC) of the next week (exclusive). The query SHALL use the partial index in Requirement 9, criterion 18. (DB-DON-02. Replaces V3 criterion 7.3, which joined through `columns`.)
4. WHEN member activity for a Board is requested, THE Schema SHALL allow one row per current Board_Member to be computed with three counts: live Cards created by that User (`cards.created_by`), Comments written by that User on live Cards of the Board (`comments.created_by`), and live Cards assigned to that User (`cards.assignee_id`). A count with no matching rows SHALL be 0. (Replaces V3 criterion 7.4, which counted `activity_logs` rows. The three-count definition is V4 decision OD-6, which is still open. The baseline counts `activity_logs` rows, and that table is removed, so the baseline definition cannot apply. See `design.md`.)
5. WHEN the Cards assigned to a User are requested, THE Schema SHALL allow the Cards to be selected by `assignee_id` joined to `boards` through `cards.board_id` with `cards.deleted_at IS NULL`, so that results can be grouped by `boards.name`. (Replaces V3 criterion 7.5, which joined through `columns`.)
6. WHEN Cards are searched by text, THE Schema SHALL allow a case-insensitive substring match of the search term (1 to 200 characters) against `cards.title` and `cards.description`, excluding Cards where `cards.deleted_at IS NOT NULL`. A Card SHALL match if either field contains the term.
7. WHEN a Card is soft-deleted, THE queries in criteria 2 to 6 SHALL exclude that Card. (DB-SOFT-02. New in V4.)

### Requirement 8: Referential integrity (non-functional)

**User Story:** As a developer, I want the database to enforce relationships and deletes, so that stored data stays consistent.

#### Acceptance Criteria

1. THE Schema SHALL declare every column that references another table's row as a foreign key constraint, except `notifications.board_id`, which has no foreign key by design (DB-NTF-01).
2. IF a statement inserts or updates a row with a non-null foreign key value that does not match an existing parent row, THEN THE Database SHALL reject the statement with a foreign-key-violation error, persist no part of the statement, and leave all existing rows unchanged.
3. WHEN a Board is hard-deleted, THE Database SHALL delete all of its `board_members` and `columns` rows, and through the cascade all of its `cards` and their `comments`, within the same transaction. Notifications with that `board_id` are kept (Requirement 6, criterion 7). (DB-CAS-01. Replaces V3 criterion 8.3, which also deleted `activity_logs` and `notifications`.)
4. WHEN a Column is hard-deleted, THE Database SHALL delete all Cards belonging to that Column and all Comments of those Cards within the same transaction, leaving zero Cards that reference the deleted Column's id. (DB-CAS-01. Replaces V3 criterion 8.4, which did not mention comments.)
5. WHEN a Card row is removed by a cascade from its Column or Board, THE Database SHALL delete all Comments belonging to that Card within the same transaction. A direct Card delete is a Soft_Delete and is not a cascade (Requirement 4, criterion 5). (DB-CAS-01, DB-SOFT-01. Replaces V3 criterion 8.5.)
6. THE Schema SHALL define a UUID primary key on every table except `board_members`, which SHALL use the composite primary key (`board_id`, `user_id`). (DB-CNV-03)
7. WHEN a User is hard-deleted, THE Database SHALL set `created_by`, `added_by` and `assignee_id` to null on the rows that reference that User, delete that User's `board_members` and `notifications` rows, and SHALL NOT reject the delete. (DB-CAS-01, DB-OWN-01. Replaces V3 criterion 8.7, which rejected the delete with RESTRICT.)
8. THE Database cascades SHALL act as a safety net only. They SHALL NOT decide who may delete. The backend checks permissions before a delete reaches the Database (BE-AZ-04). (DB-CAS-02. New in V4.)
9. THE Schema SHALL declare every foreign key with an explicit `ondelete` value that matches the table in DB-CAS-01. The ORM relationships of parents with a database cascade SHALL set `passive_deletes=True` and `cascade="all, delete-orphan"`. (DB-CAS-03. New in V4.)
10. THE Schema SHALL define `created_by`, `added_by` and `assignee_id` as nullable references to `users` with `ON DELETE SET NULL`, and SHALL NOT make them NOT NULL or give them `ON DELETE CASCADE`. (DB-OWN-01. New in V4.)
11. THE Schema SHALL set `created_by` at insert time from the authenticated User and SHALL NOT expose it as a writable field in any API schema. The Database has no trigger for this rule. The backend enforces it (DB-OWN-02). (New in V4.)

### Requirement 9: Indexing and query performance (non-functional)

**User Story:** As a user, I want boards and cards to load fast, so that the application feels responsive.

Criteria 1 to 7 of V3 are superseded by criteria 10 to 22 below. Criteria 8 and 9 are unchanged. The IDs of the retained criteria do not change. (See appendix.)

#### Acceptance Criteria

1. (Superseded in V4 by criterion 10.)
2. (Superseded in V4 by criterion 16.)
3. (Superseded in V4 by criterion 12.)
4. (Superseded in V4 by criterion 19.)
5. (Superseded in V4 by criterion 11.)
6. (Removed in V4. The `activity_logs` table is removed.)
7. (Superseded in V4 by criterion 18.)
8. WHEN a board containing up to 50 columns and 5,000 cards is loaded against a database seeded to that size, THE Schema SHALL allow the board, column, and card queries to each complete in 200 ms or less at the 95th percentile over 100 consecutive runs. (Unchanged from V3.)
9. IF a migration that creates the indexes in these criteria fails, THEN THE Schema SHALL roll back the whole migration, leave the existing tables and data unchanged, and report an error identifying the index that failed. (Unchanged from V3.)
10. THE Schema SHALL define the index `uq_users_email_lower` as a unique index on `lower(email)`. (DB-IDX-01, row `users`)
11. THE Schema SHALL define the index `ix_board_members_user_id` on `board_members` (`user_id`), so that retrieving all boards of one user is served by the index. (DB-IDX-01, row `board_members`)
12. THE Schema SHALL define the partial index `ix_boards_created_at_public` on `boards` (`created_at` DESC) WHERE `is_public`, so that public board listing is served by the index. (DB-IDX-01, DB-VIS-01)
13. THE Schema SHALL define the index `ix_columns_board_id_position` on `columns` (`board_id`, `position`), so that the columns of one board in position order are served by the index. (DB-IDX-01, DB-ORD-02)
14. THE Schema SHALL define the unique partial index `uq_columns_board_id_done` on `columns` (`board_id`) WHERE `is_done`. (DB-IDX-01, DB-DON-01)
15. THE Schema SHALL define the partial index `ix_cards_column_id_position` on `cards` (`column_id`, `position`) WHERE `deleted_at IS NULL`, so that the board view and position moves are served by the index. (DB-IDX-01, DB-ORD-02, DB-SOFT-02)
16. THE Schema SHALL define the partial index `ix_cards_assignee_id` on `cards` (`assignee_id`) WHERE `assignee_id IS NOT NULL AND deleted_at IS NULL`, so that the "assigned to me" query is served by the index. (DB-IDX-01)
17. THE Schema SHALL define the partial index `ix_cards_board_id_created_by` on `cards` (`board_id`, `created_by`) WHERE `deleted_at IS NULL`, so that the cards-created count in analytics is served by the index. (DB-IDX-01)
18. THE Schema SHALL define the partial index `ix_cards_board_id_completed_at` on `cards` (`board_id`, `completed_at`) WHERE `completed_at IS NOT NULL AND deleted_at IS NULL`, so that weekly completion is served by the index. (DB-IDX-01, DB-DON-02)
19. THE Schema SHALL define the index `ix_comments_card_id_created_at` on `comments` (`card_id`, `created_at`), so that the comments of one card are served by the index. (DB-IDX-01)
20. THE Schema SHALL define the index `ix_comments_created_by` on `comments` (`created_by`), so that the comments-added count in analytics is served by the index. (DB-IDX-01)
21. THE Schema SHALL define the index `ix_notifications_user_id_created_at` on `notifications` (`user_id`, `created_at` DESC), so that the paginated list is served by the index without a sort step. (DB-IDX-01, DB-NTF-02)
22. THE Schema SHALL define the partial index `ix_notifications_user_id_unread` on `notifications` (`user_id`) WHERE NOT `is_read`, for unread lookups and the unread count. (DB-IDX-01, DB-NTF-02)
23. THE Schema SHALL NOT define a UNIQUE constraint or a unique index on `position`, within a Column or across a Board. The position indexes in criteria 13 and 15 SHALL be non-unique. Position ties are resolved by the rebalance in `backend.md`. (DB-ORD-02)
24. THE Schema SHALL NOT define any index that is not listed in criteria 10 to 22, the primary keys and the unique constraints. Each index needs an endpoint that uses it (DB-IDX-01).

### Requirement 10: Migrations and reproducibility (non-functional)

**User Story:** As a developer, I want schema changes versioned, so that any environment can be built identically.

#### Acceptance Criteria

1. THE Migration_System SHALL hold every Schema change as a versioned migration file in the repository, with each migration file having a unique revision identifier and exactly one parent revision (except the initial revision, which has none), so that the revision history forms a single linear chain with one head.
2. WHEN `flask db upgrade` is run against an empty PostgreSQL database, THE Migration_System SHALL create every table, column, constraint, index and trigger defined by the models and steering, exit with status code 0, and record the latest revision identifier as the current revision.
3. WHEN `flask db upgrade` is run against a database already at the latest revision, THE Migration_System SHALL exit with status code 0, leave the Schema unchanged, and leave all existing rows unchanged.
4. WHEN `flask db downgrade` is run for the latest revision, THE Migration_System SHALL revert only that revision, exit with status code 0, and set the current revision to the immediately preceding revision, or to no revision if the latest revision is the initial one.
5. WHEN `flask db migrate` is run after the models match the latest revision, THE Migration_System SHALL detect zero Schema differences and generate no new migration file with operations.
6. IF a migration fails while `flask db upgrade` is running, THEN THE Migration_System SHALL exit with a non-zero status code, display an error message identifying the failed revision, and leave the database at the last successfully applied revision with no partial changes from the failed revision.
7. THE Migration_System SHALL review every autogenerated migration before it is committed, and SHALL correct the CHECK constraints, partial indexes, server defaults and triggers that autogeneration does not detect. An applied migration SHALL NOT be edited; a problem is fixed with a new migration. (DB-MIG-01. New in V4.)
8. THE Migration_System SHALL implement `downgrade()` for every revision, and CI SHALL run `flask db upgrade` on an empty database, then `flask db downgrade base`, then `flask db upgrade` again. (DB-MIG-02. New in V4.)
9. THE Migration_System SHALL keep schema changes and data changes in separate migrations, and a migration that changes data SHALL be safe on a table with existing rows (add nullable, backfill, then set NOT NULL). (DB-MIG-03. New in V4.)

### Requirement 11: PostgreSQL deployment and configuration (non-functional)

Unchanged from V3. Criteria 1 to 7 are carried over without change.

**User Story:** As a developer, I want the database to run on Railway PostgreSQL, so that the application can be deployed.

#### Acceptance Criteria

1. THE Database SHALL run on PostgreSQL.
2. THE Database configuration SHALL read its connection string from the `DATABASE_URL` environment variable and SHALL NOT contain credentials (username, password, host) in source code or committed files.
3. WHEN the application starts and `DATABASE_URL` begins with `postgres://`, THE Database configuration SHALL replace only the leading `postgres://` with `postgresql://` before creating the SQLAlchemy engine, leaving the rest of the string unchanged.
4. WHERE the application is deployed on Railway, THE Database configuration SHALL connect using SSL with `sslmode=require`.
5. IF `DATABASE_URL` is not set or is an empty string, THEN THE Database configuration SHALL raise an error whose message contains the text `DATABASE_URL`, SHALL NOT create a SQLAlchemy engine, and SHALL prevent the application from starting.
6. IF a connection attempt to PostgreSQL at startup is not established within 10 seconds, THEN THE Database configuration SHALL retry the attempt, bounding each attempt to 10 seconds, for up to 3 attempts in total.
7. IF all 3 connection attempts at startup fail, THEN THE Database configuration SHALL raise an error indicating the database is unreachable, SHALL NOT include the password from `DATABASE_URL` in the error message, and SHALL prevent the application from starting.

### Requirement 12: Seed data for development

**User Story:** As a developer, I want realistic demo data for every role, so that I can test the application locally.

#### Acceptance Criteria

1. WHEN the Seed_Command is run against an empty Database, THE Database SHALL contain three Users (one Admin, one Member and one Guest-only User with no `board_members` row), one public Board with three Columns at positions 1.0, 2.0 and 3.0 where the third is the Done_Column, five Cards distributed across those Columns, two Comments on Cards of the public Board, and one private Board (`is_public` false) with one Column and one Card. The Admin SHALL hold the `admin` role on both Boards, and the Member SHALL hold the `member` role on the public Board. (DB-SEED-01. Replaces V3 criterion 12.1, which had two Users, one Board and five Cards.)
2. WHEN the Seed_Command is run one or more additional times, THE Database SHALL contain the same rows and the same row counts for Users, Boards, Board memberships, Columns, Cards and Comments as after the first run, with no duplicate rows created. (DB-SEED-01. Extends V3 criterion 12.2.)
3. WHEN the Seed_Command completes successfully, THE Seed_Command SHALL exit with a success status and report that seeding finished.
4. IF the Seed_Command fails partway through, THEN THE Seed_Command SHALL roll back all changes made by that run, exit with a failure status, and report an error indicating the cause of the failure.
5. IF `FLASK_ENV` is `production` and the Seed_Command is run without `--force`, THEN THE Seed_Command SHALL exit with a failure status without changing any row. (DB-SEED-01. Replaces the V3 Railway check. Railway detection remains in Requirement 11 criterion 4.)
6. THE Seed_Command SHALL create passwords only from the documented demo value (`SEED_PASSWORD`, default `revotask-dev`). It SHALL NOT create real credentials. (DB-SEED-01)

### Requirement 13: Constraint and cascade tests against PostgreSQL (non-functional)

**User Story:** As a developer, I want the database rules tested without the application's own checks, so that the guarantees hold for raw SQL too.

#### Acceptance Criteria

1. THE Test_Suite SHALL run every database test against PostgreSQL 18 and SHALL NOT use SQLite or PostgreSQL 16. (`database-testing` steering)
2. THE Test_Suite SHALL assert that a second user whose email differs only by letter case is rejected with the error `uq_users_email_lower`. (DB-TST-01)
3. THE Test_Suite SHALL assert that a second Done_Column on one Board is rejected with the error `uq_columns_board_id_done`. (DB-TST-01, DB-DON-01)
4. THE Test_Suite SHALL assert that a Column or Card with `position <= 0` is rejected by `ck_columns_position` or `ck_cards_position`. (DB-TST-01, DB-ORD-01)
5. THE Test_Suite SHALL assert that a membership `role` other than `member` or `admin` is rejected by `ck_board_members_role`. (DB-TST-01)
6. THE Test_Suite SHALL assert that a Card moved to a Column of another Board is rejected by the composite foreign key. (DB-TST-01, DB-SCH-03)
7. THE Test_Suite SHALL assert that a second membership row for the same User and Board is rejected by `pk_board_members`. (DB-TST-01)
8. THE Test_Suite SHALL assert that hard-deleting a Board removes its memberships, columns, cards (including soft-deleted cards) and comments. (DB-TST-01, DB-CAS-01)
9. THE Test_Suite SHALL assert that hard-deleting a User sets `created_by` and `assignee_id` to NULL, keeps the affected rows, and does not fail. (DB-TST-01, DB-CAS-01)
10. THE Test_Suite SHALL assert that hard-deleting a Board leaves its notifications in place. (DB-TST-01, DB-NTF-01)
11. THE Test_Suite SHALL assert that soft-deleting a Card keeps its row with `deleted_at` set, and that `Card.active()` excludes it. (DB-TST-01, DB-SOFT-01, DB-SOFT-02)
12. THE Test_Suite SHALL assert that a Comment `content` of 0 characters or more than 2,000 characters is rejected by `ck_comments_content_length`, and that a 2,000-character content is accepted. (DB-TST-01, DB-SCH-02)

### Requirement 14: Conventions (non-functional)

**User Story:** As a developer, I want one set of naming, key and timestamp conventions, so that migrations and models stay consistent.

#### Acceptance Criteria

1. THE Schema SHALL use PostgreSQL in development, tests and production. Models SHALL live in `app/models/<entity>.py`, one model per file, exported from `app/models/__init__.py`, and SHALL subclass `db.Model`. Schema changes SHALL be made only through Flask-Migrate migrations, and `db.create_all()` SHALL NOT be called outside a throwaway test setup. (DB-CNV-01)
2. THE Schema SHALL name tables in plural snake_case, columns in snake_case, primary keys `id`, and foreign keys `<entity>_id`. The metadata SHALL use a naming convention so that every index, unique, check, foreign key and primary key constraint has a deterministic name with the prefix `ix_`, `uq_`, `ck_`, `fk_` or `pk_`. (DB-CNV-02)
3. THE Schema SHALL give every table except `board_members` a primary key `id` of type UUID with the default `gen_random_uuid()`, mapped as `UUID(as_uuid=True)`. (DB-CNV-03)
4. THE Schema SHALL give mutable tables (`users`, `boards`, `columns`, `cards`, `comments`) `created_at` and `updated_at` as TIMESTAMPTZ NOT NULL DEFAULT now(), and SHALL refresh `updated_at` on update. Append-only tables (`board_members`, `notifications`) SHALL have `created_at` only. All timestamps SHALL be stored in UTC. (DB-CNV-04)
5. THE Schema SHALL declare nullability explicitly for every column. NOT NULL is the default choice. Rows are hard-deleted, except cards, which are soft-deleted through `cards.deleted_at`. No other table SHALL have `deleted_at`, `is_deleted` or an archive column. (DB-CNV-05)
6. THE Schema SHALL take each text length limit from the table in Requirement 1 to 6 and SHALL NOT define a larger or separate limit. Text columns that have a limit but no VARCHAR length (`cards.description`, `comments.content`) SHALL carry a check constraint as a backstop. (DB-SCH-02)

## Appendix: Superseded and removed V3 criteria

V3 text is preserved verbatim in `history/requirements-V3.md`. This table lists each V3 criterion that V4 changes, replaces or removes. Criteria not listed here are unchanged from V3 or were reworded only for the column rename.

| V3 criterion | V4 status | V4 replacement |
|---|---|---|
| 1.1 | Modified | Req 1, criterion 1 (types and lengths from DB-SCH-01) |
| 1.7 | Modified | Req 1, criterion 7 (VARCHAR limits plus minimum-length checks, reinstated from baseline, OD-3) |
| 2.1 | Superseded | Req 2, criterion 1 (`created_by`, `is_public`, no `owner_id`, no `deleted_at`) |
| 2.2 | Modified | Req 2, criterion 2 (`added_by`, `created_at` only) |
| 2.3 | Modified | Req 2, criterion 3 (composite primary key) |
| 2.9 | Modified | Req 2, criterion 9 (name up to 100 characters, minimum 1 character, OD-3) |
| 3.1 | Superseded | Req 3, criterion 1 (`name`, `position`, `is_done`, `created_by`, UNIQUE (id, board_id), no `deleted_at`) |
| 3.2 | Modified | Req 3, criterion 2 |
| 3.3 | Modified | Req 3, criterion 3 (`ck_columns_position`, with the NaN and infinity bound, OD-4) |
| 3.5 | Superseded | Req 3, criterion 5 (`name`, 1 to 100 characters, OD-3) |
| 3.6 | Modified | Req 3, criterion 6 (`deleted_at` removed) |
| 4.1 | Superseded | Req 4, criterion 1 (`board_id`, `title` 200, `due_date`, `description` 5,000) |
| 4.2 | Modified | Req 4, criterion 2 (`position` column, `order` attribute) |
| 4.3 | Modified | Req 4, criterion 3 (`ck_cards_position`, with the NaN and infinity bound, OD-4) |
| 4.9 | Modified | Req 4, criterion 9 (`created_by` nullable) |
| 5.1 | Superseded | Req 5, criterion 1 (`content`, `created_by`, no `deleted_at`) |
| 5.2 | Modified | Req 5, criterion 2 |
| 5.3 | Modified | Req 5, criterion 3 (`created_by` replaces `user_id`) |
| 5.4 | Removed | Req 5, criterion 4 (comments are hard-deleted) |
| 5.5 | Superseded | Req 5, criterion 5 (`ck_comments_content_length`, 1 to 2,000 characters) |
| 5.6 | Modified | Req 5, criterion 6 |
| 6.1 | Superseded | Req 6, criterion 1 (no `card_id`, no FK on `board_id`, `type` VARCHAR(30) with check) |
| 6.2 | Modified | Req 6, criterion 2 |
| 6.3 | Modified | Req 6, criterion 3 (index `ix_notifications_user_id_created_at`) |
| 6.5 | Modified | Req 6, criterion 5 (no FK checks on `board_id` or `card_id`) |
| 7.1 | Removed | Req 7, criterion 1 (`activity_logs` table removed, breaking change) |
| 7.2 | Modified | Req 7, criterion 2 |
| 7.3 | Modified | Req 7, criterion 3 (`cards.board_id`, partial index) |
| 7.4 | Superseded | Req 7, criterion 4 (three counts from joins over `cards` and `comments`) |
| 7.5 | Modified | Req 7, criterion 5 |
| 7.6 | Modified | Req 7, criterion 6 (`Card.active()` semantics, criterion 7) |
| 7.7 | Removed | No replacement (no `activity_logs` foreign keys). Req 7, criterion 7 is new. |
| 8.1 | Modified | Req 8, criterion 1 (exception for `notifications.board_id`) |
| 8.3 | Modified | Req 8, criterion 3 (`activity_logs` and `notifications` no longer deleted) |
| 8.4 | Modified | Req 8, criterion 4 (comments of the cards are deleted too) |
| 8.5 | Modified | Req 8, criterion 5 (card removal by cascade only) |
| 8.7 | Superseded | Req 8, criterion 7 (`SET NULL` and `CASCADE`, no `RESTRICT`) |
| 9.1 | Superseded | Req 9, criterion 15 (partial `(column_id, position)`) |
| 9.2 | Superseded | Req 9, criterion 16 (partial, `assignee_id`) |
| 9.3 | Superseded | Req 9, criterion 13 (`columns` `(board_id, position)`) |
| 9.4 | Superseded | Req 9, criterion 19 (`(card_id, created_at)`) |
| 9.5 | Superseded | Req 9, criterion 11 (`board_members` `(user_id)`) |
| 9.6 | Removed | `activity_logs` index removed with the table |
| 9.7 | Superseded | Req 9, criterion 18 (partial `(board_id, completed_at)`) |
| 10.x | Extended | Req 10, criteria 7 to 9 added (DB-MIG-01 to 03). Criteria 1 to 6 unchanged. |
| 12.1 | Superseded | Req 12, criterion 1 (DB-SEED-01 data set) |
| 12.2 | Modified | Req 12, criterion 2 (adds comments to the compared tables) |
| Glossary `Activity_Log` | Removed | Not in the steering schema |
| Glossary `Order_Value` | Superseded | Glossary `Position` |
| Glossary `Soft_Delete` | Modified | Cards only |
| Introduction reference to `/guidelines/database.md` | Modified | `.kiro/steering/database.md` |

New in V4 with no V3 counterpart: Requirement 13 (constraint and cascade tests), Requirement 14 (conventions), Requirement 3 criteria 7 and 8, Requirement 4 criteria 10 to 14, Requirement 5 criterion 3 wording, Requirement 6 criterion 7, Requirement 7 criterion 7, Requirement 8 criteria 7 to 11, Requirement 9 criteria 10 to 24, Requirement 10 criteria 7 to 9, Requirement 12 criteria 5 and 6, and Requirement 2 criteria 10 to 14.
