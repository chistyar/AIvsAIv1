from abc import ABC, abstractmethod
from typing import Tuple

class BaseSwitch(ABC):
    @abstractmethod
    def set_state(self, state: int) -> int:
        """Set state: 0 (off) or 1 (on). Returns current state."""
        pass

    @abstractmethod
    def get_state(self) -> int:
        """Get current state: 0 or 1."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Release resources."""
        pass


class BaseMotor(ABC):
    @abstractmethod
    def set_speed(self, speed: int) -> int:
        """Set motor PWM speed in range 0-255. 0 means off. Returns speed."""
        pass

    @abstractmethod
    def get_speed(self) -> int:
        """Get current motor speed (0-255)."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Release resources."""
        pass


class BaseDHTSensor(ABC):
    @abstractmethod
    def read(self) -> Tuple[float, float]:
        """Read sensor data on-demand. Returns (temperature_celsius, humidity_percent)."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Release resources."""
        pass


class BaseLCD(ABC):
    @abstractmethod
    def init_display(self) -> bool:
        """Initialize the I2C LCD display. Returns True if successful."""
        pass

    @abstractmethod
    def display_text(self, line1: str = "", line2: str = "") -> None:
        """Display text on lines 1 and 2."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear LCD screen."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Release resources."""
        pass


class BaseCamera(ABC):
    @abstractmethod
    def capture_frame(self) -> Tuple[bytes, int, int]:
        """Capture a single frame as JPEG. Returns (jpeg_bytes, width, height)."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Release camera resources."""
        pass
