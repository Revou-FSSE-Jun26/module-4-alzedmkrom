---
inclusion: always
---

# RevoTask Frontend Guidelines

Stack: Next.js 16.x (App Router) + React + TypeScript (strict) + Tailwind CSS + `react-hot-toast` + native HTML5 Drag and Drop. Tests: Vitest + React Testing Library + MSW. Node.js 20.9 or newer.
Every guideline has an ID, a **Rule**, a **Rationale**, and a **RevoTask example**. Cite the ID when reporting a violation (e.g. "violates FE-DND-03").

## Scope and boundaries

This file owns: pages, components, hooks, client state, the session flow, forms, UX states, and how the UI consumes the API.

This file does NOT own, and must not restate. Reference by ID instead:
- The error body, status codes, and pagination envelope: `backend.md` section 3 (BE-ERR-01 to 05).
- The permission matrix and the viewer's role: BE-AZ-02 and BE-SVC-04.
- Ordering constants and formulas: BE-ORD-01 and BE-ORD-02.
- Input limits per field: the column lengths in `database.md` (DB-SCH-01) and the schema rules in BE-VAL-05.
- Notification types and payload: BE-NTF-03.
- Anything about tables, columns, or cascades: `database.md`.
- The visual design (layout, colors, styling, component appearance): the reference file `.kiro/design-visual/design.html`, see FE-UX-04.

When the UI must copy a value from the backend (ordering constants, field limits), it lives in exactly one `lib/` file with a comment citing the backend rule ID.

## User types

RevoTask has two primary user types. Design every screen for them first.
- **Member:** creates boards, organizes work into columns, moves cards by drag-and-drop, collaborates through comments, and tracks their assigned tasks.
- **Admin:** manages member access, oversees every card on the board, and monitors team activity through analytics and notifications.

Guests (logged in, no membership on the board) and Anonymous visitors (not logged in) can only read public boards. Do not build features for them beyond reading, and do not let their needs change Member or Admin screens.

## Product decisions beyond the original requirements

These were deliberate decisions. Do not undo them, and do not add behavior that contradicts them.
- The JWT is kept in an httpOnly cookie so sessions survive refreshes and Server Components can read them, and it is also placed in `AuthContext` for Client Components (FE-AUTH-01, FE-AUTH-02).
- Registration signs the new user in automatically. The register response has no token, so the frontend calls the login Server Action with the same credentials and then opens `/`.
- Added UI the requirement list omits but the roles need: create board, add and rename columns, add and edit cards, delete controls, an Admin members panel, and an Admin analytics panel (FE-PAGE-07).
- A "Move to column" select in `CardDetailModal` is the keyboard and touch fallback for native drag-and-drop (FE-DND-05).
- Column reordering has no UI, even though the backend supports it.
- Forms inside dialogs use `BaseModal`. The `/login`, `/register`, and `/profile` forms are rendered inline on their pages.
- The assigned-tasks page uses `GET /api/cards?assignee=me`, as the requirement states.

---

## 1. Structure and server/client boundaries

### FE-STR-01 Framework, version, and language
- **Rule:** Use Next.js 16.x with the App Router only (no Pages Router). Pin the exact Next.js and React versions in `package.json` and commit the lockfile. TypeScript runs in `strict` mode and `any` is not allowed without a comment explaining why. Request-scoped APIs are used asynchronously (`await cookies()`, `await params`, `await searchParams`). Do not enable Cache Components or use `use cache`. When unsure how a Next.js 16 API behaves, read the current Next.js documentation instead of relying on memory.
- **Rationale:** Caching and request APIs changed across recent Next.js majors, so code written from older habits silently breaks or serves stale data.
- **RevoTask example:** `app/boards/[id]/page.tsx` declares `params` as a `Promise<{ id: string }>` and awaits it before fetching.

### FE-STR-02 Folder layout and file names
- **Rule:** Use this layout and these exact names:
  - `app/` for routes: `/` (dashboard), `login/`, `register/`, `boards/[id]/`, `my-tasks/`, `profile/`.
  - `components/shared/`: `BaseButton.tsx`, `BaseBadge.tsx`, `BaseModal.tsx`.
  - `components/board/`: `KanbanBoard.tsx`, `CardDetailModal.tsx`, `CommentList.tsx`, plus the other board components.
  - `components/layout/`: `NotificationBell.tsx` and the header.
  - `hooks/`: `useDragAndDrop.ts`, `useNotifications.ts`, `useErrorHandler.ts`.
  - `lib/`: `apiClient.ts`, `errors.ts`, `toast.ts`, `ordering.ts`, `validation.ts`, `roles.ts`.
  - `context/`: `AuthContext.tsx`. `types/`: API payload types.
