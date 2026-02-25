import argparse
import asyncio
import sys
from pathlib import Path

from telegram import Bot

from .app_config import load_config
from .telegram_runtime import run_bot


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Professor Thaddeus bot")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the Telegram bot")
    run_parser.set_defaults(command="run")

    message_parser = subparsers.add_parser(
        "message", help="Send a message to the configured Telegram chat"
    )
    message_parser.add_argument("text", nargs="+", help="Message text")

    if not argv:
        return parser.parse_args(["run"])
    return parser.parse_args(argv)


def send_message(text: str) -> None:
    config = load_config(Path("config.json"))
    bot = Bot(token=config.telegram.bot_token)
    asyncio.run(bot.send_message(chat_id=config.telegram.chat_id, text=text))
    print("Message sent.")


def run_cli() -> None:
    args = parse_args(sys.argv[1:])
    if args.command == "message":
        send_message(" ".join(args.text).strip())
        return
    run_bot()
