---
inclusion: always
---

# RevoTask Backend Guidelines

Stack: Flask (blueprints) + SQLAlchemy + Marshmallow + JWT + pytest.
Every guideline has an ID, a **Rule**, a **Rationale**, and a **RevoTask example**. Cite the ID when reporting a violation (e.g. "violates BE-AZ-04").

## Scope and boundaries

This file owns: blueprint structure, schemas and validation, the response and error contract, authentication, authorization, ordering rules, analytics definitions, service-layer behavior, notification triggers, security configuration, and backend tests.

This file does NOT own, and must not restate:
- Models, constraints, indexes, migrations, cascade settings, column types: see `database.md`.
- How the UI consumes the error shape, stores the token, computes drag-and-drop positions, or handles optimistic updates: see `frontend.md`. The ordering constants and the position request/response contract are defined here (section 6).

Where this file depends on a database fact it says "see `database.md` → <section>".

## User types

RevoTask has two primary user types. Design every feature for them first.
- **Member:** creates boards, organizes work into columns, moves cards by drag-and-drop, collaborates through comments, and tracks their assigned tasks.
- **Admin:** manages member access, oversees every card on the board, and monitors team activity through analytics and notifications. Admin is a per-board role; creating a board makes the creator its Admin.

Guest and Anonymous are secondary, read-only viewers of public boards. Do not build features for them beyond reading, and do not let their needs change Member or Admin behavior.

## Product decisions beyond the original requirements

These were deliberate decisions. Do not "fix" them back to the literal requirements, and do not add behavior that contradicts them.
- Roles are **per board**. There is no global role and no `users.role`.
- Whoever creates a board becomes its **Admin**. A board can have several Admins (co-admins), all equal.
- A user with no membership on a board is a **Guest** on it (read-only). **Anonymous** visitors (no token) can read public boards.
- Boards are **public by default** (`is_public = true`); an Admin can make a board private.
- Members delete only what they created, and a Member cannot delete a column that contains another member's card. Comments are owner-only for edit and delete, including for Admins. Admins can delete any card or column, and the board itself, cascading over everyone's work.

Deviations from the literal endpoint list (keep, and mention in the README or spec):
- `GET /api/boards` takes a `scope` parameter and is paginated.
- `PATCH /api/boards/<id>` also accepts `is_public`. `PATCH /api/columns/<id>` also accepts `is_done` (Admin only).
- Comment edit and delete also require current board membership.
- Added endpoints: board member management (BE-AZ-07) and `GET /api/cards?assignee=me` (BE-SVC-05), the assigned-tasks list the frontend `/my-tasks` page requires.
- `GET /api/notifications` also returns `unread_count` (BE-NTF-03).
- `DELETE` endpoints for boards, columns, and cards are restricted by role and ownership (BE-AZ-04).
- `DELETE /api/cards/<id>` is a soft delete (BE-SVC-06).
- Analytics is limited to Admins of that board.

---

## 1. Project structure

### BE-STR-01 One blueprint per domain
- **Rule:** Each domain lives in `app/blueprints/<name>/` with exactly `__init__.py`, `routes.py`, `service.py`, `schema.py`. Domains (exactly these eight): `auth`, `boards`, `columns`, `cards`, `comments`, `notifications`, `analytics`, `users`. Board member management (BE-AZ-07) lives in `boards`. Blueprints are registered only in `app/__init__.py` (app factory). `GET /api/users/me` lives in `users`; `GET /api/cards?assignee=me` lives in `cards`.
- **Rationale:** A fixed layout lets a reviewer find any behavior in one place and lets AI output be checked against a known shape.
- **RevoTask example:** `POST /api/boards/<id>/columns` is routed in `columns/routes.py`, validated in `columns/schema.py`, and implemented in `columns/service.py`, even though the URL starts with `/boards`.

### BE-STR-02 Routes are thin
- **Rule:** A route function only does four things: authenticate, validate input via a schema, call one service function, serialize the result. Routes contain no SQLAlchemy queries, no `db.session` calls, no business rules, and no role comparisons.
- **Rationale:** Logic in routes cannot be unit-tested without HTTP and gets duplicated across endpoints.
- **RevoTask example:** `PATCH /api/cards/<id>/position` calls `card_service.move_card(user, card_id, data)`. It does not touch the session itself.

### BE-STR-03 Analytics logic lives in the service layer
- **Rule:** All analytics aggregates are computed in `analytics/service.py` with SQLAlchemy joins and `func` aggregates, as defined in BE-ANL-01. Never load all rows and count them in Python.
- **Rationale:** Aggregating in the database stays fast as boards grow, and the requirements mandate SQLAlchemy joins in the service layer.
- **RevoTask example:** "Cards per column" is one `JOIN columns → cards GROUP BY column.id` query, not a loop over `board.columns` calling `len(column.cards)`.

