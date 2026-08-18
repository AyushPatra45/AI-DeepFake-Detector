from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as functional

from app.deepfake.runtime import ModelRuntime
from app.schemas import Artifact


def save_diagnostics(
    runtime: ModelRuntime,
    face_rgb: np.ndarray,
    *,
    artifact_dir: Path,
    job_id: str,
) -> list[Artifact]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    tensor = (
        torch.from_numpy(face_rgb.astype(np.float32) / 255)
        .permute(2, 0, 1)
        .unsqueeze(0)
        .to(runtime.device)
    )
    with torch.no_grad():
        residuals = runtime.model.srm(tensor)
        combined = torch.cat([residuals, runtime.model.bayar(tensor)], dim=1)
        frequency = runtime.model.fft(combined)

    residual_map = residuals[0].abs().mean(dim=0).cpu().numpy()
    frequency_map = frequency[0, :10].mean(dim=0).cpu().numpy()
    residual_visual = _colour_map(residual_map, cv2.COLORMAP_VIRIDIS)
    frequency_visual = _colour_map(frequency_map, cv2.COLORMAP_MAGMA)
    gradcam_visual = _gradcam(runtime, tensor, face_rgb)

    outputs = {
        "face_crop": ("face-crop.png", cv2.cvtColor(face_rgb, cv2.COLOR_RGB2BGR)),
        "srm_residual": ("srm-residual.png", residual_visual),
        "fft_spectrum": ("fft-spectrum.png", frequency_visual),
        "gradcam": ("gradcam-overlay.png", gradcam_visual),
    }
    artifacts = []
    for kind, (file_name, image) in outputs.items():
        destination = artifact_dir / file_name
        if not cv2.imwrite(str(destination), image):
            raise RuntimeError(f"Could not write diagnostic artifact {file_name}")
        artifacts.append(
            Artifact(
                kind=kind,
                path=f"/artifacts/{job_id}/{file_name}",
                description={
                    "face_crop": "Largest detected and expanded facial crop",
                    "srm_residual": "SRM high-frequency residual response",
                    "fft_spectrum": "FFT magnitude response of residual features",
                    "gradcam": "ConvNeXt Grad-CAM attention overlay",
                }[kind],
            )
        )
    return artifacts


def _colour_map(values: np.ndarray, colour_map: int) -> np.ndarray:
    low = float(values.min())
    high = float(values.max())
    normalised = (values - low) / max(high - low, 1e-6)
    return cv2.applyColorMap((normalised * 255).astype(np.uint8), colour_map)


def _gradcam(runtime: ModelRuntime, tensor: torch.Tensor, face_rgb: np.ndarray) -> np.ndarray:
    features: list[torch.Tensor] = []
    gradients: list[torch.Tensor] = []
    target_layer = runtime.model.spatial_backbone[-1]
    forward_handle = target_layer.register_forward_hook(
        lambda _module, _inputs, output: features.append(output)
    )
    backward_handle = target_layer.register_full_backward_hook(
        lambda _module, _grad_inputs, grad_outputs: gradients.append(grad_outputs[0])
    )
    try:
        runtime.model.zero_grad(set_to_none=True)
        with torch.enable_grad():
            runtime.model(tensor.clone().requires_grad_(True))[0, 0].backward()
        if not features or not gradients:
            heatmap = np.zeros(face_rgb.shape[:2], dtype=np.float32)
        else:
            weights = gradients[0][0].mean(dim=(1, 2))
            activation = features[0][0]
            heatmap_tensor = functional.relu((weights[:, None, None] * activation).sum(dim=0))
            heatmap = heatmap_tensor.detach().cpu().numpy()
            heatmap = (heatmap - heatmap.min()) / max(float(heatmap.max() - heatmap.min()), 1e-6)
            heatmap = cv2.resize(
                heatmap,
                (face_rgb.shape[1], face_rgb.shape[0]),
                interpolation=cv2.INTER_LINEAR,
            )
    finally:
        forward_handle.remove()
        backward_handle.remove()

    coloured = cv2.applyColorMap((heatmap * 255).astype(np.uint8), cv2.COLORMAP_JET)
    face_bgr = cv2.cvtColor(face_rgb, cv2.COLOR_RGB2BGR)
    return cv2.addWeighted(face_bgr, 0.6, coloured, 0.4, 0)
