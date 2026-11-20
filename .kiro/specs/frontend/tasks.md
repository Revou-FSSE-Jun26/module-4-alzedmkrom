# Implementation Plan: RevoTask Frontend

Version: V3 (see `CHANGELOG.md`)

## Overview

Implementation is in TypeScript (Next.js 16.4.6 App Router, React 19.3.1, Tailwind CSS 4.3.5, react-hot-toast 2.6.1) under `/frontend`, a new directory that holds only `.gitkeep` today. The order is: project scaffold and install verification; the `lib` modules; `AuthContext`; the hooks; the shared components; the app shell (layout, Header, NotificationBell, `proxy.ts`, error and not-found pages); then each page with its components (login, register, dashboard, board detail, my tasks, profile, members, analytics); then the Vitest component and property tests (fast-check), the Playwright end-to-end suite, the README and the Vercel configuration. Property tests use `fast-check` with at least 100 runs and cover the 23 correctness properties of `design.md`. Example tests use Vitest, jsdom and React Testing Library. The E2E suite runs Playwright against the deployed Vercel URL.

All paths below are relative to `/frontend`. Component and property tests live in `__tests__/` (`shared`, `auth`, `hooks`, `lib`, `components`, `meta`, `helpers`), end-to-end tests in `e2e/`. Requirement numbers in task text refer to `requirements.md` (V2). Decision numbers `F1` to `F17` refer to the table "Decisions the requirements did not specify" in `design.md`.

Structure decisions:
- Task 7 names its direct predecessors in a `_Depends on:_` line under each subtask (V3). The other tasks carry no such line.

- The Route_Guard file is `proxy.ts` with `export function proxy`, not `middleware.ts` (design, "Next.js 16 specifics", Requirements Decision 16). Every page that takes a route parameter declares `{ params: Promise<{ id: string }> }` and awaits it.
- Test files are written after all implementation tasks (tasks 16 to 22), as sub-tasks marked `*` under one parent per area. Test support files that other tests need (`__tests__/setup.ts`, `__tests__/helpers/server-only-stub.ts`, `__tests__/helpers/renderWithAuth.tsx`, `e2e/helpers/auth.ts`) are not optional and sit with the code they support.
- Two small pure helpers are added to modules the design already names, so that Properties 9 and 15 can be tested without rendering: `visibleCards(cards, searchIds)` in `lib/boardState.ts` (used by `BoardView`) and `changedCardFields(card, values)` and `changedProfileFields(user, values)` in `lib/validation.ts` (used by `CardDetailModal` and `ProfileForm`). The design leaves these helpers open.
- ESLint enforces three structural rules (task 1.4): no native `button` JSX element outside `components/shared/BaseButton.tsx` (Requirement 8.9), `react-hot-toast` imported only in `lib/toast.ts` and `app/layout.tsx` (Requirement 24.5), and no explicit `any` or `@ts-ignore` (Requirement 24.2). Every implementation task below must keep `npm run lint` and `npm run typecheck` clean.
- Server-only modules (`lib/serverSession.ts`, `lib/serverApi.ts`) start with `import 'server-only'`. Client Components start with `"use client"` only when they use a hook, an event-handler prop, a context hook or a browser global (Requirement 23.2). `components/shared/BaseButton.tsx`, `BaseBadge.tsx`, `FormField.tsx`, `FormAlert.tsx` and `AnalyticsPanel.tsx` need no directive unless a hook is used.
- Install note: with npm 12 the default `allow-remote=none` makes `npm install` fail with `EALLOWREMOTE`, because Tailwind's optional WASM package is fetched by tarball URL. A dry run with `--allow-remote=all` resolves cleanly (438 packages, no peer conflicts, Node 26 accepted). Task 1.1 therefore adds `frontend/.npmrc` with `allow-remote=all`, and task 1.2 verifies the install without any command-line flag. The Vercel build has to be verified as well (see Notes).

## Tasks

- [x] 1. Set up the project scaffold
  - [x] 1.1 Create `package.json` and `.npmrc`
    - `package.json`: `name` `revotask-frontend`, `private` true, `engines.node` `>=22.12`, and the scripts `dev` (`next dev`), `build` (`npm run lint && next build`), `start` (`next start`), `lint` (`eslint .`), `typecheck` (`tsc --noEmit`), `test` (`vitest run`), `test:e2e` (`playwright test`)
    - `dependencies` hold only `next` 16.4.6, `react` 19.3.1, `react-dom` 19.3.1, `react-hot-toast` 2.6.1 and `server-only`, each pinned to the exact version of the design table. No chart, drag-and-drop or state-management package in `dependencies` or `devDependencies`
    - `devDependencies`: `typescript` `~5.9.3`, `@types/node`, `@types/react`, `@types/react-dom`, `tailwindcss` 4.3.5, `@tailwindcss/postcss` 4.3.5, `postcss` `^8.5`, `eslint` `^9.39`, `eslint-config-next` 16.4.6, `vitest` `^5.1.1`, `jsdom` `^31`, `@vitejs/plugin-react` `^6.3`, `vite` `^8.3`, `@testing-library/react` `^16.3.3`, `@testing-library/dom` `^10`, `@testing-library/user-event` `^14.6`, `@testing-library/jest-dom` `^8`, `fast-check` `^4.10`, `@playwright/test` `^1.65`. Read the `@types/*` versions from the npm registry so that they match React 19 and Node 22
    - Create `.npmrc` containing `allow-remote=all`, preceded by a comment that explains why: npm 12 defaults to `allow-remote=none`, Tailwind's optional WASM package is fetched by tarball URL, and without this line `npm install` fails with `EALLOWREMOTE`. The comment also says to check the Vercel build log, because Vercel may run an older npm that does not know this key
    - _Requirements: 23.4, 24.2, 24.3, 25.1, 26.1, 27.8_

  - [x] 1.2 Verify the install of the pinned stack
    - From `frontend/`, run `npm install` with no `--allow-remote` flag, so that only `.npmrc` supplies the setting. Expect exit code 0, no `EALLOWREMOTE` error, about 438 packages (the dry-run count, informational) and no peer-dependency conflict
    - Run `npm ls` and expect exit code 0, then run `npm ci` in a clean `node_modules` and expect exit code 0 with the same result, so that the lockfile is reproducible
    - Commit `package-lock.json`. If `npm install` fails with `EALLOWREMOTE`, check that the command ran in `frontend/` and that `.npmrc` is not git-ignored, and do not work around it with a flag in `package.json` scripts
    - _Requirements: 23.4, 27.8_

  - [x] 1.3 Create the TypeScript, Next.js, PostCSS and Tailwind configuration
    - `tsconfig.json`: `strict` true and no strict-family flag set to false, `target` ES2022, `module` esnext, `moduleResolution` bundler, `jsx` react-jsx, `noEmit`, `paths` `{"@/*": ["./*"]}`, `include` `next-env.d.ts`, `**/*.ts`, `**/*.tsx`, `.next/types/**/*.ts`
    - `next.config.ts`: `poweredByHeader` false and the headers `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin` (F13). No `eslint` key and no webpack config
    - `postcss.config.mjs` with the `@tailwindcss/postcss` plugin. `tailwind.config.ts` with `content` globs for `app` and `components` and a `theme.extend` palette for badges and buttons. `app/globals.css` with `@import "tailwindcss";` and `@config "../tailwind.config.ts";`
    - _Requirements: 21.6, 24.1_

  - [x] 1.4 Create `eslint.config.mjs`
    - Flat config: `defineConfig([...nextVitals, ...nextTs, project rules, globalIgnores([...])])` with `nextVitals` from `eslint-config-next/core-web-vitals` and `nextTs` from `eslint-config-next/typescript`
    - Rules at level `error`: `@typescript-eslint/no-explicit-any`, `@typescript-eslint/ban-ts-comment` banning `ts-ignore` and `ts-nocheck`, `react/no-danger`, `no-alert`, `no-console` (allow `warn` and `info`), `no-restricted-syntax` with the selector `JSXOpeningElement[name.name='button']` switched off for `components/shared/BaseButton.tsx`, and `no-restricted-imports` for `react-hot-toast` switched off for `lib/toast.ts` and `app/layout.tsx`
    - Ignores: `.next/**`, `node_modules/**`, `playwright-report/**`, `test-results/**`, `coverage/**`, `next-env.d.ts`
    - _Requirements: 7.7, 8.9, 24.2, 24.3, 24.4, 24.5_

  - [x] 1.5 Create the Vitest configuration and setup files
    - `vitest.config.ts`: `@vitejs/plugin-react`, alias `@` to the project root and `server-only` to `__tests__/helpers/server-only-stub.ts`, `environment` jsdom, `setupFiles` `__tests__/setup.ts`, `include` `__tests__/**/*.test.{ts,tsx}`, `allowOnly` false, `restoreMocks` true, `css` false
    - `__tests__/setup.ts` registers `@testing-library/jest-dom/vitest` and calls `cleanup` after each test. `__tests__/helpers/server-only-stub.ts` is an empty module
    - _Requirements: 25.1, 25.8_

  - [x] 1.6 Create `playwright.config.ts`
    - Try `process.loadEnvFile('.env.local')` inside a `try`, then read `PLAYWRIGHT_BASE_URL` (trimmed) and throw an `Error` whose message names `PLAYWRIGHT_BASE_URL` when it is empty
    - `testDir` `e2e`, `timeout` 60,000, `expect.timeout` 10,000, `retries` 0, `fullyParallel` true, reporters `html` (`outputFolder` `playwright-report`, `open` never) and `list`, `use` with `baseURL`, `trace` `retain-on-failure` and `screenshot` `only-on-failure`, one project `chromium` (F17), and no `webServer` entry
    - _Requirements: 26.1, 26.6, 26.8, 26.9_

  - [x] 1.7 Create `.env.example` and `.gitignore`
    - `.env.example` with exactly `NEXT_PUBLIC_API_BASE_URL=http://localhost:5000`, `API_BASE_URL=http://localhost:5000` and `PLAYWRIGHT_BASE_URL=http://localhost:3000`, each on its own line, with no trailing slash, no user-info part and no secret
    - `.gitignore` entries: `.next/`, `node_modules/`, `.env`, `.env.local`, `.env.*.local`, `coverage/`, `test-results/`, `next-env.d.ts`, `*.tsbuildinfo`. No entry matches `.env.example`, and `playwright-report/` is not listed
    - _Requirements: 26.8, 27.1, 27.2, 27.3_

