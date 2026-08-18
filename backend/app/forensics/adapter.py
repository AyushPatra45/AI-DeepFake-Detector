from __future__ import annotations

from pathlib import Path

from app.adapters import AnalysisContext
from app.forensics.ela import generate_ela
from app.forensics.lsb import analyse_lsb
from app.forensics.metadata import extract_metadata
from app.schemas import Artifact, MediaType, ModuleResult, ModuleStatus


class ImageForensicsAnalyzer:
    name = "image_forensics"
    version = "0.1.0"

    def analyse(self, context: AnalysisContext) -> ModuleResult:
        metadata = extract_metadata(context.source_path, context.media.media_type)
        findings: dict = {"metadata": metadata}
        artifacts: list[Artifact] = []
        warnings: list[str] = []

        if context.media.media_type.is_video:
            warnings.append(
                "ELA and pixel LSB extraction are not applied to decoded video frames because "
                "codec recompression changes those signals; video metadata is reported instead."
            )
        else:
            ela = generate_ela(
                context.source_path,
                context.artifact_dir / "ela-heatmap.png",
            )
            findings["ela"] = {
                "jpeg_quality": ela.jpeg_quality,
                "mean_error": ela.mean_error,
                "percentile_95_error": ela.percentile_95_error,
                "max_error": ela.max_error,
                "highlighted_pixel_ratio": ela.highlighted_pixel_ratio,
                "interpretation": (
                    "ELA visualises recompression differences. Bright areas require human "
                    "interpretation and are not proof of editing."
                ),
            }
            artifacts.append(
                Artifact(
                    kind="ela_heatmap",
                    path=f"/artifacts/{context.job_id}/{ela.output_path.name}",
                    description="Error Level Analysis heatmap",
                )
            )

            lsb = analyse_lsb(context.source_path)
            findings["lsb"] = lsb.findings
            if lsb.extracted_payload:
                payload_path = _write_inert_payload(
                    context.artifact_dir / "extracted-lsb-payload.bin",
                    lsb.extracted_payload,
                )
                artifacts.append(
                    Artifact(
                        kind="extracted_payload",
                        path=f"/artifacts/{context.job_id}/{payload_path.name}",
                        description="Inert bytes extracted from a supported LSB layout",
                    )
                )
                warnings.append("An LSB payload was extracted as inert bytes and was not executed")

            if context.media.media_type == MediaType.PNG:
                warnings.append(
                    "ELA on PNG uses a generated JPEG comparison and is less directly "
                    "interpretable than ELA on an original JPEG."
                )

        return ModuleResult(
            module=self.name,
            status=ModuleStatus.COMPLETED,
            version=self.version,
            settings={"ela_jpeg_quality": 90, "lsb_bit_plane": 0},
            findings=findings,
            artifacts=artifacts,
            warnings=warnings,
        )


def _write_inert_payload(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path