- **Rationale:** A fixed layout lets a reviewer find anything quickly and lets AI output be checked against a known shape.
- **RevoTask example:** the drag hook is `hooks/useDragAndDrop.ts`, not `lib/dnd.ts` or an inline function in `KanbanBoard.tsx`.

### FE-STR-03 Server Components by default
- **Rule:** Pages and layouts are Server Components. Add `"use client"` only to components that need state, effects, event handlers, or browser APIs. The Dashboard (`/`) and Board Detail (`/boards/[id]`) are Server Components that fetch on the server and pass the data as props to Client Components. `KanbanBoard` is a Client Component that owns the drag state. Initial page data is never fetched in a `useEffect`.
- **Rationale:** Server fetching avoids loading spinners on first paint and keeps data fetching out of the browser bundle.
- **RevoTask example:** `app/boards/[id]/page.tsx` fetches the board, then renders `<KanbanBoard initialBoard={board} />`.

### FE-STR-04 API types mirror the backend
- **Rule:** Types in `types/` mirror backend payloads exactly, with snake_case field names (`my_role`, `created_by`, `completed_at`). There is no renaming or mapping layer. The error body type mirrors BE-ERR-01. Do not invent fields: if a field is missing from the payload, report it as a backend question.
- **Rationale:** Renaming layers drift from the API and hide bugs.
- **RevoTask example:** `Card` has `created_by: string | null` and `assignee: { id: string; name: string } | null`, as returned by the board endpoint.

---

## 2. Authentication and session

### FE-AUTH-01 Token storage
- **Rule:** After a successful login, a Server Action stores the JWT in an httpOnly cookie (`Secure` in production, `SameSite=Lax`, lifetime from the `expires_in` value in the login response). The token is never written to `localStorage`, `sessionStorage`, or a non-httpOnly cookie, and is never logged.
- **Rationale:** The cookie lets the session survive a refresh and lets Server Components read it. The token also reaches `AuthContext` in memory (FE-AUTH-02) because Client Components attach it to requests, so the cookie protects it at rest, not from every script on the page. That is why FE-SEC-01 forbids raw HTML.
- **RevoTask example:** refreshing `/my-tasks` keeps the user logged in, because the server reads the cookie.

### FE-AUTH-02 AuthContext is hydrated by the root layout
- **Rule:** The root layout (a Server Component) reads the cookie and, when present, calls `GET /api/users/me`. It passes `{ token, user }` to `AuthProvider`, which Client Components read through `useAuth()`. Server Components never use `AuthContext`; they read the cookie and pass the token to `apiClient`. The login form is a Client Component with controlled inputs that calls a login Server Action; on success it navigates and calls `router.refresh()` so the layout re-hydrates the context. The profile form updates `user` in `AuthContext` after a successful save.
- **Rationale:** React context does not exist in Server Components, and the backend's login response contains no user.
- **RevoTask example:** `/profile` is pre-filled from `useAuth().user`, which the layout loaded from `GET /api/users/me`.

### FE-AUTH-03 Logout
- **Rule:** Logout calls a Server Action that deletes the cookie, then clears `AuthContext` and redirects to `/login`.
- **Rationale:** A leftover cookie or context value keeps the previous user's data reachable.
- **RevoTask example:** after logout, the header shows "Log in" and `/my-tasks` redirects to `/login`.

### FE-AUTH-04 Expired or invalid sessions
- **Rule:** A 401 from any API call (other than the login request itself) clears the session and redirects to `/login?next=<current path>`, with one "Session expired" toast per redirect. A 401 on the login request is a wrong-credentials error shown inline ("Invalid email or password"). Server Components catch `ApiError` with status 401 and call `redirect`. The `next` value must be a same-origin relative path (FE-SEC-03).
- **Rationale:** One policy for 401 avoids half-logged-in states and toast spam.
- **RevoTask example:** an expired token on `/my-tasks` sends the user to `/login?next=/my-tasks`.

