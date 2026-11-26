# Requirements Document

Version: V2 (see `CHANGELOG.md`)

## Introduction

This spec covers the Next.js frontend of RevoTask, a Trello-like task manager. Two kinds of users work in it. Board members create and manage boards, organize work into columns, move cards by drag-and-drop, collaborate in comments and track the cards assigned to them. Board administrators additionally manage member access, oversee all cards of a board and monitor team activity through analytics and notifications.

The frontend consumes the Flask REST API specified in `.kiro/specs/backend/` (requirements V2) and does not redefine it. The API contract this spec relies on is: the Success_Envelope `{"data": ...}` and the Error_Envelope `{"error": "..."}`; the login response `{access_token, token_type, expires_in, user: {id, name, email}}`; the board detail with nested `columns` and `cards`; the card move response with `rebalanced` and `siblings`; the column reorder response `{columns, rebalanced}`; the notifications page `{items, page, per_page, total}`; `GET /api/cards?assignee=me` grouped by board; `GET /api/cards?search=`; comments with `content` and `author`; the board member routes; the analytics shape; and the error status order 401, 404, 403, 400, 409. The database spec is not touched.

The frontend lives in a new `frontend/` directory at the repository root and uses the Next.js App Router, TypeScript and Tailwind CSS. Every file path in this document is relative to `frontend/`. Every acceptance criterion ends with a tag that names the page, component, hook or lib file it maps to, for example `(Page: /login)` or `(File: hooks/useDragAndDrop.ts)`, so that `design.md` and `tasks.md` can trace it. The last section holds the traceability matrix. The decisions that the brief and the backend spec left open are listed in "Decisions Beyond the Brief" below the Glossary.

## Glossary

- **Frontend**: The Next.js application in `frontend/` defined by this spec.
- **API**: The RevoTask Flask REST API specified in `.kiro/specs/backend/`.
- **Success_Envelope / Error_Envelope**: The response bodies `{"data": <payload>}` and `{"error": "<message>"}` defined by the backend spec.
- **API_Client**: The typed fetch wrapper in `lib/apiClient.ts`.
- **ApiError**: The error class in `lib/errors.ts` with `statusCode` (number) and `message` (string).
- **Toast_Wrapper**: The module `lib/toast.ts` that wraps `react-hot-toast` `toast.success`, `toast.error` and `toast.loading`.
- **Error_Handler**: The hook in `hooks/useErrorHandler.ts` that maps an ApiError to a toast message.
- **Auth_Context**: The React context in `context/AuthContext.tsx` that holds the Access_Token and the Current_User and exposes `login`, `logout` and `updateUser`.
- **Access_Token**: The JWT returned by `POST /api/auth/login`.
- **Session_Cookie**: The cookie named `revotask_token` that holds the Access_Token so that Server Components can read it.
- **Current_User**: The user `{id, name, email}` that owns the Access_Token.
- **Route_Guard**: The file `middleware.ts` that redirects requests to protected paths.
- **Protected_Path**: Every path except `/login`, `/register`, static assets and Next.js internals.
- **Header**: The component `components/Header.tsx` shown on every Protected_Path page. It holds the navigation, the Notification_Bell and the logout button.
- **Base_Button, Base_Badge, Base_Modal**: The shared components `components/shared/BaseButton.tsx`, `BaseBadge.tsx` and `BaseModal.tsx`.
- **Card_Detail_Modal**: The Client Component `components/CardDetailModal.tsx`.
- **Comment_List**: The Client Component `components/CommentList.tsx`.
- **Board_View**: The Client Component `components/BoardView.tsx` that holds the local React state of one board and renders the Kanban layout.
- **Drag_Hook**: The hook in `hooks/useDragAndDrop.ts`.
- **Order_Helper**: The pure function module `lib/order.ts` that computes the FLOAT order midpoint.
- **Notification_Hook**: The hook in `hooks/useNotifications.ts`.
- **Notification_Bell**: The component `components/NotificationBell.tsx`.
- **Board_Admin / Board_Member**: A Current_User whose `role` on a board is `admin` / any role, as returned by the API in the board `role` field.
- **Kanban_Journey**: The 8-step end-to-end scenario defined in Requirement 26.
- **E2E_Suite**: The Playwright tests in `e2e/` that run against the deployed Vercel URL.
- **Component_Tests**: The React Testing Library tests run by `npm test`.
- **Page and component subject names**: A subject such as Login_Page, Register_Page, Dashboard_Page, Board_Page, My_Tasks_Page, Profile_Page, Members_Page, Analytics_Page, Analytics_Panel, Create_Board_Modal, Column_Form_Modal, Card_Form_Modal, Add_Member_Modal, Member_List, Card_Search or Debounce_Hook names the file listed in the `(Page: ...)` or `(File: ...)` tag of its criterion and in the traceability matrix.
- **Viewport_Mobile**: A browser viewport of 375 by 667 CSS pixels.

## Decisions Beyond the Brief

The brief and the backend spec do not settle the points below. This spec fixes them. Rejecting one of them is recorded as a later version.

1. **Token storage.** The Access_Token is held in Auth_Context for Client Components and mirrored in the non-httpOnly Session_Cookie for Server Components. A non-httpOnly cookie is needed because the browser sends the Bearer header itself to a cross-origin API. The trade-off is exposure to script injection. The cookie uses `SameSite=Lax`, `Path=/`, `Secure` on HTTPS and `Max-Age` equal to `expires_in`.
2. **Current_User after a reload.** The root layout reads the Session_Cookie on the server and calls `GET /api/users/me` to restore the Current_User, because the cookie holds only the token.
3. **Base URL.** `NEXT_PUBLIC_API_BASE_URL` and `API_BASE_URL` hold the API origin without a trailing slash and without `/api`. Each request path starts with `/api/`. `API_BASE_URL` falls back to `NEXT_PUBLIC_API_BASE_URL` when unset.
4. **No token refresh.** The API has no refresh route. An expired token (HTTP 401) ends the session and redirects to `/login`.
5. **Registration signs in.** `POST /api/auth/register` returns 201 with `{id, name, email, created_at}` and no token, and `POST /api/auth/login` returns the token. After a 201 from register, the Register_Page therefore sends one `POST /api/auth/login` with the same trimmed `email` and the same `password`, calls `login` from Auth_Context with the result and redirects to `/`. If the auto-login request fails, the Register_Page shows the success toast "Account created. Please log in." through Toast_Wrapper and redirects to `/login`, because the account exists and the user must not be told that registration failed. This replaces the V1 decision "Registration does not sign in" (see `CHANGELOG.md`, V2). The redirect of Requirement 4, criterion 7 and the redirect of the Register_Page after `login` both lead to `/`.
6. **Modal scope.** Base_Modal wraps every form that opens on demand (create board, create and edit card, column forms, add member, delete confirmations, and the comment forms inside Card_Detail_Modal). The full-page forms on `/login`, `/register` and `/profile` stay page-level forms.
7. **Search scope.** `GET /api/cards?search=` returns cards from all of the user's boards, without a board id. The board page therefore shows only the cards of the open board whose `id` is in the result.
8. **Keyboard and touch alternative to dragging.** Native HTML5 drag-and-drop works neither with a keyboard nor on touch screens. Card_Detail_Modal therefore offers a "Column" select that moves the card to the end of the chosen column through the same Drag_Hook move function.
9. **Admin pages.** Board members live at `/boards/[id]/members` and analytics at `/boards/[id]/analytics`, both linked from the board header. Analytics is a page, not a panel. The charts are plain CSS bars, with no chart library.
10. **Column reorder.** Columns are reordered by dragging the column header with the same Drag_Hook, using `PATCH /api/boards/<id>/columns/reorder`.
11. **Notification count.** The API returns no unread total, so the Notification_Hook requests `per_page=100` and counts the unread items of that page.
12. **My Tasks rendering.** `/my-tasks` is a Server Component, like Dashboard and Board Detail.
13. **Test runner.** `npm test` runs Component_Tests. The runner (Jest or Vitest) is left to `design.md`.
14. **E2E data.** The E2E_Suite registers a fresh user with a unique email for each run, so that no credentials are stored. The report folder `playwright-report/` is not git-ignored so that a generated report can be committed.
15. **Network failures.** A fetch that fails before a response arrives throws an ApiError with `statusCode` 0.
16. **Route Guard file name.** The file is named `middleware.ts`. `design.md` may use `proxy.ts` if the installed Next.js major version requires it.

17. **Detailing choices.** The board, column, card and member names are trimmed before validation. The My Tasks page shows an Open board button on each card and the badges Completed and Open. A card dropped on a column is placed by the vertical midpoint of the cards. A 401 during notification polling logs the user out and stops polling. The members and analytics pages render the not-found page on 404 and a message on 403. A mobile E2E scenario checks that no page scrolls sideways.

## Requirements

### Requirement 1: Session and token storage

**User Story:** As a user, I want my login to survive a page reload and be readable by server-rendered pages, so that I stay signed in.

#### Acceptance Criteria

1. WHEN the login API call succeeds and `login` is called with an Access_Token, an `expires_in` value in seconds and a user, THE Auth_Context SHALL set the Access_Token and the Current_User in React state and write the Session_Cookie with the Access_Token as its value, `Path=/`, `SameSite=Lax`, `Max-Age` equal to `expires_in`, and no `HttpOnly` attribute. (File: context/AuthContext.tsx, lib/session.ts)
2. WHEN the Auth_Context writes the Session_Cookie and the page is served over HTTPS, THE Auth_Context SHALL include the `Secure` attribute in the Session_Cookie. When the page is served over HTTP, THE Auth_Context SHALL omit it. (File: lib/session.ts)
3. WHEN the root layout renders on the server and the Session_Cookie is present with a non-empty value, THE Frontend SHALL call `GET /api/users/me` with the header `Authorization: Bearer <token>` and pass the token and the returned user to Auth_Context as its initial values. (File: app/layout.tsx, lib/serverSession.ts)
4. WHEN the root layout renders on the server and the Session_Cookie is absent or empty, THE Frontend SHALL send no `GET /api/users/me` request and pass a null token and a null user to Auth_Context. (File: app/layout.tsx, lib/serverSession.ts)
5. IF `GET /api/users/me` fails with status 401 in the root layout, THEN THE Frontend SHALL render the page with a null token and a null user and SHALL NOT throw an error. (File: app/layout.tsx)
6. IF `GET /api/users/me` fails in the root layout with an ApiError whose status is not 401, THEN THE Frontend SHALL let the error propagate so that the error boundary of Requirement 10, criterion 13 renders. (File: app/layout.tsx, app/error.tsx)
7. WHEN `logout` is called, THE Auth_Context SHALL set the token and the user in state to null, delete the Session_Cookie (same `Path=/`, `Max-Age=0`) and then navigate to `/login`. (File: context/AuthContext.tsx)
8. WHEN `updateUser` is called with a user object, THE Auth_Context SHALL replace the Current_User in state with that object and leave the token in state and the Session_Cookie unchanged. (File: context/AuthContext.tsx)
9. THE Frontend SHALL read the Session_Cookie in Server Components only through `lib/serverSession.ts`, and no other module SHALL read the cookie named `revotask_token` on the server. (File: lib/serverSession.ts)

