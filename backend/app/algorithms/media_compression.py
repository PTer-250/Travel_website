"""Compression utilities for diary media files."""

from __future__ import annotations

import zlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps


@dataclass
class MediaCompressionResult:
    """Result metadata returned after attempting compression."""

    payload: bytes
    is_compressed: bool
    ratio: float
    content_type: Optional[str] = None
    filename: Optional[str] = None


class MediaCompressionService:
    """Compression helpers for diary media payloads."""

    COMPRESSION_LEVEL = 6
    MIN_COMPRESS_SIZE = 4096  # 4KB threshold for binary zlib
    MIN_COMPRESSION_RATIO = 0.95  # require >=5% savings for zlib

    IMAGE_MAX_DIMENSION = 1920
    IMAGE_MIN_RATIO = 0.97  # skip if WebP savings <3% and no resize
    IMAGE_QUALITY = 80

    def compress(
        self,
        data: bytes,
        *,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
        is_image: bool = False,
    ) -> MediaCompressionResult:
        """Compress payloads with dedicated paths for images and binary blobs."""

        if is_image:
            return self._compress_image(data, content_type, filename)

        return self._compress_binary(data, content_type, filename)

    def _compress_image(
        self,
        data: bytes,
        content_type: Optional[str],
        filename: Optional[str],
    ) -> MediaCompressionResult:
        """Re-encode images as optimized WebP while respecting orientation/size."""

        if not data:
            return MediaCompressionResult(data, False, 1.0, content_type, filename)

        try:
            with Image.open(BytesIO(data)) as image:
                # Skip animated GIF/WebP to avoid dropping frames
                if getattr(image, "is_animated", False):
                    return MediaCompressionResult(data, False, 1.0, content_type, filename)

                image = ImageOps.exif_transpose(image)
                original_size = len(data)
                resized = False

                max_dim = max(image.size)
                if max_dim > self.IMAGE_MAX_DIMENSION:
                    scale = self.IMAGE_MAX_DIMENSION / float(max_dim)
                    new_size = (
                        max(1, int(image.width * scale)),
                        max(1, int(image.height * scale)),
                    )
                    image = image.resize(new_size, Image.Resampling.LANCZOS)
                    resized = True

                # WebP keeps transparency while offering great compression
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGBA" if "A" in image.mode else "RGB")

                buffer = BytesIO()
                image.save(
                    buffer,
                    format="WEBP",
                    quality=self.IMAGE_QUALITY,
                    method=6,
                )
                payload = buffer.getvalue()
        except Exception:
            # Fallback to the original payload if Pillow cannot process it
            return MediaCompressionResult(data, False, 1.0, content_type, filename)

        ratio = len(payload) / original_size if original_size else 1.0
        if not resized and ratio > self.IMAGE_MIN_RATIO:
            return MediaCompressionResult(data, False, 1.0, content_type, filename)

        base_name = Path(filename or "media").stem or "media"
        return MediaCompressionResult(
            payload=payload,
            is_compressed=True,
            ratio=ratio,
            content_type="image/webp",
            filename=f"{base_name}.webp",
        )

    def _compress_binary(
        self,
        data: bytes,
        content_type: Optional[str],
        filename: Optional[str],
    ) -> MediaCompressionResult:
        """Fallback zlib compression for non-image payloads."""

        original_size = len(data)
        if original_size == 0 or original_size < self.MIN_COMPRESS_SIZE:
            return MediaCompressionResult(data, False, 1.0, content_type, filename)

        try:
            compressed = zlib.compress(data, self.COMPRESSION_LEVEL)
        except zlib.error:
            return MediaCompressionResult(data, False, 1.0, content_type, filename)

        compressed_size = len(compressed)
        ratio = compressed_size / original_size if original_size else 1.0

        if ratio > self.MIN_COMPRESSION_RATIO:
            return MediaCompressionResult(data, False, 1.0, content_type, filename)

        return MediaCompressionResult(compressed, True, ratio, content_type, filename)

    def decompress(self, data: bytes, is_compressed: bool) -> bytes:
        """Restore binary payloads when zlib compression was applied."""

        if not is_compressed:
            return data

        try:
            return zlib.decompress(data)
        except zlib.error:
            # When the payload has been re-encoded (e.g., optimized image),
            # the stored bytes are already in their final form.
            return data


media_compression_service = MediaCompressionService()
