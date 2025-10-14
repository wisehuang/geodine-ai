# Bot Configurations

This directory contains configuration files for multiple LINE bots. Each bot is configured using a YAML file.

## Creating a New Bot

1. Copy the example configuration file:
   ```bash
   cp example-bot.yaml.example my-bot.yaml
   ```

2. Edit the configuration file with your bot's details:
   - `bot_id`: Unique identifier (lowercase, use hyphens)
   - `name`: Human-readable name
   - `channel_access_token`: LINE channel access token
   - `channel_secret`: LINE channel secret
   - Other optional settings

3. Add the bot's credentials to your `.env` file if using environment variables:
   ```env
   MY_BOT_ACCESS_TOKEN=your_access_token_here
   MY_BOT_SECRET=your_secret_here
   ```

4. Restart the server to load the new bot configuration

## Configuration Options

### Required Fields

- **bot_id** (string): Unique identifier for the bot
- **name** (string): Human-readable name
- **channel_access_token** (string): LINE channel access token
- **channel_secret** (string): LINE channel secret

### Optional Fields

- **description** (string): Description of the bot's purpose
- **webhook_path** (string): Custom webhook path (defaults to `/line/{bot_id}/webhook`)
- **use_ai_parsing** (boolean): Whether to use AI for parsing user requests (default: true)
- **default_radius** (integer): Default search radius in meters (default: 1000)
- **default_language** (string): Default language code (default: "en")
- **enabled** (boolean): Whether the bot is active (default: true)

## Environment Variables

You can reference environment variables in your configuration using the syntax `${VARIABLE_NAME}`.

Example:
```yaml
channel_access_token: "${MY_BOT_ACCESS_TOKEN}"
channel_secret: "${MY_BOT_SECRET}"
```

## Legacy Configuration

For backward compatibility, the system will automatically create a bot named "geodine-ai" if `LINE_CHANNEL_ACCESS_TOKEN` and `LINE_CHANNEL_SECRET` are set in the `.env` file. This bot will use the `/line/webhook` endpoint.

## Webhook URLs

Each bot will have its own webhook endpoint:
- Default: `https://your-domain.com/line/{bot_id}/webhook`
- Custom: As specified in `webhook_path`

Configure these webhook URLs in your LINE Developer Console for each bot.
