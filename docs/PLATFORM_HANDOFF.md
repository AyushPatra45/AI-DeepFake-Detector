# Platform Foundation Hand-off

## What is implemented

Ayush's platform branch provides:

- content-signature validation for JPEG, PNG, MP4, and MOV uploads;
- streamed file writing with a configurable size limit and SHA-256 hashing;
- sanitised display filenames and application-generated storage paths;
- SQLite-backed queued, processing, partial, completed, and failed job states;
- image dimension verification with Pillow;
- configurable OpenCV video sampling with frame indexes and timestamps;
- isolated analyzer execution through a typed adapter protocol;
- JSON and PDF evidence report exports;
- static access to generated evidence artifacts;
- automated API, storage, ingestion, adapter, media, and report tests.

## Local setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn app.main:app --app-dir backend --reload
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Service and code-version check |
| POST | `/api/v1/analyses` | Upload media and queue analysis |
| GET | `/api/v1/analyses` | List recent jobs |
| GET | `/api/v1/analyses/{job_id}` | Read status, findings, frames, and warnings |
| GET | `/api/v1/analyses/{job_id}/report.json` | Download structured report |
| GET | `/api/v1/analyses/{job_id}/report.pdf` | Download readable report |

## Palak deepfake integration

The `deepfake_detection` adapter is connected. It loads the attributed calibrated
checkpoint, detects and expands the largest face, runs ConvNeXt plus SRM/Bayar FFT
inference, aggregates video scores, and generates face, residual, spectrum, and
Grad-CAM artifacts.

Palak's next work is scientific validation: dataset manifests, identity-disjoint
splits, benchmark reproduction, cross-dataset testing, robustness experiments, and
documented threshold analysis.

## Ayana forensics integration

The `image_forensics` adapter is connected. It generates ELA with measured statistics,
inspects RGB LSB distributions, safely extracts supported marker/length/signature
payloads as inert bytes, and normalises image/video metadata. The frontend presents
these independently from the deepfake probability.

Ayana's next work is validation and usability: test a wider controlled steganography
corpus, document false positives, verify evidence wording with users, and refine the
result views from feedback.

## Result rules

- `status=completed` means the module executed successfully, not that manipulation was
  detected.
- `status=skipped` requires a clear unsupported-condition explanation.
- `status=failed` is isolated; other modules and available evidence remain reportable.
- Every module supplies a meaningful version and its important thresholds/settings.
- Extracted payloads are inert evidence and must never be executed or rendered as
  active HTML.

## Current expected result

With the calibrated checkpoint installed and a detectable face present, supported
images and videos can finish as `completed`. Missing weights, no-face media, or an
unsupported module condition produces `partially_completed` with an explicit warning;
the platform never fabricates a result.
