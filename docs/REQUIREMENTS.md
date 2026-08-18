# Requirements and Acceptance Criteria

## Functional requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| FR-01 | Accept supported image and video uploads | Valid JPEG/PNG and MP4/MOV files create an analysis job; invalid files are rejected |
| FR-02 | Preserve evidence identity | SHA-256 hash, size, detected MIME type, and analysis time appear in every result |
| FR-03 | Analyse still images for deepfake indicators | A supported image returns probability, decision threshold, model version, and explanation assets |
| FR-04 | Analyse full-length videos efficiently | Frames are sampled with timestamps; sampling policy is shown in the report |
| FR-05 | Detect and align faces | Each analysed face is linked to its frame and failures do not crash the job |
| FR-06 | Use spatial and frequency features | Inference uses a CNN/ConvNeXt branch and an SRM/Bayar + FFT branch |
| FR-07 | Aggregate video evidence | Video result includes aggregate score, suspicious timestamps, and top evidence frames |
| FR-08 | Generate ELA evidence | JPEG-compatible inputs return a heatmap and quality setting; unsuitable inputs show a limitation |
| FR-09 | Analyse common LSB patterns | Result includes inspected channels/planes, statistical indicators, signatures, and supported extraction output |
| FR-10 | Inspect metadata | Relevant EXIF/container/codec metadata and parsing warnings are returned |
| FR-11 | Keep modules independent | A failure in one optional forensic module is visible but does not discard other results |
| FR-12 | Show analysis progress | UI displays queued, processing, completed, partially completed, and failed states |
| FR-13 | Export reports | Completed jobs can export structured JSON and a readable PDF report |
| FR-14 | Retain job history | User can list and reopen results during the configured retention period |

## Non-functional requirements

| ID | Requirement | Target |
| --- | --- | --- |
| NFR-01 | Reproducibility | Report records source hash, code version, model version, thresholds, and module settings |
| NFR-02 | Model evaluation | Publish ROC-AUC, F1, precision, recall, confusion matrix, and calibration on immutable test splits |
| NFR-03 | Generalisation | Evaluate at least one dataset/manipulation family excluded from training and discuss domain shift |
| NFR-04 | Robustness | Measure effects of JPEG quality, resizing, blur, noise, and video frame sampling |
| NFR-05 | Performance | Process a normal image interactively and a five-minute video through sampling without loading the whole video into memory |
| NFR-06 | Security | Validate content, constrain paths, limit sizes, sanitise names, and never execute extracted data |
| NFR-07 | Privacy | Process locally by default and automatically remove temporary media under a documented retention policy |
| NFR-08 | Reliability | Automated tests cover core algorithms, API integration, malformed media, and no-face cases |
| NFR-09 | Accessibility | Main workflow is keyboard usable, labelled, responsive, and not colour-only |
| NFR-10 | Explainability | Every score states what it measures, its uncertainty, and its main limitations |

## Supported prototype boundary

### Included

- JPEG and PNG image analysis.
- MP4 and MOV video analysis where codecs are available through OpenCV/FFmpeg.
- Face-focused deepfake detection on sampled frames.
- ELA, SRM/noise residual, FFT spectrum, and Grad-CAM evidence.
- LSB inspection and safe extraction for documented simple embedding layouts.
- Local, single-organisation prototype deployment.

### Not promised

- Guaranteed detection of every generator, manipulation, or steganography algorithm.
- Legal proof of authenticity or identification of the person who edited a file.
- Recovery of encrypted payloads or payloads using unknown stego keys/algorithms.
- Real-time analysis of every frame in arbitrarily long videos.
- Cloud-scale multi-tenant production deployment in the first prototype.

## Software requirements

| Area | Planned choice |
| --- | --- |
| Runtime | Python 3.11 |
| ML | PyTorch 2.x and timm |
| Vision/media | OpenCV and FFmpeg |
| Numerical processing | NumPy and SciPy |
| Image/metadata | Pillow and ExifRead or equivalent maintained parser |
| API | FastAPI, Pydantic and Uvicorn |
| Persistence | SQLite with SQLAlchemy |
| Reporting | ReportLab/WeasyPrint and JSON export |
| Frontend | HTML, CSS and JavaScript served by the application |
| Testing | Pytest, HTTPX and Playwright for the final workflow |
| Quality | Ruff and a consistent formatter/type-check configuration |

Versions must be pinned after the first working environment is verified. The project
must include setup instructions and a sample configuration without secrets.

## Hardware and data requirements

- Development machine with at least 16 GB RAM and sufficient storage for selected
  dataset subsets; GPU with CUDA is recommended for training but not mandatory for
  CPU inference testing.
- Datasets must have documented sources, licences/terms, checksums, and split rules.
- Candidate datasets: FaceForensics++, Celeb-DF v2, and a small controlled
  steganography corpus produced from licence-compatible cover images.
- Raw datasets and checkpoints must live outside Git or in an approved model/artifact
  store; only manifests and download instructions belong in the repository.

## Minimum release acceptance

1. Fresh installation succeeds from the documented setup on a second machine.
2. One real image, one manipulated image, one stego image, and one video complete the
   expected workflow and produce reports.
3. Malformed files, unsupported files, no-face media, and partial module failures are
   handled visibly without server crashes.
4. All core automated tests pass and the evaluation report is reproducible.
5. Model performance is reported honestly on in-domain and cross-dataset data; no
   unverified accuracy claim appears in the UI or documentation.
6. Extracted payloads are stored as inert bytes and are never executed or rendered as
   active HTML/scripts.
7. Third-party code, models, and datasets are attributed with their licences/terms.

