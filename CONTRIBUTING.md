# Contributing

## Git workflow

1. Pull the latest `main` before starting work.
2. Create a short-lived branch such as `feature/video-sampling`,
   `feature/deepfake-baseline`, `feature/ela`, or `fix/upload-validation`.
3. Keep commits focused and use messages such as `feat: add uniform frame sampler`.
4. Push the branch and open a pull request using the repository template.
5. Obtain review from at least one teammate and pass automated checks before merging.
6. Delete the merged branch and select the next planned task.

Do not commit directly to `main` after the planning baseline is established.

## Pull-request expectations

- Explain the problem, approach, ownership, and how the change was tested.
- Include screenshots for user-interface changes and metrics for model changes.
- Update API contracts and documentation when behaviour changes.
- Do not combine unrelated refactoring with a feature.
- Resolve reviewer comments or explain why a suggested change is not appropriate.

## Definition of done for a task

- Acceptance criterion is met.
- Automated tests cover normal, error, and important edge cases.
- Formatting and static checks pass.
- No dataset, checkpoint, upload, generated frame, report, secret, or environment file
  is accidentally committed.
- Documentation and attribution are updated.
- Another teammate can run or verify the feature.

## Data and experiment rules

- Record dataset version, source, terms, checksums, preprocessing, and split seed.
- Separate identities between training, validation, and testing where possible.
- Store experiment configuration with the resulting metrics and checkpoint checksum.
- Never select a final threshold using the test set.
- Report failed experiments and negative results that affect project decisions.

## Coding rules

- Use typed Python interfaces between modules.
- Keep media paths and user input out of shell commands.
- Return structured errors instead of silently skipping failures.
- Never execute extracted payloads or load untrusted pickled objects.
- Add comments only where the reason for an implementation is not obvious.

