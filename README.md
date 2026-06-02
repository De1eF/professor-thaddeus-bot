# professor-thaddeus-bot

Telegram bot that watches Twitch/YouTube channels and posts live/offline updates.

## Run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create `.env` from `.env_example` and set values:

- `THADDEUS_CONFIG_URL`: URL to remote `config.json`
- `THADDEUS_CONFIG_BRANCH`: Git branch to read config/resources from, defaults to `main`
- `THADDEUS_RESOURCES_URL`: URL to remote resources folder (for command files)
- `THADDEUS_GIT_USERNAME`: optional
- `THADDEUS_GIT_TOKEN`: optional

3. Start:

```bash
python main.py
```

4. Send a one-off message (optional):

```bash
python main.py message "Hello"
```

5. Force a daily message date check for testing (optional):

```bash
python main.py daily-check
python main.py daily-check --date 06-03
```

## Remote Config

The app loads config from `THADDEUS_CONFIG_URL` on startup.
Set `THADDEUS_CONFIG_BRANCH=dev` to read the config and resources from the `dev`
branch instead of `main`.

`telegram.chat_id` supports:
- `-1001234567890` (chat only)
- `-1001234567890_2111` (chat + topic/thread)

You can set stream update topic explicitly with `telegram.stream_message_thread_id`.
You can set daily date-based message topic explicitly with `telegram.daily_message_thread_id`.
Legacy `telegram.message_thread_id` is still supported for backward compatibility.

## Custom Commands

Set `dynamic_commands` in remote config.

Each command has:
- `command`: command name (with or without `/`)
- `message`: text to send

If `message` contains `file:relative/path.ext`, the bot fetches that file from `THADDEUS_RESOURCES_URL` and sends it.

Example:
- `/rules` -> sends text
- `/guide` with `file:getting-started.pdf` -> sends that PDF

## Daily Messages

Set `daily_messages` in remote config to post date-based messages once per day.
The bot checks every day at 10:00 GMT+2. Dates use `MM-DD`; the year is ignored.
Daily messages are sent to `telegram.chat_id` and use `telegram.daily_message_thread_id`.
You can override that destination inside `daily_messages` with `chat_id` and `message_thread_id`,
but the usual setup is one Telegram channel with separate stream and daily-message topics.

If an entry has `image`, the value is fetched from `THADDEUS_RESOURCES_URL`.
The image is sent as a Telegram photo with the plaintext as its caption when
the caption fits Telegram's photo caption limit. Longer plaintext is sent as a
separate text message before the photo.

## Sample `config.json`

```json
{
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "-1001234567890",
    "stream_message_thread_id": 2111,
    "daily_message_thread_id": 2112
  },
  "twitch": {
    "client_id": "YOUR_TWITCH_CLIENT_ID",
    "client_secret": "YOUR_TWITCH_CLIENT_SECRET"
  },
  "youtube": {
    "api_key": "YOUR_YOUTUBE_API_KEY"
  },
  "poll_interval_seconds": 60,
  "log_polling": true,
  "state_file": "notify.json",
  "daily_messages": {
    "entries": [
      {
        "date": "06-02",
        "plaintext": "Today's reminder.",
        "image": "owl-fuck.gif"
      },
      {
        "date": "06-03",
        "plaintext": "Text-only reminder."
      }
    ]
  },
  "subscriptions": [
    {
      "id": "criticalrole",
      "platform": "twitch",
      "channel": "criticalrole",
      "display_name": "Critical Role",
      "live_message": "Critical Role is live: {url}",
      "offline_message": "Critical Role is offline."
    }
  ],
  "dynamic_commands": [
    {
      "command": "rules",
      "message": "Be respectful. No spam."
    },
    {
      "command": "guide",
      "message": "Start here: file:getting-started.pdf"
    }
  ]
}
```