---

## 2. Validation (Marshmallow)

### BE-VAL-01 Every input goes through a schema
- **Rule:** Every JSON body and query string is validated by a Marshmallow schema before reaching a service. Services never read `request` directly. Path IDs use Flask's `<uuid:...>` converter, so a malformed ID returns 404 `NOT_FOUND` (BE-ERR-05).
- **Rationale:** Validation in one layer guarantees services receive clean, typed data.
- **RevoTask example:** `GET /api/notifications` validates `page` and `per_page` with `PaginationQuerySchema`, not `request.args.get("page")` inside the service.

### BE-VAL-02 Unknown fields are rejected
- **Rule:** All schemas set `class Meta: unknown = RAISE`. A request containing an unexpected field fails validation.
- **Rationale:** Silently ignored fields hide client bugs and enable mass-assignment attacks.
- **RevoTask example:** `PATCH /api/users/me` with `{"name": "Ana", "password": "x"}` or `{"role": "admin"}` returns 422, because `UserUpdateSchema` only allows `name` and `email`. `POST /api/auth/register` with a `role` field also returns 422.

### BE-VAL-03 Typed, bounded fields
- **Rule:** IDs are `fields.UUID`. Strings have `validate.Length(min=1, max=N)`, with N taken from the column length in `database.md` → DB-SCH-01, and are stripped. Emails use `fields.Email` and are trimmed and lowercased before storage and comparison (register, login, profile update, add member). Orders use `fields.Float` with `validate.Range(min=0, min_inclusive=False)`. Membership roles use `validate.OneOf(["member", "admin"])`. A `PATCH` body with no fields returns 422.
- **Rationale:** Explicit bounds prevent empty names, oversized payloads, non-positive orders, and invalid roles. Normalized emails prevent duplicate accounts that differ only by case.
- **RevoTask example:** `CardPositionSchema` requires `column_id` as a UUID and `order` as a float greater than 0. `{"order": 0}` and `{"order": -1.5}` are rejected. Logging in as `Ana@Example.com` matches the account registered as `ana@example.com`.

### BE-VAL-04 Schema naming and separation
- **Rule:** Input schemas are named `<Entity><Action>Schema` (`CardCreateSchema`, `CardUpdateSchema`, `CardPositionSchema`). Output schemas are `<Entity>Schema`. Input and output schemas are never shared. Any response that can reach an Anonymous or Guest viewer, or embeds another user (comment author, card assignee, member list), serializes users with `PublicUserSchema` (id and name only). Email is exposed only to the user themselves (`GET /api/users/me`) and to Admins of the board in the members list.
- **Rationale:** Sharing one schema for input and output is how fields like `password_hash` leak, and public boards must not expose personal data.
- **RevoTask example:** `GET /api/boards/<id>` for an Anonymous visitor lists card assignees with `{id, name}` only.

### BE-VAL-05 Field lists per schema
- **Rule:** Input schemas accept exactly these fields (all others are rejected by BE-VAL-02). Maximum lengths of stored text are defined once, in `database.md` → DB-SCH-01 (the column types), and schemas take them from there; only rules that exist nowhere in the database are written here, such as the password minimum.

| Schema | Fields |
|---|---|
| `RegisterSchema` | `name`, `email`, `password` (min 8, max 128) |
| `LoginSchema` | `email`, `password` |
| `UserUpdateSchema` | `name`, `email` (both optional, at least one) |
| `BoardCreateSchema` | `name`, `is_public` (optional, default true) |
| `BoardUpdateSchema` | `name`, `is_public` (both optional, at least one) |
| `ColumnCreateSchema` | `name` |
| `ColumnUpdateSchema` | `name`, `is_done` (both optional; `is_done` is Admin only) |
| `ColumnReorderSchema` | `column_id`, `order` |
| `CardCreateSchema` | `title`, `description` (optional), `assignee_id` (optional), `due_date` (optional, ISO date) |
| `CardUpdateSchema` | `title`, `description`, `assignee_id` (nullable), `due_date` (nullable); all optional, at least one |
| `CardPositionSchema` | `column_id`, `order` |
| `CommentCreateSchema` / `CommentUpdateSchema` | `content` (required, non-empty) |
| `MemberAddSchema` | `email`, `role` |
| `MemberUpdateSchema` | `role` |
| Query schemas | `PaginationQuerySchema` (`page`, `per_page`), `BoardListQuerySchema` (pagination + `scope`), `AssignedCardsQuerySchema` (pagination + `assignee`, `board_id`, `done`) |

