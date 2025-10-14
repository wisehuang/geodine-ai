# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GeoDine-AI is a multi-bot LINE Bot platform that supports:
1. **Restaurant Finder Bot** - Natural language restaurant search using Google Maps API
2. **Weather OOTD Bot** - Weather forecasts with AI-generated outfit recommendations

The system uses a factory pattern to manage multiple independent LINE bots from a single server instance.


## Claude Usage Instructions and Command Guidelines

### Documentation Generation Control Instructions

To prevent Claude from automatically generating code documentation or technical files on every interaction, please keep the following instructions included in the preamble of each interaction:

- **Do not generate any documentation unless explicitly requested by me.**
- Generate documentation only when I explicitly instruct you with phrases like "please generate documentation" or "generate docs".
- Keep responses focused on the code and explanation only when no documentation generation is requested.

## Essential Commands

### Running the Application

```bash
# Start the server (auto-reload enabled)
python -m src.server

# First-time setup or after upgrading (migrates database schema)
python migrate_db.py

# Test image generation (Weather OOTD bot only)
python test_image_generation.py

# Test daily broadcast (requires API key)
curl -X POST "http://localhost:8000/broadcast/test" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"bot_id": "weather-ootd", "test_user_id": "YOUR_LINE_USER_ID"}'

# Check broadcast status
curl -X GET "http://localhost:8000/broadcast/status/weather-ootd" \
  -H "X-API-Key: your_api_key"
```

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Test YAML configuration syntax
python -c "import yaml; yaml.safe_load(open('bots/my-bot.yaml'))"

# Check environment variables
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('VARIABLE_NAME'))"

# Test weather service
python -c "from src.weather_service import WeatherService; print(WeatherService.get_today_weather())"

# Query database
sqlite3 geodine.db "SELECT * FROM bots;"
sqlite3 geodine.db ".schema users"
```

### Local Testing with ngrok

```bash
# Expose local server for LINE webhook testing
ngrok http 8000
# Then configure webhook URL in LINE Developer Console:
# https://your-ngrok-url.ngrok.io/line/{bot_id}/webhook
```

## Architecture

### Multi-Bot System

The codebase implements a **factory pattern with singleton registry** for managing multiple independent LINE bots:

```
FastAPI Server (src/server.py)
    ↓
LINE Bot Router (src/line_bot.py) - Dynamic endpoint registration
    ↓
Bot Registry (src/bot_registry.py) - Singleton factory managing bot instances
    ↓
Bot Instances - Each with independent LINE API clients
    ↓
Handler Selection - Routes to appropriate handler based on bot_type
    ├─ Restaurant Bot Handler (src/line_bot_handler.py)
    └─ Weather Bot Handler (src/weather_bot_handler.py)
```

### Key Design Patterns

1. **Singleton Registry** (`src/bot_registry.py`):
   - Single `BotRegistry` instance manages all bots
   - Creates `BotInstance` wrappers with LINE API clients
   - Provides lookup by `bot_id` or `webhook_path`

2. **Factory Pattern** (`src/line_bot.py`):
   - Dynamically creates webhook endpoints for each bot
   - Routes to correct handler based on `bot_type` field
   - Supports two handler types: "restaurant" (default) and "weather"

3. **Configuration Management** (`src/bot_config.py`):
   - YAML-based bot configurations in `bots/` directory
   - Environment variable substitution: `"${VAR_NAME}"`
   - Legacy `.env` support for backward compatibility

4. **Multi-Tenancy** (`src/database.py`):
   - Users isolated per bot using `bot_id` foreign key
   - Composite unique constraint: `(bot_id, line_user_id)`
   - All database functions accept `bot_id` parameter

### Handler Routing Logic

When a webhook event arrives:
1. FastAPI routes to `/line/{webhook_path}` endpoint
2. Webhook handler validates LINE signature for specific bot
3. Based on `bot_instance.bot_type`:
   - `"weather"` → `register_weather_bot_handlers()` in `src/weather_bot_handler.py`
   - `"restaurant"` (or any other value) → `register_bot_handlers()` in `src/line_bot_handler.py`
4. Handler processes event using bot's specific configuration and LINE API client

### Database Schema

```sql
-- Bots table (multi-bot support)
CREATE TABLE bots (
    id INTEGER PRIMARY KEY,
    bot_id TEXT UNIQUE NOT NULL,  -- e.g., "geodine-ai", "weather-ootd"
    name TEXT NOT NULL,
    created_at TIMESTAMP
);

