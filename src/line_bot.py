import os
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, LocationMessage, 
    TextSendMessage, FlexSendMessage
)
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from src.restaurant_finder import search_restaurants
from src.utils import parse_user_request, parse_user_request_with_ai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up LINE Bot API
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# Flag to control whether to use AI for parsing
USE_AI_PARSING = os.getenv("USE_AI_PARSING", "False").lower() == "true"

router = APIRouter(prefix="/line", tags=["LINE Bot"])

class LineWebhookRequest(BaseModel):
    destination: str
    events: List[Dict[str, Any]]

@router.post("/webhook", operation_id="line_webhook")
async def line_webhook(
    request: Request,
    x_line_signature: Optional[str] = Header(None)
):
    """
    Handle webhook events from the LINE platform
    """
    body = await request.body()
    
    try:
        handler.handle(body.decode("utf-8"), x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid LINE signature")
    
    return {"status": "OK"}

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """Handle text messages, parse user requests"""
    user_id = event.source.user_id
    text = event.message.text
    
    # Parse user request (with AI if enabled)
    if USE_AI_PARSING:
        query_params = parse_user_request_with_ai(text)
    else:
        query_params = parse_user_request(text)
    
    if "location" not in query_params and "location_name" not in query_params:
        # If location information is missing, ask the user to provide location
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="Please share your location so I can find restaurants nearby")
        )
        return
    
    # If location information is available, search for restaurants
    results = search_restaurants(query_params)
    
    # Convert results to LINE Flex Message
    flex_message = create_restaurant_flex_message(results)
    
    line_bot_api.reply_message(
        event.reply_token,
        FlexSendMessage(alt_text="Restaurant Recommendations", contents=flex_message)
    )

@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    """Handle location messages, search for nearby restaurants"""
    user_id = event.source.user_id
    latitude = event.message.latitude
    longitude = event.message.longitude
    
    # Search for nearby restaurants with default parameters
    query_params = {
        "location": (latitude, longitude),
        "radius": 1000,  # Default search radius: 1 kilometer
        "type": "restaurant"
    }
    
    results = search_restaurants(query_params)
    
    # Convert results to LINE Flex Message
    flex_message = create_restaurant_flex_message(results)
    
    line_bot_api.reply_message(
        event.reply_token,
        FlexSendMessage(alt_text="Nearby Restaurants", contents=flex_message)
    )

def create_restaurant_flex_message(restaurants):
    """Convert restaurant information to LINE Flex Message format"""
    # Implementation of Flex Message generation logic
    # See LINE official documentation for reference
    
    # Simplified version of Flex Message
    contents = {
        "type": "carousel",
        "contents": []
    }
    
    for restaurant in restaurants:
        bubble = {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": restaurant.get("photo_url", "https://via.placeholder.com/300x200"),
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": restaurant["name"],
                        "weight": "bold",
                        "size": "xl"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": f"Rating: {restaurant.get('rating', 'N/A')}"
                                    }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": f"Distance: {restaurant.get('distance', 'N/A')} meters"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "Open in Google Maps",
                            "uri": f"https://www.google.com/maps/place/?q=place_id:{restaurant['place_id']}"
                        }
                    }
                ]
            }
        }
        contents["contents"].append(bubble)
    
    return contents
