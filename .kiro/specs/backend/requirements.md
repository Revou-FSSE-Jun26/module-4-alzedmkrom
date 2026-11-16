# Requirements Document

Version: V2 (see `CHANGELOG.md`)

## Introduction

This spec covers the Flask REST API of RevoTask, a Trello-like task manager. Two kinds of users call the API. Board members create boards, organize work into columns, move cards by drag-and-drop, comment on cards and track tasks assigned to them. Board administrators additionally manage member access, oversee all cards of a board and monitor team activity through analytics and notifications.

The API consumes the database layer from `.kiro/specs/database/` (models in `backend/app/models`, reference queries in `app/models/queries.py`). It does not redefine tables, constraints or indexes. The Next.js frontend is a separate spec.

Each blueprint lives in `app/blueprints/<name>/` with `routes.py` (HTTP only), `service.py` (business rules and SQLAlchemy queries) and `schema.py` (Marshmallow validation). Every acceptance criterion ends with a `Route:` tag that names the route, or the application component, that the later design must trace it to. The final section lists the full route-to-requirement matrix. Version V2 adds Requirement 24, which documents the API with one Swagger UI page generated from the Marshmallow schemas of the blueprints.

### Assumptions made for this version

- Board rename and board delete are limited to Board_Admins. Columns, cards and comments can be created and edited by any Board_Member.
- A Board_Member can edit and move any card of the board. Only the card creator or a Board_Admin can delete a card.
- The `PATCH /api/boards/<id>/columns/reorder` body names one column and its new Order_Value (single-item move), mirroring the card position endpoint.
- The API field for a comment's text is `content`. It maps to the `comments.body` column.
- Analytics is restricted to Board_Admins, because the brief gives analytics to administrators.
- An empty `PATCH /api/cards/<id>` body returns 400 instead of 200 with no change.
- When a requested Order_Value ties with another sibling, the moved column or card is placed after the sibling.
- Reorder and move responses carry a `rebalanced` flag. The column reorder response is `{columns, rebalanced}`. The card move response is the Card plus `rebalanced` and, when true, `siblings`.

### Assumptions made for version V2

- The request "Swagger UI for each blueprint file or API" is interpreted as ONE Swagger UI page for the whole Flask app, served by the API at GET /api/docs. Each of the 9 blueprints (auth, users, boards, columns, cards, comments, notifications, analytics, health) appears in that page as its own tagged group, and every route of the Route Traceability Matrix appears as one operation. The API does not serve one Swagger UI per blueprint.
- The two documentation routes are registered by `create_app` directly on the application. They are not a tenth Blueprint, so Requirement 20 criterion 4 (9 Blueprints, 27 files) stays true.
- Route ownership for tagging: `boards` owns the board routes and the member routes. `columns` owns POST /api/boards/<id>/columns, PATCH /api/boards/<id>/columns/reorder, PATCH /api/columns/<id> and DELETE /api/columns/<id>. `cards` owns POST /api/columns/<id>/cards, GET /api/cards and the /api/cards/<id> routes including `/position`. `comments` owns the comment routes under /api/cards/<id>/comments and /api/comments/<id>. `analytics` owns GET /api/boards/<id>/analytics.
- The documentation is enabled by default in every environment. Only `SWAGGER_ENABLED=false` disables it.
- The Swagger UI static assets are served by the API itself under the path prefix `/swagger-ui/` (outside `/api/`), so the page needs no external host.
- Non-goal: the documentation page and the OpenAPI_Document are not protected by authentication.

## Glossary

- **API**: The RevoTask Flask REST API defined by this spec.
- **Success_Envelope**: The JSON body `{"data": <payload>}` returned for every successful response.
- **Error_Envelope**: The JSON body `{"error": "<message>"}` returned for every failed response. `<message>` is a string.
- **Current_User**: The User identified by the Access_Token of the request.
- **Access_Token**: A JWT issued by the login route and sent as `Authorization: Bearer <token>`. Its subject is the User id.
- **Role**: `admin` or `member`, as stored in `board_members.role` by the database spec.
- **Board_Admin**: A Current_User whose Role on the Board is `admin`.
- **Board_Member**: A Current_User with a `board_members` row for the Board, with either Role.
- **Live_Record**: A Board, Column, Card or Comment whose `deleted_at` is null and whose ancestors (Column, Board) all have `deleted_at` null.
- **Order_Value**: The positive finite float stored in `columns.order` or `cards.order`.
- **Min_Gap**: The smallest allowed difference between two adjacent Order_Values, equal to `1e-6`.
- **Rebalance**: Renumbering all Live_Record siblings of a Column or Board to `1.0, 2.0, 3.0, ...` while keeping their relative order.
- **Service_Layer**: The `service.py` module of a blueprint.
- **Activity_Action**: The `activity_logs.action` value written by the API: `column_created`, `card_created`, `card_updated`, `card_completed`, `card_moved`, `card_deleted`, `comment_added`, `member_added`, `member_removed`, `member_role_changed`.
- **Notification_Type**: The `notifications.type` value written by the API: `card_assigned`, `card_moved`, `comment_added`, `member_added`.
- **Test_Suite**: The pytest tests under `backend/tests/api/`.
- **Deployment_Config**: The Gunicorn command, Railway start and pre-deploy commands, and `requirements.txt` of the backend.
- **OpenAPI_Document**: The OpenAPI 3 JSON document generated by the API and served at GET /api/openapi.json. It describes every route of the Route Traceability Matrix except the Documentation_Routes and `create_app`.
- **Swagger_UI**: The interactive HTML documentation page served by the API at GET /api/docs. It loads the OpenAPI_Document and offers an Authorize button for the Access_Token.
- **Blueprint_Tag**: An OpenAPI tag whose name equals the name of one of the 9 Blueprints (`auth`, `users`, `boards`, `columns`, `cards`, `comments`, `notifications`, `analytics`, `health`). Swagger_UI shows one group per Blueprint_Tag.
- **Documentation_Routes**: The two routes GET /api/docs and GET /api/openapi.json.
- **Swagger_UI_Assets**: The JavaScript, CSS and image files that Swagger_UI needs, served by the API under the path prefix `/swagger-ui/`.

## Requirements

### Requirement 1: Register a user

**User Story:** As a visitor, I want to register an account, so that I can sign in and use boards.

#### Acceptance Criteria

1. WHEN a request whose body is a JSON object containing only `name` (string, 1 to 255 characters), `email` (string, valid address, 3 to 254 characters after trimming) and `password` (string, 8 to 128 characters, used as received without trimming) is sent, THE API SHALL create a User with a salted password hash, return status 201 and return the User `id`, `name`, `email` (in its stored form) and `created_at` (ISO 8601 timestamp in UTC) in the Success_Envelope, with no `password` or password hash field in the response. (Route: POST /api/auth/register)
2. THE API SHALL trim leading and trailing whitespace from the `email` and convert it to lower case before validating its length and format and before storing it. (Route: POST /api/auth/register)
3. IF the `email` is valid and, after trimming and lower-casing, matches the `email` of an existing User, THEN THE API SHALL return status 409 with an Error_Envelope, create no User and leave the existing User unchanged. (Route: POST /api/auth/register)
4. IF `name`, `email` or `password` is missing, is null, has the wrong type or violates its length or format limit, THEN THE API SHALL return status 400 with an Error_Envelope whose message names every invalid field and create no User. (Route: POST /api/auth/register)
5. IF the request body contains a field other than `name`, `email` or `password`, THEN THE API SHALL return status 400 with an Error_Envelope whose message names every such field and create no User. (Route: POST /api/auth/register)
6. IF the request body is empty, is not valid JSON, or is valid JSON but not an object, THEN THE API SHALL return status 400 with an Error_Envelope and create no User. (Route: POST /api/auth/register)
7. IF two or more registration requests with the same normalized `email` are processed concurrently and no User with that `email` exists beforehand, THEN THE API SHALL create exactly one User, return status 201 for one request and return status 409 with an Error_Envelope for each of the others. (Route: POST /api/auth/register)

### Requirement 2: Log in

**User Story:** As a registered user, I want to log in, so that I receive a token for later requests.

#### Acceptance Criteria