-- Users table (per-bot isolation)
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    bot_id INTEGER NOT NULL,      -- Foreign key to bots table
    line_user_id TEXT NOT NULL,
    created_at TIMESTAMP,
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    UNIQUE(bot_id, line_user_id)  -- User unique per bot
);

-- Other tables: locations, preferences, interaction_logs
-- All reference users table for per-bot data isolation
```

## Bot Configuration

### Adding a New Bot

1. **Create YAML configuration** in `bots/` directory:
```yaml
bot_id: "my-bot"                              # Unique identifier
name: "My Restaurant Bot"                     # Human-readable name
channel_access_token: "${MY_BOT_TOKEN}"       # LINE credentials (from .env)
channel_secret: "${MY_BOT_SECRET}"
bot_type: "restaurant"                        # "restaurant" or "weather"
webhook_path: "/line/my-bot/webhook"          # Optional, defaults to /line/{bot_id}/webhook
use_ai_parsing: true                          # Use OpenAI for parsing (restaurant bot only)
default_radius: 1000                          # Search radius in meters
default_language: "en"                        # Default language code
enabled: true                                 # Enable/disable bot
```

2. **Add credentials to `.env`**:
```env
MY_BOT_TOKEN=your_line_access_token
MY_BOT_SECRET=your_line_channel_secret
```

3. **Restart server** - Bot automatically loads and registers webhook endpoint

4. **Configure LINE webhook** in LINE Developer Console:
   - URL: `https://your-domain.com/line/my-bot/webhook`

### Weather OOTD Bot Configuration

Weather bot requires additional `image_prompt_template` field for custom image generation:

```yaml
bot_type: "weather"
image_prompt_template: "Your custom prompt with variables: {weather_description}, {temperature}, {conditions}"
```

Variables automatically populated from weather data:
- `{weather_description}` - English weather condition (e.g., "Clear sky")
- `{temperature}` - Temperature range (e.g., "23°C - 34°C")
- `{conditions}` - Chinese weather analysis (e.g., "炎熱", "中雨、涼爽")

### Configuration Loading

Priority order:
1. **YAML files** in `bots/*.yaml` (highest priority)
2. **Legacy .env** variables (`LINE_CHANNEL_ACCESS_TOKEN`, `LINE_CHANNEL_SECRET`)
   - Creates bot with `bot_id: "geodine-ai"`
   - Uses original webhook path `/line/webhook`

## Bot-Specific Services

### Restaurant Bot (`bot_type: "restaurant"`)

**Handler**: `src/line_bot_handler.py`

**Key Components**:
- `src/restaurant_finder.py` - Google Maps Places API integration
- `src/utils.py` - Request parsing (regex or OpenAI function calling)
- `src/translation.py` - Language detection and translation

**Text Message Flow**:
1. Detect language and translate to English if needed
2. Use OpenAI function calling to determine if request is about restaurants
3. Parse request using regex or OpenAI (based on `use_ai_parsing` flag)
4. If location found → search and display results
5. If no location → ask user to share location

**Location Message Flow**:
1. Save location to database with `bot_id`
2. Search for nearby restaurants
3. Display as LINE Flex Message carousel

### Weather OOTD Bot (`bot_type: "weather"`)

**Handler**: `src/weather_bot_handler.py`

**Key Components**:
- `src/weather_service.py` - Open-Meteo API integration (free, no key required)
- `src/image_generation_service.py` - OpenAI Images API direct REST calls

**Default Location**: Taipei, Taiwan (25.01°N, 121.46°E)

**Text Commands**:
- `hi`, `hello`, `help` - Welcome message with instructions
- `weather` - Current weather info
- `outfit`, `ootd` - Generate AI outfit recommendation

**Location Message Flow**:
1. Save location to database with `bot_id`
2. Fetch weather data from Open-Meteo API
3. Analyze weather conditions (temperature, precipitation)
4. Generate Chinese condition descriptions (炎熱, 溫暖, 舒適, 涼爽, 寒冷, 大雨, 中雨, 小雨)
5. Format custom prompt with weather variables
6. Call OpenAI Images API (DALL-E 3) with formatted prompt
7. Send weather info + generated image to user

