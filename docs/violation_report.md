# RevoTask Violation Report

<!--
HOW TO USE THIS TEMPLATE (delete this comment block before submitting)

1. Generate code in Kiro WITHOUT the steering files (baseline).
2. Review that code against the steering files. Every time you find code that breaks a guideline, add an entry in section 2.
3. Write a targeted refinement prompt for each violation, apply the fix, and record it.
4. Run the before/after comparison in section 3.
5. Replace every "TODO:" with real content. Before submitting, run:  grep -n "TODO" violation_report.md   (it must return nothing).

Only report violations you actually found in Kiro's output. Do not invent or soften findings. Everything below must be in your own words and backed by evidence (code, command output, or test results).
-->

## 0. Overview

| Item | Value |
|---|---|
| Author | TODO: name |
| Date of review | TODO: YYYY-MM-DD |
| Kiro version / model used | TODO: |
| Steering files reviewed against | `backend.md` v7, `database.md` v3, `frontend.md` v9 (update if the files changed; see the changelogs) |
| Steering location in repo | `.kiro/steering/` |
| Baseline code (generated without steering) | TODO: branch/commit link, e.g. `baseline-no-steering` |
| Code after steering + refinement | TODO: branch/commit link |
| Number of violations reported | TODO: n (minimum 3) |

**Original generation prompt(s)** (paste verbatim, exactly as given to Kiro):

```text
TODO: prompt used for the baseline generation
```

---

## 1. Summary of violations

| ID | Area | Guideline broken | Severity | Fix status | Fix commit |
|---|---|---|---|---|---|
| V-01 | TODO: backend / database / frontend | TODO: e.g. `BE-XX-NN` (`backend.md`) | TODO: High / Medium / Low | TODO: Fixed / Partly fixed | TODO: link |
| V-02 | TODO | TODO | TODO | TODO | TODO |
| V-03 | TODO | TODO | TODO | TODO | TODO |

<!-- Severity guide: High = security hole, data loss, or wrong permissions. Medium = wrong behavior or broken contract. Low = maintainability, naming, or structure. -->

---

## 2. Violation details

<!--
Copy the block below once per violation. Keep the numbering (V-01, V-02, ...). Minimum 3 entries.
Cite the guideline by its ID and file (for example "BE-AZ-04 in backend.md").
If one piece of code breaks several guidelines, list the main one here and put the others under "Also affects".
-->

### V-01: TODO: short title

| Field | Details |
|---|---|
| Guideline broken | TODO: ID and file, e.g. `XX-YYY-NN` (`backend.md`) |
| Rule (short, in your words) | TODO: what the guideline requires |
| Location in generated code | TODO: `path/to/file.py:line` |
| Also affects | TODO: other guideline IDs, or "none" |
| Severity | TODO: High / Medium / Low |
| How I found it | TODO: manual review / grep / test / lint (include the command if any) |

**What Kiro generated** (short excerpt of the real code):

```text
TODO: paste the offending code
```

**Why this violates the guideline:**
TODO: explain the specific mismatch between the code and the rule, and what could go wrong.

**Refinement prompt I wrote** (exact text sent to Kiro):

```text
TODO: targeted prompt that names the guideline ID and the exact change needed
```

**Fix applied** (excerpt of the corrected code or diff):

```text
TODO: paste the corrected code or diff
```

| Field | Details |
|---|---|
| Fix commit | TODO: link |
| Fixed by | TODO: Kiro refinement / my manual edit / both |
| How I verified the fix | TODO: test name, command output, or manual steps |

---

### V-02: TODO: short title

| Field | Details |
|---|---|
| Guideline broken | TODO |
| Rule (short, in your words) | TODO |
| Location in generated code | TODO |
| Also affects | TODO |
| Severity | TODO |
| How I found it | TODO |

**What Kiro generated:**

```text
TODO
```

**Why this violates the guideline:**
TODO

**Refinement prompt I wrote:**

```text
TODO
```

**Fix applied:**

```text
TODO
```

| Field | Details |
|---|---|
| Fix commit | TODO |
| Fixed by | TODO |
| How I verified the fix | TODO |

---

### V-03: TODO: short title

| Field | Details |
|---|---|
| Guideline broken | TODO |
| Rule (short, in your words) | TODO |
| Location in generated code | TODO |
| Also affects | TODO |
| Severity | TODO |
| How I found it | TODO |

**What Kiro generated:**

```text
TODO
```

**Why this violates the guideline:**
TODO

