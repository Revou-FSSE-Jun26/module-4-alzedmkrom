# Changelog


## V1 - Initial Release
- Initial requirements generated for the RevoTask Flask REST API (spec `backend`, 2026-11-14).
- Initial implementation scope established: Auth, Users, Boards, Board members, Columns, Cards, Comments, Notifications, Analytics, Health, plus cross-cutting authorization, error envelope, CORS, configuration, deployment and non-functional requirements.
- The database schema, models and reference queries stay owned by the `database` spec (`.kiro/specs/database/`). This spec consumes them and does not redefine them.
- Design (`design.md`) and tasks (`tasks.md`) are not yet written. No part of this spec is implemented.
- Requirements 1 to 23 went through automatic detailing before review. It added edge cases and exact response shapes. Decisions added by the detailing: an empty `PATCH /api/cards/<id>` body returns 400, ties in `order` place the moved item after its sibling, and the reorder and move responses carry `rebalanced` (card move adds `siblings` when true).

## V2 - 2026-11-14

### Changes
- Type: Specification change.
- Added Requirement 24 (API documentation with Swagger UI): one Swagger UI page at GET /api/docs and the OpenAPI 3 document at GET /api/openapi.json, with the 9 blueprints as tagged groups, every route as an operation, schemas generated from the Marshmallow schemas of each blueprint, a Bearer JWT security scheme, an optional `SWAGGER_ENABLED` switch, and tests.
- Requirement 17 criterion 1 and Requirement 18 criterion 1: added an exception for the Documentation_Routes and the Swagger UI assets.
- Requirement 20 criteria 1, 2 and 7: added `SWAGGER_ENABLED` (default `true`) to the environment variables and `.env.example`, and listed an OpenAPI generation library compatible with Marshmallow, an OpenAPI 3 validator and the Swagger UI assets.
- Requirement 23 criterion 1: excluded the two documentation routes, which Requirement 24 tests cover. The coverage criterion is unchanged.
- Route Traceability Matrix: added rows for GET /api/docs and GET /api/openapi.json, and added 24 to the `create_app and error handlers` row.
- Glossary: added OpenAPI_Document, Swagger_UI, Blueprint_Tag, Documentation_Routes and Swagger_UI_Assets.
- Introduction: added "Assumptions made for version V2". The request is read as one Swagger UI for the whole app with one tag per blueprint.

### Reason
- The user asked for Swagger UI documentation for each blueprint or API of the app.

### Impact
- Requirements: 17 (criterion 1), 18 (criterion 1), 20 (criteria 1, 2, 7), 23 (criterion 1), new 24, Glossary, Introduction, Route Traceability Matrix.
- Design components: none yet. `design.md` does not exist. It must cover the OpenAPI assembly in `create_app`, per-blueprint documentation in `routes.py` and `schema.py`, and static asset serving under `/swagger-ui/`.
- Implementation tasks: none yet. `tasks.md` does not exist. Existing code is not changed by this version, and `backend/.env.example` and `backend/requirements.txt` still need the new entries when implemented.
- Cross-requirement notes: Requirement 24 criterion 20 limits Requirement 21 criterion 2 for request schemas in the OpenAPI_Document. Requirement 24 criterion 23 excludes the Documentation_Routes from Requirement 23 criterion 5.

### Design (generated under V2, no version change)
- Type: Design document. `design.md` was generated from `requirements.md` V2 and carries `Version: V2`. No requirement, scope or agreed behavior changed, so the version is not incremented.
- Affected design components: new `design.md` covering `app/common/`, the 9 blueprints, `create_app` changes, OpenAPI assembly, deployment files and the test strategy.
- Choices the requirements left open are listed in `design.md`, section "Decisions Beyond the Requirements and Open Points" (for example the login field `access_token` with a nested `user` object, strict versus lenient unknown-field handling, and the order in which the `<user_id>` of member routes is resolved). If any of them is rejected, record it as V3.
- Implementation tasks: `tasks.md` is not created yet. No part of the spec is implemented.

### Tasks (generated under V2, no version change)
- Type: Implementation plan. `tasks.md` was generated from `requirements.md` V2 and `design.md` V2 and carries `Version: V2`. No requirement, scope or agreed behavior changed, so the version is not incremented.
- Affected implementation tasks: new `tasks.md` with 18 top-level items, one task for every route of the design's route table (routes 1 to 30 and the documentation routes), the 30 correctness properties as separate optional property-test tasks, and a Task Dependency Graph of 11 waves.
- Structure choice: task 3.1 creates the nine blueprint packages with stub `routes.py` files and the `register_blueprints` registry once, so route tasks of different blueprints can run in parallel.
- Nothing in `tasks.md` is implemented yet.