- [x] 2. Implement the `lib` modules
  - [x] 2.1 Implement `lib/errors.ts` and `lib/toast.ts`
    - `ApiError extends Error` with `readonly statusCode: number`, constructor `(statusCode, message)` calling `super(message)` and setting `name = 'ApiError'`
    - `lib/toast.ts` exports `success`, `error`, `loading` and `dismiss`, each calling the matching `react-hot-toast` function exactly once with the same arguments and returning the toast id. It is the only file besides `app/layout.tsx` that imports `react-hot-toast`
    - _Requirements: 5.6, 6.1, 6.2, 6.3, 6.5, 24.5_

  - [x] 2.2 Implement `lib/types.ts`
    - Export `Role`, `NotificationType`, `User`, `RegisteredUser`, `LoginResponse`, `Board`, `Column`, `Card`, `ColumnWithCards`, `BoardDetail`, `Member`, `Comment`, `Notification`, `NotificationPage`, `MyTasksGroup`, `Analytics`, `CardMoveResult`, `ColumnReorderResult`, `DeletedId` and `MemberRemoved` exactly as in the Data Models section of `design.md`. No other module declares a type for the same response
    - _Requirements: 5.9_

  - [x] 2.3 Implement `lib/apiClient.ts`
    - `resolveBaseUrl()`: server (`typeof window === 'undefined'`) reads the literal `process.env.API_BASE_URL` and falls back to the literal `process.env.NEXT_PUBLIC_API_BASE_URL` only when `API_BASE_URL` is unset, client reads `NEXT_PUBLIC_API_BASE_URL`. Trim the value, throw an `Error` whose message names the variable when it is empty, and strip every trailing `/`
    - `apiRequest<T>(method, path, { token, body })` builds the URL from the base and the `/api/...` path, sends `Authorization: Bearer <token>` only for a non-empty token, sends `Content-Type: application/json` and a JSON body only when a body is given, adds `cache: 'no-store'` on the server, turns a rejected `fetch` into `ApiError(0, 'Network request failed')`, returns the `data` field for statuses 200 to 299 (an `ApiError` `Invalid response from server` when `data` is missing) and throws `ApiError(status, error)` otherwise, with the fallback message `Request failed with status <status>`
    - Export `apiClient` with `get`, `post`, `patch` and `delete`. Reference both environment variables as literal `process.env.NAME` expressions so that Next inlines them
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.10_

  - [x] 2.4 Implement `lib/order.ts` (Order_Helper)
    - `orderBetween(above, below)`: both neighbours give `(above + below) / 2` with no rounding, only a lower neighbour gives `above + 1.0`, only an upper neighbour gives `below / 2`, none gives exactly `1.0`
    - `orderForIndex(sortedOthers, index)` maps an index from 0 to the list length onto `orderBetween`. `dropIndex(midpoints, pointer)` returns the index of the first midpoint greater than the pointer coordinate, or the list length
    - _Requirements: 11.7, 13.2, 13.3, 13.4, 13.5, 13.13, 13.14_

  - [x] 2.5 Implement `lib/validation.ts`
    - Export `LIMITS`, `codePointLength` (F5), `isValidEmail` (the grammar of Requirement 3.2, F6), `validateEmail`, `validateRegister` (name and password untrimmed, email trimmed), `validateLogin`, `validateProfile`, `validateRequiredText`, `validateOptionalText`, `validateComment` and the `FieldErrors` type. Every validator returns `null` or the message to show
    - Add `changedCardFields(card, values)` (keys among `title`, `description`, `assignee_id`, `completed` whose value differs, comparing `description` with `card.description ?? ''` and `completed` with `card.completed_at !== null`) and `changedProfileFields(user, values)` (`name` and trimmed `email`)
    - _Requirements: 3.2, 3.3, 4.2, 9.4, 10.10, 11.2, 12.2, 12.5, 12.10, 12.11, 14.5, 17.2, 17.3, 17.4, 19.3_

  - [x] 2.6 Implement `lib/collections.ts` and `lib/format.ts`
    - `collections.ts`: `sortByOrder`, `sortByCreatedAt(items, 'asc' | 'desc')`, `sortByActionsDesc` (all stable) and `barPercentages(counts)` (`count / max * 100`, all 0 when the maximum is 0)
    - `format.ts`: `formatUnreadCount` (null for 0, `"99+"` above 99, else the decimal text), `formatDateTime` (`toLocaleString()`) and `formatDate` (`toLocaleDateString()`)
    - _Requirements: 14.2, 18.4, 18.5, 20.2, 20.4_

  - [x] 2.7 Implement `lib/boardState.ts`
    - Export `BoardState`, `BoardAction`, `initBoardState`, `boardReducer`, `findCard` and `visibleCards(cards, searchIds)` (the cards whose id is in the set, order preserved, all cards when the set is `null`)
    - Reducer rules: every action returns a new object and never mutates its input. `card/moved` removes the card from its column, inserts `{ ...card, order }` into the target column and re-sorts it stably. `column/moved` re-sorts the columns. `*/orders-applied` overwrites `order` by id, ignores unknown ids and re-sorts. `card/replaced` keeps the position. `column/added` appends a column with an empty `cards` list in `order` position. `state/restored` returns the snapshot itself
    - _Requirements: 10.2, 11.3, 11.5, 11.6, 11.7, 11.8, 11.10, 12.5, 12.6, 12.9, 13.7, 13.9, 13.10, 15.4, 15.6_

  - [x] 2.8 Implement `lib/session.ts`
    - Export `SESSION_COOKIE = 'revotask_token'`, the pure `buildSessionCookie(token, maxAgeSeconds, secure)` (value `encodeURIComponent(token)`, `Path=/`, `SameSite=Lax`, `Max-Age=<n>`, `Secure` only when the flag is true, never `HttpOnly`), and the browser-only `writeSessionCookie(token, expiresIn)` (`secure` is `location.protocol === 'https:'`) and `clearSessionCookie()` (same `Path=/`, `Max-Age=0`)
    - The module must be safe to import from `proxy.ts` and from Client Components
    - _Requirements: 1.1, 1.2, 1.7_

  - [x] 2.9 Implement `lib/serverSession.ts`
    - Start with `import 'server-only'`. Export `getSessionToken` (React `cache()`, awaits `cookies()`, an empty value counts as no token) and `getServerSession` (`cache()`): no token gives `{ token: null, user: null }` with no request, `GET /api/users/me` success gives the token and the user, a 401 gives the null pair without throwing, any other `ApiError` is rethrown
    - This is the only module under `app/`, `components/`, `hooks/` and `context/` that reads the `revotask_token` cookie on the server
    - _Requirements: 1.3, 1.4, 1.5, 1.6, 1.9_

  - [x] 2.10 Implement `lib/serverApi.ts`
    - Start with `import 'server-only'`. Export `serverApi.get<T>(path)`: read the token through `getSessionToken`, redirect to `/login` when there is none, call `apiRequest('GET', path, { token })`, and on an `ApiError` with status 401 call `redirect('/login?reason=session-expired')` outside any `try` block. Rethrow every other error unchanged
    - _Requirements: 2.3_

- [x] 3. Implement the auth context and its test helper
  - [x] 3.1 Implement `context/AuthContext.tsx`
    - Export `AuthContextValue`, `AuthContext`, `AuthProvider({ initialToken, initialUser, children })` and `useAuth()` (throws outside the provider). State is `useState` seeded from the props
    - `login(token, expiresIn, user)` writes the Session_Cookie with `writeSessionCookie`, then sets state. `clearSession()` clears state and the cookie with no navigation (F4). `logout()` calls `clearSession()`, `router.replace('/login')` and `router.refresh()` and sends no request. `updateUser(user)` replaces the user and leaves the token and cookie unchanged
    - _Requirements: 1.1, 1.7, 1.8, 2.5, 2.6_

  - [x] 3.2 Create `__tests__/helpers/renderWithAuth.tsx`
    - Render a tree inside `AuthContext.Provider` with a token, a user and spies for `login`, `logout`, `clearSession` and `updateUser`. Return the render result and the spies
    - _Requirements: 25.1, 25.3, 25.7_

- [x] 4. Implement the hooks
  - [x] 4.1 Implement `hooks/useApi.ts`
    - `useApi()` returns `{ get, post, patch, delete }` bound to `useAuth().token` through `useMemo`, so the object is stable while the token is stable (F1)
    - _Requirements: 5.3_

  - [x] 4.2 Implement `hooks/useErrorHandler.ts`
    - Export the pure `describeError(error)` returning `{ message, endsSession }` and `useErrorHandler()` returning `(error: unknown) => void`. Messages: 400 and 409 the `ApiError` message, 401 "Your session has expired. Please log in again.", 403 "You do not have permission to do this.", 404 "The requested item was not found.", 0 "Cannot reach the server. Check your connection.", everything else "Something went wrong. Please try again."
    - Show the toast only through `error` of `lib/toast.ts`. Call `logout()` once when `endsSession` is true and never for another status
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 24.4, 24.5_

  - [x] 4.3 Implement `hooks/useDebounce.ts`
    - `useDebounce<T>(value, delayMs)` sets a `setTimeout` after every value change, clears it in the effect cleanup and returns the value that was current when the timer last fired
    - _Requirements: 15.2, 15.3_

  - [x] 4.4 Implement `hooks/useNotifications.ts`
    - Constants `POLL_INTERVAL_MS = 30_000` and `PAGE_SIZE = 100`. Return `{ items, unreadCount, markAsRead, refresh }`. `refresh()` calls `GET /api/notifications?per_page=100` and replaces `items`, keeping ids of the `pendingReadIds` ref as read (F10)
    - One effect keyed on the token: null token does nothing, otherwise `refresh()` once and `setInterval(tick, 30_000)`, and the cleanup clears the interval and drops late responses. A non-401 polling failure keeps `items`, shows nothing and waits for the next tick. A 401 calls the error handler and stops polling
    - `markAsRead(id)` sets `is_read` true before the response, sends `PATCH /api/notifications/<id>/read`, and on failure sets it back to false and calls the error handler
    - _Requirements: 18.1, 18.2, 18.3, 18.6, 18.7, 18.8, 18.11_

  - [x] 4.5 Implement `hooks/useDragAndDrop.ts`
    - Export `DragAndDrop` and `useDragAndDrop({ boardId, state, dispatch, disabled })` with the state, props getters and functions of the design. Use only native HTML5 events (`draggable`, `dragstart`, `dragover`, `drop`, `dragend`), `setData('text/plain', id)` and a ref for the dragged kind and id. Block dragging while `disabled` (F7) or `isMoving` (F8)
    - Card drop: collect the vertical midpoints of the `[data-card-id]` elements of the target column without the dragged one and call `dropIndex` with `clientY`. Column drop: collect horizontal midpoints of the `[data-column-id]` elements without the dragged one and call `dropIndex` with `clientX` (F9)
    - `moveCard(cardId, targetColumnId, position | 'end')`: take the snapshot from a ref, compute `others` and `index`, return with no change and no request when the target and index are unchanged, otherwise compute the order with `orderForIndex`, dispatch `card/moved` before the request, send `PATCH /api/cards/<id>/position` with `{ column_id, order }`, apply `siblings` when `rebalanced` is true, and on failure dispatch `state/restored` and call the error handler. `moveColumn` follows the same shape with `PATCH /api/boards/<boardId>/columns/reorder` and `columns/orders-applied`
    - Highlight exactly one column through `overColumnId`, cleared on `drop` and `dragend`. A drop outside every column or an Escape cancel changes nothing and sends nothing
    - _Requirements: 11.7, 11.8, 11.9, 11.10, 13.1, 13.6, 13.7, 13.8, 13.9, 13.10, 13.11, 13.13, 13.14, 13.15_

