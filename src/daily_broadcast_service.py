"""
Daily Weather Broadcast Service

This service handles the daily broadcast of weather-based outfit recommendations
to all Weather OOTD bot subscribers. Designed to be called via cron job.
"""
import os
import time
from typing import List, Dict, Any, Optional
from linebot.models import TextSendMessage, ImageSendMessage
from linebot.exceptions import LineBotApiError

from src.database import get_all_bot_subscribers
from src.bot_registry import bot_registry, BotInstance
from src.weather_service import WeatherService, get_location_name
from src.image_generation_service import get_image_service


class DailyBroadcastService:
    """Service for broadcasting daily weather and outfit recommendations"""

    def __init__(self, bot_id: str = "weather-ootd"):
        """
        Initialize broadcast service for a specific bot

        Args:
            bot_id: The bot ID to broadcast from (default: "weather-ootd")
        """
        self.bot_id = bot_id
        self.bot_instance = bot_registry.get_bot(bot_id)

        if not self.bot_instance:
            raise ValueError(f"Bot '{bot_id}' not found in registry. Ensure bot is enabled in configuration.")

        if self.bot_instance.bot_type != "weather":
            raise ValueError(f"Bot '{bot_id}' is not a weather bot (type: {self.bot_instance.bot_type})")

        self.image_service = get_image_service()

    def broadcast_daily_weather(self, delay_between_users: float = 0.5) -> Dict[str, Any]:
        """
        Broadcast daily weather and outfit recommendation to all subscribers

        Args:
            delay_between_users: Delay in seconds between sending to each user (default: 0.5)
                                This prevents hitting LINE API rate limits

        Returns:
            Dict with broadcast results: {
                'total_subscribers': int,
                'successful': int,
                'failed': int,
                'errors': List[str]
            }
        """
        print(f"[Broadcast] Starting daily weather broadcast for bot: {self.bot_id}")

        # Get all subscribers
        subscribers = get_all_bot_subscribers(self.bot_id)
        total_subscribers = len(subscribers)

        print(f"[Broadcast] Found {total_subscribers} subscribers")

        if total_subscribers == 0:
            return {
                'total_subscribers': 0,
                'successful': 0,
                'failed': 0,
                'errors': []
            }

        # Track results
        successful = 0
        failed = 0
        errors = []

        # Process each subscriber
        for idx, subscriber in enumerate(subscribers, 1):
            line_user_id = subscriber['line_user_id']
            latitude = subscriber.get('latitude')
            longitude = subscriber.get('longitude')

            print(f"[Broadcast] Processing subscriber {idx}/{total_subscribers}: {line_user_id}")

            try:
                # Use subscriber's location or default to Taipei
                if latitude and longitude:
                    location_name = subscriber.get('location_name') or get_location_name(latitude, longitude)
                else:
                    latitude = WeatherService.DEFAULT_LATITUDE
                    longitude = WeatherService.DEFAULT_LONGITUDE
                    location_name = "Taipei, Taiwan (default)"

                # Fetch weather data
                weather_data = WeatherService.get_today_weather(latitude, longitude)

                if not weather_data:
                    error_msg = f"Failed to fetch weather for user {line_user_id}"
                    print(f"[Broadcast] ❌ {error_msg}")
                    errors.append(error_msg)
                    failed += 1
                    continue

                # Send weather summary first
                weather_summary = WeatherService.format_weather_summary(weather_data)
                intro_message = (
                    f"☀️ Good morning! Here's your daily weather & outfit recommendation\n\n"
                    f"📍 {location_name}\n\n"
                    f"{weather_summary}\n\n"
                    f"🎨 Generating your outfit image..."
                )

                self.bot_instance.api.push_message(
                    line_user_id,
                    TextSendMessage(text=intro_message)
                )

                # Generate outfit image (this may take time)
                print(f"[Broadcast] Generating image for user {line_user_id}...")
                image_url_or_path = self._generate_outfit_image(weather_data)

                if image_url_or_path:
                    # Convert relative path to full URL if needed
                    if image_url_or_path.startswith("/generated_images/"):
                        server_url = os.getenv("SERVER_URL", "https://your-server-url.com")
                        full_url = f"{server_url}{image_url_or_path}"
                    else:
                        full_url = image_url_or_path

                    # Send the generated image
                    self.bot_instance.api.push_message(
                        line_user_id,
                        ImageSendMessage(
                            original_content_url=full_url,
                            preview_image_url=full_url
                        )
                    )

                    # Send follow-up message
                    follow_up = (
                        "✨ Here's your daily outfit recommendation!\n\n"
                        "Have a wonderful day! 💕"
                    )
                    self.bot_instance.api.push_message(
                        line_user_id,
                        TextSendMessage(text=follow_up)
                    )

                    print(f"[Broadcast] ✅ Successfully sent to user {line_user_id}")
                    successful += 1
                else:
                    # Image generation failed, but still count as partial success
                    error_message = (
                        "⚠️ Unable to generate outfit image at the moment.\n"
                        "Please use the 'outfit' command later to try again!"
                    )
                    self.bot_instance.api.push_message(
                        line_user_id,
                        TextSendMessage(text=error_message)
                    )

                    error_msg = f"Image generation failed for user {line_user_id}"
                    print(f"[Broadcast] ⚠️ {error_msg}")
                    errors.append(error_msg)
                    successful += 1  # Still count as success since weather was sent

            except LineBotApiError as e:
                error_msg = f"LINE API error for user {line_user_id}: {str(e)}"
                print(f"[Broadcast] ❌ {error_msg}")
                errors.append(error_msg)
                failed += 1

            except Exception as e:
                error_msg = f"Unexpected error for user {line_user_id}: {str(e)}"
                print(f"[Broadcast] ❌ {error_msg}")
                errors.append(error_msg)
                failed += 1

            # Delay between users to avoid rate limiting
            if idx < total_subscribers:
                time.sleep(delay_between_users)

        # Summary
        result = {
            'total_subscribers': total_subscribers,
            'successful': successful,
            'failed': failed,
            'errors': errors
        }

        print(f"[Broadcast] Completed! Success: {successful}, Failed: {failed}")
        return result

    def _generate_outfit_image(self, weather_data: dict) -> Optional[str]:
        """
        Generate outfit image using weather data and bot's custom prompt

        Args:
            weather_data: Weather data dictionary from WeatherService

        Returns:
            Image URL or None if generation fails
        """
        try:
            # Get custom prompt from bot configuration
            custom_prompt = self.bot_instance.config.image_prompt_template

            # Generate image using gpt-image-1
            image_url = self.image_service.generate_outfit_image(
                weather_data=weather_data,
                custom_prompt=custom_prompt,
                model="gpt-image-1",
                quality="auto"
            )

            return image_url

        except Exception as e:
            print(f"[Broadcast] Error generating outfit image: {e}")
            return None

    def send_test_broadcast(self, test_user_id: str) -> bool:
        """
        Send test broadcast to a single user for testing purposes

        Args:
            test_user_id: LINE user ID to send test to

        Returns:
            True if successful, False otherwise
        """
        print(f"[Broadcast] Sending test broadcast to user: {test_user_id}")

        try:
            # Use default Taipei location for test
            latitude = WeatherService.DEFAULT_LATITUDE
            longitude = WeatherService.DEFAULT_LONGITUDE
            location_name = "Taipei, Taiwan (test)"

            # Fetch weather data
            weather_data = WeatherService.get_today_weather(latitude, longitude)

            if not weather_data:
                print("[Broadcast] ❌ Failed to fetch weather data")
                return False

            # Send weather summary
            weather_summary = WeatherService.format_weather_summary(weather_data)
            intro_message = (
                f"🧪 TEST BROADCAST\n\n"
                f"☀️ Daily Weather & Outfit Recommendation\n\n"
                f"📍 {location_name}\n\n"
                f"{weather_summary}\n\n"
                f"🎨 Generating your outfit image..."
            )

            self.bot_instance.api.push_message(
                test_user_id,
                TextSendMessage(text=intro_message)
            )

            # Generate and send image
            print("[Broadcast] Generating test image...")
            image_url = self._generate_outfit_image(weather_data)

            if image_url:
                self.bot_instance.api.push_message(
                    test_user_id,
                    ImageSendMessage(
                        original_content_url=image_url,
                        preview_image_url=image_url
                    )
                )

                self.bot_instance.api.push_message(
                    test_user_id,
                    TextSendMessage(text="✅ Test broadcast completed successfully!")
                )

                print("[Broadcast] ✅ Test broadcast successful")
                return True
            else:
                self.bot_instance.api.push_message(
                    test_user_id,
                    TextSendMessage(text="❌ Test failed: Unable to generate image")
                )
                print("[Broadcast] ❌ Test failed: Image generation failed")
                return False

        except Exception as e:
            print(f"[Broadcast] ❌ Test failed with error: {e}")
            return False


def get_broadcast_service(bot_id: str = "weather-ootd") -> DailyBroadcastService:
    """
    Get or create a DailyBroadcastService instance

    Args:
        bot_id: Bot ID to create service for

    Returns:
        DailyBroadcastService instance

    Raises:
        ValueError: If bot not found or not a weather bot
    """
    return DailyBroadcastService(bot_id)
