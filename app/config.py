import os
import platform

class Settings:
    # Pin configurations (BCM numbering)
    GPIO_16_PIN: int = int(os.getenv("GPIO_16_PIN", "16"))
    MOTOR_PWM_PIN: int = int(os.getenv("MOTOR_PWM_PIN", "5"))
    DHT11_PIN: int = int(os.getenv("DHT11_PIN", "26"))

    # PWM settings
    MOTOR_PWM_FREQ: int = int(os.getenv("MOTOR_PWM_FREQ", "1000"))

    # I2C / LCD settings
    I2C_BUS: int = int(os.getenv("I2C_BUS", "1"))
    LCD_ADDRESS_CANDIDATES: list[int] = [0x27, 0x3F]
    LCD_DEFAULT_TEXT_LINE1: str = os.getenv("LCD_DEFAULT_TEXT_LINE1", "Hello World")
    LCD_DEFAULT_TEXT_LINE2: str = os.getenv("LCD_DEFAULT_TEXT_LINE2", "RPi Gateway")
    LCD_UPDATE_INTERVAL_SEC: float = float(os.getenv("LCD_UPDATE_INTERVAL_SEC", "2.5"))
    LCD_TEMP_MIN_OFFSET: float = float(os.getenv("LCD_TEMP_MIN_OFFSET", "8.0"))

    # USB Camera settings
    CAMERA_INDEX: int = int(os.getenv("CAMERA_INDEX", "0"))
    CAMERA_WIDTH: int = int(os.getenv("CAMERA_WIDTH", "640"))
    CAMERA_HEIGHT: int = int(os.getenv("CAMERA_HEIGHT", "480"))

    # Mock hardware settings
    # Automatically enabled on non-Linux or if MOCK_HARDWARE=true
    MOCK_HARDWARE: bool = (
        os.getenv("MOCK_HARDWARE", "false").lower() in ("true", "1", "yes")
        or platform.system() != "Linux"
    )

settings = Settings()
