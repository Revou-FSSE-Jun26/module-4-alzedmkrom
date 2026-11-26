# backend.md Changelog

Newest first. Versions v1 to v4 were rewritten over and cannot be downloaded; their entries are reconstructed from the conversation and summarize changes rather than showing exact diffs. All versions were produced on 2026-11-14. The current file is v7.

Keep this file outside `.kiro/steering/` (for example `docs/`) so Kiro does not load it as context.

---

## v7 (current): Rubric alignment and soft-deleted cards

Edits after checking the files against the assignment checklist.

**Changed**
- **File names (BE-STR-01, BE-STR-03, BE-NTF-01):** each blueprint now has `routes.py`, `service.py`, and `schema.py` (singular), as the checklist says. They were `services.py` and `schemas.py`.
- **Eight blueprints:** the separate `members` blueprint is gone. Board member management lives in the `boards` blueprint (BE-AZ-07). The domains are exactly `auth`, `boards`, `columns`, `cards`, `comments`, `notifications`, `analytics`, `users`.
- **Order attribute:** the model attribute and API field are both `order`, and only the database column is named `position`. The "schemas map between the two" wording is removed (section 6 intro, BE-SVC-02).
- **Field lengths:** maximum lengths of stored text are now defined only in `database.md` (DB-SCH-01). BE-VAL-03 and BE-VAL-05 take them from there, and the numbers are removed from the BE-VAL-05 table, so the limits are not duplicated.
- **Card delete is a soft delete:** the BE-AZ-02 matrix row, BE-AZ-04 (soft-deleted cards are ignored by the foreign-card check, and comments are hidden, not removed), BE-ANL-01 (excluded from every figure), BE-SVC-05 (non-deleted cards only), and the deviations list are updated.

**Added**
- BE-SVC-06: `DELETE /api/cards/<id>` sets `deleted_at` and returns 204. A soft-deleted card behaves as nonexistent (404 for it and its comments), every card query goes through `Card.active()`, and deleting a column or board still removes cards permanently through the cascade.
- BE-TST-04: a test for the soft-delete behavior.

**Related changes in other files**
- `database.md` v3: `cards.deleted_at`, the Soft delete section, `db.Float` models, partial indexes, and the single definition of text lengths.
- `frontend.md` v2: `BaseButton` rules for My Tasks and Profile, and validation limits sourced from `database.md`.

---

## v6: Frontend alignment

Edits so the frontend requirements and the backend agree. Made before writing `frontend.md`.

**Changed**
- Assigned-tasks endpoint moved from `GET /api/users/me/cards` (users blueprint) to `GET /api/cards?assignee=me` (cards blueprint), as the frontend `/my-tasks` requirement states. `assignee` is required and accepts only `me`; a missing or different value returns 422, so there is still no endpoint that lists all cards. Updated in BE-SVC-05, BE-STR-01, BE-VAL-05, BE-ERR-03, BE-TST-04, and the deviations list.

**Added**
- `GET /api/notifications` returns `unread_count`, the total unread across all pages, so the notification bell can show a true count (BE-NTF-03, with a pointer in BE-ERR-03).
- Board, column, and card payloads include `created_by` (user id or null), so the UI can show the own-only delete controls without a second request (BE-SVC-04).

**Related change in another file**
- `database.md` v2: index references updated to the new endpoint path.

---

## v5

Small consistency edit after `database.md` was created.

**Changed**
- BE-SVC-02: "ordered by `order`" is now "ordered by position (the API field `order`)".
- Section 6 intro: added that the API field `order` is stored in the model attribute `position`, and schemas map between them. Reason: `order` is a reserved SQL word, so `database.md` names the column `position`.

---

## v4: Cross-check against the original requirements

Full rewrite after re-reading the endpoint list. Fixed six problems and filled gaps.

**Fixed**
- **Ordering contradiction (BE-ORD-01 to 03):** the client now computes `order` and the server validates and stores it, matching `CardPositionSchema`. The server picks positions only when creating items (appended to the end). Collisions and gaps under `MIN_GAP` trigger a server rebalance returning `"rebalanced": true` and the new sibling orders. Constants `ORDER_STEP = 1024.0` and `MIN_GAP = 1e-6` are defined here.
- **Check order (BE-AZ-03):** now authentication (401), then visibility (404), then permission (403). It was visibility first.
- **`is_done` (BE-VAL-05, BE-AZ-02, BE-ORD-03):** `ColumnUpdateSchema` accepts it, Admin only, at most one done column per board.
- **Member activity (BE-ANL-01):** redefined as cards created, comments added, cards assigned, and assigned cards completed this week, all from joins with no activity log.
- **Stale assignees (BE-AZ-06):** removing a user from a board clears their card assignments in the same transaction.
- **Notification noise (BE-NTF-01):** "card moved" fires only when the column changes.

