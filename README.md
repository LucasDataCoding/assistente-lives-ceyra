# Twitch Chat Bot 🤖

A customizable Twitch chat bot that tracks command usage and persists data in JSON format. Perfect for streamers who want to engage with their audience!

## Features ✨
- Tracks command usage (e.g., `!hello`) with user-specific counters
- Persists data between sessions using `hellocounter.json`
- Customizable prefix and channels
- Built with Python using `twitchio` library

## Setup Guide 🛠️

### 1. Prerequisites
- Python 3.8+
- Twitch account (for bot)
- [Twitch OAuth Token](https://twitchtokengenerator.com)

### 2. Configuration
Create/modify `.config` file in the root directory:

```ini
[CHAT]
CHAT_TOKEN = oauth:YOUR_BOT_TOKEN_HERE
CHANNELS = [YOUR_CHANNEL_NAME_LOWERCASE_HERE]
PREFIX = !
BOT_USERNAME = YOUR_BOT_NAME_HERE
CLIENT_ID = OPTIONAL_YOUR_CLIENT_ID_HERE  # Only needed for advanced features
```

**How to get these values:**
- `CHAT_TOKEN`: Generate at [Twitch Token Generator](https://twitchtokengenerator.com) (select "Bot Chat Token")
- `CHANNELS`: Your Twitch channel name in lowercase (e.g., `["lucasdatacoding"]`)
- `BOT_USERNAME`: Your bot account's username
- `CLIENT_ID`: Only needed if using Twitch API features (get from [Twitch Developer Console](https://dev.twitch.tv/console))

### 3. Installation
```bash
# Clone the repository
git clone https://github.com/your-repo/twitch-bot.git
cd twitch-bot

# Install dependencies
pip install -r requirements.txt
```

### 4. Available Commands
| Command | Description |
|---------|-------------|
| `!hello` | Greets user and shows usage count |
| `!hellocount` | Shows your personal hello count |
| `!tophello` | Shows top 5 hello users |

## Running the Bot 🚀
```bash
python bot.py
```

## Customization 🎨
### Add new commands:
Edit `bot.py` and add new command handlers:
```python
@commands.command()
async def yourcommand(self, ctx: commands.Context):
    await ctx.send("Your custom response!")
```

### Modify persistence:
- Data is saved in `hellocounter.json`
- Modify `load_counter()` and `save_counter()` methods to change storage format

## Troubleshooting 🔧
| Issue | Solution |
|-------|----------|
| Bot connects but doesn't respond | Check token permissions have `chat:read` and `chat:write` |
| "Login authentication failed" | Generate new OAuth token |
| Commands work but no messages sent | Add bot as moderator: `/mod YOUR_BOT_NAME` |

## License 📄
MIT License - Feel free to modify and distribute!

---

**Happy Streaming!** 🎮📺  
*If you enjoy this bot, consider starring the repo!*
```
