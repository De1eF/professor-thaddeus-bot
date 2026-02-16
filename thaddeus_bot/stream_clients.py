import requests

from .app_config import TwitchConfig, YouTubeConfig


class TwitchClient:
    def __init__(self, config: TwitchConfig):
        self._config = config
        self._access_token: str | None = None

    def _ensure_token(self) -> str:
        if self._access_token:
            return self._access_token

        response = requests.post(
            "https://id.twitch.tv/oauth2/token",
            params={
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
                "grant_type": "client_credentials",
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        self._access_token = payload["access_token"]
        return self._access_token

    def check_live(self, channel: str) -> tuple[bool, str, str | None]:
        token = self._ensure_token()
        response = requests.get(
            "https://api.twitch.tv/helix/streams",
            params={"user_login": channel},
            headers={
                "Client-Id": self._config.client_id,
                "Authorization": f"Bearer {token}",
            },
            timeout=20,
        )

        if response.status_code == 401:
            self._access_token = None
            token = self._ensure_token()
            response = requests.get(
                "https://api.twitch.tv/helix/streams",
                params={"user_login": channel},
                headers={
                    "Client-Id": self._config.client_id,
                    "Authorization": f"Bearer {token}",
                },
                timeout=20,
            )

        response.raise_for_status()
        data = response.json().get("data", [])
        if not data:
            return False, f"https://www.twitch.tv/{channel}", None

        stream = data[0]
        return True, f"https://www.twitch.tv/{channel}", stream.get("title")


class YouTubeClient:
    def __init__(self, config: YouTubeConfig):
        self._config = config

    def check_live(self, channel_id: str) -> tuple[bool, str, str | None]:
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "channelId": channel_id,
                "eventType": "live",
                "type": "video",
                "maxResults": 1,
                "key": self._config.api_key,
            },
            timeout=20,
        )
        response.raise_for_status()
        items = response.json().get("items", [])

        default_url = f"https://www.youtube.com/channel/{channel_id}/live"
        if not items:
            return False, default_url, None

        first = items[0]
        video_id = first.get("id", {}).get("videoId")
        title = first.get("snippet", {}).get("title")
        url = f"https://www.youtube.com/watch?v={video_id}" if video_id else default_url
        return True, url, title

