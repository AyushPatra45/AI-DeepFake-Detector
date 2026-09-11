# Synthetic Demonstration Corpus

The repository includes a deterministic generator for licence-safe image-forensics
demonstrations. It creates controlled ELA comparison cases and one payload that the
supported LSB extractor can recover. The generated media is deliberately excluded
from Git because it can be reproduced from source.

## Generate the corpus

From the repository root, run:

```bash
python scripts/create_demo_corpus.py
```

The command writes six images and `manifest.json` under `demo/generated/`. Every
manifest entry records its scenario, dimensions, format, SHA-256 checksum, expected
LSB result, and intended ELA comparison. Repeating the command with the same seed and
dependency versions produces the same files.

An alternate location, seed, or safe text payload can be supplied explicitly:

```bash
python scripts/create_demo_corpus.py \
  --output-dir /tmp/forensics-demo \
  --seed 20260912 \
  --payload controlled-demo-payload
```

## Included cases

| File | Controlled purpose | Expected observation |
| --- | --- | --- |
| `clean-cover.png` | PNG cover without embedded data | No supported LSB payload |
| `lsb-marker-payload.png` | Same cover with `STEGv1:` data in interleaved RGB LSBs | Exact text payload is extracted |
| `original-quality-95.jpg` | Single JPEG encoding | Reference ELA case |
| `recompressed-quality-55.jpg` | Deliberate second JPEG encoding | Recompression comparison case |
| `edited-region-quality-88.jpg` | Visible mirrored-region edit | Controlled edit comparison case |
| `screenshot-style.png` | Flat interface-like PNG | Screenshot/PNG interpretation case |

Use the web interface to upload the files individually and compare the LSB findings,
ELA heatmaps, metadata, and report exports. The corpus contains no face and is not a
deepfake-model benchmark.

## Validation boundary

This corpus proves that the implemented analysis paths execute on known inputs. It
does not establish detector accuracy, ELA reliability on unknown images, detection of
encrypted or keyed steganography, or cross-dataset deepfake generalisation. ELA may
react to ordinary compression and image-processing history, so a bright region is not
proof of manipulation. LSB statistics are also indicators unless a supported payload
structure is recovered.

Ayana's Y-01 and Y-02 tasks remain necessary: she must independently expand the
controlled corpus, record extraction rates, evaluate false positives, and explain the
results. Palak's P-03 dataset evaluation is separate and remains blocked until an
approved facial deepfake dataset subset is available.
