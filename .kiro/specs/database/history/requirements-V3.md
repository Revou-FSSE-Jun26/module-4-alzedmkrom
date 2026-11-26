# Requirements Document

## Introduction

This spec covers the database layer of RevoTask, a Trello-like task manager. The layer uses PostgreSQL, SQLAlchemy models and Flask-Migrate migrations. It stores users, boards, board memberships with roles, columns, cards, comments and notifications. It also provides the data needed for per-board analytics, card search and the "assigned to me" view.

Routes, request validation and UI are out of scope. They belong to the backend and frontend specs. The database guidelines will be written later in `/guidelines/database.md`, and this spec and that file must stay consistent.

## Glossary

- **Database**: The PostgreSQL database that stores all RevoTask data.
- **Schema**: The set of tables, columns, constraints and indexes defined by the SQLAlchemy models.
- **Migration_System**: Flask-Migrate (Alembic), applied with `flask db upgrade`.
- **User**: A registered person who signs in to RevoTask.
- **Board**: A workspace that contains columns and cards.
- **Board_Member**: A User's membership of a Board, stored with a role.
- **Role**: Either `member` or `admin`, stored on a Board_Member.
- **Column**: An ordered list of cards inside a Board.
- **Card**: A task inside a Column.
- **Order_Value**: A positive floating-point number (`db.Float`) that sets the position of a Column within a Board or of a Card within a Column. It is stored in a column named `order` on both `columns` and `cards`.
- **Soft_Delete**: Marking a record as deleted by setting `deleted_at`, without removing the row.
- **Completed_Card**: A Card whose `completed_at` timestamp is not null.
- **Comment**: A text note written by a User on a Card.
- **Notification**: A message addressed to one User, with a read or unread state.
- **Activity_Log**: A record of an action a User performed on a Board, used for member activity analytics.
- **Seed_Command**: The command that loads sample development data into the Database.

## Requirements

### Requirement 1: Users and password storage

**User Story:** As a user, I want my account stored securely, so that I can register and log in.

#### Acceptance Criteria

1. THE Schema SHALL define a `users` table with a UUID primary key, `name` (text, 1 to 255 characters, NOT NULL), `email` (text, 3 to 254 characters, NOT NULL), `password_hash` (text, NOT NULL), `created_at` (timestamp with time zone, NOT NULL) and `updated_at` (timestamp with time zone, NOT NULL).
2. THE Schema SHALL enforce a unique constraint on `users.email` that compares values case-insensitively, so that `A@x.com` and `a@x.com` are treated as duplicates.
3. THE Schema SHALL store only a salted hash of the password in `password_hash` and SHALL NOT define a plaintext password column.
4. IF an insert or update would duplicate an existing `users.email`, THEN THE Database SHALL reject the statement with a unique-violation error and SHALL leave the existing `users` rows unchanged.
5. WHEN a row is inserted into `users` without values for `id`, `created_at` or `updated_at`, THE Database SHALL generate a UUID for `id` and set `created_at` and `updated_at` to the current database time.
6. WHEN a row in `users` is updated, THE Database SHALL set `updated_at` to the current database time and SHALL leave `created_at` unchanged.
7. IF an insert or update sets `name`, `email` or `password_hash` to NULL or violates the length limits in criterion 1, THEN THE Database SHALL reject the statement with a constraint-violation error and SHALL leave the existing `users` rows unchanged.

### Requirement 2: Boards and membership roles

**User Story:** As a board administrator, I want each board to record its members and their roles, so that I can manage access.

#### Acceptance Criteria

1. THE Schema SHALL define a `boards` table with a UUID primary key, a non-null `name` of 1 to 255 characters, a non-null `owner_id` referencing `users`, a non-null `created_at`, a non-null `updated_at` and a nullable `deleted_at`.
2. THE Schema SHALL define a `board_members` table with a non-null `board_id` referencing `boards`, a non-null `user_id` referencing `users`, a non-null `role` and a non-null `created_at`.
3. THE Schema SHALL enforce a unique constraint on the pair (`board_id`, `user_id`).
4. THE Schema SHALL restrict `board_members.role` to the values `member` and `admin`.
5. WHEN a Board is created, THE Schema SHALL allow a Board_Member row with role `admin` to be stored for the creating User.
6. WHEN a User is removed from a Board, THE Database SHALL delete only that User's Board_Member row for that Board and SHALL retain every Card and Comment that User created on that Board, with `created_by` values unchanged.
7. IF an insert or update on `board_members` has a `role` other than `member` or `admin`, THEN THE Database SHALL reject the statement with a constraint violation error and leave existing rows unchanged.
8. IF an insert on `board_members` repeats an existing (`board_id`, `user_id`) pair, THEN THE Database SHALL reject the statement with a unique constraint violation error and leave the existing row unchanged.
9. IF an insert on `boards` has a `name` that is null, empty, or longer than 255 characters, THEN THE Database SHALL reject the statement with a constraint violation error and store no row.