New columns and cards are appended to the end of their container by the server (BE-ORD-01); clients cannot send `order` on create.
- **Rationale:** Without explicit field lists, generated code invents fields or drops ones the UI needs.
- **RevoTask example:** `POST /api/columns/<id>/cards` with `{"title": "Fix login", "order": 5}` returns 422 because `order` is not in `CardCreateSchema`.

---

## 3. Response and error contract

This section is the single source of truth. `frontend.md` only references it.

### BE-ERR-01 One error shape
- **Rule:** Every error response has this body and nothing else:
  `{"error": {"code": "<UPPER_SNAKE>", "message": "<human readable>", "details": {...} | null}}`
  Errors are produced by registered error handlers, never hand-built in routes.
- **Rationale:** One shape lets the client write one error handler.
- **RevoTask example:** a bad `CardPositionSchema` payload returns `{"error": {"code": "VALIDATION_ERROR", "message": "Invalid request data.", "details": {"order": ["Must be greater than 0."]}}}`.

### BE-ERR-02 Status code map
- **Rule:**

| Status | Code | Used when |
|---|---|---|
| 400 | `BAD_REQUEST` | Malformed JSON or missing body |
| 401 | `UNAUTHENTICATED` | No token on a protected or write route; invalid or expired token; wrong login credentials |
| 403 | `FORBIDDEN` | The user can see the board but their board role or ownership is insufficient |
| 404 | `NOT_FOUND` | Resource missing, malformed UUID in the path, or the board is private and the user is not a member |
| 409 | `CONFLICT` | Duplicate email, already a member, `LAST_ADMIN`, or a delete blocked by another member's cards |
| 422 | `VALIDATION_ERROR` | Schema validation failed |
| 500 | `INTERNAL_ERROR` | Unhandled error (generic message only) |

Success: 200 read/update, 201 create, 204 delete (empty body).
- **Rationale:** Consistent codes make behavior predictable and testable.
- **RevoTask example:** registering an existing email returns 409 `EMAIL_TAKEN`; a Guest creating a card returns 403 `FORBIDDEN`; an Anonymous visitor doing the same returns 401 `UNAUTHENTICATED`.

### BE-ERR-03 Pagination envelope
- **Rule:** Paginated endpoints (`GET /api/boards`, `GET /api/notifications`, `GET /api/cards?assignee=me`) accept `page` (default 1, min 1) and `per_page` (default 20, max 100) and return `{"items": [...], "page": n, "per_page": n, "total": n, "pages": n}`. Values over the max are rejected with 422, not silently clamped. `GET /api/notifications` adds one extra field, `unread_count` (BE-NTF-03).
- **Rationale:** An unbounded `per_page` lets one request dump a table.
- **RevoTask example:** `GET /api/notifications?page=2&per_page=10` returns that envelope, ordered newest first.

### BE-ERR-04 No internal details in responses
- **Rule:** The 500 handler logs the exception server-side and returns a generic message. No stack traces, SQL, or file paths in any response. `app.debug` is never true outside local development.
- **Rationale:** Internals help attackers and confuse users.
- **RevoTask example:** a failing analytics query returns `{"error": {"code": "INTERNAL_ERROR", "message": "Something went wrong.", "details": null}}`.

### BE-ERR-05 Success response shapes
- **Rule:** A single resource is returned as a bare JSON object (no wrapper). Non-paginated lists (comments, members, columns of a board) are returned as `{"items": [...]}`. Field names are snake_case. Timestamps are ISO-8601 UTC strings ending in `Z`. Comments are ordered oldest first.
- **Rationale:** Predictable shapes let the frontend share one set of types and parsers.
- **RevoTask example:** `GET /api/cards/<id>/comments` returns `{"items": [{"id": "...", "content": "...", "author": {"id": "...", "name": "..."}, "created_at": "2026-11-13T08:00:00Z"}]}`.

---

## 4. Authentication

### BE-AUTH-01 Password hashing
- **Rule:** Hash passwords with `werkzeug.security.generate_password_hash` (or bcrypt). Never store, log, or return plaintext passwords or `password_hash`.
- **Rationale:** A database leak must not expose credentials.
- **RevoTask example:** `POST /api/auth/register` stores only the hash, and the 201 response is a `UserSchema` dump without any password field.

### BE-AUTH-02 JWT with explicit expiry
- **Rule:** `POST /api/auth/login` returns `{"access_token": "...", "token_type": "Bearer", "expires_in": <seconds>}`. The token carries `sub` (user id), `iat`, and `exp`. Lifetime comes from `JWT_EXPIRES_MINUTES` (default 60). Tokens never lack `exp`.
- **Rationale:** A token without expiry is valid forever if stolen.
- **RevoTask example:** an expired token on `GET /api/boards` returns 401 `UNAUTHENTICATED` with the standard error shape.