- [x] 5. Implement the shared components
  - [x] 5.1 Implement `components/shared/BaseButton.tsx`
    - Props `variant` (`primary` default, `secondary`, `destructive`), `loading` and all native button props. Render `<button type={type ?? 'button'} disabled={disabled || loading} aria-busy={loading}>` with a distinct Tailwind class set per variant, a spinner while loading, and `className` merged last. This is the only file that renders a native `button`
    - _Requirements: 8.1, 8.2, 8.3, 8.9_

  - [x] 5.2 Implement `components/shared/BaseBadge.tsx`
    - Props `color` (`gray` default, `blue`, `green`, `yellow`, `red`), `className`, `children`. Render a `span` with a distinct class set per color, using `-700` or `-800` text on `-100` backgrounds
    - _Requirements: 8.4_

  - [x] 5.3 Implement `components/shared/BaseModal.tsx`
    - Props `open`, `title`, `onClose`, `children`, `size`. Return `null` while closed. While open, render through `createPortal` into `document.body` a backdrop and a `div role="dialog" aria-modal="true" aria-labelledby` pointing at the `h2` that holds the title. A backdrop click calls `onClose`, a click inside the dialog does not
    - A module-level `modalStack` makes only the topmost modal handle keys. One `document` `keydown` listener per open modal: Escape calls `onClose` once, Tab and Shift+Tab wrap focus between the first and last focusable element. On open, move focus within 100 ms to the first focusable element or to the dialog container (`tabIndex={-1}`). On close, restore focus to the remembered element when it is still connected, otherwise to `body`
    - Mobile: `max-h-[100dvh] max-w-full overflow-y-auto` on the dialog
    - _Requirements: 8.5, 8.6, 8.7, 8.8, 21.4, 22.1, 22.2, 22.3, 22.4_

  - [x] 5.4 Implement `components/shared/ConfirmModal.tsx`
    - Props `open`, `title`, `message`, `confirmLabel`, `pending`, `onConfirm`, `onCancel`. A `BaseModal` with a destructive confirm `BaseButton` (disabled while `pending`) and a cancel `BaseButton` whose click calls `onCancel` and sends nothing
    - _Requirements: 8.8, 12.6, 14.13, 19.7, 19.10_

  - [x] 5.5 Implement `components/shared/FormField.tsx`
    - Props `label`, `error`, `hint`, `children` as a render prop receiving `{ id, 'aria-invalid', 'aria-describedby' }`. Use `useId()`, render `<label htmlFor={id}>`, the control, and `<p id="{id}-error">` only while `error` is set. With no error, `aria-invalid` is false and `aria-describedby` is absent
    - _Requirements: 22.5, 22.8_

  - [x] 5.6 Implement `components/shared/FormAlert.tsx`
    - Props `message`. Render `<div role="alert">` with the message while it is set and nothing otherwise
    - _Requirements: 3.6, 4.5, 22.8_

- [x] 6. Checkpoint - Ensure the foundation compiles
  - Run `npm run typecheck` and `npm run lint` from `frontend/` and ensure both exit with code 0, ask the user if questions arise.

- [x] 7. Implement the app shell
  - [x] 7.1 Implement `components/NotificationBell.tsx`
    - Use `useNotifications()`. A secondary `BaseButton` with `aria-label="Notifications"`, `aria-expanded` and an inline SVG bell with `aria-hidden`. Show a red `BaseBadge` with `formatUnreadCount(unreadCount)` only when it is not null
    - The open panel shows "No notifications" for an empty `items`, otherwise `sortByCreatedAt(items, 'desc')` as secondary `BaseButton` rows with the `message`, `formatDateTime(created_at)` and an unread marker only when `is_read` is false. A click on an unread item calls `markAsRead`, then `router.push('/boards/' + board_id)`, then closes the panel. Escape and a click outside close the panel
    - _Depends on: 4.4, 2.6, 5.1, 5.2_
    - _Requirements: 18.4, 18.5, 18.6, 18.9, 22.6_

  - [x] 7.2 Implement `components/Header.tsx`
    - Render the brand link, `NotificationBell` and a `<nav id="main-nav">` with links to `/`, `/my-tasks`, `/profile`, the user name and a "Log out" `BaseButton` that calls `logout()` and waits for no response. Below `sm` the nav has class `hidden` unless `menuOpen`, and a menu `BaseButton` (`aria-label="Toggle navigation"`, `aria-expanded`, `aria-controls="main-nav"`, class `sm:hidden`) toggles `menuOpen`. From `sm` up the nav is inline and the menu button is hidden by CSS only
    - _Depends on: 7.1, 3.1, 5.1_
    - _Requirements: 2.5, 18.10, 21.2, 21.7, 21.8, 22.6_

  - [x] 7.3 Implement `components/AppShell.tsx`
    - Use `usePathname()`. Render `Header` on every path except `/login` and `/register`, and wrap the children in `<main class="mx-auto w-full max-w-screen-2xl px-4 py-6">`
    - _Depends on: 7.2_
    - _Requirements: 2.5, 18.10, 21.1_

  - [x] 7.4 Implement `app/layout.tsx`
    - Server Component. Export `metadata` and the `viewport` export (`width=device-width, initial-scale=1`). Call `getServerSession()` and render `AuthProvider` with the initial token and user, `AppShell` and exactly one `Toaster` from `react-hot-toast`. Import `./globals.css`
    - A 401 from `/api/users/me` renders with a null session. Any other `ApiError` propagates to `app/global-error.tsx`
    - _Depends on: 1.3, 2.9, 3.1, 7.3_
    - _Requirements: 1.3, 1.4, 1.5, 1.6, 6.4, 21.5, 21.6_

  - [x] 7.5 Implement `proxy.ts` (Route_Guard)
    - `export function proxy(request: NextRequest)`: pass `/login` and `/register`, pass any other path when `request.cookies.get(SESSION_COOKIE)?.value` is a non-empty string, otherwise `NextResponse.redirect(new URL('/login', request.url))`. Do not validate the token
    - `export const config = { matcher: [...] }` excluding `_next/static`, `_next/image`, `favicon.ico` and static-asset extensions (`svg`, `png`, `jpg`, `jpeg`, `gif`, `webp`, `ico`, `css`, `js`, `map`, `txt`, `xml`)
    - _Depends on: 2.8_
    - _Requirements: 2.1, 2.2, 2.6_

  - [x] 7.6 Implement `app/error.tsx`
    - Client Component receiving `{ error, retry }`. Render "Something went wrong." and a "Try again" `BaseButton` whose click calls `retry()`. Do not show `error.message` and do not log to the console
    - _Depends on: 5.1_
    - _Requirements: 9.7, 10.13, 16.7_

  - [x] 7.7 Implement `app/global-error.tsx`
    - Client Component with its own `<html><body>`, importing `./globals.css`, with the same content and the same "Try again" button as `app/error.tsx`
    - _Depends on: 1.3, 5.1, 7.6_
    - _Requirements: 1.6_

  - [x] 7.8 Implement `app/not-found.tsx`
    - Server Component with the text "Page not found" and a link to `/`
    - _Depends on: 1.3_
    - _Requirements: 10.5, 19.11, 20.7_

  - [x] 7.9 Implement `components/NotMemberMessage.tsx`
    - Server Component with `<p>You are not a member of this board</p>` and a `Link` to `/`
    - _Depends on: 1.3_
    - _Requirements: 10.6, 19.11_

- [x] 8. Implement the login and register pages
  - [x] 8.1 Implement `components/auth/LoginForm.tsx` and `app/login/page.tsx`
    - `page.tsx` is a Server Component: `const { reason } = await searchParams` and `<LoginForm sessionExpired={reason === 'session-expired'} />`
    - `LoginForm` (Client Component, prop `sessionExpired`): controlled `email` and masked `password` inputs through `FormField`, a primary submit `BaseButton` with `type="submit"` and a link to `/register`. When a token is held and `sessionExpired` is false, render nothing and `router.replace('/')`. When `sessionExpired`, call `clearSession()` in an effect and show "Your session has expired. Please log in again."
    - Submit: an email with no non-whitespace character or an empty password shows a field error next to each such field and sends no request. Otherwise disable the button, `POST /api/auth/login`, then `login(access_token, expires_in, user)` and `router.replace('/')`. A 401 shows the message in `FormAlert` above the form and keeps the email. Any other error goes to `useErrorHandler`. Re-enable the button on failure
    - _Requirements: 2.4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 22.5, 22.8, 24.4_

  - [x] 8.2 Implement `components/auth/RegisterForm.tsx` and `app/register/page.tsx`
    - `page.tsx` is a Server Component that renders `RegisterForm`
    - `RegisterForm`: controlled `name`, `email` and masked `password` inputs through `FormField` and a primary submit `BaseButton`. The same redirect-when-signed-in guard as `LoginForm`
    - Submit sequence: `validateRegister`, on errors show one message per field and send nothing. Otherwise disable the button, `POST /api/auth/register` with the trimmed email. On 409 or 400 show the message in `FormAlert`, keep the values, show no toast and re-enable. On any other failure call `useErrorHandler`. After a 201 send exactly one `POST /api/auth/login` with the same trimmed email and password and never read a token from the register response. On a login 200 call `login` once, show one success toast ("Welcome to RevoTask!", F12) and `router.replace('/')`. On any login failure show the success toast "Account created. Please log in.", clear the form, `router.replace('/login')`, call `login` zero times and pass nothing to the error handler. The password stays in component state only
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 4.7, 22.5, 22.8, 24.4_