### Requirement 3: Columns with float ordering

**User Story:** As a board member, I want columns to keep a stable order, so that I can reorder them without rewriting every column.

#### Acceptance Criteria

1. THE Schema SHALL define a `columns` table with a UUID primary key, `board_id` referencing `boards`, `title`, an Order_Value stored as `order = db.Column(db.Float, nullable=False)`, `created_at`, `updated_at` and `deleted_at`.
2. THE Schema SHALL require `columns.board_id`, `columns.title` and `columns.order` to be non-null, and SHALL limit `columns.title` to a maximum of 255 characters.
3. IF a Column is stored with an Order_Value less than or equal to zero, THEN THE Database SHALL reject the statement with a check-constraint error and SHALL leave the existing rows unchanged.
4. IF a Column is stored with a `board_id` that does not match an existing row in `boards`, THEN THE Database SHALL reject the statement with a foreign-key error and SHALL leave the existing rows unchanged.
5. IF a Column is stored with a `title` that is empty or longer than 255 characters, THEN THE Database SHALL reject the statement with an error indicating the title is invalid and SHALL leave the existing rows unchanged.
6. WHEN a Column is inserted without explicit `created_at` and `updated_at` values, THE Schema SHALL set both to the current UTC time, and SHALL leave `deleted_at` null.

### Requirement 4: Cards

**User Story:** As a board member, I want cards that can be soft-deleted, moved and assigned, so that I can manage tasks without losing history.

#### Acceptance Criteria

1. THE Schema SHALL define a `cards` table with a UUID primary key, `column_id` referencing `columns` (not null), `title` (not null, 1 to 255 characters), `description` (nullable, maximum 10,000 characters), `assignee_id` referencing `users` (nullable), `created_by` referencing `users` (not null), `created_at` (not null), `updated_at` (not null), `deleted_at` (nullable) and `completed_at` (nullable).
2. THE Schema SHALL define the Card Order_Value as `order = db.Column(db.Float, nullable=False)`.
3. IF a Card is stored with an Order_Value less than or equal to zero, THEN THE Database SHALL reject the statement with a check-constraint error and SHALL leave the existing row data unchanged.
4. WHEN a Card row is updated, THE Schema SHALL set `updated_at` to the current UTC time, and the new `updated_at` value SHALL be greater than or equal to the previous `updated_at` value.
5. WHEN a Card is soft-deleted, THE Schema SHALL record the deletion time as a UTC timestamp in `deleted_at`, SHALL keep the row and all its column values unchanged except `deleted_at` and `updated_at`.
6. THE Schema SHALL allow `assignee_id` to be null, so that a Card can be unassigned.
7. WHEN a User account is removed, THE Database SHALL set `cards.assignee_id` to null for all Cards assigned to that User and SHALL keep those Card rows, including soft-deleted ones.
8. WHEN a Card is marked complete, THE Schema SHALL store the completion time as a UTC timestamp in `completed_at`.
9. IF a Card is stored with a `column_id`, `assignee_id` or `created_by` that does not match an existing row in the referenced table, THEN THE Database SHALL reject the statement with a foreign-key error and SHALL leave the existing row data unchanged.

### Requirement 5: Comments

**User Story:** As a board member, I want to comment on cards, so that I can discuss tasks with other members.

#### Acceptance Criteria

1. THE Schema SHALL define a `comments` table with a UUID primary key, `card_id` referencing `cards`, `user_id` referencing `users`, `body`, `created_at`, `updated_at` and `deleted_at`.
2. THE Schema SHALL require `comments.body`, `comments.card_id`, `comments.user_id`, `comments.created_at` and `comments.updated_at` to be non-null, and SHALL allow `comments.deleted_at` to be null.
3. THE Schema SHALL store `comments.user_id` so that the owner of each Comment can be identified.
4. WHEN a Comment is soft-deleted, THE Schema SHALL record the deletion time in `comments.deleted_at` and SHALL keep the row.
5. IF an insert or update sets `comments.body` to an empty string, a string containing only whitespace, or a string longer than 5,000 characters, THEN THE Schema SHALL reject the operation with a constraint violation and SHALL leave existing rows unchanged.
6. IF an insert or update sets `comments.card_id` or `comments.user_id` to a value that does not match an existing row in `cards` or `users` respectively, THEN THE Schema SHALL reject the operation with a foreign key violation and SHALL leave existing rows unchanged.
7. WHEN a Comment row is updated, THE Schema SHALL set `comments.updated_at` to the time of the update, and `comments.updated_at` SHALL be greater than or equal to `comments.created_at`.