### BE-AUTH-03 Board roles are read from the database, not the token
- **Rule:** The token never carries any role. Board role is resolved from the `board_members` table on each request (see BE-AZ-01).
- **Rationale:** A demoted or removed user loses access immediately instead of at token expiry.
- **RevoTask example:** an Admin demoted to Member gets 403 on `GET /api/boards/<id>/analytics` on their next request, using the same token.

### BE-AUTH-04 Two decorators, no others
- **Rule:** Protected routes use `@auth_required` from `app/auth_utils.py`. Only these routes use `@auth_optional`, which sets `current_user` to `None` when no token is sent: `GET /api/boards`, `GET /api/boards/<id>`, `GET /api/cards/<id>/comments`. A token that is present but invalid or expired still returns 401, and is never treated as anonymous. `POST /api/auth/register` and `POST /api/auth/login` are public. Login returns the same 401 message for unknown email and wrong password.
- **Rationale:** A small, explicit list of public endpoints is easy to audit, and identical login errors prevent account enumeration.
- **RevoTask example:** `GET /api/users/me` uses `@auth_required`; `GET /api/boards/<id>` uses `@auth_optional` so an Anonymous visitor can read a public board.

---

## 5. Authorization

### BE-AZ-01 Per-board roles, resolved in one function
- **Rule:** There is no global role and no `users.role`. `app/permissions.py` exposes `resolve_board_role(user, board)` returning one of `anonymous`, `guest`, `member`, `admin`:
  - `anonymous`: `user` is `None`.
  - `guest`: logged in, no row in `board_members` for this board.
  - `member` / `admin`: the `role` of the user's `board_members` row (see `database.md` → Board membership).
  Registration creates a plain user and never accepts a role. Admin power on one board gives no power on another.
- **Rationale:** One resolver means roles cannot be computed inconsistently across endpoints.
- **RevoTask example:** a user who is Admin of board A and has no row on board B is a `guest` on board B, so `PATCH /api/boards/B` returns 403.

### BE-AZ-02 Permission matrix is the single source of truth
- **Rule:** Permissions are defined once in `app/permissions.py` as an action-to-rule map and enforced through one call: `authorize(user, action, resource)`, invoked at the start of the service function. Routes and services must not contain inline role comparisons. The map encodes this matrix (evaluated per board):

| Action | Anonymous | Guest | Member | Admin (this board) |
|---|---|---|---|---|
| View board, columns, cards, comments | Public boards | Public boards | Yes | Yes |
| Create a new board | 401 | Yes (becomes its Admin) | Yes (becomes its Admin) | Yes (becomes its Admin) |
| Rename board, toggle `is_public` | 401 | 403 | 403 | Yes |
| Add, rename, reorder columns | 401 | 403 | Yes | Yes |
| Set column `is_done` | 401 | 403 | 403 | Yes |
| Create, edit, move cards, set assignee | 401 | 403 | Yes | Yes |
| Add comment | 401 | 403 | Yes | Yes |
| Edit or delete comment | 401 | 403 | Own only (while a member) | Own only (while a member) |
| Delete column | 401 | 403 | Only own, and only if every card in it is also theirs (BE-AZ-04) | Any (cascades) |
| Delete card | 401 | 403 | Only own | Any (soft delete, BE-SVC-06) |
| Delete board | 401 | 403 | 403 | Yes (cascades) |
| Analytics for this board | 401 | 403 | 403 | Yes |
| List members | 401 | 403 | Yes | Yes (sees emails) |
| Add, promote, demote, remove members | 401 | 403 | 403 | Yes |
| Own profile, notifications, assigned cards | 401 | Yes | Yes | Yes |

"Anyone logged in can create a board" is intentional: it is how a user becomes the first Admin of a board.
- **Rationale:** A central map prevents one endpoint from forgetting a check and makes role tests derivable from the table.
- **RevoTask example:** `DELETE /api/cards/<id>` calls `authorize(current_user, "card:delete", card)`; the route has no role logic.

### BE-AZ-03 Order of checks: authentication, then visibility, then permission
- **Rule:** For any board-scoped resource, resolve it to its board first (comment → card → column → board), then check in this order: (1) authentication: a protected or write route without a valid token returns 401; (2) visibility: a private board and a non-member returns 404 `NOT_FOUND` (this includes an Anonymous GET on a private board); (3) permission: a board role or ownership that is insufficient returns 403.
- **Rationale:** 401 tells the client to log in, 404 hides private boards, and 403 tells a logged-in user they lack rights. A fixed order prevents contradictory responses.
- **RevoTask example:** an Anonymous `POST /api/columns/<id>/cards` returns 401 on any board. A Guest gets 403 on a public board and 404 on a private one.

