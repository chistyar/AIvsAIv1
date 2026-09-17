import time
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.hardware.manager import hardware_manager
from app.config import settings

router = APIRouter(prefix="/api/sensor", tags=["Sensors (DHT11)"])

class DHT11Response(BaseModel):
    pin: int = Field(default=settings.DHT11_PIN, description="BCM GPIO pin connected to DHT11 data line")
    temperature_celsius: float = Field(..., description="Measured temperature in degrees Celsius")
    humidity_percent: float = Field(..., description="Measured relative humidity percentage (0-100%)")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp of the reading")
    status: str = Field(default="ok", description="Status indicator: 'ok' or 'simulated'")

@router.get(
    "/dht11",
    response_model=DHT11Response,
    summary="Read DHT11 temperature and humidity",
    description="Trigger an on-demand reading from the DHT11 sensor connected to GPIO 26."
)
def get_dht11_reading():
    try:
        temp, hum = hardware_manager.read_dht()
        return DHT11Response(
            pin=settings.DHT11_PIN,
            temperature_celsius=temp,
            humidity_percent=hum,
            status="simulated" if hardware_manager.is_mock else "ok"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"DHT11 sensor reading failed: {str(e)}"
        )
