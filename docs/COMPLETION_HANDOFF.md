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

1. Palak: finish the claimed P-03 evaluation on the approved private FaceForensics++
   c23 corpus. Follow the corrected frozen 70-pair protocol in Issue #7; do not
   re-split the official test set or tune thresholds on it. Publish reviewed
   aggregate metrics, failure coverage, robustness and runtime results only.
2. Team: recruit five real participants and run `evaluation/usability/study.py`
   following `docs/USABILITY_EVALUATION.md`. Anonymous observed records are required.
3. Ayush: review the resulting evidence, run the documented setup on a second machine,
   then close release acceptance. Passing software tests does not complete scientific
   evaluation or certify absence of all errors.

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

Local verification: 96 Python tests and four Node result-rendering tests pass; Ruff
and whitespace checks pass. A fresh server accepted a synthetic no-face image,
verified its source hash, completed the available forensic modules and exported JSON
and PDF successfully. The no-face skip was confirmed in the desktop browser.
One existing Starlette/httpx deprecation warning remains in the test dependencies.

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