**Refinement prompt I wrote:**

```text
TODO
```

**Fix applied:**

```text
TODO
```

| Field | Details |
|---|---|
| Fix commit | TODO |
| Fixed by | TODO |
| How I verified the fix | TODO |

<!-- Add V-04, V-05, ... below by copying the block. Aim for violations from all three areas (backend, database, frontend) if you find them. -->

---

## 3. Before/after comparison

### 3.1 Setup

<!--
A fair comparison changes only one thing: whether the steering files are loaded.
- Same prompt text, same Kiro version and model, same requirements.
- Run 1 (before): steering files removed from `.kiro/steering/`. Commit the result on its own branch.
- Run 2 (after): steering files present. Commit the result on its own branch.
- Do not hand-edit either result before scoring.
-->

| Item | Before (no steering) | After (with steering) |
|---|---|---|
| Branch / commit | TODO | TODO |
| Steering files loaded | None | `backend.md` v7, `database.md` v3, `frontend.md` v9 |
| Prompt used | TODO: same prompt for both | TODO: same prompt for both |
| Kiro version / model | TODO | TODO |
| Date run | TODO | TODO |

### 3.2 Scoring checklist

<!--
Mark each check Pass or Fail for each run. A feature that is missing counts as Fail.
Use the evidence column for the file path, line, or command output that proves the result.
-->

| # | Guideline | Check | Before | After | Evidence |
|---|---|---|---|---|---|
| 1 | BE-STR-01 | The 8 blueprints each have `routes.py`, `service.py`, and `schema.py` | TODO | TODO | TODO |
| 2 | BE-STR-02 | No `db.session` or query code in any `routes.py` | TODO | TODO | TODO |
| 3 | BE-VAL-02 | Every input schema rejects unknown fields | TODO | TODO | TODO |
| 4 | BE-VAL-03 | `CardPositionSchema` requires a UUID `column_id` and `order` greater than 0 | TODO | TODO | TODO |
| 5 | BE-ERR-01 | All errors use the single `{"error": {"code", "message", "details"}}` shape | TODO | TODO | TODO |
| 6 | BE-ERR-03 | `GET /api/notifications` is paginated with `page` and `per_page`, with a maximum `per_page` | TODO | TODO | TODO |
| 7 | BE-AUTH-01 | Passwords are hashed, and no response includes `password_hash` | TODO | TODO | TODO |
| 8 | BE-AUTH-02 | The JWT has an expiry (`exp`) taken from configuration | TODO | TODO | TODO |
| 9 | BE-AZ-04 | A Member can delete only their own card or column, a column holding another member's card returns 409, and an Admin can delete any | TODO | TODO | TODO |
| 10 | BE-AZ-04 | Comment edit and delete are owner-only, even for an Admin | TODO | TODO | TODO |
| 11 | BE-SVC-01 | Services commit once and roll back on error, and routes never commit | TODO | TODO | TODO |
| 12 | BE-SVC-02 | `GET /api/boards/<id>` loads columns and cards with eager loading (no per-column or per-card queries) | TODO | TODO | TODO |
| 13 | BE-SEC-01 | No hard-coded secrets, values come from the environment, and `.env.example` exists | TODO | TODO | TODO |
| 14 | DB-CNV-03 | Every primary key is a UUID | TODO | TODO | TODO |
| 15 | DB-SCH-01 | The `Card` model has `created_at`, `updated_at`, and `deleted_at` | TODO | TODO | TODO |
| 16 | DB-MEM-01 | Roles are stored per board (`board_members.role`), and `users` has no role column | TODO | TODO | TODO |
| 17 | DB-ORD-01 | Card and column ordering uses `db.Float` with a positive-value CHECK | TODO | TODO | TODO |
| 18 | DB-CAS-01 | Foreign keys declare the `ON DELETE` behavior from the cascade table | TODO | TODO | TODO |
| 19 | DB-IDX-01 | The listed indexes exist (record how many of the 12 rows are present) | TODO | TODO | TODO |
| 20 | FE-STR-03 | Dashboard and Board Detail are Server Components | TODO | TODO | TODO |
| 21 | FE-API-01, FE-API-03 | One `apiClient` makes all backend calls and throws an `ApiError` with `statusCode` and `message` | TODO | TODO | TODO |
| 22 | FE-DND-03 | Drag-and-drop uses native events, updates optimistically, and restores the exact original position on error | TODO | TODO | TODO |
| 23 | FE-NTF-01 | Notifications poll every 30 seconds and clear the interval on unmount | TODO | TODO | TODO |
| 24 | FE-UI-01 | My Tasks and Profile use `BaseButton`, with no raw `<button>` elsewhere | TODO | TODO | TODO |
| 25 | FE-AUTH-01 | The token is not stored in `localStorage` or `sessionStorage` | TODO | TODO | TODO |
| 26 | FE-SEC-01 | No `dangerouslySetInnerHTML` anywhere | TODO | TODO | TODO |
| 27 | FE-UX-03 | No text below 14px (except avatar initials and the notification count), body text and helper messages at 16px, and `BaseBadge` (medium weight) at 14px | TODO | TODO | TODO |

