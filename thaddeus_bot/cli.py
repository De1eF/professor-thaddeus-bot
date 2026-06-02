import argparse
import asyncio
import sys
from datetime import date, datetime

from telegram import Bot

from .app_config import load_config
from .daily_messages import GMT_PLUS_2, DailyMessageScheduler
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

    daily_check_parser = subparsers.add_parser(
        "daily-check",
        aliases=["check-date"],
        help="Force a one-time daily message date check",
    )
    daily_check_parser.add_argument(
        "--date",
        help="Optional date to check in MM-DD format. Defaults to today in GMT+2.",
    )

    if not argv:
        return parser.parse_args(["run"])
    return parser.parse_args(argv)


def send_message(text: str) -> None:
    config = load_config()
    bot = Bot(token=config.telegram.bot_token)
    asyncio.run(
        bot.send_message(
            chat_id=config.telegram.chat_id,
            message_thread_id=config.telegram.stream_message_thread_id,
            text=text,
        )
    )
    print("Message sent.")


def force_daily_check(raw_date: str | None) -> None:
    config = load_config()
    bot = Bot(token=config.telegram.bot_token)
    current_date = _parse_daily_check_date(raw_date)
    scheduler = DailyMessageScheduler(config, bot=bot)
    sent_count = asyncio.run(scheduler.run_once(current_date))
    print(
        f"Daily date check complete for {current_date:%m-%d}. "
        f"Sent {sent_count} message(s)."
    )


def _parse_daily_check_date(raw_date: str | None) -> date:
    if not raw_date:
        return datetime.now(GMT_PLUS_2).date()

    try:
        parsed = datetime.strptime(f"2000-{raw_date}", "%Y-%m-%d").date()
    except ValueError as exc:
        raise SystemExit("--date must use MM-DD format, for example 06-03.") from exc
    return parsed


def run_cli() -> None:
    args = parse_args(sys.argv[1:])
    if args.command == "message":
        send_message(" ".join(args.text).strip())
        return
    if args.command in ("daily-check", "check-date"):
        force_daily_check(args.date)
        return
    run_bot()