### Requirement 6: Notifications

**User Story:** As a user, I want notifications stored per user, so that I can page through them and mark them as read.

#### Acceptance Criteria

1. THE Schema SHALL define a `notifications` table with a UUID primary key, `user_id` referencing `users`, `board_id` referencing `boards`, `card_id` referencing `cards` (nullable), `type`, `message`, `is_read` defaulting to false, and `created_at` defaulting to the insertion timestamp.
2. THE Schema SHALL require `notifications.user_id`, `notifications.type`, `notifications.message`, `notifications.board_id`, `notifications.is_read` and `notifications.created_at` to be non-null, with `type` limited to 1 to 50 characters and `message` limited to 1 to 500 characters.
3. WHEN a query selects the Notifications of one User ordered by `created_at` descending with an offset (0 to 1,000,000) and a limit (1 to 100), THE Database SHALL return only that User's rows, at most the limit count, starting after the offset, using an index on (`user_id`, `created_at`).
4. WHEN `is_read` is set to true for a Notification, THE Database SHALL keep the row and leave every other column value unchanged.
5. IF an insert or update of a Notification violates a non-null constraint, a length limit, or a foreign key reference (`user_id`, `board_id`, or a non-null `card_id`), THEN THE Database SHALL reject the statement with a constraint violation error and leave the table unchanged.
6. WHEN a query selects Notifications for a User who has no Notifications, THE Database SHALL return zero rows without error.

### Requirement 7: Activity log and analytics support

**User Story:** As a board administrator, I want activity and completion data stored, so that I can see board analytics.

#### Acceptance Criteria

1. THE Schema SHALL define an `activity_logs` table with a UUID primary key, a non-null `board_id` referencing `boards`, a non-null `user_id` referencing `users`, a non-null `action` string of 1 to 100 characters, a nullable `card_id` referencing `cards`, and a non-null `created_at` timestamp (UTC) that defaults to the insertion time.
2. WHEN the total number of Cards per Column for a Board is requested, THE Schema SHALL allow one count per Column to be computed with a SQLAlchemy join of `cards` to `columns` filtered by `columns.board_id` and `cards.deleted_at IS NULL`, and a Column with zero non-deleted Cards SHALL be returned with a count of 0.
3. WHEN the Cards completed in the current week for a Board are requested, THE Schema SHALL allow the count to be computed from `cards.completed_at` joined to `columns` filtered by `columns.board_id`, `cards.deleted_at IS NULL` and `cards.completed_at` falling between 00:00:00 Monday (UTC) of the current week (inclusive) and 00:00:00 Monday (UTC) of the next week (exclusive).
4. WHEN member activity for a Board is requested, THE Schema SHALL allow the count of `activity_logs` rows per User to be computed from `activity_logs` joined to `users` filtered by `activity_logs.board_id`, and a User with no matching rows SHALL be returned with a count of 0 only where that User is a member of the Board.
5. WHEN the Cards assigned to a User are requested, THE Schema SHALL allow the Cards to be selected by `assignee_id` joined through `columns` to `boards` with `cards.deleted_at IS NULL`, so that results can be grouped by `boards.name`.
6. WHEN Cards are searched by text, THE Schema SHALL allow a case-insensitive substring match of the search term (1 to 200 characters) against `cards.title` and `cards.description`, excluding Cards where `cards.deleted_at IS NOT NULL`, and a Card SHALL match if either field contains the term.
7. IF an `activity_logs` row is inserted with a `board_id`, `user_id` or non-null `card_id` that does not reference an existing row, THEN THE Schema SHALL reject the insert with a foreign key violation and SHALL leave the `activity_logs` table unchanged.

### Requirement 8: Referential integrity (non-functional)

**User Story:** As a developer, I want the database to enforce relationships, so that stored data stays consistent.

#### Acceptance Criteria

