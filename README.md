# GeoDine-AI

A LINE Bot application for finding restaurants based on user requirements using natural language processing and Google Maps integration.

**Now supports multiple LINE bots!** Run multiple bots from a single server instance with independent configurations and user data.

**Includes Weather OOTD Bot:** Get weather forecasts and AI-generated outfit recommendations!

## Features

### Core Platform
- **Multi-Bot Support**: Run multiple independent LINE bots from a single server instance
- **Flexible Configuration**: YAML-based bot configurations with environment variable support
- **Multi-Tenancy**: Isolated user data per bot using SQLite database
- **API Security**: Protected endpoints with API key authentication
- **MCP Integration**: FastAPI-MCP server for advanced integrations
- **Static File Serving**: Automated image hosting for generated content

### Restaurant Finder Bot
- **Natural Language Processing**: Parse user requests like "Find Japanese food near Central Park"
- **AI-Powered Understanding**: OpenAI GPT-4o integration for advanced language comprehension (optional)
- **Location-Based Search**: Find restaurants near user's location or specified places
- **Customizable Filters**: Search by cuisine type, price level, and operating status
- **Interactive UI**: Rich visual responses with restaurant details using LINE Flex Messages
- **Google Maps Integration**: Powered by Google Maps Places API for accurate restaurant data
- **Multi-language Support**: Automatic language detection and translation (English, Chinese, Japanese, Korean)
- **Dual Parsing Modes**: Choose between regex-based or AI-powered request parsing

### Weather OOTD Bot
- **Weather Forecasts**: Real-time weather data from Open-Meteo API (no API key required)
- **AI Outfit Recommendations**: DALL-E 3 generated outfit images based on weather conditions
- **Location-Aware**: Personalized forecasts for user location or defaults to Taipei, Taiwan
- **Beautiful Visuals**: Weather emojis and professionally styled images
- **Daily Broadcasts**: Automated daily weather + outfit messages via cron jobs
- **Custom Prompts**: Configurable image generation prompts with weather variable substitution
- **Rate Limiting**: Built-in delays to respect LINE API limits

## Architecture

![Sequence Diagram](GeoDine-AI%20Sequence%20Diagram.png)

The application uses a **factory pattern with singleton registry** for managing multiple independent LINE bots:

```
FastAPI Server (server.py)
    ↓
LINE Bot Router (line_bot.py) - Dynamic endpoint registration
    ↓
Bot Registry (bot_registry.py) - Singleton factory managing bot instances
    ↓
Bot Instances - Each with independent LINE API clients
    ↓
Handler Selection - Routes to appropriate handler based on bot_type
    ├─ Restaurant Bot Handler (line_bot_handler.py)
    └─ Weather Bot Handler (weather_bot_handler.py)
```

### Key Components

**Core System:**
- **server.py**: FastAPI application with MCP integration and static file serving
- **line_bot.py**: Dynamic webhook endpoint registration for multiple bots
- **bot_config.py**: YAML-based configuration management with environment variable substitution
- **bot_registry.py**: Singleton factory pattern for bot instance management
- **database.py**: SQLite database with multi-bot support and data isolation
- **security.py**: API key authentication and LINE signature verification
- **broadcast_router.py**: Daily broadcast endpoints for automated messaging

**Restaurant Bot:**
- **line_bot_handler.py**: Message handling and response logic
- **restaurant_finder.py**: Google Maps Places API integration
- **utils.py**: Request parsing (regex or OpenAI function calling)
- **translation.py**: Language detection and translation using OpenAI
- **language_pack.py**: Localized strings and messages

**Weather Bot:**
- **weather_bot_handler.py**: Weather bot message handling with event deduplication
- **weather_service.py**: Open-Meteo API integration for weather data
- **image_generation_service.py**: OpenAI DALL-E 3 direct REST API calls
- **daily_broadcast_service.py**: Automated daily broadcast service with rate limiting

## Installation

### Prerequisites

- Python 3.8+
- LINE Developer Account (for each bot)
- **For Restaurant Bot:**
  - Google Maps API Key
  - OpenAI API Key (for translation and optional AI parsing)
