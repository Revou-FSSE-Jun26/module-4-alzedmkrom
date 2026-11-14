# AI Workflow Summary (draft template)

Fill this in as you work. Replace every `TODO` and every italic hint. When finished, copy the result into the "AI Workflow Summary" section of `README.md` and delete the hints. Only write what you actually did.

---

## AI Workflow Summary

### 1. Project brief

*Where does the brief live (README or /specs)? What did you write yourself versus take from the course brief?*

- Location: TODO
- Overview, user roles (board member, board administrator), core features, tech stack: TODO
- Non-functional requirements included (at least 2): TODO
- What I changed or added to the course brief: TODO

### 2. Specification generation and iteration with Kiro

*Describe the path from idea to tasks, and how you improved each AI-generated document.*

- Specs are split by layer: `database`, `backend`, `frontend` (link each folder).
- Workflow per spec: requirements, then design, then tasks. Requirements went through automatic detailing, then a requirements analysis pass.
- Example of a refinement round (real before and after):
  - Before: TODO (for example, requirement 11.6 had one criterion for connection timeout)
  - Prompt or answer I gave: TODO
  - After: TODO (for example, split into retry criterion 6 and error criterion 7)
- Where the full history is recorded: `CHANGELOG.md` in each spec folder (V1, V2, ...).
- Things I rejected or corrected in AI output: TODO

### 3. Steering guidelines

*Say which files exist, when you wrote them, and how they are applied.*

- Workspace steering files: `tool-usage.md`, `change-management.md` (TODO: add others).
- Project guidelines in `/guidelines`: `frontend.md`, `backend.md`, `database.md`. Each rule has a Rule, a Rationale and a RevoTask Example.
- Written before code generation: TODO (yes or no, with dates or commit links)
- How I checked the three files do not overlap or contradict each other: TODO
- Before and after comparison of AI output with and without the guidelines: TODO (link)

### 4. Code generation and review

*Explain how generated code was checked against the guidelines before commit.*

- How I ran tasks (one task at a time, or queued): TODO
- My review checklist (guideline by guideline): TODO
- Example of code I changed after review: TODO (file, what was wrong, what I changed)
- Tests I ran after each task: TODO

### 5. Violations found and resolved

*At least 3 violations are required. Keep the full list in the violation report and link it here.*

| # | Generated code (file) | Guideline broken | Fix applied |
|---|-----------------------|------------------|-------------|
| 1 | TODO | TODO | TODO |
| 2 | TODO | TODO | TODO |
| 3 | TODO | TODO | TODO |

Full report: TODO (link)

### 6. Kiro CLI for tests and documentation

*Say what the CLI produced and what you refined by hand or by re-prompting.*

- Tests generated with the CLI (pytest, React Testing Library, Playwright): TODO
- Documentation generated with the CLI: TODO
- A prompt I had to refine, and why: TODO
- Things I fixed manually: TODO

---

## Running notes (private, delete before copying to README)

Add one line per event so you do not rely on memory later.

| Date | Phase | What happened | Evidence (file or commit) |
|------|-------|---------------|---------------------------|
| 2026-11-14 | Specs | Database requirements, design and tasks generated. Analysis changed 11.6 into 11.6 and 11.7. | `.kiro/specs/database/CHANGELOG.md` |
| 2026-11-14 | Steering | Added `change-management.md` after the specs existed, then created `CHANGELOG.md`. | `.kiro/steering/change-management.md` |
| | | | |