### BE-AZ-04 Members delete only their own work, never cascading over others' cards
- **Rule:** A Member may delete a column or card only if (a) they created it (`created_by == user.id`) and (b) for a column, every card inside it was also created by them. If any card has a different or null `created_by`, the delete fails with 409 `COLUMN_HAS_FOREIGN_WORK` and `details: {"cards": n}`. Check (b) in the service before deleting. A Member can always delete their own card; comments on it are hidden with it (BE-SVC-06) and do not block the delete. Soft-deleted cards are ignored by check (b). Admins of the board skip check (b) and may delete columns, cards, and the board itself, cascading to children (see `database.md` → Cascade rules). Comments have no children: only the author may delete or edit them, including when the requester is an Admin.
- **Rationale:** The database cascade would otherwise silently destroy other members' cards, so the service must refuse first. Comments are discussion attached to a card and do not block a delete.
- **RevoTask example:** a Member deletes their own column that contains one card created by another member: response is 409 `COLUMN_HAS_FOREIGN_WORK` with `details: {"cards": 1}`. The same Member's column containing only their own cards returns 204. A Member deleting their own card returns 204 even if others commented on it.

### BE-AZ-05 Membership is required before ownership
- **Rule:** Ownership alone never grants access. A user removed from a board becomes a Guest on it, and loses the ability to delete or edit items they created there, including their own comments.
- **Rationale:** A removed member must not retain control of a board they left.
- **RevoTask example:** a user removed from a board gets 403 (public board) or 404 (private board) when deleting a card they created there.

### BE-AZ-06 Assignee and co-admin integrity
- **Rule:**
  - A card's `assignee_id` must be a Member or Admin of the card's board; otherwise 422.
  - Removing a user from a board sets `assignee_id` to NULL on that board's cards assigned to them, in the same transaction.
  - A board must always keep at least one Admin: demoting or removing the last Admin returns 409 `LAST_ADMIN`.
  - An Admin may promote a Member to Admin and demote another Admin to Member. Co-admins have equal rights.
- **Rationale:** Assigning to outsiders breaks visibility, stale assignees break "track my tasks", and a board with no Admin cannot be managed.
- **RevoTask example:** `PATCH /api/cards/<id>` with an `assignee_id` of a Guest returns 422 with `details: {"assignee_id": ["User is not a member of this board."]}`.

### BE-AZ-07 Board creation and member management endpoints
- **Rule:** Creating a board (`POST /api/boards`) inserts the board and the creator's `admin` membership row in the same transaction. Member management endpoints (in the `boards` blueprint, schema-validated):
  - `GET /api/boards/<id>/members` (Member or Admin)
  - `POST /api/boards/<id>/members` with `{"email", "role"}` (Admin only; unknown email returns 422; already a member returns 409 `ALREADY_MEMBER`)
  - `PATCH /api/boards/<id>/members/<user_id>` with `{"role"}` (Admin only)
  - `DELETE /api/boards/<id>/members/<user_id>` (Admin only)
- **Rationale:** The scenario gives Admins control of member access, and the original endpoint list does not cover it. Creating the Admin row atomically prevents orphaned boards.
- **RevoTask example:** a Member calling `POST /api/boards/<id>/members` gets 403; an Admin adding a Guest by email creates a `member` row and notifies that user.

---

## 6. Ordering logic (FLOAT strategy)

Column types and constraints for `order`: see `database.md` → Ordering columns. The model attribute and the API field are both `order`; only the database column is named `position`. The client computes positions; the server validates and stores them. `frontend.md` references this section for the constants and formulas.

### BE-ORD-01 Constants and formulas
- **Rule:** `app/ordering.py` defines `ORDER_STEP = 1024.0` and `MIN_GAP = 1e-6`. The position formulas are:
  - Between two neighbors: `(prev + next) / 2`.
  - At the start of a container: `first / 2`.
  - At the end of a container: `last + ORDER_STEP`.
  - In an empty container: `ORDER_STEP`.
  The client uses these when it sends `order`. The server uses the "end" and "empty" formulas when it creates a column or card (`POST` endpoints), so new items are always appended.
- **Rationale:** One set of constants prevents the frontend and backend from drifting, and midpoint insertion updates only the moved row.
- **RevoTask example:** dragging a card between orders `1024.0` and `2048.0` sends `{"column_id": "...", "order": 1536.0}` to `PATCH /api/cards/<id>/position`.