- **For Weather Bot:**
  - OpenAI API Key (for DALL-E 3 image generation)
  - No weather API key needed (uses free Open-Meteo API)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/geodine-ai.git
   cd geodine-ai
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your credentials. You can use `.env.example` as a template:
   ```env
   # Server Configuration
   HOST=0.0.0.0
   PORT=8000

   # API Keys
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   API_KEY=your_generated_api_key_here  # Generate with: openssl rand -hex 32

   # Legacy Single Bot Support (optional - creates bot_id "geodine-ai")
   LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
   LINE_CHANNEL_SECRET=your_line_channel_secret_here

   # Per-Bot Credentials (referenced in YAML configs)
   MY_BOT_ACCESS_TOKEN=your_bot_token
   MY_BOT_SECRET=your_bot_secret
   WEATHER_OOTD_ACCESS_TOKEN=your_weather_bot_token
   WEATHER_OOTD_SECRET=your_weather_bot_secret

   # Feature Flags
   USE_AI_PARSING=true  # Global default, can be overridden per bot in YAML
   ```

   > **Important**: Never commit your `.env` file to version control.

4. Create bot configuration files in the `bots/` directory (see examples in `bots/*.yaml.example`)

## Running the Application

### First-Time Setup

If you have an existing database from a previous version, run the migration script:
```bash
python migrate_db.py
```

### Starting the Server

Start the server:
```bash
python -m src.server
```

The server will start on http://0.0.0.0:8000 with auto-reload enabled.

The server will automatically:
- Load bot configurations from the `bots/` directory
- Create webhook endpoints for each enabled bot
- Display registered bots and their webhook URLs in the console

## Managing Multiple Bots

### Adding a New Bot

1. **Create a bot configuration file:**
   ```bash
   cp bots/example-bot.yaml.example bots/my-bot.yaml
   ```

2. **Edit the configuration:**
   ```yaml
   bot_id: "my-bot"
   name: "My Food Bot"
   channel_access_token: "${MY_BOT_ACCESS_TOKEN}"
   channel_secret: "${MY_BOT_SECRET}"
   use_ai_parsing: true
   default_radius: 1000
   default_language: "en"
   enabled: true
   ```

3. **Add credentials to `.env`:**
   ```env
   MY_BOT_ACCESS_TOKEN=your_access_token_here
   MY_BOT_SECRET=your_secret_here
   ```

4. **Restart the server** to load the new bot

5. **Configure webhook in LINE Developer Console:**
   - Webhook URL: `https://your-domain.com/line/my-bot/webhook`
   - Enable webhook
   - Verify the webhook

### Bot Configuration Options

Configuration fields for bot YAML files:

**Required:**
- `bot_id`: Unique identifier (used in URLs and database)
- `name`: Human-readable name
- `channel_access_token`: LINE channel access token
- `channel_secret`: LINE channel secret

**Optional:**
- `bot_type`: `"restaurant"` (default) or `"weather"`
- `webhook_path`: Custom webhook path (defaults to `/line/{bot_id}/webhook`)
- `description`: Human-readable description
- `use_ai_parsing`: `true` (default) or `false` - Use OpenAI for parsing (restaurant bot only)
- `default_radius`: Search radius in meters (default: 1000)
- `default_language`: Default language code (default: "en")
- `enabled`: `true` (default) or `false` - Enable/disable bot
- `image_prompt_template`: Custom DALL-E 3 prompt (weather bot only)

**Weather Bot Prompt Variables:**
- `{weather_description}`: English weather condition
- `{temperature}`: Temperature range
- `{conditions}`: Chinese weather analysis

See `bots/README.md` and example files for detailed configuration options.

### Managing Existing Bots

- **Disable a bot**: Set `enabled: false` in its configuration file
- **Update bot settings**: Edit the YAML file and restart the server
- **Remove a bot**: Delete its configuration file and restart the server

### Legacy Support

The system maintains backward compatibility with the original single-bot setup:
- Bots configured via `.env` variables (`LINE_CHANNEL_ACCESS_TOKEN`, `LINE_CHANNEL_SECRET`)
- Will automatically create a bot with ID "geodine-ai"
- Uses the original webhook path `/line/webhook`

## API Endpoints

### LINE Bot Webhooks

Each bot has its own webhook endpoint:

- **POST /line/{bot_id}/webhook**: Webhook for a specific bot
  - Requires valid LINE signature in X-Line-Signature header
  - Example: `/line/geodine-ai/webhook`, `/line/my-bot/webhook`