### Requirement 2: Route protection and logout

**User Story:** As a user, I want pages that need a login to send me to the login page, so that my data stays private.

#### Acceptance Criteria

1. IF a request targets a Protected_Path and carries no Session_Cookie, or a Session_Cookie with an empty value, THEN THE Route_Guard SHALL redirect the request to `/login` before any page content of that path is rendered, and SHALL NOT redirect requests to `/login` or `/register`. (File: middleware.ts)
2. WHILE the Session_Cookie is present with a non-empty value, THE Route_Guard SHALL let requests to Protected_Paths proceed without redirecting them. The Route_Guard does not validate the token. (File: middleware.ts)
3. IF a Server Component receives an ApiError with status 401 from the API, THEN THE Frontend SHALL redirect to `/login?reason=session-expired` and render no content of the requested page. (File: lib/serverApi.ts)
4. WHEN the `/login` page loads with the query `reason=session-expired`, THE Login_Page SHALL delete the Session_Cookie and show the exact visible message "Your session has expired. Please log in again." (Page: /login)
5. WHEN a logged-in user clicks the logout button, THE Header SHALL call `logout` from Auth_Context, which clears the token and the Current_User from state, deletes the Session_Cookie and redirects to `/login`, without waiting for any API response. (File: components/Header.tsx)
6. WHEN a browser requests a Protected_Path after `logout` has deleted the Session_Cookie, THE Route_Guard SHALL redirect the request to `/login`. (File: middleware.ts)

### Requirement 3: Registration page

**User Story:** As a visitor, I want to register an account, so that I can sign in.

#### Acceptance Criteria

1. THE Register_Page SHALL render a controlled text input for `name`, a controlled input for `email` and a controlled password input for `password`, each with a visible label, and a Base_Button of variant primary that submits the form. (Page: /register)
2. WHEN the user submits the form, THE Register_Page SHALL validate on the client that `name` has 1 to 255 characters with no trimming, that `email` after trimming leading and trailing whitespace has 3 to 254 characters and is a valid address, and that `password` has 8 to 128 characters with no trimming. A valid address contains exactly one `@`, at least one character before it, a domain after it that contains at least one `.` with a non-empty text on each side, and no whitespace. (Page: /register)
3. IF any field is invalid, THEN THE Register_Page SHALL show one error message next to each invalid field, send no request, keep the entered values in all three fields and keep the submit button enabled. (Page: /register)
4. WHEN all fields are valid, THE Register_Page SHALL send exactly one `POST /api/auth/register` with `name`, `email` after trimming leading and trailing whitespace, and `password`, and SHALL disable the submit button from the moment of submission until the register request has failed or, after status 201, the login request of criterion 5 has finished or failed. (Page: /register)
5. WHEN the register request returns status 201, THE Register_Page SHALL send exactly one `POST /api/auth/login` with the same trimmed `email` and the same `password`, and SHALL NOT read an Access_Token from the register response. (Page: /register)
6. IF the API returns status 409 or 400, THEN THE Register_Page SHALL show the `message` of the ApiError in an inline message next to the form, keep the entered values in all three fields, show no toast and re-enable the submit button. (Page: /register)
7. IF the register request fails with an ApiError other than status 409 or 400, including status 0, THEN THE Register_Page SHALL pass it to Error_Handler, keep the entered values in all three fields and re-enable the submit button. (Page: /register)
8. WHEN the login request of criterion 5 returns status 200, THE Register_Page SHALL call `login` from Auth_Context exactly once with the Access_Token, `expires_in` and `user` of the response, show one success toast through Toast_Wrapper and redirect to `/`. (Page: /register)
9. IF the login request of criterion 5 fails with any ApiError, including status 0 and status 401, THEN THE Register_Page SHALL show exactly one success toast with the exact text "Account created. Please log in." through Toast_Wrapper, call `login` from Auth_Context zero times, redirect to `/login`, keep no form values and pass nothing to Error_Handler. (Page: /register)
10. THE Register_Page SHALL hold the `password` only in its component state while the sequence of criteria 4 to 9 runs, and SHALL NOT write it to the Session_Cookie, to `localStorage`, to `sessionStorage` or to any URL. (Page: /register)

### Requirement 4: Login page

**User Story:** As a registered user, I want to log in, so that I can use my boards.

#### Acceptance Criteria

1. THE Login_Page SHALL render a controlled input `email`, a controlled input `password` that masks its characters, a visible label for each input, a Base_Button of variant primary with `type="submit"` that submits the form, and a link to `/register`. (Page: /login)
2. IF `email` has no non-whitespace character or `password` has 0 characters when the form is submitted, THEN THE Login_Page SHALL show an error message next to each such field, mark the field as invalid as defined in Requirement 22.8, and send no request. (Page: /login)
3. WHEN both fields pass the check of criterion 2 and the form is submitted, THE Login_Page SHALL send one `POST /api/auth/login` with `email` and `password` and SHALL disable the submit button from the moment of submission until the response arrives or the request fails. (Page: /login)
4. WHEN the API returns status 200, THE Login_Page SHALL call `login` from Auth_Context with the Access_Token, `expires_in` and `user` of the response, and then redirect to `/`. (Page: /login)
5. IF the API returns status 401, THEN THE Login_Page SHALL show the `message` of the ApiError above the form, keep the entered `email` in its input, re-enable the submit button, and not pass the error to Error_Handler. (Page: /login)
6. IF an ApiError with a status other than 401 occurs, including `statusCode` 0, THEN THE Login_Page SHALL pass it to Error_Handler, keep the entered `email` in its input and re-enable the submit button. (Page: /login)
7. WHILE the Auth_Context holds a token, THE Login_Page and THE Register_Page SHALL redirect to `/` and SHALL render no form. (Page: /login, /register)

### Requirement 5: API client

**User Story:** As a developer, I want one typed fetch wrapper, so that every call handles the envelope, the token and errors the same way.

#### Acceptance Criteria

1. THE API_Client SHALL read the base URL from `NEXT_PUBLIC_API_BASE_URL` WHEN it runs in a Client Component and from `API_BASE_URL` WHEN it runs in a Server Component, using `NEXT_PUBLIC_API_BASE_URL` for a Server Component only when `API_BASE_URL` is unset. It SHALL remove every trailing `/` character from the value and build each request URL by appending the call's path, which starts with `/api/`, to that value. (File: lib/apiClient.ts)
2. IF the base URL variable for the current runtime is unset, an empty string or only whitespace (after the fallback of criterion 1 for Server Components), THEN THE API_Client SHALL throw an `Error` whose `message` contains the variable name (`NEXT_PUBLIC_API_BASE_URL` in a Client Component, `API_BASE_URL` in a Server Component) and SHALL send no request. (File: lib/apiClient.ts)
3. WHEN a request is sent and a non-empty token is available, THE API_Client SHALL send the header `Authorization: Bearer <token>` with the token unchanged. In Client Components the token comes from Auth_Context, and in Server Components the caller passes the token read by `lib/serverSession.ts`. (File: lib/apiClient.ts)
4. WHEN a request has a body, THE API_Client SHALL serialize it as JSON and send it with the header `Content-Type: application/json`. (File: lib/apiClient.ts)
5. WHEN the API returns a status from 200 to 299 inclusive, THE API_Client SHALL return the `data` field of the Success_Envelope as the generic type argument `T` of the call, without modifying its value. (File: lib/apiClient.ts)
6. IF the API returns a status below 200 or above 299, THEN THE API_Client SHALL throw an ApiError with `statusCode` equal to that status and `message` equal to the `error` field of the Error_Envelope. WHEN the response body is not valid JSON or its `error` field is not a non-empty string, THE API_Client SHALL use the `message` `Request failed with status <status>`, where `<status>` is the decimal status code. (File: lib/apiClient.ts, lib/errors.ts)
7. IF the fetch rejects before any response arrives, THEN THE API_Client SHALL throw an ApiError with `statusCode` 0 and a `message` of at least 1 character. (File: lib/apiClient.ts)
8. WHEN a Server Component calls the API, THE API_Client SHALL send the request with `cache: 'no-store'`. (File: lib/apiClient.ts)
9. THE Frontend SHALL export the TypeScript types of every API response used by the pages (User, Board, Column, Card, Comment, Notification, Member, MyTasksGroup, Analytics) from the single module `lib/types.ts`, and no other module SHALL declare a type for the same response. (File: lib/types.ts)
10. IF no token is available or the token is an empty string, THEN THE API_Client SHALL send the request without an `Authorization` header. (File: lib/apiClient.ts)

### Requirement 6: ApiError and toast wrapper

**User Story:** As a developer, I want one error class and one toast module, so that messages are shown consistently.

#### Acceptance Criteria

