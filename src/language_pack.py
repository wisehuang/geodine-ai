"""
Language pack module for GeoDine-AI.
Contains all message strings and prompts used in the application.
"""

from typing import Dict, Any
from src.translation import translate_text

# Remove placeholder function
# def _placeholder_translate(text, target_language):
#     return text  # Just return the original text for now

# Default language is English
DEFAULT_LANGUAGE = "en"

# Bot responses
BOT_MESSAGES = {
    # General messages
    "not_restaurant_related": "Sorry, I can only help with food and drink related queries.",
    "greeting": "Hello! I'm a food & drink recommendation bot. What type of food or drink would you like to find today?",
    "greeting_short": "Hello! I'm a food & drink recommendation bot. How can I help you find a place to eat or drink today?",
    
    # Location related
    "location_needed": "Please share your location first so I can find food and drink places nearby.",
    "searching_generic": "Looking for food and drink places near your location...",
    "location_request": "Please share your location so I can find food and drink places nearby.",
    "location_error": "I couldn't determine your location. Please share your location and try again.",
    "searching_criteria": "Searching for food and drink places matching your criteria...",
    
    # Search results
    "no_results": "Sorry, I couldn't find any food or drink places matching your criteria.",
    "search_error": "I encountered an error while searching: ",
    
    # Location message response
    "location_saved": "I've saved your location! What type of food or drink are you looking for?",
    "location_examples": "For example, you can say:",
    "location_example_1": "- \"Japanese food\"",
    "location_example_2": "- \"Bubble tea shop\"",
    "location_example_3": "- \"Street food\"",
    "location_example_4": "- Or just say \"Any\" for general recommendations",
    
    # Generic keywords for detecting "any" food/drink requests
    "any": "any",
    "anything": "anything",
    "general": "general",
    "whatever": "whatever",
    "any_restaurant": "any restaurant",
    "any_food": "any food",
    
    # UI labels
    "view_map": "View in Google Maps",
    "rating": "Rating",
    "reviews": "reviews",
    "price": "Price",
    "address": "Address",
    
    # Error template
    "non_restaurant_query": "I'm sorry, but I can only help with finding food and drink places. I can't assist with {query_type} queries."
}

# Non-food/drink keywords for detection
NON_RESTAURANT_KEYWORDS = [
    "weather", "news", "stock", "movie", "film", "music", 
    "translate", "calculator", "alarm", "reminder", "calendar",
    "shopping", "buy", "purchase", "chat", "talk", "conversation"
]

# System prompts
SYSTEM_PROMPTS = {
    "language_detector": "You are a language detector. Identify the language of the text and respond with the appropriate language code (e.g., 'en', 'zh-tw', 'ja', 'ko', etc.).",
    "translator": "You are a translator. Translate the following English text to {target_language}. Only return the translated text without any explanations or notes.",
    "restaurant_intent": "You are a food and drink recommendation bot. Your main purpose is to help users find places to eat or drink. Determine if the user's message is related to finding food, beverages, or dining establishments, or if it's a different type of request.",
    "restaurant_analyzer": "You are a helpful assistant that analyzes food and drink establishments to find the best matches for user requests. Consider all types of places including restaurants, cafes, bubble tea shops, dessert places, street food, bars, and other food and beverage locations."
}

# Greeting patterns (regular expressions)
GREETING_PATTERNS = [
    r'^hi\b', r'^hello\b', r'^hey\b', r'^what\'?s up\b', 
    r'^good morning\b', r'^good afternoon\b', r'^good evening\b',
    r'^help\b', r'^howdy\b', r'^yo\b'
]

# OpenAI function definitions
RESTAURANT_INTENT_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "restaurant_search",
            "description": "Search for food and drink establishments based on user criteria",
            "parameters": {
                "type": "object",
                "properties": {
                    "cuisine": {
                        "type": "string",
                        "description": "Type of cuisine or establishment (e.g., Japanese, Italian, Cafe, Bubble Tea, etc.)"
                    },
                    "location": {
                        "type": "string",
                        "description": "Location for food/drink search"
                    },
                    "price_level": {
                        "type": "integer",
                        "description": "Price level (1-4)"
                    },
                    "open_now": {
                        "type": "boolean",
                        "description": "Whether the place should be currently open"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "non_restaurant_query",
            "description": "Handle a query that is not related to food or drink search",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "description": "Type of query (e.g., weather, news, general chat, etc.)"
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Why this is not a food or drink related query"
                    }
                },
                "required": ["query_type", "explanation"]
            }
        }
    }
]

def get_message(key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """
    Get a message from the language pack and translate it if needed.
    
    Args:
        key: The message key
        language: Target language code (e.g., 'en', 'zh-tw')
        **kwargs: Format parameters to apply to the message
        
    Returns:
        Translated message string
    """
    # Get the message from the language pack
    message = BOT_MESSAGES.get(key, f"[Missing message: {key}]")
    
    # Apply any format parameters
    if kwargs:
        message = message.format(**kwargs)
    
    # Translate if needed
    if language != DEFAULT_LANGUAGE:
        message = translate_text(message, language)
    
    return message

def get_system_prompt(key: str, **kwargs) -> str:
    """
    Get a system prompt from the language pack.
    System prompts are always in English and don't need translation.
    
    Args:
        key: The prompt key
        **kwargs: Format parameters to apply to the prompt
        
    Returns:
        System prompt string
    """
    prompt = SYSTEM_PROMPTS.get(key, f"[Missing prompt: {key}]")
    
    # Apply any format parameters
    if kwargs:
        prompt = prompt.format(**kwargs)
    
    return prompt

def get_restaurant_intent_functions() -> list:
    """
    Get the function definitions for food and drink intent detection.
    
    Returns:
        List of function definitions
    """
    return RESTAURANT_INTENT_FUNCTIONS

def get_greeting_patterns() -> list:
    """
    Get the greeting patterns for detecting greetings.
    
    Returns:
        List of regex patterns
    """
    return GREETING_PATTERNS

def get_non_restaurant_keywords() -> list:
    """
    Get the keywords for detecting non-food/drink queries.
    
    Returns:
        List of keywords
    """
    return NON_RESTAURANT_KEYWORDS

def get_preference_questions(language: str = DEFAULT_LANGUAGE) -> list:
    """
    Get the preference questions to ask users after they share their location.
    
    Args:
        language: Target language code
        
    Returns:
        List of questions in the target language
    """
    questions = [
        get_message("location_saved", language),
        get_message("location_examples", language),
        get_message("location_example_1", language),
        get_message("location_example_2", language),
        get_message("location_example_3", language),
        get_message("location_example_4", language)
    ]
    
    return questions

def get_generic_terms(language: str = DEFAULT_LANGUAGE) -> list:
    """
    Get the generic terms for detecting "any" food/drink requests in the specified language.
    
    Args:
        language: Target language code
        
    Returns:
        List of translated generic terms
    """
    terms = [
        get_message("any", language),
        get_message("anything", language),
        get_message("general", language),
        get_message("whatever", language),
        get_message("any_restaurant", language),
        get_message("any_food", language)
    ]
    
    return terms

def get_ui_labels(language: str = DEFAULT_LANGUAGE) -> Dict[str, str]:
    """
    Get the UI labels for the food/drink carousel in the specified language.
    
    Args:
        language: Target language code
        
    Returns:
        Dictionary of UI labels
    """
    labels = {
        "view_map": get_message("view_map", language),
        "rating": get_message("rating", language),
        "reviews": get_message("reviews", language),
        "price": get_message("price", language),
        "address": get_message("address", language)
    }
    
    return labels 