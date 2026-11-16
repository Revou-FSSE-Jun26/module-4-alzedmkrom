# Implementation Plan: RevoTask Backend API

Version: V2 (see `CHANGELOG.md`)

## Overview

Implementation is in Python (Flask, Flask-JWT-Extended, Flask-CORS, Marshmallow 3, apispec, SQLAlchemy) under `/backend`, on top of the existing database layer. The order is: dependencies, configuration and test scaffolding; the shared modules under `app/common`; the extended `create_app` with a blueprint registry; the nine blueprints (schema and service first, then routes); OpenAPI and Swagger UI assembly; deployment files; then the cross-cutting tests. Property-based tests use Hypothesis against real PostgreSQL 18 through the fixtures of `tests/database/conftest.py`. Example, smoke and integration tests cover routes, structure, configuration, query count, performance and OpenAPI shape.

All paths below are relative to `/backend`. API tests live in `tests/api/`, property tests in `tests/api/properties/`. Route numbers in task text refer to the route table of `design.md`.

Structure decisions that keep the tasks independent of each other:

- Task 3.1 creates the nine blueprint packages, each with an empty `__init__.py` and a stub `routes.py` that holds only `bp = Blueprint("<name>", __name__)`, and a `register_blueprints` that imports all nine. Later route tasks extend the existing `routes.py` and never edit the registry.
- Each blueprint has a schema-and-service task and a routes task. Route tasks use the decorator order of the design: `@bp.<method>`, `@document`, `@protected`.
- `routes.py` holds no query, `service.py` never imports `flask.request`, and `schema.py` never touches `db` (Requirement 20.5).

## Tasks

- [x] 1. Set up dependencies, configuration and test scaffolding
  - [x] 1.1 Update dependency, environment and test configuration files
    - Add to `requirements.txt`, each with a minimum and an exclusive maximum: `Flask-JWT-Extended>=4.7,<5.0`, `Flask-CORS>=6.0,<7.0`, `marshmallow>=3.23,<4.0`, `apispec[marshmallow]>=6.8,<7.0`, `swagger-ui-bundle>=1.1,<2.0`, `python-dotenv>=1.0,<2.0`, `gunicorn>=23.0,<28.0`, `openapi-spec-validator>=0.7,<1.0`, `pytest-cov>=5.0,<8.0`, `pytest-randomly>=3.15,<6.0`
    - Extend `.env.example` (keep `DB_REQUIRE_SSL` and `SEED_PASSWORD`) with `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRES=3600`, `CORS_ORIGINS=http://localhost:3000`, `SWAGGER_ENABLED=true`, all placeholders with no real credential
    - Create `.coveragerc` (`source = app/blueprints`, `fail_under = 80.0`, `precision = 1`, `show_missing = true`) and add `markers = performance: slow timing tests` to `pytest.ini`
    - Create `tests/conftest.py` that sets `os.environ.setdefault("JWT_SECRET_KEY", "test-secret-not-for-production-0123456789")` at import time so the existing database fixtures keep working
    - _Requirements: 20.2, 20.7, 23.3, 23.4, 23.6, 23.7_

  - [x] 1.2 Implement `app/config.py`
    - Add the frozen `Settings` dataclass, `parse_cors_origins`, `parse_swagger_enabled`, `parse_expires`, `load_settings` (raises `RuntimeError("JWT_SECRET_KEY is not set or is empty")` for a missing, empty or whitespace-only value) and `compile_origins` (anchored, case-sensitive `re.compile(re.escape(o) + r"\Z")`)
    - _Requirements: 2.2, 19.1, 20.1, 20.3, 24.1_

  - [ ]* 1.3 Write property test for settings parsing
    - Create `tests/api/properties/test_prop_settings.py`
    - **Property 8: Settings parsing**
    - **Validates: Requirements 2.2, 19.1, 20.1, 20.3, 24.1**

