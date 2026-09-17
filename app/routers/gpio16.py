from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.hardware.manager import hardware_manager
from app.config import settings

router = APIRouter(prefix="/api/gpio16", tags=["GPIO 16 Switch (NPN)"])

class SwitchSetRequest(BaseModel):
    state: int = Field(
        ...,
        ge=0,
        le=1,
        description="Desired state for GPIO 16 NPN transistor: 0 = OFF (LOW), 1 = ON (HIGH)"
    )

class SwitchResponse(BaseModel):
    pin: int = Field(default=settings.GPIO_16_PIN, description="BCM GPIO pin number")
    state: int = Field(..., description="Current state: 0 (OFF) or 1 (ON)")
    is_on: bool = Field(..., description="Boolean flag: True if active/turned on")
    message: str = Field(..., description="Human-readable status summary")

@router.get(
    "",
    response_model=SwitchResponse,
    summary="Get current state of GPIO 16",
    description="Returns the current binary state (0=off, 1=on) of the NPN transistor connected to GPIO 16."
)
def get_gpio16_state():
    try:
        val = hardware_manager.switch.get_state()
        return SwitchResponse(
            pin=settings.GPIO_16_PIN,
            state=val,
            is_on=(val == 1),
            message=f"GPIO 16 is currently {'ON' if val == 1 else 'OFF'}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read GPIO 16 state: {str(e)}"
        )

@router.post(
    "",
    response_model=SwitchResponse,
    summary="Set state of GPIO 16",
    description="Turns GPIO 16 NPN transistor ON (1) or OFF (0)."
)
def set_gpio16_state(request: SwitchSetRequest):
    try:
        val = hardware_manager.switch.set_state(request.state)
        return SwitchResponse(
            pin=settings.GPIO_16_PIN,
            state=val,
            is_on=(val == 1),
            message=f"GPIO 16 switched to {'ON' if val == 1 else 'OFF'}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set GPIO 16 state: {str(e)}"
        )

@router.post(
    "/on",
    response_model=SwitchResponse,
    summary="Turn ON GPIO 16",
    description="Shortcut endpoint to turn ON the NPN transistor on GPIO 16 (sets state to 1)."
)
def turn_gpio16_on():
    return set_gpio16_state(SwitchSetRequest(state=1))

@router.post(
    "/off",
    response_model=SwitchResponse,
    summary="Turn OFF GPIO 16",
    description="Shortcut endpoint to turn OFF the NPN transistor on GPIO 16 (sets state to 0)."
)
def turn_gpio16_off():
    return set_gpio16_state(SwitchSetRequest(state=0))
