from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

import cv2

from app.adapters import AnalysisContext
from app.deepfake.aggregation import softmax_weighted_score
from app.deepfake.diagnostics import save_diagnostics
from app.deepfake.face import FaceCropper
from app.deepfake.runtime import ModelRuntime, load_runtime
from app.schemas import ModuleResult, ModuleStatus


@dataclass
class DeepfakeAnalyzer:
    checkpoint_path: Path
    image_size: int = 512
    batch_size: int = 4
    name: str = "deepfake_detection"
    version: str = "dual-stream-0.1.0"
    _runtime: ModelRuntime | None = field(default=None, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    @classmethod
    def from_env(cls) -> DeepfakeAnalyzer:
        return cls(
            checkpoint_path=Path(
                os.getenv("APP_MODEL_PATH", "models/dual_stream_calibrated.pth")
            ).resolve(),
            image_size=int(os.getenv("APP_DEEPFAKE_IMAGE_SIZE", "512")),
            batch_size=int(os.getenv("APP_DEEPFAKE_BATCH_SIZE", "4")),
        )

    def analyse(self, context: AnalysisContext) -> ModuleResult:
        if not self.checkpoint_path.is_file():
            return ModuleResult(
                module=self.name,
                status=ModuleStatus.SKIPPED,
                version=self.version,
                settings={"checkpoint_path": str(self.checkpoint_path)},
                warnings=[
                    "Calibrated model checkpoint is not installed. Run "
                    "scripts/download_model.py before requesting deepfake inference."
                ],
            )

        runtime = self._get_runtime()
        cropper = FaceCropper(target_size=self.image_size)
        candidates = _candidate_images(context)
        faces = []
        frame_references = []
        for image_path, frame in candidates:
            image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
            if image is None:
                continue
            face = cropper.crop_largest(image)
            if face is not None:
                faces.append(face)
                frame_references.append(frame)

        if not faces:
            return ModuleResult(
                module=self.name,
                status=ModuleStatus.SKIPPED,
                version=self.version,
                settings={"image_size": self.image_size},
                warnings=["No detectable face was available for the face-focused model"],
            )

        probabilities = runtime.predict(faces, batch_size=self.batch_size)
        for frame, probability in zip(frame_references, probabilities, strict=True):
            if frame is not None:
                frame.deepfake_probability = probability

        score = (
            softmax_weighted_score(probabilities, temperature=0.1)
            if context.media.media_type.is_video
            else probabilities[0]
        )
        top_index = max(range(len(probabilities)), key=probabilities.__getitem__)
        artifacts = save_diagnostics(
            runtime,
            faces[top_index],
            artifact_dir=context.artifact_dir,
            job_id=context.job_id,
        )
        frame_scores = [
            {
                "frame_index": frame.frame_index if frame is not None else None,
                "timestamp_seconds": frame.timestamp_seconds if frame is not None else None,
                "probability": round(probability, 6),
            }
            for frame, probability in zip(frame_references, probabilities, strict=True)
        ]
        return ModuleResult(
            module=self.name,
            status=ModuleStatus.COMPLETED,
            version=self.version,
            settings={
                "image_size": self.image_size,
                "batch_size": self.batch_size,
                "threshold": runtime.threshold,
                "calibration_temperature": runtime.temperature,
                "video_aggregation": "softmax_weighted_tau_0.1",
                "checkpoint_sha256": runtime.checkpoint_sha256,
            },
            findings={
                "deepfake_probability": round(score, 6),
                "decision": "suspicious" if score >= runtime.threshold else "lower_risk",
                "analysed_faces": len(faces),
                "candidate_frames": len(candidates),
                "frame_scores": frame_scores,
            },
            artifacts=artifacts,
            warnings=[
                "Deepfake probability is model-dependent and may not generalise to unseen "
                "generators, heavy blur, or out-of-distribution media."
            ],
        )

    def _get_runtime(self) -> ModelRuntime:
        if self._runtime is None:
            with self._lock:
                if self._runtime is None:
                    self._runtime = load_runtime(self.checkpoint_path)
        return self._runtime


def _candidate_images(context: AnalysisContext) -> list[tuple[Path, object | None]]:
    if not context.media.media_type.is_video:
        return [(context.source_path, None)]
    return [
        (context.artifact_dir / Path(frame.artifact.path).name, frame) for frame in context.frames
    ]
