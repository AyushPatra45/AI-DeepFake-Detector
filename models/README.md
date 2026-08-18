# Model files

Model checkpoints are intentionally excluded from Git. Install the attributed
dual-stream checkpoint with:

```bash
python scripts/download_model.py
```

The application records the downloaded file's SHA-256 checksum in every completed
deepfake result. See `THIRD_PARTY.md` for provenance, licence, dataset restrictions,
and the original model's known cross-dataset limitations.

Verified published checkpoint SHA-256:

```text
c5c2002b5ef6c7ee0c542d7d203e16386dc641b685859d8a58ac883b52c8e4c9
```
