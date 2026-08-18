from __future__ import annotations

import json
import textwrap
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.schemas import JobView


def report_payload(job: JobView) -> dict:
    return {
        "report_type": "forensic-risk-assessment",
        "disclaimer": (
            "This report contains forensic risk indicators, not conclusive legal proof "
            "of authenticity or manipulation."
        ),
        "job": job.model_dump(mode="json"),
    }


def write_json_report(job: JobView, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report_payload(job), indent=2), encoding="utf-8")
    return destination


def write_pdf_report(job: JobView, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = canvas.Canvas(str(destination), pagesize=A4)
    width, height = A4
    x = 50
    y = height - 55

    def line(text: str, *, font: str = "Helvetica", size: int = 10, gap: int = 15) -> None:
        nonlocal y
        for wrapped in textwrap.wrap(text, width=92) or [""]:
            if y < 55:
                document.showPage()
                y = height - 55
            document.setFont(font, size)
            document.drawString(x, y, wrapped)
            y -= gap

    line("AI-Powered Deepfake & Steganography Forensics", font="Helvetica-Bold", size=16, gap=22)
    line("Forensic Risk Assessment", font="Helvetica-Bold", size=12, gap=20)
    line(f"Analysis ID: {job.id}")
    line(f"Status: {job.status.value}")
    line(f"Source: {job.source_name}")
    line(f"Media type: {job.media_type.value}")
    line(f"SHA-256: {job.sha256}")
    line(f"Size: {job.size_bytes} bytes")
    line(f"Created: {job.created_at.isoformat()}")
    y -= 8

    if job.result:
        line("Media", font="Helvetica-Bold", size=12, gap=18)
        media = job.result.media
        line(f"Dimensions: {media.width} x {media.height}")
        if media.duration_seconds is not None:
            line(f"Duration: {media.duration_seconds:.3f} seconds")
            line(f"Frame rate: {media.frame_rate} FPS")
            line(f"Sampled frames: {len(job.result.frames)}")

        y -= 8
        line("Module findings", font="Helvetica-Bold", size=12, gap=18)
        for module in job.result.modules:
            line(f"{module.module}: {module.status.value}", font="Helvetica-Bold")
            for warning in module.warnings:
                line(f"Warning: {warning}")
            if module.findings:
                line(json.dumps(module.findings, sort_keys=True))

        if job.result.warnings:
            y -= 8
            line("Analysis warnings", font="Helvetica-Bold", size=12, gap=18)
            for warning in job.result.warnings:
                line(warning)

    y -= 10
    line(
        "Limitation: This report contains forensic risk indicators, not conclusive "
        "legal proof of authenticity or manipulation.",
        font="Helvetica-Oblique",
    )
    document.save()
    return destination
