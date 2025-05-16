# GeoDine-AI

A LINE Bot application for finding restaurants based on user requirements using natural language processing and Google Maps integration.

## Features

- **Natural Language Processing**: Parse user requests like "Find Japanese food near Central Park"
- **AI-Powered Understanding**: Optional integration with OpenAI's GPT-4o for advanced language comprehension
- **Location-Based Search**: Find restaurants near user's current location or specified places
- **Customizable Filters**: Search by cuisine type, price level, and operating status
- **Interactive UI**: Rich visual responses with restaurant details using LINE Flex Messages
- **Google Maps Integration**: Powered by Google Maps Places API for accurate restaurant data
- **Multi-language Support**: Automatic language detection and translation for user messages
- **Persistent Storage**: SQLite database for storing user locations and preferences
- **API Security**: Protected endpoints with API key authentication

## Architecture

![Sequence Diagram](GeoDine-AI%20Sequence%20Diagram.png)

The application consists of several key components:

- **LINE Bot (line_bot.py)**: Handles webhook events from LINE platform
- **Restaurant Finder (restaurant_finder.py)**: Interfaces with Google Maps API to find restaurants
- **Utils (utils.py)**: Provides text parsing capabilities with regex and/or OpenAI
- **Translation (translation.py)**: Handles language detection and translation using OpenAI
- **Language Pack (language_pack.py)**: Contains localized strings and messages
- **Database (database.py)**: Manages SQLite database operations
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

Start the server:
```
python -m src.server
```

The server will start on http://0.0.0.0:8000 with auto-reload enabled.

## API Endpoints

### LINE Bot

- **POST /line/webhook**: Webhook endpoint for LINE platform events
  - Requires valid LINE signature in X-Line-Signature header

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

## Future Improvements

- Add user preference tracking
- Implement reservation capabilities
- Enhance the restaurant recommendation algorithm
- Add support for restaurant reviews and ratings
- Implement caching for frequently accessed data
- Add rate limiting for API endpoints
- Implement JWT authentication for additional security 