For backward compatibility:
- **POST /line/webhook**: Legacy webhook endpoint for "geodine-ai" bot

### Restaurant Finder

- **POST /restaurants/search**: Search for restaurants based on criteria
  - Requires valid API key in X-API-Key header
  - Parameters:
    - `location`: Geographic coordinates (latitude, longitude)
    - `keyword`: Search keyword (e.g., "vegetarian", "Japanese")
    - `radius`: Search radius in meters (default: 1000)
    - `type`: Place type (default: "restaurant")
    - `price_level`: Price level from 0-4
    - `open_now`: Whether to show only currently open restaurants

### Daily Broadcast (Weather Bot)

- **POST /broadcast/daily-weather**: Broadcast daily weather & outfit to all subscribers
  - Requires valid API key in X-API-Key header
  - Parameters:
    - `bot_id`: Bot ID to broadcast from (default: "weather-ootd")
    - `delay_between_users`: Delay in seconds between users (default: 0.5)
  - Returns broadcast statistics (total, successful, failed)

- **POST /broadcast/test**: Send test broadcast to a single user
  - Requires valid API key in X-API-Key header
  - Parameters:
    - `bot_id`: Bot ID to test
    - `test_user_id`: LINE user ID to send test to

- **GET /broadcast/status/{bot_id}**: Get broadcast status and subscriber count
  - Requires valid API key in X-API-Key header

## API Security

The application implements several security measures:

1. **API Key Authentication**:
   - All `/restaurants/*` endpoints require a valid API key
   - The API key must be provided in the `X-API-Key` header
   - The API key is verified using secure comparison to prevent timing attacks

2. **LINE Signature Verification**:
   - All LINE webhook requests are verified using the LINE signature
   - The signature is validated using the LINE SDK

3. **Environment Variables**:
   - All sensitive credentials are stored in environment variables
   - The `.env` file should never be committed to version control