- [x] 9. Implement the dashboard
  - [x] 9.1 Implement `components/CreateBoardModal.tsx`
    - No props. A "Create board" `BaseButton` that is always rendered, and a `BaseModal` with a controlled `name` input through `FormField` and a submit `BaseButton`. Validate with `validateRequiredText('Name', value, 255)`; on an error keep the modal open and send nothing
    - On a valid name disable submit, `POST /api/boards` with the trimmed name, and on success close the modal, show a success toast and `router.push('/boards/' + id)`. On failure call `useErrorHandler`, keep the modal open with the value and re-enable submit
    - _Requirements: 9.3, 9.4, 9.5, 9.6, 22.5, 22.8_

  - [x] 9.2 Implement `app/page.tsx` (Dashboard)
    - Server Component. `serverApi.get<Board[]>('/api/boards')`, a heading and `<CreateBoardModal />`. An empty list shows "You have no boards yet". Otherwise one `Link` to `/boards/<id>` per board in API order with the name and a `BaseBadge` showing the role (blue for `admin`, gray otherwise). A non-401 failure propagates to `app/error.tsx`
    - _Requirements: 9.1, 9.2, 9.3, 9.7, 23.1_

- [ ] 10. Implement the board detail page
  - [ ] 10.1 Implement `components/CardItem.tsx`
    - Props `card`, `assigneeName`, `dnd`, `onOpen`. Render `<li><div role="button" tabIndex={0} data-testid="card" data-card-id={id} {...dnd.cardDragProps(id)}>` (a `div`, not a native `button`, because it is draggable). Show the title, a green "Completed" `BaseBadge` when `completed_at` is set and the assignee name when `assignee_id` is set. Click and Enter call `onOpen`, with Enter only when `e.target === e.currentTarget`
    - _Requirements: 10.3, 22.7, 22.9_

  - [ ] 10.2 Implement `components/KanbanColumn.tsx`
    - Props `column`, `cards`, `memberById`, `dnd`, `onAddCard`, `onRename`, `onDelete`, `onOpenCard`. Render `<section aria-labelledby data-column-id>` with a highlight ring while `dnd.overColumnId` equals the column id. The header carries `dnd.columnHandleProps(id)`, an `h2` with the title, a count `BaseBadge` with the number of shown cards, and rename and delete `BaseButton`s
    - The body is `<ul data-testid="column-cards" {...dnd.cardDropProps(id)}>` with one `CardItem` per card, in `order` ascending, and a "No cards" drop area when the column holds no cards to show. An "Add card" `BaseButton` sits at the bottom
    - _Requirements: 10.2, 10.4, 11.4, 11.6, 13.11, 15.4_

  - [ ] 10.3 Implement `components/CardSearch.tsx`
    - Props `onResults(ids | null)`. A single-line input with `maxLength={200}` whose `onChange` also truncates typed or pasted text to 200 code points. `useDebounce(term, 300)` and the trimmed value drive one effect: an empty term bumps `latestRequest`, calls `onResults(null)` and sends nothing; otherwise `GET /api/cards?search=<encodeURIComponent(trimmed)>` with an incrementing request id
    - A response applies only when its id equals `latestRequest.current`. A stale response is dropped. A failure of the latest request goes to `useErrorHandler` with no inline message and no change to the shown cards
    - _Requirements: 15.1, 15.2, 15.3, 15.5, 15.7, 15.8_

  - [ ] 10.4 Implement `components/BoardHeader.tsx`
    - Props `board { id, name, role }` and `onRenamed(name)`. Show the name, a role `BaseBadge` and a link to `/boards/<id>/members` for every role. Only for `admin`: rename and delete `BaseButton`s and a link to `/boards/<id>/analytics`
    - Rename: `BaseModal` with a `name` input, `validateRequiredText('Name', v, 255)`, `PATCH /api/boards/<id>` with `{ name }`, on 200 `onRenamed(response.name)`, success toast and close. Delete: `ConfirmModal`, `DELETE /api/boards/<id>`, success toast and `router.push('/')`. A failure of either calls `useErrorHandler`, keeps the modal open and changes nothing
    - _Requirements: 10.7, 10.8, 10.9, 10.10, 10.11, 10.12, 22.5, 22.8_

  - [ ] 10.5 Implement `components/ColumnFormModal.tsx`
    - Props `mode` (`create` or `rename`), `open`, `boardId`, `column`, `onClose`, `onSaved`. A `title` input through `FormField`, empty in create mode and pre-filled in rename mode, validated with `validateRequiredText('Title', v, 255)`. Create sends `POST /api/boards/<boardId>/columns`, rename sends `PATCH /api/columns/<id>`. Submit is disabled while pending. A failure calls `useErrorHandler`, keeps the modal open with the title and re-enables submit
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.11, 22.5, 22.8_

  - [ ] 10.6 Implement `components/CardFormModal.tsx`
    - Props `open`, `columnId`, `members`, `onClose`, `onCreated`. Fields `title`, `description` and an `assignee` select (an empty option selected by default, then one option per member in API order). Title is required and at most 255, description at most 10,000. Submit sends `POST /api/columns/<columnId>/cards` with `{ title, description, assignee_id: selected || null }`; on 201 call `onCreated(card)`, close and show a success toast. A failure calls `useErrorHandler`, keeps the modal open with the values and re-enables submit
    - _Requirements: 12.1, 12.2, 12.3, 12.8, 12.9, 22.5, 22.8_

  - [ ] 10.7 Implement `components/CommentList.tsx`
    - Props `cardId`. State `comments` (null before the first response), draft, edit and delete state. `GET /api/cards/<cardId>/comments` once on mount, stored through `sortByCreatedAt(response, 'asc')`. A failed `GET` calls `useErrorHandler` and leaves `comments` null so "No comments yet" never shows. An empty list shows "No comments yet"
    - Each comment shows `content`, `author.name` and `formatDateTime(created_at)`. Edit and delete `BaseButton`s render only when `comment.author.id` equals the Current_User id. The create form (textarea with a visible label and a submit `BaseButton`) validates with `validateComment`, sends `POST /api/cards/<id>/comments`, appends the 201 response and clears the textarea. Edit swaps in a textarea with save and cancel `BaseButton`s and `PATCH /api/comments/<id>`; delete opens a `ConfirmModal` and sends `DELETE /api/comments/<id>`
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8, 14.9, 14.10, 14.11, 14.12, 14.13, 22.5, 22.8_

  - [ ] 10.8 Implement `components/CardDetailModal.tsx`
    - Props `card`, `columnId`, `columns`, `members`, `boardRole`, `dnd`, `onClose`, `onSaved`, `onDeleted`. A `BaseModal` with an edit form (`title`, `description`, `assignee` select, `completed` checkbox, pre-filled from the card), validated like `CardFormModal`. Submit is disabled while `changedCardFields` is empty or a request is pending, and sends `PATCH /api/cards/<id>` with only the changed fields, then `onSaved(response)`
    - A "Column" select lists `columns` and calls `dnd.moveCard(card.id, selectedColumnId, 'end')` on change. The delete `BaseButton` renders only when `card.created_by` equals the Current_User id or `boardRole` is `admin`; it opens a `ConfirmModal`, confirm sends `DELETE /api/cards/<id>` then `onDeleted(id)` and closes both modals, cancel closes only the confirmation. Render `CommentList` below the form. Failures call `useErrorHandler` and keep the entered values
    - _Requirements: 12.4, 12.5, 12.6, 12.7, 12.8, 12.10, 12.11, 13.13, 14.1, 22.5, 22.7, 22.8_

  - [ ] 10.9 Implement `components/BoardView.tsx`
    - Props `initialBoard` and `members`. State: `useReducer(boardReducer, initialBoard, initBoardState)`, `searchIds`, `modal` and `selectedCardId`. `useDragAndDrop` with `disabled: searchIds !== null`. Derive `memberById` and, per column, the shown cards with `visibleCards`
    - Render `BoardHeader`, a toolbar with `CardSearch` and an "Add column" `BaseButton`, and one container `<div class="flex gap-4 overflow-x-auto" {...dnd.columnDropProps()}>` with the columns in `order` ascending. Show "No cards match your search" when a filter is active and every column shows 0 cards. Column delete goes through `ConfirmModal` and `DELETE /api/columns/<id>`, then `column/removed`; a failure calls `useErrorHandler` and leaves the state unchanged
    - Render `ColumnFormModal` and `CardFormModal` from `modal`, and `CardDetailModal` from `selectedCardId`, closing it when `findCard` returns null. Dispatch `column/added` with an empty `cards` list, `column/renamed`, `card/added` (appended last), `card/replaced`, `card/removed` and `board/renamed`
    - _Requirements: 10.2, 10.3, 10.4, 11.3, 11.5, 11.6, 11.10, 12.9, 13.11, 15.4, 15.6, 21.3_

  - [ ] 10.10 Implement `app/boards/[id]/page.tsx`
    - Server Component with `{ params: Promise<{ id: string }> }`. Start `GET /api/boards/<id>` and `GET /api/boards/<id>/members` before awaiting either, then `Promise.all`. A 404 calls `notFound()`, a 403 renders `<NotMemberMessage />`, any other error is rethrown to `app/error.tsx`. Success renders `<BoardView initialBoard members />`
    - _Requirements: 10.1, 10.5, 10.6, 10.13, 13.12, 23.1, 23.3_

