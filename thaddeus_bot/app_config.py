import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str


@dataclass
class TwitchConfig:
    client_id: str
    client_secret: str


@dataclass
class YouTubeConfig:
    api_key: str


@dataclass
class AppConfig:
    telegram: TelegramConfig
    twitch: TwitchConfig | None
    youtube: YouTubeConfig | None
    poll_interval_seconds: int
    state_file: Path
    notify_on_startup: bool
    subscriptions: list[dict[str, Any]]


def load_config(path: Path) -> AppConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))

    telegram_payload = payload["telegram"]
    twitch_payload = payload.get("twitch")
    youtube_payload = payload.get("youtube")

    return AppConfig(
        telegram=TelegramConfig(
            bot_token=telegram_payload["bot_token"],
            chat_id=str(telegram_payload["chat_id"]).strip(),
        ),
        twitch=TwitchConfig(
            client_id=twitch_payload["client_id"],
            client_secret=twitch_payload["client_secret"],
        )
        if twitch_payload
        else None,
        youtube=YouTubeConfig(api_key=youtube_payload["api_key"]) if youtube_payload else None,
        poll_interval_seconds=int(payload.get("poll_interval_seconds", 60)),
        state_file=Path(payload.get("state_file", "state.json")),
        notify_on_startup=bool(payload.get("notify_on_startup", False)),
        subscriptions=payload["subscriptions"],
    )

