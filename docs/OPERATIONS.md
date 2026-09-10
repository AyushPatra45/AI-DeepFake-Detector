# Prototype Operations and Data Retention

## Resource limits

The service validates all positive limits at startup. Configure them with environment
variables or equivalent `Settings` values:

| Variable | Default | Purpose |
| --- | ---: | --- |
| `APP_MAX_UPLOAD_BYTES` | 524288000 | Maximum uploaded file size before the request is rejected |
| `APP_MAX_MEDIA_PIXELS` | 40000000 | Maximum decoded width multiplied by height for images and videos |
| `APP_MAX_VIDEO_DURATION_SECONDS` | 7200 | Maximum accepted video duration |
| `APP_FRAME_INTERVAL_SECONDS` | 1.0 | Uniform video sampling interval |
| `APP_MAX_SAMPLED_FRAMES` | 300 | Maximum frames extracted from one video |

The upload limit protects disk and network use. Decoded pixel and duration limits
protect memory, decoder time, and CPU/GPU analysis time. Frame limits make long-video
processing bounded and reproducible. A media-limit violation marks the analysis job as
failed with a visible reason; it does not crash the service.

## Retention policy

| Variable | Default | Purpose |
| --- | ---: | --- |
| `APP_RETENTION_HOURS` | 168 | Keep terminal jobs and their files for seven days |
| `APP_CLEANUP_INTERVAL_SECONDS` | 3600 | Run cleanup once per hour while the API is active |

Cleanup runs when the application starts and then at the configured interval. It
removes expired completed, partially completed, and failed job records together with
their uploaded media, artifact directory, and generated JSON/PDF reports. Queued and
processing jobs are preserved even when their timestamps are old. Abandoned `.part`
uploads older than the retention cutoff are also removed.

Deletion is restricted to the configured upload, artifact, and report directories. A
database record with a path outside those roots is retained and reported as a cleanup
failure instead of deleting an arbitrary file.

## Deployment boundary

FastAPI background tasks are sufficient for the local, single-organisation prototype.
They are not a durable distributed job queue: a process restart interrupts active
analysis, and multiple long videos compete for local resources. Add a separate worker
and queue only if concurrent or multi-host deployment becomes an actual requirement.

For a clean installation check, use a dedicated `APP_DATA_DIR`, process the controlled
validation samples, download the reports, and confirm cleanup with a deliberately short
retention period in a non-production environment.