### BE-ORD-02 Server validation and rebalance
- **Rule:** The service accepts the client's `order` after validation (BE-ORD-03). It then sorts the target container's items, inserting the moved item at the position its `order` implies; on an exact tie with a sibling it goes after that sibling. If any two adjacent orders in the container are closer than `MIN_GAP`, the service renumbers the whole container to multiples of `ORDER_STEP` in the same transaction, keeping relative order. The response is the updated item plus `"rebalanced": bool` and `"siblings": [{"id", "order"}]`; `siblings` is empty unless a rebalance happened, in which case it lists every item in the container with its new order.
- **Rationale:** Repeated halving eventually runs out of float precision and produces duplicate orders; returning the new orders lets the client update without refetching.
- **RevoTask example:** after many drags into the same slot, the response has `"rebalanced": true` and siblings numbered `1024.0, 2048.0, 3072.0, ...`.

### BE-ORD-03 Move validation
- **Rule:** `CardPositionSchema` validates `column_id` (UUID) and `order` (positive float). The service verifies the target column exists and belongs to the same board as the card (otherwise 422), and that the user may move cards on that board (BE-AZ-02). Moving within the same column is allowed. `PATCH /api/boards/<id>/columns/reorder` uses `ColumnReorderSchema` (`column_id`, `order`) with the same rules. Moving a card into a column with `is_done = true` sets `completed_at`; moving it out clears it (see `database.md` → Done columns). At most one column per board may be flagged done.
- **Rationale:** Cards must not jump between boards, and "completed this week" analytics depend on `completed_at`.
- **RevoTask example:** moving a card to a column on another board returns 422 with `details: {"column_id": ["Column belongs to a different board."]}`.

---

## 7. Analytics

### BE-ANL-01 Definitions and response shape
- **Rule:** `GET /api/boards/<id>/analytics` (Admin of that board only) returns:
  `{"week_start": "<ISO>", "cards_per_column": [{"column_id", "name", "total_cards"}], "completed_this_week": n, "member_activity": [{"user_id", "name", "cards_created", "comments_added", "cards_assigned", "assigned_cards_completed_this_week"}]}`
  - **This week** means Monday 00:00 UTC of the current week up to now.
  - **Completed** means `completed_at` falls in that window (the card is in a column flagged `is_done`).
  - **Member activity** covers only current members and Admins of the board, and every figure comes from SQLAlchemy joins on existing tables. No activity-log table.
  - Columns with zero cards appear with `total_cards: 0`.
  - Soft-deleted cards (BE-SVC-06) are excluded from every figure.
- **Rationale:** Without fixed definitions, generated code invents its own and tests cannot assert numbers.
- **RevoTask example:** a Member who created 3 cards and finished 1 assigned card this week appears as `cards_created: 3`, `assigned_cards_completed_this_week: 1`.

---

## 8. Service layer and data access

### BE-SVC-01 Services own transactions
- **Rule:** Each service function that writes does a single `db.session.commit()` on success and `db.session.rollback()` on any exception, then re-raises a domain error. Routes never commit.
- **Rationale:** Partial writes corrupt ordering, membership, and notification state.
- **RevoTask example:** creating a board and the creator's admin membership happen in one commit; creating a card and its "card assigned" notification happen in one commit.

### BE-SVC-02 No N+1 queries
- **Rule:** Endpoints that return nested data use eager loading (`selectinload` / `joinedload`) and a bounded query count. Lazy loading inside serialization loops is forbidden.
- **Rationale:** N+1 queries make board loads slow as data grows.
- **RevoTask example:** `GET /api/boards/<id>` loads columns and cards with `selectinload(Board.columns).selectinload(Column.cards)`, ordered by `order` and limited to active cards (BE-SVC-06), in a fixed number of queries.

### BE-SVC-03 List endpoints are scoped in the query
- **Rule:** `GET /api/boards` accepts a validated `scope` parameter: `mine` (boards where the user has a membership; default when logged in) or `public` (boards with `is_public = true`; default and only option when anonymous). `scope=mine` without a token returns 401. Scoping is done in SQL, never by filtering in Python.
- **Rationale:** Filtering in Python leaks data on bugs and wastes memory, and the scope keeps "list all boards for the current user" intact.
- **RevoTask example:** a logged-in user calling `GET /api/boards` receives only boards joined through their `board_members` rows.

