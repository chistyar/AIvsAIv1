import base64
import time
from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field
from app.hardware.manager import hardware_manager
from app.config import settings

router = APIRouter(prefix="/api/camera", tags=["USB Camera"])

class CameraBase64Response(BaseModel):
    image_base64: str = Field(
        ...,
        description="Base64-encoded JPEG image string prefixed with 'data:image/jpeg;base64,'. Ready for multimodal LLM vision input."
    )
    format: str = Field(default="jpeg", description="Image encoding format")
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    size_bytes: int = Field(..., description="Binary size of the JPEG image in bytes")
    timestamp: float = Field(default_factory=time.time, description="Capture timestamp")
    device_index: int = Field(default=settings.CAMERA_INDEX, description="USB camera device index")
    status: str = Field(default="ok", description="Status of capture: 'ok' or 'simulated'")

@router.get(
    "/capture",
    summary="Capture image from USB webcam (Binary JPEG)",
    description=(
        "Captures a single frame from the connected USB webcam and returns raw binary JPEG image data. "
        "Ideal for browser viewing, direct download, or curl."
    ),
    responses={
        200: {
            "content": {"image/jpeg": {}},
            "description": "Raw JPEG image file"
        }
    }
)
def capture_image_jpeg():
    try:
        jpeg_bytes, width, height = hardware_manager.camera.capture_frame()
        return Response(content=jpeg_bytes, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Camera capture failed: {str(e)}"
        )

@router.get(
    "/base64",
    response_model=CameraBase64Response,
    summary="Capture image from USB webcam for AI Agent (Base64 JSON)",
    description=(
        "Captures a single frame from the connected USB webcam and returns it as a base64-encoded data URL in JSON format. "
        "Designed specifically for AI Agent tool use (OpenAI GPT-4o, Gemini 1.5/2.0, Claude 3.5 Sonnet)."
    )
)
def capture_image_base64():
    try:
        jpeg_bytes, width, height = hardware_manager.camera.capture_frame()
        b64_str = base64.b64encode(jpeg_bytes).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{b64_str}"

        return CameraBase64Response(
            image_base64=data_url,
            format="jpeg",
            width=width,
            height=height,
            size_bytes=len(jpeg_bytes),
            timestamp=time.time(),
            device_index=settings.CAMERA_INDEX,
            status="simulated" if hardware_manager.is_mock else "ok"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Camera capture failed: {str(e)}"
        )
