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
from src.database import init_db, save_user_location, get_user_locations
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize database
init_db()

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
    reply_token = event.reply_token
    text = event.message.text
    
    # Check if text is "Any" (user wants generic recommendations)
    if text.lower() in ["any", "anything", "general"]:
        # Get user's most recent location
        saved_locations = get_user_locations(user_id, limit=1)
        
        if not saved_locations:
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="Please share your location first so I can find restaurants nearby.")
            )
            return
            
        # Use the most recent location with default parameters
        recent_location = saved_locations[0]
        query_params = {
            "location": (recent_location['latitude'], recent_location['longitude']),
            "radius": 1000,
            "type": "restaurant"
        }
        
        search_and_reply(query_params, reply_token)
        return
    
    # Parse user request (with AI if enabled)
    if USE_AI_PARSING:
        query_params = parse_user_request_with_ai(text)
    else:
        query_params = parse_user_request(text)
    
    # If no location in parameters, check if user has saved locations
    if "location" not in query_params and "location_name" not in query_params:
        # Get user's saved locations
        saved_locations = get_user_locations(user_id, limit=1)
        
        if saved_locations and len(saved_locations) > 0:
            # Use the most recent saved location
            recent_location = saved_locations[0]
            location = (recent_location['latitude'], recent_location['longitude'])
            query_params['location'] = location
            
            # No need to send a separate message about using saved location
            # Just include it in the search and reply
        else:
            # If no saved locations, ask user to share location
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="Please share your location so I can find restaurants nearby")
            )
            return
    
    # Search and reply with results
    search_and_reply(query_params, reply_token)

@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    """Handle location messages, save to DB and ask for restaurant preferences"""
    user_id = event.source.user_id
    reply_token = event.reply_token
    latitude = event.message.latitude
    longitude = event.message.longitude
    address = event.message.address if hasattr(event.message, 'address') else None
    
    print(f"Received location from user {user_id}: {latitude}, {longitude}")
    
    # Log the location data for debugging
    location_data = {
        "user_id": user_id,
        "latitude": latitude,
        "longitude": longitude,
        "address": address
    }
    print(f"Location data: {location_data}")
    
    # Save user location to database
    location_id = save_user_location(
        line_user_id=user_id,
        latitude=latitude,
        longitude=longitude,
        address=address
    )
    
    # Ask user about restaurant preferences
    preference_questions = [
        "I've saved your location! What type of restaurant are you looking for?",
        "For example, you can say:",
        "- \"Japanese food\"",
        "- \"Affordable Italian restaurants\"", 
        "- \"Vegetarian restaurants open now\"",
        "- Or just say \"Any\" for general recommendations"
    ]
    
    # Use reply token to send response
    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text="\n".join(preference_questions))
    )

def search_and_reply(query_params, reply_token):
    """Search for restaurants and reply with results"""
    try:
        # Inform user that search is in progress
        search_text = "Searching for restaurants"
        if "keyword" in query_params:
            search_text += f" ({query_params['keyword']})"
        search_text += "..."
        
        # Search for restaurants
        results = search_restaurants(query_params)
        
        # If no results found
        if not results or len(results) == 0:
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="Sorry, I couldn't find any restaurants matching your criteria.")
            )
            return
        
        # Convert results to LINE Flex Message
        flex_message = create_restaurant_flex_message(results)
        
        # Use reply token to send response
        line_bot_api.reply_message(
            reply_token,
            [
                TextSendMessage(text=f"Found {len(results)} restaurants for you:"),
                FlexSendMessage(alt_text="Restaurant Recommendations", contents=flex_message)
            ]
        )
    except Exception as e:
        print(f"Error searching restaurants: {str(e)}")
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=f"I encountered an error while searching: {str(e)}")
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
