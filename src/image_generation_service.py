"""
Image generation service using OpenAI Images API
"""
import os
import base64
import requests
import uuid
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class ImageGenerationService:
    """Service for generating images using OpenAI Images API"""

    API_ENDPOINT = "https://api.openai.com/v1/images/generations"

    def __init__(self):
        """Initialize with OpenAI API key"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Create directory for storing generated images
        self.images_dir = Path("generated_images")
        self.images_dir.mkdir(exist_ok=True)

    def generate_outfit_image(
        self,
        weather_data: dict = None,
        weather_context: str = None,
        custom_prompt: str = None,
        model: str = "gpt-image-1",
        size: str = "1024x1536",
        quality: str = "auto"
    ) -> Optional[str]:
        """
        Generate an outfit recommendation image based on weather conditions

        Args:
            weather_data: Dictionary containing weather information (temp_max, temp_min, weather_code, etc.)
            weather_context: Legacy parameter - Weather condition description (e.g., "cold weather, rainy")
            custom_prompt: Optional custom prompt template with variables:
                          {weather_description}, {temperature}, {conditions}
            model: Image model to use ("gpt-image-1", "dall-e-3" or "dall-e-2")
            size: Image size ("1024x1024", "1792x1024", or "1024x1792" for dall-e-3)
            quality: Image quality ("standard" or "hd" for dall-e-3)

        Returns:
            URL of the generated image or None if generation fails
        """
        # Generate prompt based on input
        if custom_prompt and weather_data:
            prompt = self._format_custom_prompt(custom_prompt, weather_data)
        elif custom_prompt and weather_context:
            # Legacy support: use weather_context if weather_data not provided
            prompt = custom_prompt.format(
                weather_description=weather_context,
                temperature=weather_context,
                conditions=weather_context
            )
        elif weather_data:
            prompt = self._generate_prompt_from_weather_data(weather_data)
        elif weather_context:
            prompt = self._generate_default_prompt(weather_context)
        else:
            prompt = "Create a stylish outfit recommendation for moderate weather conditions."

        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size
        }

        # Add quality parameter (dall-e-3 uses "hd"/"standard", gpt-image-1 uses "high"/"medium"/"low"/"auto")
        if model == "dall-e-3":
            # Map to dall-e-3 quality values
            if quality in ["high", "hd"]:
                payload["quality"] = "hd"
            else:
                payload["quality"] = "standard"
        elif model == "gpt-image-1":
            payload["quality"] = quality

        # gpt-image-1 always returns base64, dall-e-2/3 can return URLs
        if model in ["dall-e-2", "dall-e-3"]:
            payload["response_format"] = "url"

        try:
            print(f"Generating image with prompt: {prompt}")
            print(f"Using model: {model}, size: {size}, quality: {quality}")

            response = requests.post(
                self.API_ENDPOINT,
                headers=self.headers,
                json=payload,
                timeout=300
            )

            response.raise_for_status()
            data = response.json()

            if "data" in data and len(data["data"]) > 0:
                image_data = data["data"][0]

                # gpt-image-1 returns base64, dall-e-2/3 return URL
                if "url" in image_data:
                    image_url = image_data["url"]
                    print(f"Image generated successfully (URL): {image_url}")
                    return image_url
                elif "b64_json" in image_data:
                    # For gpt-image-1, save the base64 image locally and return file path
                    b64_data = image_data["b64_json"]

                    # Generate unique filename
                    filename = f"{uuid.uuid4()}.png"
                    filepath = self.images_dir / filename

                    # Decode and save
                    image_bytes = base64.b64decode(b64_data)
                    with open(filepath, "wb") as f:
                        f.write(image_bytes)

                    print(f"Image generated successfully (base64, saved to: {filepath})")
                    # Return relative path that can be served by FastAPI
                    return f"/generated_images/{filename}"
                else:
                    print(f"Unexpected response format: {data}")
                    return None
            else:
                print(f"Unexpected response format: {data}")
                return None

        except requests.exceptions.Timeout:
            print("Error: Request timed out after 300 seconds")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error generating image: {e}")
            print(f"Response: {e.response.text if e.response else 'No response'}")
            return None
        except Exception as e:
            print(f"Error generating image: {e}")
            return None

    def _format_custom_prompt(self, template: str, weather_data: dict) -> str:
        """
        Format custom prompt template with weather data

        Args:
            template: Prompt template with placeholders
            weather_data: Weather data dictionary

        Returns:
            Formatted prompt
        """
        from src.weather_service import WeatherService

        # Extract weather information
        weather_code = weather_data.get('weather_code', 0)
        temp_max = weather_data.get('temp_max', 25)
        temp_min = weather_data.get('temp_min', 20)
        precipitation = weather_data.get('precipitation', 0)

        # Get weather description
        weather_description = WeatherService.get_weather_description(weather_code)

        # Format temperature
        temperature = f"{temp_min}°C - {temp_max}°C"

        # Build conditions string
        conditions_parts = []

        # Add precipitation info
        if precipitation > 10:
            conditions_parts.append("大雨")
        elif precipitation > 5:
            conditions_parts.append("中雨")
        elif precipitation > 0:
            conditions_parts.append("小雨")

        # Add temperature feeling
        avg_temp = (temp_max + temp_min) / 2
        if avg_temp > 30:
            conditions_parts.append("炎熱")
        elif avg_temp > 25:
            conditions_parts.append("溫暖")
        elif avg_temp > 18:
            conditions_parts.append("舒適")
        elif avg_temp > 10:
            conditions_parts.append("涼爽")
        else:
            conditions_parts.append("寒冷")

        conditions = "、".join(conditions_parts) if conditions_parts else "舒適的天氣"

        # Format the template
        try:
            prompt = template.format(
                weather_description=weather_description,
                temperature=temperature,
                conditions=conditions
            )
        except KeyError as e:
            print(f"Warning: Missing placeholder in template: {e}")
            # Fallback to simple formatting
            prompt = template

        return prompt

    def _generate_prompt_from_weather_data(self, weather_data: dict) -> str:
        """
        Generate default prompt from weather data

        Args:
            weather_data: Weather data dictionary

        Returns:
            Generated prompt
        """
        from src.weather_service import WeatherService

        weather_code = weather_data.get('weather_code', 0)
        temp_max = weather_data.get('temp_max', 25)
        temp_min = weather_data.get('temp_min', 20)

        weather_desc = WeatherService.get_weather_description(weather_code)

        prompt = (
            f"Create a stylish outfit recommendation for {weather_desc} weather, "
            f"with temperatures between {temp_min}°C and {temp_max}°C. "
            f"The image should show a complete, fashionable outfit suitable for these conditions."
        )

        return prompt

    def _generate_default_prompt(self, weather_context: str) -> str:
        """
        Generate default prompt for outfit recommendation image (legacy support)

        Args:
            weather_context: Weather condition description

        Returns:
            Complete prompt for DALL-E
        """
        prompt = (
            f"Create a stylish and fashionable outfit recommendation illustration for {weather_context}. "
            f"The image should show a complete outfit laid out on a clean, minimal background. "
            f"Include clothing items appropriate for the weather conditions, such as tops, bottoms, "
            f"outerwear, shoes, and accessories. The style should be modern, trendy, and Instagram-worthy. "
            f"Use a flat lay photography style with good lighting and color coordination. "
            f"Make it visually appealing and suitable for social media sharing."
        )

        return prompt

    def generate_outfit_image_dalle2(
        self,
        weather_context: str,
        custom_prompt: str = None
    ) -> Optional[str]:
        """
        Generate outfit image using DALL-E 2 (more cost-effective)

        Args:
            weather_context: Weather condition description
            custom_prompt: Optional custom prompt template

        Returns:
            URL of the generated image or None if generation fails
        """
        return self.generate_outfit_image(
            weather_context=weather_context,
            custom_prompt=custom_prompt,
            model="dall-e-2",
            size="1024x1024"
        )


# Singleton instance
_image_service = None


def get_image_service() -> ImageGenerationService:
    """Get or create singleton ImageGenerationService instance"""
    global _image_service
    if _image_service is None:
        _image_service = ImageGenerationService()
    return _image_service
