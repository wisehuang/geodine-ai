"""
Translation module for GeoDine-AI.
Contains functions for language detection and translation.
"""

import re
import os
import time
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Language detection cache to avoid repeated API calls
language_cache = {}
MAX_CACHE_SIZE = 1000

# Translation cache to avoid repeated API calls
translation_cache = {}
MAX_TRANSLATION_CACHE_SIZE = 1000

def translate_text(text: str, target_language: str) -> str:
    """
    Translate text to the target language using ChatGPT.
    
    Args:
        text: The text to translate (in English)
        target_language: The target language code (e.g., 'zh-tw', 'ja', 'ko')
        
    Returns:
        Translated text in the target language
    """
    # If the target language is English or not specified, return the original text
    if not target_language or target_language == 'en':
        return text
    
    # Create a cache key from the text and target language
    cache_key = f"{text[:100]}|{target_language}"
    
    # Check cache first
    if cache_key in translation_cache:
        return translation_cache[cache_key]
    
    try:
        # Use ChatGPT to translate the text
        response = client.chat.completions.create(
            model="gpt-4o",  # Using 4o is sufficient for translation
            messages=[
                {"role": "system", "content": f"You are a translator. Translate the following English text to {target_language}. Only return the translated text without any explanations or notes."},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=150  # Adjust based on expected length
        )
        
        # Extract response
        translated_text = response.choices[0].message.content.strip()
        
        # Update cache (with basic size management)
        if len(translation_cache) >= MAX_TRANSLATION_CACHE_SIZE:
            # Remove a random entry if cache is full
            translation_cache.pop(next(iter(translation_cache)))
        translation_cache[cache_key] = translated_text
        
        return translated_text
            
    except Exception as e:
        print(f"Error translating text with ChatGPT: {str(e)}")
        # Return original text if translation fails
        return text

def detect_language(text: str) -> str:
    """
    Detect the language of input text using ChatGPT.
    
    Args:
        text: The input text to analyze
        
    Returns:
        Language code (e.g., 'zh-tw', 'en', 'ja', 'ko', etc.)
    """
    # If text is empty or too short, default to English
    if not text or len(text.strip()) < 2:
        return 'en'
    
    # Check cache first
    cache_key = text[:100]  # Use first 100 chars as cache key
    if cache_key in language_cache:
        return language_cache[cache_key]
    
    try:
        # Use ChatGPT to detect language
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a language detector. Identify the language of the text and respond with the appropriate language code (e.g., 'en', 'zh-tw', 'ja', 'ko', etc.). If the language is any variant of Chinese (such as zh, zh-cn, zh-hk, zh-tw), always respond with 'zh-tw'."},
                {"role": "user", "content": text[:150]}  # Only send first 150 chars
            ],
            temperature=0,
            max_tokens=10
        )
        
        # Extract response
        result = response.choices[0].message.content.strip().lower()
        
        # Update cache (with basic size management)
        if len(language_cache) >= MAX_CACHE_SIZE:
            # Remove a random entry if cache is full
            language_cache.pop(next(iter(language_cache)))
        language_cache[cache_key] = result
        
        return result
            
    except Exception as e:
        print(f"Error detecting language with ChatGPT: {str(e)}")
        # Fallback to a simple check for common languages
        chinese_pattern = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\u20000-\u2a6df\u2a700-\u2b73f\u2b740-\u2b81f\u2b820-\u2ceaf\uf900-\ufaff]')
        japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\uFF00-\uFFEF\u4E00-\u9FAF]')
        korean_pattern = re.compile(r'[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F\uA960-\uA97F\uD7B0-\uD7FF]')
        
        if chinese_pattern.search(text):
            return 'zh-tw'
        elif japanese_pattern.search(text):
            return 'ja'
        elif korean_pattern.search(text):
            return 'ko'
        return 'en' 