1. WHEN an ApiError is constructed with a number `statusCode` and a string `message`, THE ApiError class SHALL return an instance of `Error` whose `statusCode` and `message` fields equal the constructor arguments unchanged, and whose `statusCode` field is declared `readonly` so that an assignment to it fails TypeScript compilation. (File: lib/errors.ts)
2. WHEN an ApiError is thrown in one module and caught in another module, THE ApiError class SHALL satisfy both `error instanceof ApiError` and `error instanceof Error`, and the caught error SHALL keep its original `statusCode` and `message`. (File: lib/errors.ts)
3. WHEN `success`, `error` or `loading` of the Toast_Wrapper is called with a message string, THE Toast_Wrapper SHALL call `toast.success`, `toast.error` or `toast.loading` of `react-hot-toast` respectively, exactly once, with that message, and return the toast id that `react-hot-toast` returns. (File: lib/toast.ts)
4. THE root layout SHALL mount exactly one `Toaster` component from `react-hot-toast` in its rendered output, so that toasts appear on every page. (File: app/layout.tsx)
5. WHEN `dismiss` of the Toast_Wrapper is called with an optional toast id, THE Toast_Wrapper SHALL call `toast.dismiss` of `react-hot-toast` exactly once with the same argument, and a call with no id SHALL dismiss all visible toasts. (File: lib/toast.ts)

### Requirement 7: Error handler hook

**User Story:** As a user, I want clear messages when something fails, so that I know what to do next.

#### Acceptance Criteria

1. WHEN Error_Handler receives an ApiError with `statusCode` 400 or 409, THE Error_Handler SHALL show one error toast whose text equals the `message` of the ApiError. (File: hooks/useErrorHandler.ts)
2. WHEN Error_Handler receives an ApiError with `statusCode` 401, THE Error_Handler SHALL show one error toast with the text "Your session has expired. Please log in again." and then call `logout` from Auth_Context exactly once. (File: hooks/useErrorHandler.ts)
3. WHEN Error_Handler receives an ApiError with `statusCode` 403, THE Error_Handler SHALL show one error toast with the text "You do not have permission to do this." (File: hooks/useErrorHandler.ts)
4. WHEN Error_Handler receives an ApiError with `statusCode` 404, THE Error_Handler SHALL show one error toast with the text "The requested item was not found." (File: hooks/useErrorHandler.ts)
5. WHEN Error_Handler receives an ApiError with `statusCode` 0, THE Error_Handler SHALL show one error toast with the text "Cannot reach the server. Check your connection." (File: hooks/useErrorHandler.ts)
6. WHEN Error_Handler receives an error that is not an ApiError, or an ApiError whose `statusCode` is not 0, 400, 401, 403, 404 or 409 (including every status of 500 or higher), THE Error_Handler SHALL show one error toast with the text "Something went wrong. Please try again." (File: hooks/useErrorHandler.ts)
7. THE Error_Handler SHALL show every toast by calling the `error` function of Toast_Wrapper and SHALL call `toast.error` of `react-hot-toast` in no other way. (File: hooks/useErrorHandler.ts, lib/toast.ts)
8. WHEN Error_Handler receives an error with a `statusCode` other than 401, THE Error_Handler SHALL NOT call `logout`. (File: hooks/useErrorHandler.ts)

### Requirement 8: Shared components

**User Story:** As a developer, I want reusable button, badge and modal components, so that the interface is consistent.

#### Acceptance Criteria

1. THE Base_Button SHALL accept the prop `variant` with the values `primary`, `secondary` and `destructive`, SHALL use `primary` when the prop is omitted, and SHALL render a native `button` element whose Tailwind `class` attribute differs for each of the three variants. (File: components/shared/BaseButton.tsx)
2. WHERE the prop `loading` is true or the prop `disabled` is true, THE Base_Button SHALL set the `disabled` attribute on the rendered `button` element and SHALL NOT call the `onClick` prop when the user clicks it. (File: components/shared/BaseButton.tsx)
3. THE Base_Button SHALL set the `type` attribute to `button` when the `type` prop is omitted, SHALL use the `type` prop value when it is given, and SHALL forward all other native button props to the rendered `button` element. (File: components/shared/BaseButton.tsx)
4. THE Base_Badge SHALL accept the prop `color` with the values `gray`, `blue`, `green`, `yellow` and `red`, SHALL use `gray` when the prop is omitted, and SHALL render its children with a Tailwind `class` attribute that differs for each of the five colors. (File: components/shared/BaseBadge.tsx)
5. WHILE the prop `open` of Base_Modal is true, THE Base_Modal SHALL render an element with `role="dialog"` that contains a heading whose text equals the prop `title` and contains its children, and SHALL render a backdrop element behind the dialog. (File: components/shared/BaseModal.tsx)
6. WHILE the prop `open` is false, THE Base_Modal SHALL render no dialog, no backdrop and no children, so that none of them is present in the DOM. (File: components/shared/BaseModal.tsx)
7. WHEN the user presses the Escape key or clicks the backdrop while the Base_Modal is open, THE Base_Modal SHALL call its `onClose` prop once, and a click on the dialog content SHALL NOT call `onClose`. (File: components/shared/BaseModal.tsx)
8. THE Frontend SHALL render each on-demand form listed in Decision 6 inside a Base_Modal, and SHALL render the forms of `/login`, `/register` and `/profile` as page-level forms outside any Base_Modal. The on-demand forms are the create-board form, the create-card and edit-card forms, the column create and rename forms, the add-member form, the delete confirmations, and the comment forms inside Card_Detail_Modal. (File: components/shared/BaseModal.tsx)
9. THE Frontend SHALL render every button of every page, including `/my-tasks` and `/profile`, with Base_Button, so that no page or component other than Base_Button renders a native `button` element directly. (Page: /my-tasks, /profile)

### Requirement 9: Dashboard and board creation

**User Story:** As a board member, I want to see all my boards and create a new one, so that I can start working.

#### Acceptance Criteria

1. THE Dashboard_Page SHALL be a Server Component that calls `GET /api/boards` with the token from the Session_Cookie and renders one link to `/boards/<id>` for each returned board, in the order returned by the API. Each link shows the board `name` and the `role` value as text in a Base_Badge. (Page: /)
2. WHEN `GET /api/boards` returns an empty list, THE Dashboard_Page SHALL show the text "You have no boards yet" and no board links. (Page: /)
3. THE Dashboard_Page SHALL render the create-board Base_Button whether `GET /api/boards` returns zero boards or one or more, and WHEN the user clicks it, THE Dashboard_Page SHALL open a Base_Modal with a controlled input `name` that has a visible label and a submit Base_Button. (File: components/CreateBoardModal.tsx)
4. IF `name` has no non-whitespace character or has more than 255 characters after trimming leading and trailing whitespace when the form is submitted, THEN THE Create_Board_Modal SHALL show an error message next to the `name` input, keep the modal open with the entered value and send no request. (File: components/CreateBoardModal.tsx)
5. WHEN the user submits a valid `name`, THE Create_Board_Modal SHALL disable the submit button until the response arrives, send `POST /api/boards` with the trimmed `name`, and, when the request succeeds, close the modal, show a success toast through Toast_Wrapper and navigate to `/boards/<id>` of the returned board. (File: components/CreateBoardModal.tsx)
6. IF `POST /api/boards` fails, THEN THE Create_Board_Modal SHALL pass the ApiError to Error_Handler, keep the modal open with the entered `name`, re-enable the submit button and navigate nowhere. (File: components/CreateBoardModal.tsx)
7. IF `GET /api/boards` fails with an ApiError whose status is not 401, THEN THE Dashboard_Page SHALL render the error boundary with a "Try again" Base_Button, as defined in Requirement 10.13. (File: app/error.tsx)
### Requirement 10: Board detail page

**User Story:** As a board member, I want to open a board and see its columns and cards, so that I can see the state of the work.

#### Acceptance Criteria

1. WHEN a user opens `/boards/<id>`, THE Board_Page SHALL, as a Server Component, start `GET /api/boards/<id>` and `GET /api/boards/<id>/members` in parallel with the token from the Session_Cookie. When both succeed, it SHALL pass the board (including its `role`, `columns` and `cards`) and the member list as initial props to Board_View. (Page: /boards/[id])
2. THE Board_View SHALL render the columns of the board side by side in a single horizontal row in `order` ascending. Each column SHALL show its `title`, its card count (the number of cards in that column) and its cards in `order` ascending. (File: components/BoardView.tsx, components/KanbanColumn.tsx)
3. THE Board_View SHALL render each card with its `title`. WHERE `completed_at` is not null, it SHALL also render a Base_Badge of color `green` with the text "Completed". WHERE `assignee_id` is not null, it SHALL also render the `name` of the board member whose `id` equals `assignee_id`. (File: components/CardItem.tsx)
4. IF a column holds 0 cards, THEN THE Board_View SHALL render in that column a drop area labelled "No cards" that accepts a dropped card. (File: components/KanbanColumn.tsx)
5. IF `GET /api/boards/<id>` returns status 404, THEN THE Board_Page SHALL render the Next.js not-found page and SHALL NOT render Board_View. (Page: /boards/[id], File: app/not-found.tsx)
6. IF `GET /api/boards/<id>` returns status 403, THEN THE Board_Page SHALL render the message "You are not a member of this board" and a link to `/`, and SHALL NOT render Board_View. (Page: /boards/[id])
7. WHERE the board `role` of the Current_User is `admin`, THE Board_View SHALL show a Base_Button to rename the board, a Base_Button to delete the board, a link to `/boards/<id>/members` and a link to `/boards/<id>/analytics`. (File: components/BoardHeader.tsx)
8. WHERE the board `role` of the Current_User is `member`, THE Board_View SHALL show a link to `/boards/<id>/members` and SHALL show no rename button, no delete button and no link to `/boards/<id>/analytics`. (File: components/BoardHeader.tsx)
9. WHEN a Board_Admin submits the rename Base_Modal (a controlled input `name` and a submit Base_Button) with a `name` of 1 to 255 characters, THE Board_View SHALL send `PATCH /api/boards/<id>`, replace the displayed board name with the `name` in the response, close the modal and show a success toast through Toast_Wrapper. (File: components/BoardHeader.tsx)
10. IF the rename `name` is empty or longer than 255 characters when the form is submitted, THEN THE Board_View SHALL show an error message next to the input and send no request. (File: components/BoardHeader.tsx)
11. WHEN a Board_Admin confirms the delete in a Base_Modal, THE Board_View SHALL send `DELETE /api/boards/<id>`, show a success toast through Toast_Wrapper and navigate to `/`. (File: components/BoardHeader.tsx)
12. IF `PATCH /api/boards/<id>` or `DELETE /api/boards/<id>` fails, THEN THE Board_View SHALL pass the ApiError to Error_Handler, keep the Base_Modal open and leave the displayed board name and the Board_View state unchanged. (File: components/BoardHeader.tsx)
13. IF a Server Component call of the Board_Page fails with an ApiError whose status is neither 401 (handled by criterion 3 of Requirement 2), 403 nor 404, THEN THE Frontend SHALL render the error boundary with a "Try again" Base_Button that re-renders the page segment when clicked. (File: app/error.tsx)