- [ ] 11. Implement the My Tasks page
  - [ ] 11.1 Implement `components/OpenBoardButton.tsx`
    - Client Component with the prop `boardId`: a secondary `BaseButton` labelled "Open board" whose `onClick` calls `router.push('/boards/' + boardId)`
    - _Requirements: 8.9, 16.5_

  - [ ] 11.2 Implement `app/my-tasks/page.tsx`
    - Server Component. `serverApi.get<MyTasksGroup[]>('/api/cards?assignee=me')`. An empty list shows "No cards are assigned to you" and no section. Otherwise one `<section>` per group in API order, keyed by `board_id`, with an `h2` holding `board_name` and one list item per card in API order: the title, a `BaseBadge` (green "Completed" when `completed_at` is set, gray "Open" otherwise) and `<OpenBoardButton boardId={group.board_id} />`. A non-401 failure reaches `app/error.tsx`
    - _Requirements: 8.9, 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7, 23.1_

- [ ] 12. Implement the profile page
  - [ ] 12.1 Implement `components/ProfileForm.tsx` and `app/profile/page.tsx`
    - `page.tsx` is a Server Component that renders `ProfileForm`
    - `ProfileForm`: controlled `name` and `email` inputs through `FormField`, pre-populated from `useAuth().user`, and a primary submit `BaseButton`. Validate with `validateProfile`; errors show next to each invalid field and send nothing. Submit is disabled while `changedProfileFields` is empty or a request is pending
    - Send `PATCH /api/users/me` with only the changed fields (email trimmed). On 200 call `updateUser(response)` and show a success toast. A 409 shows the message next to `email`, keeps the values and re-enables submit. Any other error goes to `useErrorHandler`
    - _Requirements: 8.9, 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 22.5, 22.8_

- [ ] 13. Implement the board members page
  - [ ] 13.1 Implement `components/AddMemberModal.tsx`
    - Props `boardId` and `onAdded(member)`. A trigger `BaseButton` and a `BaseModal` with an `email` input (`maxLength` 254, `validateEmail`), a `role` select (`member` default, `admin`) and a submit `BaseButton`. Send `POST /api/boards/<boardId>/members` with the trimmed email and the role; on 201 call `onAdded`, close and show a success toast. A failure calls `useErrorHandler` and keeps the modal open with the values
    - _Requirements: 19.2, 19.3, 19.4, 19.8, 22.5, 22.8_

  - [ ] 13.2 Implement `components/MemberList.tsx`
    - Props `boardId`, `initialMembers`, `currentUserId`, `isAdmin`. Rows in API order with `name`, `email`, a role `BaseBadge` and `<time suppressHydrationWarning>` with `formatDate(created_at)` (F11). For an admin: `AddMemberModal`, a role select per row (`PATCH /api/boards/<boardId>/members/<user_id>`, replace the role from the response, reset the select on failure) and a "Remove" `BaseButton` per row. For a member: a "Leave board" `BaseButton` only on the own row, and no select, remove or add control
    - Removal and leaving go through `ConfirmModal` and `DELETE /api/boards/<boardId>/members/<user_id>`. Removing another member deletes the row, removing oneself calls `router.push('/')`. Failures call `useErrorHandler` and leave the list unchanged
    - _Requirements: 19.1, 19.5, 19.6, 19.7, 19.8, 19.9, 19.10_

  - [ ] 13.3 Implement `app/boards/[id]/members/page.tsx`
    - Server Component. `Promise.all([serverApi.get<Member[]>('/api/boards/<id>/members'), getServerSession()])`. A 404 calls `notFound()`, a 403 renders `<NotMemberMessage />`. `isAdmin` is true when the member whose `user_id` equals the session user id has the role `admin`. Render `<MemberList />`
    - _Requirements: 19.1, 19.11, 23.1_

- [ ] 14. Implement the analytics page
  - [ ] 14.1 Implement `components/AnalyticsPanel.tsx`
    - Server-compatible component with no hook and no directive. Props `cardsPerColumn`, `completedThisWeek`, `memberActivity`. One bar per item in API order with the title and the integer count as text and a `div role="img" aria-label="<title>: <count>"` whose inline `width` comes from `barPercentages`. An empty `cardsPerColumn` shows "This board has no columns". Show `completedThisWeek` next to the label "Completed this week" and one entry per member from `sortByActionsDesc(memberActivity)` with the name and `actions`
    - _Requirements: 20.2, 20.3, 20.4, 20.6_

  - [ ] 14.2 Implement `app/boards/[id]/analytics/page.tsx`
    - Server Component. `serverApi.get<Analytics>('/api/boards/<id>/analytics')` once. A 403 renders "Analytics are available to board administrators" and a link to `/boards/<id>` with no chart, count or member list. A 404 calls `notFound()`. Success renders `<AnalyticsPanel />`
    - _Requirements: 20.1, 20.5, 20.7, 23.1_

- [ ] 15. Checkpoint - Ensure the application builds
  - Copy `.env.example` to `.env.local`, then run `npm run typecheck` and `npm run build` from `frontend/` and ensure both exit with code 0, ask the user if questions arise.

- [ ] 16. Write the lib and pure-logic tests
  - [ ]* 16.1 Write unit tests for `lib/errors.ts` and `lib/toast.ts`
    - Create `__tests__/lib/errors.test.ts` and `__tests__/lib/toast.test.ts`
    - `ApiError` keeps `statusCode` and `message`, satisfies `instanceof ApiError` and `instanceof Error` across modules. Each toast wrapper function calls the matching `react-hot-toast` function once with the same arguments and returns its id, and `dismiss()` with no id dismisses all
    - _Requirements: 6.1, 6.2, 6.3, 6.5, 24.5_

  - [ ]* 16.2 Write unit tests for `lib/apiClient.ts`
    - Create `__tests__/lib/apiClient.test.ts` (client, jsdom) and `__tests__/lib/apiClient.server.test.ts` (`// @vitest-environment node`)
    - Cover: a 2xx response returns `data`, the `Authorization` header with and without a token, a non-2xx response throws `ApiError` with the status and the `error` text or `Request failed with status <status>`, a rejected `fetch` gives status 0, the base URL from `NEXT_PUBLIC_API_BASE_URL` (client) and `API_BASE_URL` with the fallback (server) with trailing slashes removed, an unset variable throws an error naming it, and `cache: 'no-store'` on the server
    - _Requirements: 5.1, 5.2, 5.3, 5.5, 5.6, 5.7, 5.8, 5.10, 25.6_

  - [ ]* 16.3 Write property test for response handling
    - Create `__tests__/lib/apiClient.property.test.ts`
    - **Property 11: Response handling**
    - **Validates: Requirements 5.5, 5.6, 5.7, 6.1, 6.2**

  - [ ]* 16.4 Write property test for request construction
    - Add to `__tests__/lib/apiClient.property.test.ts`. Run the server-side half with `vi.stubGlobal('window', undefined)` inside the same property
    - **Property 12: Request construction**
    - **Validates: Requirements 5.1, 5.3, 5.4, 5.8, 5.10**

  - [ ]* 16.5 Write unit tests for `lib/order.ts`
    - Create `__tests__/lib/order.test.ts`
    - Neighbours 1.0 and 2.0 give 1.5, a first card with order 2.0 gives 1.0, a last card with order 3.0 gives 4.0, an empty column gives 1.0
    - _Requirements: 13.2, 13.3, 13.4, 13.5, 25.4_

  - [ ]* 16.6 Write property test for order placement
    - Create `__tests__/lib/order.property.test.ts`
    - **Property 1: Order placement**
    - **Validates: Requirements 11.7, 13.2, 13.3, 13.4, 13.5, 13.13**

  - [ ]* 16.7 Write property test for drop index
    - Add to `__tests__/lib/order.property.test.ts`
    - **Property 2: Drop index from midpoints**
    - **Validates: Requirements 13.14**

  - [ ]* 16.8 Write unit tests for `lib/validation.ts`
    - Create `__tests__/lib/validation.test.ts`
    - Boundary cases of every validator (0, 1, 255, 256 characters, password 7, 8, 128, 129, email 2, 3, 254, 255, whitespace-only values), email grammar examples (`a@b.c` valid, `a@.c`, `a@b.`, `@b.c`, `a b@c.d`, two `@` invalid), and the changed-field helpers
    - _Requirements: 3.2, 3.3, 4.2, 12.2, 12.10, 14.5, 17.2, 19.3_

  - [ ]* 16.9 Write property test for validators
    - Create `__tests__/lib/validation.property.test.ts`. Strings mix boundary lengths with `fc.string({ unit: 'binary' })` so that non-BMP code points and whitespace-only values occur
    - **Property 14: Validators accept exactly the specified inputs**
    - **Validates: Requirements 3.2, 3.3, 4.2, 9.4, 10.10, 11.2, 12.2, 12.10, 14.5, 17.2, 19.3**

  - [ ]* 16.10 Write property test for changed fields
    - Add to `__tests__/lib/validation.property.test.ts`
    - **Property 15: Edits send only changed fields**
    - **Validates: Requirements 12.4, 12.5, 12.11, 17.3, 17.4**

  - [ ]* 16.11 Write unit tests for `lib/session.ts`
    - Create `__tests__/lib/session.test.ts`
    - `writeSessionCookie` writes the cookie string with `Secure` on `https:` and without it on `http:`, `clearSessionCookie` sets `Max-Age=0` with `Path=/`, and the string never contains `HttpOnly`
    - _Requirements: 1.1, 1.2, 1.7_

  - [ ]* 16.12 Write property test for the session cookie string
    - Create `__tests__/lib/session.property.test.ts`
    - **Property 16: Session cookie string**
    - **Validates: Requirements 1.1, 1.2**

  - [ ]* 16.13 Write unit tests for `lib/serverSession.ts` and `lib/serverApi.ts`
    - Create `__tests__/lib/serverSession.test.ts` and `__tests__/lib/serverApi.test.ts` (`// @vitest-environment node`, `next/headers` and `next/navigation` mocked)
    - Cover: no cookie or an empty cookie gives the null pair and no request, `/me` success, `/me` 401 gives the null pair without throwing, `/me` 500 rethrows, `serverApi` redirects to `/login?reason=session-expired` on a 401 and rethrows other errors
    - _Requirements: 1.3, 1.4, 1.5, 1.6, 1.9, 2.3_

  - [ ]* 16.14 Write property test for sorting helpers
    - Create `__tests__/lib/collections.property.test.ts`
    - **Property 19: Sorting helpers**
    - **Validates: Requirements 14.2, 18.5, 20.4**

  - [ ]* 16.15 Write property test for bar percentages
    - Add to `__tests__/lib/collections.property.test.ts`
    - **Property 20: Bar percentages**
    - **Validates: Requirements 20.2**

  - [ ]* 16.16 Write property test for unread count and badge text
    - Create `__tests__/lib/format.property.test.ts`. Check `formatUnreadCount` directly and `unreadCount` through `renderHook(useNotifications)` with a mocked `apiClient`
    - **Property 18: Unread count and badge text**
    - **Validates: Requirements 18.3, 18.4**

  - [ ]* 16.17 Write unit tests for `lib/boardState.ts`
    - Create `__tests__/lib/boardState.test.ts`
    - Examples for each action, `card/replaced` keeps the position, `state/restored` returns the snapshot itself, a repeated `card/moved` with the same arguments is idempotent, equal orders place the moved card after the existing one, and `visibleCards` with `null` and with a set
    - _Requirements: 10.2, 11.3, 11.5, 11.6, 12.9, 13.7, 15.4_

  - [ ]* 16.18 Write property test for move invariants
    - Create `__tests__/lib/boardState.property.test.ts`. Board generators use unique ids, strictly increasing orders with a gap of at least 1e-6 and 0 to 6 cards per column
    - **Property 3: Moves preserve board invariants**
    - **Validates: Requirements 11.7, 13.6, 13.7**

  - [ ]* 16.19 Write property test for applied rebalance orders
    - Add to `__tests__/lib/boardState.property.test.ts`
    - **Property 6: Rebalanced orders are applied exactly**
    - **Validates: Requirements 11.8, 13.10**

  - [ ]* 16.20 Write property test for search filter and counts
    - Add to `__tests__/lib/boardState.property.test.ts`, using `visibleCards` and the column count rule
    - **Property 9: Search filter and counts**
    - **Validates: Requirements 15.4, 15.6**

  - [ ]* 16.21 Write property test for the route guard
    - Create `__tests__/lib/proxy.property.test.ts` (`// @vitest-environment node`, `NextRequest` built from `next/server`)
    - **Property 17: Route guard**
    - **Validates: Requirements 2.1, 2.2, 2.6**

