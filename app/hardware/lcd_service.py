import logging
import time
from typing import Optional, List
from app.hardware.base import BaseLCD

logger = logging.getLogger("hardware.lcd")

# Commands
LCD_CLEARDISPLAY = 0x01
LCD_RETURNHOME = 0x02
LCD_ENTRYMODESET = 0x04
LCD_DISPLAYCONTROL = 0x08
LCD_CURSORSHIFT = 0x10
LCD_FUNCTIONSET = 0x20
LCD_SETCGRAMADDR = 0x40
LCD_SETDDRAMADDR = 0x80

# Flags for display entry mode
LCD_ENTRYLEFT = 0x02
LCD_ENTRYSHIFTDECREMENT = 0x00

# Flags for display on/off control
LCD_DISPLAYON = 0x04
LCD_CURSOROFF = 0x00
LCD_BLINKOFF = 0x00

# Flags for function set
LCD_4BITMODE = 0x00
LCD_2LINE = 0x08
LCD_5x8DOTS = 0x00

# Flags for backlight control
LCD_BACKLIGHT = 0x08
LCD_NOBACKLIGHT = 0x00

ENABLE_BIT = 0b00000100 # Enable bit
RS_BIT = 0b00000001     # Register select bit

class RPiLCD(BaseLCD):
    """LCD 1602 controller over I2C PCF8574 expander."""

    def __init__(self, bus_num: int = 1, address_candidates: Optional[List[int]] = None):
        self.bus_num = bus_num
        self.address_candidates = address_candidates or [0x27, 0x3F]
        self.address: Optional[int] = None
        self.bus = None
        self.backlight = LCD_BACKLIGHT

    def _find_address(self) -> Optional[int]:
        """Auto-detect I2C address of the LCD backpack."""
        for addr in self.address_candidates:
            try:
                # Try reading a byte to see if device ACKs
                self.bus.read_byte(addr)
                logger.info(f"LCD 1602 detected at I2C address 0x{addr:02X}")
                return addr
            except Exception:
                continue

        # If not found in candidates, scan bus 0x03 to 0x77
        logger.warning("LCD not found at common addresses (0x27, 0x3F). Scanning I2C bus...")
        for addr in range(0x03, 0x78):
            try:
                self.bus.read_byte(addr)
                logger.info(f"Found active I2C device at 0x{addr:02X}, using as LCD")
                return addr
            except Exception:
                continue
        return None

    def _write_nibble(self, nibble: int) -> None:
        self.bus.write_byte(self.address, nibble | self.backlight)
        # Pulse enable
        self.bus.write_byte(self.address, nibble | ENABLE_BIT | self.backlight)
        time.sleep(0.0005)
        self.bus.write_byte(self.address, (nibble & ~ENABLE_BIT) | self.backlight)
        time.sleep(0.0001)

    def _send_byte(self, bits: int, mode: int) -> None:
        """Send byte to LCD in two 4-bit nibbles."""
        high = mode | (bits & 0xF0)
        low = mode | ((bits << 4) & 0xF0)
        self._write_nibble(high)
        self._write_nibble(low)

    def command(self, cmd: int) -> None:
        self._send_byte(cmd, 0)
        time.sleep(0.002)

    def write_char(self, char_code: int) -> None:
        self._send_byte(char_code, RS_BIT)

    def init_display(self) -> bool:
        try:
            import smbus2
            self.bus = smbus2.SMBus(self.bus_num)
            self.address = self._find_address()
            if self.address is None:
                logger.error(f"No LCD device detected on I2C bus {self.bus_num}")
                return False

            time.sleep(0.05)
            # Initialization sequence for 4-bit mode (HD44780 standard)
            self._write_nibble(0x30)
            time.sleep(0.005)
            self._write_nibble(0x30)
            time.sleep(0.001)
            self._write_nibble(0x30)
            time.sleep(0.001)
            self._write_nibble(0x20) # 4-bit mode

            self.command(LCD_FUNCTIONSET | LCD_4BITMODE | LCD_2LINE | LCD_5x8DOTS)
            self.command(LCD_DISPLAYCONTROL | LCD_DISPLAYON | LCD_CURSOROFF | LCD_BLINKOFF)
            self.clear()
            self.command(LCD_ENTRYMODESET | LCD_ENTRYLEFT | LCD_ENTRYSHIFTDECREMENT)
            logger.info("LCD 1602 initialization complete")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize LCD 1602: {e}")
            return False

    def clear(self) -> None:
        if self.address is not None and self.bus is not None:
            try:
                self.command(LCD_CLEARDISPLAY)
                time.sleep(0.003)
            except Exception as e:
                logger.warning(f"Error clearing LCD: {e}")

    def display_text(self, line1: str = "", line2: str = "") -> None:
        if self.address is None or self.bus is None:
            logger.warning("Cannot display text: LCD not initialized")
            return
        try:
            self.clear()
            # Line 1 (address 0x80)
            self.command(LCD_SETDDRAMADDR | 0x00)
            for char in line1[:16]:
                self.write_char(ord(char))

            # Line 2 (address 0xC0)
            if line2:
                self.command(LCD_SETDDRAMADDR | 0x40)
                for char in line2[:16]:
                    self.write_char(ord(char))
            logger.info(f"LCD text updated: Line 1='{line1[:16]}', Line 2='{line2[:16]}'")
        except Exception as e:
            logger.error(f"Error writing text to LCD: {e}")

    def cleanup(self) -> None:
        if self.bus is not None:
            try:
                self.clear()
                self.bus.close()
                logger.info("LCD bus closed")
            except Exception as e:
                logger.warning(f"Error closing LCD bus: {e}")
