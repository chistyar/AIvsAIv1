import io
import time
import logging
from typing import Tuple
from app.config import settings
from app.hardware.base import BaseCamera

logger = logging.getLogger("hardware.camera")

class MockCamera(BaseCamera):
    """Generates synthetic camera frames for testing and development."""

    def __init__(self, width: int = None, height: int = None):
        self.width = width or settings.CAMERA_WIDTH
        self.height = height or settings.CAMERA_HEIGHT
        logger.info(f"[MOCK] Camera initialized ({self.width}x{self.height})")

    def capture_frame(self) -> Tuple[bytes, int, int]:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (self.width, self.height), color=(28, 33, 40))
        draw = ImageDraw.Draw(img)

        # Draw tech border and grid
        draw.rectangle([(10, 10), (self.width - 10, self.height - 10)], outline=(88, 166, 255), width=2)
        draw.line([(0, self.height // 2), (self.width, self.height // 2)], fill=(45, 51, 59), width=1)
        draw.line([(self.width // 2, 0), (self.width // 2, self.height)], fill=(45, 51, 59), width=1)

        # Text information
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        draw.text((25, 25), "USB CAMERA STREAM [MOCK / SIMULATED]", fill=(255, 255, 255))
        draw.text((25, 55), f"Resolution: {self.width}x{self.height}", fill=(139, 148, 158))
        draw.text((25, 80), f"Timestamp: {now_str}", fill=(139, 148, 158))
        draw.text((25, 105), f"Device: /dev/video{settings.CAMERA_INDEX}", fill=(139, 148, 158))

        # Center target
        cx, cy = self.width // 2, self.height // 2
        draw.ellipse([(cx - 40, cy - 40), (cx + 40, cy + 40)], outline=(63, 185, 80), width=2)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        jpeg_bytes = buffer.getvalue()
        logger.info(f"[MOCK] Captured camera frame ({len(jpeg_bytes)} bytes)")
        return jpeg_bytes, self.width, self.height

    def cleanup(self) -> None:
        logger.info("[MOCK] Camera cleaned up")


class RPiUSBCamera(BaseCamera):
    """Captures real frames from a USB webcam using OpenCV / V4L2."""

    def __init__(self, device_index: int = None, width: int = None, height: int = None):
        self.device_index = device_index if device_index is not None else settings.CAMERA_INDEX
        self.width = width or settings.CAMERA_WIDTH
        self.height = height or settings.CAMERA_HEIGHT
        self.mock_fallback = MockCamera(width=self.width, height=self.height)
        logger.info(f"RPiUSBCamera initialized for device index {self.device_index}")

    def capture_frame(self) -> Tuple[bytes, int, int]:
        try:
            import cv2
        except ImportError:
            logger.warning("OpenCV (cv2) is not installed. Falling back to mock camera.")
            return self.mock_fallback.capture_frame()

        # Open video capture device
        # Using cv2.CAP_V4L2 on Linux ensures optimal webcam compatibility
        cap = cv2.VideoCapture(self.device_index)
        if not cap.isOpened():
            logger.warning(f"Could not open video device /dev/video{self.device_index}. Using mock frame.")
            return self.mock_fallback.capture_frame()

        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

            # Skip initial frames to allow auto-exposure/auto-white-balance to settle
            for _ in range(3):
                ret, frame = cap.read()
                if not ret:
                    break

            if not ret or frame is None:
                logger.warning("Failed to grab valid frame from webcam. Using mock frame.")
                return self.mock_fallback.capture_frame()

            actual_h, actual_w = frame.shape[:2]

            # Encode as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
            success, buffer = cv2.imencode(".jpg", frame, encode_param)
            if not success:
                logger.warning("JPEG encoding failed. Using mock frame.")
                return self.mock_fallback.capture_frame()

            jpeg_bytes = buffer.tobytes()
            logger.info(f"Successfully captured camera frame ({actual_w}x{actual_h}, {len(jpeg_bytes)} bytes)")
            return jpeg_bytes, actual_w, actual_h
        finally:
            cap.release()

    def cleanup(self) -> None:
        logger.info("RPiUSBCamera cleaned up")
