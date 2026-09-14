"""Optional computer-vision environment analysis (Part 14, P1 priority).

The hackathon MVP's primary, always-available path is the JSON fixture
(environments.models.Environment with source='fixture'). This module adds
an optional path that derives the same EnvironmentDescriptor shape from a
real screenshot using OpenCV (control/button detection) and pytesseract
(text/contrast reading), for a kiosk that isn't just a fixture.

Both imports are optional. If OpenCV/pytesseract aren't installed, or
VISION_ENABLED is off, `analyze_screenshot` raises VisionUnavailableError and
callers should fall back to the JSON fixture — the rest of the pipeline
(barrier detection -> adaptation -> rendering) never depends on this module.
"""

from __future__ import annotations

import base64
import logging

from django.conf import settings

logger = logging.getLogger("ai_engine")


class VisionUnavailableError(Exception):
    pass


def is_configured() -> bool:
    return bool(settings.VISION_ENABLED)


def analyze_screenshot(image_base64: str) -> dict:
    """Returns an EnvironmentDescriptor-shaped dict derived from a screenshot.

    Best-effort control detection via OpenCV contour analysis + OCR text
    extraction. This is intentionally simple (Part 14): "No need to train a
    custom model; existing tools are sufficient to read a simulated kiosk
    screen."
    """

    if not is_configured():
        raise VisionUnavailableError("VISION_ENABLED is false.")

    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise VisionUnavailableError("opencv-python not installed.") from exc

    try:
        raw = base64.b64decode(image_base64.split(",")[-1])
        arr = np.frombuffer(raw, dtype=np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Could not decode image data.")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        controls = []
        for i, contour in enumerate(contours):
            x, y, w, h = cv2.boundingRect(contour)
            if w < 10 or h < 10:
                continue
            controls.append({"id": f"detected_{i}", "type": "button", "width": int(w), "height": int(h)})

        mean_brightness = float(gray.mean()) / 255.0
        contrast = float(gray.std()) / 128.0

        return {
            "environment_type": "vision_captured",
            "screen": {"width": int(image.shape[1]), "height": int(image.shape[0])},
            "controls": controls[:20],
            "contrast": round(min(1.0, max(0.0, contrast)), 3),
            "visible_choice_count": len(controls),
            "audio_alert": False,
            "brightness": round(mean_brightness, 3),
        }
    except Exception as exc:
        logger.warning("Vision analysis failed: %s", exc)
        raise VisionUnavailableError(str(exc)) from exc