- [ ] 17. Write the hook and context tests
  - [ ]* 17.1 Write unit tests for `AuthProvider`
    - Create `__tests__/auth/AuthContext.test.tsx`
    - `login` sets state and writes the cookie, `logout` clears state and the cookie and calls `router.replace('/login')` with no request, `clearSession` does not navigate, `updateUser` replaces the user and leaves the token and cookie unchanged, `useAuth` throws outside the provider
    - _Requirements: 1.1, 1.7, 1.8, 2.5_

  - [ ]* 17.2 Write unit tests for `useApi`
    - Create `__tests__/hooks/useApi.test.tsx`
    - Each method forwards the Auth_Context token to the mocked `apiClient`, and the returned object is stable while the token is stable
    - _Requirements: 5.3_

  - [ ]* 17.3 Write unit tests for `useErrorHandler`
    - Create `__tests__/hooks/useErrorHandler.test.tsx`, with the Toast_Wrapper mocked
    - The mocked `error` receives the Requirement 7 message for statuses 400, 401, 403, 404, 409, 0, 500 and for a thrown error that is not an `ApiError`. `logout` is called once for 401 and never for another status
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 25.5_

  - [ ]* 17.4 Write property test for error handler message mapping
    - Create `__tests__/hooks/useErrorHandler.property.test.ts`
    - **Property 13: Error handler message mapping**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.8**

  - [ ]* 17.5 Write unit tests for `useDebounce`
    - Create `__tests__/hooks/useDebounce.test.tsx` with fake timers
    - The value changes only after the delay, and a change inside the delay restarts the interval
    - _Requirements: 15.2, 15.3, 25.8_

  - [ ]* 17.6 Write unit tests for `useNotifications`
    - Create `__tests__/hooks/useNotifications.test.tsx` with fake timers and the `apiClient` mocked
    - Exactly 1 request on mount, none after advancing 29,999 ms, exactly 1 more at 30,000 ms, none after the token becomes null or after unmount. `markAsRead` is optimistic and rolls back with one error handler call. A non-401 polling failure keeps `items` and shows no toast, a 401 calls the error handler and stops polling
    - _Requirements: 18.1, 18.2, 18.3, 18.6, 18.7, 18.8, 18.11, 25.5, 25.8_

  - [ ]* 17.7 Write unit tests for `useDragAndDrop`
    - Create `__tests__/hooks/useDragAndDrop.test.tsx`, with the `apiClient` mocked, a stub `dataTransfer` and stubbed `getBoundingClientRect`
    - The state shows the card at its new position before the pending PATCH resolves, a rejected PATCH restores a state deeply equal to the one before the drop and calls the error handler once, `rebalanced: true` replaces the orders of the target column from `siblings`, a column reorder behaves the same way, a drop outside a column and an Escape cancel send nothing, only one column is highlighted at a time, and dragging is blocked while `disabled` or `isMoving`
    - _Requirements: 11.7, 11.8, 11.9, 11.10, 13.1, 13.6, 13.7, 13.8, 13.9, 13.10, 13.11, 13.14, 13.15, 25.4_

  - [ ]* 17.8 Write property test for drops at the current position
    - Create `__tests__/hooks/useDragAndDrop.property.test.tsx`
    - **Property 4: Drops at the current position are no-ops**
    - **Validates: Requirements 11.9, 13.8**

  - [ ]* 17.9 Write property test for failed moves
    - Add to `__tests__/hooks/useDragAndDrop.property.test.tsx`
    - **Property 5: A failed move restores the prior state**
    - **Validates: Requirements 11.10, 13.7, 13.9**

- [ ] 18. Write the shared component tests
  - [ ]* 18.1 Write unit tests for `BaseButton`
    - Create `__tests__/shared/BaseButton.test.tsx`
    - Each variant renders a native `button` with a distinct class set, the default variant is `primary`, `onClick` is not called when `disabled` or `loading` is true, `type` defaults to `button`, other native props are forwarded
    - _Requirements: 8.1, 8.2, 8.3, 25.2_

  - [ ]* 18.2 Write unit tests for `BaseBadge`
    - Create `__tests__/shared/BaseBadge.test.tsx`
    - Each color renders a distinct class set and the default color is `gray`
    - _Requirements: 8.4, 25.2_

  - [ ]* 18.3 Write unit tests for `BaseModal`
    - Create `__tests__/shared/BaseModal.test.tsx` with `userEvent` and fake timers
    - `open` true renders `role="dialog"`, `aria-modal`, `aria-labelledby`, the title heading and the children, `open` false renders nothing, Escape and a backdrop click each call `onClose` once and a click inside does not, Tab on the last element focuses the first and Shift+Tab on the first focuses the last, focus moves in within 100 ms, closing returns focus to the opener or to `body`, and with two stacked modals only the topmost traps focus
    - _Requirements: 8.5, 8.6, 8.7, 22.1, 22.2, 22.3, 22.4, 25.2_

  - [ ]* 18.4 Write unit tests for `ConfirmModal` and `FormAlert`
    - Create `__tests__/shared/ConfirmModal.test.tsx` and `__tests__/shared/FormAlert.test.tsx`
    - Confirm calls `onConfirm`, cancel calls `onCancel` and nothing else, confirm is disabled while `pending`, `FormAlert` renders `role="alert"` only while a message is set
    - _Requirements: 8.8, 14.13, 22.8_

  - [ ]* 18.5 Write property test for form field accessibility wiring
    - Create `__tests__/shared/FormField.property.test.tsx`
    - **Property 21: Form field accessibility wiring**
    - **Validates: Requirements 22.5, 22.8**

- [ ] 19. Write the shell and authentication page tests
  - [ ]* 19.1 Write unit tests for `LoginForm`
    - Create `__tests__/auth/LoginForm.test.tsx` with the `apiClient` mocked and `next/navigation` mocked
    - An empty email or an empty password shows an error next to the field and leaves the mock uncalled, a valid submit calls the mock exactly once, success calls `login` and redirects to `/`, a 401 shows the message above the form and keeps the email, another error calls the error handler, `sessionExpired` clears the session and shows the expired message, a held token redirects to `/`
    - _Requirements: 2.4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 25.3_

  - [ ]* 19.2 Write unit tests for `RegisterForm`
    - Create `__tests__/auth/RegisterForm.test.tsx` with the `apiClient`, `login`, router, Toast_Wrapper and Error_Handler mocked
    - Field errors with an uncalled mock for a `name` of 0 or 256 characters, an `email` of 2 or 255 characters or without a valid format, and a `password` of 7 or 129 characters. A valid submit calls register once and then login once with the trimmed email and the password, calls `login` once, redirects to `/`, and keeps the submit button disabled until both mocks resolved. A rejected login shows the toast "Account created. Please log in." once, redirects to `/login`, leaves `login` and the error handler uncalled. A 409 or 400 on register shows the message inline with no toast. The password is never written to storage, cookies or a URL
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 25.3_

  - [ ]* 19.3 Write unit tests for `NotificationBell`
    - Create `__tests__/components/NotificationBell.test.tsx`
    - No badge for 0, the number for 1 to 99, "99+" above 99, a non-empty `aria-label`, "No notifications" for an empty list, items ordered by `created_at` descending, an unread marker only on unread items, a click on an unread item marks it read, navigates to `/boards/<board_id>` and closes the panel
    - _Requirements: 18.4, 18.5, 18.6, 18.9, 22.6_

  - [ ]* 19.4 Write unit tests for `Header`
    - Create `__tests__/components/Header.test.tsx`
    - The logout button calls `logout` once, the Notification_Bell is rendered with an `aria-label`, the menu button toggles the nav and sets `aria-expanded`, and the nav and menu button carry the CSS classes that hide and show them per breakpoint
    - _Requirements: 2.5, 18.10, 21.2, 21.7, 21.8, 22.6_

  - [ ]* 19.5 Write unit tests for `app/layout.tsx` and `AppShell`
    - Create `__tests__/components/layout.test.tsx` and `__tests__/components/AppShell.test.tsx`
    - Call the async layout with `getServerSession` mocked: the token and the user reach `AuthProvider`, a null session sends no `/me` request, a 401 renders with a null session, another error propagates, exactly one `Toaster` renders, and the viewport export is `width=device-width, initial-scale=1`. `AppShell` hides `Header` on `/login` and `/register` and shows it elsewhere
    - _Requirements: 1.3, 1.4, 1.5, 1.6, 6.4, 21.5_

  - [ ]* 19.6 Write unit tests for the error and not-found pages
    - Create `__tests__/components/errorPages.test.tsx`
    - `app/error.tsx` and `app/global-error.tsx` render "Try again" and call `retry()` on click and show no `error.message`, `app/not-found.tsx` links to `/`, `NotMemberMessage` renders the text and the link to `/`
    - _Requirements: 1.6, 9.7, 10.5, 10.6, 10.13, 16.7_

