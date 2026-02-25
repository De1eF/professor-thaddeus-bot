import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import requests


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str
    message_thread_id: int | None


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
    dynamic_commands: dict[str, str]


def load_config() -> AppConfig:
    _load_dotenv(Path(".env"))

    config_url = os.getenv("THADDEUS_CONFIG_URL", "").strip()
    if not config_url:
        raise RuntimeError("THADDEUS_CONFIG_URL is required.")

    payload = _fetch_remote_config(config_url)

    telegram_payload = payload["telegram"]
    twitch_payload = payload.get("twitch")
    youtube_payload = payload.get("youtube")
    chat_id, inferred_thread_id = _parse_chat_and_thread(telegram_payload["chat_id"])
    explicit_thread_id = telegram_payload.get("message_thread_id")
    message_thread_id = (
        int(explicit_thread_id) if explicit_thread_id is not None else inferred_thread_id
    )

    return AppConfig(
        telegram=TelegramConfig(
            bot_token=telegram_payload["bot_token"],
            chat_id=chat_id,
            message_thread_id=message_thread_id,
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
        dynamic_commands=_parse_dynamic_commands(payload.get("dynamic_commands", [])),
    )


def _fetch_remote_config(config_url: str) -> dict[str, Any]:
    normalized_url = _normalize_config_url(config_url)
    headers, auth = _build_auth()

    response = requests.get(normalized_url, headers=headers, auth=auth, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_remote_resource(resource_path: str) -> tuple[bytes, str]:
    _load_dotenv(Path(".env"))
    resources_base_url = os.getenv("THADDEUS_RESOURCES_URL", "").strip()
    if not resources_base_url:
        raise RuntimeError("THADDEUS_RESOURCES_URL is required for file resources.")

    normalized_base = _normalize_remote_url(resources_base_url)
    normalized_path = _normalize_resource_path(resource_path)
    resource_url = _build_resource_url(normalized_base, normalized_path)
    headers, auth = _build_auth()

    response = requests.get(resource_url, headers=headers, auth=auth, timeout=30)
    response.raise_for_status()
    filename = Path(normalized_path).name or "resource.bin"
    return response.content, filename


def _build_auth() -> tuple[dict[str, str], tuple[str, str] | None]:
    username = os.getenv("THADDEUS_GIT_USERNAME", "").strip()
    token = os.getenv("THADDEUS_GIT_TOKEN", "").strip()

    headers = {"Accept": "application/json"}
    auth: tuple[str, str] | None = None

    if username and token:
        auth = (username, token)
    elif token:
        headers["Authorization"] = f"Bearer {token}"
    return headers, auth


def _normalize_remote_url(remote_url: str) -> str:
    parsed = urlparse(remote_url)
    if parsed.netloc.lower() != "github.com":
        return remote_url.rstrip("/")

    parts = parsed.path.strip("/").split("/")
    if len(parts) >= 4 and parts[2] in ("blob", "tree"):
        owner = parts[0]
        repo = parts[1]
        branch = parts[3]
        rest = "/".join(parts[4:])
        base = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}"
        return f"{base}/{rest}".rstrip("/") if rest else base
    return remote_url.rstrip("/")


def _normalize_config_url(config_url: str) -> str:
    return _normalize_remote_url(config_url)


def _normalize_resource_path(resource_path: str) -> str:
    path = resource_path.strip().lstrip("/")
    if not path:
        raise RuntimeError("Resource path cannot be empty.")
    if ".." in path.split("/"):
        raise RuntimeError("Resource path cannot contain '..'.")
    return path


def _build_resource_url(base_url: str, resource_path: str) -> str:
    encoded_path = "/".join(quote(part, safe="") for part in resource_path.split("/"))
    return f"{base_url.rstrip('/')}/{encoded_path}"


def _parse_dynamic_commands(raw_commands: Any) -> dict[str, str]:
    parsed: dict[str, str] = {}
    if isinstance(raw_commands, dict):
        for command, message in raw_commands.items():
            _add_dynamic_command(parsed, command, message)
        return parsed

    if isinstance(raw_commands, list):
        for item in raw_commands:
            if isinstance(item, dict):
                _add_dynamic_command(parsed, item.get("command"), item.get("message"))
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                _add_dynamic_command(parsed, item[0], item[1])
    return parsed


def _add_dynamic_command(parsed: dict[str, str], command: Any, message: Any) -> None:
    if not isinstance(command, str) or not isinstance(message, str):
        return

    normalized_command = command.strip().lstrip("/").lower()
    if not normalized_command:
        return
    parsed[normalized_command] = message.strip()


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _parse_chat_and_thread(raw_chat_id: Any) -> tuple[str, int | None]:
    value = str(raw_chat_id).strip()
    if value.startswith("#"):
        value = value[1:].strip()
    if "_" not in value:
        return value, None

    chat_part, thread_part = value.rsplit("_", 1)
    if not chat_part or not thread_part.isdigit():
        return value, None
    return chat_part, int(thread_part)
