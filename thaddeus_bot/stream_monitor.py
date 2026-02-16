import asyncio
import json
import logging
import random
from pathlib import Path
from typing import Any

from telegram import Bot

from .app_config import AppConfig
from .stream_clients import TwitchClient, YouTubeClient


LOG = logging.getLogger("stream-notifier")


class StreamMonitor:
    def __init__(self, config: AppConfig, bot: Bot):
        self._config = config
        self._bot = bot
        self._state = self._load_state(config.state_file)

        self._twitch = TwitchClient(config.twitch) if config.twitch else None
        self._youtube = YouTubeClient(config.youtube) if config.youtube else None

    @staticmethod
    def _load_state(path: Path) -> dict[str, bool]:
        if not path.exists():
            return {}

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return {k: bool(v) for k, v in payload.items()}
        except Exception:
            LOG.exception("Failed to load state file %s", path)

        return {}

    def _save_state(self) -> None:
        self._config.state_file.write_text(
            json.dumps(self._state, indent=2),
            encoding="utf-8",
        )

    async def run_forever(self) -> None:
        LOG.info("Starting monitor for %s subscriptions", len(self._config.subscriptions))
        try:
            while True:
                await self._run_once()
                await asyncio.sleep(self._config.poll_interval_seconds)
        except asyncio.CancelledError:
            LOG.info("Monitor task cancelled")
            raise

    async def _run_once(self) -> None:
        for sub in self._config.subscriptions:
            sub_id = sub["id"]
            platform = sub["platform"].lower()
            channel = sub["channel"]
            channel_name = sub.get("display_name", channel)

            try:
                is_live, url, title = self._check_live(platform, channel)
            except Exception:
                LOG.exception("Failed to check stream status for %s", sub_id)
                continue

            previous = self._state.get(sub_id)
            self._state[sub_id] = is_live
            self._save_state()

            if previous is None and not self._config.notify_on_startup:
                continue

            if previous == is_live:
                continue

            template_key = "live_message" if is_live else "offline_message"
            template = self._pick_template(sub.get(template_key))
            if not template:
                LOG.warning("No %s configured for %s", template_key, sub_id)
                continue

            text = self._render(template, platform, channel_name, channel, title, url, is_live)
            if is_live:
                await self._bot.send_message(chat_id=self._config.telegram.chat_id, text=url)
            await self._bot.send_message(chat_id=self._config.telegram.chat_id, text=text)
            LOG.info("Sent %s notification for %s", "live" if is_live else "offline", sub_id)

    async def simulate_event(self, subscription_id: str, is_live: bool) -> str:
        sub = self._find_subscription(subscription_id)
        if sub is None:
            raise ValueError(f"Subscription id not found: {subscription_id}")

        sub_id = sub["id"]
        platform = sub["platform"].lower()
        channel = sub["channel"]
        channel_name = sub.get("display_name", channel)
        url = self._default_stream_url(platform, channel)
        title = "Simulated event"

        template_key = "live_message" if is_live else "offline_message"
        template = self._pick_template(sub.get(template_key))
        if not template:
            raise ValueError(f"No {template_key} configured for {sub_id}")

        text = self._render(template, platform, channel_name, channel, title, url, is_live)
        if is_live:
            await self._bot.send_message(chat_id=self._config.telegram.chat_id, text=url)
        await self._bot.send_message(chat_id=self._config.telegram.chat_id, text=text)
        self._state[sub_id] = is_live
        self._save_state()
        return f"Simulated {'online' if is_live else 'offline'} event for {sub_id}."

    def build_status_report(self) -> str:
        if not self._config.subscriptions:
            return "No subscriptions configured."

        lines: list[str] = []
        live_count = 0
        offline_count = 0
        error_count = 0

        for sub in self._config.subscriptions:
            sub_id = sub["id"]
            platform = sub["platform"].lower()
            channel = sub["channel"]
            display_name = sub.get("display_name", channel)

            try:
                is_live, url, title = self._check_live(platform, channel)
            except Exception as exc:
                error_count += 1
                lines.append(f"- {display_name} ({platform}) [{sub_id}]: ERROR - {exc}")
                continue

            if is_live:
                live_count += 1
                title_suffix = f" | {title}" if title else ""
                lines.append(f"- {display_name} ({platform}) [{sub_id}]: LIVE{title_suffix} | {url}")
            else:
                offline_count += 1
                lines.append(f"- {display_name} ({platform}) [{sub_id}]: OFFLINE | {url}")

        summary = (
            f"Status check complete: {live_count} live, {offline_count} offline, {error_count} errors."
        )
        return f"{summary}\n" + "\n".join(lines)

    def _check_live(self, platform: str, channel: str) -> tuple[bool, str, str | None]:
        if platform == "twitch":
            if not self._twitch:
                raise RuntimeError("Twitch subscription found but Twitch API config is missing")
            return self._twitch.check_live(channel)

        if platform == "youtube":
            if not self._youtube:
                raise RuntimeError("YouTube subscription found but YouTube API config is missing")
            return self._youtube.check_live(channel)

        raise ValueError(f"Unsupported platform: {platform}")

    def _find_subscription(self, subscription_id: str) -> dict[str, Any] | None:
        for sub in self._config.subscriptions:
            if sub.get("id") == subscription_id:
                return sub
        return None

    @staticmethod
    def _default_stream_url(platform: str, channel: str) -> str:
        if platform == "twitch":
            return f"https://www.twitch.tv/{channel}"
        if platform == "youtube":
            return f"https://www.youtube.com/channel/{channel}/live"
        raise ValueError(f"Unsupported platform: {platform}")

    @staticmethod
    def _pick_template(template_value: Any) -> str | None:
        if isinstance(template_value, str):
            return template_value

        if isinstance(template_value, list):
            options = [item for item in template_value if isinstance(item, str) and item.strip()]
            if options:
                return random.choice(options)

        return None

    @staticmethod
    def _render(
        template: str,
        platform: str,
        display_name: str,
        channel: str,
        title: str | None,
        url: str,
        is_live: bool,
    ) -> str:
        return template.format(
            platform=platform,
            display_name=display_name,
            channel=channel,
            title=title or "",
            status="live" if is_live else "offline",
            url=url,
        ).strip()