### FE-AUTH-05 Route access
- **Rule:** `/` and `/boards/[id]` are open to Anonymous visitors, so public boards can be read. `/my-tasks` and `/profile` redirect Anonymous visitors to `/login`. `/login` and `/register` redirect logged-in users to `/`. Checks run on the server (in the page or layout, or the framework's request-interception file; use the name in the current Next.js docs), never only in a Client Component.
- **Rationale:** Client-only guards flash protected content before redirecting.
- **RevoTask example:** an Anonymous visitor opening a public board sees it read-only, with a "Log in to contribute" prompt.

---

## 3. API client and errors

### FE-API-01 One client for all backend calls
- **Rule:** `lib/apiClient.ts` is the only place that calls `fetch` for the backend. It is a typed wrapper (`apiClient.get<T>`, `post`, `patch`, `delete`) that reads the base URL from `API_BASE_URL` on the server and `NEXT_PUBLIC_API_BASE_URL` in the browser, and throws a clear error if the variable is missing. It takes the token as an explicit option, attaches `Authorization: Bearer <token>` when one is given, and never imports `AuthContext` or `cookies()` itself. A 204 response returns `undefined`.
- **Rationale:** One client means one place to fix headers, errors, and base URLs, and passing the token explicitly keeps it usable from both server and client code.
- **RevoTask example:** `apiClient.patch<Card>("/api/cards/" + id + "/position", body, { token })`.

### FE-API-02 Explicit fetch caching
- **Rule:** Every server-side call through `apiClient` sets `cache: "no-store"`. No request is cached or revalidated on a timer unless a guideline says so.
- **Rationale:** Boards change constantly, and cached responses can show one user's data or stale roles to another.
- **RevoTask example:** the Dashboard always shows boards created a minute ago.

### FE-API-03 ApiError
- **Rule:** `lib/errors.ts` exports `ApiError` with `statusCode: number`, `message: string`, `code: string | null`, and `details: Record<string, string[]> | null`. `apiClient` throws it for every non-2xx response, filling the fields from the BE-ERR-01 body. A network failure throws `ApiError` with `statusCode: 0` and `code: "NETWORK_ERROR"`. A non-JSON error body (for example an HTML 502) throws `ApiError` with the response status and `code: "UNKNOWN"`.
- **Rationale:** Components must handle one error type, whatever went wrong.
- **RevoTask example:** a 422 on `PATCH /api/cards/<id>/position` becomes `ApiError { statusCode: 422, code: "VALIDATION_ERROR", details: { order: ["Must be greater than 0."] } }`.

### FE-API-04 Toast wrapper
- **Rule:** `lib/toast.ts` is the only file that imports `react-hot-toast`. It exports helpers wrapping `toast.success()`, `toast.error()`, and `toast.loading()` (the latter returns an id that can be dismissed). `<Toaster />` is mounted once, in the root layout.
- **Rationale:** One wrapper keeps toast styling and duration consistent and makes the library replaceable.
- **RevoTask example:** saving a profile calls the success helper from `lib/toast.ts`, not `toast.success` directly.

### FE-API-05 useErrorHandler mapping
- **Rule:** `hooks/useErrorHandler.ts` turns an `ApiError` into a user-facing toast. It checks `code` overrides first, then `statusCode`:

| Condition | Behavior |
|---|---|
| `statusCode` 401 | Handled by FE-AUTH-04, no extra toast |
| 403 | "You don't have permission to do that." |
| 404 | "That item no longer exists." |
| 409 | The server's `message` (known codes such as `COLUMN_HAS_FOREIGN_WORK`, `LAST_ADMIN`, `EMAIL_TAKEN`, and `ALREADY_MEMBER` may have friendlier text) |
| 422 | No toast when field errors are shown inline (FE-FRM-02); otherwise "Please check the highlighted fields." |
| 0 (`NETWORK_ERROR`) | "Can't reach the server. Check your connection." |
| 5xx or unknown | "Something went wrong. Please try again." |

Components never build their own messages from `statusCode`, and never show raw `details`, stack traces, or error bodies.
- **Rationale:** Consistent messages, and no internals shown to users. Status meanings are defined in BE-ERR-02.
- **RevoTask example:** a Member deleting a column that holds another member's card sees the server's 409 message, and the column stays on screen.

---

## 4. Pages

### FE-PAGE-01 `/register` and `/login`
- **Rule:** Both are Client Component forms with controlled inputs and client-side validation (FE-FRM). `/register` submits `POST /api/auth/register`, then calls the login Server Action with the same email and password (auto-login). On success it shows a success toast, refreshes the layout so `AuthContext` loads the new user, and opens `/`. If the auto-login fails, it shows the "Account created. Please log in." toast and redirects to `/login`. A 409 `EMAIL_TAKEN` is shown on the email field. `/login` follows FE-AUTH-02 and FE-AUTH-04.
- **Rationale:** The register response has no token, so the frontend signs the user in with the same credentials. The user does not have to type them twice.
- **RevoTask example:** registering `ana@example.com` twice shows "Email already in use" under the email input.

### FE-PAGE-02 `/` Dashboard
- **Rule:** A Server Component that fetches `GET /api/boards`, reading `scope` and `page` from `searchParams`. The default scope is `mine` for logged-in users and `public` for Anonymous visitors, and logged-in users can switch between them. It renders board cards with the pagination controls from the BE-ERR-03 envelope, an empty state, and a "Create board" button for logged-in users only.
- **Rationale:** The endpoint is paginated and scoped, so the URL must carry both for links and refreshes to work.
- **RevoTask example:** `/?scope=public&page=2` shows the second page of public boards.

### FE-PAGE-03 `/boards/[id]` Board Detail
- **Rule:** A Server Component that awaits `params`, fetches `GET /api/boards/<id>`, and renders columns and cards in a Kanban layout through `KanbanBoard`. A 404 calls `notFound()`, and a 401 follows FE-AUTH-04. The route has `loading.tsx` and `error.tsx`. The viewer's `my_role` is passed down to every child that needs it (FE-ROLE-01).
- **Rationale:** The server fetch gives a fast first paint, and the board page is where public boards must work for Anonymous visitors.
- **RevoTask example:** opening a private board as a non-member shows the standard not-found page.

### FE-PAGE-04 CardDetailModal and comments
- **Rule:** `CardDetailModal.tsx` is a Client Component that composes `CommentList.tsx` inside `BaseModal.tsx`. Comments load from `GET /api/cards/<id>/comments` when the modal opens and show oldest first. A controlled comment form submits `POST /api/cards/<id>/comments`, with the content limit from `lib/validation.ts`. Edit and delete controls appear only on comments whose `author.id` equals the current user's id, and only while `my_role` is `member` or `admin`. Deleting asks for confirmation. The modal also lets Members and Admins edit the title, description, assignee, and due date, and delete the card where FE-PAGE-07 allows.
- **Rationale:** Comments are owner-only for edit and delete, even for Admins (BE-AZ-04), so the UI must not offer actions the backend will refuse.
- **RevoTask example:** an Admin viewing another user's comment sees no edit or delete controls on it.

### FE-PAGE-05 `/my-tasks`
- **Rule:** A protected Server Component that fetches `GET /api/cards?assignee=me` (never `/api/cards` without `assignee=me`), using `page` from `searchParams`. Cards are grouped by `board_name`, keyed by `board_id`, with each group linking to `/boards/<board_id>`. It has an empty state and a loading skeleton. Pagination and the per-group "Open board" action use `BaseButton` (FE-UI-01).
- **Rationale:** The backend returns a flat paginated list, so grouping is a presentation concern, and the endpoint only supports the `me` form.
- **RevoTask example:** two cards from "Sprint 12" and one from "Marketing" render as two groups.

### FE-PAGE-06 `/profile`
- **Rule:** A protected page with a Client Component form, with controlled inputs pre-populated from `AuthContext`. It submits only `name` and `email` to `PATCH /api/users/me`, and only the fields that changed. There is no password field and no role field. On success it updates `AuthContext` and shows a success toast; a 409 email conflict is shown on the email field. Save and Cancel are `BaseButton`s (FE-UI-01).
- **Rationale:** The backend rejects unknown fields (BE-VAL-02), so sending extra fields causes 422s.
- **RevoTask example:** changing only the name sends `{"name": "Ana K."}`.

### FE-PAGE-07 Board management UI
- **Rule:** The board page provides these controls, each through a form in `BaseModal` or an inline control, and each handled with `useErrorHandler`:
  - **Any logged-in user:** create a board from the Dashboard.
  - **Members and Admins:** add and rename columns, add and edit cards, set the assignee, and the "Move to column" select (FE-DND-05).
  - **Admins:** rename the board, toggle public/private, set a column as done, delete any column or card, delete the board, a members panel (add by email, change role, remove), and an analytics panel.
  - **Members' own-only deletes:** a Member sees delete controls on a column or card only when its `created_by` equals the current user's id. The server still decides (BE-AZ-04), so a 409 or 403 is expected and handled.
  - Every delete or removal asks for confirmation in `BaseModal` with a destructive `BaseButton`.
  - The analytics and members panels fetch only when `my_role` allows them.
- **Rationale:** Without these screens Members and Admins could not do the jobs the scenario gives them.
- **RevoTask example:** an Admin adds a Guest by email in the members panel, then the Guest, after refreshing, can drag cards.

---

## 5. Forms and validation

### FE-FRM-01 Controlled, labelled inputs
- **Rule:** Every input is controlled (`value` and `onChange` bound to state). Every input has a visible `<label>` linked by `htmlFor`/`id`, the correct `type` (`email`, `password`), and sensible `autoComplete` values. Uncontrolled inputs and `ref`-read values are not allowed.
- **Rationale:** Controlled inputs make validation, pre-population, and testing predictable, and labels make forms usable with assistive technology.
- **RevoTask example:** the profile form's name input shows `user.name` and updates on every keystroke.

### FE-FRM-02 Client validation mirrors the backend; the server is the authority
- **Rule:** Field limits live in one file, `lib/validation.ts`, copied from the column lengths in `database.md` (DB-SCH-01) and the other schema rules in BE-VAL-05, with a comment citing them. Forms validate on submit (and on blur after the first submit) and show messages next to the field. When the server returns 422, `error.details` is mapped onto the matching fields; details that match no field are shown in a toast.
- **Rationale:** Client checks give quick feedback, but only the server's answer is final, and duplicated limits across components drift.
- **RevoTask example:** a card title over the limit shows an inline message before any request, and a server-side 422 on `title` shows the same place.

### FE-FRM-03 Submit behavior
- **Rule:** The submit button is disabled while the request is pending and shows a loading state, so double submits are impossible. On error, the form stays open, keeps what the user typed, and re-enables.
- **Rationale:** Losing input after an error is the most common form complaint.
- **RevoTask example:** a failed "Add comment" leaves the typed text in the box.

---

## 6. Shared components (`components/shared/`)

### FE-UI-01 BaseButton
- **Rule:** `BaseButton` has `variant` of `primary`, `secondary`, or `destructive` (default `primary`), a `loading` state that disables it and sets `aria-busy`, and a default `type="button"`. It forwards native button props. `destructive` is used only for deleting or removing something. With an `href` prop it renders a Next.js `Link` styled the same way, for navigation. Every clickable control that looks like a button uses `BaseButton`, including the pagination controls and "Open board" on `/my-tasks` and Save and Cancel on `/profile`. Raw `<button>` elements and one-off styled anchors are not allowed outside `BaseButton.tsx`.
- **Rationale:** One button component keeps variants, loading behavior, and accessibility consistent.
- **RevoTask example:** the "Delete board" confirmation uses `<BaseButton variant="destructive">`; the `/my-tasks` pagination uses `<BaseButton variant="secondary" href="?page=2">`; `/profile` ends with `<BaseButton type="submit" loading={saving}>Save</BaseButton>`.

### FE-UI-02 BaseBadge
- **Rule:** `BaseBadge` supports color variants (for example `gray`, `blue`, `green`, `yellow`, `red`) and always contains text at `text-sm` (FE-UX-03) in medium weight (`font-medium`), so it reads lighter than the semibold card titles. Color is never the only way meaning is shown.
- **Rationale:** Color-only status excludes color-blind users.
- **RevoTask example:** the board header shows `<BaseBadge color="blue">Admin</BaseBadge>` from `my_role`, and a "Done" badge on the done column.

### FE-UI-03 BaseModal
- **Rule:** `BaseModal` takes `open`, `onClose`, `title`, and children, and renders in a portal with `role="dialog"`, `aria-modal="true"`, and `aria-labelledby`. Escape and backdrop click close it (both disabled while a submit is pending), focus moves into the modal and returns to the trigger on close, focus stays trapped inside, and page scroll is locked while open. All dialog forms and all confirmation prompts use it.
- **Rationale:** A shared modal gives every dialog the same accessible behavior.
- **RevoTask example:** `CardDetailModal` wraps its content in `BaseModal`, and pressing Escape closes it.

### FE-UI-04 Styling
- **Rule:** Use Tailwind utility classes. Inline `style` is only for values computed at runtime. Shared components live in `components/shared/` and are imported from there.
- **Rationale:** One styling approach keeps the look consistent and the bundle small.
- **RevoTask example:** a column's width is a Tailwind class, not a hard-coded CSS pixel value in `style`.

---

## 7. Drag and drop

### FE-DND-01 Native HTML5 only
- **Rule:** Card dragging uses the native HTML5 Drag and Drop API (`draggable`, `onDragStart`, `onDragOver`, `onDrop`, `onDragEnd`) and the drag data type `application/x-revotask-card`. No drag-and-drop libraries are added. All of it is managed by `hooks/useDragAndDrop.ts`.
- **Rationale:** The requirement names the native API, and a hook keeps drag logic out of the board's markup.
- **RevoTask example:** `KanbanBoard` calls `const dnd = useDragAndDrop({ board, token })` and spreads handlers onto cards and columns.

### FE-DND-02 Position calculation lives in one pure function
- **Rule:** `lib/ordering.ts` holds the ordering constants (copied from BE-ORD-01, with a comment citing it) and a pure `computeOrder(previous, next)` implementing the BE-ORD-01 formulas. It receives the neighbors from the current local state, excluding the dragged card. It has unit tests.
- **Rationale:** The client computes `order`, so a wrong formula corrupts the column, and a pure function is easy to test.
- **RevoTask example:** dropping a card between two cards with orders `1024.0` and `2048.0` sends `1536.0`.

### FE-DND-03 Optimistic update with exact revert
- **Rule:** On drop, the hook saves a snapshot of the previous state, updates local React state immediately, and calls `PATCH /api/cards/<id>/position` with `{ column_id, order }`. If the API returns any error, the hook restores the snapshot exactly (column and position) and passes the error to `useErrorHandler`. On success, it reconciles with the response (`order`, `completed_at`); when the response says `rebalanced` is true, it applies the returned sibling orders to that column.
- **Rationale:** The UI must feel instant but never show a position the server rejected.
- **RevoTask example:** moving a card to a column on another board gets 422 from the backend, and the card visibly snaps back to where it was.

### FE-DND-04 Guards
- **Rule:** The hook ignores a drop that does not change the card's column or position, ignores drag payloads that are not RevoTask cards, and disables dragging a card while its own move request is pending. Cards are draggable only when `my_role` is `member` or `admin`. Dropping into an empty column works. Drop targets show a visible highlight.
- **Rationale:** Guards prevent pointless requests, races, and drags the server would reject.
- **RevoTask example:** a Guest sees cards without a drag cursor, and dragging a text selection onto a column does nothing.

### FE-DND-05 Accessible fallback
- **Rule:** `CardDetailModal` includes a "Move to column" select for Members and Admins. It calls the same move function as drag-and-drop, so the optimistic update, revert, and error handling are shared, and places the card at the end of the chosen column.
- **Rationale:** Native HTML5 drag-and-drop does not work with keyboards or most touch screens.
- **RevoTask example:** on a phone, choosing "Done" in the select moves the card and the board updates immediately.

---

## 8. Notifications

### FE-NTF-01 useNotifications polling
- **Rule:** `hooks/useNotifications.ts` polls `GET /api/notifications` every 30,000 ms (a named constant) and updates notification state. It polls only while the user is logged in, clears its timer on unmount, skips a tick if the previous request is still pending, pauses while `document.hidden` and refreshes once when the tab becomes visible again, and stops after a 401. It returns notifications, `unreadCount`, `markRead`, and `refresh`.
- **Rationale:** Uncleared timers and overlapping requests are the usual causes of leaks and request storms.
- **RevoTask example:** logging out stops the polling with no further requests.

### FE-NTF-02 NotificationBell
- **Rule:** `NotificationBell.tsx` sits in the header and shows `unread_count` from the API response, not a count computed from the page (the list is paginated). The badge is hidden at 0 and capped at "99+". A dropdown lists messages as plain text with timestamps. Clicking one calls `PATCH /api/notifications/<id>/read` with an optimistic decrement that is reverted on error. It links to `/boards/<board_id>` only when `board_id` is set and the type is not `board_deleted` or `member_removed`.
- **Rationale:** A count from one page would be wrong, and links to boards the user can no longer open would only produce 404s.
- **RevoTask example:** 42 unread notifications across 3 pages shows "42", not the number on page 1.

---

## 9. Role-aware UI

### FE-ROLE-01 `my_role` is the source of truth
- **Rule:** The viewer's role comes from the `my_role` field of the board payload (BE-SVC-04). `lib/roles.ts` maps it to a few UI flags (for example `canWrite`: member or admin; `canManage`: admin) and is the only place that does so. Own-only controls (BE-AZ-04) compare `created_by` or `author.id` with the current user's id. The matrix itself is not re-implemented or restated here.
- **Rationale:** One mapping prevents controls from disagreeing across components, and the backend remains the authority.
- **RevoTask example:** `KanbanBoard` reads `const { canWrite } = rolesFor(board.my_role)` and renders the "Add card" button only when it is true.

### FE-ROLE-02 Different read-only messages
- **Rule:** Anonymous visitors see a "Log in to contribute" prompt. Guests see a read-only note: "You have read-only access. Ask a board admin to add you as a member." Neither sees write controls.
- **Rationale:** Each viewer needs a different next step.
- **RevoTask example:** a logged-in Guest on a public board sees the board and the Guest note, with no "Add card" button.

### FE-ROLE-03 The UI hides, the server enforces
- **Rule:** After a 403 or 404 on a write, the UI shows the mapped toast (FE-API-05) and calls `router.refresh()` so the role and data are reloaded. A control being hidden is never treated as proof the action is forbidden, and a visible control is never treated as proof it will succeed.
- **Rationale:** Roles can change while a page is open.
- **RevoTask example:** an Admin who was demoted in another tab sees the 403 toast, and the Admin panels disappear after the refresh.

---

## 10. UX states and accessibility

### FE-UX-01 Loading, empty, and error states
- **Rule:** Every data route (`/`, `/boards/[id]`, `/my-tasks`) has `loading.tsx` with a skeleton, an `error.tsx` with a retry action, and, for the board, `not-found.tsx`. Every list has an empty state: no boards, no columns ("Add the first column" for Members and Admins, plain text for read-only viewers), no cards in a column, no assigned tasks, no notifications.
- **Rationale:** Blank screens look broken, and the assignment is judged against polished demo apps.
- **RevoTask example:** a new board shows "No columns yet" with an "Add column" button for its Admin.

### FE-UX-02 Responsive and accessible
- **Rule:** The Kanban layout scrolls horizontally on narrow screens with a minimum column width. Use semantic landmarks (`header`, `nav`, `main`), visible focus styles, and `aria-label` on icon-only buttons. Every interactive element is reachable by keyboard.
- **Rationale:** The app must work on phones and with keyboards, not only with a mouse on a wide screen.
- **RevoTask example:** the `NotificationBell` button has `aria-label="Notifications, 3 unread"`.

### FE-UX-03 Readable text sizes
- **Rule:** Body text, form labels, input text, buttons, list rows, card titles, comments, notification messages, toasts, and helper messages use at least 16px (Tailwind `text-base`). Helper messages are field hints and errors, notes under forms, links such as "New here? Create an account", read-only notices, page and board descriptions, and the messages in empty, error, and not-found states. Badges (`BaseBadge`), due and completed dates, comment counts, and notification timestamps use 14px (`text-sm`). Due and completed dates always use the same size as `BaseBadge`, whether shown as plain text or inside a badge, so the same information never appears in two sizes. No text is smaller than 14px, with one exception: numbers or initials inside small circles (avatars and the notification count) may use 12px (`text-xs`). Page titles use `text-2xl` or larger. Sizes come from Tailwind text-size classes (which are relative units), not fixed pixel values in `style`, so browser zoom and font-size settings still apply.
- **Rationale:** People who wear glasses or have low vision need to read the interface comfortably, and generated UI tends to default to small text. A message people must read to understand what is happening is content, not a caption, so it gets the full body size.
- **RevoTask example:** the "Email already in use." message under a field and the "No boards yet" message in an empty state are `text-base`; a Kanban card's title is `text-base`, while its due date is `text-sm` whether it is plain text ("Due Nov 22") or a `BaseBadge` ("Due Nov 18"); a `text-xs` caption under a comment would violate this rule.

### FE-UX-04 Follow the visual design reference
- **Rule:** The visual design reference is `.kiro/design-visual/design.html` (path from the repo root). Kiro does not load it automatically, so before building or changing any page or component, open that file and follow it: screens are matched by `data-screen` and `data-route`, components by `data-component`, and colors, spacing, and styling by its Tailwind classes and the notes in its top comment. Design tokens (brand colors, light and dark values, radii, shadows) live in one place in the app (the Tailwind config and global CSS variables) and are never repeated inline. The reference is not shipped: nothing is imported from it, and its design bar (marked `data-design-only`) is never built. If the reference conflicts with this file on behavior, data, or text sizes (FE-UX-03), this file wins and the conflict is reported instead of silently resolved. The reference file is not edited unless asked.
- **Rationale:** A single visual source keeps every page consistent and stops generated code from inventing its own styles. Stating where the file lives and what wins in a conflict makes drift checkable.
- **RevoTask example:** the primary `BaseButton` uses the gradient fill, glow, and sizes from the `.btn-primary` rule in `.kiro/design-visual/design.html`, the Kanban card follows its `data-component="Card"` markup, and the "Design bar" at the top of the reference is not built.

---

## 11. Security and environment

### FE-SEC-01 No raw HTML from user content
- **Rule:** Never use `dangerouslySetInnerHTML`. Board names, card text, comments, and notification messages are rendered as text.
- **Rationale:** User-written content on public boards is an XSS risk, and the token lives in client memory (FE-AUTH-01).
- **RevoTask example:** a comment containing `<script>` appears as literal text.

### FE-SEC-02 Environment variables
- **Rule:** `API_BASE_URL` (server only) and `NEXT_PUBLIC_API_BASE_URL` (browser) are the only API variables. Only `NEXT_PUBLIC_` variables are visible in the browser. No secrets in client code. Provide `.env.example` with placeholders only. The backend's `CORS_ORIGINS` must include the frontend origin (BE-SEC-02).
- **Rationale:** Anything in the browser bundle is public.
- **RevoTask example:** `.env.example` lists `API_BASE_URL=http://localhost:5000` and `NEXT_PUBLIC_API_BASE_URL=http://localhost:5000`.

### FE-SEC-03 Safe URLs
- **Rule:** Build query strings with `URLSearchParams`. The `next` parameter after login is accepted only if it is a relative path starting with a single `/`. External links use `rel="noopener noreferrer"`.
- **Rationale:** An unchecked `next` is an open redirect.
- **RevoTask example:** `/login?next=https://evil.example` redirects to `/` after login.

---

## 12. Testing

### FE-TST-01 Tooling
- **Rule:** Use Vitest, React Testing Library, and MSW to mock the API. No test calls the real backend. Test files sit next to the code as `*.test.ts(x)`. `tsc --noEmit` and the ESLint config for Next.js must pass.
- **Rationale:** Mocked, local tests are fast and reproducible.
- **RevoTask example:** `useDragAndDrop.test.tsx` uses an MSW handler for `PATCH /api/cards/:id/position`.

### FE-TST-02 Required tests
- **Rule:** Include tests for:
  - `apiClient`: Bearer header attached, base URL chosen by environment, `ApiError` on 401, 422, 5xx, and network failure, and 204 returning `undefined`.
  - `useErrorHandler`: one test per mapping row in FE-API-05.
  - `computeOrder` and `useDragAndDrop`: optimistic update, exact revert on error, rebalance applied, same-position drop ignored, no drag when read-only.
  - `useNotifications`: 30 s polling with fake timers, cleanup on unmount, no overlapping requests, paused while hidden, stopped on 401.
  - Forms: validation messages, 422 `details` mapped to fields, double submit blocked.
  - `BaseModal`: Escape closes, focus trapped and restored.
  - Role-aware rendering: the controls shown for Anonymous, Guest, Member (own and others' items), and Admin.
  - `/my-tasks` grouping by board name.
  - `BaseButton` usage: the interactive controls on `/my-tasks` and `/profile` render through `BaseButton`, and an ESLint rule (restricting the JSX `button` element outside `BaseButton.tsx`) or a CI grep finds no raw `<button>` elsewhere.
  - Text size (FE-UX-03): a lint rule or CI grep finds no `text-xs` or arbitrary text sizes below 14px (such as `text-[10px]`) outside the avatar and notification-count components, and `BaseBadge` renders at `text-sm`.
- **Rationale:** These are the behaviors the assignment names and where generated code most often fails quietly.
- **RevoTask example:** `revert_restores_original_column_and_order` drops a card, returns a 500 from MSW, and asserts the card is back at its original position.
