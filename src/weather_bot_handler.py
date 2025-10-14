"""
Weather OOTD Bot message handlers
Refactored to use clean architecture with base handler
"""
import os
from linebot.models import (
    MessageEvent, TextMessage, LocationMessage,
    TextSendMessage, ImageSendMessage
)

from src.weather_service import WeatherService, get_location_name
from src.image_generation_service import get_image_service
from src.database import save_user_location, get_user_location_for_search
from src.bot_registry import BotInstance
from src.handlers.base_handler import BaseLineHandler


class WeatherBotHandler(BaseLineHandler):
    """
    Handler for weather OOTD bot.
    Extends BaseLineHandler with weather-specific functionality.
    """

    def __init__(self, bot_instance: BotInstance):
        """Initialize weather bot handler"""
        super().__init__(bot_instance)

    def handle_text_message(self, event):
        """Handle text messages for weather bot"""
        user_id = event.source.user_id
        text = event.message.text.lower().strip()

        print(f"Weather bot received text: {text} from user {user_id}")

        # Check for greeting or help messages
        greetings = ["hi", "hello", "hey", "start", "help"]
        if any(greeting in text for greeting in greetings):
            welcome_message = (
                "👋 Welcome to Weather OOTD Bot!\n\n"
                "I help you decide what to wear based on the weather. 👔☀️\n\n"
                "📍 Please share your location to get started, "
                "or I'll use Taipei, Taiwan as the default location.\n\n"
                "Commands:\n"
                "• Share location - Get weather & outfit\n"
                "• 'weather' - Get current weather\n"
                "• 'outfit' - Generate outfit recommendation"
            )
            self.safe_reply_or_push(event, TextSendMessage(text=welcome_message))
            return

        # Check for weather request
        if "weather" in text:
            self.send_weather_info(event, user_id)
            return

        # Check for outfit request
        if "outfit" in text or "ootd" in text or "recommend" in text:
            self.generate_and_send_outfit(event, user_id)
            return

        # Default response
        default_message = (
            "I can help you with:\n"
            "• 'weather' - Check current weather\n"
            "• 'outfit' / 'ootd' - Get outfit recommendation\n"
            "• Share your location for personalized results\n\n"
            "What would you like to know?"
        )
        self.safe_reply_or_push(event, TextSendMessage(text=default_message))

    def handle_location_message(self, event):
        """Handle location messages for weather bot"""
        user_id = event.source.user_id
        latitude = event.message.latitude
        longitude = event.message.longitude
        address = event.message.address if hasattr(event.message, 'address') else None

        print(f"Weather bot received location from user {user_id}: {latitude}, {longitude}")

        # Save user location to database
        location_id = save_user_location(
            line_user_id=user_id,
            latitude=latitude,
            longitude=longitude,
            address=address,
            bot_id=self.bot_id
        )

        # Get location name
        location_name = address if address else get_location_name(latitude, longitude)

        # Send confirmation message
        confirmation = f"📍 Location saved: {location_name}\n\n⏳ Fetching weather data and generating outfit recommendation..."

        self.safe_reply_or_push(event, TextSendMessage(text=confirmation))

        # Generate and send weather + outfit
        self.generate_and_send_outfit(event, user_id, show_confirmation=False)

    def send_weather_info(self, event, user_id: str):
        """Send weather information to user"""
        # Get user location from database
        location = get_user_location_for_search(user_id, self.bot_id)

        if location:
            latitude = location['lat']
            longitude = location['lng']
            location_name = get_location_name(latitude, longitude)
        else:
            # Use default location (Taipei)
            latitude = WeatherService.DEFAULT_LATITUDE
            longitude = WeatherService.DEFAULT_LONGITUDE
            location_name = "Taipei, Taiwan (default)"

        # Fetch weather data
        weather_data = WeatherService.get_today_weather(latitude, longitude)

        if weather_data:
            weather_summary = WeatherService.format_weather_summary(weather_data)
            message = f"🌤️ Weather for {location_name}\n\n{weather_summary}"
        else:
            message = "❌ Unable to fetch weather data. Please try again later."

        self.safe_reply_or_push(event, TextSendMessage(text=message))

    def generate_and_send_outfit(
        self,
        event,
        user_id: str,
        show_confirmation: bool = True
    ):
        """Generate outfit recommendation based on weather and send to user"""
        try:
            # Get user location from database
            location = get_user_location_for_search(user_id, self.bot_id)

            if location:
                latitude = location['lat']
                longitude = location['lng']
                location_name = get_location_name(latitude, longitude)
            else:
                # Use default location (Taipei)
                latitude = WeatherService.DEFAULT_LATITUDE
                longitude = WeatherService.DEFAULT_LONGITUDE
                location_name = "Taipei, Taiwan (default)"

                # Inform user about default location
                if show_confirmation:
                    default_msg = (
                        f"📍 Using default location: {location_name}\n"
                        "💡 Share your location for personalized recommendations!\n\n"
                        "⏳ Generating outfit recommendation..."
                    )
                    self.safe_reply_or_push(event, TextSendMessage(text=default_msg))

            # Fetch weather data
            weather_data = WeatherService.get_today_weather(latitude, longitude)

            if not weather_data:
                error_msg = "❌ Unable to fetch weather data. Please try again later."
                self.api.push_message(user_id, TextSendMessage(text=error_msg))
                return

            # Generate weather context for outfit recommendation
            weather_context = WeatherService.get_outfit_recommendation_context(weather_data)
            weather_summary = WeatherService.format_weather_summary(weather_data)

            # Send weather info first
            weather_msg = f"🌤️ Weather for {location_name}\n\n{weather_summary}\n\n🎨 Generating your outfit recommendation..."
            self.api.push_message(user_id, TextSendMessage(text=weather_msg))

            # Generate outfit image using OpenAI Images API
            image_service = get_image_service()

            # Get custom prompt from bot configuration
            custom_prompt = self.bot_instance.config.image_prompt_template

            # Use gpt-image-1 model
            image_url_or_path = image_service.generate_outfit_image(
                weather_data=weather_data,
                custom_prompt=custom_prompt,
                model="gpt-image-1",
                quality="auto"
            )

            if image_url_or_path:
                # Convert relative path to full URL if needed
                if image_url_or_path.startswith("/generated_images/"):
                    # Get server URL from environment or use default
                    server_url = os.getenv("SERVER_URL", "https://your-server-url.com")
                    full_url = f"{server_url}{image_url_or_path}"
                else:
                    # Already a full URL (dall-e-2/3)
                    full_url = image_url_or_path

                # Send the generated image
                self.api.push_message(
                    user_id,
                    ImageSendMessage(
                        original_content_url=full_url,
                        preview_image_url=full_url
                    )
                )

                # Send follow-up message
                follow_up = (
                    "✨ Here's your outfit recommendation!\n\n"
                    "👔 Style tip: Dress in layers and choose colors that match your mood!\n\n"
                    "💬 Want another recommendation? Just type 'outfit'!"
                )
                self.api.push_message(user_id, TextSendMessage(text=follow_up))
            else:
                # Image generation failed
                error_msg = (
                    "❌ Unable to generate outfit image at the moment.\n"
                    "Please try again later or contact support."
                )
                self.api.push_message(user_id, TextSendMessage(text=error_msg))

        except Exception as e:
            print(f"Error generating outfit recommendation: {e}")
            error_msg = f"❌ An error occurred: {str(e)}\nPlease try again later."
            self.api.push_message(user_id, TextSendMessage(text=error_msg))

    def register_handlers(self):
        """Register message handlers with the webhook handler"""
        @self.handler.add(MessageEvent, message=TextMessage)
        def text_message_handler(event):
            self.handle_text_message(event)

        @self.handler.add(MessageEvent, message=LocationMessage)
        def location_message_handler(event):
            self.handle_location_message(event)

        return self.handler


# Backward compatibility: Keep function-based API for existing code
def register_weather_bot_handlers(bot_instance: BotInstance):
    """
    Register message handlers for weather bot instance (backward compatibility wrapper)
    Returns the handler so it can be used in webhook processing
    """
    handler_instance = WeatherBotHandler(bot_instance)
    return handler_instance.register_handlers()
