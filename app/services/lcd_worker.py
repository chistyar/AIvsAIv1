import asyncio
import logging
from app.config import settings
from app.hardware.manager import hardware_manager
from app.services.temp_simulator import temp_simulator

logger = logging.getLogger("services.lcd_worker")

class LCDWorker:
    def __init__(self):
        self._task: asyncio.Task = None
        self._running = False

    async def _loop(self):
        logger.info("LCD temperature background update loop started")
        # Ensure LCD is initialized
        try:
            hardware_manager.lcd.init_display()
        except Exception as e:
            logger.warning(f"Initial LCD display init error: {e}")

        while self._running:
            try:
                line1, line2 = temp_simulator.get_display_strings()
                hardware_manager.lcd.display_text(line1=line1, line2=line2)
            except Exception as e:
                logger.debug(f"LCD update error in loop: {e}")

            try:
                await asyncio.sleep(settings.LCD_UPDATE_INTERVAL_SEC)
            except asyncio.CancelledError:
                break

        logger.info("LCD temperature loop stopped")

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("LCD worker stopped cleanly")

lcd_worker = LCDWorker()
