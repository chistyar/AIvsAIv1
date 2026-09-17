from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.hardware.manager import hardware_manager
from app.config import settings

router = APIRouter(prefix="/api/motor", tags=["Motor PWM (GPIO 5)"])

class MotorSpeedRequest(BaseModel):
    speed: int = Field(
        ...,
        ge=0,
        le=255,
        description="PWM speed value from 0 (completely OFF) to 255 (maximum speed 100% duty cycle)"
    )

class MotorResponse(BaseModel):
    pin: int = Field(default=settings.MOTOR_PWM_PIN, description="BCM GPIO pin number for motor PWM")
    speed: int = Field(..., description="Current speed value (0-255)")
    duty_cycle_percent: float = Field(..., description="Calculated PWM duty cycle percentage (0.0% to 100.0%)")
    is_running: bool = Field(..., description="True if speed > 0")
    message: str = Field(..., description="Status summary")

@router.get(
    "",
    response_model=MotorResponse,
    summary="Get current motor speed",
    description="Returns the current PWM speed setting (0 to 255) for the motor connected to GPIO 5."
)
def get_motor_speed():
    try:
        speed = hardware_manager.motor.get_speed()
        duty = round((speed / 255.0) * 100.0, 1)
        return MotorResponse(
            pin=settings.MOTOR_PWM_PIN,
            speed=speed,
            duty_cycle_percent=duty,
            is_running=(speed > 0),
            message=f"Motor speed is {speed}/255 ({duty}%)"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read motor speed: {str(e)}"
        )

@router.post(
    "",
    response_model=MotorResponse,
    summary="Set motor PWM speed",
    description="Adjusts the motor PWM output on GPIO 5. Accepts speed in range 0-255 (0 = off)."
)
def set_motor_speed(request: MotorSpeedRequest):
    try:
        speed = hardware_manager.motor.set_speed(request.speed)
        duty = round((speed / 255.0) * 100.0, 1)
        return MotorResponse(
            pin=settings.MOTOR_PWM_PIN,
            speed=speed,
            duty_cycle_percent=duty,
            is_running=(speed > 0),
            message=f"Motor speed set to {speed}/255 ({duty}%)"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set motor PWM: {str(e)}"
        )

@router.post(
    "/stop",
    response_model=MotorResponse,
    summary="Stop motor",
    description="Shortcut endpoint to immediately stop the motor (sets PWM speed to 0)."
)
def stop_motor():
    return set_motor_speed(MotorSpeedRequest(speed=0))
