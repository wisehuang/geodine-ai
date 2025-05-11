import re
import os
import json
import time
from typing import Dict, Any, Tuple, List
from openai import OpenAI
from src.translation import translate_text, detect_language
from src.language_pack import (
    get_system_prompt, get_greeting_patterns, 
    get_non_restaurant_keywords, get_message, 
    get_restaurant_intent_functions
)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Language detection cache to avoid repeated API calls
language_cache = {}
MAX_CACHE_SIZE = 1000

# Translation cache to avoid repeated API calls
translation_cache = {}
MAX_TRANSLATION_CACHE_SIZE = 1000

def is_restaurant_related(text: str) -> Tuple[bool, str]:
    """
    Check if the user's input is related to finding food, drinks, or dining establishments using OpenAI function calling.
    
    Args:
        text: The user's input text
        
    Returns:
        A tuple of (is_related, message)
        - is_related: Boolean indicating if the input is related to food/drink finding
        - message: A message to send if not related
    """
    # Detect language for potential reply message only
    language = detect_language(text)
    text_lower = text.lower()
    
    # Get greeting patterns from language pack
    greeting_patterns = get_greeting_patterns()
    
    # Check for greeting patterns
    # For English input
    if language == 'en':
        for pattern in greeting_patterns:
            if re.search(pattern, text_lower):
                return True, get_message("greeting_short")
    # For non-English input, translate each greeting pattern and check
    else:
        # Option 1: Check if the input starts with common greetings in their language
        # (This avoids doing many translations for pattern matching)
        # Translate a few key greetings to check against
        hello_translated = translate_text("hello", language).lower()
        hi_translated = translate_text("hi", language).lower()
        hey_translated = translate_text("hey", language).lower()
        help_translated = translate_text("help", language).lower()
        
        if (text_lower.startswith(hello_translated) or 
            text_lower.startswith(hi_translated) or
            text_lower.startswith(hey_translated) or
            text_lower.startswith(help_translated)):
            # Translate the greeting response
            return True, get_message("greeting_short", language)
    
    # Simple keyword matching to detect food-related queries
    food_drink_keywords = {
        # English food keywords
        "food", "eat", "restaurant", "dining", "meal", "lunch", "dinner", "breakfast", "brunch",
        "cuisine", "menu", "dishes", "snack", "street food", "take out", "takeaway", "delivery",
        # English drink keywords
        "drink", "coffee", "cafe", "tea", "bubble tea", "boba", "milk tea", "juice", "bar", 
        "alcohol", "beer", "wine", "cocktail", "beverage",
        # English dessert/bakery keywords
        "dessert", "cake", "ice cream", "sweet", "bakery", "pastry", "bread",
        # Chinese food keywords
        "食物", "吃", "餐廳", "用餐", "餐點", "午餐", "晚餐", "早餐", "早午餐", 
        "菜系", "菜單", "菜色", "小吃", "路邊攤", "外帶", "外送",
        # Chinese drink keywords
        "飲料", "咖啡", "茶", "珍珠奶茶", "手搖杯", "果汁", "酒吧", 
        "酒", "啤酒", "葡萄酒", "調酒", "飲品",
        # Chinese dessert/bakery keywords
        "甜點", "蛋糕", "冰淇淋", "甜食", "麵包店", "糕點", "麵包"
    }
    
    # Check if any food/drink keyword is in the text
    for keyword in food_drink_keywords:
        if keyword in text_lower:
            return True, ""
    
    # Use ChatGPT with function calling for more accurate intent classification
    if os.getenv("USE_AI_PARSING", "False").lower() == "true":
        try:
            # Get system prompt and functions from language pack
            system_prompt = get_system_prompt("restaurant_intent")
            functions = get_restaurant_intent_functions()
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                tools=functions,
                tool_choice="auto",
                temperature=0.1
            )
            
            # Get the AI's response
            response_message = response.choices[0].message
            
            # Check if the AI chose to call a function
            if response_message.tool_calls:
                tool_call = response_message.tool_calls[0]
                function_name = tool_call.function.name
                
                if function_name == "restaurant_search":
                    # The AI determined this is a food/drink-related query
                    return True, ""
                elif function_name == "non_restaurant_query":
                    # The AI determined this is not food/drink-related
                    function_args = json.loads(tool_call.function.arguments)
                    query_type = function_args.get("query_type", "")
                    
                    # Get non-restaurant query message from language pack
                    return False, get_message("non_restaurant_query", language, query_type=query_type)
            
            # If no function call, default to treating as food/drink-related
            return True, ""
            
        except Exception as e:
            print(f"Error using OpenAI API for intent detection: {str(e)}")
            # Fall back to simpler checks if AI check fails
    
    # Simple keyword matching for non-food/drink queries as fallback
    # Define English non-food/drink keywords only
    non_restaurant_keywords = get_non_restaurant_keywords()
    
    # For English input, check against English keywords
    if language == 'en':
        for keyword in non_restaurant_keywords:
            if keyword in text_lower:
                return False, get_message("non_restaurant_query", language, query_type=keyword)
    # For non-English input, translate the input text to English and check against English keywords
    else:
        # This approach might be less accurate but avoids translating many keywords
        # Alternatively, you could translate each keyword to the target language
        translated_text_to_en = ""
        try:
            # Try to translate the input to English for keyword matching
            translated_text_to_en = translate_text(text, "en").lower()
        except Exception as e:
            print(f"Error translating input to English: {str(e)}")
            # If translation fails, skip this check
            pass
        
        if translated_text_to_en:
            for keyword in non_restaurant_keywords:
                if keyword in translated_text_to_en:
                    return False, get_message("non_restaurant_query", language, query_type=keyword)
    
    # Default to assuming it's food/drink-related if no other conditions matched
    return True, ""

