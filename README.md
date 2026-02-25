# professor-thaddeus-bot

Config-driven Telegram bot that watches Twitch and YouTube channels and posts notifications when each channel goes live or offline.

## Features

- Tracks any mix of Twitch and YouTube subscriptions.
- Per-subscription live/offline message templates (single message or list).
- Always includes a stream link in every message.
- Poll-based monitoring with configurable interval.
- Persists stream state (`state.json`) to avoid duplicate notifications.
- Supports `/status` command to poll Twitch/YouTube APIs and report current state per subscription.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Copy config and edit values:

```bash
copy config.example.json config.json
```

3. Set your real values in `config.json`:

- `telegram.bot_token`: Telegram bot token from BotFather.
- `telegram.chat_id`: Chat or user id where notifications are sent.
- `twitch.client_id` and `twitch.client_secret`: Twitch app credentials.
- `youtube.api_key`: YouTube Data API key.

4. Start the bot:

```bash
python main.py
```

Send a one-off message to the configured Telegram chat:

```bash
python main.py message "Hello from CLI"
```

## One-command launcher (Windows)

Run:

```bat
run_bot.bat
```

This script will:
- Ensure Python is installed (installs via `winget` if missing).
- Create `.venv` if needed.
- Install/update dependencies from `requirements.txt`.
- Start the root entrypoint (`python main.py`).

## Docker CLI Message Command

With the container running, send a message to the configured chat:

```bash
docker compose exec bot python main.py message "Hello from Docker"
```

## Config template variables

Message templates support:

- `{platform}`
- `{display_name}`
- `{channel}`
- `{title}`
- `{status}`
- `{url}`

If `{url}` is not in your template, the bot appends it automatically.

For each subscription, `live_message` and `offline_message` can be:
- A single string template.
- A list of string templates (one is chosen randomly for each notification).

## Subscription format

Each item in `subscriptions` uses:

- `id`: Unique id for state tracking.
- `platform`: `twitch` or `youtube`.
- `channel`: Twitch login name or YouTube channel id.
- `display_name`: Optional display name.
- `live_message`: String or list of strings for when stream becomes live.
- `offline_message`: String or list of strings for when stream becomes offline.