### Requirement 11: Columns

**User Story:** As a board member, I want to add, rename, delete and reorder columns, so that the board matches my workflow.

#### Acceptance Criteria

1. WHEN the user clicks the add-column button, THE Board_View SHALL open a Base_Modal with a controlled input `title` that is empty and a submit Base_Button. (File: components/ColumnFormModal.tsx)
2. IF `title` has no non-whitespace character or has more than 255 characters when the add-column or rename form is submitted, THEN THE Column_Form_Modal SHALL show an error message next to the `title` input, send no request and keep the modal open. (File: components/ColumnFormModal.tsx)
3. WHEN the user submits a valid `title` in the add-column form, THE Column_Form_Modal SHALL disable the submit button, send `POST /api/boards/<id>/columns` and, on status 201, append the returned column with an empty `cards` list to the Board_View state, render it among the columns in `order` ascending, and close the modal. (File: components/ColumnFormModal.tsx, components/BoardView.tsx)
4. WHEN the user clicks the rename button of a column, THE Board_View SHALL open a Base_Modal with a controlled input `title` pre-filled with the current column title and a submit Base_Button. (File: components/ColumnFormModal.tsx, components/KanbanColumn.tsx)
5. WHEN the user submits a valid new title in the rename form of a column, THE Column_Form_Modal SHALL disable the submit button, send `PATCH /api/columns/<id>`, replace the column title in the Board_View state with the title in the response, leave the cards and `order` of the column unchanged, and close the modal. (File: components/ColumnFormModal.tsx, components/BoardView.tsx)
6. WHEN the user clicks the delete button of a column and confirms in a Base_Modal, THE Board_View SHALL send `DELETE /api/columns/<id>` and, on a successful response, remove the column and all its cards from the Board_View state and close the confirmation modal. (File: components/KanbanColumn.tsx, components/BoardView.tsx)
7. WHEN the user drops a column header at a position that differs from its current position, THE Drag_Hook SHALL compute the new order with Order_Helper, using the `order` values of the other columns and the rules of Requirement 13 criteria 2 to 5 (mean of the two neighbours, half of the first `order`, last `order` plus 1.0), apply the new position to the Board_View state before the response arrives, and send `PATCH /api/boards/<id>/columns/reorder` with `column_id` and `order`. (File: hooks/useDragAndDrop.ts, lib/order.ts)
8. WHEN the column reorder response has `rebalanced` equal to `true`, THE Drag_Hook SHALL replace the `order` of every column in the Board_View state with the value in the response `columns` and sort the columns by `order` ascending. (File: hooks/useDragAndDrop.ts)
9. WHEN a column header is dropped at the position it already has, THE Drag_Hook SHALL change no state and send no request. (File: hooks/useDragAndDrop.ts)
10. IF a column delete request or a column reorder request fails, THEN THE Board_View SHALL pass the ApiError to Error_Handler and restore the Board_View state held before the request, so that the columns and their cards appear in their original positions. (File: components/BoardView.tsx, hooks/useDragAndDrop.ts)
11. IF an add-column or rename request fails, THEN THE Column_Form_Modal SHALL pass the ApiError to Error_Handler, keep the modal open with the entered `title`, re-enable the submit button and leave the Board_View state unchanged. (File: components/ColumnFormModal.tsx)

### Requirement 12: Card create, edit and delete

**User Story:** As a board member, I want to create, edit, complete, assign and delete cards, so that I can track tasks.

#### Acceptance Criteria

1. WHEN the user clicks the add-card button of a column, THE Board_View SHALL open a Base_Modal with an empty controlled input `title`, an empty controlled input `description` and an `assignee` select. The select SHALL list one option per board member, labelled with the member `name`, in the order returned by the API, preceded by an empty option that is selected by default. (File: components/CardFormModal.tsx)
2. IF, when the create form is submitted, `title` has no non-whitespace character or is longer than 255 characters, or `description` is longer than 10,000 characters, THEN THE Card_Form_Modal SHALL show an error message next to each invalid field, send no request and keep the modal open with the entered values. An empty `description` is valid. (File: components/CardFormModal.tsx)
3. WHEN the user submits a valid create form, THE Card_Form_Modal SHALL disable the submit button until the response arrives and send `POST /api/columns/<id>/cards`, where `<id>` is the column whose add-card button opened the modal, with `title`, `description` and `assignee_id` set to the selected member id, or to null when the empty option is selected. (File: components/CardFormModal.tsx)
4. WHEN the user opens a card, THE Card_Detail_Modal SHALL show an edit form with controlled inputs `title`, `description`, `assignee` and a `completed` checkbox. The inputs SHALL be pre-filled with the card values. The `assignee` select SHALL hold the same options as in criterion 1 and the checkbox SHALL be checked when `completed_at` is not null. (File: components/CardDetailModal.tsx)
5. WHEN the user submits a valid edit form with at least one value that differs from the card values, THE Card_Detail_Modal SHALL disable the submit button until the response arrives, send `PATCH /api/cards/<id>` with only the changed fields among `title`, `description`, `assignee_id` and `completed`, and replace the card in the Board_View state with the response. (File: components/CardDetailModal.tsx)
6. WHERE the Current_User is the card creator or a Board_Admin, THE Card_Detail_Modal SHALL show a destructive Base_Button that opens a confirmation Base_Modal. WHEN the user confirms, THE Card_Detail_Modal SHALL send `DELETE /api/cards/<id>`. WHEN the API reports success, THE Card_Detail_Modal SHALL remove the card from the Board_View state and close both modals. WHEN the user cancels, THE Card_Detail_Modal SHALL close the confirmation Base_Modal and send no request. (File: components/CardDetailModal.tsx)
7. WHERE the Current_User is neither the card creator nor a Board_Admin, THE Card_Detail_Modal SHALL render no delete button. (File: components/CardDetailModal.tsx)
8. IF a card create, edit or delete request fails, THEN THE Card_Form_Modal and THE Card_Detail_Modal SHALL pass the ApiError to Error_Handler, keep the modal open with the entered values, re-enable the submit button and leave the Board_View state unchanged. (File: components/CardFormModal.tsx, components/CardDetailModal.tsx)
9. WHEN the create request returns status 201, THE Card_Form_Modal SHALL append the returned card as the last card of the column in the Board_View state, close the modal and show a success toast through Toast_Wrapper. (File: components/CardFormModal.tsx, components/BoardView.tsx)
10. IF, when the edit form is submitted, `title` has no non-whitespace character or is longer than 255 characters, or `description` is longer than 10,000 characters, THEN THE Card_Detail_Modal SHALL show an error message next to each invalid field, send no request and keep the modal open with the entered values. (File: components/CardDetailModal.tsx)
11. WHILE every value of the edit form equals the card values, THE Card_Detail_Modal SHALL disable the edit submit button and send no request. (File: components/CardDetailModal.tsx)

### Requirement 13: Drag and drop of cards

**User Story:** As a board member, I want to drag a card to another place, so that the board shows the state of the work.

#### Acceptance Criteria

1. THE Drag_Hook SHALL use the native HTML5 Drag and Drop API (`draggable`, `dragstart`, `dragover`, `drop`) and no drag-and-drop library. (File: hooks/useDragAndDrop.ts)
2. WHEN a card is dropped on a column at a position between two cards, THE Order_Helper SHALL return `(above + below) / 2`, where `above` and `below` are the `order` values of the two adjacent cards, computed as a floating-point number and not rounded. (File: lib/order.ts)
3. WHEN a card is dropped above the first card of a column, THE Order_Helper SHALL return `first / 2`, where `first` is the `order` of the first card. (File: lib/order.ts)
4. WHEN a card is dropped below the last card of a column, THE Order_Helper SHALL return `last + 1.0`, where `last` is the `order` of the last card. (File: lib/order.ts)
5. WHEN a card is dropped on a column that holds no cards, THE Order_Helper SHALL return exactly 1.0. (File: lib/order.ts)
6. WHEN the dragged card is dropped in its source column, THE Drag_Hook SHALL exclude the dragged card from the list of cards used to find the card above and the card below the drop position. (File: hooks/useDragAndDrop.ts)
7. WHEN a card is dropped at a new position, THE Drag_Hook SHALL update the Board_View state with the target `column_id` and the computed `order` before the API responds, and then send `PATCH /api/cards/<id>/position` with a JSON body holding `column_id` and `order`. (File: hooks/useDragAndDrop.ts)
8. WHEN a card is dropped in its source column between the same two neighbours it already has (or at the same end of the column when it is first or last), THE Drag_Hook SHALL leave the Board_View state unchanged and send no request. (File: hooks/useDragAndDrop.ts)
9. IF `PATCH /api/cards/<id>/position` fails, THEN THE Drag_Hook SHALL restore the Board_View state held before the drop, so that the card returns to its original column and `order`, and SHALL pass the ApiError to Error_Handler. (File: hooks/useDragAndDrop.ts)
10. WHEN the move response has `rebalanced` equal to `true`, THE Drag_Hook SHALL set the `order` of every card of the target column to the `order` in the `siblings` entry with the same `id`, and sort the column by `order` ascending. (File: hooks/useDragAndDrop.ts)
11. WHILE a card is being dragged, THE Board_View SHALL apply a highlight style to the one column under the pointer and to no other column, and SHALL remove the highlight on `drop` and on `dragend`. (File: components/KanbanColumn.tsx)
12. WHEN the page reloads after the move response of a drop has arrived with status 200, THE Board_Page SHALL render the card in the target column at the same position among that column's cards that it had before the reload. (Page: /boards/[id])
13. WHEN the user changes the selection of the "Column" select in Card_Detail_Modal to a column other than the card's current column, THE Card_Detail_Modal SHALL call the move function of Drag_Hook with that column and the position after the last card of that column, so that Order_Helper returns the `order` of the last card plus 1.0, or 1.0 when the column holds no cards. (File: components/CardDetailModal.tsx, hooks/useDragAndDrop.ts)
14. WHEN a card is dropped on a column, THE Drag_Hook SHALL place it before the first card of that column (dragged card excluded) whose vertical midpoint is below the vertical coordinate of the pointer at the drop, and after the last card when no such card exists. (File: hooks/useDragAndDrop.ts)
15. IF a card is dropped outside every column, or the drag is cancelled with Escape, THEN THE Drag_Hook SHALL leave the Board_View state unchanged and send no request. (File: hooks/useDragAndDrop.ts)

