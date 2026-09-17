import logging
from typing import Tuple
from app.hardware.base import BaseSwitch, BaseMotor, BaseDHTSensor, BaseLCD

logger = logging.getLogger("hardware.mock")

class MockSwitch(BaseSwitch):
    def __init__(self, pin: int = 16):
        self.pin = pin
        self.state = 0
        logger.info(f"[MOCK] Switch initialized on GPIO {pin}, default state = 0 (OFF)")

    def set_state(self, state: int) -> int:
        self.state = 1 if state else 0
        logger.info(f"[MOCK] Switch on GPIO {self.pin} set to {self.state} ({'ON' if self.state == 1 else 'OFF'})")
        return self.state

    def get_state(self) -> int:
        return self.state

    def cleanup(self) -> None:
        self.state = 0
        logger.info(f"[MOCK] Switch on GPIO {self.pin} cleaned up")


class MockMotor(BaseMotor):
    def __init__(self, pin: int = 5, freq: int = 1000):
        self.pin = pin
        self.freq = freq
        self.speed = 0
        logger.info(f"[MOCK] Motor initialized on GPIO {pin} (PWM freq: {freq}Hz), default speed = 0")

    def set_speed(self, speed: int) -> int:
        clamped = max(0, min(255, speed))
        self.speed = clamped
        duty = (clamped / 255.0) * 100.0
        logger.info(f"[MOCK] Motor PWM on GPIO {self.pin} set to speed {self.speed}/255 (duty cycle: {duty:.1f}%)")
        return self.speed

    def get_speed(self) -> int:
        return self.speed

    def cleanup(self) -> None:
        self.speed = 0
        logger.info(f"[MOCK] Motor on GPIO {self.pin} stopped and cleaned up")


class MockDHTSensor(BaseDHTSensor):
    def __init__(self, pin: int = 26):
        self.pin = pin
        self.simulated_temp = 23.5
        self.simulated_humidity = 48.0
        logger.info(f"[MOCK] DHT11 sensor initialized on GPIO {pin}")

    def read(self) -> Tuple[float, float]:
        logger.info(f"[MOCK] Read DHT11 on GPIO {self.pin} -> {self.simulated_temp}°C, {self.simulated_humidity}%")
        return self.simulated_temp, self.simulated_humidity

    def cleanup(self) -> None:
        logger.info(f"[MOCK] DHT11 sensor on GPIO {self.pin} cleaned up")


class MockLCD(BaseLCD):
    def __init__(self, addresses: list[int] = None):
        self.addresses = addresses or [0x27, 0x3F]
        self.line1 = ""
        self.line2 = ""
        logger.info(f"[MOCK] LCD1602 initialized on I2C addresses {self.addresses}")

    def init_display(self) -> bool:
        logger.info("[MOCK] LCD1602 display initialized successfully")
        return True

    def display_text(self, line1: str = "", line2: str = "") -> None:
        self.line1 = line1[:16]
        self.line2 = line2[:16]
        border = "+" + "-" * 16 + "+"
        logger.info(f"[MOCK LCD OUTPUT]\n{border}\n|{self.line1:<16}|\n|{self.line2:<16}|\n{border}")

    def clear(self) -> None:
        self.line1 = ""
        self.line2 = ""
        logger.info("[MOCK] LCD screen cleared")

    def cleanup(self) -> None:
        logger.info("[MOCK] LCD cleaned up")