**Image Generation Flow**:
```python
# src/image_generation_service.py
# 1. Analyze weather data
weather_description = "Mainly clear"          # From weather_code
temperature = "23.5°C - 34.5°C"               # From temp_min/temp_max
conditions = "炎熱"                            # Based on avg temperature & precipitation

# 2. Format custom prompt template
prompt = template.format(
    weather_description=weather_description,
    temperature=temperature,
    conditions=conditions
)

# 3. POST to OpenAI Images API
POST https://api.openai.com/v1/images/generations
{
    "model": "dall-e-3",
    "prompt": prompt,
    "n": 1,
    "size": "1024x1024",
    "quality": "standard"
}
```

## Common Code Patterns

### Accessing Bot Configuration

```python
# In handlers, bot_instance is passed as parameter
bot_instance: BotInstance

# Access configuration
bot_id = bot_instance.bot_id
custom_prompt = bot_instance.config.image_prompt_template
use_ai = bot_instance.use_ai_parsing

# Use bot's LINE API client
bot_instance.api.reply_message(reply_token, messages)
bot_instance.api.push_message(user_id, messages)
```

### Database Operations (Bot-Aware)

```python
from src.database import save_user_location, get_user_location_for_search

# All database functions accept bot_id parameter
save_user_location(
    line_user_id=user_id,
    latitude=lat,
    longitude=lng,
    bot_id=bot_instance.bot_id  # Always pass bot_id
)

location = get_user_location_for_search(user_id, bot_id)
```

### Safe Reply Pattern (Weather Bot)

```python
# src/weather_bot_handler.py uses safe_reply_or_push()
# Handles expired reply tokens by falling back to push messages
safe_reply_or_push(
    bot_instance,
    event,
    TextSendMessage(text="message")
)
```

## Environment Variables

Required in `.env` file:

```env
# Server
HOST=0.0.0.0
PORT=8000

# API Keys (required for both bot types)
GOOGLE_MAPS_API_KEY=...      # Restaurant bot only
OPENAI_API_KEY=...            # Both bots (translation + image generation)
API_KEY=...                   # Internal API security (generate with: openssl rand -hex 32)

# Legacy Single Bot Support (optional, creates bot_id "geodine-ai")
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_CHANNEL_SECRET=...

# Per-Bot Credentials (referenced in YAML configs)
MY_BOT_ACCESS_TOKEN=...
MY_BOT_SECRET=...
WEATHER_OOTD_ACCESS_TOKEN=...
WEATHER_OOTD_SECRET=...

# Feature Flags
USE_AI_PARSING=true          # Global default, can be overridden per bot
```

## Database Migration

When upgrading from single-bot to multi-bot setup:

```bash
# Run migration (creates backup automatically)
python migrate_db.py
```

**What it does**:
1. Creates backup: `geodine.db.backup.<timestamp>`
2. Creates `bots` table
3. Adds default "geodine-ai" bot
4. Migrates `users` table to add `bot_id` column
5. Associates existing users with default bot
6. Updates constraints (UNIQUE on `bot_id + line_user_id`)

**Safety**: Idempotent - safe to run multiple times

## Important Implementation Details

### OpenAI API Usage

**Restaurant Bot**:
- Uses OpenAI SDK (`openai` package) for function calling and translation
- Model: GPT-4o for text understanding

**Weather Bot**:
- Uses **direct REST API calls** (not SDK) for image generation
- Endpoint: `https://api.openai.com/v1/images/generations`
- Model: DALL-E 3 (configurable to DALL-E 2 for cost savings)
- Implementation: `requests` library with manual headers

### Duplicate Event Prevention

Weather bot implements event deduplication:
```python
# src/weather_bot_handler.py
processed_events = {}  # Tracks event IDs with timestamps
# Skips events seen in last 5 minutes
```

### LINE API Reply Token Limitations

Reply tokens expire quickly. Weather bot uses fallback pattern:
1. Try `api.reply_message(reply_token, messages)`
2. If "Invalid reply token" error → `api.push_message(user_id, messages)`

## Testing LINE Webhooks Locally