### Requirement 14: Card detail and comments

**User Story:** As a board member, I want to read and write comments on a card, so that the team stays aligned.

#### Acceptance Criteria

1. THE Card_Detail_Modal SHALL be a Client Component that renders Comment_List inside a Base_Modal. (File: components/CardDetailModal.tsx, components/CommentList.tsx)
2. WHEN the Card_Detail_Modal opens, THE Comment_List SHALL send `GET /api/cards/<id>/comments` once and render each comment of the response with its `content`, the `author.name` and `created_at` as a date and time in the browser locale, sorted by `created_at` ascending, so that the oldest comment is first. (File: components/CommentList.tsx)
3. WHEN the `GET /api/cards/<id>/comments` response arrives with an empty list, THE Comment_List SHALL show the text "No comments yet". (File: components/CommentList.tsx)
4. THE Comment_List SHALL render a form with a controlled textarea `content` that has a visible label, and a submit Base_Button. (File: components/CommentList.tsx)
5. IF `content` has no non-whitespace character or is longer than 5,000 characters when the create form or the edit form is submitted, THEN THE Comment_List SHALL show an error message next to the textarea, keep the entered text and send no request. (File: components/CommentList.tsx)
6. WHEN the user submits valid `content` in the create form, THE Comment_List SHALL send `POST /api/cards/<id>/comments`, disable the submit button until the response arrives and, on status 201, append the returned comment at the end of the list and clear the textarea. (File: components/CommentList.tsx)
7. WHERE `author.id` of a comment equals the Current_User id, THE Comment_List SHALL show an edit button and a delete button on that comment. (File: components/CommentList.tsx)
8. WHEN the user submits a valid edited `content`, THE Comment_List SHALL send `PATCH /api/comments/<id>`, disable the save button until the response arrives and, on status 200, replace the comment in the list with the response, keep its position, and leave edit mode. (File: components/CommentList.tsx)
9. WHEN the user confirms a comment deletion in the Base_Modal of criterion 13, THE Comment_List SHALL send `DELETE /api/comments/<id>` and, on a successful response, remove that comment from the list and close the Base_Modal. (File: components/CommentList.tsx)
10. WHERE `author.id` of a comment differs from the Current_User id, THE Comment_List SHALL show no edit button and no delete button on that comment, including for a Board_Admin. (File: components/CommentList.tsx)
11. IF a comment request (`GET`, `POST`, `PATCH` or `DELETE`) fails, THEN THE Comment_List SHALL pass the ApiError to Error_Handler, keep the list and the entered text unchanged, and, for a failed `GET`, not show the text "No comments yet". (File: components/CommentList.tsx)
12. WHEN the user clicks the edit button of a comment, THE Comment_List SHALL replace the displayed `content` of that comment with a controlled textarea pre-filled with the current `content`, a save Base_Button and a cancel Base_Button, where cancel restores the displayed `content` and sends no request. (File: components/CommentList.tsx)
13. WHEN the user clicks the delete button of a comment, THE Comment_List SHALL open a Base_Modal that asks for confirmation, with a destructive Base_Button to confirm and a Base_Button to cancel, where cancel closes the Base_Modal and sends no request. (File: components/CommentList.tsx)

### Requirement 15: Card search

**User Story:** As a board member, I want to search cards, so that I can find work quickly.

#### Acceptance Criteria

1. THE Board_View SHALL render a single-line text search input that accepts at most 200 characters and truncates typed or pasted text beyond the 200th character. (File: components/CardSearch.tsx)
2. WHEN 300 milliseconds pass with no change to the search input value and the trimmed term (leading and trailing whitespace removed) is not empty, THE Card_Search SHALL send exactly one `GET /api/cards?search=<term>` request with the trimmed term percent-encoded. (File: components/CardSearch.tsx, hooks/useDebounce.ts)
3. WHEN the user changes the search input value less than 300 milliseconds after the previous change, THE Debounce_Hook SHALL discard the pending value and restart the 300 millisecond interval, so that one request, carrying the last value, is sent for a burst of keystrokes. (File: hooks/useDebounce.ts)
4. WHEN a search response arrives that is not ignored under criterion 7, THE Board_View SHALL show in each column only the cards of the open board whose `id` is in the response, keep all columns displayed, and show as each column's card count the number of cards shown in that column. (File: components/BoardView.tsx)
5. WHEN the debounced term is empty after trimming, THE Card_Search SHALL show all cards of the open board with their unfiltered card counts, send no request, discard any pending request, and ignore the response of any request still in flight. (File: components/CardSearch.tsx)
6. WHEN a search response that is not ignored under criterion 7 contains no `id` of a card of the open board, THE Board_View SHALL show the text "No cards match your search" and a card count of 0 in every column. (File: components/BoardView.tsx)
7. IF a search response arrives after a newer search request was sent, THEN THE Card_Search SHALL ignore the older response and leave the displayed cards and card counts unchanged. (File: components/CardSearch.tsx)
8. IF the search request fails, THEN THE Card_Search SHALL pass the ApiError to Error_Handler, show no inline message, and keep the cards and card counts displayed before the request was sent. (File: components/CardSearch.tsx)

### Requirement 16: My Tasks page

**User Story:** As a board member, I want a list of the cards assigned to me, so that I can see what I have to do.

#### Acceptance Criteria

1. WHEN a user requests `/my-tasks`, THE My_Tasks_Page SHALL, as a Server Component, send one `GET /api/cards?assignee=me` request with the token read through `lib/serverSession.ts` and `cache: 'no-store'`. (Page: /my-tasks)
2. WHEN the response holds one or more groups, THE My_Tasks_Page SHALL render one section for each group, in the order returned by the API and without re-sorting. Each section SHALL have a heading whose text equals `board_name`. Two groups with different `board_id` and the same `board_name` SHALL render as two separate sections. (Page: /my-tasks)
3. THE My_Tasks_Page SHALL render inside each section one item for each card of the group's `cards`, in the order returned by the API, showing the card `title`. (Page: /my-tasks)
4. THE My_Tasks_Page SHALL render on each card item a Base_Badge. WHEN `completed_at` is not null, the badge SHALL have color `green` and the text "Completed". WHEN `completed_at` is null, the badge SHALL have color `gray` and the text "Open". (Page: /my-tasks)
5. THE My_Tasks_Page SHALL render on each card item a Base_Button of variant secondary with the label "Open board" that links to `/boards/<board_id>`, where `board_id` is the `board_id` of the card's group. (Page: /my-tasks)
6. WHEN the response is an empty list, THE My_Tasks_Page SHALL show the text "No cards are assigned to you" and render no section. (Page: /my-tasks)
7. IF the request fails with an ApiError whose status is not 401, THEN THE My_Tasks_Page SHALL render the error boundary of Requirement 10 criterion 13 and render no section. (Page: /my-tasks, File: app/error.tsx)
### Requirement 17: Profile page

**User Story:** As a user, I want to update my name and email, so that my profile stays correct.

#### Acceptance Criteria

1. THE Profile_Page SHALL render controlled inputs `name` and `email`, each with a visible label and pre-populated from the Current_User of Auth_Context, and a Base_Button of variant primary that submits the form. (Page: /profile)
2. IF `name` has 0 characters or more than 255 characters, or `email` is not a valid address of 3 to 254 characters after trimming, when the form is submitted, THEN THE Profile_Page SHALL show an error message next to each invalid field, send no request, and keep the entered values and the Current_User unchanged. (Page: /profile)
3. WHILE the trimmed `email` and the `name` both equal the corresponding values of the Current_User, THE Profile_Page SHALL disable the submit button. (Page: /profile)
4. WHEN the user submits valid values that differ from the Current_User in at least one field, THE Profile_Page SHALL send `PATCH /api/users/me` containing only the changed fields, with `email` trimmed, and disable the submit button until the response arrives. (Page: /profile)
5. WHEN the API returns status 200, THE Profile_Page SHALL call `updateUser` from Auth_Context with the returned user, show a success toast through Toast_Wrapper, and disable the submit button because the fields now equal the updated Current_User. (Page: /profile)
6. IF the API returns status 409, THEN THE Profile_Page SHALL show the `message` of the ApiError next to the `email` field, keep the entered values, keep the Current_User unchanged, and re-enable the submit button. (Page: /profile)
7. IF any other ApiError occurs, THEN THE Profile_Page SHALL pass it to Error_Handler, keep the entered values, keep the Current_User unchanged, and re-enable the submit button. (Page: /profile)

### Requirement 18: Notifications

**User Story:** As a user, I want a notification bell with an unread count, so that I notice changes on my boards.

#### Acceptance Criteria

