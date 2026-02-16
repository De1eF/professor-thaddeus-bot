import asyncio
import logging
from pathlib import Path
from queue import Queue
from typing import TypeAlias

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .app_config import load_config
from .stream_monitor import StreamMonitor

LOG = logging.getLogger("telegram-runtime")
ConsoleCommand: TypeAlias = tuple[str, str | None]


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
    command_queue: Queue[ConsoleCommand] | None = application.bot_data.get("command_queue")
    if command_queue is not None:
        application.bot_data["command_task"] = application.create_task(
            process_console_commands(application, command_queue)
        )


async def on_shutdown(application: Application) -> None:
    for task_key in ("command_task", "monitor_task"):
        task: asyncio.Task | None = application.bot_data.get(task_key)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


async def process_console_commands(application: Application, command_queue: Queue[ConsoleCommand]) -> None:
    monitor: StreamMonitor = application.bot_data["monitor"]
    while True:
        command, value = await asyncio.to_thread(command_queue.get)
        if command == "stop":
            LOG.info("Console requested shutdown.")
            application.stop_running()
            return
        if command not in ("online", "offline") or not value:
            LOG.warning("Ignoring invalid console command: %s %s", command, value)
            continue

        try:
            result = await monitor.simulate_event(subscription_id=value, is_live=(command == "online"))
            LOG.info(result)
        except Exception:
            LOG.exception("Failed to run console command: %s %s", command, value)


def run_bot(
    config_path: Path = Path("config.json"),
    command_queue: Queue[ConsoleCommand] | None = None,
) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Suppress Telegram polling noise while keeping app-level logs.
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

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
    application.bot_data["command_queue"] = command_queue

    application.add_handler(CommandHandler("status", status_command))
    # Python 3.14 no longer creates a default event loop for the main thread.
    # python-telegram-bot 21.x still expects one to exist when run_polling starts.
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    application.run_polling(allowed_updates=Update.ALL_TYPES)
