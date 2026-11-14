# Completion handoff - 24 September 2026

## Implemented in codex/forensics-completion-fixes

Implemented by Ayush with Codex assistance. These changes are not attributed to
Palak or Ayana and are not marked merged until reviewed on GitHub.

- Preserve face-model percentages when no origin marker is detected.
- Show ELA measurements, LSB extraction, and origin evidence independently.
- Treat failed/missing checks as not evaluated, rather than negative detections.
- Distinguish editable AI-origin text from the visible-watermark candidate signal.
  Generic copyright-watermark text no longer implies an AI origin.
- Bound watermark inspection to 12 uniformly selected samples with a 1280-pixel
  maximum edge. Bounding boxes refer to the resized evidence image.
- Serialize access to the shared deepfake model so concurrent Grad-CAM hooks and
  gradients cannot mix between jobs.
- Recompute SHA-256 before media inspection and fail changed evidence explicitly.
- Include module versions, settings, timings and score interpretation in PDF reports.
- Provide a launcher that retains its bound socket and selects a free local port.
- Add regression coverage for modified evidence, copied metadata, bounded watermark
  sampling and frontend score/failure behavior.

## What remains and who does it

November 14 follow-up: capped video analysis now samples across the full duration
rather than only the beginning. Frame counts remain bounded and timestamps are
estimated from frame index and nominal FPS. The model and its threshold are
unchanged, so wider coverage is not a measured accuracy improvement. Optional
diagnostic failures no longer discard model scores. The workspace now previews
selected media, exposes metadata, and can search and filter its 100 most recent cases.

Ayush owns the remaining execution. Palak and Ayana retain credit for the
benchmark and forensic evaluation tooling they implemented.

1. **P-03:** Obtain authorized access to the private frozen `catalog.csv` and its
   corresponding frame directory, or obtain existing aggregate run outputs for
   review. Follow [the approved protocol](MODEL_EVALUATION.md) without changing the
   split or tuning on it. The local checkpoint already matches the pinned digest.
   Keep private media, catalogs and per-sample results outside Git.
2. **Y-03H:** Recruit five participants and record actual observations in the
   ignored `evaluation/usability/generated/study.json`. Follow
   [the study protocol](USABILITY_EVALUATION.md) and publish only aggregate results.
3. **Second-machine check:** On a separate machine, clone the release branch into
   a fresh directory, follow the README setup, and run the tests. Start the app,
   upload the generated LSB control, and open its JSON and PDF reports. Record
   OS, Python version, commit, test outcome, and upload/export outcome.
   GitHub CI is separate evidence, not a second-machine app walkthrough.

Handoff branch verification: 107 Python tests, seven frontend tests, and Ruff
passed. The study record is blank; no benchmark or participant outcome is claimed.

## Detection boundary

The installed model detects face-manipulation patterns. It does not classify every
synthetic scene or every generator. ELA measures JPEG recompression differences;
LSB inspects supported payload layouts. Neither is an AI probability. Missing faces,
watermarks, or payloads do not establish that media is real.

Visible logos can be copied. The sparkle detector is a heuristic and has no measured
real-world false-positive rate. File-byte provenance leads are not signature-verified.
Universal full-image generation detection and verified C2PA/SynthID are not completed
capabilities of this prototype.

## Run and verify

Local verification: 100 Python tests and seven Node frontend tests pass; Ruff
and whitespace checks pass. A fresh server accepted a synthetic no-face image,
verified its source hash, completed the available forensic modules and exported JSON
and PDF successfully. The no-face skip was confirmed in the desktop browser.
One existing Starlette/httpx deprecation warning remains in the test dependencies.

The local suite includes capped video sampling, preservation of scores after a
diagnostic failure, and exact recovery for the documented known-seed LSB format.
See `docs/FORENSICS_EVALUATION.md` for the offline recovery command. The default
web scan does not recover arbitrary keyed layouts. A fresh external-directory
corpus run passed all 16 expectations; the recovered keyed fixture matched its
recorded SHA-256.

From the repository, with the environment activated:

```bash
python scripts/run_local.py
python -m pytest
python -m ruff check backend evaluation scripts
node --test frontend/results.test.cjs
```

Use the URL printed by the launcher. Existing stored reports are historical evidence;
submit the source again to apply updated backend analysis. Refreshing the browser
updates presentation but does not rerun old jobs.
