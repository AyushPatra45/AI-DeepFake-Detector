# Palak baseline evaluation

This directory contains Palak's reproducible first-stage evaluation pipeline. It
creates checksummed dataset catalogs, enforces identity/source-disjoint splits, runs
the attributed dual-stream checkpoint, and records predictions, metrics, model
provenance, and the software environment.

No dataset, identity annotation, checkpoint, or accuracy result is committed by
default. FaceForensics++ and Celeb-DF must be obtained under their respective access
terms. Generated datasets, manifests containing local study information, checkpoints,
and results remain excluded from Git unless the team confirms they are safe and
appropriate to publish.

## 1. Prepare metadata

Create a CSV outside Git with one row per extracted face frame:

```csv
path,label,identity_ids,source_group,manipulation
real/video001/frame0001.jpg,real,person001,video001,original
fake/video101/frame0001.jpg,fake,person001;person019,video101,Deepfakes
```

- `path` is relative to `--source-root` and must identify a JPEG or PNG image.
- `identity_ids` lists every source/target identity involved, separated by semicolons.
- `source_group` identifies the original video or capture session. All its frames stay
  in one split.
- `manipulation` records the generator/manipulation family where known.

Never infer an identity from a sequential frame filename. Use the dataset's official
mapping or a documented team annotation.

## 2. Build and split the catalog

From the repository root:

```bash
python -m evaluation.deepfake.prepare_dataset \
  --source-root /path/to/extracted_faces \
  --metadata /path/to/approved_metadata.csv \
  --dataset "FaceForensics++" \
  --output evaluation/deepfake/manifests/catalog.csv

python -m evaluation.deepfake.create_splits \
  --catalog evaluation/deepfake/manifests/catalog.csv \
  --output-dir evaluation/deepfake/manifests/splits \
  --seed 2205
```

The splitter treats identities connected through a fake pair as one component. It
also keeps duplicate file hashes and frames from the same source group together. It
fails instead of silently creating overlapping splits.

Review `split_summary.json`, then freeze the catalog and split manifests used for the
reported experiment. If they may be published under the dataset terms, force-add only
the CSV/JSON manifests—not the media itself—and document that decision in the dataset
card.

## 3. Run the published-checkpoint baseline

Install the project and checkpoint as described in the root README, then run:

```bash
python -m evaluation.deepfake.evaluate \
  --manifest evaluation/deepfake/manifests/splits/test.csv \
  --data-root /path/to/extracted_faces \
  --checkpoint models/dual_stream_calibrated.pth \
  --output-dir evaluation/deepfake/results/baseline
```

Outputs:

- `predictions.csv`: per-sample score, decision, and no-face/read failures.
- `metrics.json`: ROC-AUC, F1, precision, recall, specificity, accuracy, Brier score,
  calibration error, checkpoint details, manifest hash, package versions, and commit.
- `confusion_matrix.csv`: real/fake confusion matrix.

The baseline reports only successfully detected faces and separately counts no-face
and unreadable samples. Report coverage with the accuracy metrics; excluding failed
samples without disclosure would bias the result.

## Reproducibility checklist

- [ ] Dataset name, version, source URL, access date, and terms recorded.
- [ ] Extraction procedure and frame interval recorded.
- [ ] Both identities in every manipulated pair recorded.
- [ ] Split integrity audit passes with a fixed seed.
- [ ] Test manifest is frozen before inspecting final results.
- [ ] Checkpoint and manifest SHA-256 hashes appear in `metrics.json`.
- [ ] Coverage, class balance, per-manipulation results, and failure cases reported.
- [ ] Results are described as a published-checkpoint baseline, not team-trained accuracy.
