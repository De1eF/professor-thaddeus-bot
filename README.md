# professor-thaddeus-bot

Telegram bot that watches Twitch/YouTube channels and posts live/offline updates.

## Run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create `.env` from `.env_example` and set values:

- `THADDEUS_CONFIG_URL`: URL to remote `config.json`
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

## Remote Config

The app loads config from `THADDEUS_CONFIG_URL` on startup and on `/reload`.

`telegram.chat_id` supports:
- `-1001234567890` (chat only)
- `-1001234567890_2111` (chat + topic/thread)

You can also set topic explicitly with `telegram.message_thread_id`.

## Custom Commands

Set `dynamic_commands` in remote config.

Each command has:
- `command`: command name (with or without `/`)
- `message`: text to send

If `message` contains `file:relative/path.ext`, the bot fetches that file from `THADDEUS_RESOURCES_URL` and sends it.

Example:
- `/rules` -> sends text
- `/guide` with `file:getting-started.pdf` -> sends that PDF

## Sample `config.json`

```json
{
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "-1001234567890",
    "message_thread_id": 2111
  },
  "twitch": {
    "client_id": "YOUR_TWITCH_CLIENT_ID",
    "client_secret": "YOUR_TWITCH_CLIENT_SECRET"
  },
  "youtube": {
    "api_key": "YOUR_YOUTUBE_API_KEY"
  },
  "poll_interval_seconds": 60,
  "state_file": "state.json",
  "notify_on_startup": false,
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

