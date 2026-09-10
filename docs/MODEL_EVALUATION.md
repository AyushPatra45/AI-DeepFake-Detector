# Deepfake Baseline Evaluation

## Status and scope

This document covers task P-01: reproducibly evaluate the attributed dual-stream
checkpoint on a fixed, approved dataset subset. The manifest, leakage controls,
metrics, provenance capture, and tests are implemented under `evaluation/deepfake/`.

No approved dataset subset is present in this repository, so no accuracy, ROC-AUC,
F1, precision, recall, or calibration result is claimed here. A published-checkpoint
baseline becomes a scientific result only after the commands below are run against a
frozen test manifest and the generated evidence is reviewed.

P-01 does not retrain the model, change production inference, perform cross-dataset or
degradation experiments, or establish universal deepfake-detection accuracy.

## Baseline under evaluation

The production application loads `models/dual_stream_calibrated.pth`, downloaded by
`scripts/download_model.py`. The repository records the expected checkpoint SHA-256 as:

```text
c5c2002b5ef6c7ee0c542d7d203e16386dc641b685859d8a58ac883b52c8e4c9
```

The checkpoint supplies the decision threshold and calibration temperature. The
evaluator records both values, but it does not tune either value on the test set.
Production preprocessing is reused: OpenCV detects the largest face, expands the crop,
resizes it to 512 by 512 RGB pixels, and the runtime returns a calibrated fake-media
probability.

## Dataset requirements

Obtain FaceForensics++, Celeb-DF, or another approved dataset under its official terms.
Raw media, face crops, identity annotations, checkpoints, and generated results must
remain outside Git unless their publication is explicitly permitted.

Create a private metadata CSV from `evaluation/deepfake/metadata_template.csv` with:

| Column | Meaning |
| --- | --- |
| `path` | JPEG/PNG path relative to the supplied data root |
| `label` | `real`/`fake` or `0`/`1` |
| `identity_ids` | Every source and target identity, separated with semicolons |
| `source_group` | Original video or capture-session identifier |
| `manipulation` | Generator/manipulation family, or `original` |

The catalog command validates relative paths, supported extensions, unique paths,
unique content hashes, identities, labels, and source groups. Each catalog row records
the media SHA-256.

## Fixed split procedure

The splitter forms connected components across three constraints:

1. Every source and target identity.
2. Every frame from the same source video/session.
3. Duplicate SHA-256 content.

A component is assigned wholly to train, validation, or test. This prevents identity,
video-frame, and duplicate-media leakage. The default split is 70/15/15 with seed
`2205`; the exact catalog and generated manifests must be frozen before final test
results are inspected.

## Reproduction commands

Run from the repository root after installing the project and checkpoint:

```bash
python -m evaluation.deepfake.prepare_dataset \
  --source-root /path/to/extracted_frames \
  --metadata /private/path/approved_metadata.csv \
  --dataset "FaceForensics++" \
  --output evaluation/deepfake/manifests/catalog.csv

python -m evaluation.deepfake.create_splits \
  --catalog evaluation/deepfake/manifests/catalog.csv \
  --output-dir evaluation/deepfake/manifests/splits \
  --seed 2205

python -m evaluation.deepfake.evaluate \
  --manifest evaluation/deepfake/manifests/splits/test.csv \
  --data-root /path/to/extracted_frames \
  --checkpoint models/dual_stream_calibrated.pth \
  --output-dir evaluation/deepfake/results/baseline
```

Generated evidence consists of:

- `predictions.csv`: per-sample score, decision, dataset, manipulation, and failure
  status.
- `metrics.json`: accuracy, precision, recall, specificity, F1, ROC-AUC, Brier score,
  ten-bin expected calibration error, coverage counts, checkpoint/manifest hashes,
  Git revision, and dependency versions.
- `confusion_matrix.csv`: real/fake confusion counts at the recorded threshold.
- `split_summary.json`: class, identity, and source-group counts plus the split seed and
  leakage-audit result.

## Actual software verification

Run on 11 September 2026 after merging `origin/main` into
`codex/palak-dataset-evaluation`:

```text
.\.venv\Scripts\python.exe -m pytest -q evaluation/deepfake/tests
5 passed

.\.venv\Scripts\python.exe -m pytest -q backend/tests
25 passed, 2 third-party deprecation warnings

.\.venv\Scripts\python.exe -m pytest -q
30 passed, 2 third-party deprecation warnings

.\.venv\Scripts\ruff.exe check backend evaluation scripts
All checks passed!
```

The warnings originate from FastAPI/Starlette test dependencies and do not indicate a
failure in the evaluation pipeline.

## Results

| Evidence | Current value |
| --- | --- |
| Approved dataset/version | Not supplied |
| Frozen test manifest | Not generated |
| Evaluated samples | Not run |
| Face-detection coverage | Not run |
| ROC-AUC/F1/precision/recall | Not run; no claim |
| Confusion matrix | Not run |
| Calibration metrics | Not run |

When the experiment is run, copy only reviewed aggregate results into this table and
record the immutable manifest/checkpoint hashes. Do not commit restricted sample paths
or identity information.

## Limitations and remaining validation

- The checkpoint was published externally; loading it is not evidence that this team
  trained it or reproduced its original metrics.
- The current Haar cascade selects only the largest detected face. Missed, profile,
  occluded, small, or multiple faces can bias coverage and results.
- Metrics calculated only on detected faces must always be reported with no-face and
  read-error counts.
- Identity-disjoint splitting reduces leakage but does not remove dataset-specific
  compression, camera, demographic, or manipulation shortcuts.
- The checkpoint threshold (`0.01` in the existing status record) is unusually low and
  must not be changed or endorsed from test-set performance alone.
- A single in-domain subset cannot establish generalisation to unseen generators.
- Cross-dataset, JPEG, resize, blur, noise, latency, aggregation, and detailed failure
  experiments remain later work and are not completed by P-01.
- Grad-CAM, SRM, and FFT images are supporting diagnostics, not proof of manipulation.

See `evaluation/deepfake/README.md` for the operational checklist and dataset-card
template.
