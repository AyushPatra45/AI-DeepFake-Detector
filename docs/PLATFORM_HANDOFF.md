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

## How Palak connects the deepfake module

1. Create a class with `name = "deepfake_detection"`.
2. Implement `analyse(context: AnalysisContext) -> ModuleResult`.
3. Read `context.source_path` for images or `context.frames` for sampled video frames.
4. Return model version, settings, calibrated findings, warnings, and artifact paths.
5. Register the class in `default_analyzers()` after its tests pass.

Frame probabilities can be added to copies of `context.frames` in a later aggregation
adapter. Do not overwrite source files or sampled evidence frames.

## How Ayana connects the forensics module

1. Create a class with `name = "image_forensics"`.
2. Implement `analyse(context: AnalysisContext) -> ModuleResult`.
3. Run ELA, LSB/steganalysis, and metadata analysis on the original source or selected
   sampled frames as appropriate.
4. Store generated heatmaps under the job artifact directory and return web paths as
   `Artifact` objects.
5. Keep ELA observations, steganography indicators, and extracted inert payload data
   as distinct findings.

## Result rules

- `status=completed` means the module executed successfully, not that manipulation was
  detected.
- `status=skipped` requires a clear unsupported-condition explanation.
- `status=failed` is isolated; other modules and available evidence remain reportable.
- Every module supplies a meaningful version and its important thresholds/settings.
- Extracted payloads are inert evidence and must never be executed or rendered as
  active HTML.

## Current expected result

Until both adapters merge, valid uploads finish as `partially_completed`. This is
intentional and visible in reports; the platform does not fabricate model or forensic
results.
