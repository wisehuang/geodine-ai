# GeoDine-AI

A LINE Bot application for finding restaurants based on user requirements using natural language processing and Google Maps integration.

## Features

- **Natural Language Processing**: Parse user requests like "Find Japanese food near Central Park"
- **AI-Powered Understanding**: Optional integration with OpenAI's GPT-4o for advanced language comprehension
- **Location-Based Search**: Find restaurants near user's current location or specified places
- **Customizable Filters**: Search by cuisine type, price level, and operating status
- **Interactive UI**: Rich visual responses with restaurant details using LINE Flex Messages
- **Google Maps Integration**: Powered by Google Maps Places API for accurate restaurant data

## Architecture

![Sequence Diagram](sequence_diagram.png)

The application consists of several key components:

- **LINE Bot (line_bot.py)**: Handles webhook events from LINE platform
- **Restaurant Finder (restaurant_finder.py)**: Interfaces with Google Maps API to find restaurants
- **Utils (utils.py)**: Provides text parsing capabilities with regex and/or OpenAI
- **Server (server.py)**: FastAPI application that brings everything together

## Installation

### Prerequisites

- Python 3.8+
- LINE Developer Account
- Google Maps API Key
- OpenAI API Key (optional)

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

3. Create a `.env` file in the project root with your credentials:
   ```
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key
   LINE_CHANNEL_ACCESS_TOKEN=your_line_token
   LINE_CHANNEL_SECRET=your_line_secret
   HOST=0.0.0.0
   PORT=8000
   OPENAI_API_KEY=your_openai_api_key  # Optional
   USE_AI_PARSING=true  # Set to false to use regex-based parsing
   ```

## Running the Application

Start the server:
```
python -m src.server
```

The server will start on http://0.0.0.0:8000 with auto-reload enabled.

## API Endpoints

### LINE Bot

- **POST /line/webhook**: Webhook endpoint for LINE platform events

### Restaurant Finder

- **POST /restaurants/search**: Search for restaurants based on criteria
  - Parameters:
    - `location`: Geographic coordinates (latitude, longitude)
    - `keyword`: Search keyword (e.g., "vegetarian", "Japanese")
    - `radius`: Search radius in meters (default: 1000)
    - `type`: Place type (default: "restaurant")
    - `price_level`: Price level from 0-4
    - `open_now`: Whether to show only currently open restaurants

## Testing

### API Testing

Use FastAPI's built-in Swagger UI at http://localhost:8000/docs to test endpoints interactively.

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
   - User sends a text query like "Find Japanese food near Central Park"
   - The app parses the request using either regex or OpenAI
   - If location is found, restaurants are searched and results displayed
   - If no location is found, the app asks the user to share their location

2. **Location Message Flow**:
   - User shares their location via LINE
   - The app searches for nearby restaurants
   - Results are displayed as an interactive carousel

## Future Improvements

- Add user preference tracking
- Implement reservation capabilities
- Add multi-language support
- Enhance the restaurant recommendation algorithm 