1. WHILE the Auth_Context holds a token, THE Notification_Hook SHALL send `GET /api/notifications?per_page=100` once on mount and then every 30 seconds (30,000 milliseconds), and replace the `items` in its state with the `items` of each successful response. (File: hooks/useNotifications.ts)
2. WHEN the Auth_Context token becomes null or the component unmounts, THE Notification_Hook SHALL clear the polling timer and send no further `GET /api/notifications` request. (File: hooks/useNotifications.ts)
3. THE Notification_Hook SHALL expose `items`, `unreadCount`, `markAsRead(id)` and `refresh()`, where `unreadCount` is the number of items in `items` with `is_read` equal to false (at most 100, see Decision 11), and `refresh()` sends one `GET /api/notifications?per_page=100` immediately and replaces `items` with the response. (File: hooks/useNotifications.ts)
4. THE Notification_Bell SHALL show `unreadCount` in a Base_Badge of color `red` as the number itself when `unreadCount` is 1 to 99, as "99+" when `unreadCount` is above 99, and SHALL render no badge when `unreadCount` is 0. (File: components/NotificationBell.tsx)
5. WHEN the user clicks the Notification_Bell, THE Notification_Bell SHALL open a list of the notifications ordered by `created_at` descending, each showing its `message`, its `created_at` and, only when `is_read` is false, an unread marker. (File: components/NotificationBell.tsx)
6. WHEN the user clicks a notification with `is_read` equal to false, THE Notification_Hook SHALL set `is_read` to true in its state before the API responds, send `PATCH /api/notifications/<id>/read`, and navigate to `/boards/<board_id>` of that notification. (File: hooks/useNotifications.ts, components/NotificationBell.tsx)
7. IF `PATCH /api/notifications/<id>/read` fails, THEN THE Notification_Hook SHALL set `is_read` of that notification back to false in its state, pass the ApiError to Error_Handler, and leave the navigation already started unchanged. (File: hooks/useNotifications.ts)
8. IF a polling request fails with any ApiError whose status is not 401 (including status 0), THEN THE Notification_Hook SHALL keep the previous `items`, show no toast and continue polling on the next 30-second tick. (File: hooks/useNotifications.ts)
9. WHEN the user opens the list and `items` is empty, THE Notification_Bell SHALL show the text "No notifications". (File: components/NotificationBell.tsx)
10. THE Header SHALL render the Notification_Bell, with an `aria-label`, on every Protected_Path page. (File: components/Header.tsx)
11. IF a polling request fails with status 401, THEN THE Notification_Hook SHALL pass the ApiError to Error_Handler and send no further polling request. (File: hooks/useNotifications.ts)

### Requirement 19: Board members

**User Story:** As a board administrator, I want to manage member access, so that I control who can use the board.

#### Acceptance Criteria

1. THE Members_Page SHALL be a Server Component that calls `GET /api/boards/<id>/members` with the token from the Session_Cookie and renders one row per returned member, in the order returned by the API, with `name`, `email`, a Base_Badge showing the `role`, and the date of joining taken from `created_at`. (Page: /boards/[id]/members)
2. WHERE the Current_User is a Board_Admin, THE Members_Page SHALL show an add-member Base_Button that opens a Base_Modal with a controlled input `email` (maximum 254 characters), a `role` select with the options `member` and `admin` and the default `member`, and a submit Base_Button. (File: components/AddMemberModal.tsx)
3. IF `email` is empty or is not a valid address of 3 to 254 characters after trimming when the add-member form is submitted, THEN THE Add_Member_Modal SHALL show an error message next to the `email` input, send no request and keep the modal open. (File: components/AddMemberModal.tsx)
4. WHEN the user submits a valid add-member form, THE Add_Member_Modal SHALL send `POST /api/boards/<id>/members` with the trimmed `email` and the selected `role`, disable the submit button until the response arrives, and on status 201 append the returned member to the Member_List, close the modal and show a success toast through Toast_Wrapper. (File: components/AddMemberModal.tsx)
5. WHERE the Current_User is a Board_Admin, THE Member_List SHALL show on every member row a role select with the options `member` and `admin`, preselected with the current `role`, and a remove button. (File: components/MemberList.tsx)
6. WHERE the Current_User has role `member`, THE Member_List SHALL show a "Leave board" button only on the row of the Current_User, and SHALL show no role select, no remove button and no add-member button. (File: components/MemberList.tsx)
7. WHEN the Current_User confirms the removal of the own membership in a Base_Modal, whether through the "Leave board" button or the remove button, THE Member_List SHALL send `DELETE /api/boards/<id>/members/<user_id>` and, on status 200, navigate to `/`. (File: components/MemberList.tsx)
8. IF a member request fails with an ApiError, THEN THE Member_List and THE Add_Member_Modal SHALL pass the ApiError to Error_Handler, so that the `message` of a 400 or 409 (duplicate member, last administrator) is shown in a toast, leave the Member_List unchanged, reset a changed role select to the previous `role`, and keep the Add_Member_Modal open with the entered values. (File: components/MemberList.tsx, components/AddMemberModal.tsx)
9. WHEN a Board_Admin changes the role select of a member row, THE Member_List SHALL send `PATCH /api/boards/<id>/members/<user_id>` with the selected `role`, and on status 200 replace the `role` of that member in the list with the value in the response. (File: components/MemberList.tsx)
10. WHEN a Board_Admin confirms the removal of another member in a Base_Modal, THE Member_List SHALL send `DELETE /api/boards/<id>/members/<user_id>`, and on status 200 remove that member row from the list. (File: components/MemberList.tsx)
11. IF `GET /api/boards/<id>/members` returns status 404, THEN THE Members_Page SHALL render the Next.js not-found page. IF it returns status 403, THEN THE Members_Page SHALL render the message "You are not a member of this board" and a link to `/`. (Page: /boards/[id]/members, File: app/not-found.tsx)

### Requirement 20: Board analytics

**User Story:** As a board administrator, I want per-board analytics, so that I can monitor progress and team activity.

#### Acceptance Criteria

1. WHEN a request for `/boards/<id>/analytics` is rendered, THE Analytics_Page SHALL, as a Server Component, call `GET /api/boards/<id>/analytics` once with the token from the Session_Cookie and pass the `cards_per_column`, `completed_this_week` and `member_activity` values of the response to Analytics_Panel. (Page: /boards/[id]/analytics)
2. WHEN the response holds one or more items in `cards_per_column`, THE Analytics_Panel SHALL render one horizontal CSS bar per item, in the order returned by the API, showing the column `title` and the integer `card_count` as text, with the bar width equal to `card_count` divided by the largest `card_count` of the list, expressed as a percentage. The largest bar is 100% wide, and every bar is 0% wide when the largest `card_count` is 0. (File: components/AnalyticsPanel.tsx)
3. WHEN the Analytics_Panel renders, THE Analytics_Panel SHALL show `completed_this_week` as a non-negative integer, including 0, next to the label "Completed this week". (File: components/AnalyticsPanel.tsx)
4. WHEN the Analytics_Panel renders, THE Analytics_Panel SHALL show one list entry for each item of `member_activity`, with the member `name` and the integer `actions`, ordered by `actions` descending, and members with equal `actions` SHALL keep the order returned by the API. A member with 0 `actions` is listed with 0. (File: components/AnalyticsPanel.tsx)
5. IF the API returns status 403, THEN THE Analytics_Page SHALL render the text "Analytics are available to board administrators" and a link to `/boards/<id>`, and SHALL render no chart, count or member list. (Page: /boards/[id]/analytics)
6. WHEN `cards_per_column` is an empty list, THE Analytics_Panel SHALL show the text "This board has no columns" in place of the bars, and SHALL still render `completed_this_week` and `member_activity`. (File: components/AnalyticsPanel.tsx)
7. IF the API returns status 404, THEN THE Analytics_Page SHALL render the Next.js not-found page. (Page: /boards/[id]/analytics, File: app/not-found.tsx)

### Requirement 21: Responsive layout (non-functional)

**User Story:** As a user on a phone, I want every page to be usable, so that I can work away from a desk.

#### Acceptance Criteria

1. WHILE the viewport width is from 320 to 1920 CSS pixels, THE Frontend SHALL render every page so that `document.documentElement.scrollWidth` is less than or equal to the viewport width, every button, link and input has a bounding box whose left edge is at or beyond 0 and whose right edge is at or before the viewport width (except the cards and columns inside the Board_View scroll container of criterion 3), and no two controls have overlapping bounding boxes. (Page: all pages)
2. WHILE the viewport width is below 640 CSS pixels, THE Header SHALL hide its navigation links and show a menu Base_Button. (File: components/Header.tsx)
3. THE Board_View SHALL place the columns in one container with horizontal overflow set to scroll, so that the container scrolls sideways and the document width stays less than or equal to the viewport width for any number of columns. (File: components/BoardView.tsx)
4. WHILE the viewport width is below 640 CSS pixels and the Base_Modal is open, THE Base_Modal SHALL render a dialog whose width and height do not exceed the viewport width and height, and SHALL scroll the dialog content vertically inside the dialog when the content is taller than the dialog. (File: components/shared/BaseModal.tsx)
5. THE Frontend SHALL render in the document head the viewport meta tag with the content `width=device-width, initial-scale=1`. (File: app/layout.tsx)
6. THE Frontend SHALL style its components with Tailwind CSS utility classes and SHALL declare no CSS framework other than Tailwind CSS. (File: tailwind.config.ts, app/globals.css)
7. WHEN the user clicks the menu Base_Button of the Header while the viewport width is below 640 CSS pixels, THE Header SHALL show the navigation links if they are hidden and hide them if they are shown. (File: components/Header.tsx)
8. WHILE the viewport width is 640 CSS pixels or more, THE Header SHALL show its navigation links inline and render no menu Base_Button. (File: components/Header.tsx)

### Requirement 22: Accessibility (non-functional)

**User Story:** As a keyboard or screen-reader user, I want dialogs and forms to be operable, so that I can use RevoTask without a mouse.

#### Acceptance Criteria