- [x] 2. Implement shared modules under `app/common`
  - [x] 2.1 Create `app/common/__init__.py` and `app/common/constants.py`
    - Add `Role`, `ActivityAction`, `NotificationType` enums, `NOTIFICATION_MESSAGE_MAX = 500`, `PAGE_SIZE_DEFAULT`, `PAGE_SIZE_MAX`, `OFFSET_MAX`, `MIN_GAP = 1e-6`
    - _Requirements: 6.2, 8.2, 10.4, 13.1, 13.3, 14.1, 14.5_

  - [x] 2.2 Implement `app/common/envelope.py`
    - Add `ok(payload, status=200)`, `error_response(status, message)` and `format_field_errors` (one `<field>: <message>` entry per leaf error, fields sorted, nested keys joined with `.`, `_schema` rendered as the bare message, joined with `; `)
    - _Requirements: 18.1, 18.7_

  - [ ]* 2.3 Write property test for field error formatting
    - Create `tests/api/properties/test_prop_format_errors.py`
    - **Property 6: Field error messages follow one format**
    - **Validates: Requirements 18.7**

  - [x] 2.4 Implement `app/common/errors.py`
    - Add `ApiError`, `Unauthorized`, `Forbidden`, `NotFound`, `Conflict`, `ValidationFailed` and `register_error_handlers` (handlers for `ApiError`, `IntegrityError` (23505 gives 409, other class-23 codes give 400, no SQL text), `HTTPException` (fixed texts for 404, 405, 413) and `Exception` (rollback, `app.logger.exception`, constant 500 message))
    - _Requirements: 18.1, 18.4, 18.5, 18.6, 18.8, 21.3_

  - [x] 2.5 Implement `app/common/validation.py`
    - Add `Text`, `Email`, `StrictUUID`, `OrderValue`, `StrictBoolean`, `DigitsInt`, `UTCDateTime`, `StrictSchema` (`unknown=RAISE`), `LenientSchema` (`unknown=EXCLUDE`), `parse_uuid`, `load_body` (JSON object only) and `load_query` (a repeated key is an error for that key)
    - _Requirements: 1.2, 1.4, 1.6, 8.3, 9.7, 10.5, 13.3, 17.2, 17.6, 18.2, 18.3, 18.7_

  - [ ]* 2.6 Write property test for strict scalar fields
    - Create `tests/api/properties/test_prop_strict_fields.py`
    - **Property 3: Strict scalar fields accept exactly their type**
    - **Validates: Requirements 8.3, 9.7, 10.5, 13.3**

  - [x] 2.7 Implement `app/common/schemas.py`
    - Add the shared response schemas `IdOutSchema`, `AuthorOutSchema`, `ColumnOutSchema` and `CardOutSchema` with `required=True` on always-present fields and no password field
    - _Requirements: 5.2, 7.1, 9.1, 18.2, 21.2_

  - [ ]* 2.8 Write property test for identifier and timestamp serialization
    - Create `tests/api/properties/test_prop_serialization.py`
    - **Property 7: Identifiers and timestamps serialize in one form**
    - **Validates: Requirements 18.2**

  - [x] 2.9 Add `jwt = JWTManager()` to `app/extensions.py` and implement `app/common/auth.py`
    - Add `hash_password`, `verify_password` (checks a dummy hash when the stored hash is `None`), `protected` (`@jwt_required()` plus `__protected__` marker), `current_user` and `register_jwt_callbacks` (`user_lookup_loader` plus the unauthorized, invalid-token, expired-token, lookup-error and revoked-token loaders, all returning the 401 envelope `Authentication required`)
    - _Requirements: 2.1, 17.1, 21.1, 21.5_

  - [ ]* 2.10 Write property test for password hashing
    - Create `tests/api/properties/test_prop_password_hash.py`
    - **Property 10: Password hashes never reveal the password**
    - **Validates: Requirements 21.1**

  - [x] 2.11 Implement `app/common/db.py`
    - Add `lock_board` (`SELECT ... FOR UPDATE` on the board row) and `commit_or_conflict` (commit; on `IntegrityError` roll back and raise `Conflict` for 23505, `ValidationFailed` for other class-23 codes)
    - _Requirements: 4.5, 6.9, 14.6, 18.5_

  - [x] 2.12 Implement `app/common/ordering.py`
    - Add `next_order`, `MovePlan` and `plan_move` (the checks and renumbering described in the design: any sibling within `MIN_GAP` triggers a rebalance, the moved row goes after siblings with an equal order, rows numbered `1.0 ... N`)
    - _Requirements: 7.1, 8.1, 8.2, 9.1, 10.2, 10.4_

  - [ ]* 2.13 Write property test for moves without a close sibling
    - Create `tests/api/properties/test_prop_plan_move_simple.py`
    - **Property 16: A move without a close sibling changes only the moved row**
    - **Validates: Requirements 8.1, 10.2**

  - [ ]* 2.14 Write property test for rebalancing
    - Create `tests/api/properties/test_prop_plan_move_rebalance.py`
    - **Property 17: A rebalance numbers the rows 1 to N and keeps their order**
    - **Validates: Requirements 8.2, 10.4**

  - [x] 2.15 Implement `app/common/events.py`
    - Add `log_activity`, `create_notification` (both only `db.session.add`, no flush or commit), `fit_message` (truncate the title and end it with `…` so the result has at most 500 characters) and `message_card_assigned`, `message_card_moved`, `message_comment_added`, `message_member_added`
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7_

  - [ ]* 2.16 Write property test for notification message length
    - Create `tests/api/properties/test_prop_fit_message.py`
    - **Property 19: Notification messages always fit**
    - **Validates: Requirements 14.7**

  - [x] 2.17 Implement `app/common/access.py`
    - Add `BoardAccess`, `ColumnAccess`, `CardAccess`, `CommentAccess`, `get_board_for_user` (selects only `Board.id` and `role`), `get_column_for_user`, `get_card_for_user`, `get_comment_for_user` (one joined query each: no row gives 404, role `NULL` gives 403, live-record filters on the record and its ancestors) and `require_admin`, `require_admin_or_self`, `require_card_deleter`, `require_comment_owner`
    - _Requirements: 5.6, 6.11, 9.9, 12.6, 17.2, 17.3, 17.4_

  - [x] 2.18 Implement the `document` decorator in `app/common/openapi.py`
    - Add `OpenAPIError` and `document(...)` that attaches metadata to the view function as `fn.__openapi__` and changes no behavior (`build_openapi` and `register_docs` are added in tasks 14.1 and 14.2)
    - _Requirements: 24.17, 24.18_

