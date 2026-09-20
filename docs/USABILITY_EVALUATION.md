# Interface Accessibility and Usability Evaluation

## Status

The Y-03 engineering audit, keyboard corrections, defensive UI behavior, and
reproducible study tooling are complete. The five-person study remains a human-data
dependency. No participant results are recorded until five real participants conduct
the tasks, so the repository does not make a fabricated usability claim.

## Scope

The evaluation covers:

- Media upload and progress
- Result interpretation
- Visual evidence and video timeline
- Case history and report download
- Keyboard operation
- Responsive presentation
- Accessible names, states and announcements

Only project-generated synthetic media is used. No participant names, private media
or other personal information is collected.

## Baseline accessibility audit

Audit date: 2026-09-19

Environment:

- Local application at `http://127.0.0.1:8000/`
- Chromium-based browser
- Keyboard-only checks
- Source review of `frontend/index.html`, `frontend/app.js` and
  `frontend/styles.css`

| Check | Result | Evidence |
| --- | --- | --- |
| Main navigation is keyboard operable | Pass | Both application views can be opened without a mouse |
| File chooser is keyboard operable | Pass | Enter opens the native file picker |
| Result tabs support arrow-key navigation | Fail | Right Arrow on Overview does not select Visual evidence |
| New results receive keyboard focus | Fail | Results scroll into view but the result heading is not focused |
| Upload area has visible keyboard focus | Fail | The transparent file input has no corresponding focus style |
| Collapsed navigation retains accessible names | Fail | Responsive CSS hides the only non-`aria-hidden` button text |
| Status meaning is conveyed only by colour | Pass | Risk and module states also contain visible text |
| Evidence images have alternative text | Pass | Artifact descriptions populate image alternative text |

The unusual characters displayed by some PowerShell output are not counted as a
browser defect because the browser renders the symbols correctly.

## Implemented corrections

- Added a keyboard skip link and explicit upload requirements.
- Added accessible state and control relationships to application navigation.
- Added complete tab and tab-panel relationships.
- Implemented Left Arrow, Right Arrow, Home, and End behavior for tabs.
- Added visible focus treatment to the upload area and interactive controls.
- Moved focus to view and result headings after context changes.
- Preserved navigation accessible names in collapsed layouts.
- Added live engine, progress, history, and error announcements.
- Added progress-bar value semantics and reduced-motion support.
- Reset stale result content and the active tab before showing each new case.
- Hid report actions when a failed analysis has no reportable result.
- Added client-side type and size checks for chooser and drag-and-drop uploads.
- Added table captions and descriptive names for case and report actions.
- Added persistent wording that model and ELA outputs are indicators, not proof.

## Engineering verification

Verification date: 2026-09-20

| Check | Result | Evidence |
| --- | --- | --- |
| View navigation moves focus | Pass | Live browser check focused each active view heading |
| Result tabs support keyboard navigation | Pass | Right Arrow selected Visual evidence and displayed its panel |
| Result context receives focus | Pass | A reopened synthetic case focused Forensic findings |
| Dynamic state is announced | Pass | Status regions and progress values expose live text and state |
| Failed/new results cannot retain stale findings | Pass | `resetResult` clears summaries, evidence, warnings, frames, and reports |
| Unsupported/oversized drops are rejected early | Pass | Client validation covers type, extension, and the 500 MB limit |
| Automated regression suite | Pass | Accessibility, API, forensic, and evaluation tests pass together |

These checks are engineering evidence, not a substitute for observations from real
participants.

## Five-person usability study

Participants will be identified only as P1 through P5.

Each participant will be asked to:

1. Upload the supplied synthetic image and start analysis.
2. Explain the result or why a probability is unavailable.
3. Open Visual evidence and describe what it does and does not prove.
4. Open Case history and return to the analysed case.
5. Download a JSON or PDF report.

### Post-task questionnaire

After completing the five tasks, ask each participant:

1. Rate the ease of uploading and starting analysis from 1 (very difficult) to
   5 (very easy).
2. Rate the clarity of the result summary from 1 (very unclear) to 5 (very clear).
3. Rate the clarity of the visual-evidence limitations from 1 to 5.
4. What was the most confusing part?
5. What single change would most improve the interface?

Record only the answers and participant identifier. Do not record names or other
personal information.

Create the anonymous study record with:

```powershell
python evaluation/usability/study.py init evaluation/usability/generated/study.json
```

After entering only the task statuses, three ratings, and two short comments for P1
through P5, validate and summarize it with:

```powershell
python evaluation/usability/study.py summarize evaluation/usability/generated/study.json `
  --output evaluation/usability/generated/summary.json
```

The validator accepts task outcomes `success`, `assisted`, `failed`, or `not_run`.
It rejects unexpected participant fields to discourage storing names or other personal
data. A summary is marked `publishable: true` only when all five task sets and rating
sets are complete. Generated study records are excluded from Git.

| Participant | Upload | Interpret result | Visual evidence | History | Report | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| P1 | Pending | Pending | Pending | Pending | Pending | |
| P2 | Pending | Pending | Pending | Pending | Pending | |
| P3 | Pending | Pending | Pending | Pending | Pending | |
| P4 | Pending | Pending | Pending | Pending | Pending | |
| P5 | Pending | Pending | Pending | Pending | Pending | |

## Limitations

The audit is not an accessibility conformance certification. The five-person study
is a small formative study and must not be presented as population-level evidence.
Automated checks cannot establish whether users understand the forensic limitations;
that question requires the pending observed study.
