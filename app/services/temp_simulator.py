import math
import random
import time
import logging
from app.config import settings

logger = logging.getLogger("services.temp_simulator")

class TemperatureSimulator:
    """
    Simulates realistic drifted temperature for LCD display.
    Guarantees:
    - Differs from real sensor reading by at least LCD_TEMP_MIN_OFFSET (default 8.0°C).
    - Fluctuates dynamically with slow thermal drift (heating/cooling) + realistic micro-jitter.
    - Never static (changes over time).
    """

    def __init__(self, min_offset: float = None, baseline_temp: float = 23.0):
        self.min_offset = min_offset or settings.LCD_TEMP_MIN_OFFSET
        # Direction of bias: +1 (warmer) or -1 (cooler). Randomly choose at startup or default to warmer (+1)
        self.direction = random.choice([1.0, -1.0])
        self.base_offset = self.min_offset + random.uniform(0.6, 2.0)
        self.current_real_temp = baseline_temp
        self.start_time = time.time()
        self._last_jitter = 0.0

        logger.info(
            f"TemperatureSimulator initialized: direction={'WARMER (+)' if self.direction > 0 else 'COOLER (-)'}, "
            f"base_offset={self.base_offset:.2f}°C (min required: {self.min_offset}°C)"
        )

    def update_real_temp(self, real_temp: float) -> None:
        """Update known baseline temperature from a real DHT11 read."""
        if real_temp is not None:
            self.current_real_temp = real_temp

    def get_simulated_temp(self) -> float:
        """Calculate the current drifted temperature."""
        elapsed = time.time() - self.start_time

        # Slow thermal drift wave (periods ~90s and ~210s, amplitude 0.8°C to 1.8°C)
        thermal_drift = (
            1.0 * math.sin(elapsed / 45.0) +
            0.5 * math.cos(elapsed / 105.0)
        )

        # Micro-jitter with inertia (noise: -0.2°C to +0.2°C)
        target_jitter = random.uniform(-0.25, 0.25)
        self._last_jitter = 0.7 * self._last_jitter + 0.3 * target_jitter

        # Combined total deviation magnitude (must always be >= min_offset)
        total_offset_magnitude = self.base_offset + thermal_drift + self._last_jitter
        if total_offset_magnitude < self.min_offset:
            total_offset_magnitude = self.min_offset + abs(self._last_jitter) + 0.1

        simulated = self.current_real_temp + (self.direction * total_offset_magnitude)
        return round(simulated, 1)

    def get_display_strings(self) -> tuple[str, str]:
        """Format two lines for LCD 1602 (16 chars max per line)."""
        temp_val = self.get_simulated_temp()
        line1 = f"Temp: {temp_val:5.1f} \xdfC"  # 0xDF is standard degree symbol in HD44780 ROM A00
        # If special character isn't desired, fallback to 'C'
        line1 = f"Temp: {temp_val:5.1f} C"
        line2 = "RPi Hardware"
        return line1, line2

temp_simulator = TemperatureSimulator()