- [x] 3. Extend `create_app` and create the blueprint registry
  - [x] 3.1 Extend `app/__init__.py` and create the blueprint packages
    - In `create_app(verify_db=True)`: load `backend/.env` with `load_dotenv(override=False)`, normalize `DATABASE_URL` first, then `load_settings`; set `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRES`, `MAX_CONTENT_LENGTH = 1_048_576` and `SQLALCHEMY_ENGINE_OPTIONS` merged with `hide_parameters=True`; init `jwt` and call `register_jwt_callbacks`; configure `CORS` with `compile_origins`, methods GET, POST, PATCH, DELETE, OPTIONS, headers `Authorization` and `Content-Type`, `supports_credentials=False`, `always_send=False`; call `register_error_handlers`; call `register_blueprints`; keep the seed command and the `verify_db` behavior unchanged
    - Create `app/blueprints/__init__.py` with `register_blueprints` importing the nine `routes` modules, and for each of `auth`, `users`, `boards`, `columns`, `cards`, `comments`, `notifications`, `analytics`, `health` an empty `__init__.py` and a stub `routes.py` containing only `bp = Blueprint("<name>", __name__)`
    - _Requirements: 17.4, 18.4, 18.5, 18.6, 18.8, 19.1, 19.2, 19.3, 19.4, 19.5, 20.1, 20.3, 20.4, 20.9, 21.3_

  - [x] 3.2 Create the API test infrastructure
    - Create `tests/api/__init__.py`, `tests/api/properties/__init__.py` and `tests/api/conftest.py` that imports `database_url`, `app` and `engine` from `tests.database.conftest` and adds `clean_db` (autouse `TRUNCATE ... RESTART IDENTITY CASCADE` of the eight tables), `client`, `make_user`, `make_board`, `make_column`, `make_card`, `make_comment`, `make_notification` (insert with a precomputed password hash and commit), `auth_headers(user)`, `snapshot()` and `count_queries()` (records statements through `before_cursor_execute`)
    - _Requirements: 23.1, 23.3, 23.7_

- [x] 4. Implement the auth blueprint
  - [x] 4.1 Implement `app/blueprints/auth/schema.py` and `service.py`
    - Schemas: `RegisterSchema` (`StrictSchema`; `name` 1 to 255, `email`, `password` 8 to 128 untrimmed), `LoginSchema` (`LenientSchema`), `RegisterOutSchema`, `UserBriefOutSchema`, `LoginOutSchema` (`access_token`, `token_type`, `expires_in`, `user`)
    - Service: `register_user` (pre-check, then `commit_or_conflict` so a concurrent loser gets 409), `login` (trim and lower-case the email, `verify_password` with the dummy hash on a miss, one `Unauthorized("Invalid email or password")` for both failure cases, returns user, token and expires_in)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 2.1, 2.2, 2.3, 2.4, 2.5, 21.1, 21.2, 21.5_

  - [x] 4.2 Implement `app/blueprints/auth/routes.py`
    - Route 1: `POST /api/auth/register` (`register`, public, 201 `RegisterOutSchema`, `conflict=True`)
    - Route 2: `POST /api/auth/login` (`login`, public, 200 `LoginOutSchema`)
    - _Requirements: 1.1, 1.3, 1.6, 2.1, 2.4, 2.5, 17.5, 21.2, 24.12, 24.13, 24.19_

  - [ ]* 4.3 Write property test for registration and login
    - Create `tests/api/properties/test_prop_register_login.py`
    - **Property 1: Registration and login round trip**
    - **Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.3, 2.4, 21.5**

  - [ ]* 4.4 Write example tests for auth
    - Create `tests/api/test_auth.py`
    - Success and failure for register and login (400, 401, 409), no password field in responses, `expires_in` from `JWT_ACCESS_TOKEN_EXPIRES`, 8 concurrent registrations give one 201, the rest 409 and one row
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6, 1.7, 2.1, 2.2, 2.4, 2.5, 23.1_

- [ ] 5. Implement the users blueprint
  - [~] 5.1 Implement `app/blueprints/users/schema.py` and `service.py`
    - Schemas: `ProfileUpdateSchema` (`StrictSchema`, `at_least_one` rule giving 400 for `{}`), `ProfileOutSchema`
    - Service: `get_profile`, `update_profile` (only supplied fields, email trimmed and lower-cased, own email is not a conflict, `commit_or_conflict`)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [~] 5.2 Implement `app/blueprints/users/routes.py`
    - Route 3: `GET /api/users/me` (`get_me`, 200 `ProfileOutSchema`)
    - Route 4: `PATCH /api/users/me` (`update_me`, 200 `ProfileOutSchema`, `conflict=True`)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 17.1_

  - [ ]* 5.3 Write example tests for users
    - Create `tests/api/test_users.py`
    - Profile read and update, unknown field (`password`, `id`) gives 400 even with a valid `name`, `{}` gives 400, 409 on another user's email, own email accepted, `null` and empty values give 400
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 23.1_

