# Team Workboard

This is the single source of truth for active project work. Update this file before
starting a task and again when its state changes. `TEAM_STATUS.md` records broader
milestones; this file prevents two members from editing the same area at the same time.

Last remote audit: 11 September 2026 by Ayush. GitHub contained no Palak- or
Ayana-authored branches or commits at that time. Palak reported local commit `9c285c5`,
which is not shared until its branch is pushed.

## Status values

- `READY`: available for a member to claim.
- `CLAIMED`: owner and branch are recorded; implementation has not started.
- `IN_PROGRESS`: code, experiments, tests, or documentation are being produced.
- `BLOCKED`: progress needs a decision, dependency, dataset, or another hand-off.
- `PR_OPEN`: branch is pushed and a pull request is ready for review.
- `MERGED`: reviewed work is present on `main`.

## Active work

| ID | Task | Owner | Status | Branch | Owned files or area | Updated | PR / evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A-02 | Add retention cleanup and configurable analysis limits | Unassigned | READY | Suggested: `ayush/retention-limits` | `backend/app/config.py`, ingestion/storage cleanup, related tests | 2026-09-05 | Not started |
| P-01 | Reproduce the deepfake baseline on a fixed dataset subset | Palak | IN_PROGRESS | `codex/palak-dataset-evaluation` | `evaluation/`, `.gitignore`, `README.md`, `docs/TEAM_STATUS.md`, `pyproject.toml`; no production deepfake files reported | 2026-09-11 | Local commit `9c285c5`; push pending |
| P-02 | Add deepfake failure and batch-inference tests | Palak | READY | Suggested after P-01: `palak/deepfake-edge-tests` | `backend/tests/test_deepfake.py`; coordinate before changing `backend/app/deepfake/` | 2026-09-05 | Not started |
| Y-01 | Build a controlled clean and LSB-embedded image corpus | Ayana | READY | Suggested: `ayana/stego-validation` | New `evaluation/steganography/`, fixtures, and `docs/FORENSICS_EVALUATION.md` | 2026-09-05 | Not started |
| Y-02 | Evaluate ELA cases and document false positives | Ayana | READY | Suggested after Y-01: `ayana/ela-validation` | Evaluation assets/scripts and `docs/FORENSICS_EVALUATION.md`; coordinate before production ELA edits | 2026-09-05 | Not started |
| Y-03 | Run interface accessibility and usability checks | Ayana | READY | Suggested: `ayana/usability-study` | `frontend/`, new usability notes; coordinate before changing shared API schemas | 2026-09-05 | Not started |

Only one large task per person may be `CLAIMED` or `IN_PROGRESS` at a time.

## Completed and merged work

| Work | Assigned domain | Implemented / committed by | State | Evidence |
| --- | --- | --- | --- | --- |
| Project roadmap and team plan | Shared | Ayush | MERGED | Commit `c85722c` |
| Platform backend foundation | Ayush | Ayush | MERGED | PR #1, commit `49b0b5f` |
| Shared workboard and collision rules | Shared | Ayush | MERGED | Commits `81aa4d0` and `0f34555` |
| ELA, LSB and metadata integration | Ayana domain | Ayush with Codex assistance | MERGED | PR #2, commit `d027194`; Ayana must still review and validate it |
| Dual-stream detector integration | Palak domain | Ayush with Codex assistance | MERGED | PR #2, commit `04119ab`; Palak must still review and validate it |
| Browser forensic workspace | Ayana domain | Ayush with Codex assistance | MERGED | PR #2, commit `49cba6d`; Ayana must still review and validate it |
| Integrated status and follow-up documentation | Shared | Ayush | MERGED | PR #2, commit `eaa5d71` |

Assignment is not authorship. The `Implemented / committed by` column must match the
actual work and Git history.

## Collision-prevention procedure

1. Run `git switch main`, `git pull --ff-only origin main`, and `git fetch --prune`.
2. Read this file and choose one `READY` task assigned to you.
3. Confirm that nobody owns the same files or area in an active row.
4. Change the row to `CLAIMED` and add your intended implementation branch and files.
   Land this coordination-only edit on `main` through the GitHub editor or a tiny claim
   pull request before writing implementation code.
5. Pull the claimed row from `main`, then create the implementation branch recorded in
   the row. Never implement directly on `main`.
6. Change the row to `IN_PROGRESS` in the implementation branch when work begins.
7. Before editing a shared file such as `README.md`, `pyproject.toml`, API schemas, or
   report formats, record it in the row and notify the other owners.
8. Commit in small units and push at least at the end of each work session.
9. When opening a pull request, change the status to `PR_OPEN` and add its link.
10. After merge, move the factual result to the completed table and select the next
    `READY` task.

Do not overwrite another member's branch, force-push shared work, or mark work
`MERGED` before it is present on `origin/main`.

## Daily update format

Add a short entry only when useful; keep the newest entry first.

| Date | Member | Task | Done | Next | Blocker |
| --- | --- | --- | --- | --- | --- |
| 2026-09-11 | Palak | P-01 | Created local baseline-pipeline commit `9c285c5` | Merge current `origin/main`, verify, push the existing branch, and open a pull request | Branch is not yet on GitHub |
| 2026-09-11 | Ayush | A-01 | Merged the workboard into `origin/main` | Palak and Ayana can claim their first validation tasks | None |
| 2026-09-05 | Ayush | A-01 | Audited remote branches and created coordination rules | Open and merge the workboard pull request | None |

## Handoff checklist

- Branch is pushed and visible on GitHub.
- Pull request explains the task ID, changed files, approach, and limitations.
- Tests or experiment commands and their actual results are recorded.
- Generated datasets, uploads, checkpoints, secrets, and large artifacts are not in Git.
- Documentation states what is complete and what remains unvalidated.
- Another teammate can run, review, and explain the work.