1. WHEN a request with the `email` and `password` of an existing User is sent, THE API SHALL return status 200 with the Success_Envelope containing an Access_Token whose subject is the User `id`, `token_type` equal to `Bearer`, `expires_in` as an integer number of seconds, and the User `id`, `name` and `email`. The Success_Envelope SHALL contain no other User field, and in particular no password or password hash. (Route: POST /api/auth/login)
2. THE API SHALL set the Access_Token expiry and the `expires_in` value to the number of seconds in `JWT_ACCESS_TOKEN_EXPIRES`, defaulting to 3600 seconds when the variable is unset. (Route: POST /api/auth/login)
3. THE API SHALL match the submitted `email` to a User by trimming leading and trailing whitespace and comparing case-insensitively, consistent with the trimmed, lower-case storage in Requirement 1. THE API SHALL compare the `password` exactly as submitted, without trimming or case conversion. (Route: POST /api/auth/login)
4. IF the `email` matches no User or the `password` does not match the stored hash, THEN THE API SHALL return status 401 with an Error_Envelope whose `error` message is identical for both cases, issue no Access_Token, and change no stored data. (Route: POST /api/auth/login)
5. IF the request body is not a JSON object, or `email` or `password` is missing, is not a string, or is an empty string, THEN THE API SHALL return status 400 with an Error_Envelope naming each invalid field, issue no Access_Token, and change no stored data. (Route: POST /api/auth/login)

### Requirement 3: Current user profile

**User Story:** As a signed-in user, I want to read and update my profile, so that my name and email stay correct.

#### Acceptance Criteria

1. WHEN a request with a valid Access_Token is sent, THE API SHALL return status 200 with exactly the Current_User `id`, `name`, `email`, `created_at` and `updated_at` in the Success_Envelope, with `created_at` and `updated_at` as ISO 8601 UTC strings and with no `password` or `password_hash` field. (Route: GET /api/users/me)
2. WHEN a request with a JSON object containing `name` (string, 1 to 255 characters), `email` (string, valid address, 3 to 254 characters after trimming) or both, and no other field, is sent, THE API SHALL update only the supplied fields, store the `email` trimmed and in lower case, set `updated_at` to the time of the update, and return status 200 with the updated profile in the same shape as GET /api/users/me. A field that is not supplied SHALL keep its previous value. (Route: PATCH /api/users/me)
3. IF the request body contains `password`, `password_hash` or any other field than `name` and `email` (including `id`, `created_at` and `updated_at`), THEN THE API SHALL return status 400 with an Error_Envelope naming each such field and leave the User unchanged, even when the body also contains a valid `name` or `email`. (Route: PATCH /api/users/me)
4. IF the request body is a JSON object that contains neither `name` nor `email` and no field rejected by criterion 3, including the empty object `{}`, THEN THE API SHALL return status 400 with an Error_Envelope and leave the User unchanged. (Route: PATCH /api/users/me)
5. IF the new `email`, after trimming and conversion to lower case, matches the `email` of a User other than the Current_User, THEN THE API SHALL return status 409 with an Error_Envelope and leave the User unchanged, including any `name` supplied in the same request. A new `email` that matches only the Current_User's own `email` SHALL NOT cause a 409. (Route: PATCH /api/users/me)
6. IF a supplied `name` or `email` is not a string (including `null`), is empty, or violates its length or format limit, THEN THE API SHALL return status 400 with an Error_Envelope naming each invalid field and leave the User unchanged, including the other field when it is valid. (Route: PATCH /api/users/me)

### Requirement 4: Create and list boards

**User Story:** As a board member, I want to create boards and list mine, so that I can start and find work.

#### Acceptance Criteria

1. WHEN a request with a `name` that is a string of 1 to 255 characters is sent, THE API SHALL create a Board with `owner_id` equal to the Current_User `id`, create a `board_members` row with Role `admin` for the Current_User in the same transaction, and return status 201 with the Board `id`, `name`, `owner_id`, `role` equal to `admin`, `created_at` and `updated_at` in the Success_Envelope. (Route: POST /api/boards)
2. IF `name` is missing, is a string of 0 characters, is longer than 255 characters or is not a string, or IF the request body is not a JSON object, THEN THE API SHALL return status 400 with an Error_Envelope identifying `name` as invalid and create no Board and no `board_members` row. (Route: POST /api/boards)
3. WHEN a request is sent, THE API SHALL return status 200 with a list in the Success_Envelope containing every Live_Record Board in which the Current_User has a `board_members` row, each with `id`, `name`, `owner_id`, the Current_User's `role` on that Board, `created_at` and `updated_at`, ordered by `updated_at` descending and, for equal `updated_at` values, by `id` ascending, with no pagination and no Board in which the Current_User has no `board_members` row. (Route: GET /api/boards)
4. WHEN the Current_User has no Live_Record Board with a `board_members` row, THE API SHALL return status 200 with an empty list in the Success_Envelope. (Route: GET /api/boards)
5. IF the Board row or the `board_members` row cannot be written, THEN THE API SHALL roll back the transaction, return status 500 with an Error_Envelope, and persist neither the Board nor the `board_members` row. (Route: POST /api/boards)

### Requirement 5: Read, rename and delete a board

**User Story:** As a board member, I want to open a board with all its columns and cards, and as an administrator I want to rename or delete it.

#### Acceptance Criteria

1. WHEN a Board_Member requests a Live_Record Board, THE API SHALL return status 200 in the Success_Envelope with the Board `id`, `name`, `owner_id`, `created_at` and `updated_at`, the Current_User's `role`, and a `columns` list holding every Live_Record Column ordered by `order` ascending. Each Column SHALL carry its `id`, `board_id`, `title`, `order`, `created_at`, `updated_at` and a `cards` list holding its Live_Record Cards ordered by `order` ascending. A Board with no Live_Record Column SHALL return an empty `columns` list, and a Column with no Live_Record Card SHALL return an empty `cards` list. (Route: GET /api/boards/<id>)
2. THE API SHALL return each Card in the board response with `id`, `title`, `description`, `assignee_id`, `created_by`, `order`, `completed_at`, `created_at` and `updated_at`. `assignee_id` and `completed_at` SHALL be null when not set. THE API SHALL omit every Card whose `deleted_at` is not null and every Card whose Column has `deleted_at` not null. (Route: GET /api/boards/<id>)
3. WHEN a Board_Admin sends a `name` of 1 to 255 characters, THE API SHALL update the Board name, set `updated_at` to the time of the update, and return status 200 with the Board `id`, `name`, `owner_id`, the Current_User's `role`, `created_at` and `updated_at`. (Route: PATCH /api/boards/<id>)
4. IF `name` is missing, empty, longer than 255 characters or not a string, THEN THE API SHALL return status 400 with an Error_Envelope naming `name` and leave the Board unchanged. (Route: PATCH /api/boards/<id>)
5. WHEN a Board_Admin deletes a Live_Record Board, THE API SHALL set `deleted_at` on the Board to the time of the request, leave `deleted_at` and every other column of all Columns, Cards, Comments and memberships of the Board unchanged, delete no row, and return status 200 with the Board `id`. After the deletion, THE API SHALL omit the Board from GET /api/boards and treat it as not a Live_Record for every route. (Route: DELETE /api/boards/<id>)
6. IF a Board_Member whose Role is `member` sends a rename or delete request, THEN THE API SHALL return status 403 with an Error_Envelope, regardless of whether the request body is valid, and leave the Board unchanged. (Route: PATCH /api/boards/<id>, DELETE /api/boards/<id>)

### Requirement 6: Board member management

**User Story:** As a board administrator, I want to add, remove and change the role of members, so that I control who can access the board.

#### Acceptance Criteria