- [ ] 6. Implement the boards blueprint, including members
  - [~] 6.1 Implement board schemas and service in `app/blueprints/boards/schema.py` and `service.py`
    - Schemas: `BoardCreateSchema`, `BoardUpdateSchema`, `BoardOutSchema`, `ColumnWithCardsOutSchema`, `BoardDetailOutSchema`
    - Service: `create_board` (board plus admin membership in one transaction), `list_boards` (order `updated_at` desc, `id` asc), `get_board_detail` (calls `queries.load_board`, groups cards in a dict, builds plain dicts, no lazy relationships), `rename_board`, `delete_board` (`soft_delete()` on the board only)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 22.1, 22.2_

  - [~] 6.2 Implement board routes in `app/blueprints/boards/routes.py`
    - Route 5: `POST /api/boards` (`create_board`, 201 `BoardOutSchema`)
    - Route 6: `GET /api/boards` (`list_boards`, 200 `BoardOutSchema[]`)
    - Route 7: `GET /api/boards/{id}` (`get_board`, `get_board_for_user`, 200 `BoardDetailOutSchema`)
    - Route 8: `PATCH /api/boards/{id}` (`rename_board`, `get_board_for_user` then `require_admin` before `load_body`)
    - Route 9: `DELETE /api/boards/{id}` (`delete_board`, `require_admin`, 200 `IdOutSchema`)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 17.2, 17.3, 22.1, 22.2_

  - [~] 6.3 Implement member schemas and service in `app/blueprints/boards/schema.py` and `service.py`
    - Schemas: `MemberAddSchema` (`email`, `role` default `member`), `MemberRoleSchema`, `MemberOutSchema`, `MemberRemovedOutSchema`
    - Service: `list_members` (order `created_at` asc), `add_member` (lock board, lookup by `lower(email)`, 404 for unknown user, 409 for existing membership, `member_added` activity and notification), `change_member_role` and `remove_member` (lock board, target membership lookup after the caller's checks, 409 before any write when the board would lose its last admin, `member_role_changed` and `member_removed` activities, bulk `UPDATE cards SET assignee_id = NULL` for live cards of the board assigned to the removed user)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11, 6.12, 14.4, 14.5, 14.7_

  - [~] 6.4 Implement member routes in `app/blueprints/boards/routes.py`
    - Route 10: `GET /api/boards/{id}/members` (`list_members`, `get_board_for_user`, 200 `MemberOutSchema[]`)
    - Route 11: `POST /api/boards/{id}/members` (`add_member`, `require_admin`, 201 `MemberOutSchema`, `conflict=True`)
    - Route 12: `PATCH /api/boards/{id}/members/{user_id}` (`change_member_role`, `require_admin`, then target lookup, `conflict=True`)
    - Route 13: `DELETE /api/boards/{id}/members/{user_id}` (`remove_member`, `require_admin_or_self`, then target lookup, 200 `MemberRemovedOutSchema`, `conflict=True`)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11, 6.12, 17.2, 17.3_

  - [ ]* 6.5 Write property test for board list and board detail
    - Create `tests/api/properties/test_prop_board_reads.py`
    - **Property 27: Board list and board detail match the reference**
    - **Validates: Requirements 4.3, 4.4, 5.1**

  - [ ]* 6.6 Write property test for membership operations
    - Create `tests/api/properties/test_prop_membership.py` using a stateful machine over add, role change and remove
    - **Property 25: Membership operations keep the board administrable**
    - **Validates: Requirements 6.6, 6.7, 6.8, 6.9, 6.10**

  - [ ]* 6.7 Write example tests for boards
    - Create `tests/api/test_boards.py`
    - Create, list (empty and ordered), detail with empty columns and cards, rename, delete, 400 on bad `name`, 403 for role `member` on rename and delete, 404 for a soft-deleted board
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 23.1_

  - [ ]* 6.8 Write example tests for members
    - Create `tests/api/test_members.py`
    - List, add (201, 404 unknown email, 409 existing, 400 bad role), change role, remove, self-removal by a `member`, last-admin 409, 404 for a user without membership, 403 for non-admin changes, unassignment of cards on removal
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11, 6.12, 23.1_

- [ ] 7. Implement the columns blueprint
  - [~] 7.1 Implement `app/blueprints/columns/schema.py` and `service.py`
    - Schemas: `ColumnCreateSchema`, `ColumnUpdateSchema`, `ColumnReorderSchema` (`StrictUUID` `column_id`, `OrderValue` `order`), `ColumnReorderOutSchema`
    - Service: `create_column` (lock board, `next_order`, `column_created` activity), `rename_column` (only `title` and `updated_at`), `delete_column` (`soft_delete()` on the column only), `reorder_columns` (lock board, find `column_id` among live columns of the board or 404, `plan_move`, write only changed rows, return sorted columns and `rebalanced`)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4, 14.5_

  - [~] 7.2 Implement `app/blueprints/columns/routes.py`
    - Route 14: `POST /api/boards/{id}/columns` (`create_column`, `get_board_for_user`, 201 `ColumnOutSchema`)
    - Route 15: `PATCH /api/columns/{id}` (`rename_column`, `get_column_for_user`, 200 `ColumnOutSchema`)
    - Route 16: `DELETE /api/columns/{id}` (`delete_column`, `get_column_for_user`, 200 `IdOutSchema`)
    - Route 17: `PATCH /api/boards/{id}/columns/reorder` (`reorder_columns`, `get_board_for_user`, 200 `ColumnReorderOutSchema`; the route must not be shadowed by `/api/columns/<id>` rules)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4, 17.2, 17.3_

  - [ ]* 7.3 Write example tests for columns
    - Create `tests/api/test_columns.py`
    - Create (order `max + 1.0`), rename keeps `order`, delete leaves cards untouched, reorder without and with rebalance, 400 for bad `column_id` or `order`, 404 for a column of another board or a soft-deleted column
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4, 23.1_

- [ ] 8. Implement the cards blueprint
  - [~] 8.1 Implement card create, update and delete in `app/blueprints/cards/schema.py` and `service.py`
    - Schemas: `CardCreateSchema` and `CardUpdateSchema` (`StrictSchema`; update has the `at_least_one` rule)
    - Service: `create_card` (assignee must be a board member, lock board, `next_order`, `created_by` from the token, `card_created` activity, `card_assigned` notification unless the assignee is the caller), `update_card` (only supplied keys, `changed` rule, `completed_at` set once, cleared on `false`, `card_completed` logged once, `card_updated` when changed, `card_assigned` when the assignee changes to another user), `delete_card` (`soft_delete()`, `card_deleted` activity)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.10, 14.1, 14.4, 14.5, 14.7_

  - [~] 8.2 Implement card move, My Tasks and search in `app/blueprints/cards/schema.py` and `service.py`
    - Schemas: `CardPositionSchema` (validated before the target column lookup), `SiblingOutSchema`, `CardMoveOutSchema`, `CardListQuerySchema` (`exactly_one` of `assignee=me` and `search`), `TaskGroupOutSchema`
    - Service: `move_card` (target column among live columns of the same board or 404, lock board, `plan_move` over the live siblings without the moved card, `card_moved` activity and notification only when the column changes, `siblings` only when rebalanced), `list_my_tasks` (calls `queries.my_tasks`, groups by `board_id` in first-seen order), `search` (calls `queries.search_cards` with the caller's id)
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 11.1, 11.2, 11.3, 11.4, 11.5, 14.2, 14.4, 14.5_

  - [~] 8.3 Implement `app/blueprints/cards/routes.py`
    - Route 18: `POST /api/columns/{id}/cards` (`create_card`, `get_column_for_user`, 201 `CardOutSchema`)
    - Route 19: `GET /api/cards` (`list_cards`, `load_query` with `CardListQuerySchema`, branches to `list_my_tasks` or `search`, one operation documented with a `oneOf` data field)
    - Route 20: `PATCH /api/cards/{id}` (`update_card`, `get_card_for_user`, 200 `CardOutSchema`)
    - Route 21: `DELETE /api/cards/{id}` (`delete_card`, `get_card_for_user` then `require_card_deleter`, 200 `IdOutSchema`)
    - Route 22: `PATCH /api/cards/{id}/position` (`move_card`, `get_card_for_user`, 200 `CardMoveOutSchema`)
    - _Requirements: 9.1, 9.2, 9.6, 9.7, 9.8, 9.9, 9.10, 10.1, 10.5, 10.6, 11.1, 11.2, 11.3, 11.4, 11.5, 17.2, 17.3_

  - [ ]* 8.4 Write property test for next order
    - Create `tests/api/properties/test_prop_next_order.py` covering `next_order` and creation of `n` columns and `n` cards through the API
    - **Property 15: Next order is one above the maximum**
    - **Validates: Requirements 7.1, 9.1**

  - [ ]* 8.5 Write property test for reorder and move endpoints
    - Create `tests/api/properties/test_prop_reorder_move.py`
    - **Property 18: The reorder and move endpoints agree with `plan_move`**
    - **Validates: Requirements 8.1, 8.2, 10.2, 10.4**

  - [ ]* 8.6 Write property test for partial updates
    - Create `tests/api/properties/test_prop_partial_update.py` for `PATCH /api/users/me` and `PATCH /api/cards/{id}`
    - **Property 23: A partial update changes only the supplied fields**
    - **Validates: Requirements 3.2, 9.2**

  - [ ]* 8.7 Write property test for assignee membership
    - Create `tests/api/properties/test_prop_assignee.py`
    - **Property 24: An assignee must be a board member**
    - **Validates: Requirements 9.6**

  - [ ]* 8.8 Write property test for My Tasks and search
    - Create `tests/api/properties/test_prop_cards_list.py`, including terms with `%`, `_` and `\`
    - **Property 28: My Tasks and search match the reference**
    - **Validates: Requirements 11.1, 11.2, 11.5**

  - [ ]* 8.9 Write example tests for cards
    - Create `tests/api/test_cards.py`
    - Create with and without assignee, update fields, `completed` true twice then false, `card_updated` only on a changed value, empty body gives 400, unknown field (`order`, `column_id`, `created_by`) gives 400, delete by creator and by admin, 403 for another member
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10, 23.1_

  - [ ]* 8.10 Write example tests for card moves
    - Create `tests/api/test_card_move.py`
    - Move within and across columns, rebalance response with `siblings`, `CardPositionSchema` validation runs before the column lookup (400 before 404), 404 for a column of another board, no `card_moved` activity within the same column
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 23.1_

  - [ ]* 8.11 Write example tests for the card list route
    - Create `tests/api/test_cards_list.py`
    - `assignee=me` grouped by board (two boards with the same name stay separate), `search=` hit and miss, neither parameter, both parameters, invalid `assignee`, empty and 201-character `search`
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 23.1_

- [~] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Implement the comments blueprint
  - [~] 10.1 Implement `app/blueprints/comments/schema.py` and `service.py`
    - Schemas: `CommentSchema` (`content` 1 to 5,000 with a non-whitespace character), `CommentOutSchema` (`content` from `Comment.body`, nested `author`)
    - Service: `create_comment` (`comment_added` activity, one notification per distinct non-null creator or assignee who is not the author and is still a board member, via one `IN` query on `board_members`), `list_comments` (order `created_at` asc), `update_comment`, `delete_comment` (`soft_delete()`)
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 14.3, 14.4, 14.5, 14.7_

  - [~] 10.2 Implement `app/blueprints/comments/routes.py`
    - Route 23: `POST /api/cards/{id}/comments` (`create_comment`, `get_card_for_user`, 201 `CommentOutSchema`)
    - Route 24: `GET /api/cards/{id}/comments` (`list_comments`, `get_card_for_user`, 200 `CommentOutSchema[]`)
    - Route 25: `PATCH /api/comments/{id}` (`update_comment`, `get_comment_for_user` then `require_comment_owner`, 200 `CommentOutSchema`)
    - Route 26: `DELETE /api/comments/{id}` (`delete_comment`, `get_comment_for_user` then `require_comment_owner`, 200 `IdOutSchema`)
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 17.2, 17.3_

  - [ ]* 10.3 Write example tests for comments
    - Create `tests/api/test_comments.py`
    - Status 201 on a valid comment, status 400 naming `content` when `content` is missing (also empty, whitespace only, 5,001 characters, not a string), status 401 when the request has no Access_Token, status 403 when a non-owner updates or deletes (including a board admin), list order and omission of deleted comments, notifications to creator and assignee
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 14.3, 23.1, 23.2_

- [ ] 11. Implement the notifications blueprint
  - [~] 11.1 Implement `app/blueprints/notifications/schema.py` and `service.py`
    - Schemas: `NotificationListQuerySchema` (`DigitsInt` `page` and `per_page`, `offset_limit` rule naming `page`), `NotificationOutSchema`, `NotificationPageOutSchema`
    - Service: `list_notifications` (calls `queries.notifications_page` and a count; nulls `card_id` of cards that are not live records with one extra `select(Card.id)` query), `mark_read` (`parse_uuid`, 404 when missing or owned by another user, sets `is_read` only when false)
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7_

  - [~] 11.2 Implement `app/blueprints/notifications/routes.py`
    - Route 27: `GET /api/notifications` (`list_notifications`, `load_query`, 200 `NotificationPageOutSchema`)
    - Route 28: `PATCH /api/notifications/{id}/read` (`mark_read`, own-record lookup inside the service, 200 `NotificationOutSchema`)
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 17.1, 17.2_

  - [ ]* 11.3 Write property test for notification pages
    - Create `tests/api/properties/test_prop_notification_pages.py`
    - **Property 29: Notification pages match the reference slice**
    - **Validates: Requirements 13.1, 13.3, 13.4**

  - [ ]* 11.4 Write property test for idempotent completion and mark-read
    - Create `tests/api/properties/test_prop_idempotent.py`
    - **Property 22: Completion and mark-read are idempotent**
    - **Validates: Requirements 9.3, 9.4, 13.5, 13.7**

  - [ ]* 11.5 Write example tests for notifications
    - Create `tests/api/test_notifications.py`
    - Defaults, paging and `total`, empty page past the end, invalid `page` and `per_page` (sign, decimal point, empty, offset above 1,000,000), `card_id` masked for a soft-deleted card, mark-read, mark-read of another user's notification gives 404
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 23.1_

- [ ] 12. Implement the analytics blueprint
  - [~] 12.1 Implement `app/blueprints/analytics/schema.py` and `service.py`
    - Schema: `AnalyticsOutSchema` (`cards_per_column`, `completed_this_week`, `member_activity`)
    - Service: `get_analytics` composing `queries.card_counts_per_column`, `queries.completed_this_week` and `queries.member_activity`
    - _Requirements: 15.1, 15.2, 15.3, 15.5, 15.6_

  - [~] 12.2 Implement `app/blueprints/analytics/routes.py`
    - Route 29: `GET /api/boards/{id}/analytics` (`get_analytics`, `get_board_for_user` then `require_admin`, 200 `AnalyticsOutSchema`)
    - _Requirements: 15.1, 15.4, 17.2, 17.3_

  - [ ]* 12.3 Write example tests for analytics
    - Create `tests/api/test_analytics.py`
    - Response shape, empty columns give 0 and an empty list, week boundary with a patched clock, `member_activity` lists members with 0 actions, 403 for role `member`
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 23.1_

- [ ] 13. Implement the health blueprint
  - [~] 13.1 Implement `app/blueprints/health/schema.py`, `service.py` and `routes.py`
    - Schema: `HealthOutSchema`; service: `get_status()` returning `{"status": "ok"}` with no database access
    - Route 30: `GET /api/health` (`health`, public, 200 `HealthOutSchema`)
    - _Requirements: 16.1, 16.2_

  - [ ]* 13.2 Write example tests for health
    - Create `tests/api/test_health.py`
    - Payload is exactly `{"status": "ok"}`, no `Authorization` header needed, response under 1,000 ms, `POST` gives 405 with an Error_Envelope
    - _Requirements: 16.1, 16.2, 23.1_

- [ ] 14. Implement OpenAPI and Swagger UI assembly
  - [~] 14.1 Implement `build_openapi` in `app/common/openapi.py`
    - `APISpec(title="RevoTask API", version="1.0.0", openapi_version="3.0.3", plugins=[MarshmallowPlugin(...)])` with a resolver that strips a trailing `Schema`, the nine tags, the `bearerAuth` scheme and the `ErrorEnvelope` component
    - Walk `app.url_map` for `/api/` rules (skipping the documentation endpoints, `HEAD` and `OPTIONS`): path `<name>` becomes `{name}` with a required `string`/`uuid` parameter; query, request body and `<Name>Envelope` success schemas (from `Schema.from_dict`) from `__openapi__`; error responses 401, 404, 403, 400, 409 derived from the rule; `security` of `[]` for public routes; the `OneOfData` field for `GET /api/cards`
    - A route without metadata, or any apispec failure, raises `OpenAPIError` whose message starts with `OpenAPI`
    - _Requirements: 24.9, 24.10, 24.11, 24.12, 24.13, 24.14, 24.15, 24.16, 24.17, 24.19, 24.20, 24.21_

  - [~] 14.2 Implement `register_docs` and wire it into `create_app`
    - Add `register_docs(app)` that builds the document once, stores `json.dumps(spec, sort_keys=True)` bytes and adds three `GET`-only URL rules (not a Blueprint, no `@protected`): `/api/docs` (HTML loading `/swagger-ui/swagger-ui.css` and `/swagger-ui/swagger-ui-bundle.js` with `url: "/api/openapi.json"`, no other host), `/api/openapi.json` (raw bytes, `application/json`, no envelope) and `/swagger-ui/<path:filename>` (`send_from_directory` from `swagger_ui_bundle.swagger_ui_path`)
    - In `app/__init__.py` call `register_docs(app)` after `register_blueprints(app)` only when `settings.swagger_enabled` is true
    - _Requirements: 24.1, 24.2, 24.3, 24.4, 24.5, 24.6, 24.7, 24.8, 24.21_

  - [ ]* 14.3 Write the OpenAPI and docs tests
    - Create `tests/api/test_openapi.py`
    - Fetch `/api/openapi.json`, assert 200 and `application/json`, validate with `openapi-spec-validator` (zero errors), list every `/api/` rule of the URL map except the documentation routes, `HEAD` and `OPTIONS`, and assert each method and path (with `<name>` written `{name}`) is exactly one operation with one tag from the nine names and a summary of at most 120 characters
    - Assert parameters, request bodies, success statuses (201 for the six create routes), error responses, `security`, `bearerAuth`, `password` only in the register and login request schemas, and property names and `required` lists equal to the Marshmallow fields (parametrized over every documented schema class)
    - Docs page: `text/html`, no external host, assets under `/swagger-ui/` return 200, byte-identical document across requests, invalid token still 200, `SWAGGER_ENABLED=false` gives 404 envelopes, `POST` gives 405, an undocumented `/api/` route raises `OpenAPIError`
    - _Requirements: 24.2, 24.3, 24.4, 24.5, 24.6, 24.7, 24.9, 24.10, 24.11, 24.12, 24.13, 24.14, 24.15, 24.16, 24.17, 24.19, 24.20, 24.21, 24.22, 24.23_

- [ ] 15. Add deployment configuration
  - [~] 15.1 Create `railway.json`
    - `deploy.startCommand` = `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 30 "app:create_app()"`, `deploy.preDeployCommand` = `["flask db upgrade"]`, `deploy.healthcheckPath` = `/api/health`
    - _Requirements: 20.6, 20.8_

  - [ ]* 15.2 Write configuration and deployment tests
    - Create `tests/api/test_config.py`
    - `.env` loading with process-environment precedence, blank and missing `JWT_SECRET_KEY` raises an error containing `JWT_SECRET_KEY` before any engine exists, `.env.example` is tracked and has the five `NAME=value` lines with placeholders, `requirements.txt` lines have `>=` and `<`, `railway.json` start and pre-deploy commands, `.coveragerc` has `fail_under = 80.0`
    - _Requirements: 20.1, 20.2, 20.3, 20.6, 20.7, 20.8, 20.9, 23.4_

- [~] 16. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 17. Write cross-cutting and remaining property tests
  - [ ]* 17.1 Write the protected-route and log tests
    - Create `tests/api/test_cross_cutting.py`
    - For every protected route from the route registry (`app.url_map` plus `__openapi__`): one test with no Access_Token asserting 401 and a string `error`, and one test with a valid token asserting a status other than 401
    - Capture logs and assert no password, token, `Authorization` value or `JWT_SECRET_KEY` appears, including after a forced 500; a SQL injection string (`'; DROP TABLE users; --`) is stored as literal text
    - _Requirements: 17.1, 18.6, 21.3, 21.4, 23.5_

  - [ ]* 17.2 Write property test for authentication order
    - Create `tests/api/properties/test_prop_auth_first.py`
    - **Property 11: Authentication precedes every other check**
    - **Validates: Requirements 17.1, 17.4, 23.5, 24.4**

  - [ ]* 17.3 Write property test for board-scoped access
    - Create `tests/api/properties/test_prop_access.py`
    - **Property 12: Board-scoped routes are closed to non-members and members lacking the role**
    - **Validates: Requirements 5.6, 6.11, 9.9, 12.6, 15.4, 17.3**

  - [ ]* 17.4 Write property test for check order
    - Create `tests/api/properties/test_prop_check_order.py`
    - **Property 13: The first failing check decides the status**
    - **Validates: Requirements 5.6, 17.2, 17.4**

  - [ ]* 17.5 Write property test for envelopes and server errors
    - Create `tests/api/properties/test_prop_envelope.py`
    - **Property 14: Every response is an envelope and no input causes a server error**
    - **Validates: Requirements 16.1, 18.1, 18.3, 18.4, 18.6, 18.8, 21.2**

  - [ ]* 17.6 Write property test for bounded text fields
    - Create `tests/api/properties/test_prop_text_bounds.py` over every bounded text field of the request schemas, including `NUL`, lone surrogates and non-BMP characters
    - **Property 2: Bounded text fields accept exactly their range**
    - **Validates: Requirements 1.4, 2.5, 3.6, 4.2, 5.4, 7.3, 11.3, 12.2**

  - [ ]* 17.7 Write property test for unknown fields
    - Create `tests/api/properties/test_prop_unknown_fields.py`
    - **Property 4: Unknown fields are rejected by strict schemas and ignored by lenient ones**
    - **Validates: Requirements 1.5, 3.3, 9.7, 17.5, 17.6**

  - [ ]* 17.8 Write property test for request body shape
    - Create `tests/api/properties/test_prop_body_shape.py`
    - **Property 5: A request body must be a JSON object**
    - **Validates: Requirements 1.6, 18.3**

  - [ ]* 17.9 Write property test for CORS origin matching
    - Create `tests/api/properties/test_prop_cors_origins.py` building an app per drawn origin list with `create_app(verify_db=False)`
    - **Property 9: CORS origin matching is exact**
    - **Validates: Requirements 19.2, 19.4, 19.5, 24.8**

  - [ ]* 17.10 Write example tests for CORS
    - Create `tests/api/test_cors.py`
    - Preflight from a listed origin (status 200 or 204, methods and headers), unlisted origin, no `Origin` header, default `http://localhost:3000`, header present on 401 and 404 responses and on the documentation routes
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 24.8, 23.1_

  - [ ]* 17.11 Write property test for activity logs and notifications
    - Create `tests/api/properties/test_prop_events.py` using `RuleBasedStateMachine` with a reference model
    - **Property 20: Activity logs and notifications match the event model**
    - **Validates: Requirements 6.2, 9.1, 9.3, 9.5, 10.3, 12.1, 14.1, 14.2, 14.3, 14.4, 14.5**

  - [ ]* 17.12 Write property test for failed event writes
    - Create `tests/api/properties/test_prop_event_failure.py`, patching `log_activity` or `create_notification` to raise and comparing `snapshot()` before and after, plus a failing membership insert in board creation
    - **Property 21: A failed event write leaves no change**
    - **Validates: Requirements 4.5, 14.6**

  - [ ]* 17.13 Write property test for soft deletes
    - Create `tests/api/properties/test_prop_soft_delete_api.py`
    - **Property 26: Soft-deleted records are invisible and nothing else changes**
    - **Validates: Requirements 5.2, 5.5, 7.4, 9.8, 12.3, 12.5, 17.2**

  - [ ]* 17.14 Write property test for literal text handling
    - Create `tests/api/properties/test_prop_literal_text.py`
    - **Property 30: Request values are stored and matched as literal text**
    - **Validates: Requirements 21.4**

  - [ ]* 17.15 Write example tests for events
    - Create `tests/api/test_events.py`
    - Activity and notification rules for card create, assign, move, comment and member add; `board_id` and `card_id` set as specified; `member_added` notification has `card_id` null; long titles truncated to 500 characters
    - _Requirements: 6.2, 9.1, 9.5, 10.3, 12.1, 14.1, 14.2, 14.3, 14.4, 14.5, 14.7, 23.1_

  - [ ]* 17.16 Write structure tests
    - Create `tests/api/test_structure.py`
    - Nine blueprints each with `routes.py`, `service.py` and `schema.py`; `routes.py` has no `select`, `db.session` or `.query`; `service.py` does not import `flask.request` or `jsonify`; `schema.py` does not import `db`; `__openapi__` metadata is set only in blueprint files and `common/openapi.py`
    - _Requirements: 20.4, 20.5, 24.18_

  - [ ]* 17.17 Write the board query-count test
    - Create `tests/api/test_query_count.py` using `count_queries()`
    - `GET /api/boards/{id}` runs exactly 3 board-load queries (boards, columns, cards) after authentication and membership lookups, and the count is equal for a board with 1 empty column and for a board with 50 columns and 5,000 cards
    - _Requirements: 22.2_

  - [ ]* 17.18 Write the performance tests
    - Create `tests/api/test_performance.py` marked `@pytest.mark.performance`
    - Bulk-insert 50 columns and 5,000 cards (100 per column); after 1 discarded warm-up request, 100 sequential requests each for `GET /api/boards/{id}` and `GET /api/boards/{id}/analytics` with p95 at most 500 ms
    - _Requirements: 22.1, 22.3_

  - [ ]* 17.19 Write the coverage gate test
    - Create `tests/api/test_coverage_gate.py`
    - Load `.coveragerc` and assert `source` is `app/blueprints` and `fail_under` is 80.0; run `coverage report --fail-under` against a temporary data file with measured coverage below the threshold and assert a non-zero exit and the measured percentage in the output
    - _Requirements: 23.4, 23.6_

- [~] 18. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP. The requirements for the Test_Suite (Requirements 23 and 24.22, 24.23) are met only when the optional tests are written.
- Each task references specific requirements for traceability. Every route of the design's route table has a task: routes 1 to 2 (4.2), 3 to 4 (5.2), 5 to 9 (6.2), 10 to 13 (6.4), 14 to 17 (7.2), 18 to 22 (8.3), 23 to 26 (10.2), 27 to 28 (11.2), 29 (12.2), 30 (13.1), and the documentation routes (14.2).
- Checkpoints ensure incremental validation.
- Property tests validate universal correctness properties (Properties 1 to 30 of `design.md`) and run against PostgreSQL 18, never SQLite. Pure-function properties (6, 7, 8, 10, 15, 16, 17, 19) need no database.
- Unit and example tests validate specific examples, structure, configuration and documentation shape.
- Run the full suite from `backend/` with `python -m pytest`, and the coverage gate with `python -m pytest tests/api --cov=app/blueprints`.
- Open points from `design.md` stay open: Railway config as code is deprecated after 2026-12-01 (set the same three values in the dashboard then), the marshmallow 3 pin, and the nested `user` object of the login response (D9).

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "15.1"] },
    { "id": 1, "tasks": ["1.2", "2.2", "2.12", "2.15", "2.18"] },
    { "id": 2, "tasks": ["1.3", "2.3", "2.4", "2.13", "2.14", "2.16"] },
    { "id": 3, "tasks": ["2.5", "2.9", "2.11"] },
    { "id": 4, "tasks": ["2.6", "2.7", "2.10", "2.17", "3.1"] },
    {
      "id": 5,
      "tasks": ["2.8", "3.2", "4.1", "5.1", "6.1", "7.1", "8.1", "10.1", "11.1", "12.1", "13.1"]
    },
    {
      "id": 6,
      "tasks": ["4.2", "5.2", "6.2", "6.3", "7.2", "8.2", "10.2", "11.2", "12.2"]
    },
    {
      "id": 7,
      "tasks": ["4.3", "4.4", "5.3", "6.4", "6.5", "6.7", "7.3", "8.3", "10.3", "11.3", "11.5", "12.3", "13.2"]
    },
    {
      "id": 8,
      "tasks": ["6.6", "6.8", "8.4", "8.5", "8.6", "8.7", "8.8", "8.9", "8.10", "8.11", "11.4", "14.1"]
    },
    {
      "id": 9,
      "tasks": [
        "14.2", "17.1", "17.3", "17.4", "17.5", "17.6", "17.7", "17.8", "17.11", "17.12",
        "17.13", "17.14", "17.15", "17.16", "17.17", "17.18", "17.19"
      ]
    },
    { "id": 10, "tasks": ["14.3", "15.2", "17.2", "17.9", "17.10"] }
  ]
}
```
