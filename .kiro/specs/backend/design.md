# Design Document: RevoTask Backend API

Version: V2 (see `CHANGELOG.md`)

## Overview

This document designs the Flask REST API of RevoTask for all 24 requirements in `requirements.md` (V2). The API consumes the existing database layer and defines no table, constraint, index or migration:

| Existing module | Used for |
|-----------------|----------|
| `app/extensions.py` (`db`, `migrate`) | Session and metadata. This design adds `jwt = JWTManager()`. |
| `app/models/*` (`User`, `Board`, `BoardMember`, `BoardColumn`, `Card`, `Comment`, `Notification`, `ActivityLog`) | All persistence. `SoftDeleteMixin.soft_delete()` implements every delete except member removal. |
| `app/models/queries.py` (`load_board`, `card_counts_per_column`, `completed_this_week`, `member_activity`, `my_tasks`, `search_cards`, `notifications_page`, `week_bounds_utc`) | Board load (Req 5, 22), analytics (Req 15), My Tasks and search (Req 11), notification pages (Req 13). The services call them and do not copy them. |
| `app/db_config.py` (`normalize_database_url`, `engine_options`, `verify_connection`) | Connection handling. Unchanged. |
| `app/__init__.py` (`create_app(verify_db=True)`, `skip_empty_revision`) | Extended in place. The signature does not change. |
| `tests/database/conftest.py` (`database_url`, `app`, `engine`, `FIELD_REGISTRY`, strategies) | Reused by `tests/api/`. |

### Key design decisions

Decisions marked **(new)** fill a gap that the requirements leave open.

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Each blueprint has `routes.py` (HTTP only), `service.py` (rules and queries), `schema.py` (Marshmallow). Cross-blueprint helpers live in `app/common/`. | Requirement 20.5. |
| D2 | Authentication is an explicit decorator, `@protected`, on each route, not a global `before_request`. | A public route is visible in the code and in the OpenAPI document. An unmatched path never reaches auth, so 404 stays 404 (Req 18.4). |
| D3 | Every route that takes a path id follows one fixed sequence: `@protected` (401), `get_*_for_user` (404 then 403), role checks (403), schema load (400), service action (400/404/409). The sequence is the check order of Req 17.4. | Validation runs after existence and permission without any route re-ordering its own checks. |
| D4 | Path ids are declared as default string converters (`<id>`), not `<uuid:id>`, and parsed by `parse_uuid()` after authentication. | With the `uuid` converter, an invalid UUID would be a routing 404 before authentication runs, which breaks "401 first" (Req 17.4). |
| D5 | Each access helper loads the record, its board id and the caller's role in one joined query (`outerjoin(BoardMember)`). No row means 404. A row with role `NULL` means 403. | One query separates 404 from 403 with no extra lookup. For board reads the helper selects only `Board.id` and `role`, so `load_board` can run its own three queries (Req 22.2). |
| D6 | Services call `commit_or_conflict()` once at the end. Activity rows and notifications are added to the same session before it. Any exception reaches the error handler, which rolls back. | One transaction per request (Req 14.5, 14.6, 4.5). |
| D7 | Order-sensitive and membership-changing writes first lock the board row with `SELECT ... FOR UPDATE` (`lock_board`). | Serializes "max order + 1", rebalancing and the "last admin" check under concurrency. |
| D8 | Float ordering uses one pure function, `plan_move`, for columns and cards. | One tested algorithm, and a clean target for property tests (Req 8, 10). |
| D9 | **(new)** Login returns `{access_token, token_type, expires_in, user: {id, name, email}}`. The token field is `access_token`. | The requirements name the parts and not the keys. A nested `user` keeps the "no other User field" rule easy to see. |
| D10 | **(new)** Schemas that the requirements say reject unknown fields (register, `PATCH /users/me`, card create, card update) use `StrictSchema` (`unknown=RAISE`). All other request schemas use `LenientSchema` (`unknown=EXCLUDE`). | Requirement 17.6: unknown `user_id`, `owner_id` or `created_by` is ignored on the other routes. |
| D11 | **(new)** All text fields use the `Text` field, which also rejects `NUL` and lone surrogates. | `psycopg2` raises on these values, which would give a 500 instead of a 400. |
| D12 | OpenAPI 3.0.3 is generated with `apispec` and `MarshmallowPlugin`. Each route carries a `@document(...)` decorator. The assembler walks `app.url_map`. `apispec-webframeworks` is not used. | The decorator keeps documentation in the owning blueprint, derives path parameters and error responses from the rule, and makes "route without documentation" a startup error (Req 24.18, 24.21). |
| D13 | **(new)** Swagger UI assets come from the `swagger-ui-bundle` package (Swagger UI 4.15.5, see Research). Docs routes are plain `app.add_url_rule` calls, not a Blueprint. | No external host, no tenth blueprint (Req 20.4, 24.5). |
| D14 | **(new)** CORS uses Flask-CORS with compiled, anchored, case-sensitive patterns and `always_send=False`. | Flask-CORS compares plain string origins case-insensitively and can send the header when no `Origin` is present. Requirements 19.2 and 19.5 forbid both. |
| D15 | **(new)** API tests isolate by `TRUNCATE ... CASCADE` before each test, not by a rolled-back outer transaction. | Services commit. Flask-SQLAlchemy's `get_bind` also ignores a session-level `bind`, so the savepoint fixture of `tests/database/conftest.py` does not apply. Real commits also test real rollback behavior. |
| D16 | **(new)** `marshmallow>=3.23,<4`. | The installed version is 3.23. Marshmallow 4 changes field internals that the custom fields override. |
| D17 | **(new)** The Railway pre-deploy and start commands live in `backend/railway.json`. | See Research: Railway marks config-as-code as deprecated. |
| D18 | **(new)** `engine_options()` is merged with `hide_parameters=True` in `create_app`. `MAX_CONTENT_LENGTH` is 1 MiB. | SQLAlchemy error text would otherwise carry bound values into logs (Req 21.3). The size limit bounds request bodies. |
| D19 | **(new)** A database constraint violation maps to 409 for SQLSTATE `23505` and 400 for every other class-23 code (Req 18.5). This replaces the 422 that `database/design.md` suggests for 23514 and 23502. | The backend requirements are the contract. |
| D20 | **(new)** The `<user_id>` of the member routes is resolved after the caller's board membership and role checks. | The caller learns nothing about the member list of a board they may not read. |

### Research findings

