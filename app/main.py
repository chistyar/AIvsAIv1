import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.hardware.manager import hardware_manager
from app.services.lcd_worker import lcd_worker
from app.routers import gpio16, motor, sensor, camera

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Raspberry Pi Hardware API...")
    logger.info(f"Hardware Mode: {'MOCK' if hardware_manager.is_mock else 'REAL RASPBERRY PI 4'}")

    # Start background LCD update loop (displays realistic fluctuating temperature)
    lcd_worker.start()

    yield

    # Shutdown
    logger.info("Shutting down Raspberry Pi Hardware API...")
    await lcd_worker.stop()
    hardware_manager.cleanup()

app = FastAPI(
    title="Raspberry Pi 4 Hardware Gateway",
    description=(
        "Microservice API for Raspberry Pi 4 hardware control. "
        "Provides endpoints for digital switching on GPIO 16, motor PWM control on GPIO 5, "
        "on-demand DHT11 temperature/humidity readings on GPIO 26, USB webcam image capture, "
        "and dynamic thermal display on I2C LCD 1602. "
        "Fully compatible with AI Agent Function Calling via OpenAPI schema."
    ),
    version="1.1.0",
    lifespan=lifespan
)

# Enable CORS for external dashboard or frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(gpio16.router)
app.include_router(motor.router)
app.include_router(sensor.router)
app.include_router(camera.router)

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint to verify service and hardware status."""
    return {
        "status": "healthy",
        "hardware_mode": "mock" if hardware_manager.is_mock else "physical",
        "pins": {
            "switch_npn": settings.GPIO_16_PIN,
            "motor_pwm": settings.MOTOR_PWM_PIN,
            "dht11_sensor": settings.DHT11_PIN,
            "i2c_bus": settings.I2C_BUS,
            "camera_device": f"/dev/video{settings.CAMERA_INDEX}"
        }
    }

@app.get("/", tags=["System"])
def root():
    """Service overview and quick documentation links."""
    return {
        "service": "Raspberry Pi 4 Hardware Gateway",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
        "endpoints": {
            "gpio16_switch": "/api/gpio16",
            "motor_pwm": "/api/motor",
            "dht11_sensor": "/api/sensor/dht11",
            "camera_capture": "/api/camera/capture",
            "camera_base64": "/api/camera/base64",
            "health": "/health"
        }
    }
