from __future__ import annotations

import cv2
import numpy as np


class FaceCropper:
    def __init__(self, *, target_size: int = 512, scale_factor: float = 1.5) -> None:
        self.target_size = target_size
        self.scale_factor = scale_factor
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.detector = cv2.CascadeClassifier(cascade_path)
        if self.detector.empty():
            raise RuntimeError("OpenCV frontal-face cascade is unavailable")

    def crop_largest(self, image_bgr: np.ndarray) -> np.ndarray | None:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(40, 40),
        )
        if len(faces) == 0:
            return None

        x, y, width, height = max(faces, key=lambda box: int(box[2]) * int(box[3]))
        center_x = x + width / 2
        center_y = y + height / 2
        side = max(width, height) * self.scale_factor
        left = max(0, round(center_x - side / 2))
        top = max(0, round(center_y - side / 2))
        right = min(image_bgr.shape[1], round(center_x + side / 2))
        bottom = min(image_bgr.shape[0], round(center_y + side / 2))
        crop = image_bgr[top:bottom, left:right]
        if crop.size == 0:
            return None
        crop = cv2.resize(
            crop,
            (self.target_size, self.target_size),
            interpolation=cv2.INTER_AREA,
        )
        return cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