1. **Start server**: `python -m src.server`
2. **Start ngrok**: `ngrok http 8000`
3. **Configure LINE Developer Console**:
   - Webhook URL: `https://xxx.ngrok.io/line/{bot_id}/webhook`
   - Enable "Use webhook"
   - Click "Verify" button
4. **Check server logs** for incoming events
5. **Send test message** from LINE app

## Daily Broadcast System

The Weather OOTD bot supports automated daily broadcasts via cron jobs.

### Architecture

```
Cron Job → POST /broadcast/daily-weather
    ↓
DailyBroadcastService (src/daily_broadcast_service.py)
    ↓
For each subscriber:
    1. Fetch weather (Open-Meteo API)
    2. Generate image (OpenAI DALL-E 3) ← 5-10 seconds
    3. Send via LINE API
    4. Delay (rate limiting)
```

### Key Components

**src/daily_broadcast_service.py**: Main broadcast service
- `DailyBroadcastService.broadcast_daily_weather()` - Broadcasts to all subscribers
- `DailyBroadcastService.send_test_broadcast()` - Test to single user
- Built-in rate limiting with `delay_between_users` parameter

**src/broadcast_router.py**: FastAPI endpoints
- `POST /broadcast/daily-weather` - Main broadcast endpoint
- `POST /broadcast/test` - Test broadcast
- `GET /broadcast/status/{bot_id}` - Status and subscriber count

**src/database.py**: Database functions
- `get_all_bot_subscribers()` - Returns all users for a bot with location data

### Usage

**Test Broadcast**:
```bash
curl -X POST "http://localhost:8000/broadcast/test" \
  -H "X-API-Key: your_api_key" \
  -d '{"bot_id": "weather-ootd", "test_user_id": "USER_ID"}'
```

**Schedule Daily Broadcast (crontab)**:
```cron
# Daily at 7 AM
0 7 * * * curl -X POST "http://localhost:8000/broadcast/daily-weather" \
  -H "X-API-Key: your_api_key" \
  -d '{"bot_id": "weather-ootd"}' >> /var/log/weather-broadcast.log 2>&1
```

**Important Notes**:
- Image generation is synchronous and takes time (~5-10 seconds per user)
- Rate limiting prevents LINE API throttling (default: 0.5s between users)
- For 100 subscribers: ~8-15 minutes total broadcast time
- Errors for individual users don't stop the broadcast

**Full Documentation**: See [DAILY_BROADCAST_SETUP.md](DAILY_BROADCAST_SETUP.md)

## Key Files for Modifications

**Adding New Bot Type**:
- `src/bot_config.py` - Add new fields to `BotConfig` dataclass if needed
- `src/line_bot.py` - Add new handler registration in `create_webhook_endpoint()`
- Create new handler file: `src/your_bot_handler.py`

**Modifying Restaurant Search**:
- `src/restaurant_finder.py` - Google Maps API integration
- `src/utils.py` - Request parsing logic
- `src/line_bot_handler.py` - Message handling and response formatting

**Modifying Weather/Outfit Generation**:
- `src/weather_service.py` - Weather data fetching and analysis
- `src/image_generation_service.py` - Image generation and prompt formatting
- `src/weather_bot_handler.py` - Message handling and user flow

**Database Schema Changes**:
- `src/database.py` - Update schema and functions
- Create new migration script similar to `migrate_db.py`

## Documentation

**Setup Guides**:
- `README.md` - Main documentation, installation, running the app
- `MULTI_BOT_GUIDE.md` - Comprehensive multi-bot architecture guide
- `WEATHER_BOT_SETUP.md` - Weather OOTD bot complete setup
- `CUSTOM_PROMPT_GUIDE.md` - Custom image prompt configuration

**Quick References**:
- `QUICK_START_MULTI_BOT.md` - 5-minute multi-bot setup
- `WEATHER_BOT_QUICKREF.md` - Weather bot quick reference
- `bots/README.md` - Bot configuration options

**Implementation Details**:
- `CHANGES.md` - Complete change summary for multi-bot refactor
- `API_UPDATE_SUMMARY.md` - OpenAI API direct REST implementation
- `FINAL_IMPLEMENTATION_SUMMARY.md` - Weather bot implementation summary
