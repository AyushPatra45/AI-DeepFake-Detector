# Third-party Software, Models and Datasets

This file must be updated whenever code, model weights, datasets, icons, or other
assets are added to the project.

## Candidate deepfake reference

- Project: `yyouretoast/deepfake-detection`
- Source: https://github.com/yyouretoast/deepfake-detection
- Licence: MIT (verify and retain the exact licence text when code is incorporated)
- Use: attributed adaptation of the ConvNeXt spatial stream, SRM/Bayar + FFT frequency
  stream, frame aggregation, checkpoint loading, and diagnostic approach.
- Adapted files: `backend/app/deepfake/`.
- Retained licence: `licenses/yyouretoast-deepfake-detection-MIT.txt`.
- Published checkpoint: `yyouretoast/deepfake-detector/dual_stream_calibrated.pth`
  on Hugging Face. The checkpoint is downloaded locally and is not committed.
- Verified checkpoint SHA-256:
  `c5c2002b5ef6c7ee0c542d7d203e16386dc641b685859d8a58ac883b52c8e4c9`.
- Important limitation: the reference project reports strong in-distribution results
  but materially weaker cross-dataset performance. This limitation must remain visible
  in our UI and reports.

## Candidate datasets

| Dataset | Planned use | Requirement before use |
| --- | --- | --- |
| FaceForensics++ | Training/evaluation of facial manipulations | Obtain access and follow academic terms |
| Celeb-DF v2 | Training or cross-dataset evaluation | Obtain access and follow release agreement |
| Controlled stego corpus | LSB testing | Use licence-compatible cover images and record embedding settings |

Dataset files must not be committed. Add exact citations, versions, URLs, terms, and
access dates to the final dataset card before experiments are reported.

## Attribution checklist

- Preserve copyright and licence notices required by each dependency.
- Mark files or sections containing adapted code.
- Cite research papers for implemented methods.
- Record model-weight licences separately from source-code licences.
- Confirm whether demonstration media can be redistributed.
