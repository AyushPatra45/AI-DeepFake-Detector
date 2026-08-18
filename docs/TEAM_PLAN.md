# Team Responsibilities

## Ownership principles

Each member owns a major technical area from research through tests and documentation.
Ownership does not mean working alone: every pull request requires review from another
member, and integration interfaces are agreed by the whole team.

## Ayush Patra: platform and integration lead

Estimated share: 33 percent.

- Maintain the roadmap, shared schemas, repository and integration decisions.
- Build FastAPI endpoints, upload validation, hashing and SQLite job storage.
- Implement video decoding, configurable frame sampling and timestamp tracking.
- Integrate module outputs without treating unlike evidence as one probability.
- Build JSON/PDF report generation and model/configuration traceability.
- Package the application and maintain end-to-end and security tests.

Primary hand-offs:

- Gives decoded image/face/frame objects and timestamps to Palak's inference API.
- Gives original-quality images/keyframes to Ayana's forensic-analysis API.
- Receives typed results from both modules for storage, display, and reporting.

## Palak: deepfake ML and evaluation lead

Estimated share: 34 percent.

- Research spatial and frequency-domain deepfake detection methods.
- Prepare FaceForensics++/Celeb-DF subsets and identity-disjoint split manifests.
- Establish a reproducible pretrained baseline and document its provenance.
- Implement or adapt the ConvNeXt spatial and SRM/Bayar + FFT frequency streams.
- Train/fine-tune, calibrate thresholds, version checkpoints, and expose inference.
- Generate Grad-CAM, residual, and FFT diagnostics.
- Evaluate in-domain, cross-dataset, degradation, latency, and failure cases.

Primary hand-offs:

- Publishes a stable `predict(batch) -> DeepfakeResult[]` interface.
- Supplies checkpoint checksum, model version, thresholds, and metric reports to Ayush.
- Supplies explanation images and user-safe interpretation text to Ayana's UI.

## Ayana: image forensics and user experience lead

Estimated share: 33 percent.

- Implement ELA with adjustable recompression quality and heatmap generation.
- Implement RGB bit-plane inspection, LSB statistics, signature scanning, and safe
  extraction for explicitly supported simple payload formats.
- Extract and normalise useful EXIF, container, codec, and timestamp metadata.
- Build the upload, progress, result, timeline, evidence, and report-history screens.
- Clearly label confidence, unsupported formats, limitations, and module failures.
- Own frontend unit tests, accessibility checks, and usability evaluation.

Primary hand-offs:

- Publishes `analyse(image) -> ForensicResult` for ELA, metadata, and steganography.
- Consumes Ayush's API contract and Palak's explanation assets in the results UI.
- Provides reusable result components for screenshots and final presentation.

## Shared responsibilities

| Activity | Lead | Required support |
| --- | --- | --- |
| Literature survey | Palak | Ayush and Ayana each review at least two sources |
| Result schema and terminology | Ayush | Approval from Palak and Ayana |
| Controlled test corpus | Palak | All members contribute and verify licences |
| Integration test week | Ayush | Palak and Ayana fix their module defects |
| User study | Ayana | Ayush recruits users; Palak analyses results |
| Review presentations | Rotates | Every member presents their owned module |
| Final report | Ayush coordinates | Each member writes and verifies their section |

## Weekly working rhythm

- Monday: choose sprint tasks and write measurable acceptance checks.
- Wednesday: 20-minute integration check; raise blockers early.
- Saturday: merge reviewed work, run the full test suite, and update evidence.
- Each member keeps at most one large task in progress.
- A task is complete only with code, tests, and short documentation.

## Pull-request review map

| Author | Primary reviewer | Backup reviewer |
| --- | --- | --- |
| Ayush | Palak | Ayana |
| Palak | Ayana | Ayush |
| Ayana | Ayush | Palak |

## Fair evaluation evidence

Each member should have attributable commits, pull requests, tests, documentation, and
a demonstration of their owned module. Pair-work should list both contributors in the
pull-request description.