### BE-SVC-04 Board responses include the viewer's role
- **Rule:** Board payloads include `my_role` (`anonymous`, `guest`, `member`, `admin`), computed by `resolve_board_role`. Board, column, and card payloads also include `created_by` (the creator's user id, or `null`), so the UI can show the own-only delete controls from BE-AZ-04 without a second request; comments already expose `author` (BE-ERR-05). Clients use these for UI decisions and never re-implement the matrix; the server still enforces every action.
- **Rationale:** One source of truth for permissions avoids drift between frontend and backend.
- **RevoTask example:** `GET /api/boards/<id>` returns `"my_role": "member"` for a Member, and each card carries `"created_by": "<user id>"`.

### BE-SVC-05 Assigned tasks
- **Rule:** `GET /api/cards?assignee=me` (`@auth_required`, in the `cards` blueprint) returns non-deleted cards (BE-SVC-06) whose `assignee_id` is the current user, only on boards where the user currently has a `member` or `admin` row, using the BE-ERR-03 envelope. `assignee` is required and accepts only the value `me`; any other value, or a missing `assignee`, returns 422, so there is no endpoint that lists all cards. Each item includes card id, title, column name, board id, board name, and `completed_at`. Optional `board_id` and `done` filters are validated by `AssignedCardsQuerySchema`. Scoping is done in SQL.
- **Rationale:** The scenario requires Members to track their assigned tasks, and the original endpoint list has no way to do it.
- **RevoTask example:** a user removed from a board no longer sees that board's cards in this list.

### BE-SVC-06 Cards are soft-deleted
- **Rule:** `DELETE /api/cards/<id>` sets `cards.deleted_at` to the current UTC time (see `database.md` → Soft delete) and returns 204; it does not remove the row. A soft-deleted card is treated as nonexistent: every card query goes through the model helper `Card.active()`, so the card never appears in board payloads, in `GET /api/cards?assignee=me`, or in analytics (BE-ANL-01), and any request addressing it, or addressing comments on it, returns 404 `NOT_FOUND`. No endpoint restores or lists deleted cards. Deleting a column or board still removes its cards permanently through the cascade, including soft-deleted ones. Notifications about a card deletion are sent exactly as for any card delete (BE-NTF-01).
- **Rationale:** A deleted card stays recoverable by an operator while the API behaves as if it were gone, and one helper prevents queries that forget the filter.
- **RevoTask example:** after a Member deletes their own card, `GET /api/boards/<id>` no longer lists it, `GET /api/cards/<id>/comments` returns 404, and the row still exists in the table with `deleted_at` set.

---

## 9. Notifications

### BE-NTF-01 Triggers are defined in one place
- **Rule:** Notification creation happens only through `notifications/service.py::notify(...)`, called from the originating service within the same transaction. The only triggers are:
  - **Card assigned:** notifies the new assignee.
  - **Comment added:** notifies the card's assignee.
  - **Board activity:** notifies that board's Admins when a card is created, deleted, or moved to a different column. Moving within the same column does not notify.
  - **Membership changed** (added, role changed, removed): notifies the affected user, and the board's other Admins.
  - **Admin deletes someone else's work:** when an Admin deletes a card or column created by another user, that creator is notified with a fixed message such as `Your card "<title>" was deleted by an administrator.` When a board is deleted, every other member and Admin of that board is notified; recipients are collected before the cascade runs.
  A recipient receives at most one notification per event, and the actor is never notified (BE-NTF-02).
- **Rationale:** Scattered notification code causes duplicates and missed events.
- **RevoTask example:** `POST /api/cards/<id>/comments` calls `notify(...)` once for the assignee, inside the comment service.

### BE-NTF-02 No self-notifications; read state is owner-scoped
- **Rule:** The actor is never notified of their own action. `PATCH /api/notifications/<id>/read` only works on the current user's own notifications; someone else's returns 404.
- **Rationale:** Self-notifications are noise, and cross-user reads leak activity.
- **RevoTask example:** an Admin moving a card to another column does not receive a notification for it; the board's other Admins do.

### BE-NTF-03 Notification payload and retention
- **Rule:** A notification is returned as `{"id", "type", "message", "board_id", "is_read", "created_at"}`. `type` is one of `card_assigned`, `comment_added`, `card_created`, `card_moved`, `card_deleted`, `column_deleted`, `board_deleted`, `member_added`, `member_role_changed`, `member_removed`. `message` is stored text, written when the notification is created, so it stays readable after the card, column, or board is gone (see `database.md` → Notification retention). `GET /api/notifications` returns the BE-ERR-03 envelope plus `unread_count`, the total number of unread notifications for the user across all pages, so a client can show a badge without loading every page. `PATCH /api/notifications/<id>/read` returns the updated notification with 200 and is idempotent.
- **Rationale:** A notification about a deletion is useless if it disappears with the thing deleted.
- **RevoTask example:** after an Admin deletes a Member's card, that Member's `GET /api/notifications` still lists `{"type": "card_deleted", "message": "Your card \"Fix login\" was deleted by an administrator."}`.

---

## 10. Security and configuration

### BE-SEC-01 Secrets come from the environment
- **Rule:** `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`, and `CORS_ORIGINS` are read from environment variables through a config class. No secrets or default production values in source. Provide `.env.example` with placeholders only.
- **Rationale:** Committed secrets are compromised secrets.
- **RevoTask example:** `JWT_SECRET_KEY` is loaded from `os.environ`; the app refuses to start in production if it is missing.

### BE-SEC-02 Restricted CORS
- **Rule:** CORS allows only the origins in `CORS_ORIGINS`, never `*` in production.
- **Rationale:** Wildcard CORS lets any site call the API with a user's credentials.
- **RevoTask example:** only the deployed RevoTask frontend origin and `http://localhost:3000` are allowed.

### BE-SEC-03 Parameterized queries only
- **Rule:** Use SQLAlchemy expressions or bound parameters. Never build SQL with f-strings or string concatenation.
- **Rationale:** String-built SQL enables injection.
- **RevoTask example:** the analytics join uses `select(...).join(...).where(Board.id == board_id)`, not `f"... WHERE board_id = '{board_id}'"`.

---

## 11. Testing

### BE-TST-01 Test setup
- **Rule:** Use pytest with an app-factory fixture, an isolated test database per run, and fixtures for: `anonymous_client`, `guest_client` (logged in, no membership), `member_client`, `other_member_client`, `admin_client` (Admin of the test board), and `outside_admin_client` (Admin of a different board). Tests never depend on each other's data or ordering.
- **Rationale:** Isolated tests are reproducible and make failures traceable.
- **RevoTask example:** `conftest.py` creates one public board and one private board, with memberships set up for each fixture.

### BE-TST-02 Minimum coverage per endpoint
- **Rule:** Every endpoint has at least: one success test, one validation failure (422) where it accepts input, and one authentication failure (401) if protected. Assert both the status code and the error `code`.
- **Rationale:** These three cases catch the most common AI-generated omissions.
- **RevoTask example:** `PATCH /api/cards/<id>/position` is tested with a valid move (200), `order: 0` (422), and no token (401).

### BE-TST-03 Role and ownership matrix tests
- **Rule:** Every role-sensitive endpoint has a test per applicable cell in the BE-AZ-02 matrix, following the BE-AZ-03 check order, including: private-board non-member (404), cross-board isolation (`outside_admin_client` gets 403 on a public board and 404 on a private one), and the foreign-card case (409) for column deletes.
- **Rationale:** The matrix is only trustworthy if each cell is exercised.
- **RevoTask example:** `DELETE /api/columns/<id>` is tested for: Anonymous 401, Guest 403, `outside_admin_client` 403, Member non-creator 403, Member creator with only own cards 204, Member creator with another member's card 409, Admin 204. `DELETE /api/cards/<id>` is tested for: Anonymous 401, Guest 403, Member non-creator 403, Member creator 204 (even with another member's comment on it), Admin 204. `DELETE /api/comments/<id>` also tests Admin non-author 403.

