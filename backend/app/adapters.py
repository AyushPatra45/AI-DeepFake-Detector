from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.schemas import FrameFinding, MediaInfo, ModuleResult, ModuleStatus


@dataclass(frozen=True)
class AnalysisContext:
    job_id: str
    source_path: Path
    artifact_dir: Path
    media: MediaInfo
    frames: list[FrameFinding]


class ForensicAnalyzer(Protocol):
    name: str

    def analyse(self, context: AnalysisContext) -> ModuleResult:
        """Analyse media and return one self-contained module result."""
        ...


@dataclass(frozen=True)
class UnavailableAnalyzer:
    name: str
    owner: str
    expected_capabilities: str

    def analyse(self, context: AnalysisContext) -> ModuleResult:
        return ModuleResult(
            module=self.name,
            status=ModuleStatus.SKIPPED,
            version="unconnected",
            warnings=[
                f"{self.owner}'s adapter has not been connected yet. "
                f"Expected: {self.expected_capabilities}."
            ],
        )


def default_analyzers() -> list[ForensicAnalyzer]:
    from app.forensics.adapter import ImageForensicsAnalyzer

    return [
        UnavailableAnalyzer(
            name="deepfake_detection",
            owner="Palak",
            expected_capabilities="CNN/ConvNeXt, SRM/Bayar + FFT, and Grad-CAM",
        ),
        ImageForensicsAnalyzer(),
    ]
