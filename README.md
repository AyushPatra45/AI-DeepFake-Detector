# AI-Powered Deepfake & Steganography Forensics

A digital-forensics platform that analyses images and videos for deepfake indicators,
image-manipulation evidence, and hidden data. The system combines a dual-stream
deepfake detector with explainable forensic modules and produces an evidence-based
report instead of claiming absolute proof.

## Project status

**Current phase:** Platform foundation implementation

The problem statement, architecture, ownership, requirements, and milestones are
defined. Ayush's backend foundation now provides safe upload ingestion, SHA-256
evidence hashing, SQLite job tracking, image inspection, timestamped video sampling,
typed analyzer adapters, and JSON/PDF report exports. The deepfake and image-forensics
adapters remain explicitly marked as unconnected until their feature branches merge.

## Planned capabilities

- Upload and validate images and full-length videos.
- Sample video frames and detect/align faces efficiently.
- Classify facial media using spatial and frequency-domain features.
- Generate Grad-CAM, noise-residual, FFT, and ELA visualisations.
- Detect common LSB steganography indicators and safely extract supported payloads.
- Inspect useful file and media metadata.
- Show suspicious video timestamps and per-frame evidence.
- Export a unified forensic report with limitations and confidence scores.

## High-level pipeline

```text
Image / Video
    |
    v
Validation, hashing and metadata
    |
    +--> Image preprocessing
    |
    +--> Video frame sampling --> face detection and alignment
                               |
                               v
                  Dual-stream deepfake detector
                  - Spatial ConvNeXt/CNN branch
                  - SRM/Bayar + FFT branch
                               |
            +------------------+------------------+
            |                  |                  |
            v                  v                  v
           ELA        LSB/steganalysis      Grad-CAM/FFT
            |                  |                  |
            +------------------+------------------+
                               |
                               v
                    Evidence and PDF/JSON report
```

Deepfake probability, ELA observations, and steganography findings are reported as
separate evidence signals. They will not be blindly averaged because they answer
different forensic questions.

## Team

| Member | Primary ownership |
| --- | --- |
| Ayush Patra | Technical lead, backend, video pipeline, integration and reporting |
| Palak | Deepfake model, datasets, training, evaluation and explainability |
| Ayana | ELA, steganography, metadata analysis, frontend and usability testing |

Everyone participates in literature review, integration testing, documentation, and
presentations. See [Team Plan](docs/TEAM_PLAN.md) for the detailed split and hand-offs.

## Documentation

- [Project Plan](docs/PROJECT_PLAN.md)
- [Requirements and Acceptance Criteria](docs/REQUIREMENTS.md)
- [System Architecture](docs/ARCHITECTURE.md)
- [Team Responsibilities](docs/TEAM_PLAN.md)
- [Platform Foundation Hand-off](docs/PLATFORM_HANDOFF.md)
- [Contributing and Git Workflow](CONTRIBUTING.md)
- [Third-party Software and Attribution](THIRD_PARTY.md)

## Intended technology stack

- Python 3.11
- PyTorch, timm, OpenCV, NumPy and SciPy
- FastAPI backend with background analysis jobs
- HTML, CSS and JavaScript frontend
- SQLite for prototype job metadata and report history
- Pytest for automated testing

The exact dependency versions will be pinned when the implementation environment is
created. Large datasets, model checkpoints, user uploads, extracted frames, and
generated reports are intentionally excluded from Git.

## Run the backend

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn app.main:app --app-dir backend --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API. Runtime uploads,
artifacts, reports, and SQLite data are written under `runtime/` by default.

Run verification with:

```bash
pytest
ruff check backend
```

## Teammate integration contract

Feature modules implement the `ForensicAnalyzer` protocol in
`backend/app/adapters.py`. An analyzer receives an `AnalysisContext` containing the
source path, validated media information, and sampled video frames, then returns one
typed `ModuleResult`. This keeps model, ELA, LSB, and metadata failures isolated while
preserving all available evidence in the final report.

## Scope statement

This is an academic, fully functional prototype. It is designed to surface forensic
risk indicators and supporting evidence. It is not a universal authenticity oracle,
and its reports must not be treated as conclusive legal proof without expert review.

## Reference implementation

The deepfake module will evaluate and may adapt ideas from
[yyouretoast/deepfake-detection](https://github.com/yyouretoast/deepfake-detection),
which uses a ConvNeXt spatial stream and an SRM/Bayar + FFT frequency stream. Any code
adapted from it must retain its MIT licence notice and be documented in
[THIRD_PARTY.md](THIRD_PARTY.md).
