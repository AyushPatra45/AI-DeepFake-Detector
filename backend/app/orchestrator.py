from __future__ import annotations

from time import perf_counter

from app.adapters import AnalysisContext, ForensicAnalyzer
from app.config import Settings
from app.media import inspect_media
from app.schemas import AnalysisResult, JobStatus, ModuleResult, ModuleStatus
from app.storage import JobRepository


def process_job(
    job_id: str,
    repository: JobRepository,
    settings: Settings,
    analyzers: list[ForensicAnalyzer],
) -> None:
    repository.set_status(job_id, JobStatus.PROCESSING)
    try:
        job = repository.get(job_id)
        source_path = repository.source_path(job_id)
        started = perf_counter()
        inspected = inspect_media(
            source_path,
            job.media_type,
            output_dir=settings.artifact_dir / job_id,
            interval_seconds=settings.frame_interval_seconds,
            max_frames=settings.max_sampled_frames,
            max_pixels=settings.max_media_pixels,
            max_video_duration_seconds=settings.max_video_duration_seconds,
        )
        media_duration_ms = round((perf_counter() - started) * 1000)

        modules: list[ModuleResult] = [
            ModuleResult(
                module="platform_ingestion",
                status=ModuleStatus.COMPLETED,
                version="1.0",
                settings={
                    "frame_interval_seconds": settings.frame_interval_seconds,
                    "max_sampled_frames": settings.max_sampled_frames,
                    "max_media_pixels": settings.max_media_pixels,
                    "max_video_duration_seconds": settings.max_video_duration_seconds,
                },
                findings={
                    "sha256_verified": True,
                    "sampled_frame_count": len(inspected.frames),
                },
                duration_ms=media_duration_ms,
            )
        ]
        context = AnalysisContext(
            job_id=job_id,
            source_path=source_path,
            artifact_dir=settings.artifact_dir / job_id,
            media=inspected.info,
            frames=inspected.frames,
        )
        for analyzer in analyzers:
            analyzer_started = perf_counter()
            try:
                module = analyzer.analyse(context)
                if module.module != analyzer.name:
                    raise ValueError(
                        f"Analyzer {analyzer.name} returned module name {module.module}"
                    )
                module.duration_ms = round((perf_counter() - analyzer_started) * 1000)
                modules.append(module)
            except Exception as exc:
                modules.append(
                    ModuleResult(
                        module=analyzer.name,
                        status=ModuleStatus.FAILED,
                        version="unknown",
                        warnings=[f"{type(exc).__name__}: {exc}"],
                        duration_ms=round((perf_counter() - analyzer_started) * 1000),
                    )
                )
        result = AnalysisResult(
            job_id=job_id,
            source_sha256=job.sha256,
            code_version=settings.code_version,
            media=inspected.info,
            modules=modules,
            frames=inspected.frames,
            warnings=inspected.warnings,
        )
        partial = any(module.status != ModuleStatus.COMPLETED for module in modules)
        repository.complete(job_id, result, partial=partial)
    except Exception as exc:
        repository.fail(job_id, f"{type(exc).__name__}: {exc}")
