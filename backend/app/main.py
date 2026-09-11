from __future__ import annotations

import asyncio
from collections.abc import Sequence
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.adapters import ForensicAnalyzer, default_analyzers
from app.config import Settings
from app.ingestion import InvalidMediaError, UploadTooLargeError, save_upload
from app.orchestrator import process_job
from app.reporting import write_json_report, write_pdf_report
from app.retention import RetentionManager
from app.schemas import HealthResponse, JobList, JobView
from app.storage import JobNotFoundError, JobRepository


def _repository(request: Request) -> JobRepository:
    return request.app.state.repository


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def create_app(
    settings: Settings | None = None,
    analyzers: Sequence[ForensicAnalyzer] | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    resolved_settings.create_directories()
    repository = JobRepository(resolved_settings.database_path)
    retention_manager = RetentionManager(repository, resolved_settings)
    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await asyncio.to_thread(retention_manager.run_if_due, force=True)

        async def cleanup_loop() -> None:
            while True:
                await asyncio.sleep(resolved_settings.cleanup_interval_seconds)
                await asyncio.to_thread(retention_manager.run_if_due, force=True)

        cleanup_task = asyncio.create_task(cleanup_loop())
        try:
            yield
        finally:
            cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await cleanup_task

    app = FastAPI(
        title="AI-Powered Deepfake & Steganography Forensics API",
        version="0.1.0",
        description="Evidence-oriented image and video forensic analysis API",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.repository = repository
    app.state.retention_manager = retention_manager
    app.state.analyzers = list(analyzers) if analyzers is not None else default_analyzers()
    app.mount(
        "/artifacts",
        StaticFiles(directory=resolved_settings.artifact_dir),
        name="artifacts",
    )
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    def root() -> FileResponse:
        return FileResponse(frontend_dir / "index.html")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(version=resolved_settings.code_version)

    @app.post("/api/v1/analyses", response_model=JobView, status_code=202)
    async def create_analysis(
        background_tasks: BackgroundTasks,
        request: Request,
        file: Annotated[UploadFile, File()],
    ) -> JobView:
        job_id = str(uuid4())
        try:
            media = await save_upload(
                file,
                job_id=job_id,
                upload_dir=_settings(request).upload_dir,
                max_bytes=_settings(request).max_upload_bytes,
            )
        except UploadTooLargeError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        except InvalidMediaError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc

        job = _repository(request).create(
            job_id=job_id,
            source_name=media.source_name,
            source_path=media.path,
            media_type=media.media_type,
            sha256=media.sha256,
            size_bytes=media.size_bytes,
        )
        background_tasks.add_task(
            process_job,
            job_id,
            _repository(request),
            _settings(request),
            request.app.state.analyzers,
        )
        return job

    @app.get("/api/v1/analyses", response_model=JobList)
    def list_analyses(
        request: Request,
        limit: int = Query(default=50, ge=1, le=200),
    ) -> JobList:
        return JobList(jobs=_repository(request).list(limit))

    @app.get("/api/v1/analyses/{job_id}", response_model=JobView)
    def get_analysis(job_id: str, request: Request) -> JobView:
        return _get_job(_repository(request), job_id)

    @app.get("/api/v1/analyses/{job_id}/report.json")
    def json_report(job_id: str, request: Request) -> FileResponse:
        job = _get_completed_job(_repository(request), job_id)
        destination = _settings(request).report_dir / f"{job_id}.json"
        write_json_report(job, destination)
        return FileResponse(destination, media_type="application/json", filename=destination.name)

    @app.get("/api/v1/analyses/{job_id}/report.pdf")
    def pdf_report(job_id: str, request: Request) -> FileResponse:
        job = _get_completed_job(_repository(request), job_id)
        destination = _settings(request).report_dir / f"{job_id}.pdf"
        write_pdf_report(job, destination)
        return FileResponse(destination, media_type="application/pdf", filename=destination.name)

    return app


def _get_job(repository: JobRepository, job_id: str) -> JobView:
    try:
        return repository.get(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Analysis job not found") from exc


def _get_completed_job(repository: JobRepository, job_id: str) -> JobView:
    job = _get_job(repository, job_id)
    if job.result is None:
        raise HTTPException(status_code=409, detail="Analysis report is not ready")
    return job


app = create_app()