4. **Photo URL Security**:
   - When displaying restaurant photos, ensure you use fully qualified URLs (https://...) 
   - LINE API requires absolute URLs for images in Flex Messages

## Testing

### API Testing

Use FastAPI's built-in Swagger UI at http://localhost:8000/docs to test endpoints interactively.
Note that you'll need to provide the API key in the "Authorize" dialog.

### LINE Bot Testing

1. Use a tool like [ngrok](https://ngrok.com/) to expose your local server:
   ```
   ngrok http 8000
   ```

2. Set the webhook URL in LINE Developer Console to your ngrok URL + `/line/webhook`

3. Start chatting with your LINE Bot

## Understanding the Sequence

The application flows in two main paths:

1. **Text Message Flow**: 
   - User sends a text message
   - The bot detects the language and translates if necessary
   - The bot uses OpenAI function calling to determine if the message is about finding a restaurant
   - If not, the bot replies that it can only help with restaurant recommendations
   - If yes, the app parses the request using either regex or OpenAI
   - If location is found, restaurants are searched and results displayed
   - If no location is found, the app asks the user to share their location

2. **Location Message Flow**:
   - User shares their location via LINE
   - The app stores the location in the database
   - The app searches for nearby restaurants
   - Results are displayed as an interactive carousel

## Supported Languages

The Restaurant Bot supports automatic language detection and translation for:
- English (en)
- Traditional Chinese (zh-tw)
- Japanese (ja)
- Korean (ko)

The Weather Bot provides forecasts and outfit recommendations in English with Chinese weather condition descriptions.

## Weather OOTD Bot

The Weather OOTD (Outfit of the Day) bot provides weather forecasts with AI-generated outfit recommendations.

### Features
- 🌤️ **Weather Forecasts**: Real-time weather data from Open-Meteo API (no API key required)
- 👔 **AI Outfit Recommendations**: DALL-E 3 generated outfit images based on current weather
- 📍 **Location-Based**: Personalized for user location or defaults to Taipei, Taiwan
- 🎨 **Beautiful Visuals**: Weather emojis and professionally styled images
- 🔔 **Daily Broadcasts**: Automated morning messages via cron jobs
- ⚙️ **Customizable Prompts**: Configure image generation prompts with weather variables

### Quick Setup

1. **Create configuration:**
   ```bash
   cp bots/weather-ootd.yaml.example bots/weather-ootd.yaml
   ```

2. **Edit the configuration** to customize the image prompt template:
   ```yaml
   bot_id: "weather-ootd"
   name: "Weather OOTD Bot"
   channel_access_token: "${WEATHER_OOTD_ACCESS_TOKEN}"
   channel_secret: "${WEATHER_OOTD_SECRET}"
   bot_type: "weather"
   enabled: true
   image_prompt_template: "Your custom prompt with {weather_description}, {temperature}, {conditions}"
   ```

3. **Add credentials to `.env`:**
   ```env
   WEATHER_OOTD_ACCESS_TOKEN=your_token
   WEATHER_OOTD_SECRET=your_secret
   OPENAI_API_KEY=your_openai_key
   ```

4. **Restart server**

5. **Configure webhook in LINE Developer Console:**
   - Webhook URL: `https://your-domain.com/line/weather-ootd/webhook`

### User Commands
- `hi`, `hello`, `help`: Display welcome message with instructions
- `weather`: Get current weather forecast
- `outfit`, `ootd`: Generate AI outfit recommendation based on weather
- **Share location**: Save location for personalized forecasts

### Daily Automated Broadcasts

Schedule automated daily weather + outfit messages to all subscribers:

**Test Broadcast:**
```bash
curl -X POST "http://localhost:8000/broadcast/test" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"bot_id": "weather-ootd", "test_user_id": "YOUR_LINE_USER_ID"}'
```

**Check Status:**
```bash
curl -X GET "http://localhost:8000/broadcast/status/weather-ootd" \
  -H "X-API-Key: your_api_key"
```

**Schedule Daily Broadcast (crontab):**
```bash
# Daily at 7 AM
0 7 * * * curl -X POST "http://localhost:8000/broadcast/daily-weather" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"bot_id": "weather-ootd"}' >> /var/log/weather-broadcast.log 2>&1
```

**Important Notes:**
- Image generation takes ~5-10 seconds per user
- Built-in rate limiting prevents LINE API throttling
- For 100 subscribers: ~8-15 minutes total broadcast time
- Individual errors don't stop the broadcast

### Technical Details

- **Weather Data**: Open-Meteo API (free, no key required)
- **Image Generation**: OpenAI DALL-E 3 via direct REST API
- **Default Location**: Taipei, Taiwan (25.01°N, 121.46°E)
- **Event Deduplication**: Prevents duplicate processing within 5 minutes
- **Reply Token Fallback**: Automatically uses push messages if reply token expires

**Full Documentation:**
- Complete Setup Guide: [WEATHER_BOT_SETUP.md](WEATHER_BOT_SETUP.md)
- Daily Broadcast Setup: [DAILY_BROADCAST_SETUP.md](DAILY_BROADCAST_SETUP.md)
- Custom Prompts: [CUSTOM_PROMPT_GUIDE.md](CUSTOM_PROMPT_GUIDE.md)

## Upgrading from Single Bot to Multi-Bot

If you're upgrading from an earlier version:

1. **Backup your database:**
   ```bash
   cp geodine.db geodine.db.backup
   ```

2. **Install new dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the migration script:**
   ```bash
   python migrate_db.py
   ```

4. **Your existing bot will continue to work** with the legacy webhook endpoint `/line/webhook`

5. **Add new bots** by creating configuration files in the `bots/` directory

## Troubleshooting

### Bot not loading

- Check that the YAML file is valid and in the `bots/` directory
- Verify that `enabled: true` in the configuration
- Check server logs for error messages
- Ensure environment variables are set correctly

### Webhook not working

- Verify webhook URL in LINE Developer Console
- Check that the webhook path matches the configuration
- Ensure LINE signature verification is passing
- Check server logs for webhook errors

### Database issues

- Run `python migrate_db.py` if upgrading from an older version
- Check file permissions on `geodine.db`
- Verify SQLite is working: `sqlite3 geodine.db ".tables"`

## Future Improvements

- Add user preference tracking per bot
- Implement reservation capabilities
- Enhance the restaurant recommendation algorithm
- Add support for restaurant reviews and ratings
- Implement caching for frequently accessed data
- Add rate limiting for API endpoints per bot
- Implement JWT authentication for additional security
- Add bot analytics and usage metrics
- Support for hot-reloading bot configurations 