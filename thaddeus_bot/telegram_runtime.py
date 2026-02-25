import asyncio
import logging
import re
from io import BytesIO

from telegram import BotCommand, InputFile, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from .app_config import fetch_remote_resource, load_config
from .stream_monitor import StreamMonitor

LOG = logging.getLogger("telegram-runtime")
FILE_REF_PATTERN = re.compile(r"file:([^\s]+)")


async def _ensure_allowed_chat(
    update: Update,
    allowed_chat_id: str,
    allowed_thread_id: int | None,
) -> bool:
    chat = update.effective_chat
    if chat is None:
        return False

    if str(chat.id) != allowed_chat_id:
        if update.effective_message:
            await update.effective_message.reply_text(
                "Nope, I refuse to execute that command in this chat."
            )
        return False

    if allowed_thread_id is not None:
        message = update.effective_message
        incoming_thread_id = message.message_thread_id if message is not None else None
        if incoming_thread_id != allowed_thread_id:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "Nope, I refuse to execute that command in this topic."
                )
            return False
    return True


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    monitor: StreamMonitor = context.application.bot_data["monitor"]
    allowed_chat_id: str = context.application.bot_data["allowed_chat_id"]
    allowed_thread_id: int | None = context.application.bot_data["allowed_thread_id"]

    if not await _ensure_allowed_chat(update, allowed_chat_id, allowed_thread_id):
        return

    await update.effective_message.reply_text("Checking subscription status...")
    report = await asyncio.to_thread(monitor.build_status_report)
    await update.effective_message.reply_text(report)


async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    application = context.application
    allowed_chat_id: str = application.bot_data["allowed_chat_id"]
    allowed_thread_id: int | None = application.bot_data["allowed_thread_id"]
    if not await _ensure_allowed_chat(update, allowed_chat_id, allowed_thread_id):
        return

    lock: asyncio.Lock = application.bot_data["reload_lock"]
    async with lock:
        await update.effective_message.reply_text("Reloading configuration...")

        try:
            new_config = await asyncio.to_thread(load_config)
        except Exception:
            LOG.exception("Failed to reload configuration")
            await update.effective_message.reply_text("Reload failed: unable to load remote config.")
            return

        existing_config = application.bot_data["config"]
        if new_config.telegram.bot_token != existing_config.telegram.bot_token:
            await update.effective_message.reply_text(
                "Reload failed: bot token changed. Restart the app to apply token changes."
            )
            return

        old_task: asyncio.Task | None = application.bot_data.get("monitor_task")
        if old_task:
            old_task.cancel()
            try:
                await old_task
            except asyncio.CancelledError:
                pass

        monitor = StreamMonitor(new_config, bot=application.bot)
        application.bot_data["config"] = new_config
        application.bot_data["dynamic_commands"] = new_config.dynamic_commands
        application.bot_data["monitor"] = monitor
        application.bot_data["allowed_chat_id"] = new_config.telegram.chat_id
        application.bot_data["allowed_thread_id"] = new_config.telegram.message_thread_id
        application.bot_data["monitor_task"] = application.create_task(monitor.run_forever())
        await _refresh_bot_commands(application)

        await update.effective_message.reply_text("Configuration reloaded.")


def _extract_command_name(update: Update) -> str | None:
    message = update.effective_message
    if message is None or not message.text:
        return None

    text = message.text.strip()
    if not text.startswith("/"):
        return None

    token = text.split(maxsplit=1)[0][1:]
    if not token:
        return None

    command = token.split("@", 1)[0].strip().lower()
    return command or None


async def dynamic_command_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    command_name = _extract_command_name(update)
    if command_name is None or command_name in {"status", "reload"}:
        return

    application = context.application
    dynamic_commands: dict[str, str] = application.bot_data["dynamic_commands"]
    template = dynamic_commands.get(command_name)
    if template is None:
        return

    allowed_chat_id: str = application.bot_data["allowed_chat_id"]
    allowed_thread_id: int | None = application.bot_data["allowed_thread_id"]
    if not await _ensure_allowed_chat(update, allowed_chat_id, allowed_thread_id):
        return

    file_refs = FILE_REF_PATTERN.findall(template)
    for ref in file_refs:
        try:
            content, filename = await asyncio.to_thread(fetch_remote_resource, ref)
        except Exception:
            LOG.exception("Failed to fetch dynamic command resource: %s", ref)
            await context.bot.send_message(
                chat_id=allowed_chat_id,
                message_thread_id=allowed_thread_id,
                text=f"Failed to load resource: {ref}",
            )
            continue

        await context.bot.send_document(
            chat_id=allowed_chat_id,
            message_thread_id=allowed_thread_id,
            document=InputFile(BytesIO(content), filename=filename),
        )

    text_response = FILE_REF_PATTERN.sub("", template).strip()
    if text_response:
        await context.bot.send_message(
            chat_id=allowed_chat_id,
            message_thread_id=allowed_thread_id,
            text=text_response,
        )


async def on_startup(application: Application) -> None:
    monitor: StreamMonitor = application.bot_data["monitor"]
    application.bot_data["monitor_task"] = application.create_task(monitor.run_forever())
    await _refresh_bot_commands(application)


async def _refresh_bot_commands(application: Application) -> None:
    dynamic_commands: dict[str, str] = application.bot_data["dynamic_commands"]
    commands = [
        BotCommand("status", "Show live/offline status"),
        BotCommand("reload", "Reload remote configuration"),
    ]
    commands.extend(
        BotCommand(name, "Dynamic command")
        for name in sorted(dynamic_commands.keys())
    )
    await application.bot.set_my_commands(commands)
    LOG.info("Registered Telegram commands: %s", ", ".join(f"/{cmd.command}" for cmd in commands))


async def on_shutdown(application: Application) -> None:
    task: asyncio.Task | None = application.bot_data.get("monitor_task")
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def run_bot(
) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Suppress Telegram polling noise while keeping app-level logs.
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    config = load_config()
    application = (
        Application.builder()
        .token(config.telegram.bot_token)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )

    monitor = StreamMonitor(config, bot=application.bot)
    application.bot_data["config"] = config
    application.bot_data["dynamic_commands"] = config.dynamic_commands
    application.bot_data["monitor"] = monitor
    application.bot_data["allowed_chat_id"] = config.telegram.chat_id
    application.bot_data["allowed_thread_id"] = config.telegram.message_thread_id
    application.bot_data["reload_lock"] = asyncio.Lock()

    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("reload", reload_command))
    application.add_handler(MessageHandler(filters.COMMAND, dynamic_command_router))
    # Python 3.14 no longer creates a default event loop for the main thread.
    # python-telegram-bot 21.x still expects one to exist when run_polling starts.
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    application.run_polling(allowed_updates=Update.ALL_TYPES)
