import re
import os
import json
import time
from typing import Dict, Any, Tuple, List
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def parse_user_request_with_ai(text: str) -> Dict[str, Any]:
    """
    Parse user text request using OpenAI API for better natural language understanding
    
    Example: "I want to find Japanese food near Banqiao Station with a budget under 500 yuan"
    Should extract:
    - Location: Banqiao Station
    - Type: Japanese food
    - Price: Medium
    """
    prompt = f"""
    Extract the following information from this user request: "{text}"
    - Restaurant type or cuisine (e.g., japanese, chinese, italian, etc.)
    - Location (e.g., a place name, landmark, etc.)
    - Price level (1=affordable, 2=medium, 3=expensive, 4=luxury)
    - Other requirements (e.g., open now)
    
    Return a JSON with the following structure:
    {{
        "keyword": "cuisine type or null",
        "location_name": "location or null",
        "price_level": number or null,
        "open_now": boolean
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from user requests."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        # Parse the response JSON
        result = json.loads(response.choices[0].message.content)
        
        # Always include the restaurant type
        result["type"] = "restaurant"
        
        # Map cuisine to appropriate format if present
        cuisine_types = {
            "japanese": "japanese restaurant",
            "chinese": "chinese restaurant",
            "italian": "italian restaurant",
            "american": "american restaurant",
            "thai": "thai restaurant",
            "korean": "korean restaurant",
            "vegetarian": "vegetarian restaurant",
            "coffee": "cafe",
            "dessert": "dessert"
        }
        
        if "keyword" in result and result["keyword"]:
            for cuisine_en, cuisine_query in cuisine_types.items():
                if cuisine_en in result["keyword"].lower():
                    result["keyword"] = cuisine_query
                    break
        
        return result
    
    except Exception as e:
        print(f"Error using OpenAI API: {str(e)}")
        # Fall back to regex-based parsing if OpenAI fails
        return parse_user_request(text)

def analyze_and_select_restaurants(restaurants: List[Dict[str, Any]], user_query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Use ChatGPT to analyze restaurants from Google Maps API and select the best matches based on user request
    
    Args:
        restaurants: List of restaurant data from Google Maps API
        user_query: The original user request text
        max_results: Maximum number of restaurants to return
        
    Returns:
        List of selected restaurants with additional explanation
    """
    # Limit number of restaurants to analyze to avoid token limits
    restaurants_to_analyze = restaurants[:10]
    
    if not restaurants_to_analyze:
        return []
    
    # Format restaurant data for ChatGPT
    restaurants_json = json.dumps(restaurants_to_analyze, ensure_ascii=False)
    
    prompt = f"""
    I need you to analyze these restaurants and select {max_results} that best match the user's request.
    
    USER REQUEST: "{user_query}"
    
    RESTAURANTS (JSON): {restaurants_json}
    
    For each selected restaurant, provide:
    1. Why it's a good match for the user's request
    2. What makes it stand out from the others
    3. Any specific recommendations based on available data
    
    Return your response as JSON with the following structure:
    {{
        "selected_restaurants": [
            {{
                "restaurant": {{original restaurant object}},
                "explanation": "Why this restaurant is a good match",
                "highlight": "Key feature to highlight"
            }}
        ]
    }}
    
    Limit your selection to {max_results} restaurants.
    """
    
    try:
        # Add retry mechanism
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo-16k",  # Use a model with larger context
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that analyzes restaurant options to find the best matches for user requests."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                    max_tokens=4000
                )
                
                # Parse the response JSON
                result = json.loads(response.choices[0].message.content)
                
                # Check if the result has the expected structure
                if "selected_restaurants" not in result:
                    raise ValueError("Invalid response format: 'selected_restaurants' not found")
                
                print(f"Successfully analyzed and selected {len(result['selected_restaurants'])} restaurants")
                return result["selected_restaurants"]
                
            except Exception as e:
                print(f"Error on attempt {attempt+1}/{max_retries}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise
        
    except Exception as e:
        print(f"Error analyzing restaurants with ChatGPT: {str(e)}")
        # Fallback: Just return the top restaurants without analysis
        return [{"restaurant": r, "explanation": "", "highlight": ""} for r in restaurants_to_analyze[:max_results]]

def parse_user_request(text: str) -> Dict[str, Any]:
    """
    Parse user text request to extract key parameters
    
    Example: "I want to find Japanese food near Banqiao Station with a budget under 500 yuan"
    Should extract:
    - Location: Banqiao Station
    - Type: Japanese food
    - Price: Medium
    """
    params = {
        "type": "restaurant"
    }
    
    # Parse location (using simple rules, actual application might need more complex NLP)
    location_match = re.search(r'(at|near|find)(\w+?)(nearby|around|beside)', text)
    if location_match:
        location_name = location_match.group(2)
        params["location_name"] = location_name
        # Note: Location name needs to be converted to geographic coordinates
        # In a real application, we could use Google Geocoding API
    
    # Parse restaurant type
    cuisine_types = {
        "japanese": "japanese restaurant",
        "chinese": "chinese restaurant",
        "italian": "italian restaurant",
        "american": "american restaurant",
        "thai": "thai restaurant",
        "korean": "korean restaurant",
        "vegetarian": "vegetarian restaurant",
        "coffee": "cafe",
        "dessert": "dessert"
    }
    
    for cuisine_en, cuisine_query in cuisine_types.items():
        if cuisine_en in text.lower():
            params["keyword"] = cuisine_query
            break
    
    # Parse price level
    if "cheap" in text or "affordable" in text:
        params["price_level"] = 1
    elif "luxury" in text or "high-end" in text:
        params["price_level"] = 4
    elif "medium" in text:
        params["price_level"] = 2
    
    # Parse operating status
    if "open now" in text or "currently open" in text:
        params["open_now"] = True
    
    return params

def calculate_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Calculate distance between two geographic coordinates (using Haversine formula)
    """
    import math
    
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    # Convert coordinates to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Earth radius (kilometers)
    
    # Return distance (kilometers)
    return c * r
