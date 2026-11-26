# frontend.md Changelog

Newest first. The current file is v11, produced on 2026-11-26. Each change is logged as it is made, so entries are accurate summaries, though earlier file versions are not kept for download.

Keep this file outside `.kiro/steering/` (for example `docs/`) so Kiro does not load it as context.

---

## v11 (current): Expired session wording

**Changed**
- **FE-AUTH-04:** the rule now states what happens on each path. A 401 in a Client Component deletes the cookie, clears `AuthContext`, and redirects. A 401 in a Server Component redirects but keeps the cookie, because Server Components cannot write cookies. The browser drops that cookie at the token's expiry, and a stale cookie does not cause a redirect loop. The old text said the session was cleared on every 401, which the Server Component path did not do.

**Reason**
- Review of the open gap (v10 question): a server-side 401 leaves the cookie in place, and the team chose to accept it rather than add a Route Handler.

**Related changes in other files**
- Code: none for this entry.

---

## v10: Registration signs the user in

**Changed**
- **Product decisions:** registration no longer redirects to `/login`. The new user is signed in automatically, with the same credentials they typed.
- **FE-PAGE-01:** `/register` calls the login Server Action after a successful `POST /api/auth/register`. On success it refreshes the layout (so `AuthContext` loads the user) and opens `/`. If auto-login fails, it shows "Account created. Please log in." and redirects to `/login`.

**Related changes in other files**
- Code: `components/auth/RegisterForm.tsx`, with unit tests and the e2e helper `e2e/helpers/auth.ts`, which already expected `/`.
- Backend: none. The register response still has no token, so the frontend logs in with the same credentials.

---

## v9: Design reference location

**Added**
- **FE-UX-04:** the visual design reference is `.kiro/design-visual/design.html`. Kiro must open it before building or changing UI, match screens and components through `data-screen`, `data-route`, and `data-component`, keep design tokens in one place, and never build the design bar. On a conflict about behavior, data, or text sizes, `frontend.md` wins and the conflict is reported. The file itself is not edited unless asked.
- Scope section: a bullet pointing the visual design to the reference file.

**Related changes in other files**
- `design.html`: its top comment states its location.
- `violation_report.md`: steering version updated (`frontend.md` v9).

---

## v8: Helper messages at 16px

**Changed**
- **FE-UX-03:** helper messages move from 14px to 16px (`text-base`). That covers field hints and errors, notes under forms, links such as "New here? Create an account", read-only notices, page and board descriptions, and the messages in empty, error, and not-found states. Badges, due and completed dates, comment counts, and notification timestamps stay at 14px. The rationale and example are updated. This replaces the v6 rule that put helper messages at 14px.

**Related changes in other files**
- `design.html`: every helper message is 16px, including the inline error messages on the States screen, and the muted text color in dark mode is a little brighter.
- `violation_report.md`: check 27 and the steering version updated (`frontend.md` v8).

---

## v7: Lighter badges

**Changed**
- **FE-UI-02:** `BaseBadge` text uses medium weight (`font-medium`) at 14px, so it reads lighter than the semibold card titles. Before, badges and titles were both semibold and looked alike.

**Related changes in other files**
- `design.html`: badges use medium weight, and the type scale note mentions it.
- `violation_report.md`: check 27 and the steering version updated (`frontend.md` v7).

---

## v6: Smaller badges and helper messages

**Changed**
- **FE-UX-03:** the v5 change (18px titles and descriptions) is reverted. `BaseBadge` and helper messages (field hints and errors, notes under forms, read-only notices, links such as "New here? Create an account", and page and board descriptions) now use 14px. Due and completed dates, comment counts, and timestamps are 14px too, so a date matches the badge whether it is plain text or inside one. Body text, labels, input text, buttons, and card titles stay at 16px. Example and rationale updated.
- **FE-UI-02 and FE-TST-02:** `BaseBadge` renders at `text-sm`, not `text-base`.

**Related changes in other files**
- `design.html`: the same sizes applied across every screen, and the type scale in the top comment updated.
- `violation_report.md`: check 27 and the steering version updated (`frontend.md` v6).

---

## v5: Larger titles and descriptions (reverted in v6)

**Changed**
- **FE-UX-03:** titles and descriptions of cards, boards, and pages (card titles, board descriptions, page subtitles, modal descriptions) use `text-lg` (18px), so they stand apart from the 16px badges and field text. Due and completed dates stay at the badge size (16px) so a date never appears in two sizes. The example is updated to match.

**Related changes in other files**
- `design.html`: card titles on the board and My Tasks, board descriptions, page subtitles, the card description field, and the component sheet notes are 18px.
- `violation_report.md`: check 27 and the steering version updated (`frontend.md` v5).

---

## v4: Consistent due-date size