1. WHEN a Board_Member requests the members of a Live_Record Board, THE API SHALL return status 200 with one entry per membership of the Board, each with `user_id`, `name`, `email`, `role` and `created_at`, ordered by `created_at` ascending. (Route: GET /api/boards/<id>/members)
2. WHEN a Board_Admin sends an `email` (string, 3 to 254 characters, valid address) that matches an existing User case-insensitively after trimming, and an optional `role` (`member` or `admin`, default `member`), THE API SHALL, in one transaction, create the membership with that Role, write a `member_added` Activity_Action and write a `member_added` Notification for the added User, and return status 201 with the new member's `user_id`, `name`, `email`, `role` and `created_at`. (Route: POST /api/boards/<id>/members)
3. IF the `email` is valid but matches no User, THEN THE API SHALL return status 404 with an Error_Envelope and create no membership, Activity_Action or Notification. (Route: POST /api/boards/<id>/members)
4. IF the User already has a membership on the Board, THEN THE API SHALL return status 409 with an Error_Envelope, leave the existing membership and its Role unchanged, and create no Activity_Action or Notification. (Route: POST /api/boards/<id>/members)
5. IF `email` is missing, is not a string, is longer than 254 characters or is not a valid address, or IF `role` is present and is not the string `member` or `admin`, THEN THE API SHALL return status 400 with an Error_Envelope naming each invalid field and create no membership, Activity_Action or Notification. (Route: POST /api/boards/<id>/members)
6. WHEN a Board_Admin sends a `role` (`member` or `admin`) for an existing member, THE API SHALL, in one transaction, update that member's Role and write a `member_role_changed` Activity_Action, and return status 200 with the updated member's `user_id`, `name`, `email`, `role` and `created_at`. (Route: PATCH /api/boards/<id>/members/<user_id>)
7. WHEN a Board_Admin removes a member, THE API SHALL, in one transaction, delete that membership row, set `assignee_id` to null on every Live_Record Card of the Board assigned to that User, keep every Card and Comment authored by that User unchanged, and write a `member_removed` Activity_Action, and THE API SHALL return status 200 with the `user_id`. (Route: DELETE /api/boards/<id>/members/<user_id>)
8. WHEN a Board_Member whose Role is `member` removes the membership of the Current_User (`<user_id>` equals the Current_User id), THE API SHALL perform the removal described in criterion 7 and return status 200 with the `user_id`. (Route: DELETE /api/boards/<id>/members/<user_id>)
9. IF a role change or removal would leave the Board with zero members whose Role is `admin`, THEN THE API SHALL return status 409 with an Error_Envelope, leave every membership and every Card `assignee_id` unchanged, and write no Activity_Action. (Route: PATCH /api/boards/<id>/members/<user_id>, DELETE /api/boards/<id>/members/<user_id>)
10. IF `<user_id>` has no membership on the Board, THEN THE API SHALL return status 404 with an Error_Envelope and change no data. (Route: PATCH /api/boards/<id>/members/<user_id>, DELETE /api/boards/<id>/members/<user_id>)
11. IF a Board_Member whose Role is `member` sends an add, a role change, or a removal of a User other than the Current_User, THEN THE API SHALL return status 403 with an Error_Envelope, leave the memberships unchanged, and write no Activity_Action or Notification. (Route: POST /api/boards/<id>/members, PATCH /api/boards/<id>/members/<user_id>, DELETE /api/boards/<id>/members/<user_id>)
12. IF `role` is missing, is not a string, or is a value other than `member` or `admin`, THEN THE API SHALL return status 400 with an Error_Envelope naming the field and leave the membership and Role unchanged. (Route: PATCH /api/boards/<id>/members/<user_id>)

### Requirement 7: Columns

**User Story:** As a board member, I want to create, rename and delete columns, so that I can organize work.

#### Acceptance Criteria

1. WHEN a Board_Member sends a `title` of 1 to 255 characters for a Live_Record Board, THE API SHALL, in one transaction, create a Column with an Order_Value equal to the largest Order_Value among the Board's Live_Record Columns plus 1.0 (or 1.0 when none exist) and write a `column_created` Activity_Action, and THE API SHALL return status 201 with the Column `id`, `board_id`, `title`, `order`, `created_at` and `updated_at`. (Route: POST /api/boards/<id>/columns)
2. WHEN a Board_Member of the Board that contains a Live_Record Column sends a `title` of 1 to 255 characters, THE API SHALL update only the `title` and `updated_at` of that Column, leave its `order` and its Cards unchanged, and return status 200 with the updated Column using the fields listed in criterion 1. (Route: PATCH /api/columns/<id>)
3. IF `title` is missing, empty, longer than 255 characters or not a string, THEN THE API SHALL return status 400 with an Error_Envelope naming `title`, create no Column, change no Column, and write no Activity_Action. (Route: POST /api/boards/<id>/columns, PATCH /api/columns/<id>)
4. WHEN a Board_Member of the Board that contains a Live_Record Column deletes it, THE API SHALL set `deleted_at` on that Column only, leave every Card row of the Column with its `deleted_at` unchanged, leave the `order` of every other Column unchanged, and return status 200 with the Column `id`. (Route: DELETE /api/columns/<id>)

### Requirement 8: Reorder columns

**User Story:** As a board member, I want to drag a column to a new position, so that I can reorder without rewriting every column.

#### Acceptance Criteria

1. WHEN a Board_Member sends a `column_id` (a UUID string of a Live_Record Column of the Board) and an `order` (a JSON number, integer or decimal, greater than 0 and finite) and the difference between `order` and the Order_Value of every other Live_Record Column of the Board is at least Min_Gap, THE API SHALL store the `order` unchanged on that Column only, leave the Order_Value of every other Column unchanged, and return status 200 with an object holding `rebalanced` equal to `false` and `columns`, the Board's Live_Record Columns ordered by `order` ascending, each with `id`, `board_id`, `title`, `order`, `created_at` and `updated_at`. (Route: PATCH /api/boards/<id>/columns/reorder)
2. IF the absolute difference between the requested `order` and the Order_Value of at least one other Live_Record Column of the Board (not only the adjacent Columns) is less than Min_Gap, including a difference of 0, THEN THE API SHALL, in the same transaction, Rebalance the Board's Live_Record Columns and keep the moved Column at the requested position. The requested position is its place when all Live_Record Columns are sorted by Order_Value ascending, and the moved Column goes after any other Column with an equal Order_Value. The API SHALL then return status 200 with `rebalanced` equal to `true` and `columns` holding the renumbered Live_Record Columns ordered by `order` ascending, with the same fields as criterion 1. After the Rebalance, the Order_Values SHALL be exactly `1.0, 2.0, ..., N`, where N is the number of Live_Record Columns of the Board, and the relative order of the other Columns SHALL be unchanged. Columns that are not Live_Records SHALL NOT be changed. (Route: PATCH /api/boards/<id>/columns/reorder)
3. IF `column_id` is missing or is not a UUID string, or `order` is missing, is not a JSON number (a string, boolean, null, array or object is not a number), is 0, is negative, is NaN, or is infinite, THEN THE API SHALL return status 400 with an Error_Envelope whose message names each invalid field, and leave every Column unchanged. (Route: PATCH /api/boards/<id>/columns/reorder)
4. IF `column_id` is a valid UUID but matches no Column, matches a Column of a different Board, or matches a Column that is not a Live_Record, THEN THE API SHALL return status 404 with an Error_Envelope and leave every Column unchanged. (Route: PATCH /api/boards/<id>/columns/reorder)
### Requirement 9: Cards

**User Story:** As a board member, I want to create, edit, complete, assign and delete cards, so that I can track tasks.

#### Acceptance Criteria