- [ ] 20. Write the board feature tests
  - [ ]* 20.1 Write unit tests for `CardSearch`
    - Create `__tests__/components/CardSearch.test.tsx` with fake timers and the `apiClient` mocked
    - No request after 299 ms without typing, exactly 1 request at 300 ms, a burst of keystrokes less than 300 ms apart gives exactly 1 request, an empty trimmed term sends nothing and calls `onResults(null)`, a stale response is ignored, a failure calls the error handler and shows no inline message
    - _Requirements: 15.1, 15.2, 15.3, 15.5, 15.7, 15.8, 25.7, 25.8_

  - [ ]* 20.2 Write property test for the debounce
    - Create `__tests__/components/CardSearch.property.test.tsx` with fake timers
    - **Property 7: Debounce sends one request with the last value**
    - **Validates: Requirements 15.2, 15.3, 15.5**

  - [ ]* 20.3 Write property test for stale search responses
    - Add to `__tests__/components/CardSearch.property.test.tsx`
    - **Property 8: Stale search responses are ignored**
    - **Validates: Requirements 15.5, 15.7**

  - [ ]* 20.4 Write property test for search input truncation
    - Add to `__tests__/components/CardSearch.property.test.tsx`
    - **Property 10: Search input truncation**
    - **Validates: Requirements 15.1**

  - [ ]* 20.5 Write unit tests for `CommentList`
    - Create `__tests__/components/CommentList.test.tsx` with the `apiClient` mocked
    - A valid submit appends the returned comment and clears the textarea, a valid edit replaces the comment in place, a delete removes it after confirmation and not after cancel, comments render oldest first, an empty list shows "No comments yet", a failed `GET` shows an error and not "No comments yet", invalid content shows an error and sends nothing
    - _Requirements: 14.2, 14.3, 14.5, 14.6, 14.8, 14.9, 14.11, 14.12, 14.13, 25.7_

  - [ ]* 20.6 Write property test for comment controls
    - Create `__tests__/components/CommentList.property.test.tsx`
    - **Property 23: Comment controls follow authorship**
    - **Validates: Requirements 14.7, 14.10**

  - [ ]* 20.7 Write unit tests for `CardItem` and `KanbanColumn`
    - Create `__tests__/components/CardItem.test.tsx` and `__tests__/components/KanbanColumn.test.tsx`
    - `CardItem` shows the title, the "Completed" badge and the assignee name when set, has `tabindex="0"`, opens on Enter only when the card itself has focus. `KanbanColumn` shows the title and the count of shown cards, cards in `order` ascending, the "No cards" drop area for an empty column, and the highlight style only on the column under the pointer
    - _Requirements: 10.2, 10.3, 10.4, 13.11, 22.7, 22.9_

  - [ ]* 20.8 Write unit tests for `BoardHeader`
    - Create `__tests__/components/BoardHeader.test.tsx` with the `apiClient` mocked
    - Admin sees rename, delete and both links, a member sees only the members link. Rename validates 1 to 255 characters, shows the error and sends nothing when invalid, replaces the name on 200 and shows a toast. Delete confirms then navigates to `/`. A failed PATCH or DELETE keeps the modal open and calls the error handler
    - _Requirements: 10.7, 10.8, 10.9, 10.10, 10.11, 10.12_

  - [ ]* 20.9 Write unit tests for `ColumnFormModal`
    - Create `__tests__/components/ColumnFormModal.test.tsx` with the `apiClient` mocked
    - Create mode starts empty and rename mode is pre-filled, an empty or 256-character title shows an error and sends nothing, a valid submit disables the button, sends the right request and calls `onSaved`, a failure keeps the modal open with the title and re-enables submit
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.11_

  - [ ]* 20.10 Write unit tests for `CardFormModal`
    - Create `__tests__/components/CardFormModal.test.tsx` with the `apiClient` mocked
    - The assignee select lists an empty option first, then the members in API order, title and description limits show errors and send nothing, a valid submit sends `assignee_id` as the member id or `null`, a 201 calls `onCreated`, closes and shows a toast, a failure keeps the values
    - _Requirements: 12.1, 12.2, 12.3, 12.8, 12.9_

  - [ ]* 20.11 Write unit tests for `CardDetailModal`
    - Create `__tests__/components/CardDetailModal.test.tsx` with the `apiClient` and the drag hook mocked
    - Pre-filled form, the submit button disabled while nothing changed, the PATCH body holds only changed fields, validation errors send nothing, the "Column" select calls `moveCard(cardId, columnId, 'end')`, the delete button shows for the creator and for an admin and not for another member, cancel in the confirmation sends nothing, confirm sends `DELETE` and calls `onDeleted`, `CommentList` is rendered inside the modal
    - _Requirements: 12.4, 12.5, 12.6, 12.7, 12.8, 12.10, 12.11, 13.13, 14.1_

  - [ ]* 20.12 Write unit tests for `BoardView`
    - Create `__tests__/components/BoardView.test.tsx` with the `apiClient` mocked and `getBoundingClientRect` stubbed
    - Columns render side by side in `order` ascending inside an `overflow-x-auto` container, add, rename and delete column, add, edit and delete card, a "Column" select move, a search result filters the cards and updates the counts, "No cards match your search" when nothing matches, cards are not draggable while a filter is active, and a failed request leaves the state unchanged
    - _Requirements: 10.2, 10.4, 11.3, 11.5, 11.6, 11.10, 12.5, 12.6, 12.9, 13.13, 15.4, 15.6, 21.3_

- [ ] 21. Write the remaining page tests
  - [ ]* 21.1 Write unit tests for the dashboard
    - Create `__tests__/components/CreateBoardModal.test.tsx` and `__tests__/components/DashboardPage.test.tsx`
    - The create-board button renders with zero and with many boards, an invalid name shows an error and sends nothing, a valid name sends `POST /api/boards` with the trimmed name then navigates to `/boards/<id>`, a failure keeps the modal open. The page, called as an async function with a mocked `serverApi`, shows "You have no boards yet" for an empty list and a failure propagates
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

  - [ ]* 21.2 Write unit tests for the My Tasks page
    - Create `__tests__/components/MyTasksPage.test.tsx` and `__tests__/components/OpenBoardButton.test.tsx`
    - An empty list shows "No cards are assigned to you", two groups with the same `board_name` render two sections, the badge text and color follow `completed_at`, the "Open board" button navigates to `/boards/<board_id>` of its group, a non-401 failure propagates
    - _Requirements: 8.9, 16.1, 16.2, 16.5, 16.6, 16.7_

  - [ ]* 21.3 Write property test for lists in API order
    - Create `__tests__/components/lists.property.test.tsx`
    - **Property 22: Lists render in API order**
    - **Validates: Requirements 9.1, 16.2, 16.3, 16.4**

  - [ ]* 21.4 Write unit tests for `ProfileForm`
    - Create `__tests__/components/ProfileForm.test.tsx` with the `apiClient` mocked
    - Pre-populated fields, submit disabled while nothing changed, invalid values show errors and send nothing, the PATCH body holds only the changed fields with a trimmed email, a 200 calls `updateUser` and shows a toast, a 409 shows the message next to `email`, any other error calls the error handler
    - _Requirements: 8.9, 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7_

  - [ ]* 21.5 Write unit tests for `AddMemberModal` and `MemberList`
    - Create `__tests__/components/AddMemberModal.test.tsx` and `__tests__/components/MemberList.test.tsx` with the `apiClient` mocked
    - Invalid email shows an error and sends nothing, a 201 appends the member and shows a toast, an admin sees the role select and the remove button on every row, a member sees only "Leave board" on the own row, a role change replaces the role and a failure resets the select, removing another member deletes the row, leaving navigates to `/`, a 409 reaches the error handler and leaves the list unchanged
    - _Requirements: 19.2, 19.3, 19.4, 19.5, 19.6, 19.7, 19.8, 19.9, 19.10_

  - [ ]* 21.6 Write unit tests for the members page
    - Create `__tests__/components/MembersPage.test.tsx`
    - With `serverApi` and `getServerSession` mocked: rows render in API order, `isAdmin` follows the session user's role, a 404 calls `notFound()`, a 403 renders `NotMemberMessage`
    - _Requirements: 19.1, 19.11_

  - [ ]* 21.7 Write unit tests for the analytics page
    - Create `__tests__/components/AnalyticsPanel.test.tsx` and `__tests__/components/AnalyticsPage.test.tsx`
    - The largest bar is 100% wide and all bars are 0% for a maximum of 0, "Completed this week" shows 0, members are ordered by `actions` descending with ties in API order, an empty `cardsPerColumn` shows "This board has no columns" and still shows the count and members. The page calls the API once, a 403 shows "Analytics are available to board administrators" with a link to the board and no chart, a 404 calls `notFound()`
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7_

  - [ ]* 21.8 Write unit tests for the board page
    - Create `__tests__/components/BoardPage.test.tsx`
    - With `serverApi` mocked: both requests start before either is awaited, success renders `BoardView` with the role, columns and members, a 404 calls `notFound()`, a 403 renders `NotMemberMessage` and no `BoardView`, any other error is rethrown
    - _Requirements: 10.1, 10.5, 10.6, 10.13, 23.3_