**Changed**
- **FE-UX-03:** due and completed dates use the same size as `BaseBadge` (`text-base`), whether shown as plain text or inside a badge. Before, a date shown as a badge was 16px and a plain date was 14px. Only other secondary details, such as notification timestamps, keep the 14px minimum. The example is updated to match.

**Related changes in other files**
- `design.html`: the date and comment-count line on Kanban cards, and "No due date" on My Tasks, are now 16px.
- `violation_report.md`: steering version updated to `frontend.md` v4.

---

## v3: Readable text sizes

**Added**
- **FE-UX-03:** body text, labels, buttons, list rows, comments, notifications, toasts, and badges are at least 16px (`text-base`). Secondary details are at least 14px (`text-sm`). Nothing is smaller than 14px, except numbers or initials inside small circles (12px). Sizes use Tailwind classes, not fixed pixels.
- FE-TST-02: a lint or CI check for `text-xs` and arbitrary sizes below 14px outside the avatar and notification-count components.

**Changed**
- **FE-UI-02:** `BaseBadge` text is `text-base`.

**Related changes in other files**
- `design.html`: the same type scale applied across the whole reference file, and badges raised to 16px.
- `violation_report.md`: a new check (27) for FE-UX-03, and the steering versions updated.

---

## v2: BaseButton rules and limit sources

**Changed**
- **FE-UI-01:** `BaseButton` gets an `href` prop that renders a Next.js `Link`, and the rule now names the cases: pagination and "Open board" on `/my-tasks`, and Save and Cancel on `/profile`. Raw `<button>` elements and one-off styled anchors are not allowed outside `BaseButton.tsx`.
- **FE-PAGE-05, FE-PAGE-06:** each states which controls use `BaseButton`.
- **FE-FRM-02 and the scope list:** validation limits are copied from the column lengths in `database.md` (DB-SCH-01) and the schema rules in BE-VAL-05, instead of BE-VAL-05 alone.

**Added**
- FE-TST-02: a test and lint or CI check that the interactive controls on `/my-tasks` and `/profile` use `BaseButton` and that no raw `<button>` exists elsewhere.

**Related changes in other files**
- `backend.md` v7 and `database.md` v3: soft-deleted cards, singular file names, and limits defined only in `database.md`. Nothing in the frontend files changes for soft delete, because the UI already removes a deleted card and handles a 404.

---

## v1: First full draft

**Stack:** Next.js 16.x (App Router), React, TypeScript strict, Tailwind CSS, `react-hot-toast`, native HTML5 Drag and Drop, Vitest + React Testing Library + MSW. Front matter is `inclusion: always`. dnd-kit, suggested earlier, was dropped because the requirements name the native API.

**Added**
- **Structure (FE-STR):** Next.js 16 pinned by major in the file and by exact version in `package.json`; async request APIs; no Cache Components; Server Components by default; fixed folder and file names from the requirements; API types mirror the backend in snake_case.
- **Authentication (FE-AUTH):** token stored in an httpOnly cookie by a Server Action and hydrated into `AuthContext` by the root layout, which also loads the user from `GET /api/users/me`; logout; one policy for 401; server-side route access rules.
- **API client and errors (FE-API):** one typed `apiClient`, explicit `cache: "no-store"` for server calls, `ApiError` with `statusCode`, `message`, `code`, and `details`, a single toast wrapper, and the `useErrorHandler` mapping table.
- **Pages (FE-PAGE):** `/register`, `/login`, `/` dashboard, `/boards/[id]`, `CardDetailModal` with `CommentList`, `/my-tasks`, `/profile`, and the board management UI (create, edit, delete, members panel, analytics panel).
- **Forms (FE-FRM):** controlled labelled inputs, validation limits in one file, 422 `details` mapped to fields, double-submit protection.
- **Shared components (FE-UI):** `BaseButton`, `BaseBadge`, `BaseModal`, and Tailwind styling rules.
- **Drag and drop (FE-DND):** native events only, a pure `computeOrder` function, optimistic update with exact revert, rebalance handling, guards, and a "Move to column" select as the keyboard and touch fallback.
- **Notifications (FE-NTF):** 30 s polling with cleanup and pause rules, and a bell that shows the API's `unread_count`.
- **Role-aware UI (FE-ROLE), UX (FE-UX), security (FE-SEC), testing (FE-TST).**

**Decisions recorded**
- Registration redirects to `/login`. Column reordering has no UI. Forms in dialogs use `BaseModal`, while the login, register, and profile forms are inline on their pages.
- Own-only delete controls for Members compare `created_by` with the current user's id.

**Related changes in other files**
- `backend.md` v6: assigned-tasks endpoint moved to `GET /api/cards?assignee=me`, `unread_count` added to notifications, and `created_by` added to board, column, and card payloads.
- `database.md` v2: index references updated to the new endpoint path.