- **Flask-CORS matching.** The installed Flask-CORS 6.0.5 matches plain string origins case-insensitively with `casefold()`, and matches compiled `re.Pattern` origins with `pattern.match`. With `always_send=True` and no `Origin` header, it returns the literal origins. D14 uses anchored compiled patterns and `always_send=False`. This was read from the installed `flask_cors/core.py`.
- **Swagger UI assets.** `swagger-ui-bundle` 1.1.0 ships the static files of Swagger UI 4.15.5 and exposes the directory as `swagger_ui_bundle.swagger_ui_path` ([PyPI](https://pypi.org/project/swagger-ui-bundle/)). That version renders OpenAPI 3.0 documents, so the API emits `3.0.3`. `flask-swagger-ui` is not used because it registers a Blueprint.
- **apispec.** `apispec` 6.10.1 supports OpenAPI 3 and `MarshmallowPlugin`; the project's `main` branch dropped marshmallow 3 ([apispec repository](https://github.com/marshmallow-code/apispec)). The pin `apispec[marshmallow]>=6.8,<7.0` stays on the 6.x line that still supports marshmallow 3 (D16).
- **Railway.** Config as Code (`railway.json`) is deprecated and keeps working for existing services until 2026-12-01. `deploy.preDeployCommand` is an array of commands ([Railway reference](https://docs.railway.com/reference/config-as-code), [deprecation notice](https://docs.railway.com/config-as-code)). The file satisfies Requirements 20.6 and 20.8 and is testable. After the cutoff, the same three values (start command, pre-deploy command, health check path) must be set on the service in the Railway dashboard. This is an open point.
- **Flask-JWT-Extended.** The `unauthorized_loader`, `invalid_token_loader`, `expired_token_loader` and `user_lookup_error_loader` callbacks let the API return its own 401 envelope. Registering `user_lookup_loader` makes a token whose subject is not a User fail with a lookup error, which D2's callback turns into 401.

*Content was rephrased for compliance with licensing restrictions.*

## Architecture

```mermaid
flowchart LR
    C[Client or Swagger UI] -->|HTTP JSON| CORS[Flask-CORS]
    CORS --> R[Flask routing]
    R -->|no match 404, wrong method 405| EH[Error handlers]
    R --> RT[routes.py]
    RT -->|@protected| AU[common/auth.py]
    RT -->|get_x_for_user| AC[common/access.py]
    RT -->|load_body, load_query| SC[schema.py and common/validation.py]
    RT --> SV[service.py]
    SV --> EV[common/events.py]
    SV --> OR[common/ordering.py]
    SV --> Q[models/queries.py]
    SV --> M[models/*]
    M --> PG[(PostgreSQL 18)]
    RT -->|ok + Schema.dump| EN[common/envelope.py]
    EH --> EN
    CA[create_app] --> R
    CA --> OA[common/openapi.py]
    OA -->|GET /api/docs, /api/openapi.json, /swagger-ui/*| C
```

### Request lifecycle

```mermaid
sequenceDiagram
    participant Cl as Client
    participant Rt as routes.py
    participant Au as @protected
    participant Ac as access.py
    participant Sc as schema.py
    participant Sv as service.py
    participant Db as PostgreSQL
    Cl->>Rt: PATCH /api/cards/{id} + Bearer token
    Rt->>Au: verify JWT, load User
    Au-->>Cl: 401 if token or user invalid
    Rt->>Ac: get_card_for_user(user.id, id)
    Ac->>Db: one joined SELECT
    Ac-->>Cl: 404 no live record, 403 not a member
    Rt->>Sc: load_body(CardUpdateSchema)
    Sc-->>Cl: 400 field errors
    Rt->>Sv: update_card(user, access, data)
    Sv->>Db: UPDATE, INSERT activity and notifications
    Sv-->>Cl: 400 assignee, 409 conflict
    Sv->>Db: COMMIT (commit_or_conflict)
    Rt-->>Cl: 200 {"data": CardOutSchema.dump(card)}
```

### Check order (Requirement 17.4)

| Step | Check | Status | Implemented in |
|------|-------|--------|----------------|
| 0 | No route for the path, or method not allowed | 404, 405 | Flask routing and `errors.py` handlers. No route code runs. |
| 1 | Authentication: header form, signature, expiry, subject is an existing User | 401 | `@protected` and the JWT callbacks in `common/auth.py` |
| 2 | Record existence: id is a UUID, the record and its Column and Board ancestors have `deleted_at` null | 404 | `get_board_for_user`, `get_column_for_user`, `get_card_for_user`, `get_comment_for_user` in `common/access.py`; `notifications.service.mark_read` |
| 3 | Board membership and Role: caller is a member; admin-only routes; owner-only routes | 403 | Same helpers (membership), then `require_admin`, `require_admin_or_self`, `require_card_deleter`, `require_comment_owner` in `common/access.py` |
| 4 | Request validation: JSON object, Marshmallow load, then rules that need the database (assignee is a member) | 400 | `load_body` / `load_query` in `common/validation.py` with the blueprint's `schema.py`; domain checks in `service.py` |
| 5 | Lookups driven by body values, then uniqueness and state conflicts | 404, 409 | `service.py`; unique indexes map through `commit_or_conflict` |

Step 5 holds three lookups whose key arrives in the body or in a sub-path id: `column_id` of the reorder body (Req 8.4), `column_id` of the move body (Req 10.6) and the `email` of add member (Req 6.3). They follow validation, because the key must be valid before it can be looked up. The `<user_id>` path segment of the member routes follows D20.

## Components and Interfaces

### Directory layout

```
backend/
  app/
    __init__.py            create_app (extended)
    config.py              Settings, load_settings, parse_cors_origins, parse_swagger_enabled
    extensions.py          db, migrate (existing) + jwt
    db_config.py, seed.py, models/      unchanged
    common/
      __init__.py
      constants.py         Role, ActivityAction, NotificationType, limits, MIN_GAP
      errors.py            ApiError family, register_error_handlers
      envelope.py          ok(), error_response(), format_field_errors()
      validation.py        Text, Email, StrictUUID, OrderValue, StrictBoolean, DigitsInt, UTCDateTime,
                           StrictSchema, LenientSchema, parse_uuid, load_body, load_query
      schemas.py           shared response schemas: IdOutSchema, AuthorOutSchema, ColumnOutSchema, CardOutSchema
      auth.py              protected, current_user, register_jwt_callbacks, hash_password, verify_password
      access.py            BoardAccess and friends, get_*_for_user, require_*
      db.py                commit_or_conflict, lock_board
      ordering.py          MIN_GAP, next_order, plan_move, MovePlan
      events.py            log_activity, create_notification, fit_message
      openapi.py           document, build_openapi, register_docs, OpenAPIError
    blueprints/
      __init__.py          ALL_BLUEPRINTS, register_blueprints
      auth/ users/ boards/ columns/ cards/ comments/ notifications/ analytics/ health/
        __init__.py        empty package marker
        routes.py          bp = Blueprint("<name>", __name__) and the route functions
        service.py
        schema.py
  tests/
    conftest.py            new: sets JWT_SECRET_KEY default for every test module
    database/              existing
    api/                   new
  .coveragerc, railway.json, .env.example, requirements.txt
```

`blueprints/*/` holds the 3 required files and an empty `__init__.py`, so Requirement 20.4's 27 files are present (the marker is not counted). Blueprint names equal the OpenAPI tag names, and `rule.endpoint.split(".")[0]` is the tag of an operation. Rules carry full paths (`"/api/boards/<id>/columns"`), no `url_prefix`, because `columns` owns paths under two prefixes (Requirement 24 assumptions).

### `create_app` changes (`app/__init__.py`)

```python
def create_app(verify_db: bool = True) -> Flask:
    load_dotenv(BACKEND_DIR / ".env", override=False)          # process env wins (Req 20.9, 20.1)
    app = Flask(__name__)
    uri = normalize_database_url(os.environ.get("DATABASE_URL"))   # existing: raises before any engine
    settings = load_settings(os.environ)                       # raises RuntimeError naming JWT_SECRET_KEY (Req 20.3)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=uri,
        SQLALCHEMY_ENGINE_OPTIONS={**engine_options(), "hide_parameters": True},   # D18
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=settings.jwt_secret_key,
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(seconds=settings.jwt_access_token_expires),
        MAX_CONTENT_LENGTH=1_048_576,
    )
    db.init_app(app); migrate.init_app(app, db, ...unchanged...)
    jwt.init_app(app); register_jwt_callbacks(jwt)
    CORS(app, resources={r"/*": {"origins": compile_origins(settings.cors_origins),
                                 "methods": ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
                                 "allow_headers": ["Authorization", "Content-Type"],
                                 "supports_credentials": False, "always_send": False}})
    register_error_handlers(app)
    from app import models                                      # noqa: F401
    register_blueprints(app)                                    # 9 blueprints
    if settings.swagger_enabled:
        register_docs(app)                                      # builds the document, then adds 3 URL rules
    app.cli.add_command(seed_command)
    if verify_db:
        with app.app_context(): verify_connection(db.engine)
    return app
```

Order matters in two places. `DATABASE_URL` is checked before `JWT_SECRET_KEY`, so the existing database tests for blank `DATABASE_URL` keep passing. Both checks happen before `db.init_app`, so no engine exists when either fails. `register_docs` runs after `register_blueprints` so the assembler sees every `/api/` rule.

`tests/conftest.py` sets `os.environ.setdefault("JWT_SECRET_KEY", "test-secret-not-for-production-0123456789")` at import time. Without it, the existing `app` fixture in `tests/database/conftest.py` would fail on the new check.

### `app/config.py`

```python
@dataclass(frozen=True)
class Settings:
    jwt_secret_key: str
    jwt_access_token_expires: int          # seconds
    cors_origins: tuple[str, ...]
    swagger_enabled: bool

def parse_cors_origins(raw: str | None) -> tuple[str, ...]:
    """Split on ',', strip each entry, drop empty ones; ('http://localhost:3000',) when none remain (Req 19.1)."""
def parse_swagger_enabled(raw: str | None) -> bool:
    """False only when raw.strip().casefold() == 'false' (Req 24.1)."""
def parse_expires(raw: str | None) -> int:
    """3600 when unset or empty; RuntimeError naming JWT_ACCESS_TOKEN_EXPIRES unless a positive decimal integer."""
def load_settings(env: Mapping[str, str]) -> Settings:
    """RuntimeError('JWT_SECRET_KEY is not set or is empty') when missing or blank (Req 20.3)."""
def compile_origins(origins: Iterable[str]) -> list[re.Pattern]:
    """re.compile(re.escape(o) + r'\\Z'): exact and case-sensitive (D14)."""
```

### Common modules

**`errors.py`**

```python
class ApiError(Exception):
    status: int; message: str
class Unauthorized(ApiError): status = 401
class Forbidden(ApiError):    status = 403
class NotFound(ApiError):     status = 404
class Conflict(ApiError):     status = 409
class ValidationFailed(ApiError):          # status 400; message built by format_field_errors
    def __init__(self, errors: Mapping[str, Any] | str): ...

def register_error_handlers(app: Flask) -> None
```

Handlers, from most to least specific:

| Handler | Result |
|---------|--------|
| `ApiError` | `error_response(e.status, e.message)` |
| `IntegrityError` | rollback; `pgcode == "23505"` gives 409 `"Resource already exists"`, any other gives 400 `"Request violates a data constraint"`. No SQL text (Req 18.5). |
| `HTTPException` | `error_response(e.code, <fixed text per code>)`: 404 `"Resource not found"`, 405 `"Method not allowed"`, 413 `"Request body too large"`, otherwise `e.name`. |
| `Exception` | rollback; `app.logger.exception("Unhandled exception")`; 500 with the constant `"Internal server error"` (Req 18.6). |

**`envelope.py`**

```python
def ok(payload: Any, status: int = 200) -> Response            # jsonify({"data": payload}), status
def error_response(status: int, message: str) -> Response      # jsonify({"error": message}), status
def format_field_errors(messages: Mapping[str, Any]) -> str
    # one "<field>: <message>" entry per leaf error, fields sorted, nested keys joined with ".",
    # the "_schema" key renders as the bare message, entries joined with "; " (Req 18.7)
```

**`auth.py`**

```python
def hash_password(raw: str) -> str                  # werkzeug.security.generate_password_hash (salted)
def verify_password(stored_hash: str | None, raw: str) -> bool
    # checks against DUMMY_HASH when stored_hash is None, so unknown email costs the same as a wrong password
def protected(fn: F) -> F                           # @jwt_required() + sets fn.__protected__ = True
def current_user() -> User                          # the User loaded by the JWT user_lookup_loader
def register_jwt_callbacks(jwt: JWTManager) -> None
    # user_lookup_loader: db.session.get(User, UUID(sub)); None for a bad subject
    # unauthorized_loader, invalid_token_loader, expired_token_loader, user_lookup_error_loader,
    # revoked_token_loader: every one returns error_response(401, "Authentication required")
```

`protected` sits below `@document` and above the view, so `functools.wraps` carries the marker to the function that Flask registers. Tokens are created with `create_access_token(identity=str(user.id))`. A token with a subject that is not a UUID, or not an existing User, fails the lookup and gives 401. The Authorization header is never logged.

**`access.py`** (the helpers of Requirement 17)

```python
@dataclass(frozen=True)
class BoardAccess:   board_id: UUID; role: str; is_admin: bool
@dataclass(frozen=True)
class ColumnAccess:  column: BoardColumn; board_id: UUID; role: str; is_admin: bool
@dataclass(frozen=True)
class CardAccess:    card: Card; board_id: UUID; role: str; is_admin: bool
@dataclass(frozen=True)
class CommentAccess: comment: Comment; card: Card; board_id: UUID; role: str; is_admin: bool

def get_board_for_user(user_id: UUID, raw_id: str) -> BoardAccess      # 404 / 403
def get_column_for_user(user_id: UUID, raw_id: str) -> ColumnAccess
def get_card_for_user(user_id: UUID, raw_id: str) -> CardAccess
def get_comment_for_user(user_id: UUID, raw_id: str) -> CommentAccess
def require_admin(access) -> None                               # Forbidden unless role == "admin"
def require_admin_or_self(access: BoardAccess, user_id: UUID, target: UUID) -> None
def require_card_deleter(access: CardAccess, user_id: UUID) -> None      # creator or admin
def require_comment_owner(access: CommentAccess, user_id: UUID) -> None  # owner only, admins included
```

Every `get_*_for_user` runs the same shape of query. For a card:

```python
select(Card, Board.id, BoardMember.role)
  .join(BoardColumn, Card.column_id == BoardColumn.id)
  .join(Board, BoardColumn.board_id == Board.id)
  .outerjoin(BoardMember, and_(BoardMember.board_id == Board.id, BoardMember.user_id == user_id))
  .where(Card.id == card_id, Card.deleted_at.is_(None),
         BoardColumn.deleted_at.is_(None), Board.deleted_at.is_(None))
```

`parse_uuid(raw)` runs first and raises `NotFound` for anything that is not a canonical 36-character UUID. No row raises `NotFound`; a row with `role is None` raises `Forbidden`. `get_board_for_user` selects `(Board.id, BoardMember.role)` only, never the `Board` entity (D5).

**`db.py`**

```python
def lock_board(board_id: UUID) -> None
    # select(Board.id).where(Board.id == board_id).with_for_update() (D7)
def commit_or_conflict() -> None
    # db.session.commit(); on IntegrityError: rollback, then Conflict for 23505, ValidationFailed for other class-23
```

**`ordering.py`**

```python
MIN_GAP = 1e-6

def next_order(existing: Iterable[float]) -> float
    """max(existing) + 1.0, or 1.0 when empty (Req 7.1, 9.1)."""

@dataclass(frozen=True)
class MovePlan:
    rebalanced: bool
    orders: dict[UUID, float]      # new order of every row whose value must be written, moved row included

def plan_move(siblings: Sequence[tuple[UUID, float]], moved_id: UUID, requested: float) -> MovePlan
```

`siblings` are the Live_Record rows of the same parent (Board or Column) **without** the moved row. The algorithm is the same for columns and cards.

1. If `abs(o - requested) >= MIN_GAP` for every sibling `o` (not only the neighbours), return `MovePlan(False, {moved_id: requested})`. Nothing else changes.
2. Otherwise sort the siblings by `(order, id)`. Let `i = bisect_right([o for _, o in sorted], requested)`. The moved row goes at index `i`, so it lands after every sibling with an equal order (the tie rule of Req 8.2 and 10.4) and before every greater one.
3. Number the resulting sequence `1.0, 2.0, ..., N` and return `MovePlan(True, orders)`.

The caller writes only the rows whose value changed, then returns the parent's rows sorted by `order`. Soft-deleted siblings are never read or written. A float comparison against `1e-6` uses the stored double, so a request that differs from a sibling by exactly `1e-6` is not a conflict.

**`events.py`** (Requirement 14)

```python
def log_activity(board_id: UUID, user_id: UUID, action: ActivityAction, card_id: UUID | None = None) -> None
def create_notification(user_id: UUID, board_id: UUID, type_: NotificationType, message: str,
                       card_id: UUID | None = None) -> None
def fit_message(render: Callable[[str], str], title: str, limit: int = 500) -> str
    """render(title) when it fits; otherwise truncate the title and end it with '…' so len(result) <= limit (Req 14.7)."""

def message_card_assigned(title: str) -> str      # 'You were assigned to "<title>"'
def message_card_moved(title: str, column_title: str) -> str   # '"<title>" was moved to "<column_title>"'
def message_comment_added(title: str) -> str      # 'New comment on "<title>"'
def message_member_added(board_name: str) -> str  # 'You were added to board "<board_name>"'
```

Both write helpers only call `db.session.add`. They do not flush or commit, so they share the transaction of the caller. `fit_message` guarantees `1 <= len(message) <= 500`.

**`openapi.py`** is described in [OpenAPI generation](#openapi-generation).

### Blueprint modules

Every `routes.py` follows this template. The decorator order is fixed: route, `document`, `protected`.

```python
bp = Blueprint("cards", __name__)

@bp.patch("/api/cards/<id>")
@document(summary="Update a card", request=CardUpdateSchema, success=CardOutSchema, conflict=False)
@protected
def update_card(id: str):
    user = current_user()
    access = get_card_for_user(user.id, id)                     # 404, 403
    data = load_body(CardUpdateSchema())                        # 400
    card = service.update_card(user, access, data)              # 400, 409, commit
    return ok(CardOutSchema().dump(card))
```

`routes.py` contains no query. `service.py` never imports `flask.request`. `schema.py` never touches `db`. A test (see Testing Strategy) checks the three rules by static scan.

### Route table (traceability: route to file, function and schema)

Legend for the *Access* column: `B` = `get_board_for_user`, `C` = `get_column_for_user`, `K` = `get_card_for_user`, `M` = `get_comment_for_user`, `A` = then `require_admin`, `—` = none. Service functions are in `blueprints/<bp>/service.py`, schemas in `blueprints/<bp>/schema.py` unless the schema is listed in `common/schemas.py` (marked `*`).

| # | Route | Blueprint, `routes.py` function | Access (404, 403) | Request schema | `service.py` function | Success (status, schema) | Requirements |
|---|-------|----------------------------------|-------------------|----------------|------------------------|---------------------------|--------------|
| 1 | POST /api/auth/register | auth, `register` (public) | — | `RegisterSchema` | `register_user` | 201 `RegisterOutSchema` | 1.1 to 1.7, 21.1, 21.2 |
| 2 | POST /api/auth/login | auth, `login` (public) | — | `LoginSchema` | `login` | 200 `LoginOutSchema` | 2.1 to 2.5, 21.5 |
| 3 | GET /api/users/me | users, `get_me` | — | — | `get_profile` | 200 `ProfileOutSchema` | 3.1 |
| 4 | PATCH /api/users/me | users, `update_me` | — | `ProfileUpdateSchema` | `update_profile` | 200 `ProfileOutSchema` | 3.2 to 3.6 |
| 5 | POST /api/boards | boards, `create_board` | — | `BoardCreateSchema` | `create_board` | 201 `BoardOutSchema` | 4.1, 4.2, 4.5 |
| 6 | GET /api/boards | boards, `list_boards` | — | — | `list_boards` | 200 `BoardOutSchema[]` | 4.3, 4.4 |
| 7 | GET /api/boards/{id} | boards, `get_board` | B | — | `get_board_detail` | 200 `BoardDetailOutSchema` | 5.1, 5.2, 22.1, 22.2 |
| 8 | PATCH /api/boards/{id} | boards, `rename_board` | B, A | `BoardUpdateSchema` | `rename_board` | 200 `BoardOutSchema` | 5.3, 5.4, 5.6 |
| 9 | DELETE /api/boards/{id} | boards, `delete_board` | B, A | — | `delete_board` | 200 `IdOutSchema*` | 5.5, 5.6 |
| 10 | GET /api/boards/{id}/members | boards, `list_members` | B | — | `list_members` | 200 `MemberOutSchema[]` | 6.1 |
| 11 | POST /api/boards/{id}/members | boards, `add_member` | B, A | `MemberAddSchema` | `add_member` | 201 `MemberOutSchema` | 6.2 to 6.5, 6.11, 14.4, 14.7 |
| 12 | PATCH /api/boards/{id}/members/{user_id} | boards, `change_member_role` | B, A, then target (404) | `MemberRoleSchema` | `change_member_role` | 200 `MemberOutSchema` | 6.6, 6.9 to 6.12 |
| 13 | DELETE /api/boards/{id}/members/{user_id} | boards, `remove_member` | B, `require_admin_or_self`, then target (404) | — | `remove_member` | 200 `MemberRemovedOutSchema` | 6.7 to 6.11 |
| 14 | POST /api/boards/{id}/columns | columns, `create_column` | B | `ColumnCreateSchema` | `create_column` | 201 `ColumnOutSchema*` | 7.1, 7.3 |
| 15 | PATCH /api/columns/{id} | columns, `rename_column` | C | `ColumnUpdateSchema` | `rename_column` | 200 `ColumnOutSchema*` | 7.2, 7.3 |
| 16 | DELETE /api/columns/{id} | columns, `delete_column` | C | — | `delete_column` | 200 `IdOutSchema*` | 7.4 |
| 17 | PATCH /api/boards/{id}/columns/reorder | columns, `reorder_columns` | B | `ColumnReorderSchema` | `reorder_columns` | 200 `ColumnReorderOutSchema` | 8.1 to 8.4 |
| 18 | POST /api/columns/{id}/cards | cards, `create_card` | C | `CardCreateSchema` | `create_card` | 201 `CardOutSchema*` | 9.1, 9.6, 9.7, 14.1, 14.4, 14.7 |
| 19 | GET /api/cards | cards, `list_cards` | — | `CardListQuerySchema` | `list_my_tasks`, `search` | 200 `TaskGroupOutSchema[]` or `CardOutSchema[]` | 11.1 to 11.5 |
| 20 | PATCH /api/cards/{id} | cards, `update_card` | K | `CardUpdateSchema` | `update_card` | 200 `CardOutSchema*` | 9.2 to 9.7, 9.10, 14.1 |
| 21 | DELETE /api/cards/{id} | cards, `delete_card` | K, `require_card_deleter` | — | `delete_card` | 200 `IdOutSchema*` | 9.8, 9.9 |
| 22 | PATCH /api/cards/{id}/position | cards, `move_card` | K | `CardPositionSchema` | `move_card` | 200 `CardMoveOutSchema` | 10.1 to 10.6, 14.2, 14.4 |
| 23 | POST /api/cards/{id}/comments | comments, `create_comment` | K | `CommentSchema` | `create_comment` | 201 `CommentOutSchema` | 12.1, 12.2, 14.3, 14.4, 14.7 |
| 24 | GET /api/cards/{id}/comments | comments, `list_comments` | K | — | `list_comments` | 200 `CommentOutSchema[]` | 12.3 |
| 25 | PATCH /api/comments/{id} | comments, `update_comment` | M, `require_comment_owner` | `CommentSchema` | `update_comment` | 200 `CommentOutSchema` | 12.2, 12.4, 12.6 |
| 26 | DELETE /api/comments/{id} | comments, `delete_comment` | M, `require_comment_owner` | — | `delete_comment` | 200 `IdOutSchema*` | 12.5, 12.6 |
| 27 | GET /api/notifications | notifications, `list_notifications` | — | `NotificationListQuerySchema` | `list_notifications` | 200 `NotificationPageOutSchema` | 13.1 to 13.4 |
| 28 | PATCH /api/notifications/{id}/read | notifications, `mark_read` | own-record lookup in `mark_read` (404 for another user's) | — | `mark_read` | 200 `NotificationOutSchema` | 13.5 to 13.7 |
| 29 | GET /api/boards/{id}/analytics | analytics, `get_analytics` | B, A | — | `get_analytics` | 200 `AnalyticsOutSchema` | 15.1 to 15.6, 22.3 |
| 30 | GET /api/health | health, `health` (public) | — | — | `get_status` | 200 `HealthOutSchema` | 16.1, 16.2 |
| — | GET /api/docs, GET /api/openapi.json, GET /swagger-ui/{filename} | registered by `create_app` through `register_docs`, not a Blueprint | — | — | `docs_page`, `openapi_json`, `swagger_asset` in `common/openapi.py` | HTML, raw JSON, static file | 24.1 to 24.8, 24.21 |
| — | `create_app` and error handlers | `app/__init__.py`, `common/errors.py` | — | — | — | — | 17 to 20, 24 (cross-cutting) |

Cross-cutting requirements 14.5, 14.6, 17, 18, 19, 20, 21, 22 and 23 apply to every row. [Requirements Traceability](#requirements-traceability) maps each criterion.

### Service behavior notes

**auth.service**

- `register_user(data)` creates the `User` with `hash_password`. The email arrives normalized from the schema (trimmed, lower case). The unique index `uq_users_email_lower` decides concurrent requests: the loser's `IntegrityError` becomes `Conflict` through `commit_or_conflict` (Req 1.7). A pre-check `SELECT` avoids the exception in the common case.
- `login(data)` normalizes the email (trim, lower case), loads the User, and calls `verify_password(user.password_hash if user else None, password)`. A miss or a mismatch raises the same `Unauthorized("Invalid email or password")`. On success it returns `(user, token, expires_in)`.

**boards.service**

- `create_board` inserts `Board(owner_id=user.id)` and `BoardMember(role="admin")` and commits once. Any failure rolls back both (Req 4.5).
- `list_boards` selects `Board`, `BoardMember.role` joined on the caller, `deleted_at is null`, ordered by `Board.updated_at.desc(), Board.id.asc()`.
- `get_board_detail(access)` calls `queries.load_board(access.board_id)`: three queries (D5). It groups cards by `column_id` in a dict and builds plain dicts, so it never touches the lazy `Board.columns` or `BoardColumn.cards` relationships (no N+1).
- `delete_board` calls `board.soft_delete()` on the board only (Req 5.5).
- `add_member`: lock board, look up the User by `lower(email)`, reject an existing membership, insert the `BoardMember`, `log_activity(member_added)`, `create_notification(member_added, card_id=None)`.
- `change_member_role` and `remove_member`: lock board, load the target membership (404), count admins; a change from `admin` or a removal of an `admin` when the admin count is 1 raises `Conflict` before any write (Req 6.9). Removal deletes the `BoardMember` row, runs one bulk `UPDATE cards SET assignee_id = NULL` for live cards of live columns of the board assigned to that user, and logs `member_removed`.

**columns.service**

- `create_column`: lock board, `next_order` over live columns, insert, `log_activity(column_created)`.
- `reorder_columns(access, data)`: lock board, load live columns, find `data["column_id"]` among them (404 otherwise), `plan_move`, write changed rows, re-select sorted columns, return `(columns, plan.rebalanced)`.
- `delete_column` calls `soft_delete()` on the column. Cards keep their own `deleted_at`.

**cards.service**

- `create_card(user, access, data)`: validates `assignee_id` as a board member (400), locks the board, `next_order` over the column's live cards, inserts with `created_by=user.id`, logs `card_created`, notifies the assignee unless it is the caller (`card_assigned`).
- `update_card(user, access, data)` applies only supplied keys. `changed` is true when `title`, `description` or `assignee_id` is supplied with a value different from the stored one. `completed=True` with `completed_at is None` sets `datetime.now(timezone.utc)` and logs `card_completed` once. `completed=True` with a stored value changes nothing. `completed=False` sets `completed_at = None` and logs nothing. `card_updated` is logged once when `changed`. `card_assigned` is created when `assignee_id` becomes a non-null user different from the previous one and from the caller.
- `move_card(user, access, data)`: loads the target column with `column_id` among live columns of the same board (404), locks the board, loads the live siblings of the target column without the moved card, `plan_move`, writes `column_id` and the orders, logs `card_moved` and creates the `card_moved` notification only when the column changed. The result carries `rebalanced` and, when true, `siblings`.
- `delete_card` soft-deletes the card and logs `card_deleted`.
- `list_my_tasks(user)` calls `queries.my_tasks(user.id)` and groups the `(board_id, board_name, Card)` rows with a dict keyed by `board_id` in first-seen order. The query already orders by board name, column order and card order. Grouping by id and not by name keeps two boards with the same name apart (the database design groups by name with `groupby`, which interleaves in that case).
- `search(user, term)` calls `queries.search_cards(term, user_id=user.id)`.

**comments.service**

- `create_comment` inserts `Comment(body=content, user_id=user.id)`, logs `comment_added`, then notifies each distinct non-null user among `card.created_by` and `card.assignee_id` who is not the author and is still a board member (one `IN` query on `board_members`).
- `update_comment` replaces `body`. `delete_comment` soft-deletes. Both require ownership first (step 3).

**notifications.service**

- `list_notifications(user, page, per_page)` calls `queries.notifications_page(user.id, per_page, (page - 1) * per_page)` and a `count(*)`. One more query, `select(Card.id)` over the page's `card_id` values with live-record filters, nulls the `card_id` of any card that is soft-deleted or hidden by a deleted ancestor (the "Card no longer exists" wording of Requirement 13.2 is read as "not a Live_Record", decision 5 below).
- `mark_read(user, raw_id)`: `parse_uuid`, `session.get(Notification, id)`, 404 when missing or `user_id != user.id`, sets `is_read = True` only when false, commits, returns the same shape.

**analytics.service**

- `get_analytics(access)` returns `cards_per_column` from `card_counts_per_column`, `completed_this_week` from `completed_this_week`, and `member_activity` from `member_activity`, all from `queries.py` (Req 15.2).

**health.service**

- `get_status()` returns `{"status": "ok"}` with no database access, so it stays under 1,000 ms when the database is slow (Req 16.2).

## Data Models

No table changes. The API reads and writes the existing models. The mapping from model fields to API fields:

| API field | Source | Notes |
|-----------|--------|-------|
| `comment.content` | `Comment.body` | `fields.String(attribute="body")` on output. |
| `comment.author` | `User.id`, `User.name` | Joined with one query for the list, one lookup for create. |
| `card.column_id` | `Card.column_id` | Only in `CardMoveOutSchema`. |
| `board.role` | `BoardMember.role` | Caller's role. |
| Every timestamp | `timestamptz` columns | `UTCDateTime` converts to UTC and writes `+00:00`. |
| Every id | `UUID` columns | `fields.UUID` writes the lower-case 36-character form. |

### Constants (`common/constants.py`)

```python
class Role(str, Enum):               MEMBER = "member"; ADMIN = "admin"
class ActivityAction(str, Enum):     COLUMN_CREATED = "column_created"; CARD_CREATED = "card_created"; CARD_UPDATED = "card_updated"
                                     CARD_COMPLETED = "card_completed"; CARD_MOVED = "card_moved"; CARD_DELETED = "card_deleted"
                                     COMMENT_ADDED = "comment_added"; MEMBER_ADDED = "member_added"
                                     MEMBER_REMOVED = "member_removed"; MEMBER_ROLE_CHANGED = "member_role_changed"
class NotificationType(str, Enum):   CARD_ASSIGNED = "card_assigned"; CARD_MOVED = "card_moved"
                                     COMMENT_ADDED = "comment_added"; MEMBER_ADDED = "member_added"
NOTIFICATION_MESSAGE_MAX = 500
PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX, OFFSET_MAX = 20, 100, 1_000_000     # equal to queries.py limits
```

### Request validation (`common/validation.py`)

```python
class Text(fields.String):
    """str only. Rejects NUL and values that cannot be encoded as UTF-8 (D11)."""

class Email(Text):
    """Trim, lower-case, then 3..254 characters and marshmallow validate.Email (Req 1.2)."""

class StrictUUID(fields.UUID):
    """str in canonical 8-4-4-4-12 hexadecimal form only. No braces, URN or 32-digit form."""

class OrderValue(fields.Float):
    """JSON number only: a bool or a str is invalid. NaN and infinities are invalid (allow_nan=False).
    validate=Range(min=0, min_inclusive=False). An int too large for float is invalid, not an exception."""

class StrictBoolean(fields.Boolean):
    """isinstance(value, bool) only. 'true', 1 and 'yes' are invalid."""

class DigitsInt(fields.Integer):
    """Query integers: str of 1 to 18 ASCII digits only. No sign, space, point or empty value (Req 13.3)."""

class UTCDateTime(fields.DateTime):
    """Output: value.astimezone(timezone.utc).isoformat(), so the offset is always +00:00 (Req 18.2)."""

class StrictSchema(Schema):   class Meta: unknown = RAISE      # error "<name>: Unknown field." per extra key
class LenientSchema(Schema):  class Meta: unknown = EXCLUDE

def parse_uuid(raw: str) -> UUID                       # NotFound unless canonical UUID
def load_body(schema: Schema) -> dict                  # JSON object or ValidationFailed (400), then schema.load
def load_query(schema: Schema) -> dict                 # request.args; a repeated key is an error for that key
```

`load_body` uses `request.get_json(force=True, silent=True)`. An empty body, invalid JSON and any top-level value that is not an object (array, string, number, boolean, null) all raise `ValidationFailed("Request body must be a JSON object")` (Req 1.6, 18.3). `ValidationFailed` formats `ValidationError.messages` with `format_field_errors`, giving `name: Missing data for required field.; password: Length must be between 8 and 128.`

### Request schemas

```python
# auth/schema.py
class RegisterSchema(StrictSchema):
    name = Text(required=True, validate=Length(1, 255))
    email = Email(required=True)
    password = Text(required=True, validate=Length(8, 128))          # never trimmed

class LoginSchema(LenientSchema):
    email = Text(required=True, validate=Length(min=1))
    password = Text(required=True, validate=Length(min=1))           # the service trims and lower-cases the email

# users/schema.py
class ProfileUpdateSchema(StrictSchema):
    name = Text(validate=Length(1, 255))
    email = Email()
    @validates_schema
    def at_least_one(self, data, **kw):                              # {} gives 400 (Req 3.4)
        if not data: raise ValidationError("Provide name, email or both", "_schema")

# boards/schema.py
class BoardCreateSchema(LenientSchema):  name = Text(required=True, validate=Length(1, 255))
class BoardUpdateSchema(BoardCreateSchema): ...
class MemberAddSchema(LenientSchema):
    email = Email(required=True)
    role = fields.String(validate=OneOf(["member", "admin"]), load_default="member")
class MemberRoleSchema(LenientSchema):   role = fields.String(required=True, validate=OneOf(["member", "admin"]))

# columns/schema.py
class ColumnCreateSchema(LenientSchema): title = Text(required=True, validate=Length(1, 255))
class ColumnUpdateSchema(ColumnCreateSchema): ...
class ColumnReorderSchema(LenientSchema):
    column_id = StrictUUID(required=True)
    order = OrderValue(required=True, validate=Range(min=0, min_inclusive=False))

# cards/schema.py
class CardCreateSchema(StrictSchema):                                # 'order', 'column_id', 'created_by', 'completed' are unknown (Req 9.7)
    title = Text(required=True, validate=Length(1, 255))             # null is "not a string"
    description = Text(allow_none=True, validate=Length(max=10000))
    assignee_id = StrictUUID(allow_none=True)
class CardUpdateSchema(StrictSchema):
    title = Text(validate=Length(1, 255))
    description = Text(allow_none=True, validate=Length(max=10000))
    assignee_id = StrictUUID(allow_none=True)
    completed = StrictBoolean()
    @validates_schema
    def at_least_one(self, data, **kw): ...                          # Req 9.10
class CardPositionSchema(LenientSchema):                             # Req 10.1: validated before the target column is looked up
    column_id = StrictUUID(required=True)
    order = OrderValue(required=True, validate=Range(min=0, min_inclusive=False))
class CardListQuerySchema(LenientSchema):                            # unknown query keys are ignored
    assignee = fields.String(validate=OneOf(["me"]))
    search = Text(validate=Length(1, 200))
    @validates_schema
    def exactly_one(self, data, **kw):                               # none or both: error on 'assignee' and 'search' (Req 11.4)

# comments/schema.py
class CommentSchema(LenientSchema):
    content = Text(required=True, validate=[Length(1, 5000), has_non_whitespace])

# notifications/schema.py
class NotificationListQuerySchema(LenientSchema):
    page = DigitsInt(load_default=1, validate=Range(min=1), metadata={"default": 1})
    per_page = DigitsInt(load_default=20, validate=Range(min=1, max=100), metadata={"default": 20})
    @validates_schema
    def offset_limit(self, data, **kw):                              # (page - 1) * per_page > 1_000_000 -> error on 'page' (Req 13.3)
```

`has_non_whitespace` is `any(not ch.isspace() for ch in value)`. PostgreSQL's `\S` check is the final arbiter: a string that passes here and fails the database constraint returns 400 through `IntegrityError` (D19). Schema errors use field keys, so an `Unknown field.` error names each extra field (Req 1.5, 3.3, 9.7).

### Response schemas

All response schemas live with the blueprint that owns the route, except those used by several blueprints (`common/schemas.py`, marked `*`). Response fields are marked `required=True` where the field is always present, so the OpenAPI `required` list is useful; `dump` ignores the flag.

| Schema | Fields |
|--------|--------|
| `IdOutSchema*` | `id` |
| `AuthorOutSchema*` | `id`, `name` |
| `ColumnOutSchema*` | `id`, `board_id`, `title`, `order`, `created_at`, `updated_at` |
| `CardOutSchema*` | `id`, `title`, `description` (nullable), `assignee_id` (nullable), `created_by`, `order`, `completed_at` (nullable), `created_at`, `updated_at` |
| `RegisterOutSchema` | `id`, `name`, `email`, `created_at` |
| `LoginOutSchema` | `access_token`, `token_type`, `expires_in`, `user` (`UserBriefOutSchema`: `id`, `name`, `email`) |
| `ProfileOutSchema` | `id`, `name`, `email`, `created_at`, `updated_at` |
| `BoardOutSchema` | `id`, `name`, `owner_id`, `role`, `created_at`, `updated_at` |
| `BoardDetailOutSchema` | `BoardOutSchema` fields plus `columns` (`ColumnWithCardsOutSchema`: `ColumnOutSchema` fields plus `cards`: `CardOutSchema[]`) |
| `MemberOutSchema` | `user_id`, `name`, `email`, `role`, `created_at` |
| `MemberRemovedOutSchema` | `user_id` |
| `ColumnReorderOutSchema` | `columns` (`ColumnOutSchema[]`), `rebalanced` |
| `CardMoveOutSchema` | `CardOutSchema` fields plus `column_id`, `rebalanced`, `siblings` (`SiblingOutSchema[]`: `id`, `order`; present only when `rebalanced` is true) |
| `TaskGroupOutSchema` | `board_id`, `board_name`, `cards` (`CardOutSchema[]`) |
| `CommentOutSchema` | `id`, `card_id`, `content`, `author` (`AuthorOutSchema`), `created_at`, `updated_at` |
| `NotificationOutSchema` | `id`, `type`, `message`, `board_id`, `card_id` (nullable), `is_read`, `created_at` |
| `NotificationPageOutSchema` | `items` (`NotificationOutSchema[]`), `page`, `per_page`, `total` |
| `AnalyticsOutSchema` | `cards_per_column` (`column_id`, `title`, `card_count`), `completed_this_week`, `member_activity` (`user_id`, `name`, `actions`) |
| `HealthOutSchema` | `status` |

No response schema has a `password` or `password_hash` field (Req 21.2, 24.20). The two shapes of `GET /api/cards` share one operation. The `data` property is documented with `oneOf` of the two array shapes, produced by a small `OneOfData` field class whose apispec attribute function resolves both schema classes into `$ref` entries. If apispec cannot express this, the fallback is `anyOf` through the same field. The test in Requirement 24.22 asserts the two branches.

### Example payloads

```json
{"data": {"access_token": "<jwt>", "token_type": "Bearer", "expires_in": 3600,
          "user": {"id": "0b9f...", "name": "Alice", "email": "alice@revotask.test"}}}
```

```json
{"data": {"id": "3f2a...", "column_id": "91c0...", "title": "Write design", "order": 2.0,
          "rebalanced": true, "siblings": [{"id": "3f2a...", "order": 2.0}, {"id": "77ab...", "order": 1.0}],
          "description": null, "assignee_id": null, "created_by": "0b9f...", "completed_at": null,
          "created_at": "2026-11-14T09:00:00+00:00", "updated_at": "2026-11-14T09:05:00+00:00"}}
```

### OpenAPI generation

`common/openapi.py`:

```python
class OpenAPIError(RuntimeError): ...

def document(*, summary: str, request: type[Schema] | None = None, query: type[Schema] | None = None,
             success: type[Schema] | None = None, many: bool = False, status: int | None = None,
             public: bool = False, conflict: bool = False) -> Callable[[F], F]:
    """Attach metadata to the view function as fn.__openapi__. Changes no behavior."""

def build_openapi(app: Flask) -> dict
def register_docs(app: Flask) -> None
```

`build_openapi(app)`:

1. Create `APISpec(title="RevoTask API", version="1.0.0", openapi_version="3.0.3", plugins=[MarshmallowPlugin(schema_name_resolver=...)])`. The resolver strips a trailing `Schema` from the class name. Add one tag per blueprint name, the `bearerAuth` scheme (`http`, `bearer`, `JWT`) and the `ErrorEnvelope` component. These are the only definitions made outside the blueprint directories (Req 24.18).
2. For each `rule` in `app.url_map.iter_rules()` whose path starts with `/api/`, skipping the three documentation endpoints and the methods `HEAD` and `OPTIONS`: read `app.view_functions[rule.endpoint].__openapi__`. Missing metadata raises `OpenAPIError("OpenAPI: route <rule> has no documentation")`.
3. Build the operation:
   - `tags=[endpoint.split(".")[0]]` and `summary`.
   - Path `<name>` segments become `{name}`. Each is a required `in: path` parameter with `{"type": "string", "format": "uuid"}`.
   - `query` adds `{"in": "query", "schema": QuerySchema}`, which apispec expands per field into `required`, `minimum`, `maximum`, `minLength`, `maxLength`, `enum` and `default`.
   - `request` adds a required `requestBody` with `application/json` and the schema class.
   - Success response: status from `status` or the HTTP method (`201` for the six POST create routes), schema `<Name>Envelope`, built with `Schema.from_dict({"data": fields.Nested(inner, many=many, required=True)}, name=...)`, so `data` is the only required property.
   - Error responses, derived from the rule: `401` unless `public`; `404` when a path parameter exists; `403` when the path has a `boards`, `columns`, `cards` or `comments` identifier; `400` when the operation has a body or a query; `409` when `conflict=True` (register, `PATCH /users/me`, add member, change role, remove member). Each refers to `ErrorEnvelope`.
   - `security=[{"bearerAuth": []}]`, or `[]` when `public` (register, login, health).
4. Wrap any exception from apispec in `OpenAPIError` whose message starts with `OpenAPI` (Req 24.21).

`register_docs(app)` calls `build_openapi`, serializes it once with `json.dumps(spec, sort_keys=True)` and keeps the bytes, so every response is byte-identical (Req 24.3). Then:

| URL rule | Endpoint function | Response |
|----------|-------------------|----------|
| `GET /api/docs` | `docs_page` | HTML that loads `/swagger-ui/swagger-ui.css`, `/swagger-ui/swagger-ui-bundle.js` and runs `SwaggerUIBundle({url: "/api/openapi.json", dom_id: "#swagger-ui"})`. No other host. |
| `GET /api/openapi.json` | `openapi_json` | the stored bytes, `Content-Type: application/json`, no envelope |
| `GET /swagger-ui/<path:filename>` | `swagger_asset` | `send_from_directory(Path(str(swagger_ui_path)), filename)`; a missing file is a 404 envelope |

When `SWAGGER_ENABLED` is false, `register_docs` is not called. The three paths then match no rule and return the 404 envelope with no extra code (Req 24.6). The docs rules allow only `GET`, so `POST /api/docs` returns 405 (Req 24.7). They carry no `@protected` (Req 24.4). Flask-CORS covers them because the resource pattern is `/*` (Req 24.8).

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Properties 6, 7, 8, 10, 15, 16, 17 and 19 test pure functions. The others run against the real application and PostgreSQL 18 through the Flask test client. Each property that needs data creates its own users and boards per example, with unique emails, so examples do not interfere.

### Property 1: Registration and login round trip

*For any* valid name, any valid email written with any casing and surrounding whitespace, and any valid password, registering and then logging in with any other casing or padding of the same email and the same password SHALL return a token whose subject is the new user's id and a stored email equal to the trimmed lower-case form. A second registration with any other casing or padding of that email SHALL return 409 and leave one user row. *For any* login with an unknown email or a wrong password, the status and the whole response body SHALL be identical.

**Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.3, 2.4, 21.5**

### Property 2: Bounded text fields accept exactly their range

*For any* bounded text field of the request schemas (user `name` 1 to 255, `password` 8 to 128, board `name`, column `title`, card `title` 1 to 255, card `description` at most 10,000 or null, comment `content` 1 to 5,000 with one non-whitespace character, `search` 1 to 200) and *for any* string, including strings with whitespace, non-BMP characters, `NUL` and lone surrogates, the schema SHALL accept the value if and only if it is within the range and holds no `NUL` or unencodable character. A rejected request SHALL return 400 naming the field and leave the database unchanged.

**Validates: Requirements 1.4, 2.5, 3.6, 4.2, 5.4, 7.3, 11.3, 12.2**

### Property 3: Strict scalar fields accept exactly their type

*For any* JSON value, `OrderValue` SHALL accept it if and only if it is a number (not a bool, not a string), finite and greater than 0; `StrictUUID` SHALL accept it if and only if it is a string in canonical 8-4-4-4-12 hexadecimal form; `StrictBoolean` SHALL accept it if and only if it is `true` or `false`; `DigitsInt` SHALL accept it if and only if it is a string of 1 to 18 ASCII digits. A rejection SHALL name the field and leave the data unchanged.

**Validates: Requirements 8.3, 9.7, 10.5, 13.3**

### Property 4: Unknown fields are rejected by strict schemas and ignored by lenient ones

*For any* valid payload of a schema and *for any* extra key not defined by it, a `StrictSchema` (register, `PATCH /users/me`, card create, card update) SHALL fail with an error that names every extra key, and a `LenientSchema` SHALL load the payload with the extra keys removed. This holds for the keys `user_id`, `owner_id` and `created_by`, and the acting user, board owner and card creator SHALL always be the token's user.

**Validates: Requirements 1.5, 3.3, 9.7, 17.5, 17.6**

### Property 5: A request body must be a JSON object

*For any* request body that is empty, is not valid JSON, or is valid JSON whose top-level value is an array, string, number, boolean or null, a route that accepts a body SHALL return 400 with an error envelope and leave the data unchanged.

**Validates: Requirements 1.6, 18.3**

### Property 6: Field error messages follow one format

*For any* nested mapping of field errors, `format_field_errors` SHALL return one `<field>: <message>` entry per leaf message, fields in sorted order, separated by `; `, with no leading or trailing separator and with the `_schema` key rendered as its bare message.

**Validates: Requirements 18.7**

### Property 7: Identifiers and timestamps serialize in one form

*For any* UUID and *for any* timezone-aware datetime in any offset, the output field SHALL write the UUID as a 36-character lower-case hyphenated string and the datetime as an ISO 8601 string equal to the same instant in UTC with the offset `+00:00`.

**Validates: Requirements 18.2**

### Property 8: Settings parsing

*For any* string `s`, `parse_cors_origins(s)` SHALL return the comma-separated entries with each entry trimmed and empty entries dropped, or `("http://localhost:3000",)` when none remain; `parse_swagger_enabled(s)` SHALL be false if and only if `s` trimmed and compared case-insensitively equals `false`; `load_settings` SHALL raise an error containing `JWT_SECRET_KEY` for every missing, empty or whitespace-only value; and `parse_expires` SHALL return the integer for every string of decimal digits above 0 and 3600 when unset.

**Validates: Requirements 2.2, 19.1, 20.1, 20.3, 24.1**

### Property 9: CORS origin matching is exact

*For any* list of configured origins and *for any* request `Origin` value, the response SHALL carry `Access-Control-Allow-Origin` equal to that origin if and only if the value equals an entry exactly (case-sensitive, whole string), and SHALL carry no such header otherwise, and none when the request has no `Origin`. This holds for every response status.

**Validates: Requirements 19.2, 19.4, 19.5, 24.8**

### Property 10: Password hashes never reveal the password

*For any* password, `hash_password` SHALL return a value that is not equal to the password, does not contain it as a substring, verifies against the password with `verify_password`, and differs from the hash produced by a second call for the same password.

**Validates: Requirements 21.1**

### Property 11: Authentication precedes every other check

*For any* protected route, *for any* path identifier (valid, invalid or random) and *for any* body, and *for any* Authorization header that is absent, not of the form `Bearer <token>`, a malformed token, a token with a wrong signature, an expired token, or a token whose subject is not an existing user, the response SHALL be 401 with an error envelope and no data SHALL change. The same headers on the documentation routes SHALL return 200.

**Validates: Requirements 17.1, 17.4, 23.5, 24.4**

### Property 12: Board-scoped routes are closed to non-members and members lacking the role

*For any* board-scoped route and *for any* valid body, a user with no membership on the board SHALL receive 403, a user with role `member` SHALL receive 403 on every admin-only route and on comment update or delete of another user's comment (admins included), and the database SHALL be unchanged in both cases.

**Validates: Requirements 5.6, 6.11, 9.9, 12.6, 15.4, 17.3**

### Property 13: The first failing check decides the status

*For any* protected route that takes a path identifier and *for any* combination of conditions (token valid or not, record found or not, caller a member or not, caller has the role or not, body valid or not), the status SHALL equal the first failing check in the order 401, 404, 403, 400. A path identifier that is not a UUID SHALL give 404, and the database SHALL be unchanged for every failing check.

**Validates: Requirements 5.6, 17.2, 17.4**

### Property 14: Every response is an envelope and no input causes a server error

*For any* route and HTTP method in the route registry (and any path that matches no route), *for any* token state and *for any* JSON body or raw bytes, the response SHALL have `Content-Type: application/json`, a body `{"data": ...}` for status 200 to 399 and `{"error": <non-empty string>}` for status 400 to 599, SHALL have no `password` or `password_hash` key at any depth, and SHALL NOT have status 500. *For any* exception raised inside a view, with any message text, the response SHALL be status 500 with the fixed message and none of the exception text, and the transaction SHALL be rolled back.

**Validates: Requirements 16.1, 18.1, 18.3, 18.4, 18.6, 18.8, 21.2**

### Property 15: Next order is one above the maximum

*For any* collection of positive finite floats, `next_order` SHALL return `max + 1.0`, and SHALL return `1.0` for the empty collection. Creating `n` columns (or `n` cards in one column) through the API SHALL give them orders `1.0, 2.0, ..., n`.

**Validates: Requirements 7.1, 9.1**

### Property 16: A move without a close sibling changes only the moved row

*For any* set of siblings and *for any* requested order whose absolute difference from every sibling is at least `MIN_GAP`, `plan_move` SHALL return `rebalanced = False` and a plan that writes exactly the requested order for the moved row and nothing else.

**Validates: Requirements 8.1, 10.2**

### Property 17: A rebalance numbers the rows 1 to N and keeps their order

*For any* set of siblings and *for any* requested order within `MIN_GAP` of at least one sibling (including equal to one, and not only of an adjacent one), `plan_move` SHALL return `rebalanced = True` with orders exactly `1.0, 2.0, ..., N`, where `N` is the number of siblings plus one, the siblings in their original relative order, and the moved row after every sibling whose order is less than or equal to the request and before every greater one.

**Validates: Requirements 8.2, 10.4**

### Property 18: The reorder and move endpoints agree with `plan_move`

*For any* board with generated column orders, any column and any request order, `PATCH /columns/reorder` SHALL return the Live_Record columns sorted by order with the values `plan_move` predicts. *For any* card, any target column of the same board and any request order, `PATCH /cards/{id}/position` SHALL store the predicted column and order, set `rebalanced` as predicted, and list `siblings` if and only if `rebalanced` is true. Rows that are not Live_Records SHALL be unchanged.

**Validates: Requirements 8.1, 8.2, 10.2, 10.4**

### Property 19: Notification messages always fit

*For any* card title of any length and any template, `fit_message` SHALL return a string of 1 to 500 characters that equals the full rendered message when that is at most 500 characters, and otherwise contains a prefix of the title followed by `…`.

**Validates: Requirements 14.7**

### Property 20: Activity logs and notifications match the event model

*For any* sequence of card operations (create with or without assignee, update of title, description, assignee or completion, move within or across columns, comment, add member) by any board member, the multiset of `activity_logs` actions and the set of `notifications` created by each request SHALL equal the prediction of a reference model that applies the rules of Requirements 9.3 to 9.5, 10.3 and 14.1 to 14.4, with `board_id` and `card_id` set as specified.

**Validates: Requirements 6.2, 9.1, 9.3, 9.5, 10.3, 12.1, 14.1, 14.2, 14.3, 14.4, 14.5**

### Property 21: A failed event write leaves no change

*For any* route that writes an activity log or a notification and *for any* valid request, when the event write is made to fail, the response SHALL be 500 and every table SHALL be equal to its state before the request. The same holds when the board or membership insert of board creation fails.

**Validates: Requirements 4.5, 14.6**

### Property 22: Completion and mark-read are idempotent

*For any* card and *for any* number `n` of repeated `completed: true` requests, `completed_at` SHALL equal the value after the first request and exactly one `card_completed` activity SHALL exist; a later `completed: false` SHALL set it to null. *For any* notification of the caller and any `n` of repeated mark-read requests, every response body SHALL be equal and only `is_read` SHALL have changed.

**Validates: Requirements 9.3, 9.4, 13.5, 13.7**

### Property 23: A partial update changes only the supplied fields

*For any* user profile or card and *for any* non-empty subset of its writable fields with valid values, the update SHALL change exactly those fields (the email stored trimmed and lower-case), keep every other field, and keep `id`, `created_at` and, for cards, `column_id`, `order` and `created_by`.

**Validates: Requirements 3.2, 9.2**

### Property 24: An assignee must be a board member

*For any* card create or update request whose `assignee_id` is a UUID that is not a member of the card's board, the response SHALL be 400 naming `assignee_id`, and the card SHALL be unchanged or not created. A null `assignee_id` SHALL always be accepted.

**Validates: Requirements 9.6**

### Property 25: Membership operations keep the board administrable

*For any* sequence of add, role-change and remove operations by board admins, the board SHALL always have at least one admin, a rejected operation SHALL return 409 or 404 and change no membership, card assignee or activity row, and removing a member SHALL set `assignee_id` to null on exactly the live cards of the board assigned to that user and leave their authored cards and comments unchanged.

**Validates: Requirements 6.6, 6.7, 6.8, 6.9, 6.10**

### Property 26: Soft-deleted records are invisible and nothing else changes

*For any* board graph and *for any* deletion of a board, column, card or comment through the API, the deleted record and every record below it SHALL be absent from `GET /boards`, `GET /boards/{id}`, `GET /cards` (both modes), comment lists and analytics, every route addressed by its id SHALL return 404, and only the `deleted_at` and `updated_at` of the deleted row SHALL differ in the database.

**Validates: Requirements 5.2, 5.5, 7.4, 9.8, 12.3, 12.5, 17.2**

### Property 27: Board list and board detail match the reference

*For any* set of users, boards and memberships, `GET /boards` for any user SHALL equal the member boards sorted by `updated_at` descending then `id` ascending (an empty list when none), and `GET /boards/{id}` SHALL equal a reference built from the models: live columns by `order`, each with its live cards by `order`, and empty lists where nothing exists.

**Validates: Requirements 4.3, 4.4, 5.1**

### Property 28: My Tasks and search match the reference

*For any* set of boards, cards and assignees, `GET /cards?assignee=me` SHALL return groups that partition exactly the caller's live assigned cards, one group per board, ordered by board name, with cards ordered by column order then card order. *For any* term of 1 to 200 characters, including `%`, `_` and `\`, `GET /cards?search=<term>` SHALL return exactly the live cards of the caller's boards whose title or description contains the term as a case-insensitive literal substring, and an empty list when none match.

**Validates: Requirements 11.1, 11.2, 11.5**

### Property 29: Notification pages match the reference slice

*For any* number of notifications of a user, other users' notifications, `page` and `per_page` within range, the response SHALL hold the slice at offset `(page - 1) * per_page` of the user's notifications sorted by `created_at` descending, at most `per_page` long, with `total` equal to the count of all the user's notifications, and an empty `items` list past the last page. *For any* `page` and `per_page` strings that are invalid or give an offset above 1,000,000, the response SHALL be 400 naming each invalid parameter.

**Validates: Requirements 13.1, 13.3, 13.4**

### Property 30: Request values are stored and matched as literal text

*For any* string, including SQL fragments such as `'; DROP TABLE users; --`, sent in a text field, a query string or a search term, the API SHALL store or match it as literal text, and every table and every row not addressed by the request SHALL be unchanged.

**Validates: Requirements 21.4**

## Error Handling

### Responses

| Condition | Status | `error` message | Where raised |
|-----------|--------|-----------------|--------------|
| Missing, malformed, bad-signature, expired token; subject not an existing user | 401 | `Authentication required` | JWT callbacks in `auth.py` |
| Wrong email or password | 401 | `Invalid email or password` (same for both) | `auth.service.login` |
| Path id is not a UUID; record missing, soft-deleted, or under a soft-deleted ancestor; notification of another user; `column_id` or target user not found | 404 | `Resource not found` (a more specific text is allowed) | `access.py`, services |
| Unmatched path | 404 | `Resource not found` | `HTTPException` handler |
| Not a member; role too low; not the card creator or comment owner | 403 | `Forbidden` | `access.py` |
| Body or query invalid; unknown field; assignee not a member | 400 | `<field>: <message>; ...` | `load_body`, `load_query`, services |
| Method not allowed | 405 | `Method not allowed` | `HTTPException` handler |
| Body larger than 1 MiB | 413 | `Request body too large` | `HTTPException` handler |
| Duplicate email, existing membership, last admin | 409 | specific text | services, `commit_or_conflict` |
| Unique violation that reaches the handler | 409 | `Resource already exists` | `IntegrityError` handler |
| Other constraint violation | 400 | `Request violates a data constraint` | `IntegrityError` handler |
| Unhandled exception | 500 | `Internal server error` | `Exception` handler |

### Transactions and logging

- A request has one transaction. Services add rows, activity logs and notifications to `db.session` and call `commit_or_conflict()` once. Any exception skips the commit; the handler calls `db.session.rollback()`. Flask-SQLAlchemy also removes the session at teardown.
- `IntegrityError` text and SQL never reach a response (Req 18.5). `hide_parameters=True` keeps bound values out of exception text and logs (D18).
- The unhandled-exception handler logs the traceback with `app.logger.exception`. No code logs a password, a token, the Authorization header or `JWT_SECRET_KEY`. Services build exceptions from constants, never from request values.
- Services never leak SQL: they raise `ApiError` subclasses with fixed or field-based text.

### Startup errors

| Condition | Result |
|-----------|--------|
| `DATABASE_URL` missing or blank | `DatabaseConfigError` before any engine (existing behavior) |
| `JWT_SECRET_KEY` missing, empty or blank | `RuntimeError("JWT_SECRET_KEY is not set or is empty")` before `db.init_app` (Req 20.3) |
| `JWT_ACCESS_TOKEN_EXPIRES` set but not a positive decimal integer | `RuntimeError` naming `JWT_ACCESS_TOKEN_EXPIRES` |
| Docs enabled and a `/api/` route has no `@document`, or apispec fails | `OpenAPIError` whose message starts with `OpenAPI` (Req 24.21) |
| Database unreachable | `DatabaseUnreachableError` after 3 attempts (existing) |

## Deployment and Configuration

**`backend/requirements.txt`** adds these lines to the existing ones, each with a minimum and an exclusive maximum:

```
Flask-JWT-Extended>=4.7,<5.0
Flask-CORS>=6.0,<7.0
marshmallow>=3.23,<4.0
apispec[marshmallow]>=6.8,<7.0
swagger-ui-bundle>=1.1,<2.0
python-dotenv>=1.0,<2.0
gunicorn>=23.0,<28.0
openapi-spec-validator>=0.7,<1.0
pytest-cov>=5.0,<8.0
pytest-randomly>=3.15,<6.0
```

**`backend/.env.example`** keeps its two existing lines (`DB_REQUIRE_SSL`, `SEED_PASSWORD`) and adds:

```
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
JWT_SECRET_KEY=replace-with-a-long-random-string
JWT_ACCESS_TOKEN_EXPIRES=3600
CORS_ORIGINS=http://localhost:3000
SWAGGER_ENABLED=true
```

`.gitignore` already tracks `.env.example` (`!.env.example`).

**`backend/railway.json`** (D17). Railway's service root directory is `backend`.

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "deploy": {
    "startCommand": "gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 30 \"app:create_app()\"",
    "preDeployCommand": ["flask db upgrade"],
    "healthcheckPath": "/api/health"
  }
}
```

The pre-deploy command runs before the start command and a failed migration stops the release. `flask` finds the `create_app` factory in the `app` package. Gunicorn's default access log does not record request headers, so tokens stay out of logs (Req 21.3).

**`backend/.coveragerc`**

```
[run]
source = app/blueprints
[report]
fail_under = 80.0
precision = 1
show_missing = true
```

**`backend/pytest.ini`** gains `markers = performance: slow timing tests`.

## Testing Strategy

PBT applies to this feature. Validation, ordering, message building, settings parsing, serialization, the check order, the event rules and the membership rules have clear input and output behavior over large input spaces. Documentation structure, deployment files, layer separation and timing use example, smoke and integration tests, as classified in the prework.

### Tools and fixtures

- `pytest`, `Hypothesis` (not implemented from scratch), `pytest-cov`, `openapi-spec-validator`, `pytest-randomly`. PostgreSQL 18 only, through the fixtures of `backend/tests/database/conftest.py`. SQLite is never used (Req 23.3).
- `tests/conftest.py` sets the default `JWT_SECRET_KEY` for all tests.
- `tests/api/conftest.py` imports `database_url`, `app` and `engine` from `tests.database.conftest`, so the throwaway PostgreSQL 18 cluster, the version assertion and `flask db upgrade` are reused. It adds:
  - `clean_db` (autouse): `TRUNCATE users, boards, board_members, columns, cards, comments, notifications, activity_logs RESTART IDENTITY CASCADE` before each test (D15).
  - `client`: `app.test_client()`.
  - `make_user(...)`, `make_board(owner, members=...)`, `make_column`, `make_card`, `make_comment`, `make_notification`: insert through `db.session` with a precomputed password hash and commit.
  - `auth_headers(user)`: a Bearer header from `create_access_token`.
  - `snapshot()`: row counts and column values of all eight tables, used by "data unchanged" assertions.
  - `count_queries()`: a context manager that records statements through the SQLAlchemy `before_cursor_execute` event.
- The Hypothesis profile of `tests/database/conftest.py` (100 examples, no deadline, function-scoped fixture health check suppressed) is loaded by the import and applies to the API properties.

### Property tests

- Each property in [Correctness Properties](#correctness-properties) is **one** Hypothesis test with at least 100 examples, tagged `# Feature: backend, Property N: <title>`.
- Properties 6, 7, 8, 10, 15, 16, 17 and 19 call pure functions and need no database. Property 9 builds an app per drawn origin list (`create_app(verify_db=False)`).
- Properties 20 and 25 use `hypothesis.stateful.RuleBasedStateMachine`, with a reference model beside the API and invariants checked after each rule.
- Properties 13 and 14 draw from a route registry built from `app.url_map` plus each route's `__openapi__` metadata, so a new route is covered automatically.
- Property 11 draws token variants: absent header, wrong scheme, random strings, tokens signed with another key, expired tokens (`exp` in the past), and tokens whose `sub` is a random UUID or a non-UUID string.
- Property 21 patches `common.events.log_activity` or `create_notification` to raise, chosen per route, and compares `snapshot()` before and after.
- Generators build on the strategies of `tests/database/conftest.py` (`text_of_length`, `finite_positive_floats`, `aware_datetimes`, `board_graphs`).

### Unit, smoke and integration tests

| File (`tests/api/`) | Content | Requirements |
|---------------------|---------|--------------|
| `test_auth.py`, `test_users.py` | Success and failure for register, login, profile; 409 on duplicate and on taken email; concurrent registration (8 threads, one 201, rest 409, one row) | 1 to 3 |
| `test_boards.py`, `test_members.py` | Create, list, detail, rename, delete; member add, change, remove; last-admin 409; 403 and 404 cases | 4 to 6 |
| `test_columns.py`, `test_cards.py`, `test_card_move.py` | Create, rename, delete, reorder; card create, update, delete; move across columns; `CardPositionSchema` runs before the column lookup | 7 to 10 |
| `test_cards_list.py` | `assignee=me`, `search=`, neither, both, invalid | 11 |
| `test_comments.py` | 201 on a valid comment, 400 naming `content` when missing, 401 without a token, 403 when a non-owner (including an admin) updates or deletes | 12, 23.2 |
| `test_notifications.py`, `test_events.py` | Paging, mark read, masked `card_id`, notification and activity rules | 13, 14 |
| `test_analytics.py` | Shape, admin-only, empty board, week boundary with a patched clock | 15 |
| `test_health.py` | Payload; 405 on `POST`; under 1,000 ms | 16 |
| `test_cross_cutting.py` | 401 per protected route without a token and not 401 with one (parametrized over the route registry); log capture finds no password, token or secret, including after a 500; SQL injection string | 17, 18, 21, 23.5 |
| `test_cors.py` | Preflight, no `Origin`, listed and unlisted origins | 19 |
| `test_config.py` | `.env` loading and process-env precedence; blank `JWT_SECRET_KEY`; `.env.example` lines; `requirements.txt` pins; `railway.json` start and pre-deploy command; `.coveragerc` | 20 |
| `test_structure.py` | 9 blueprints each with 3 files; `routes.py` has no `select`, `db.session` or `.query`; `service.py` does not import `flask.request` or `jsonify`; `schema.py` does not import `db`; `__openapi__` metadata only in blueprint files and `openapi.py` | 20.4, 20.5, 24.18 |
| `test_openapi.py` | `/api/openapi.json` valid OpenAPI 3 with zero errors; operations equal the URL map; tags, summaries, parameters, bodies, success and error responses, security, `password` rules; schema properties and `required` equal the Marshmallow fields (parametrized over every documented schema class); `/api/docs` HTML; assets under `/swagger-ui/`; invalid token still 200; `SWAGGER_ENABLED=false` gives 404; `POST` gives 405; an undocumented route raises `OpenAPIError` | 24 |
| `test_performance.py` (`@pytest.mark.performance`) | Seeds 50 columns and 5,000 cards by bulk insert. Board p95 under 500 ms and analytics p95 under 500 ms over 100 sequential requests after 1 warm-up. Query count for board load: the three statements after authentication target `boards`, `columns`, `cards` and the count is equal for a 1-column empty board and the large one | 22 |
| `tests/api/properties/` | The 30 property tests | all |

The performance tests use the in-process test client, so the timing excludes network transfer. This is a deviation from "request sent to response received over HTTP" and is listed under open points.

### Coverage and order independence

`python -m pytest tests/api --cov=app/blueprints` reads `fail_under = 80.0` from `.coveragerc`; a run below 80.0 percent exits non-zero and prints the measured percentage (Req 23.4, 23.6). `pytest-randomly` shuffles test order and `clean_db` gives each test an empty database, so no test depends on another (Req 23.7). The command for the whole project is `python -m pytest` from `backend/`.

## Requirements Traceability

Every acceptance criterion maps to a route or component, a design element and its verification. "Property" is a number from [Correctness Properties](#correctness-properties). "Example" means an example, smoke or integration test in the file named in the Testing Strategy.

| Criteria | Route or component | Design element | Verified by |
|----------|--------------------|----------------|-------------|
| 1.1, 1.2, 1.3 | POST /api/auth/register | `RegisterSchema`, `Email`, `register_user`, `hash_password`, `uq_users_email_lower` | Property 1, Property 10 |
| 1.4, 1.5 | POST /api/auth/register | `RegisterSchema` (`StrictSchema`), `Text`, `format_field_errors` | Properties 2, 4, 6 |
| 1.6 | POST /api/auth/register | `load_body` | Property 5 |
| 1.7 | POST /api/auth/register | unique index, `commit_or_conflict` | Example (threads) |
| 2.1, 2.3, 2.4 | POST /api/auth/login | `LoginSchema`, `login`, `create_access_token`, `verify_password` | Property 1 |
| 2.2 | POST /api/auth/login | `parse_expires`, `JWT_ACCESS_TOKEN_EXPIRES` | Property 8, Example |
| 2.5 | POST /api/auth/login | `LoginSchema`, `load_body` | Properties 2, 5 |
| 3.1 | GET /api/users/me | `get_profile`, `ProfileOutSchema` | Example |
| 3.2 | PATCH /api/users/me | `ProfileUpdateSchema`, `update_profile` | Property 23 |
| 3.3 | PATCH /api/users/me | `StrictSchema` | Property 4 |
| 3.4, 3.5 | PATCH /api/users/me | `at_least_one`, unique index | Example |
| 3.6 | PATCH /api/users/me | `Text`, `Email` | Property 2 |
| 4.1, 4.2 | POST /api/boards | `BoardCreateSchema`, `create_board` | Property 2, Example |
| 4.3, 4.4 | GET /api/boards | `list_boards` | Property 27 |
| 4.5 | POST /api/boards | one transaction, `commit_or_conflict` | Property 21 |
| 5.1, 5.2 | GET /api/boards/{id} | `get_board_for_user`, `get_board_detail`, `queries.load_board` | Properties 26, 27, Example (query count) |
| 5.3, 5.4 | PATCH /api/boards/{id} | `BoardUpdateSchema`, `rename_board`, `require_admin` | Properties 2, 23 |
| 5.5 | DELETE /api/boards/{id} | `delete_board`, `soft_delete` | Property 26 |
| 5.6 | PATCH, DELETE /api/boards/{id} | `require_admin` before `load_body` | Properties 12, 13 |
| 6.1 | GET /api/boards/{id}/members | `list_members` | Example |
| 6.2 | POST /api/boards/{id}/members | `MemberAddSchema`, `add_member`, `log_activity`, `create_notification` | Property 20 |
| 6.3, 6.4, 6.5 | POST /api/boards/{id}/members | `add_member`, `MemberAddSchema` | Example |
| 6.6 | PATCH /api/boards/{id}/members/{user_id} | `MemberRoleSchema`, `change_member_role` | Property 25 |
| 6.7, 6.8 | DELETE /api/boards/{id}/members/{user_id} | `remove_member`, bulk unassign | Property 25, Example |
| 6.9 | PATCH, DELETE /api/boards/{id}/members/{user_id} | admin count under `lock_board` | Property 25 |
| 6.10 | PATCH, DELETE /api/boards/{id}/members/{user_id} | target lookup (D20) | Property 25, Example |
| 6.11 | POST, PATCH, DELETE members | `require_admin`, `require_admin_or_self` | Property 12 |
| 6.12 | PATCH /api/boards/{id}/members/{user_id} | `MemberRoleSchema` | Example |
| 7.1 | POST /api/boards/{id}/columns | `create_column`, `next_order` | Property 15 |
| 7.2, 7.3 | POST /api/boards/{id}/columns, PATCH /api/columns/{id} | `ColumnCreateSchema`, `ColumnUpdateSchema`, `rename_column` | Properties 2, 23 |
| 7.4 | DELETE /api/columns/{id} | `delete_column`, `soft_delete` | Property 26 |
| 8.1, 8.2 | PATCH /api/boards/{id}/columns/reorder | `reorder_columns`, `plan_move` | Properties 16, 17, 18 |
| 8.3 | PATCH /api/boards/{id}/columns/reorder | `ColumnReorderSchema`, `OrderValue`, `StrictUUID` | Property 3 |
| 8.4 | PATCH /api/boards/{id}/columns/reorder | column lookup in `reorder_columns` | Example |
| 9.1 | POST /api/columns/{id}/cards | `CardCreateSchema`, `create_card`, `next_order` | Properties 15, 20 |
| 9.2 | PATCH /api/cards/{id} | `CardUpdateSchema`, `update_card` | Property 23 |
| 9.3, 9.4 | PATCH /api/cards/{id} | `completed_at` rules in `update_card` | Property 22 |
| 9.5 | PATCH /api/cards/{id} | `changed` rule, `log_activity` | Property 20 |
| 9.6 | POST /api/columns/{id}/cards, PATCH /api/cards/{id} | assignee membership check | Property 24 |
| 9.7 | POST /api/columns/{id}/cards, PATCH /api/cards/{id} | `StrictSchema`, `StrictBoolean`, `Text` | Properties 3, 4 |
| 9.8 | DELETE /api/cards/{id} | `delete_card`, `soft_delete` | Property 26 |
| 9.9 | DELETE /api/cards/{id} | `require_card_deleter` | Property 12 |
| 9.10 | PATCH /api/cards/{id} | `at_least_one` | Example |
| 10.1 | PATCH /api/cards/{id}/position | `CardPositionSchema` before lookup | Example |
| 10.2, 10.4 | PATCH /api/cards/{id}/position | `move_card`, `plan_move`, `CardMoveOutSchema` | Properties 16, 17, 18 |
| 10.3 | PATCH /api/cards/{id}/position | `log_activity(card_moved)` | Property 20 |
| 10.5 | PATCH /api/cards/{id}/position | `OrderValue`, `StrictUUID` | Property 3 |
| 10.6 | PATCH /api/cards/{id}/position | target column lookup | Example |
| 11.1, 11.2, 11.5 | GET /api/cards | `list_my_tasks`, `search`, `queries.my_tasks`, `queries.search_cards` | Property 28 |
| 11.3 | GET /api/cards | `CardListQuerySchema` | Property 2 |
| 11.4 | GET /api/cards | `exactly_one` | Example |
| 12.1, 12.2 | POST /api/cards/{id}/comments, PATCH /api/comments/{id} | `CommentSchema`, `create_comment` | Properties 2, 20 |
| 12.3 | GET /api/cards/{id}/comments | `list_comments` | Property 26 |
| 12.4 | PATCH /api/comments/{id} | `update_comment` | Example |
| 12.5 | DELETE /api/comments/{id} | `delete_comment` | Property 26 |
| 12.6 | PATCH, DELETE /api/comments/{id} | `require_comment_owner` | Property 12, Example |
| 13.1, 13.4 | GET /api/notifications | `list_notifications`, `queries.notifications_page` | Property 29 |
| 13.2 | GET /api/notifications | `NotificationOutSchema`, `card_id` masking | Example |
| 13.3 | GET /api/notifications | `DigitsInt`, `offset_limit` | Properties 3, 29 |
| 13.5, 13.7 | PATCH /api/notifications/{id}/read | `mark_read` | Property 22 |
| 13.6 | PATCH /api/notifications/{id}/read | `mark_read` ownership lookup | Example |
| 14.1, 14.2, 14.3, 14.4 | POST /api/columns/{id}/cards, PATCH /api/cards/{id}, PATCH /api/cards/{id}/position, POST /api/cards/{id}/comments, POST /api/boards/{id}/members | `create_notification` in services | Property 20 |
| 14.5 | all routes that write Activity_Actions | `log_activity` | Property 20 |
| 14.6 | all routes that write events | one transaction, rollback handler | Property 21 |
| 14.7 | the five routes above | `fit_message` | Property 19 |
| 15.1, 15.2, 15.3, 15.5, 15.6 | GET /api/boards/{id}/analytics | `get_analytics`, `queries.*` | Example |
| 15.4 | GET /api/boards/{id}/analytics | `require_admin` | Property 12 |
| 16.1 | GET /api/health | `get_status` | Properties 14, Example |
| 16.2 | GET /api/health | no database access | Example |
| 17.1 | all protected routes | `@protected`, JWT callbacks | Property 11 |
| 17.2 | all routes with an id | `parse_uuid`, `get_*_for_user` | Properties 13, 26 |
| 17.3 | all board-scoped routes | membership in `get_*_for_user` | Property 12 |
| 17.4 | all protected routes | fixed route sequence (D3) | Properties 11, 13 |
| 17.5, 17.6 | all write routes | token subject only, `StrictSchema` and `LenientSchema` | Property 4 |
| 18.1, 18.4, 18.8 | all routes, error handlers | `ok`, `error_response`, `HTTPException` handler | Property 14 |
| 18.2 | all routes | `UTCDateTime`, `fields.UUID` | Property 7 |
| 18.3 | all routes with a body | `load_body` | Property 5 |
| 18.5 | error handlers | `IntegrityError` handler, `commit_or_conflict` | Example |
| 18.6 | error handlers | `Exception` handler | Property 14 |
| 18.7 | all routes that validate | `format_field_errors` | Property 6 |
| 19.1 | create_app | `parse_cors_origins` | Property 8 |
| 19.2, 19.4, 19.5 | all routes | `compile_origins`, `always_send=False` | Property 9 |
| 19.3 | all routes | Flask-CORS preflight | Example |
| 20.1, 20.9 | create_app | `load_dotenv(override=False)`, `load_settings` | Property 8, Example |
| 20.2 | create_app | `.env.example` | Example |
| 20.3 | create_app | `load_settings` | Property 8 |
| 20.4, 20.5 | create_app | blueprint layout, layer rules | Example (`test_structure.py`) |
| 20.6, 20.8 | create_app | `railway.json` | Example |
| 20.7 | create_app | `requirements.txt` | Example |
| 21.1 | POST /api/auth/register | `hash_password` | Property 10 |
| 21.2 | all routes | response schemas without password fields | Property 14 |
| 21.3 | all routes | `hide_parameters`, no logging of secrets | Example (log capture) |
| 21.4 | all routes | bound parameters, `autoescape=True` in search | Property 30 |
| 21.5 | POST /api/auth/login | `verify_password` with dummy hash, one message | Property 1 |
| 22.1, 22.3 | GET /api/boards/{id}, GET /api/boards/{id}/analytics | indexed queries, plain-dict serialization | Example (`test_performance.py`) |
| 22.2 | GET /api/boards/{id} | D5, `queries.load_board` | Example (query count) |
| 23.1 to 23.7 | the test suite, all routes | Testing Strategy, `.coveragerc`, `clean_db`, `pytest-randomly` | Example, smoke |
| 24.1 | create_app | `parse_swagger_enabled` | Property 8 |
| 24.2, 24.5 | GET /api/docs | `docs_page`, `swagger_asset` | Example |
| 24.3 | GET /api/openapi.json | stored bytes | Example |
| 24.4 | GET /api/docs, GET /api/openapi.json | no `@protected` | Property 11 |
| 24.6, 24.7 | GET /api/docs, GET /api/openapi.json | `register_docs` only when enabled; GET-only rules | Example |
| 24.8 | GET /api/docs, GET /api/openapi.json | Flask-CORS `/*` | Property 9 |
| 24.9 to 24.16, 24.19, 24.20 | GET /api/openapi.json | `build_openapi` | Example (`test_openapi.py`) |
| 24.17 | GET /api/openapi.json | `MarshmallowPlugin`, `Schema.from_dict` envelopes | Example (parametrized over schema classes) |
| 24.18 | create_app | `@document` in `routes.py`, shared parts in `openapi.py` | Example (`test_structure.py`) |
| 24.21 | create_app | `OpenAPIError` | Example |
| 24.22, 24.23 | GET /api/docs, GET /api/openapi.json | `test_openapi.py` | Example |

## Decisions Beyond the Requirements and Open Points

Decisions D9 to D20 above are not in the requirements. These smaller ones are too:

1. The `GET /api/cards` response documents `data` as a `oneOf` of the two array shapes. If apispec cannot express it, the fallback is `anyOf`.
2. Changing a member to the role it already has still writes a `member_role_changed` activity (Requirement 6.6 says "update" without a no-change exception).
3. A repeated query key (`?page=1&page=2`) is a 400 for that key. Unknown query keys are ignored.
4. `info.version` of the OpenAPI document is `1.0.0`, independent of the spec version.
5. The `card_id` of a notification is also nulled when the card is soft-deleted or hidden by a deleted ancestor, not only when it is hard-deleted.
6. A comment whose `content` passes the Python whitespace test but fails PostgreSQL's `\S` check returns 400 through the `IntegrityError` handler.
7. `__init__.py` markers in each blueprint directory are not counted among the 27 required files.
8. Performance tests run in-process, so they exclude network time.

Open points for review:

- **Railway config as code is deprecated** and stops applying after 2026-12-01 for services that use `railway.json`. The same start command, pre-deploy command and health check path must then be set in the Railway dashboard.
- **Marshmallow 3 pin.** apispec's development line drops marshmallow 3. A move to marshmallow 4 needs new custom fields and a newer apispec.
- **Detail of login response shape.** The nested `user` object (D9) is my reading of Requirement 2.1. A flat shape would change `LoginOutSchema` only.
