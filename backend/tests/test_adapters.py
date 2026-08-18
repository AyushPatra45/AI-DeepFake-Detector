from __future__ import annotations

from app.adapters import AnalysisContext, UnavailableAnalyzer
from app.schemas import MediaInfo, MediaType, ModuleStatus


def test_unavailable_adapter_returns_explicit_skipped_result(tmp_path) -> None:
    adapter = UnavailableAnalyzer(
        name="deepfake_detection",
        owner="Palak",
        expected_capabilities="model inference",
    )
    context = AnalysisContext(
        job_id="job-1",
        source_path=tmp_path / "source.png",
        media=MediaInfo(media_type=MediaType.PNG, width=10, height=10),
        frames=[],
    )

    result = adapter.analyse(context)

    assert result.module == "deepfake_detection"
    assert result.status == ModuleStatus.SKIPPED
    assert "Palak" in result.warnings[0]
