# Project Plan

## 1. Problem statement

AI-generated and digitally manipulated media can be used for misinformation,
impersonation, fraud, and social engineering. Images may also conceal data through
steganography. Existing tools commonly focus on only one task and may return a label
without enough evidence for a user to understand the result.

This project will build one forensic workflow for images and videos that combines
deepfake risk estimation, manipulation visualisation, common LSB steganography
analysis, metadata inspection, and evidence reporting.

## 2. Objectives

1. Detect deepfake indicators in uploaded images and sampled video frames.
2. Combine spatial CNN features with SRM/Bayar residual and FFT features.
3. Localise suspicious compression differences using ELA as supporting evidence.
4. Detect common LSB embedding indicators and extract supported payloads safely.
5. Aggregate frame results into video-level risk with suspicious timestamps.
6. Produce explainable, downloadable JSON and PDF reports.
7. Evaluate accuracy, robustness, performance, and known failure modes.

## 3. Deliverables

| Deliverable | Evidence of completion |
| --- | --- |
| Web application | Image/video upload, progress state, results view and history |
| Deepfake engine | Versioned model, inference API and evaluation metrics |
| Video engine | Configurable sampling, face crops and timestamp aggregation |
| ELA module | Heatmap, configurable quality and interpretation note |
| Steganography module | LSB statistics, supported extraction and payload preview |
| Metadata module | Hashes and relevant image/video metadata |
| Reporting module | Downloadable JSON and PDF forensic report |
| Test suite | Unit, integration, model and end-to-end tests |
| Documentation | Setup, architecture, dataset, evaluation and user guide |

## 4. Delivery roadmap

| Phase | Weeks | Goal | Exit condition |
| --- | --- | --- | --- |
| Review 1 | 1 | Problem, scope, literature and design | Proposal and architecture approved |
| Foundation | 2 | Repository, environments, API contracts and sample corpus | All members can run the skeleton locally |
| Parallel baselines | 3-4 | Baseline deepfake, ELA, LSB and video sampling | Each module has tests and sample output |
| Model improvement | 5-6 | Dual-stream model and evaluation pipeline | Reproducible checkpoint and metrics |
| Integration | 7-8 | Connect all engines through backend and UI | End-to-end image and video analysis works |
| Reporting | 9 | Evidence aggregation, timestamps and exports | JSON/PDF reports match stored job results |
| Validation | 10-11 | Accuracy, robustness, security and usability tests | Acceptance criteria recorded with evidence |
| Final delivery | 12 | Documentation, deployment package and presentation | Clean installation and live demonstration |

## 5. First implementation sprint

| Task | Owner | Output |
| --- | --- | --- |
| Define API request/response schemas | Ayush | OpenAPI contract and typed models |
| Build safe upload, hashing and job storage | Ayush | Tested ingestion endpoint |
| Reproduce baseline detector on a small dataset subset | Palak | Baseline notebook/script and metrics |
| Document datasets and identity-disjoint split | Palak | Dataset card and split manifest |
| Implement ELA with limitations | Ayana | Heatmap function and unit tests |
| Implement LSB bit-plane/statistical inspection | Ayana | Structured findings and unit tests |
| Agree on shared result schema | All | Versioned forensic result object |
| Prepare controlled real/fake/stego samples | All | Small, legally usable test corpus |

## 6. Development strategy

- Deliver one vertical slice first: image upload to complete report.
- Add video sampling and temporal aggregation after image modules are stable.
- Begin with a reproducible pretrained baseline before expensive retraining.
- Keep model inference, ELA, and steganography as independently testable services.
- Store model version, thresholds, configuration, and file hash in every report.
- Never execute or automatically open an extracted payload.

## 7. Validation plan

### Model validation

- Use identity-disjoint train, validation, and test splits.
- Record ROC-AUC, F1, precision, recall, confusion matrix, and calibration error.
- Test at least one dataset not used for training to expose domain shift.
- Test JPEG compression, resizing, blur, noise, and frame-rate changes.
- Report results per dataset and manipulation type, not only one combined number.

### Software validation

- Unit tests for frame sampling, ELA, LSB conversion, hashing, and aggregation.
- Integration tests from upload through stored result and report generation.
- End-to-end tests for one image, one short video, malformed media, and no-face video.
- Security tests for MIME spoofing, path traversal, oversized files, and malicious names.
- Usability testing with at least five users and a short task questionnaire.

## 8. Major risks and controls

| Risk | Impact | Control |
| --- | --- | --- |
| Unseen deepfake generators | Incorrect classification | Cross-dataset evaluation and clear uncertainty |
| Limited GPU access | Slow training | Pretrained baseline, small experiments and saved checkpoints |
| Long videos | High runtime/storage | Configurable sampling, batching and temporary-file cleanup |
| Recompression weakens ELA/FFT evidence | Misleading interpretation | Show limitations and use multiple independent signals |
| LSB extraction fails on encrypted/unknown schemes | Incomplete finding | Report statistical evidence and supported methods only |
| Dataset leakage | Inflated metrics | Identity-disjoint splitting and immutable test manifest |
| Copied code without attribution | Academic/licensing issue | Preserve licences and maintain THIRD_PARTY.md |
| Unsafe uploaded/extracted files | Security issue | Validate, sandbox, never execute, and delete by retention policy |

## 9. Definition of done

The prototype is complete when a fresh installation can accept supported images and
videos, run every selected module, show progress and errors, generate reproducible
evidence, export a report, and pass the acceptance tests in REQUIREMENTS.md. Final
evaluation must include both successful cases and documented failure cases.