1. WHEN a Board_Member sends a `title` (1 to 255 characters) and optional `description` (a string of at most 10,000 characters) and `assignee_id` (UUID of a Board_Member of the Column's Board), THE API SHALL, in one transaction, create a Card in the Live_Record Column with `created_by` equal to the Current_User, `description` and `assignee_id` null when omitted, `completed_at` null, an Order_Value equal to the largest Order_Value among the Column's Live_Record Cards plus 1.0 (or 1.0 when none exist), write a `card_created` Activity_Action, and return status 201 with the Card `id`, `title`, `description`, `assignee_id`, `created_by`, `order`, `completed_at`, `created_at` and `updated_at`. (Route: POST /api/columns/<id>/cards)
2. WHEN a Board_Member sends at least one of `title` (a string of 1 to 255 characters), `description` (a string of at most 10,000 characters, or null), `assignee_id` (a UUID or null) and `completed` (boolean) for a Live_Record Card, THE API SHALL update only the supplied fields, leave every other field unchanged, and return status 200 with the updated Card with the same fields as in criterion 1. (Route: PATCH /api/cards/<id>)
3. WHEN `completed` is true and the Card has no `completed_at`, THE API SHALL set `completed_at` to the current UTC time and write one `card_completed` Activity_Action. IF `completed` is true and the Card already has a `completed_at`, THEN THE API SHALL keep the existing `completed_at` and write no `card_completed` Activity_Action. (Route: PATCH /api/cards/<id>)
4. WHEN `completed` is false, THE API SHALL set `completed_at` to null and write no `card_completed` Activity_Action. (Route: PATCH /api/cards/<id>)
5. WHEN a Board_Member sends any of `title`, `description` or `assignee_id` with a value different from the stored value, THE API SHALL write one `card_updated` Activity_Action for the request, in addition to any `card_completed` Activity_Action from the same request. IF every supplied field other than `completed` equals its stored value, THEN THE API SHALL write no `card_updated` Activity_Action. (Route: PATCH /api/cards/<id>)
6. IF a supplied `assignee_id` is not the UUID of a Board_Member of the Card's Board, THEN THE API SHALL return status 400 with an Error_Envelope naming `assignee_id` and leave the Card unchanged. A null `assignee_id` is valid and removes the assignment. (Route: POST /api/columns/<id>/cards, PATCH /api/cards/<id>)
7. IF `title` is missing on creation, `title` is not a string, is empty or is longer than 255 characters, `description` is neither a string nor null or is longer than 10,000 characters, `assignee_id` is neither a UUID nor null, `completed` is not a boolean, or the body contains an unknown field (including `order`, `column_id` and `created_by`), THEN THE API SHALL return status 400 with an Error_Envelope naming each invalid field and leave the data unchanged. On creation, `title` null counts as not a string, and `completed` counts as an unknown field. (Route: POST /api/columns/<id>/cards, PATCH /api/cards/<id>)
8. WHEN the Card creator or a Board_Admin deletes a Live_Record Card, THE API SHALL, in one transaction, set `deleted_at` on the Card only, keep every other row, write a `card_deleted` Activity_Action and return status 200 with the Card `id`. (Route: DELETE /api/cards/<id>)
9. IF a Board_Member who is neither the Card creator nor a Board_Admin deletes a Card, THEN THE API SHALL return status 403 with an Error_Envelope and leave the Card unchanged. (Route: DELETE /api/cards/<id>)
10. IF the request body contains none of `title`, `description`, `assignee_id` and `completed`, THEN THE API SHALL return status 400 with an Error_Envelope and leave the Card unchanged. (Route: PATCH /api/cards/<id>)

### Requirement 10: Move a card

**User Story:** As a board member, I want to drag a card to another position or column, so that the board reflects the work state.

#### Acceptance Criteria

1. THE API SHALL validate the move request body with `CardPositionSchema` before looking up the target Column. The schema requires `column_id` (a UUID) and `order` (a positive finite float, as defined by Order_Value). (Route: PATCH /api/cards/<id>/position)
2. WHEN a Board_Member sends a valid `column_id` of a Live_Record Column of the same Board as a Live_Record Card, and a valid `order`, THE API SHALL set the Card's `column_id` and `order` to the sent values and return status 200 with the Card's `id`, `column_id`, `title`, `description`, `assignee_id`, `created_by`, `order`, `completed_at`, `created_at` and `updated_at` and `rebalanced` equal to `false` in the Success_Envelope. (Route: PATCH /api/cards/<id>/position)
3. WHEN the sent `column_id` differs from the Card's previous `column_id`, THE API SHALL write one `card_moved` Activity_Action. WHEN the sent `column_id` equals the Card's previous `column_id`, THE API SHALL write no `card_moved` Activity_Action. (Route: PATCH /api/cards/<id>/position)
4. IF the stored Order_Value would differ by less than Min_Gap (`1e-6`) from the Order_Value of another Live_Record Card in the target Column, THEN THE API SHALL Rebalance the target Column's Live_Record Cards in the same transaction as the move. The moved Card SHALL be placed where the requested `order` falls when the Cards of the target Column are sorted by Order_Value ascending, after any other Card with an equal Order_Value. The response SHALL have status 200 and include the Card fields of criterion 2 with `rebalanced` equal to `true`, and `siblings`, the `id` and `order` of every Live_Record Card in the target Column, ordered by `order` ascending, including the moved Card. (Route: PATCH /api/cards/<id>/position)
5. IF `column_id` is missing or not a UUID, or `order` is missing, is not a number (including a string or boolean), or is zero, negative, NaN or infinite, THEN THE API SHALL return status 400 with an Error_Envelope naming each invalid field, leave the Card unchanged and write no Activity_Action. (Route: PATCH /api/cards/<id>/position)
6. IF `column_id` is a valid UUID that does not match a Live_Record Column of the Card's Board, THEN THE API SHALL return status 404 with an Error_Envelope, leave the Card unchanged and write no Activity_Action. (Route: PATCH /api/cards/<id>/position)

### Requirement 11: My Tasks and card search

**User Story:** As a board member, I want to see my assigned cards grouped by board and search cards, so that I can find work quickly.

#### Acceptance Criteria

1. WHEN the query string is `assignee=me`, THE API SHALL return status 200 with a list in the Success_Envelope of groups `{board_id, board_name, cards}`, one group per Board that holds at least one Live_Record Card assigned to the Current_User, using the `my_tasks` query. THE API SHALL order the groups by `board_name` ascending. THE API SHALL order the `cards` of each group by the `order` of the Card's Column ascending, then by the Card `order` ascending. Each Card carries the fields listed in Requirement 5 criterion 2. (Route: GET /api/cards)
2. WHEN the query string is `search=<term>` with a term of 1 to 200 characters, THE API SHALL return status 200 with a flat list in the Success_Envelope of the Live_Record Cards whose `title` or `description` contains the term as a case-insensitive substring, restricted to Boards in which the Current_User is a Board_Member, using the `search_cards` query. Each Card carries the fields listed in Requirement 5 criterion 2. THE API SHALL treat every character of the term literally, including `%`, `_` and `\`. THE API SHALL NOT specify the order of the returned Cards. (Route: GET /api/cards)
3. IF `assignee` has a value other than `me` (including an empty value), or `search` is empty or longer than 200 characters, THEN THE API SHALL return status 400 with an Error_Envelope naming the invalid parameter and perform no query. (Route: GET /api/cards)
4. IF the request has neither `assignee` nor `search`, or has both, THEN THE API SHALL return status 400 with an Error_Envelope naming `assignee` and `search` and perform no query. (Route: GET /api/cards)
5. WHEN no Live_Record Card matches the `assignee=me` or `search=<term>` request, THE API SHALL return status 200 with an empty list in the Success_Envelope. (Route: GET /api/cards)

### Requirement 12: Comments

**User Story:** As a board member, I want to discuss cards in comments, so that the team stays aligned.

#### Acceptance Criteria

1. WHEN a Board_Member sends `content` (a string of 1 to 5,000 characters with at least one non-whitespace character) for a Live_Record Card, THE API SHALL create a Comment with `user_id` equal to the Current_User, write a `comment_added` Activity_Action and return status 201 with the Comment `id`, `card_id`, `content`, `author` (`id` and `name` of the Current_User), `created_at` and `updated_at`. (Route: POST /api/cards/<id>/comments)
2. IF `content` is missing, empty, whitespace only, longer than 5,000 characters or not a string, THEN THE API SHALL return status 400 with an Error_Envelope naming `content`, create no Comment, change no existing Comment and write no Activity_Action. (Route: POST /api/cards/<id>/comments, PATCH /api/comments/<id>)
3. WHEN a Board_Member requests the comments of a Live_Record Card, THE API SHALL return status 200 with every Live_Record Comment of that Card ordered by `created_at` ascending, each with the same fields as in criterion 1, or an empty list when the Card has no Live_Record Comment. (Route: GET /api/cards/<id>/comments)
4. WHEN the Comment owner sends valid `content` (as defined in criterion 1) for a Live_Record Comment, THE API SHALL replace the Comment `content`, leave `id`, `card_id`, `user_id` and `created_at` unchanged, and return status 200 with the updated Comment with the same fields as in criterion 1. (Route: PATCH /api/comments/<id>)
5. WHEN the Comment owner deletes a Live_Record Comment, THE API SHALL set `deleted_at` on the Comment only, keep the Comment row and every other row, and return status 200 with the Comment `id`. After this, THE API SHALL omit that Comment from the list returned for the Card. (Route: DELETE /api/comments/<id>)
6. IF a Current_User who is a Board_Member but not the Comment owner sends an update or delete request, THEN THE API SHALL return status 403 with an Error_Envelope and leave the Comment unchanged, including when the Current_User is a Board_Admin. (Route: PATCH /api/comments/<id>, DELETE /api/comments/<id>)

### Requirement 13: Notifications

**User Story:** As a user, I want to page through my notifications and mark them read, so that I notice relevant changes.

#### Acceptance Criteria

1. WHEN a request is sent with optional query parameters `page` (integer, at least 1, default 1) and `per_page` (integer, 1 to 100, default 20), THE API SHALL return status 200 with `items`, `page`, `per_page` and `total`, using the `notifications_page` query. `items` SHALL hold at most `per_page` of the Current_User's Notifications, starting at position `(page - 1) * per_page` in the list ordered by `created_at` descending. `page` and `per_page` SHALL echo the values applied. `total` SHALL be the count of all the Current_User's Notifications, read and unread, and SHALL not depend on `page` or `per_page`. (Route: GET /api/notifications)
2. THE API SHALL return each Notification with exactly `id`, `type` (one of the Notification_Type values), `message` (1 to 500 characters), `board_id`, `card_id` (null when no Card is involved or the Card no longer exists), `is_read` (boolean) and `created_at`. (Route: GET /api/notifications)
3. IF `page` or `per_page` is not an integer written as decimal digits only (a decimal point, sign, whitespace, or an empty value is invalid), is outside its range, or gives `(page - 1) * per_page` greater than 1,000,000, THEN THE API SHALL return status 400 with an Error_Envelope naming each invalid parameter and return no Notifications. The offset case SHALL name `page`. (Route: GET /api/notifications)
4. WHEN the requested `page` lies beyond the last page, including when the Current_User has no Notifications, THE API SHALL return status 200 with `items` equal to an empty list and `total` equal to the count of the Current_User's Notifications (0 when none). (Route: GET /api/notifications)
5. WHEN the Current_User marks an unread Notification of the Current_User as read, THE API SHALL set `is_read` to true, leave every other field of the Notification unchanged, and return status 200 with the Notification in the shape of criterion 2. The request has no body fields. (Route: PATCH /api/notifications/<id>/read)
6. IF the Notification does not exist or belongs to another User, THEN THE API SHALL return status 404 with an Error_Envelope and change no Notification. (Route: PATCH /api/notifications/<id>/read)
7. WHEN the Current_User marks an already read Notification of the Current_User as read, THE API SHALL return status 200 with the same Notification body as the first request and change no field. (Route: PATCH /api/notifications/<id>/read)

### Requirement 14: Notification and activity-log generation

**User Story:** As a board administrator, I want relevant actions recorded, so that notifications and analytics have data.

#### Acceptance Criteria

1. WHEN a Card is created with a non-null `assignee_id`, or an update sets `assignee_id` to a non-null User different from the Card's previous `assignee_id`, THE API SHALL create one `card_assigned` Notification with `user_id` equal to the assignee and `is_read` equal to false, unless the assignee is the Current_User. An update that sets `assignee_id` to null or to its previous value SHALL create no `card_assigned` Notification. (Route: POST /api/columns/<id>/cards, PATCH /api/cards/<id>)
2. WHEN a Card moves to a Column different from its previous Column, THE API SHALL create one `card_moved` Notification with `user_id` equal to the Card's assignee and `is_read` equal to false, unless the assignee is null or is the Current_User. A move within the same Column SHALL create no `card_moved` Notification. (Route: PATCH /api/cards/<id>/position)
3. WHEN a Comment is created, THE API SHALL create one `comment_added` Notification with `is_read` equal to false for each distinct non-null User among the Card's creator and assignee, excluding the Comment author and any User who is not a Board_Member at that time. A User who is both creator and assignee SHALL receive one Notification. (Route: POST /api/cards/<id>/comments)
4. THE API SHALL set `board_id` on each Notification to the Board that owns the affected record, and SHALL set `card_id` to the affected Card for `card_assigned`, `card_moved` and `comment_added` Notifications and to null for `member_added` Notifications. (Route: POST /api/columns/<id>/cards, PATCH /api/cards/<id>, PATCH /api/cards/<id>/position, POST /api/cards/<id>/comments, POST /api/boards/<id>/members)
5. THE API SHALL write exactly one Activity_Action row for each Activity_Action named in Requirements 6, 7, 9, 10 and 12 for the request, with `board_id`, `user_id` equal to the Current_User and, where a Card is involved, `card_id` (null otherwise), within the same database transaction as the action that caused it. (Route: all routes that write an Activity_Action in Requirements 6, 7, 9, 10 and 12)
6. IF writing a Notification or Activity_Action fails, THEN THE API SHALL return status 500 with an Error_Envelope and persist none of the request's changes, including the primary change, every Notification and every Activity_Action. (Route: all routes that write a Notification or Activity_Action)
7. THE API SHALL give each Notification a `message` of 1 to 500 characters that, where a Card is involved, contains the Card title, truncating the Card title when the full message would exceed 500 characters. (Route: POST /api/columns/<id>/cards, PATCH /api/cards/<id>, PATCH /api/cards/<id>/position, POST /api/cards/<id>/comments, POST /api/boards/<id>/members)

### Requirement 15: Board analytics

**User Story:** As a board administrator, I want per-board analytics, so that I can monitor progress and team activity.

#### Acceptance Criteria

1. WHEN a Board_Admin requests analytics of a Live_Record Board, THE API SHALL return status 200 with `cards_per_column`, `completed_this_week` and `member_activity` in the Success_Envelope. `cards_per_column` is a list with one item for each Live_Record Column of the Board, ordered by `order` ascending, each item holding `column_id`, `title` and `card_count`. `card_count` is the number of Live_Record Cards in that Column (an integer of 0 or more, 0 for an empty Column). `completed_this_week` is an integer of 0 or more. (Route: GET /api/boards/<id>/analytics)
2. THE API SHALL compute `cards_per_column`, `completed_this_week` and `member_activity` in the Service_Layer with SQLAlchemy joins, using `card_counts_per_column`, `completed_this_week` and `member_activity` from the database spec. (Route: GET /api/boards/<id>/analytics)
3. THE API SHALL count a Card in `completed_this_week` only when it is a Live_Record with `completed_at` from Monday 00:00:00 UTC of the current week (inclusive) to Monday 00:00:00 UTC of the next week (exclusive), where the current week is the one containing the server UTC time at the moment the request is processed. (Route: GET /api/boards/<id>/analytics)
4. IF a Board_Member whose Role is `member` requests analytics, THEN THE API SHALL return status 403 with an Error_Envelope. (Route: GET /api/boards/<id>/analytics)
5. WHEN a Board_Admin requests analytics of a Live_Record Board, THE API SHALL return `member_activity` as a list with one item for each User who is a Board_Member of the Board or has at least one activity log row on the Board, each item holding `user_id`, `name` and `actions`. `actions` is the number of activity log rows with that `board_id` and that `user_id`, counted over all time and over every Activity_Action. A Board_Member with no rows has `actions` equal to 0, and a User who is no longer a Board_Member appears only when `actions` is 1 or more. The API SHALL NOT specify the order of `member_activity`. (Route: GET /api/boards/<id>/analytics)
6. WHEN a Board_Admin requests analytics of a Live_Record Board that has no Live_Record Column, THE API SHALL return `cards_per_column` as an empty list and `completed_this_week` equal to 0, with `member_activity` still listing each Board_Member. (Route: GET /api/boards/<id>/analytics)

### Requirement 16: Health check

**User Story:** As an operator, I want a health endpoint, so that Railway and monitors can check the service.

#### Acceptance Criteria

1. WHEN a GET request without an `Authorization` header is sent, THE API SHALL return status 200 with a Success_Envelope whose payload is exactly `{"status": "ok"}`, with no other fields. (Route: GET /api/health)
2. WHEN a GET request without an `Authorization` header is sent, THE API SHALL return the response within 1,000 milliseconds. (Route: GET /api/health)
### Requirement 17: Authentication and authorization (cross-cutting)

**User Story:** As a board member, I want access limited to boards I belong to, so that my work stays private.

#### Acceptance Criteria

1. IF a request to any route other than POST /api/auth/register, POST /api/auth/login, GET /api/health, GET /api/docs and GET /api/openapi.json has no `Authorization` header, a header that is not of the form `Bearer <token>`, an Access_Token that is not a well-formed JWT, an Access_Token with an invalid signature, an Access_Token whose expiry time is at or before the current UTC time, or an Access_Token whose subject is not the id of an existing User, THEN THE API SHALL return status 401 with an Error_Envelope and change no data. (Route: all protected routes)
2. IF a path identifier is not a valid UUID, or names a record that does not exist, has `deleted_at` set, or has a Column or Board ancestor with `deleted_at` set, THEN THE API SHALL return status 404 with an Error_Envelope and change no data. (Route: all routes with `<id>` or `<user_id>`)
3. IF the Current_User has no `board_members` row for the Board that owns the requested Board, Column, Card or Comment, THEN THE API SHALL return status 403 with an Error_Envelope and change no data. (Route: all /api/boards/<id>..., /api/columns/<id>, /api/cards/<id>..., /api/comments/<id> routes)
4. IF a request fails more than one of the following checks, THEN THE API SHALL return the status of the first failing check in this order and perform no later check: (1) authentication, status 401; (2) record existence, status 404; (3) board membership and Role, status 403; (4) request validation, status 400; (5) uniqueness and state conflicts, status 409. A route skips each check that does not apply to it. (Route: all protected routes)
5. THE API SHALL take the acting User of every write only from the subject of the Access_Token. (Route: all write routes)
6. IF a write request body contains `user_id`, `owner_id` or `created_by` that is not a documented field of that route, THEN THE API SHALL return status 400 with an Error_Envelope naming the field where the route's own criteria reject unknown fields (POST /api/auth/register, PATCH /api/users/me, POST /api/columns/<id>/cards, PATCH /api/cards/<id>), and SHALL otherwise ignore the value and use the Current_User for the acting User, Board owner and Card creator. (Route: all write routes)

### Requirement 18: Response envelope and error handling (cross-cutting)

**User Story:** As a frontend developer, I want uniform responses, so that one client handler covers every route.

#### Acceptance Criteria

1. THE API SHALL return every response with the header `Content-Type: application/json` and a JSON body that is a Success_Envelope for status codes 200 to 399 and an Error_Envelope with a non-empty string `<message>` for status codes 400 to 599, except the status 200 response to GET /api/docs (an HTML document), the status 200 response to GET /api/openapi.json (the OpenAPI_Document as raw JSON, not wrapped in the Success_Envelope) and the responses to requests for Swagger_UI_Assets, which Requirement 24 specifies. (Route: all routes)
2. THE API SHALL serialize every identifier as a lower-case hyphenated 36-character UUID string and every timestamp as an ISO 8601 string in UTC with an explicit UTC offset designator (`Z` or `+00:00`). (Route: all routes)
3. IF a request body is not valid JSON, or is valid JSON whose top-level value is not an object (array, string, number, boolean or null), THEN THE API SHALL return status 400 with an Error_Envelope and leave the data unchanged. (Route: all routes that accept a body)
4. IF a request uses a path that matches no route, THEN THE API SHALL return status 404 with an Error_Envelope. (Route: application error handlers)
5. IF a database constraint violation reaches the API, THEN THE API SHALL roll back the transaction, leave the data unchanged, and return an Error_Envelope with status 409 for a unique violation and status 400 for any other constraint violation, with a message that contains no SQL text. (Route: application error handlers)
6. IF an unhandled exception occurs, THEN THE API SHALL roll back the transaction, log the exception with its traceback, and return status 500 with an Error_Envelope whose message text is the same for every unhandled exception and contains no exception text, SQL or file path. (Route: application error handlers)
7. IF validation of a request body or query parameter fails, THEN THE API SHALL build the Error_Envelope message from the Marshmallow field errors as one `<field>: <message>` entry per field error, with entries separated by `; ` and no leading or trailing separator. (Route: all routes that validate input)
8. IF a request uses an HTTP method that is not allowed on an existing path, THEN THE API SHALL return status 405 with an Error_Envelope. (Route: application error handlers)

### Requirement 19: CORS

**User Story:** As a frontend developer, I want the API to accept requests from the Next.js app, so that the browser can call it.

#### Acceptance Criteria

1. THE API SHALL read the allowed origins from the `CORS_ORIGINS` environment variable as a comma-separated list, trim leading and trailing whitespace from each entry, ignore empty entries, and use `http://localhost:3000` as the only allowed origin when the variable is unset or contains no non-empty entry. (Route: create_app)
2. WHEN a request carries an `Origin` header that exactly matches (case-sensitive, full string) an entry in `CORS_ORIGINS`, THE API SHALL return an `Access-Control-Allow-Origin` header whose value is that origin, and not `*`, on every response to that request regardless of status code. (Route: all routes)
3. WHEN a preflight `OPTIONS` request from a listed origin is received, THE API SHALL return status 200 or 204 without requiring an Access_Token, with `Access-Control-Allow-Origin` set to that origin, `Access-Control-Allow-Methods` containing GET, POST, PATCH, DELETE and OPTIONS, and `Access-Control-Allow-Headers` containing `Authorization` and `Content-Type`. (Route: all routes)
4. WHEN a request, including a preflight `OPTIONS` request, carries an `Origin` header that does not exactly match any entry in `CORS_ORIGINS`, THE API SHALL omit the `Access-Control-Allow-Origin` header from the response. (Route: all routes)
5. WHEN a request carries no `Origin` header, THE API SHALL omit the `Access-Control-Allow-Origin` header from the response and process the request as it would without CORS. (Route: all routes)

### Requirement 20: Configuration, structure and deployment

**User Story:** As a developer, I want environment-based configuration and a repeatable deployment, so that the API runs the same locally and on Railway.

#### Acceptance Criteria

1. WHEN `create_app` runs, THE API SHALL read `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRES` (default 3600 seconds, per Requirement 2), `CORS_ORIGINS` (default `http://localhost:3000`, per Requirement 19) and `SWAGGER_ENABLED` (default `true`, per Requirement 24) from environment variables, loading `backend/.env` with python-dotenv when the file exists and continuing without error when it does not. (Route: create_app)
2. THE Deployment_Config SHALL include a `backend/.env.example` file that is tracked by git and not matched by `.gitignore`. The file SHALL contain one `NAME=value` line for each of `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRES`, `CORS_ORIGINS` and `SWAGGER_ENABLED` (value `true`), each with a non-empty placeholder value and no real credential, secret or production host. (Route: create_app)
3. IF `JWT_SECRET_KEY` is unset or an empty string, THEN THE API SHALL raise an error from `create_app` whose message contains `JWT_SECRET_KEY`, return no application object and accept no requests. (Route: create_app)
4. THE API SHALL register one Flask Blueprint for each of auth, users, boards, columns, cards, comments, notifications, analytics and health on the application created by `create_app`. Each Blueprint SHALL have its own directory `app/blueprints/<name>/` containing the three files `routes.py`, `service.py` and `schema.py`, which makes 9 Blueprints and 27 files. (Route: create_app)
5. THE API SHALL keep SQLAlchemy queries and business rules in `service.py`, request parsing and validation in `schema.py` using Marshmallow, and HTTP concerns (reading the request, choosing the status code, building the response) in `routes.py`. `routes.py` SHALL contain no SQLAlchemy query, `schema.py` SHALL contain no database access, and `service.py` SHALL NOT use the Flask request or response objects. (Route: all routes)
6. THE Deployment_Config SHALL start the API with a Gunicorn command bound to `0.0.0.0:$PORT`, where `$PORT` is the value of the `PORT` environment variable. (Route: create_app)
7. THE Deployment_Config SHALL list Flask-JWT-Extended, Marshmallow, Flask-CORS, python-dotenv, Gunicorn, an OpenAPI generation library compatible with Marshmallow (apispec with apispec-webframeworks, or an equivalent) and an OpenAPI 3 document validator for the Test_Suite in `backend/requirements.txt`, each on its own line with a minimum version (`>=`) and an exclusive maximum version (`<`). THE Deployment_Config SHALL provide the Swagger_UI_Assets either as a package listed in `backend/requirements.txt` under the same version rule or as static files tracked by git. (Route: create_app)
8. WHEN Railway prepares a release, THE Deployment_Config SHALL run `flask db upgrade` as the Railway pre-deploy command before the Gunicorn command starts. (Route: create_app)
9. WHERE `backend/.env` sets a variable that is also set in the process environment, THE API SHALL use the process environment value and ignore the `backend/.env` value. (Route: create_app)

### Requirement 21: Security (non-functional)

**User Story:** As a user, I want my credentials protected, so that my account stays safe.

#### Acceptance Criteria

1. WHEN a User is created, THE API SHALL store in `password_hash` only a salted hash produced by a `werkzeug.security` hash function, such that the stored value is not equal to the submitted `password` and does not contain it as a substring, and two Users registered with the same `password` have different stored values. THE API SHALL store no plaintext password in any database column. (Route: POST /api/auth/register)
2. THE API SHALL return no `password` or `password_hash` field, at any nesting level, in any response body, including every Error_Envelope. (Route: all routes)
3. THE API SHALL write no password, Access_Token, `Authorization` header value or `JWT_SECRET_KEY` value to application logs at any log level, including the log entry written for an unhandled exception. After a request that sends a known `password` or Access_Token, the captured log output SHALL NOT contain that value as a substring. (Route: all routes)
4. THE API SHALL pass every value taken from a request body, query string or path to the database only as a SQLAlchemy bound parameter and SHALL build no SQL by string concatenation of request values. A request value such as `'; DROP TABLE users; --` SHALL be stored or matched as literal text and SHALL leave every table and row not targeted by the request unchanged. (Route: all routes)
5. IF a login request has an `email` that matches no User case-insensitively, or a `password` that does not match the stored hash of the matching User, THEN THE API SHALL return status 401 with the same status code and the same Error_Envelope body for both cases, so that the two responses differ in no body field and no header other than `Date`. (Route: POST /api/auth/login)

### Requirement 22: Performance (non-functional)

**User Story:** As a user, I want boards to open fast, so that the application feels responsive.

#### Acceptance Criteria

1. WHEN a Board_Member requests a Live_Record Board seeded with 50 Live_Record Columns and 5,000 Live_Record Cards (100 per Column), THE API SHALL return status 200 within 500 ms at the 95th percentile, measured from request sent to response body fully received over 100 consecutive sequential requests from one client, after 1 discarded warm-up request, with no other request running at the same time. (Route: GET /api/boards/<id>)
2. WHEN a Board_Member requests a Live_Record Board, THE API SHALL load the Board, its Live_Record Columns and their Live_Record Cards with exactly 3 database queries, one for each of the three. This count SHALL be the same for a Board with 1 Column and 0 Cards and for a Board with 50 Columns and 5,000 Cards. Authentication and membership lookups are not counted. (Route: GET /api/boards/<id>)
3. WHEN a Board_Admin requests analytics of a Live_Record Board seeded with 50 Live_Record Columns and 5,000 Live_Record Cards (100 per Column), THE API SHALL return status 200 within 500 ms at the 95th percentile, measured from request sent to response body fully received over 100 consecutive sequential requests from one client, after 1 discarded warm-up request, with no other request running at the same time. (Route: GET /api/boards/<id>/analytics)

### Requirement 23: Test coverage (non-functional)

**User Story:** As a developer, I want automated API tests, so that regressions are caught before deployment.

#### Acceptance Criteria

1. THE Test_Suite SHALL contain, for every route listed in a `(Route: ...)` tag of Requirements 1 to 16 (the Documentation_Routes are excluded here and covered by Requirement 24), at least one success test and at least one failure test. A success test asserts the documented 2xx status and the Success_Envelope payload. A failure test asserts a documented 4xx status for that route and the Error_Envelope, and asserts that the affected data is unchanged where the requirement states "leave ... unchanged". For GET /api/health, the failure test sends a method other than GET and asserts status 405. (Route: all routes)
2. THE Test_Suite SHALL contain comment tests that assert status 201 on a valid comment, status 400 naming `content` when `content` is missing, status 401 when the request has no Access_Token, and status 403 when a Current_User who is not the Comment owner (including a Board_Admin) updates or deletes a Comment. (Route: POST /api/cards/<id>/comments, PATCH /api/comments/<id>, DELETE /api/comments/<id>)
3. THE Test_Suite SHALL run against PostgreSQL 18 using the fixtures in `backend/tests/database/conftest.py`, and SHALL NOT use SQLite. (Route: all routes)
4. THE Test_Suite SHALL reach at least 80.0 percent line coverage of `backend/app/blueprints`, measured over one complete run of the Test_Suite from `backend/`. (Route: all routes)
5. THE Test_Suite SHALL contain, for each protected route (every route other than POST /api/auth/register, POST /api/auth/login and GET /api/health), one test that sends a request without an Access_Token and asserts status 401 with an Error_Envelope whose `error` value is a string, and one test that sends a request with a valid Access_Token and asserts a status other than 401. (Route: all protected routes)
6. IF measured line coverage of `backend/app/blueprints` is below 80.0 percent, THEN THE Test_Suite run SHALL finish with a non-zero exit status and report the measured percentage. (Route: all routes)
7. WHEN the Test_Suite is run once against an empty PostgreSQL 18 database, THE Test_Suite SHALL finish with zero failing tests and zero tests that depend on the execution order of other tests. (Route: all routes)

### Requirement 24: API documentation with Swagger UI

**User Story:** As a frontend developer, I want one interactive Swagger UI page, generated from the schemas of every blueprint, so that I can find each route, read its request and response shapes, and call it with my token.

#### Acceptance Criteria

1. THE API SHALL treat the Documentation_Routes and the Swagger_UI_Assets as enabled unless the `SWAGGER_ENABLED` environment variable, after trimming leading and trailing whitespace and comparing case-insensitively, equals `false`. An unset variable, an empty value and any other value SHALL mean enabled. (Route: create_app)
2. WHEN a GET request is sent to /api/docs while the Documentation_Routes are enabled, THE API SHALL return status 200 with a `Content-Type` header whose media type is `text/html` and an HTML body that loads Swagger_UI configured with the URL `/api/openapi.json`. (Route: GET /api/docs)
3. WHEN a GET request is sent to /api/openapi.json while the Documentation_Routes are enabled, THE API SHALL return status 200 with the header `Content-Type: application/json` and a body that is the OpenAPI_Document as a top-level JSON object, with no `data` or `error` wrapper key, and byte-for-byte identical for every request made during the life of one application instance. (Route: GET /api/openapi.json)
4. WHEN a request to a Documentation_Route or to a Swagger_UI_Asset carries no `Authorization` header, a malformed `Authorization` header, an invalid Access_Token or an expired Access_Token, THE API SHALL return the same successful response as for a request with a valid Access_Token and SHALL require no other credential. (Route: GET /api/docs, GET /api/openapi.json)
5. WHEN the HTML body returned by GET /api/docs references Swagger_UI_Assets, THE API SHALL serve each referenced asset from a path that starts with `/swagger-ui/` on the same host with status 200, and the HTML body SHALL reference no asset on another host. (Route: GET /api/docs)
6. WHILE `SWAGGER_ENABLED` disables the Documentation_Routes, THE API SHALL return status 404 with an Error_Envelope for GET /api/docs, GET /api/openapi.json and every path that starts with `/swagger-ui/`, as for any path that matches no route. (Route: GET /api/docs, GET /api/openapi.json)
7. IF a request to /api/docs or /api/openapi.json uses an HTTP method other than GET, HEAD or OPTIONS while the Documentation_Routes are enabled, THEN THE API SHALL return status 405 with an Error_Envelope, whether or not the request carries an Access_Token. (Route: GET /api/docs, GET /api/openapi.json)
8. THE API SHALL apply Requirement 19 to the Documentation_Routes and Swagger_UI_Assets: a request with an `Origin` header that exactly matches an entry of `CORS_ORIGINS` SHALL receive `Access-Control-Allow-Origin` set to that origin, and a request with any other `Origin` or no `Origin` SHALL receive no `Access-Control-Allow-Origin` header. (Route: GET /api/docs, GET /api/openapi.json)
9. THE OpenAPI_Document SHALL have an `openapi` field whose value starts with `3.`, an `info.title` equal to `RevoTask API`, a non-empty string `info.version`, and SHALL pass validation by an OpenAPI 3 validator with zero errors. (Route: GET /api/openapi.json)
10. THE OpenAPI_Document SHALL contain under `paths` exactly one operation for each row of the Route Traceability Matrix other than the rows for the Documentation_Routes and `create_app and error handlers`, identified by the HTTP method and by the path in which each `<name>` segment is written `{name}`. THE OpenAPI_Document SHALL contain no other operation. The row GET /api/cards (`assignee=me`, `search=`) SHALL be one operation. (Route: GET /api/openapi.json)
11. THE OpenAPI_Document SHALL declare each path parameter (`id`, `user_id`) of each operation as a required parameter with `in` equal to `path` and a string schema with format `uuid`. THE OpenAPI_Document SHALL declare for GET /api/cards the optional query parameters `assignee` (string, enum `me`) and `search` (string, `minLength` 1, `maxLength` 200), and for GET /api/notifications the optional query parameters `page` (integer, `minimum` 1, `default` 1) and `per_page` (integer, `minimum` 1, `maximum` 100, `default` 20), and SHALL declare no other query parameter on any operation. (Route: GET /api/openapi.json)
12. THE OpenAPI_Document SHALL declare for each operation that accepts a request body (POST /api/auth/register, POST /api/auth/login, PATCH /api/users/me, POST /api/boards, PATCH /api/boards/{id}, POST /api/boards/{id}/members, PATCH /api/boards/{id}/members/{user_id}, POST /api/boards/{id}/columns, PATCH /api/columns/{id}, PATCH /api/boards/{id}/columns/reorder, POST /api/columns/{id}/cards, PATCH /api/cards/{id}, PATCH /api/cards/{id}/position, POST /api/cards/{id}/comments and PATCH /api/comments/{id}) a required `requestBody` with the media type `application/json` and an object schema, and SHALL declare no `requestBody` on any other operation. (Route: GET /api/openapi.json)
13. THE OpenAPI_Document SHALL declare for each operation a response for its success status, which is 201 for POST /api/auth/register, POST /api/boards, POST /api/boards/{id}/members, POST /api/boards/{id}/columns, POST /api/columns/{id}/cards and POST /api/cards/{id}/comments, and 200 for every other operation. The response SHALL have the media type `application/json` and a schema that is an object with `data` as its only required property, where `data` describes the payload defined by the requirement of that route (the Success_Envelope shape). (Route: GET /api/openapi.json)
14. THE OpenAPI_Document SHALL declare for each operation, in addition to the success response, a response for each of these statuses that applies, with the media type `application/json` and a schema that is an object with the string property `error` as its only required property (the Error_Envelope shape): 401 for every operation other than POST /api/auth/register, POST /api/auth/login and GET /api/health; 404 for every operation that has a path parameter; 403 for every operation whose path contains a board, column, card or comment identifier; 400 for every operation that has a request body or a query parameter; 409 for POST /api/auth/register, PATCH /api/users/me, POST /api/boards/{id}/members, PATCH /api/boards/{id}/members/{user_id} and DELETE /api/boards/{id}/members/{user_id}. (Route: GET /api/openapi.json)
15. THE OpenAPI_Document SHALL list exactly 9 Blueprint_Tags in its top-level `tags` field (`auth`, `users`, `boards`, `columns`, `cards`, `comments`, `notifications`, `analytics`, `health`), and SHALL give each operation a `tags` list with exactly one element, equal to the name of the Blueprint that registers the route of that operation. (Route: GET /api/openapi.json)
16. THE OpenAPI_Document SHALL give each operation a `summary` that is a non-empty single-line string of at most 120 characters. (Route: GET /api/openapi.json)
17. THE API SHALL generate each request body schema, each query parameter schema and each response `data` schema of the OpenAPI_Document from the Marshmallow schema class that the route uses or that is defined in `schema.py` of the owning Blueprint for that purpose, including `CardPositionSchema` for PATCH /api/cards/{id}/position, such that the property names and the `required` list of the generated schema equal the field names and the required fields of that Marshmallow schema. THE API SHALL contain no hand-written JSON Schema dictionary for a request or response body. (Route: GET /api/openapi.json)
18. THE API SHALL declare the documentation of each operation (summary, parameters, request schema and response schemas) in the `routes.py` and `schema.py` files of the Blueprint that owns the route, and SHALL keep no per-route documentation in a file outside the 9 Blueprint directories. THE API SHALL declare in `create_app` or in one shared module only the `info` object, the top-level `tags`, the security scheme and the envelope components. (Route: create_app)
19. THE OpenAPI_Document SHALL declare under `components.securitySchemes` one scheme named `bearerAuth` with `type` equal to `http`, `scheme` equal to `bearer` and `bearerFormat` equal to `JWT`. THE OpenAPI_Document SHALL set `security` equal to `[{"bearerAuth": []}]` on every operation other than POST /api/auth/register, POST /api/auth/login and GET /api/health, and `security` equal to `[]` on those three operations. (Route: GET /api/openapi.json)
20. THE OpenAPI_Document SHALL contain the property `password` only in the request body schemas of POST /api/auth/register and POST /api/auth/login, and SHALL contain no property named `password` or `password_hash` in any response schema. Requirement 21 criterion 2 SHALL NOT apply to request body schemas inside the OpenAPI_Document. (Route: GET /api/openapi.json)
21. IF `create_app` runs while the Documentation_Routes are enabled and the OpenAPI_Document cannot be generated, including when a route registered under `/api/` has no documentation, THEN THE API SHALL raise an error from `create_app` whose message contains `OpenAPI`, return no application object and accept no requests. (Route: create_app)
22. THE Test_Suite SHALL contain a test that fetches /api/openapi.json, asserts status 200 and `Content-Type: application/json`, validates the body as an OpenAPI 3 document with zero errors, lists every route of the Flask URL map whose path starts with `/api/` except the Documentation_Routes and the methods HEAD and OPTIONS, and asserts that each pair of method and path (with `<converter:name>` written `{name}`) appears as one operation, that the OpenAPI_Document contains no other operation, and that every operation has a `tags` list of one element that is one of the 9 Blueprint_Tag names. (Route: GET /api/openapi.json)
23. THE Test_Suite SHALL contain a test that sends GET /api/docs, asserts status 200 and a `Content-Type` of `text/html`, and a test that repeats both Documentation_Routes requests with an invalid Access_Token and asserts status 200. THE Test_Suite SHALL also contain a test that starts the application with `SWAGGER_ENABLED=false` and asserts status 404 with an Error_Envelope for both Documentation_Routes. The Documentation_Routes are not protected routes for the purpose of Requirement 23 criterion 5. (Route: GET /api/docs, GET /api/openapi.json)

## Route Traceability Matrix

| Route | Requirements |
|-------|--------------|
| POST /api/auth/register | 1, 21 |
| POST /api/auth/login | 2, 21 |
| GET /api/users/me | 3 |
| PATCH /api/users/me | 3 |
| POST /api/boards | 4, 17 |
| GET /api/boards | 4 |
| GET /api/boards/<id> | 5, 17, 22 |
| PATCH /api/boards/<id> | 5, 17 |
| DELETE /api/boards/<id> | 5, 17 |
| GET /api/boards/<id>/members | 6, 17 |
| POST /api/boards/<id>/members | 6, 14, 17 |
| PATCH /api/boards/<id>/members/<user_id> | 6, 17 |
| DELETE /api/boards/<id>/members/<user_id> | 6, 17 |
| POST /api/boards/<id>/columns | 7, 17 |
| PATCH /api/columns/<id> | 7, 17 |
| DELETE /api/columns/<id> | 7, 17 |
| PATCH /api/boards/<id>/columns/reorder | 8, 17 |
| POST /api/columns/<id>/cards | 9, 14, 17 |
| PATCH /api/cards/<id> | 9, 14, 17 |
| DELETE /api/cards/<id> | 9, 17 |
| PATCH /api/cards/<id>/position | 10, 14, 17 |
| GET /api/cards (`assignee=me`, `search=`) | 11 |
| POST /api/cards/<id>/comments | 12, 14, 17, 23 |
| GET /api/cards/<id>/comments | 12, 17 |
| PATCH /api/comments/<id> | 12, 17, 23 |
| DELETE /api/comments/<id> | 12, 17, 23 |
| GET /api/notifications | 13 |
| PATCH /api/notifications/<id>/read | 13 |
| GET /api/boards/<id>/analytics | 15, 17, 22 |
| GET /api/health | 16 |
| GET /api/docs | 24 |
| GET /api/openapi.json | 24 |
| create_app and error handlers | 17 to 20, 24 |

Requirement 24 documents every route above except GET /api/docs, GET /api/openapi.json and `create_app and error handlers`.
