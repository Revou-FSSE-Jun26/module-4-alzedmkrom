# Changelog


## V1 - Initial Release
- Initial requirements generated for the RevoTask Next.js frontend (spec `frontend`, 2026-11-14).
- Initial implementation scope established: authentication (register, login, session cookie, route guard, logout), Dashboard, Board Detail Kanban, columns, cards, drag-and-drop, card detail with comments, card search, My Tasks, Profile, notifications, board members and analytics for administrators, shared components, API client and error handling, responsive layout, accessibility, rendering strategy, type safety, Component_Tests, Playwright E2E_Suite, and Vercel deployment and configuration (27 requirements).
- The API contract stays owned by the `backend` spec (`.kiro/specs/backend/`, requirements V2) and the schema by the `database` spec. This spec consumes them and does not redefine them.
- Every acceptance criterion carries a page, component, hook or lib file tag, and the document ends with a page and file traceability matrix.
- Decisions the brief and the backend spec left open are listed in `requirements.md`, section "Decisions Beyond the Brief" (16 items, for example the token stored in Auth_Context plus a non-httpOnly cookie, the search filter on the open board by card id, the column select as keyboard and touch alternative to dragging, and the admin pages `/boards/[id]/members` and `/boards/[id]/analytics`).
- Design (`design.md`) and tasks (`tasks.md`) are not yet written. No part of this spec is implemented.
- Requirements 1 to 27 went through automatic detailing before review. It added edge cases, exact texts and 11 new criteria. Added decision 17 (detailing choices) to the requirements. Cross references were updated (for example the error boundary is now Requirement 10.13) and the traceability matrix was rebuilt.

## V2 - 2026-11-14
Type: Specification change. No design or implementation exists yet, so there is no design or implementation change. The backend contract is unchanged (`POST /api/auth/register` returns 201 with `{id, name, email, created_at}` and no token; `POST /api/auth/login` returns `{access_token, token_type, expires_in, user}`).

### Changes
- Decision 5 "Registration does not sign in" is replaced by "Registration signs in". After a 201 from register, the Register_Page sends one `POST /api/auth/login` with the same trimmed email and the same password, calls `login` from Auth_Context and redirects to `/`. If the auto-login fails, it shows the success toast "Account created. Please log in." through Toast_Wrapper and redirects to `/login`.
- Requirement 3 (Registration page): criterion 4 now sends the trimmed email and keeps the button disabled until register and login both finished or failed. Criterion 5 is replaced by the auto-login request. Criteria 6 and 7 keep their behavior (7 now says "register request"). New criteria 8 (login 200: `login`, one success toast, redirect to `/`), 9 (login failure: toast, redirect to `/login`, no Error_Handler, no form kept) and 10 (password only in component state, never stored or put in a URL). Criteria 1 to 3 are unchanged.
- Requirement 4, criterion 7 and the Glossary: checked, no change. A token in Auth_Context still redirects `/login` and `/register` to `/`, and the redirect target after `login` is the same `/`.
- Requirement 24, criterion 4: the list of inline outcomes now includes criterion 3.9.
- Requirement 25, criterion 3: the Register_Page component test now expects the register mock once, then the login mock once, `login` once and the redirect to `/`, plus the case where the login mock rejects (toast, redirect to `/login`, Error_Handler not called).
- Requirement 26: criterion 2 scenario (a) and criterion 3 step 1 no longer have a separate login step (step 1 reads "register a unique user and see the URL path `/` with the Header logout button visible", still 8 steps). Criterion 5 (mobile scenario) wording follows the auto-login. Criterion 7 states that the helper registers users and, where a scenario needs a logged-out state (scenario (b)), clicks logout afterwards.
- Traceability matrix: row `/register` now also lists 24.4. No other row changed.
- The version line of `requirements.md` is now V2. Requirements 1, 2, 4 to 23 and 27 are unchanged.

- Design generated (2026-11-20, `design.md`, Version V2). Type: design change (new document), no change to agreed behavior, so the version stays V2. Technology stack was verified against the npm registry: Next.js 16.4.6, React 19.3.1, TypeScript ~5.9.3, Tailwind CSS 4.3.5, react-hot-toast 2.6.1, Vitest 5.1.1 with React Testing Library, fast-check 4.10, Playwright 1.65. Points the requirements left open were resolved in the design: test runner is Vitest (Decision 13), the Route_Guard file is `proxy.ts` because Next.js 16 deprecates `middleware.ts` (Decision 16), and root layout failures are caught by an added `app/global-error.tsx`. The design adds files the requirements do not name (marked `(new)` in its directory layout) and lists 17 further decisions (F1 to F17) that the requirements did not specify. No requirement text changed.

