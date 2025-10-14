"""
Weather service for fetching weather data from Open-Meteo API
"""
import requests
from typing import Dict, Any, Optional, Tuple
from datetime import datetime


class WeatherService:
    """Service for fetching weather data from Open-Meteo API"""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    # Default location: Taipei, Taiwan
    DEFAULT_LATITUDE = 25.01
    DEFAULT_LONGITUDE = 121.46
    DEFAULT_TIMEZONE = "Asia/Taipei"

    @staticmethod
    def get_weather_forecast(
        latitude: float = None,
        longitude: float = None,
        timezone: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch weather forecast from Open-Meteo API

        Args:
            latitude: Latitude coordinate (defaults to Taipei)
            longitude: Longitude coordinate (defaults to Taipei)
            timezone: Timezone for the forecast (defaults to Asia/Taipei)

        Returns:
            Weather forecast data or None if request fails
        """
        # Use defaults if not provided
        lat = latitude if latitude is not None else WeatherService.DEFAULT_LATITUDE
        lon = longitude if longitude is not None else WeatherService.DEFAULT_LONGITUDE
        tz = timezone if timezone else WeatherService.DEFAULT_TIMEZONE

        params = {
            'latitude': lat,
            'longitude': lon,
            'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,sunrise,sunset',
            'timezone': tz,
            'forecast_days': 7
        }

        try:
            response = requests.get(WeatherService.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching weather data: {e}")
            return None

    @staticmethod
    def get_today_weather(
        latitude: float = None,
        longitude: float = None,
        timezone: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get today's weather forecast

        Returns:
            Dictionary with today's weather data including:
            - date: Date string
            - temp_max: Maximum temperature (°C)
            - temp_min: Minimum temperature (°C)
            - precipitation: Precipitation sum (mm)
            - weather_code: WMO weather code
            - sunrise: Sunrise time
            - sunset: Sunset time
        """
        forecast = WeatherService.get_weather_forecast(latitude, longitude, timezone)

        if not forecast or 'daily' not in forecast:
            return None

        daily = forecast['daily']

        # Get today's data (first day in the forecast)
        today_data = {
            'date': daily['time'][0],
            'temp_max': daily['temperature_2m_max'][0],
            'temp_min': daily['temperature_2m_min'][0],
            'precipitation': daily['precipitation_sum'][0],
            'weather_code': daily.get('weathercode', [0])[0],
            'sunrise': daily.get('sunrise', [''])[0],
            'sunset': daily.get('sunset', [''])[0],
            'latitude': forecast['latitude'],
            'longitude': forecast['longitude'],
            'timezone': forecast['timezone']
        }

        return today_data

    @staticmethod
    def get_weather_description(weather_code: int) -> str:
        """
        Convert WMO weather code to human-readable description

        WMO Weather interpretation codes (WW):
        0: Clear sky
        1, 2, 3: Mainly clear, partly cloudy, and overcast
        45, 48: Fog and depositing rime fog
        51, 53, 55: Drizzle: Light, moderate, and dense intensity
        61, 63, 65: Rain: Slight, moderate and heavy intensity
        71, 73, 75: Snow fall: Slight, moderate, and heavy intensity
        77: Snow grains
        80, 81, 82: Rain showers: Slight, moderate, and violent
        85, 86: Snow showers slight and heavy
        95: Thunderstorm: Slight or moderate
        96, 99: Thunderstorm with slight and heavy hail
        """
        weather_descriptions = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }

        return weather_descriptions.get(weather_code, "Unknown weather condition")

    @staticmethod
    def get_weather_emoji(weather_code: int) -> str:
        """
        Get emoji representation of weather condition
        """
        weather_emojis = {
            0: "☀️",      # Clear sky
            1: "🌤️",     # Mainly clear
            2: "⛅",      # Partly cloudy
            3: "☁️",      # Overcast
            45: "🌫️",    # Fog
            48: "🌫️",    # Rime fog
            51: "🌦️",    # Light drizzle
            53: "🌧️",    # Moderate drizzle
            55: "🌧️",    # Dense drizzle
            61: "🌧️",    # Slight rain
            63: "🌧️",    # Moderate rain
            65: "🌧️",    # Heavy rain
            71: "🌨️",    # Slight snow
            73: "❄️",     # Moderate snow
            75: "❄️",     # Heavy snow
            77: "❄️",     # Snow grains
            80: "🌦️",    # Slight rain showers
            81: "🌧️",    # Moderate rain showers
            82: "⛈️",     # Violent rain showers
            85: "🌨️",    # Slight snow showers
            86: "❄️",     # Heavy snow showers
            95: "⛈️",     # Thunderstorm
            96: "⛈️",     # Thunderstorm with hail
            99: "⛈️"      # Thunderstorm with heavy hail
        }

        return weather_emojis.get(weather_code, "🌡️")

    @staticmethod
    def format_weather_summary(weather_data: Dict[str, Any]) -> str:
        """
        Format weather data into a readable summary

        Args:
            weather_data: Weather data from get_today_weather()

        Returns:
            Formatted weather summary string
        """
        if not weather_data:
            return "Unable to fetch weather data"

        weather_code = weather_data.get('weather_code', 0)
        emoji = WeatherService.get_weather_emoji(weather_code)
        description = WeatherService.get_weather_description(weather_code)

        temp_max = weather_data.get('temp_max')
        temp_min = weather_data.get('temp_min')
        precipitation = weather_data.get('precipitation', 0)
        date = weather_data.get('date', 'Today')

        summary = f"{emoji} {description}\n\n"
        summary += f"📅 Date: {date}\n"
        summary += f"🌡️ Temperature: {temp_min}°C - {temp_max}°C\n"

        if precipitation > 0:
            summary += f"💧 Precipitation: {precipitation} mm\n"

        return summary

    @staticmethod
    def get_outfit_recommendation_context(weather_data: Dict[str, Any]) -> str:
        """
        Generate context for outfit recommendation based on weather

        Args:
            weather_data: Weather data from get_today_weather()

        Returns:
            Context string describing weather conditions for outfit generation
        """
        if not weather_data:
            return "moderate weather conditions"

        temp_max = weather_data.get('temp_max', 20)
        temp_min = weather_data.get('temp_min', 15)
        precipitation = weather_data.get('precipitation', 0)
        weather_code = weather_data.get('weather_code', 0)

        description = WeatherService.get_weather_description(weather_code)
        avg_temp = (temp_max + temp_min) / 2

        # Temperature-based context
        if avg_temp < 10:
            temp_context = "cold weather (below 10°C)"
        elif avg_temp < 18:
            temp_context = "cool weather (10-18°C)"
        elif avg_temp < 25:
            temp_context = "mild weather (18-25°C)"
        elif avg_temp < 30:
            temp_context = "warm weather (25-30°C)"
        else:
            temp_context = "hot weather (above 30°C)"

        # Precipitation context
        if precipitation > 10:
            precip_context = ", heavy rain expected"
        elif precipitation > 5:
            precip_context = ", moderate rain expected"
        elif precipitation > 0:
            precip_context = ", light rain possible"
        else:
            precip_context = ""

        context = f"{temp_context}, {description.lower()}{precip_context}"

        return context


def get_location_name(latitude: float, longitude: float) -> str:
    """
    Get location name from coordinates using reverse geocoding
    This is a simplified version - you might want to use a proper geocoding service
    """
    # Check if it's Taipei (default location)
    if abs(latitude - WeatherService.DEFAULT_LATITUDE) < 0.1 and \
       abs(longitude - WeatherService.DEFAULT_LONGITUDE) < 0.1:
        return "Taipei, Taiwan"

    # For other locations, you could integrate with a geocoding service
    # For now, return coordinates
    return f"Location ({latitude:.2f}, {longitude:.2f})"
