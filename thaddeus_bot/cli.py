import argparse
import asyncio
import logging
import sys
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import TypeAlias

from telegram import Bot

from .app_config import load_config
from .stream_monitor import StreamMonitor
from .telegram_runtime import run_bot

ConsoleCommand: TypeAlias = tuple[str, str | None]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Professor Thaddeus bot")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the Telegram bot")
    run_parser.set_defaults(command="run")

    online_parser = subparsers.add_parser(
        "online", help="Simulate an online event for a subscription id"
    )
    online_parser.add_argument("subscription_id")

    offline_parser = subparsers.add_parser(
        "offline", help="Simulate an offline event for a subscription id"
    )
    offline_parser.add_argument("subscription_id")

    if not argv:
        return parser.parse_args(["run"])
    return parser.parse_args(argv)


def run_simulation(subscription_id: str, is_live: bool) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config = load_config(Path("config.json"))
    bot = Bot(token=config.telegram.bot_token)
    monitor = StreamMonitor(config, bot=bot)
    result = asyncio.run(monitor.simulate_event(subscription_id=subscription_id, is_live=is_live))
    print(result)


def run_console_loop(command_queue: Queue[ConsoleCommand]) -> None:
    print("Console commands: online <subscription_id>, offline <subscription_id>, exit")
    while True:
        try:
            raw = input("> ").strip()
        except EOFError:
            command_queue.put(("stop", None))
            return
        except KeyboardInterrupt:
            command_queue.put(("stop", None))
            return

        if not raw:
            continue

        lowered = raw.lower()
        if lowered in ("exit", "quit"):
            command_queue.put(("stop", None))
            return

        parts = raw.split(maxsplit=1)
        if len(parts) != 2:
            print("Expected format: online <subscription_id> or offline <subscription_id>")
            continue

        command, subscription_id = parts[0].lower(), parts[1].strip()
        if command not in ("online", "offline"):
            print("Unknown command. Use online, offline, or exit.")
            continue
        if not subscription_id:
            print("Subscription id is required.")
            continue

        command_queue.put((command, subscription_id))


def run_cli(argv: list[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "online":
        run_simulation(subscription_id=args.subscription_id, is_live=True)
    elif args.command == "offline":
        run_simulation(subscription_id=args.subscription_id, is_live=False)
    else:
        command_queue: Queue[ConsoleCommand] | None = None
        if sys.stdin.isatty():
            command_queue = Queue()
            Thread(target=run_console_loop, args=(command_queue,), daemon=True).start()
        run_bot(command_queue=command_queue)