### BE-TST-04 Flows that cross endpoints
- **Rule:** Include tests for:
  - Creating a board makes the creator its Admin.
  - An Admin adds a Guest as Member and that user can then create a card.
  - Demoting or removing the last Admin returns 409 `LAST_ADMIN`.
  - Removing a Member revokes their write access immediately and clears their card assignments.
  - An Admin deleting another member's card notifies that member, and the notification is still readable after the card is gone.
  - Moving a card within its column creates no notification; moving it to another column does.
  - A position that collides with a sibling or leaves a gap under `MIN_GAP` triggers a rebalance and returns `"rebalanced": true`.
  - `GET /api/cards?assignee=me` excludes boards the user was removed from, and returns 422 without `assignee=me`.
  - A malformed UUID in a path returns 404; an email differing only by case logs in successfully.
  - Deleting a card soft-deletes it: the row keeps `deleted_at`, and the card disappears from the board payload, `GET /api/cards?assignee=me`, and analytics; its comments return 404; a Member's column delete ignores a soft-deleted card that belongs to someone else; an Admin deleting the column removes soft-deleted cards too.
- **Rationale:** These flows are where per-board roles, ordering, and notifications break, and no single-endpoint test covers them.
- **RevoTask example:** after `POST /api/boards`, `GET /api/boards/<id>` returns `"my_role": "admin"` for the creator.
