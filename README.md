# professor-thaddeus-bot

Config-driven Telegram bot that watches Twitch and YouTube channels and posts notifications when each channel goes live or offline.

## Features

- Tracks any mix of Twitch and YouTube subscriptions.
- Per-subscription live/offline message templates (single message or list).
- Always includes a stream link in every message.
- Poll-based monitoring with configurable interval.
- Persists stream state (`state.json`) to avoid duplicate notifications.
- Supports `/status` command to poll Twitch/YouTube APIs and report current state per subscription.
- Supports CLI simulation commands for forced online/offline subscription events.

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
python -m thaddeus_bot
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
- Start `thaddeus_bot` (`python -m thaddeus_bot`).

## Console Simulation Commands

Use the package CLI to simulate subscription transitions:

```bash
python -m thaddeus_bot online subscription_id
python -m thaddeus_bot offline subscription_id
```

These commands:
- Load `config.json`
- Find the subscription by `id`
- Send the configured `live_message` or `offline_message` to Telegram
- Update `state.json` for that subscription

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
