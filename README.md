# GeoDine-AI

A LINE Bot application for finding restaurants based on user requirements using natural language processing and Google Maps integration.

**Now supports multiple LINE bots!** Run multiple bots from a single server instance with independent configurations and user data.

**Includes Weather OOTD Bot:** Get weather forecasts and AI-generated outfit recommendations!

## Features

- **Multi-Bot Support**: Run multiple LINE bots from a single server with independent configurations
- **Natural Language Processing**: Parse user requests like "Find Japanese food near Central Park"
- **AI-Powered Understanding**: Optional integration with OpenAI's GPT-4o for advanced language comprehension
- **Location-Based Search**: Find restaurants near user's current location or specified places
- **Customizable Filters**: Search by cuisine type, price level, and operating status
- **Interactive UI**: Rich visual responses with restaurant details using LINE Flex Messages
- **Google Maps Integration**: Powered by Google Maps Places API for accurate restaurant data
- **Multi-language Support**: Automatic language detection and translation for user messages
- **Persistent Storage**: SQLite database for storing user locations and preferences per bot
- **API Security**: Protected endpoints with API key authentication
- **Flexible Configuration**: YAML-based bot configurations with environment variable support

## Architecture

![Sequence Diagram](GeoDine-AI%20Sequence%20Diagram.png)

The application consists of several key components:

- **LINE Bot (line_bot.py)**: Dynamically registers webhook endpoints for multiple bots
- **Bot Configuration (bot_config.py)**: Manages bot configurations from YAML files
- **Bot Registry (bot_registry.py)**: Factory pattern for managing multiple bot instances
- **Bot Handlers (line_bot_handler.py)**: Core message handling logic for all bots
- **Restaurant Finder (restaurant_finder.py)**: Interfaces with Google Maps API to find restaurants
- **Utils (utils.py)**: Provides text parsing capabilities with regex and/or OpenAI
- **Translation (translation.py)**: Handles language detection and translation using OpenAI
- **Language Pack (language_pack.py)**: Contains localized strings and messages
- **Database (database.py)**: Manages SQLite database operations with multi-bot support
- **Security (security.py)**: Handles API authentication and security
- **Server (server.py)**: FastAPI application that brings everything together

## Installation

### Prerequisites

- Python 3.8+
- LINE Developer Account
- Google Maps API Key
- OpenAI API Key (required for translation and optional for parsing)

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
   ```
   # Server Configuration
   HOST=0.0.0.0
   PORT=8000

   # API Keys
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   API_KEY=your_generated_api_key_here  # Generate with: openssl rand -hex 32

   # LINE Bot Configuration
   LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
   LINE_CHANNEL_SECRET=your_line_channel_secret_here

   # Feature Flags
   USE_AI_PARSING=true  # Set to false to use regex-based parsing
   ```

   > **Important**: Never commit your `.env` file to version control.

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

See `bots/README.md` for detailed configuration options and examples.

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

The bot currently supports:
- English (en)
- Traditional Chinese (zh-tw)
- Japanese (ja)
- Korean (ko)

## Weather OOTD Bot

In addition to restaurant finding, the project includes a Weather OOTD (Outfit of the Day) bot:

### Features
- 🌤️ **Weather Forecasts** - Real-time weather data from Open-Meteo API
- 👔 **AI Outfit Recommendations** - DALL-E generated outfit images
- 📍 **Location-Based** - Personalized for user location or defaults to Taipei
- 🎨 **Beautiful Visuals** - Weather emojis and styled images

### Quick Setup

1. **Create configuration:**
   ```bash
   cp bots/weather-ootd.yaml.example bots/weather-ootd.yaml
   ```

2. **Add credentials to `.env`:**
   ```env
   WEATHER_OOTD_ACCESS_TOKEN=your_token
   WEATHER_OOTD_SECRET=your_secret
   OPENAI_API_KEY=your_openai_key
   ```

3. **Restart server**

4. **Configure webhook:** `https://your-domain.com/line/weather-ootd/webhook`

### Usage
- Send "hi" or "help" for instructions
- Send "weather" for current weather
- Send "outfit" for outfit recommendation
- Share location for personalized results

### Daily Automated Broadcasts
- **Automated Daily Messages**: Schedule daily weather & outfit broadcasts to all subscribers via cron jobs
- **Rate Limiting**: Built-in delays to respect LINE API limits
- **Test Mode**: Test broadcasts before scheduling

**Setup Daily Broadcasts:**
```bash
# Test broadcast to a single user
curl -X POST "http://localhost:8000/broadcast/test" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"bot_id": "weather-ootd", "test_user_id": "YOUR_LINE_USER_ID"}'

# Schedule daily broadcast at 7 AM (add to crontab)
0 7 * * * curl -X POST "http://localhost:8000/broadcast/daily-weather" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"bot_id": "weather-ootd"}' >> /var/log/weather-broadcast.log 2>&1
```

**Full Documentation:**
- Weather Bot Setup: [WEATHER_BOT_SETUP.md](WEATHER_BOT_SETUP.md)
- Daily Broadcasts: [DAILY_BROADCAST_SETUP.md](DAILY_BROADCAST_SETUP.md)

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