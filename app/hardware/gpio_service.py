import logging
from typing import Optional
from app.hardware.base import BaseSwitch, BaseMotor

logger = logging.getLogger("hardware.gpio")

class RPiSwitch(BaseSwitch):
    def __init__(self, pin: int = 16):
        self.pin = pin
        self._device = None
        try:
            from gpiozero import DigitalOutputDevice
            # Initial value False (0) for NPN transistor: off by default
            self._device = DigitalOutputDevice(pin=pin, active_high=True, initial_value=False)
            logger.info(f"RPiSwitch initialized on GPIO {pin} (initial state: 0 / OFF)")
        except Exception as e:
            logger.error(f"Failed to initialize GPIO {pin} with gpiozero: {e}")
            raise

    def set_state(self, state: int) -> int:
        if self._device is None:
            raise RuntimeError("Switch device is not initialized")
        val = 1 if state else 0
        if val == 1:
            self._device.on()
        else:
            self._device.off()
        logger.info(f"Switch on GPIO {self.pin} set to {val}")
        return val

    def get_state(self) -> int:
        if self._device is None:
            raise RuntimeError("Switch device is not initialized")
        return 1 if self._device.value else 0

    def cleanup(self) -> None:
        if self._device:
            try:
                self._device.off()
                self._device.close()
                logger.info(f"RPiSwitch on GPIO {self.pin} closed")
            except Exception as e:
                logger.warning(f"Error closing switch on GPIO {self.pin}: {e}")


class RPiMotor(BaseMotor):
    def __init__(self, pin: int = 5, freq: int = 1000):
        self.pin = pin
        self.freq = freq
        self._speed = 0
        self._device = None
        try:
            from gpiozero import PWMOutputDevice
            # Initial value 0.0 (duty cycle = 0, off)
            self._device = PWMOutputDevice(pin=pin, frequency=freq, initial_value=0.0)
            logger.info(f"RPiMotor initialized on GPIO {pin} (PWM freq: {freq}Hz, default speed: 0)")
        except Exception as e:
            logger.error(f"Failed to initialize PWM on GPIO {pin}: {e}")
            raise

    def set_speed(self, speed: int) -> int:
        if self._device is None:
            raise RuntimeError("Motor PWM device is not initialized")
        clamped = max(0, min(255, speed))
        self._speed = clamped
        # Map 0-255 to 0.0-1.0
        duty_cycle = clamped / 255.0
        self._device.value = duty_cycle
        logger.info(f"Motor on GPIO {self.pin} set to speed {clamped}/255 (duty cycle: {duty_cycle:.2f})")
        return self._speed

    def get_speed(self) -> int:
        return self._speed

    def cleanup(self) -> None:
        if self._device:
            try:
                self._device.off()
                self._device.close()
                logger.info(f"RPiMotor on GPIO {self.pin} closed")
            except Exception as e:
                logger.warning(f"Error closing motor on GPIO {self.pin}: {e}")