1. THE Schema SHALL declare every column that references another table's row as a foreign key constraint, with zero reference columns lacking a constraint.
2. IF a statement inserts or updates a row with a non-null foreign key value that does not match an existing parent row, THEN THE Database SHALL reject the statement with a foreign-key-violation error, persist no part of the statement, and leave all existing rows unchanged.
3. WHEN a Board is hard-deleted, THE Database SHALL delete all of its `board_members`, `columns`, `activity_logs` and `notifications` rows within the same transaction, leaving zero rows that reference the deleted Board's id in those tables.
4. WHEN a Column is hard-deleted, THE Database SHALL delete all Cards belonging to that Column within the same transaction, leaving zero Cards that reference the deleted Column's id.
5. WHEN a Card is hard-deleted, THE Database SHALL delete all Comments belonging to that Card within the same transaction, leaving zero Comments that reference the deleted Card's id.
6. THE Schema SHALL define a UUID primary key on every table except `board_members`, which SHALL use the composite primary key (`board_id`, `user_id`).
7. IF a statement deletes a parent row that is referenced by a child row and no cascade rule is defined for that relationship, THEN THE Database SHALL reject the statement with a foreign-key-violation error and leave both the parent and child rows unchanged.

### Requirement 9: Indexing and query performance (non-functional)

**User Story:** As a user, I want boards and cards to load fast, so that the application feels responsive.

#### Acceptance Criteria

1. THE Schema SHALL define one composite index on `cards` (`column_id`, `order`), with `column_id` as the leading key, so that retrieving the cards of one column in `order` sequence is served by the index without a separate sort step.
2. THE Schema SHALL define an index on `cards.assignee_id` so that retrieving all cards assigned to one user is served by the index.
3. THE Schema SHALL define one composite index on `columns` (`board_id`, `order`), with `board_id` as the leading key, so that retrieving the columns of one board in `order` sequence is served by the index without a separate sort step.
4. THE Schema SHALL define an index on `comments.card_id` so that retrieving all comments of one card is served by the index.
5. THE Schema SHALL define an index on `board_members.user_id` so that retrieving all boards of one user is served by the index.
6. THE Schema SHALL define one composite index on `activity_logs` (`board_id`, `created_at`), with `board_id` as the leading key, so that retrieving the activity of one board in `created_at` sequence is served by the index.
7. THE Schema SHALL define an index on `cards.completed_at` so that filtering cards by completion timestamp is served by the index.
8. WHEN a board containing up to 50 columns and 5,000 cards is loaded against a database seeded to that size, THE Schema SHALL allow the board, column, and card queries to each complete in 200 ms or less at the 95th percentile over 100 consecutive runs.
9. IF a migration that creates the indexes in criteria 1 to 7 fails, THEN THE Schema SHALL roll back the whole migration, leave the existing tables and data unchanged, and report an error identifying the index that failed.

### Requirement 10: Migrations and reproducibility (non-functional)

**User Story:** As a developer, I want schema changes versioned, so that any environment can be built identically.

#### Acceptance Criteria

1. THE Migration_System SHALL hold every Schema change as a versioned migration file in the repository, with each migration file having a unique revision identifier and exactly one parent revision (except the initial revision, which has none), so that the revision history forms a single linear chain with one head.
2. WHEN `flask db upgrade` is run against an empty PostgreSQL database, THE Migration_System SHALL create every table, column, constraint, and index defined by the models, exit with status code 0, and record the latest revision identifier as the current revision.
3. WHEN `flask db upgrade` is run against a database already at the latest revision, THE Migration_System SHALL exit with status code 0, leave the Schema unchanged, and leave all existing rows unchanged.
4. WHEN `flask db downgrade` is run for the latest revision, THE Migration_System SHALL revert only that revision, exit with status code 0, and set the current revision to the immediately preceding revision, or to no revision if the latest revision is the initial one.
5. WHEN `flask db migrate` is run after the models match the latest revision, THE Migration_System SHALL detect zero Schema differences and generate no new migration file with operations.
6. IF a migration fails while `flask db upgrade` is running, THEN THE Migration_System SHALL exit with a non-zero status code, display an error message identifying the failed revision, and leave the database at the last successfully applied revision with no partial changes from the failed revision.

### Requirement 11: PostgreSQL deployment and configuration (non-functional)

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

**User Story:** As a developer, I want sample data available, so that I can test the application locally.

#### Acceptance Criteria

1. WHEN the Seed_Command is run against an empty Database, THE Database SHALL contain exactly two Users, one Board, two Board memberships (one User with the `admin` role and the other with the `member` role), three Columns belonging to that Board with distinct positions 1 to 3, and five Cards distributed across those Columns, with every Card assigned to exactly one of the three Columns.
2. WHEN the Seed_Command is run one or more additional times, THE Database SHALL contain the same rows and the same row counts for Users, Boards, Board memberships, Columns, and Cards as after the first run, with no duplicate rows created.
3. WHEN the Seed_Command completes successfully, THE Seed_Command SHALL exit with a success status and report that seeding finished.
4. IF the Seed_Command fails partway through, THEN THE Seed_Command SHALL roll back all changes made by that run, exit with a failure status, and report an error indicating the cause of the failure.