from __future__ import annotations

from pathlib import Path

from app.adapters import AnalysisContext
from app.authenticity.provenance import scan_provenance_markers
from app.authenticity.watermark import (
    MAX_WATERMARK_EDGE,
    MAX_WATERMARK_FRAMES,
    detect_google_sparkle,
)
from app.schemas import Artifact, ModuleResult, ModuleStatus


class MediaAuthenticityAnalyzer:
    name = "media_authenticity"
    version = "0.1.0"

    def analyse(self, context: AnalysisContext) -> ModuleResult:
        image_paths = _analysis_images(context)
        watermark = detect_google_sparkle(
            image_paths,
            artifact_path=context.artifact_dir / "visible-watermark-evidence.png",
        )
        provenance = scan_provenance_markers(context.source_path)
        artifacts = []
        if watermark.artifact_path is not None:
            artifacts.append(
                Artifact(
                    kind="visible_watermark_evidence",
                    path=f"/artifacts/{context.job_id}/{watermark.artifact_path.name}",
                    description=(
                        "Detected four-point generator watermark candidate; verify provider "
                        "attribution with an official provenance service"
                    ),
                )
            )

        warnings = []
        if watermark.candidate_detected:
            warnings.append(
                "A visible Google-style sparkle watermark candidate was detected. This is "
                "strong origin evidence, but invisible SynthID must be verified using Google's "
                "official verification technology.",
            )
        elif not provenance["ai_origin_claim_detected"]:
            warnings.append(
                "Absence of a known watermark or provenance marker does not prove that "
                "media is real."
            )
        if provenance["ai_origin_claim_detected"]:
            warnings.append(
                "AI-origin text was found in file bytes, but its signature and source are "
                "not verified. Text can be copied or edited and is not proof of AI generation."
            )

        return ModuleResult(
            module=self.name,
            status=ModuleStatus.COMPLETED,
            version=self.version,
            settings={
                "video_watermark_threshold": 0.60,
                "image_watermark_threshold": 0.88,
                "provenance_scan_bytes_per_end": 8 * 1024 * 1024,
                "max_watermark_frames": MAX_WATERMARK_FRAMES,
                "max_watermark_edge": MAX_WATERMARK_EDGE,
                "watermark_sampling": "uniform across available sampled frames",
            },
            findings={
                "assessment": (
                    "strong_ai_origin_evidence" if watermark.candidate_detected
                    else "unverified_ai_origin_claim" if provenance["ai_origin_claim_detected"]
                    else "inconclusive"
                ),
                "visible_watermark": {
                    "candidate_detected": watermark.candidate_detected,
                    "family": (
                        "Google-style four-point sparkle"
                        if watermark.candidate_detected
                        else None
                    ),
                    "match_score": watermark.match_score,
                    "location": watermark.location,
                    "bounding_box": watermark.bounding_box,
                    "bounding_box_space": "resized evidence image",
                    "analysed_frames": watermark.analysed_frames,
                    "interpretation": (
                        "A persistent visible overlay is strong evidence of generated-media "
                        "provenance; it is separate from pixel-based deepfake classification."
                    ),
                },
                "provenance": provenance,
            },
            artifacts=artifacts,
            warnings=warnings,
        )


def _analysis_images(context: AnalysisContext) -> list[Path]:
    if not context.media.media_type.is_video:
        return [context.source_path]
    return [
        context.artifact_dir / Path(frame.artifact.path).name for frame in context.frames
    ]
