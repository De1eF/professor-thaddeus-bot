import argparse
import asyncio
import logging
import sys
from pathlib import Path

from telegram import Bot

from .app_config import load_config
from .stream_monitor import StreamMonitor
from .telegram_runtime import run_bot


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


def run_cli(argv: list[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "online":
        run_simulation(subscription_id=args.subscription_id, is_live=True)
    elif args.command == "offline":
        run_simulation(subscription_id=args.subscription_id, is_live=False)
    else:
        run_bot()

