import logging
from app.config import settings
from app.hardware.base import BaseSwitch, BaseMotor, BaseDHTSensor, BaseLCD, BaseCamera
from app.hardware.mock_service import MockSwitch, MockMotor, MockDHTSensor, MockLCD
from app.hardware.camera_service import MockCamera

logger = logging.getLogger("hardware.manager")

class HardwareManager:
    def __init__(self):
        self.is_mock = settings.MOCK_HARDWARE
        self.switch: BaseSwitch
        self.motor: BaseMotor
        self.dht: BaseDHTSensor
        self.lcd: BaseLCD
        self.camera: BaseCamera

        if self.is_mock:
            logger.info("Starting in MOCK hardware mode (emulated devices)")
            self._init_mock()
        else:
            logger.info("Starting in PHYSICAL hardware mode (Raspberry Pi)")
            try:
                self._init_real()
            except Exception as e:
                logger.error(f"Failed to initialize real hardware: {e}. Falling back to MOCK mode.")
                self.is_mock = True
                self._init_mock()

    def _init_mock(self):
        self.switch = MockSwitch(pin=settings.GPIO_16_PIN)
        self.motor = MockMotor(pin=settings.MOTOR_PWM_PIN, freq=settings.MOTOR_PWM_FREQ)
        self.dht = MockDHTSensor(pin=settings.DHT11_PIN)
        self.lcd = MockLCD(addresses=settings.LCD_ADDRESS_CANDIDATES)
        self.camera = MockCamera(width=settings.CAMERA_WIDTH, height=settings.CAMERA_HEIGHT)

    def _init_real(self):
        from app.hardware.gpio_service import RPiSwitch, RPiMotor
        from app.hardware.dht_service import RPiDHTSensor
        from app.hardware.lcd_service import RPiLCD
        from app.hardware.camera_service import RPiUSBCamera

        self.switch = RPiSwitch(pin=settings.GPIO_16_PIN)
        self.motor = RPiMotor(pin=settings.MOTOR_PWM_PIN, freq=settings.MOTOR_PWM_FREQ)
        self.dht = RPiDHTSensor(pin=settings.DHT11_PIN)
        self.lcd = RPiLCD(bus_num=settings.I2C_BUS, address_candidates=settings.LCD_ADDRESS_CANDIDATES)
        self.camera = RPiUSBCamera(
            device_index=settings.CAMERA_INDEX,
            width=settings.CAMERA_WIDTH,
            height=settings.CAMERA_HEIGHT
        )

    def read_dht(self) -> tuple[float, float]:
        """Read DHT11 and synchronize real temperature to the LCD simulator baseline."""
        from app.services.temp_simulator import temp_simulator
        temp, humidity = self.dht.read()
        temp_simulator.update_real_temp(temp)
        return temp, humidity

    def cleanup(self):
        logger.info("Cleaning up hardware resources...")
        for comp in [self.switch, self.motor, self.dht, self.lcd, self.camera]:
            if comp is not None:
                try:
                    comp.cleanup()
                except Exception:
                    pass

hardware_manager = HardwareManager()
