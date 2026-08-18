"""Dual-stream ConvNeXt and SRM/Bayar FFT model.

Adapted from https://github.com/yyouretoast/deepfake-detection under the MIT License.
The required copyright and licence text is retained under licenses/.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as functional
from torch import nn
from torchvision import models


class SRMConv2d(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        kernels = np.array(
            [
                [
                    [0, 0, 0, 0, 0],
                    [0, -1, 2, -1, 0],
                    [0, 2, -4, 2, 0],
                    [0, -1, 2, -1, 0],
                    [0, 0, 0, 0, 0],
                ],
                [
                    [-1, 2, -2, 2, -1],
                    [2, -6, 8, -6, 2],
                    [-2, 8, -12, 8, -2],
                    [2, -6, 8, -6, 2],
                    [-1, 2, -2, 2, -1],
                ],
                [
                    [0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0],
                    [0, 1, -2, 1, 0],
                    [0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0],
                ],
            ],
            dtype=np.float32,
        )
        kernels[0] /= 4.0
        kernels[1] /= 12.0
        kernels[2] /= 2.0
        filters = np.tile(kernels[:, np.newaxis, :, :], (3, 1, 1, 1))
        self.register_buffer("weights", torch.from_numpy(filters))

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        weights = self.weights.to(dtype=inputs.dtype, device=inputs.device)
        return functional.conv2d(inputs, weights, stride=1, padding=2, groups=3)


class BayarConv2d(nn.Module):
    def __init__(self, in_channels: int = 3, out_channels: int = 1) -> None:
        super().__init__()
        self.kernel = nn.Parameter(torch.randn(out_channels, in_channels, 5, 5))

    def constrained_kernel(self) -> torch.Tensor:
        mask = torch.ones_like(self.kernel)
        mask[:, :, 2, 2] = 0
        masked = self.kernel * mask
        sums = masked.sum(dim=(2, 3), keepdim=True)
        signs = torch.where(torch.sign(sums) == 0, torch.ones_like(sums), torch.sign(sums))
        normalised = masked / (signs * sums.abs().clamp(min=1e-5))
        center = torch.zeros_like(self.kernel)
        center[:, :, 2, 2] = -1
        return normalised + center

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        kernel = self.constrained_kernel().to(dtype=inputs.dtype, device=inputs.device)
        return functional.conv2d(inputs, kernel, stride=1, padding=2)


class RealFFT2D(nn.Module):
    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        device_type = inputs.device.type if inputs.is_cuda else "cpu"
        with torch.amp.autocast(device_type=device_type, enabled=False):
            spectrum = torch.fft.fftshift(
                torch.fft.fft2(inputs.float(), norm="ortho"), dim=(-2, -1)
            )
            magnitude = torch.log1p(torch.clamp(torch.abs(spectrum), min=1e-7))
            phase = torch.angle(spectrum) / torch.pi
            output = torch.cat(
                [
                    torch.nan_to_num(magnitude, nan=0, posinf=10, neginf=-10),
                    torch.nan_to_num(phase, nan=0, posinf=1, neginf=-1),
                ],
                dim=1,
            )
        return output.to(dtype=inputs.dtype, device=inputs.device)


class HybridDeepfakeDetector(nn.Module):
    def __init__(self, *, dropout: float = 0.3) -> None:
        super().__init__()
        convnext = models.convnext_small(weights=None)
        self.spatial_backbone = convnext.features
        self.spatial_norm = convnext.classifier[0]
        self.spatial_pool = nn.AdaptiveAvgPool2d(1)
        self.spatial_fc = nn.Sequential(nn.Linear(768, 512), nn.ReLU())
        self.register_buffer("imagenet_mean", torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))
        self.register_buffer("imagenet_std", torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1))

        self.srm = SRMConv2d()
        self.bayar = BayarConv2d()
        self.fft = RealFFT2D()
        self.freq_conv = nn.Sequential(
            nn.Conv2d(20, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
        )
        self.freq_fc = nn.Sequential(nn.Linear(128, 512), nn.ReLU())
        self.gate_fc = nn.Sequential(nn.Linear(1024, 512), nn.Sigmoid())
        self.classifier = nn.Sequential(
            nn.Linear(1024, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 1),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        mean = self.imagenet_mean.to(dtype=inputs.dtype, device=inputs.device)
        std = self.imagenet_std.to(dtype=inputs.dtype, device=inputs.device)
        spatial_maps = self.spatial_norm(self.spatial_backbone((inputs - mean) / std))
        spatial = self.spatial_fc(self.spatial_pool(spatial_maps).flatten(1))

        residuals = torch.cat([self.srm(inputs), self.bayar(inputs)], dim=1)
        frequency_maps = self.fft(residuals)
        frequency = self.freq_fc(self.freq_conv(frequency_maps).flatten(1))
        gate = self.gate_fc(torch.cat([spatial, frequency], dim=1))
        fused = torch.cat([spatial * (1 - gate), frequency * gate], dim=1)
        return self.classifier(fused)
