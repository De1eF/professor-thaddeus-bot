import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone
from io import BytesIO

from telegram import Bot, InputFile

from .app_config import AppConfig, DailyMessageEntry, fetch_remote_resource


LOG = logging.getLogger("daily-messages")
GMT_PLUS_2 = timezone(timedelta(hours=2), "GMT+2")
DAILY_SEND_TIME = time(hour=10, minute=0, tzinfo=GMT_PLUS_2)
TELEGRAM_PHOTO_CAPTION_LIMIT = 1024


class DailyMessageScheduler:
    def __init__(self, config: AppConfig, bot: Bot):
        self._config = config
        self._bot = bot

    async def run_forever(self) -> None:
        daily_config = self._config.daily_messages
        if daily_config is None:
            LOG.info("Daily messages are not configured")
            return

        LOG.info(
            "Starting daily message scheduler for %s entries in chat=%s thread=%s",
            len(daily_config.entries),
            daily_config.chat_id,
            daily_config.message_thread_id,
        )
        try:
            while True:
                now = datetime.now(GMT_PLUS_2)
                next_run = self._next_run_after(now)
                sleep_seconds = max((next_run - now).total_seconds(), 0)
                LOG.info("Next daily message check at %s", next_run.isoformat())
                await asyncio.sleep(sleep_seconds)
                await self.run_once(datetime.now(GMT_PLUS_2).date())
        except asyncio.CancelledError:
            LOG.info("Daily message scheduler task cancelled")
            raise

    async def run_once(self, current_date: date) -> int:
        daily_config = self._config.daily_messages
        if daily_config is None:
            return 0

        matches = [
            entry for entry in daily_config.entries if self._entry_matches_date(entry, current_date)
        ]
        if not matches:
            LOG.info("No daily messages configured for %s", current_date.isoformat())
            return 0

        LOG.info("Sending %s daily message(s) for %s", len(matches), current_date.isoformat())
        sent_count = 0
        for entry in matches:
            try:
                await self._send_entry(entry)
                sent_count += 1
            except Exception:
                LOG.exception("Failed to send daily message for %s", entry.date)
        return sent_count

    async def _send_entry(self, entry: DailyMessageEntry) -> None:
        daily_config = self._config.daily_messages
        if daily_config is None:
            return

        if not entry.image:
            await self._bot.send_message(
                chat_id=daily_config.chat_id,
                message_thread_id=daily_config.message_thread_id,
                text=entry.plaintext,
            )
            return

        content, filename = await asyncio.to_thread(fetch_remote_resource, entry.image)
        if len(entry.plaintext) <= TELEGRAM_PHOTO_CAPTION_LIMIT:
            await self._send_image(
                daily_config.chat_id,
                daily_config.message_thread_id,
                content,
                filename,
                entry.plaintext,
            )
            return

        await self._bot.send_message(
            chat_id=daily_config.chat_id,
            message_thread_id=daily_config.message_thread_id,
            text=entry.plaintext,
        )
        await self._send_image(
            daily_config.chat_id,
            daily_config.message_thread_id,
            content,
            filename,
            None,
        )

    async def _send_image(
        self,
        chat_id: str,
        message_thread_id: int | None,
        content: bytes,
        filename: str,
        caption: str | None,
    ) -> None:
        image_file = InputFile(BytesIO(content), filename=filename)
        if filename.lower().endswith(".gif"):
            await self._bot.send_animation(
                chat_id=chat_id,
                message_thread_id=message_thread_id,
                animation=image_file,
                caption=caption,
            )
            return

        await self._bot.send_photo(
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            photo=image_file,
            caption=caption,
        )

    @staticmethod
    def _entry_matches_date(entry: DailyMessageEntry, current_date: date) -> bool:
        try:
            configured_date = datetime.strptime(f"2000-{entry.date}", "%Y-%m-%d").date()
            return (
                configured_date.month == current_date.month
                and configured_date.day == current_date.day
            )
        except ValueError:
            LOG.warning("Ignoring daily message with invalid MM-DD date: %s", entry.date)
            return False

    @staticmethod
    def _next_run_after(now: datetime) -> datetime:
        today_run = datetime.combine(now.date(), DAILY_SEND_TIME)
        if now < today_run:
            return today_run
        return today_run + timedelta(days=1)
