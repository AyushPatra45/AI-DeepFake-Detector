# Deepfake Baseline Evaluation

## P-03 approved execution protocol

P-03 evaluates the existing externally pretrained CNN; it does not train, fine-tune,
or claim authorship of that checkpoint. Ayush approved the corrected dataset plan in
[Issue #7](https://github.com/AyushPatra45/AI-DeepFake-Detector/issues/7) on 20
September 2026. Access was obtained through the official FaceForensics++ application
using Palak's institutional account. Restricted media and access details are not
redistributed.

The frozen dataset definition is:

- FaceForensics++ public data release, official download script v4 and EU2 `v3`
  hierarchy, H.264 `c23` videos only.
- All 70 pairs in the official `dataset/splits/test.json` are one test set. P-03 does
  **not** call `create_splits`, make a 70/15/15 subdivision, or use the script's
  first-N option.
- Approved media are the 140 original YouTube sequences and both directions for each
  pair in Deepfakes, Face2Face, FaceSwap, and NeuralTextures: 700 videos total. The
  DeepFakeDetection, FaceShifter, raw, c40, masks, models, and benchmark-image
  releases are excluded.
- Five positions are frozen independently of model output at `floor(N*i/6)` for
  `i = 1..5`, where `N` is the reported video frame count. This permits at most 3,500
  frame samples. Every successfully decoded frozen frame is evaluated; missing,
  unreadable, and no-face samples remain in the failure accounting.
- `ffpp-sequence-NNN` is a sequence pseudonym, not a verified person identity. Each
  official pair is one `source_group`; both directions, all four manipulations, both
  originals, and all selected frames share that group. Therefore P-03 can claim
  official pair/source grouping, but not person-identity-disjoint evaluation.

Private metadata uses exactly `path,label,identity_ids,source_group,manipulation`.
The source media, extracted frames, official split JSON, metadata, checksummed catalog,
frame plan, checkpoint, predictions, and results stay outside this repository. Only
aggregate reviewed evidence is documented here.

### Frozen private commands

The official script help was inspected before transfer. Its `all` choice was not used
because it includes excluded releases. The private transfer selected each approved
family separately from EU2, and retained a SHA-256 inventory. Paths below are
placeholders and disclose no private location.

```bash
python -m evaluation.deepfake.video_metrics \
  --test-json <PRIVATE_ROOT>/test.json \
  --video-root <PRIVATE_ROOT>/videos \
  --frame-root <PRIVATE_ROOT>/frames \
  --metadata <PRIVATE_ROOT>/metadata.csv \
  --frame-plan <PRIVATE_ROOT>/frame_plan.json

python scripts/download_model.py \
  --output <PRIVATE_ROOT>/models/dual_stream_calibrated.pth

python -m evaluation.deepfake.prepare_dataset \
  --source-root <PRIVATE_ROOT>/frames \
  --metadata <PRIVATE_ROOT>/metadata.csv \
  --dataset "FaceForensics++ c23 official-test-70-pairs" \
  --output <PRIVATE_ROOT>/catalog.csv

python -m evaluation.deepfake.evaluate \
  --manifest <PRIVATE_ROOT>/catalog.csv \
  --data-root <PRIVATE_ROOT>/frames \
  --checkpoint <PRIVATE_ROOT>/models/dual_stream_calibrated.pth \
  --output-dir <PRIVATE_ROOT>/results/baseline
```

The untouched baseline is completed before any degradation. Robustness conditions are
JPEG quality 95/75/50, downscale-and-restore 75%/50%, Gaussian blur sigma
0.5/1.0/2.0, and Gaussian noise sigma 2/5/10 pixel levels. Noise uses seed `2205`
mixed with the immutable sample ID; the seed is not used to split the official test
set. Each condition is generated privately, checksummed with `prepare_dataset`, and
passed directly to the same evaluator.

Frame-level metrics are accuracy, precision, recall, specificity, F1, ROC-AUC, Brier
score, ten-bin ECE, confusion counts, runtime, read failures, and no-face failures.
The same classification metrics are also reported after per-video mean, top-20%, and
softmax-weighted aggregation (temperature 0.1). Per-manipulation comparisons pair each
fake family with the shared original set.

### Checkpoint provenance control

The attributed provider replaced `dual_stream_calibrated.pth` on its moving `main`
branch on 14 September 2026. The replacement is 214,687,589 bytes with SHA-256
`cacdd1f63a089f157d7cec384df632a37ee107830bd52a71d7faabeb50fd5237`; it does not
match this project's expected checkpoint and was not used. The expected 203,292,975
byte file remains available at the immutable original-upload revision
`db138ed0a70e96b087c155912cc1d306d9a97eec` and verifies as:

```text
c5c2002b5ef6c7ee0c542d7d203e16386dc641b685859d8a58ac883b52c8e4c9
```

`scripts/download_model.py` is pinned to that immutable revision. This preserves the
checkpoint already attributed by the project; it is not evidence that the team trained
or reproduced the provider's training process.

### P-03 frozen evidence

| Evidence | Value |
| --- | --- |
| Official test pairs | 70, used as one test set |
| Test JSON SHA-256 | `886f5a0da623c25820692e0d8dc33d197ddb1db527a7f1cfcb9bcbca60fe4f40` |
| Downloaded videos | 700; 1,233,742,520 bytes |
| Frozen frames | 3,500 expected; 3,500 decoded and written |
| Extraction failures | 0 videos; 0 frozen frames |
| Class counts | 700 original frames; 2,800 manipulated frames |
| Private catalog SHA-256 | `1986cb3c62dd7da1068f1e391a4ad0b8c9fea3eb4bbe8ec5656bf539c9f806cc` |
| Checkpoint revision | `db138ed0a70e96b087c155912cc1d306d9a97eec` |
| Checkpoint SHA-256 | `c5c2002b5ef6c7ee0c542d7d203e16386dc641b685859d8a58ac883b52c8e4c9` |
| Baseline metrics | Running; no metric is claimed until the private run completes |
| Robustness metrics | Not started; baseline must complete first |

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