1. WHILE the Base_Modal is open, THE Base_Modal SHALL render its container with `role="dialog"`, `aria-modal="true"` and `aria-labelledby` set to the `id` of the heading element that renders the `title` prop. (File: components/shared/BaseModal.tsx)
2. WHEN the Base_Modal opens, THE Base_Modal SHALL move the focus, within 100 milliseconds, to the first focusable element inside the dialog in DOM order. A focusable element is a non-disabled, visible `button`, `a[href]`, `input`, `select`, `textarea` or element with `tabindex` of 0 or more. IF the dialog holds no focusable element, THEN THE Base_Modal SHALL move the focus to the dialog container. (File: components/shared/BaseModal.tsx)
3. WHILE the Base_Modal is open, THE Base_Modal SHALL keep the focus inside the dialog, so that Tab on the last focusable element moves the focus to the first and Shift+Tab on the first moves the focus to the last. WHILE a second Base_Modal is open on top of the first (for example a delete confirmation inside Card_Detail_Modal), only the topmost Base_Modal SHALL trap the focus. (File: components/shared/BaseModal.tsx)
4. WHEN the Base_Modal closes, THE Base_Modal SHALL return the focus to the element that had it immediately before the modal opened. IF that element is no longer in the document, THEN THE Base_Modal SHALL move the focus to the `body` element. (File: components/shared/BaseModal.tsx)
5. THE Frontend SHALL associate every form input with a visible `label` element, linked through `htmlFor` and `id` or by wrapping the input. (Page: /login, /register, /profile, File: components/*Modal.tsx)
6. THE Frontend SHALL give every icon-only button, including the Notification_Bell, a non-empty `aria-label` that names its action. (File: components/NotificationBell.tsx, components/Header.tsx)
7. WHEN the card element of a CardItem has the focus and the user presses Enter, THE Board_View SHALL open the Card_Detail_Modal for that card, so that the "Column" select gives keyboard users the move function. Enter pressed while a control nested inside the card has the focus SHALL NOT open the modal. (File: components/CardItem.tsx, components/CardDetailModal.tsx)
8. IF a form input fails validation, THEN THE Frontend SHALL set `aria-invalid="true"` on that input and set `aria-describedby` to the `id` of the element that holds its error message. WHEN the input becomes valid, THE Frontend SHALL remove the error message element and set `aria-invalid` to `"false"` or remove it. (Page: /login, /register, /profile, File: components/*Modal.tsx)
9. THE Board_View SHALL render the card element of every CardItem with `tabindex="0"`, so that each card is reachable with the Tab key. (File: components/CardItem.tsx)

### Requirement 23: Rendering strategy and performance (non-functional)

**User Story:** As a user, I want pages that load fast, so that I can start working quickly.

#### Acceptance Criteria

1. THE Dashboard_Page, THE Board_Page, THE My_Tasks_Page, THE Members_Page and THE Analytics_Page SHALL each be a Server Component whose page file contains no `"use client"` directive and calls no React state or effect hook (`useState`, `useReducer`, `useEffect`, `useLayoutEffect`). (Page: /, /boards/[id], /my-tasks, /boards/[id]/members, /boards/[id]/analytics)
2. THE Frontend SHALL place the `"use client"` directive only in a file that uses at least one of the following: a React state or effect hook, a React context hook, a JSX event-handler prop (such as `onClick` or `onSubmit`), or a browser global (`window`, `document`, `navigator`, `localStorage`). (File: components/*)
3. WHEN a Server Component page needs two or more API responses that do not depend on each other's result, THE Frontend SHALL start all of those requests before awaiting any of them. For the Board_Page these requests are `GET /api/boards/<id>` and `GET /api/boards/<id>/members`. (Page: /boards/[id])
4. THE Frontend SHALL list no chart library, no drag-and-drop library and no state-management library in the `dependencies` or `devDependencies` of `package.json`, and no source file SHALL import such a package. A library of one of these kinds is a package whose main purpose is rendering charts, providing drag-and-drop interaction, or holding shared client state outside React. The built-in React `useState`, `useReducer` and Context APIs are allowed. (File: package.json)

### Requirement 24: Type safety and error-handling consistency (non-functional)

**User Story:** As a developer, I want strict types and one error path, so that defects appear at build time and users see uniform messages.

#### Acceptance Criteria

1. THE Frontend SHALL set `compilerOptions.strict` to `true` in `tsconfig.json` and SHALL NOT set any individual strict-family option (such as `strictNullChecks` or `noImplicitAny`) to `false`. (File: tsconfig.json)
2. THE Frontend SHALL configure ESLint with rules that forbid the explicit `any` type and the `@ts-ignore` comment, each at level `error`, and WHEN `npm run lint` runs, THE Frontend SHALL exit with code 0 and report zero error-level diagnostics for every `.ts` and `.tsx` file in `frontend/` outside `node_modules/` and `.next/`. (File: eslint.config.mjs, package.json)
3. WHEN `npm run build` runs, THE Frontend SHALL exit with code 0, report zero TypeScript errors and report zero error-level ESLint diagnostics. (File: package.json)
4. THE Frontend SHALL present a failure of an API call to the user only through Error_Handler, or through one of these inline outcomes defined in this document: the field or form messages of criteria 3.3, 3.6, 3.9, 4.2, 4.5, 17.2 and 17.6; the page states of criteria 2.3, 10.5, 10.6, 10.13, 19.11, 20.5 and 20.7; or the silent keep-previous-items rule of criterion 18.8. (File: hooks/useErrorHandler.ts, lib/toast.ts)
5. THE Frontend SHALL call `toast.error` of `react-hot-toast` only inside `lib/toast.ts`, and SHALL NOT call `alert` or `console.error` in any code path that handles an ApiError. (File: lib/toast.ts, hooks/useErrorHandler.ts)

### Requirement 25: Component tests

**User Story:** As a developer, I want automated component tests, so that regressions show before deployment.

#### Acceptance Criteria

1. WHEN `npm test` runs, THE Frontend SHALL execute all Component_Tests with React Testing Library, exit with code 0, and report 0 failed tests and 0 skipped tests. (File: package.json)
2. THE Component_Tests SHALL assert for Base_Button that each of the variants `primary`, `secondary` and `destructive` renders a native `button` with a distinct class set, that the default variant is `primary`, and that the `onClick` handler is not called when `disabled` or `loading` is true. They SHALL assert for Base_Badge that each of the colors `gray`, `blue`, `green`, `yellow` and `red` renders a distinct class set and that the default color is `gray`. They SHALL assert for Base_Modal that `open` true renders an element with `role="dialog"`, the `title` heading and the children, that `open` false renders nothing, that Escape and a backdrop click each call `onClose` exactly once, that Tab on the last focusable element moves the focus to the first and Shift+Tab on the first moves it to the last, and that closing the modal returns the focus to the element that had it before opening. (File: __tests__/shared/)
3. THE Component_Tests SHALL cover the Login_Page and the Register_Page with the API_Client mocked. For Login_Page, an empty `email` or an empty `password` SHALL show an error message next to the empty field and leave the API_Client mock uncalled, and a valid submit SHALL call the mock exactly once. For Register_Page, each of these values SHALL show an error message next to its field and leave the API_Client mock uncalled: a `name` of 0 or 256 characters, an `email` of 2 or 255 characters or without a valid address format, and a `password` of 7 or 129 characters. A valid submit SHALL call the register mock exactly once and then the login mock exactly once, with the trimmed `email` and the `password` of the form, SHALL call the mocked `login` of Auth_Context exactly once, and SHALL redirect to `/` (the mocked router receives the target `/`). The submit button SHALL stay disabled until both mocks have resolved. When the login mock rejects with an ApiError, the Register_Page SHALL call the mocked Toast_Wrapper `success` exactly once with the text "Account created. Please log in.", SHALL redirect to `/login`, SHALL leave `login` of Auth_Context uncalled and SHALL leave the mocked Error_Handler uncalled. (File: __tests__/auth/)
4. THE Component_Tests SHALL assert that Order_Helper returns 1.5 for neighbours with `order` 1.0 and 2.0, 1.0 for a first card with `order` 2.0, 4.0 for a last card with `order` 3.0, and 1.0 for an empty column. They SHALL assert for Drag_Hook, with the API_Client mocked, that the Board_View state shows the card at its new position before the pending PATCH promise resolves, that a rejected PATCH restores the state to a value deeply equal to the state before the drop and calls Error_Handler exactly once, and that a response with `rebalanced` equal to `true` replaces the `order` of every card of the target column with the value in `siblings`. (File: __tests__/hooks/, __tests__/lib/)
5. THE Component_Tests SHALL assert for Notification_Hook, with fake timers and the API_Client mocked, that exactly 1 request is sent on mount, that no further request is sent after advancing 29,999 ms, that exactly 1 further request is sent after advancing to 30,000 ms, and that no request is sent after the token becomes null or after unmount. They SHALL assert that Error_Handler calls the mocked Toast_Wrapper with the message defined in Requirement 7 for each of: status 400, 401, 403, 404, 409, 0, 500, and a thrown error that is not an ApiError. (File: __tests__/hooks/)
6. THE Component_Tests SHALL assert for API_Client, with `fetch` mocked, that a 2xx response returns the `data` field of the Success_Envelope, that the header `Authorization: Bearer <token>` is sent when a token is available and no `Authorization` header is sent otherwise, that a non-2xx response throws an ApiError whose `statusCode` equals the status and whose `message` equals the `error` field (or `Request failed with status <status>` when the body has no `error` string), that a rejected `fetch` throws an ApiError with `statusCode` 0, that the base URL comes from `NEXT_PUBLIC_API_BASE_URL` for Client Components and from `API_BASE_URL` for Server Components with a trailing slash removed, and that an unset variable throws an error whose message names that variable. (File: __tests__/lib/)
7. THE Component_Tests SHALL assert for Comment_List, with the API_Client mocked, that a valid submit appends the returned comment and clears the textarea, that a valid edit replaces the comment with the response, and that the edit and delete buttons are present only on comments whose `author.id` equals the Current_User id and absent on all other comments. They SHALL assert for Card_Search, with fake timers, that no request is sent after 299 ms without typing, that exactly 1 request is sent at 300 ms, and that a burst of keystrokes each less than 300 ms apart produces exactly 1 request. (File: __tests__/components/)
8. THE Component_Tests SHALL use the fake-timer API of the test runner for every assertion that depends on elapsed time, and SHALL contain no real-time sleep, meaning no wait on an unmocked `setTimeout` and no assertion that depends on real elapsed time. (File: __tests__/)

### Requirement 26: End-to-end tests

**User Story:** As a developer, I want end-to-end tests against the deployed site, so that the real flows are verified.

#### Acceptance Criteria

1. WHEN `npm run test:e2e` starts, THE E2E_Suite SHALL run Playwright against the URL in the environment variable `PLAYWRIGHT_BASE_URL`, which points to the Vercel deployment, and SHALL start no local server. (File: playwright.config.ts)
2. THE E2E_Suite SHALL contain four authentication scenarios, each of which ends with a web-first assertion on the page URL path or on a visible element: (a) after the registration of a unique user in the scenario, with no separate login step, the URL path is `/` and the Header logout button is visible; (b) after a login with a wrong password, the URL path stays `/login` and the error message of the ApiError is visible above the form; (c) when a browser context with no Session_Cookie requests `/`, the URL path becomes `/login`; (d) after a click on the logout button, the URL path becomes `/login` and a following request to `/` redirects to `/login` again. (File: e2e/auth.spec.ts)
3. THE E2E_Suite SHALL contain the Kanban_Journey as one test that runs these eight steps in order, each followed by the assertion given here: (1) register a unique user and see the URL path `/` with the Header logout button visible; (2) create a board and see the URL path `/boards/<id>` with the board name visible; (3) add a column "To Do" and see its heading; (4) add a column "Done" and see its heading; (5) create a card in "To Do" and see the card title inside the "To Do" column; (6) open the card, add a comment and see the comment `content` and the `author.name` in the Comment_List; (7) drag the card into "Done" with the Playwright `dragTo` action, wait for the response to `PATCH /api/cards/<id>/position` with `waitForResponse`, and see the card inside the "Done" column; (8) reload the page and see the card inside the "Done" column at the same zero-based index among the cards of that column as before the reload. (File: e2e/kanban.spec.ts)
4. IF a step of the Kanban_Journey fails, THEN THE E2E_Suite SHALL run none of the later steps, mark the test as failed and name the failed step number in the report. (File: e2e/kanban.spec.ts)
5. THE E2E_Suite SHALL contain a mobile scenario at Viewport_Mobile. After the registration of a user in the scenario, which signs the user in, the scenario SHALL check on `/` and on the page of a board created in the scenario that the `scrollWidth` of the document element is less than or equal to its `clientWidth`. (File: e2e/responsive.spec.ts)
6. THE E2E_Suite SHALL contain no call to `waitForTimeout` and no fixed-delay sleep. The E2E_Suite SHALL wait only through Playwright auto-waiting, web-first assertions or `waitForResponse`, with an assertion timeout of 10 seconds and a test timeout of 60 seconds. (File: e2e/, playwright.config.ts)
7. THE E2E_Suite SHALL register its own users, each with an email that contains a millisecond timestamp and a random suffix of at least 8 characters, a name of 1 to 255 characters and a generated password of 8 to 128 characters, and SHALL use no stored credentials. WHEN a scenario needs a registered user, such as scenarios (b) and (d) of criterion 2, the helper SHALL create the user by registering through `/register`, which signs the user in, and WHERE the scenario needs a logged-out state, the helper SHALL then click the Header logout button. (File: e2e/helpers/auth.ts)
8. WHEN `npm run test:e2e` completes, whether the tests pass or fail, THE Playwright config SHALL write the HTML report to `playwright-report/`, and the `.gitignore` SHALL NOT list that folder. (File: playwright.config.ts, .gitignore)
9. IF `PLAYWRIGHT_BASE_URL` is unset or empty when `npm run test:e2e` starts, THEN THE Playwright config SHALL throw an error whose message names `PLAYWRIGHT_BASE_URL` and the E2E_Suite SHALL run no test. (File: playwright.config.ts)

### Requirement 27: Configuration and deployment

**User Story:** As a developer, I want a documented, reproducible deployment, so that the app runs on Vercel against the Railway API.

#### Acceptance Criteria

1. THE Frontend SHALL commit a file `.env.example` that holds the variables `NEXT_PUBLIC_API_BASE_URL`, `API_BASE_URL` and `PLAYWRIGHT_BASE_URL`, each on its own line in the form `NAME=value`. Each value SHALL be non-empty. Each value SHALL be a URL whose host is `localhost` or ends in `example.com`, with no trailing slash and no user-info part. `.env.example` SHALL contain no secret or credential. (File: .env.example)
2. THE repository SHALL track no file named `.env`, `.env.local` or `.env.production` under `frontend/`, so that `git ls-files frontend` lists none of these three names. (File: .gitignore)
3. THE `.gitignore` of the Frontend SHALL contain an ignore entry for each of `.next/`, `node_modules/`, `.env`, `.env.local`, `.env.*.local`, `coverage/` and `test-results/`. No entry SHALL match `.env.example`, so that `git check-ignore .env.example` reports the file as not ignored. (File: .gitignore)
4. THE Frontend SHALL deploy to Vercel with the project root directory set to `frontend`. `NEXT_PUBLIC_API_BASE_URL` and `API_BASE_URL` SHALL be set in the Vercel project to the API origin in the format of Decision 3. `PLAYWRIGHT_BASE_URL` SHALL NOT be required in the Vercel project. (File: README.md)
5. THE README SHALL state that the `CORS_ORIGINS` variable of the backend must list the exact Vercel origin, in the form `https://<host>` with no trailing slash and no path, and the origin `http://localhost:3000`. (File: README.md, .env.example)
6. THE README SHALL state that Server Component requests are server-to-server and need no `CORS_ORIGINS` entry. (File: README.md)
7. THE README SHALL list the commands `npm run dev`, `npm run build`, `npm test` and `npm run test:e2e`, each with a one-sentence description of what it does. (File: README.md)
8. THE `package.json` SHALL define the scripts `dev`, `build`, `start`, `lint`, `test` and `test:e2e`, each with a non-empty command string. The `test` script SHALL run the Component_Tests and the `test:e2e` script SHALL run the E2E_Suite. (File: package.json)

## Page and File Traceability Matrix

| Page / File | Requirements |
| --- | --- |
| `/login` (app/login/page.tsx) | 2.4, 4, 22.5, 22.8, 24.4 |
| `/register` (app/register/page.tsx) | 3, 4.7, 22.5, 22.8, 24.4 |
| `/` Dashboard (app/page.tsx) | 9.1, 9.2, 9.7, 23.1 |
| `components/CreateBoardModal.tsx` | 9.3 to 9.6 |
| `/boards/[id]` (app/boards/[id]/page.tsx) | 10.1, 10.5, 10.6, 10.13, 13.12, 23.1, 23.3 |
| `components/BoardView.tsx`, `KanbanColumn.tsx`, `CardItem.tsx` | 10.2 to 10.4, 11.3, 11.5, 11.8, 13.11, 15.1, 15.4, 15.6, 21.3, 22.7, 22.9 |
| `components/BoardHeader.tsx` | 10.7 to 10.12 |
| `components/ColumnFormModal.tsx` | 11.1 to 11.5, 11.11 |
| `components/CardFormModal.tsx` | 12.1 to 12.3, 12.8, 12.9 |
| `components/CardDetailModal.tsx` | 12.4 to 12.8, 12.10, 12.11, 13.13, 14.1, 22.7 |
| `components/CommentList.tsx` | 14.1 to 14.13 |
| `components/CardSearch.tsx` | 15.1, 15.2, 15.5, 15.7, 15.8 |
| `/my-tasks` (app/my-tasks/page.tsx) | 8.9, 16, 23.1 |
| `/profile` (app/profile/page.tsx) | 8.9, 17, 22.5, 22.8 |
| `/boards/[id]/members` (app/boards/[id]/members/page.tsx) | 19.1, 19.11, 23.1 |
| `components/AddMemberModal.tsx`, `MemberList.tsx` | 19.2 to 19.10 |
| `/boards/[id]/analytics` (app/boards/[id]/analytics/page.tsx) | 20.1, 20.5, 20.7, 23.1 |
| `components/AnalyticsPanel.tsx` | 20.2 to 20.4, 20.6 |
| `components/Header.tsx` | 2.5, 18.10, 21.2, 21.7, 21.8, 22.6 |
| `components/NotificationBell.tsx` | 18.4, 18.5, 18.6, 18.9, 22.6 |
| `components/shared/BaseButton.tsx` | 8.1 to 8.3 |
| `components/shared/BaseBadge.tsx` | 8.4 |
| `components/shared/BaseModal.tsx` | 8.5 to 8.8, 21.4, 22.1 to 22.4 |
| `hooks/useDragAndDrop.ts` | 11.7 to 11.10, 13.1, 13.6 to 13.10, 13.13 to 13.15 |
| `hooks/useNotifications.ts` | 18.1 to 18.3, 18.6 to 18.8, 18.11 |
| `hooks/useErrorHandler.ts` | 7, 24.4 |
| `hooks/useDebounce.ts` | 15.2, 15.3 |
| `lib/apiClient.ts` | 5.1 to 5.8, 5.10 |
| `lib/errors.ts` | 5.6, 6.1, 6.2 |
| `lib/toast.ts` | 6.3, 6.5, 7.7, 24.4, 24.5 |
| `lib/order.ts` | 11.7, 13.2 to 13.5 |
| `lib/types.ts` | 5.9 |
| `lib/session.ts`, `lib/serverSession.ts`, `lib/serverApi.ts` | 1.1 to 1.4, 1.9, 2.3 |
| `context/AuthContext.tsx` | 1.1, 1.7, 1.8 |
| `app/layout.tsx` | 1.3 to 1.6, 6.4, 21.5 |
| `app/error.tsx`, `app/not-found.tsx` | 1.6, 9.7, 10.5, 10.13, 16.7, 19.11, 20.7 |
| `middleware.ts` | 2.1, 2.2, 2.6 |
| `tailwind.config.ts`, `app/globals.css` | 21.6 |
| `tsconfig.json`, `eslint.config.mjs` | 24.1 to 24.3 |
| `__tests__/` | 25 |
| `e2e/`, `playwright.config.ts` | 26 |
| `.env.example`, `.gitignore`, `README.md`, `package.json` | 23.4, 24.2, 24.3, 25.1, 26.8, 27 |