- Task list generated (2026-11-20, `tasks.md`, Version V2). Type: specification change (new document), no change to agreed behavior, so the version stays V2. It holds 27 top-level groups and 130 leaf tasks with a 13-wave Task Dependency Graph: project scaffold with install verification, `lib`, `AuthContext`, hooks, shared components, app shell (`proxy.ts`, layout, error pages), every page with its components, then Vitest component and property tests (Properties 1 to 23), the Playwright suite, the README and `vercel.json`. Task 1.1 adds `frontend/.npmrc` with `allow-remote=all` because npm 12 defaults to `allow-remote=none`, which makes `npm install` fail with `EALLOWREMOTE` on Tailwind's optional WASM package (fetched by tarball URL); a dry run with `--allow-remote=all` resolved 438 packages with no peer conflicts on Node 26. Task 1.2 verifies the install without a flag, and the Notes ask for a check of the first Vercel build. Three small pure helpers that the design leaves open are listed as task-level additions (`changedCardFields` and `changedProfileFields` in `lib/validation.ts`, `visibleCards` in `lib/boardState.ts`) so that Properties 9 and 15 are testable at the lib layer. Nothing is implemented yet.

### Reason
- A user who just registered should land in the app without a second form. The backend returns no token on register, so the Frontend obtains it with a login request.

### Impact
- Affected requirements: 3 (criteria 4 to 10), 24.4, 25.3, 26.2, 26.3, 26.5, 26.7. Affected decision: 5.
- Affected design components: none yet (`design.md` does not exist). The Register_Page (`app/register/page.tsx`), `__tests__/auth/` and `e2e/` are the future design targets.
- Affected tasks: none yet (`tasks.md` does not exist).
- Update 2026-11-20: `design.md` now exists and covers the V2 changes in `components/auth/RegisterForm.tsx`, `__tests__/auth/RegisterForm.test.tsx` and `e2e/helpers/auth.ts`, `e2e/auth.spec.ts`, `e2e/kanban.spec.ts`, `e2e/responsive.spec.ts`. `tasks.md` was not written at that time and nothing was implemented.
- Update 2026-11-20 (later): `tasks.md` now exists. The V2 changes are covered by tasks 8.2 (`RegisterForm`), 19.2 (`RegisterForm` test), 24.1 (`e2e/helpers/auth.ts`) and 24.2 to 24.4 (`e2e/*.spec.ts`). Nothing is implemented.

## V3 - 2026-11-20
Type: Specification change (`tasks.md`). No requirement or design change, so `requirements.md` and `design.md` stay at V2.

### Changes
- Task 7 (app shell) names its direct predecessors in a `_Depends on:_` line under each subtask: 7.1 on 4.4, 2.6, 5.1 and 5.2; 7.2 on 7.1, 3.1 and 5.1; 7.3 on 7.2; 7.4 on 1.3, 2.9, 3.1 and 7.3; 7.5 on 2.8; 7.6 on 5.1; 7.7 on 1.3, 5.1 and 7.6; 7.8 and 7.9 on 1.3.
- The `tasks.md` overview no longer states that all tasks are independent. It notes that task 7 carries the explicit dependencies.
- The version line of `tasks.md` is now V3. Subtask details, requirement references and checkboxes are unchanged.

### Reason
- The task tool could not place tasks 7.1 to 7.4 in the dependency order. No predecessor was written for task 7 in the spec, and the 13-wave Task Dependency Graph named in the V2 entry is not in `tasks.md`. This entry writes the predecessors into the spec. It does not add the wave graph.

### Impact
- Affected requirements: none.
- Affected design components: none.
- Affected tasks: 7.1 to 7.9. Tasks 7.5 to 7.9 were implemented before this version. Tasks 7.1 to 7.4 are not implemented.
- Tasks 1 to 6 and 8 to 27 have no dependency lines yet and are not changed by this version.
- Tasks: task 7 and sub-task 7.1 reset to not started, because 7.1 was started but its file was never written. Sub-task 7.7 moved from wave 3 to wave 4, because it depends on 7.6, which is in wave 3. No requirement or design change.
