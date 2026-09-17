import logging
import time
from typing import Tuple
from app.hardware.base import BaseDHTSensor

logger = logging.getLogger("hardware.dht")

class RPiDHTSensor(BaseDHTSensor):
    def __init__(self, pin: int = 26):
        self.pin = pin
        self._device = None
        try:
            import board
            import adafruit_dht
            # Get board pin dynamically e.g. board.D26
            pin_attr = f"D{pin}"
            if not hasattr(board, pin_attr):
                raise ValueError(f"Pin {pin_attr} not found on board")
            board_pin = getattr(board, pin_attr)
            # use_pulseio=False is required for reliable operation on Linux / Raspberry Pi OS
            self._device = adafruit_dht.DHT11(board_pin, use_pulseio=False)
            logger.info(f"RPiDHTSensor initialized on GPIO {pin} (DHT11)")
        except Exception as e:
            logger.error(f"Failed to initialize DHT11 on GPIO {pin}: {e}")
            raise

    def read(self) -> Tuple[float, float]:
        if self._device is None:
            raise RuntimeError("DHT11 sensor is not initialized")

        # Retry up to 3 times because DHT11 is single-wire timing-sensitive on Linux
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                temp = float(self._device.temperature)
                humidity = float(self._device.humidity)
                if temp is not None and humidity is not None:
                    logger.info(f"DHT11 read success on attempt {attempt}: {temp}°C, {humidity}%")
                    return temp, humidity
            except RuntimeError as e:
                # Common transient errors: Checksum error, timing error
                logger.debug(f"DHT11 read attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    time.sleep(0.5)
            except Exception as e:
                logger.error(f"Unexpected DHT11 error: {e}")
                raise

        raise RuntimeError("Failed to read data from DHT11 sensor after 3 attempts")

    def cleanup(self) -> None:
        if self._device:
            try:
                self._device.exit()
                logger.info(f"DHT11 on GPIO {self.pin} exited")
            except Exception as e:
                logger.warning(f"Error releasing DHT11 device: {e}")