- [ ] 22. Write the static hygiene tests
  - [ ]* 22.1 Write the source-structure checks
    - Create `__tests__/meta/hygiene.test.ts` that reads files with `node:fs`
    - The five server pages contain no `"use client"` and none of `useState`, `useReducer`, `useEffect`, `useLayoutEffect`. Every file under `components/` and `hooks/` that starts with `"use client"` uses a hook, a handler prop, a context hook or a browser global. No source file declares a type named like an API response outside `lib/types.ts`. Only `lib/serverSession.ts` mentions `revotask_token` or `SESSION_COOKIE` together with `cookies(`. `hooks/useDragAndDrop.ts` imports no drag-and-drop library
    - _Requirements: 1.9, 5.9, 13.1, 23.1, 23.2_

  - [ ]* 22.2 Write the configuration checks
    - Add to `__tests__/meta/hygiene.test.ts`
    - `package.json` has no chart, drag-and-drop or state-management package and defines the six scripts with non-empty commands. `tsconfig.json` has `strict: true` and no strict-family flag set to false. `.env.example` has the three variables with `localhost` URLs, no trailing slash and no secret. `.gitignore` lists the required entries, does not match `.env.example` and does not list `playwright-report/`. No file under `__tests__/` or `e2e/` contains `.skip`, `.todo`, `.only`, `xit`, `xdescribe`, `waitForTimeout` or a real-time sleep. `tailwind.config.ts` and `app/globals.css` declare no other CSS framework
    - _Requirements: 21.6, 23.4, 24.1, 25.1, 25.8, 26.6, 26.8, 27.1, 27.3, 27.8_

- [ ] 23. Checkpoint - Ensure all tests pass
  - Run `npm run lint`, `npm run typecheck` and `npm test` from `frontend/`, ensure all tests pass with 0 failed and 0 skipped, ask the user if questions arise.

- [ ] 24. Write the Playwright end-to-end suite
  - [ ] 24.1 Create `e2e/helpers/auth.ts`
    - `TestUser` and `newUser()`: email `e2e-<Date.now()>-<12-character random hex>@example.com`, a name of 1 to 255 characters and a generated password of 8 to 128 characters. No stored credentials
    - `registerThroughUi(page, { user, expectLogoutButton })`: go to `/register`, fill the labelled fields, submit, `await expect(page).toHaveURL((u) => u.pathname === '/')`, then expect the "Log out" button visible unless `expectLogoutButton` is false. `logoutThroughUi(page)`: open the menu first when the menu button is visible, then click "Log out"
    - _Requirements: 26.2, 26.5, 26.6, 26.7_

  - [ ]* 24.2 Write `e2e/auth.spec.ts`
    - Four scenarios, each ending with a web-first assertion: (a) register a unique user, expect the path `/` and the logout button visible with no separate login step, (b) register, log out, log in with a wrong password, expect the path `/login` and the API message visible above the form, (c) a fresh context with no cookie requests `/` and ends on `/login`, (d) register, click logout, expect `/login`, then `page.goto('/')` and expect `/login` again
    - _Requirements: 2.1, 2.5, 2.6, 26.2, 26.6, 26.7_

  - [ ]* 24.3 Write `e2e/kanban.spec.ts`
    - One test with eight `test.step` calls named "Step 1 ..." to "Step 8 ...", so that a failing step stops the later steps and names its number: (1) register and see `/` with the logout button, (2) create a board and see `/boards/<id>` with the name, (3) add column "To Do", (4) add column "Done", (5) create a card in "To Do" and see it inside that region, (6) open the card, add a comment and see the `content` and the user's name, (7) start `waitForResponse` for the `PATCH` to `/position`, run `dragTo` onto the "Done" `column-cards` list, await the response and see the card in "Done", (8) read the card's index among the "Done" cards, `page.reload()` and expect the same index
    - Use `getByRole('region', { name })` for columns and the `card` and `column-cards` test ids. No `waitForTimeout`
    - _Requirements: 13.12, 26.3, 26.4, 26.6, 26.7_

  - [ ]* 24.4 Write `e2e/responsive.spec.ts`
    - `test.use({ viewport: { width: 375, height: 667 } })`. Register a user (with `expectLogoutButton: false`, because the nav is collapsed), then on `/` and on a board created in the test assert `document.documentElement.scrollWidth <= clientWidth` through `expect.poll`. Also assert that the menu button is visible at 375 px and hidden at 1280 px
    - _Requirements: 21.1, 21.2, 21.8, 26.5, 26.6_

- [ ] 25. Write the README
  - [ ] 25.1 Create `README.md`
    - Setup: `npm install` (explain that `.npmrc` sets `allow-remote=all` because npm 12 blocks the tarball URL of Tailwind's optional WASM package and fails with `EALLOWREMOTE`), and copying `.env.example` to `.env.local`
    - The commands `npm run dev`, `npm run build`, `npm test` and `npm run test:e2e`, each with a one-sentence description
    - Vercel: project root directory `frontend`, set `NEXT_PUBLIC_API_BASE_URL` and `API_BASE_URL` to the API origin (for example the Railway URL, no trailing slash and no `/api`), `PLAYWRIGHT_BASE_URL` is not needed in Vercel, `NEXT_PUBLIC_*` values are compiled in so a change needs a redeploy, and a note to check the first Vercel build log for the `.npmrc` setting and the install step
    - CORS: the backend `CORS_ORIGINS` must list the exact Vercel origin as `https://<host>` with no trailing slash and no path, and `http://localhost:3000`. Server Component requests are server-to-server and need no `CORS_ORIGINS` entry. A Vercel preview deployment has its own origin and needs its own entry
    - _Requirements: 27.4, 27.5, 27.6, 27.7_

- [ ] 26. Add the Vercel deployment configuration
  - [ ] 26.1 Create `vercel.json`
    - `$schema` `https://openapi.vercel.sh/vercel.json`, `framework` `nextjs`, `installCommand` `npm ci` and `buildCommand` `npm run build`. Holds no environment value and no secret. The project root directory `frontend` and the two API variables are set in the Vercel project, as the README states
    - _Requirements: 24.3, 27.2, 27.4_

- [ ] 27. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP. Requirements 25 and 26 (Component_Tests and E2E_Suite) are met only when the optional tests are written.
- Each task references specific requirements for traceability. Every page and every file of the design's directory layout has a task: pages `/login` and `/register` (8.1, 8.2), `/` (9.2), `/boards/[id]` (10.10), `/boards/[id]/members` (13.3), `/boards/[id]/analytics` (14.2), `/my-tasks` (11.2), `/profile` (12.1); `app/layout.tsx` (7.4), `app/error.tsx` (7.6), `app/global-error.tsx` (7.7), `app/not-found.tsx` (7.8), `proxy.ts` (7.5); the shared components (5.1 to 5.6); the lib modules (2.1 to 2.10); `context/AuthContext.tsx` (3.1); the hooks (4.1 to 4.5); the configuration files (1.1 to 1.7).
- Checkpoints ensure incremental validation. Checkpoint 6 and 15 run the type check, the linter and the build, because the tests come after the implementation (tasks 16 to 22).
- Property tests validate Properties 1 to 23 of `design.md` with `fast-check`, at least 100 runs each, and carry the tag comment `// Feature: frontend, Property <n>: <title>`. Property 4 is one test in `useDragAndDrop.property.test.tsx` (17.8). The design also lists it under `boardState.property.test.ts`, where the reducer-level part (a repeated `card/moved` is idempotent) is an example test in 16.17.
- Time-dependent tests use `vi.useFakeTimers()` and advance time with `await act(async () => { await vi.advanceTimersByTimeAsync(ms) })`. No test sleeps (Requirement 25.8, 26.6).
- Run the unit and property suite from `frontend/` with `npm test`, the type check with `npm run typecheck`, and the end-to-end suite with `PLAYWRIGHT_BASE_URL=<vercel url> npm run test:e2e`. The E2E suite needs a deployed frontend and backend, so it cannot run before the Vercel deployment exists.
- Verify the Vercel build after the first deployment. `.npmrc` sets `allow-remote=all`, an npm 12 setting. If Vercel installs with an older npm that warns about an unknown config key, the install still succeeds, and if Vercel uses npm 12 the key is what lets it install Tailwind's WASM package. Check the install step of the build log either way.
- Open points from `design.md` stay open: TypeScript stays on 5.9 until `typescript-eslint` accepts 6.x, ESLint stays on 9 until `eslint-plugin-react` and `eslint-plugin-jsx-a11y` accept 10, and the `dragTo` step of the Kanban_Journey depends on Chromium accepting the synthesized drag.
- The helpers `changedCardFields`, `changedProfileFields` and `visibleCards` (tasks 2.5 and 2.7) are task-level additions that the design does not name. Rejecting them means testing Properties 9 and 15 through rendered components instead.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.3", "1.4", "1.5", "1.6", "1.7"] },
    { "id": 1, "tasks": ["1.2"] },
    {
      "id": 2,
      "tasks": [
        "2.1", "2.2", "2.4", "2.6", "2.8", "4.3", "5.1", "5.2", "5.3", "5.5", "5.6", "7.8", "7.9"
      ]
    },
    {
      "id": 3,
      "tasks": [
        "2.3", "2.5", "2.7", "3.1", "5.4", "7.5", "7.6", "11.1", "14.1",
        "16.1", "16.5", "16.6", "16.11", "16.12", "16.14", "17.5", "18.1", "18.2", "18.3", "18.5"
      ]
    },
    {
      "id": 4,
      "tasks": [
        "2.9", "3.2", "4.1", "4.2", "7.7",
        "16.2", "16.3", "16.7", "16.8", "16.9", "16.15", "16.17", "16.18", "16.21", "18.4", "19.6"
      ]
    },
    {
      "id": 5,
      "tasks": [
        "2.10", "4.4", "4.5", "8.1", "8.2", "9.1", "10.3", "10.4", "10.5", "10.6", "10.7", "12.1", "13.1",
        "16.4", "16.10", "16.19", "17.1", "17.2", "17.3", "17.4"
      ]
    },
    {
      "id": 6,
      "tasks": [
        "7.1", "9.2", "10.1", "10.8", "11.2", "13.2", "14.2",
        "16.13", "16.16", "16.20", "17.6", "17.7", "17.8", "19.1", "19.2",
        "20.1", "20.2", "20.5", "20.6", "20.8", "20.9", "20.10"
      ]
    },
    {
      "id": 7,
      "tasks": [
        "7.2", "10.2", "13.3",
        "17.9", "19.3", "20.3", "20.11", "21.1", "21.2", "21.3", "21.4", "21.5", "21.7"
      ]
    },
    { "id": 8, "tasks": ["7.3", "10.9", "19.4", "20.4", "20.7", "21.6"] },
    { "id": 9, "tasks": ["7.4", "10.10", "20.12"] },
    { "id": 10, "tasks": ["19.5", "21.8", "22.1", "24.1"] },
    { "id": 11, "tasks": ["24.2", "24.3", "24.4", "25.1", "26.1"] },
    { "id": 12, "tasks": ["22.2"] }
  ]
}
```