### 3.3 Results

| Measure | Before (no steering) | After (with steering) | Change |
|---|---|---|---|
| Checks passed (of 27) | TODO | TODO | TODO |
| Pass rate | TODO % | TODO % | TODO points |
| Backend checks passed (of 13) | TODO | TODO | TODO |
| Database checks passed (of 6) | TODO | TODO | TODO |
| Frontend checks passed (of 8) | TODO | TODO | TODO |
| Guideline violations found in review | TODO | TODO | TODO |
| Tests generated / tests passing (optional) | TODO | TODO | TODO |

**What improved most, and why:**
TODO: 2 to 4 sentences, naming specific guideline IDs.

**What did not improve, or got worse:**
TODO: be honest; a check that still fails shows a guideline that needs rewording (see section 4).

**Limits of this comparison:**
TODO: e.g. single run per condition, model non-determinism, checks that depend on features the baseline prompt did not mention.

---

## 4. Guideline feedback

<!--
Reviewing real output often shows guidelines that are unclear, too weak, or in conflict. List them here, and record the change in the matching changelog (`backend-changelog.md`, `database-changelog.md`, or `frontend-changelog.md`). If you find none, write "None found" and say how you checked.
-->

| Guideline ID | Problem found | Change made | Changelog entry |
|---|---|---|---|
| TODO | TODO | TODO | TODO |

---

## 5. Submission checklist

- [ ] At least 3 violations are listed in section 2, from real Kiro output.
- [ ] Every violation names the guideline it breaks (ID and file).
- [ ] Every violation records the fix applied, with a commit link and how it was verified.
- [ ] Every violation includes the refinement prompt that was used.
- [ ] The before/after comparison in section 3 is complete, with evidence for each check.
- [ ] No "TODO" remains in this file.
- [ ] `frontend.md`, `backend.md`, and `database.md` are committed in `.kiro/steering/`.
- [ ] Every guideline has a Rule, a Rationale, and a concrete RevoTask example.
- [ ] No contradictions or overlaps found between the three files (or each one is recorded in section 4).

---

## Appendix: Where to look first

<!--
These commands only point at likely trouble spots. A match is not automatically a violation, so open the code and confirm against the guideline before reporting it. Adjust paths to your repo layout.
-->

| Guideline | Command or check |
|---|---|
| BE-STR-01 | `ls app/blueprints/*/` and compare with the required file names |
| BE-STR-02 | `grep -rn "db.session\|\.query\.\|select(" app/blueprints/*/routes.py` |
| BE-VAL-02 | `grep -rn "unknown" app/blueprints/*/schema.py` (look for schemas without `RAISE`) |
| BE-ERR-01 | `grep -rn "jsonify" app/` and check every error response against the shape |
| BE-AUTH-02 | `grep -rn "exp\|JWT_" app/` |
| BE-SEC-01 | `grep -rni "secret\|password" app/ --include=*.py` for hard-coded values |
| DB-CNV-03 | `grep -rn "primary_key" app/models/` and check the column type |
| DB-ORD-01 | `grep -rn "db.Float\|order" app/models/` |
| DB-CAS-01 | `grep -rn "ForeignKey" app/models/` and check each `ondelete` |
| FE-API-01 | `grep -rn "fetch(" app components hooks lib` and look for calls outside `lib/apiClient.ts` |
| FE-AUTH-01 | `grep -rn "localStorage\|sessionStorage" .` (exclude `node_modules`) |
| FE-UI-01 | `grep -rn "<button" app components --include=*.tsx` (anything outside `BaseButton.tsx`) |
| FE-SEC-01 | `grep -rn "dangerouslySetInnerHTML" app components` |
| FE-UX-03 | `grep -rn "text-xs\|text-\[" app components --include=*.tsx` (anything below 14px outside avatars and the notification count) |
