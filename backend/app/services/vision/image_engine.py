"""RoadVision AI — Image Processing & Validation Engine (S5-M1).

Implements TDD v1.1 §7 and PRD v1.1 image processing:
- Byte validation & Pillow format/dimension verification
- Safe OpenCV BGR decoding
- Non-destructive annotation generation
- Structured result construction
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image

from .annotate import annotate_image, encode_image_bytes, save_annotated_image
from .config import (
    ALLOWED_IMAGE_EXTENSIONS,
    DEFAULT_CONFIDENCE,
    MAX_IMAGE_BYTES,
    MAX_IMAGE_DIMENSION,
    MAX_IMAGE_PIXELS,
)
from .errors import (
    ImageDecodeError,
    ImageDimensionExceededError,
    ImageSizeExceededError,
    ImageValidationError,
    UnsupportedImageFormatError,
)
from .model_manager import ModelManager
from .types import DetectionResult, VisionInspectionResult


def validate_image_payload(
    raw_bytes: bytes,
    filename: Optional[str] = None,
) -> Tuple[int, int, str]:
    """Validate image raw bytes and metadata against operational limits.

    Returns:
        Tuple of (width, height, format_name).
    """
    byte_count = len(raw_bytes)
    if byte_count == 0:
        raise ImageValidationError("Received empty image payload (0 bytes).")

    if byte_count > MAX_IMAGE_BYTES:
        raise ImageSizeExceededError(byte_count, MAX_IMAGE_BYTES)

    if filename:
        ext = Path(filename).suffix.lower()
        if ext and ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise UnsupportedImageFormatError(ext, ALLOWED_IMAGE_EXTENSIONS)

    # Validate using Pillow
    try:
        # Prevent DecompressionBomb attacks
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        with Image.open(io.BytesIO(raw_bytes)) as pil_img:
            img_format = (pil_img.format or "").upper()
            if img_format not in ("JPEG", "JPG", "PNG"):
                raise ImageValidationError(
                    f"Image format '{img_format}' is not supported. Must be JPEG or PNG."
                )
            width, height = pil_img.size
            if width <= 0 or height <= 0:
                raise ImageValidationError(f"Invalid image dimensions: {width}x{height}")
            if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                raise ImageDimensionExceededError(width, height, MAX_IMAGE_DIMENSION)

            total_pixels = width * height
            if total_pixels > MAX_IMAGE_PIXELS:
                raise ImageDimensionExceededError(width, height, MAX_IMAGE_DIMENSION)

            return width, height, img_format
    except (ImageSizeExceededError, ImageDimensionExceededError, UnsupportedImageFormatError):
        raise
    except Exception as e:
        raise ImageDecodeError(f"Pillow validation failed: {e}") from e


def decode_image_bytes(raw_bytes: bytes) -> np.ndarray:
    """Decode raw bytes into an OpenCV BGR numpy array."""
    np_buf = np.frombuffer(raw_bytes, dtype=np.uint8)
    image = cv2.imdecode(np_buf, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise ImageDecodeError("OpenCV failed to decode image buffer.")
    return image


class ImageEngine:
    """Processes still road images for damage detection and annotation."""

    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager

    def process_image(
        self,
        image_input: Union[bytes, Path, str, np.ndarray],
        conf: Union[float, str] = DEFAULT_CONFIDENCE,
        filename: Optional[str] = None,
        annotate: bool = True,
        output_path: Optional[Union[str, Path]] = None,
    ) -> VisionInspectionResult:
        """Run full validation, detection, and annotation pipeline on an image.

        Args:
            image_input: Raw image bytes, file path, or np.ndarray.
            conf: Confidence threshold as a float [0.10, 0.90] or mode string
                ('balanced' -> 0.25, 'high_recall' -> 0.15).
            filename: Original filename (used for extension checking if bytes provided).
            annotate: Whether to generate visual bounding box annotations.
            output_path: Optional disk path to save the annotated output.

        Returns:
            VisionInspectionResult containing detections, metadata, and optional annotated output.
        """
        # 1. Resolve image input into validated BGR matrix
        if isinstance(image_input, (str, Path)):
            path = Path(image_input)
            if not path.is_file():
                raise FileNotFoundError(f"Image file not found: {path}")
            with open(path, "rb") as f:
                raw_bytes = f.read()
            w, h, fmt = validate_image_payload(raw_bytes, filename=path.name)
            img_bgr = decode_image_bytes(raw_bytes)
        elif isinstance(image_input, bytes):
            w, h, fmt = validate_image_payload(image_input, filename=filename)
            img_bgr = decode_image_bytes(image_input)
        elif isinstance(image_input, np.ndarray):
            if image_input.size == 0:
                raise ImageValidationError("Received empty numpy array.")
            img_bgr = image_input.copy()
            h, w = img_bgr.shape[:2]
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

        # 2. Run model forward pass under inference lock
        detection_result: DetectionResult = self.model_manager.predict(
            frame=img_bgr,
            conf=conf,
        )

        # 3. Generate annotation if requested (non-destructive)
        annotated_bytes: Optional[bytes] = None
        saved_path_str: Optional[str] = None

        if annotate:
            annotated_img = annotate_image(img_bgr, detection_result)
            annotated_bytes = encode_image_bytes(annotated_img, format_ext=".jpg")

            if output_path:
                saved_path = save_annotated_image(
                    annotated_img,
                    output_path=output_path,
                    format_ext=Path(output_path).suffix or ".jpg",
                )
                saved_path_str = str(saved_path)

        # 4. Construct VisionInspectionResult
        return VisionInspectionResult(
            result=detection_result,
            annotated_image_bytes=annotated_bytes,
            annotated_output_path=saved_path_str,
            models_used=list(self.model_manager.models_used),
            device=self.model_manager.device,
            success=True,
        )

