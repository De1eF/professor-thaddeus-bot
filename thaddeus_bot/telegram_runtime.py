import asyncio
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .app_config import load_config
from .stream_monitor import StreamMonitor


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    monitor: StreamMonitor = context.application.bot_data["monitor"]
    allowed_chat_id: str = context.application.bot_data["allowed_chat_id"]

    chat = update.effective_chat
    if chat is None:
        return

    if str(chat.id) != allowed_chat_id:
        await update.effective_message.reply_text("This command is not allowed in this chat.")
        return

    await update.effective_message.reply_text("Checking subscription status...")
    report = await asyncio.to_thread(monitor.build_status_report)
    await update.effective_message.reply_text(report)


async def on_startup(application: Application) -> None:
    monitor: StreamMonitor = application.bot_data["monitor"]
    application.bot_data["monitor_task"] = application.create_task(monitor.run_forever())


async def on_shutdown(application: Application) -> None:
    task: asyncio.Task | None = application.bot_data.get("monitor_task")
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def run_bot(config_path: Path = Path("config.json")) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = load_config(config_path)
    application = (
        Application.builder()
        .token(config.telegram.bot_token)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )

    monitor = StreamMonitor(config, bot=application.bot)
    application.bot_data["monitor"] = monitor
    application.bot_data["allowed_chat_id"] = config.telegram.chat_id

    application.add_handler(CommandHandler("status", status_command))
    # Python 3.14 no longer creates a default event loop for the main thread.
    # python-telegram-bot 21.x still expects one to exist when run_polling starts.
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    application.run_polling(allowed_updates=Update.ALL_TYPES)