def parse_user_request_with_ai(text: str) -> Dict[str, Any]:
    """
    Parse user text request using OpenAI API for better natural language understanding
    
    Example: "I want to find Japanese food near Banqiao Station with a budget under 500 yuan"
    Should extract:
    - Location: Banqiao Station
    - Type: Japanese food
    - Price: Medium
    """
    # Use English prompts regardless of input language
    system_prompt = "You are a helpful assistant that extracts structured data from user requests."
    user_prompt = f"""
    Extract the following information from this user request: "{text}"
    - Food/drink type or cuisine (e.g., japanese, chinese, italian, cafe, bubble tea, dessert, etc.)
    - Location (e.g., a place name, landmark, etc.)
    - Price level (1=affordable, 2=medium, 3=expensive, 4=luxury)
    - Other requirements (e.g., open now)
    
    Return a JSON with the following structure:
    {{
        "keyword": "cuisine or establishment type or null",
        "location_name": "location or null",
        "price_level": number or null,
        "open_now": boolean
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        # Parse the response JSON
        result = json.loads(response.choices[0].message.content)
        
        # Map food/drink type to appropriate format if present
        establishment_types = {
            # Food establishments - English
            "japanese": "japanese restaurant",
            "chinese": "chinese restaurant",
            "italian": "italian restaurant",
            "american": "american restaurant",
            "thai": "thai restaurant",
            "korean": "korean restaurant",
            "vegetarian": "vegetarian restaurant",
            "burger": "burger",
            "pizza": "pizza",
            "steak": "steak",
            "seafood": "seafood",
            "hot pot": "hot pot",
            "bbq": "bbq",
            # Drink establishments - English
            "coffee": "cafe",
            "cafe": "cafe", 
            "bubble tea": "bubble tea",
            "boba": "bubble tea",
            "milk tea": "bubble tea",
            "tea": "tea house",
            "bar": "bar",
            "juice": "juice bar",
            # Dessert/Snacks - English
            "dessert": "dessert",
            "cake": "bakery",
            "bakery": "bakery",
            "ice cream": "ice cream",
            "snack": "snack",
            "street food": "street food",
            # Food establishments - Chinese
            "日本": "japanese restaurant",
            "日式": "japanese restaurant",
            "中餐": "chinese restaurant",
            "中式": "chinese restaurant",
            "義大利": "italian restaurant",
            "義式": "italian restaurant",
            "美式": "american restaurant",
            "泰式": "thai restaurant",
            "泰國": "thai restaurant",
            "韓式": "korean restaurant",
            "韓國": "korean restaurant",
            "素食": "vegetarian restaurant",
            "漢堡": "burger",
            "披薩": "pizza",
            "牛排": "steak",
            "海鮮": "seafood",
            "火鍋": "hot pot",
            "燒烤": "bbq",
            # Drink establishments - Chinese
            "咖啡": "cafe",
            "珍珠奶茶": "bubble tea",
            "珍奶": "bubble tea",
            "手搖杯": "bubble tea",
            "奶茶": "bubble tea",
            "茶": "tea house",
            "酒吧": "bar",
            "果汁": "juice bar",
            # Dessert/Snacks - Chinese
            "甜點": "dessert",
            "甜食": "dessert",
            "蛋糕": "bakery",
            "麵包": "bakery",
            "烘焙": "bakery",
            "冰淇淋": "ice cream",
            "小吃": "snack",
            "路邊攤": "street food"
        }
        
        if "keyword" in result and result["keyword"]:
            keyword_lower = result["keyword"].lower()
            for type_key, type_query in establishment_types.items():
                if type_key in keyword_lower:
                    result["keyword"] = type_query
                    break
                    
            # Set the appropriate type based on the keyword
            if any(drink_term in keyword_lower for drink_term in ["cafe", "coffee", "bubble tea", "boba", "milk tea", "bar", "juice", "咖啡", "奶茶", "珍珠", "酒吧", "果汁"]):
                result["type"] = "cafe"
            elif any(dessert_term in keyword_lower for dessert_term in ["dessert", "bakery", "cake", "ice cream", "甜點", "甜食", "蛋糕", "麵包", "烘焙", "冰淇淋"]):
                result["type"] = "bakery"
            elif any(snack_term in keyword_lower for snack_term in ["snack", "street food", "小吃", "路邊攤"]):
                result["type"] = "food"  # General food type for snacks and street food
            else:
                result["type"] = "restaurant"  # Default to restaurant
        
        return result
    
    except Exception as e:
        print(f"Error using OpenAI API: {str(e)}")
        # Fall back to regex-based parsing if OpenAI fails
        return parse_user_request(text)

def analyze_and_select_restaurants(restaurants: List[Dict[str, Any]], user_query: str, max_results: int = 3, language: str = "en") -> List[Dict[str, Any]]:
    """
    Use ChatGPT to analyze food & drink places from Google Maps API and select the best matches based on user request
    
    Args:
        restaurants: List of food & drink places from Google Maps API
        user_query: The original user request text
        max_results: Maximum number of places to return
        language: The language to use for responses ('en', 'zh-tw', 'ja', 'ko', etc.)
        
    Returns:
        List of selected places with additional explanation
    """
    # Limit number of places to analyze to avoid token limits
    restaurants_to_analyze = restaurants[:10]
    
    if not restaurants_to_analyze:
        return []
    
    # Format place data for ChatGPT
    restaurants_json = json.dumps(restaurants_to_analyze, ensure_ascii=False)
    
    # Get system prompt from language pack
    system_prompt = get_system_prompt("restaurant_analyzer")
    
    # Use English as the prompt language
    prompt = f"""
    I need you to analyze these food & drink places and select {max_results} that best match the user's request.
    
    USER REQUEST: "{user_query}"
    
    PLACES (JSON): {restaurants_json}
    
    For each selected place, provide:
    1. Why it's a good match for the user's request
    2. What makes it stand out from the others
    3. Any specific recommendations based on available data
    
    The user's language is: {language}
    Please provide your explanations in this language.
    
    Return your response as JSON with the following structure:
    {{
        "selected_restaurants": [
            {{
                "restaurant": {{original place object}},
                "explanation": "Why this place is a good match (in the user's language)",
                "highlight": "Key feature to highlight (in the user's language)"
            }}
        ]
    }}
    
    Limit your selection to {max_results} places.
    """
    
    try:
        # Add retry mechanism
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",  # Use a model with larger context
                    messages=[
                        {"role": "system", "content": system_prompt},
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
                
                print(f"Successfully analyzed and selected {len(result['selected_restaurants'])} places")
                return result["selected_restaurants"]
                
            except Exception as e:
                print(f"Error on attempt {attempt+1}/{max_retries}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise
        
    except Exception as e:
        print(f"Error analyzing places with ChatGPT: {str(e)}")
        # Fallback: Just return the top places without analysis
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
    params = {}
    
    # Detect language
    language = detect_language(text)
    text_lower = text.lower()
    
    # Parse location (using simple rules, actual application might need more complex NLP)
    if language == "en":
        location_match = re.search(r'(at|near|find)(\w+?)(nearby|around|beside)', text_lower)
        if location_match:
            location_name = location_match.group(2)
            params["location_name"] = location_name
    else:
        # Chinese location matching pattern (near/at... station/place)
        location_match = re.search(r'(在|附近|靠近|找)([^的]+?)(站|處|地方|餐廳)', text_lower)
        if location_match:
            location_name = location_match.group(2)
            params["location_name"] = location_name
    
    # Parse food and drink type with bilingual support
    establishment_types = {
        # Food establishments - English
        "japanese": "japanese restaurant",
        "chinese": "chinese restaurant",
        "italian": "italian restaurant",
        "american": "american restaurant",
        "thai": "thai restaurant",
        "korean": "korean restaurant",
        "vegetarian": "vegetarian restaurant",
        "burger": "burger",
        "pizza": "pizza",
        "steak": "steak",
        "seafood": "seafood",
        "hot pot": "hot pot",
        "bbq": "bbq",
        # Drink establishments - English
        "coffee": "cafe",
        "cafe": "cafe", 
        "bubble tea": "bubble tea",
        "boba": "bubble tea",
        "milk tea": "bubble tea",
        "tea": "tea house",
        "bar": "bar",
        "juice": "juice bar",
        # Dessert/Snacks - English
        "dessert": "dessert",
        "cake": "bakery",
        "bakery": "bakery",
        "ice cream": "ice cream",
        "snack": "snack",
        "street food": "street food",
        # Food establishments - Chinese
        "日本": "japanese restaurant",
        "日式": "japanese restaurant",
        "中餐": "chinese restaurant",
        "中式": "chinese restaurant",
        "義大利": "italian restaurant",
        "義式": "italian restaurant",
        "美式": "american restaurant",
        "泰式": "thai restaurant",
        "泰國": "thai restaurant",
        "韓式": "korean restaurant",
        "韓國": "korean restaurant",
        "素食": "vegetarian restaurant",
        "漢堡": "burger",
        "披薩": "pizza",
        "牛排": "steak",
        "海鮮": "seafood",
        "火鍋": "hot pot",
        "燒烤": "bbq",
        # Drink establishments - Chinese
        "咖啡": "cafe",
        "珍珠奶茶": "bubble tea",
        "珍奶": "bubble tea",
        "手搖杯": "bubble tea",
        "奶茶": "bubble tea",
        "茶": "tea house",
        "酒吧": "bar",
        "果汁": "juice bar",
        # Dessert/Snacks - Chinese
        "甜點": "dessert",
        "甜食": "dessert",
        "蛋糕": "bakery",
        "麵包": "bakery",
        "烘焙": "bakery",
        "冰淇淋": "ice cream",
        "小吃": "snack",
        "路邊攤": "street food"
    }
    
    for type_keyword, type_query in establishment_types.items():
        if type_keyword in text_lower:
            params["keyword"] = type_query
            
            # Set the appropriate type based on the keyword
            if any(drink_term in type_keyword for drink_term in ["cafe", "coffee", "bubble tea", "boba", "milk tea", "bar", "juice", "咖啡", "奶茶", "珍珠", "酒吧", "果汁"]):
                params["type"] = "cafe"
            elif any(dessert_term in type_keyword for dessert_term in ["dessert", "bakery", "cake", "ice cream", "甜點", "甜食", "蛋糕", "麵包", "烘焙", "冰淇淋"]):
                params["type"] = "bakery"
            elif any(snack_term in type_keyword for snack_term in ["snack", "street food", "小吃", "路邊攤"]):
                params["type"] = "food"  # General food type for snacks and street food
            else:
                params["type"] = "restaurant"  # Default to restaurant
                
            break
    
    # If no specific establishment type found, default to food search
    if "keyword" not in params:
        if "food" in text_lower or "餐" in text_lower or "吃" in text_lower:
            params["keyword"] = "food"
    
    # Parse price level with bilingual support
    if language == "en":
        if "cheap" in text_lower or "affordable" in text_lower or "inexpensive" in text_lower:
            params["price_level"] = 1
        elif "luxury" in text_lower or "high-end" in text_lower or "expensive" in text_lower:
            params["price_level"] = 4
        elif "medium" in text_lower or "moderate" in text_lower:
            params["price_level"] = 2
    else:
        # Chinese price keywords
        if "便宜" in text_lower or "平價" in text_lower or "經濟" in text_lower:
            params["price_level"] = 1
        elif "豪華" in text_lower or "高級" in text_lower or "貴" in text_lower:
            params["price_level"] = 4
        elif "中價" in text_lower or "適中" in text_lower:
            params["price_level"] = 2
    
    # Parse operating status with bilingual support
    if language == "en":
        if "open now" in text_lower or "currently open" in text_lower:
            params["open_now"] = True
    else:
        if "現在營業" in text_lower or "現在開" in text_lower or "營業中" in text_lower:
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