**Added**
- BE-VAL-05: field list for every schema.
- BE-ERR-05: success shapes (bare object, `{"items": [...]}`, snake_case, ISO-8601 UTC with `Z`); malformed path UUID returns 404.
- Email normalization (trim and lowercase) in BE-VAL-03.
- BE-NTF-03: notification payload, `type` list, stored `message`, idempotent read endpoint.
- New Analytics section (BE-ANL-01) with the response shape; routes and tests renumbered into sections 7 to 11.
- "Deviations from the literal endpoint list" section.
- Board deletion notifies every other member and Admin, with recipients collected before the cascade.
- Tests: BE-TST-03 and BE-TST-04 cover the 401/404/403 order, rebalancing, assignment clearing, email case, and malformed UUIDs.

**Changed**
- Front matter: `inclusion: fileMatch` on `**/*.py` became `inclusion: always`, so the file also loads during spec writing.
- `GET /api/boards` is paginated with the standard envelope.

---

## v3: User types, delete rules, assigned tasks

Edits to v2 after you restated the scenario's two user types and the delete rules.

**Added**
- "User types" section: Member and Admin are the primary roles; Guest and Anonymous are secondary read-only viewers.
- BE-SVC-05: `GET /api/users/me/cards` so Members can track assigned tasks (scenario capability that had no endpoint).
- Notification trigger: when an Admin deletes someone else's card, column, or board, the creator is notified with a fixed message.

**Changed**
- BE-AZ-04: only another member's card blocks a Member from deleting a column (409 `COLUMN_HAS_FOREIGN_WORK`). Comments no longer count as foreign work, and a Member can always delete their own card. This reverted a stricter rule I had added beyond what you asked.
- BE-AZ-02 matrix: "Delete column" and "Delete card" split into separate rows.
- Co-admins confirmed as equals; any Admin can delete the board.

---

## v2: Per-board roles

Full rewrite replacing the global-role model.

**Changed**
- Removed `users.role`. Roles live per board: the board creator becomes its Admin; Members are promoted by Admins; users without a membership are Guests; no token means Anonymous.
- Registration creates a plain user and never accepts a role. No seed-admin script.
- Boards are public by default (`is_public = true`), and Admins can make them private.
- Co-admins allowed, with last-admin protection (`LAST_ADMIN`).
- `GET /api/boards` gets a `scope` parameter (`mine` or `public`).
- Board responses include `my_role`.
- Added `@auth_optional` for three public read endpoints.
- Member management endpoints moved under `/api/boards/<id>/members`, with role changes through `PATCH .../members/<user_id>`. `PATCH /api/users/<id>/role` was dropped.
- Public responses use `PublicUserSchema` (id and name only).
- Cross-board isolation tests added.

**Decisions recorded**
- The group-based model (groups owning boards) was proposed and scrapped before this version.
- Admin comment moderation was proposed and reverted: comments stay owner-only for edit and delete, including for Admins.

---

## v1: First full draft

First complete `backend.md`, built on global roles.

**Included**
- Flask blueprints (`routes.py`, `schemas.py`, `services.py` per domain) with thin routes.
- Marshmallow validation with unknown fields rejected.
- Single error shape, status code map, pagination envelope.
- Password hashing, JWT with expiry, shared auth decorator.
- Global `users.role` (`guest`, `member`, `admin`) plus a `board_members` table for access; permission matrix in `permissions.py`; 404 for non-members and 403 for insufficient role.
- Strict deletes: Members delete only what they created and never cascade over others' work; Admins delete anything. Comments owner-only.
- Float ordering with server-side midpoint, rebalance, and same-board move check.
- Services own commits and rollbacks; eager loading to avoid N+1.
- Notification triggers defined in one place.
- Security configuration and a pytest strategy with per-role test cases.
- Admin-only member endpoints in a `members` blueprint, and `PATCH /api/users/<id>/role`.
- Front matter: `inclusion: fileMatch` on `**/*.py`.
