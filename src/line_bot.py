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
from src.database import init_db, save_user_location, get_user_location, get_user_location_for_search
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
        # Get user's location directly in the correct format for Google Maps API
        location = get_user_location_for_search(user_id)
        
        if not location:
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="Please share your location first so I can find restaurants nearby.")
            )
            return
            
        # Use the user's location with default parameters
        query_params = {
            "location": location,
            "radius": 1000,
            "type": "restaurant"
        }
        
        # First acknowledge the request with a reply
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text="Looking for restaurants near your location...")
        )
        
        # Then search and push results
        search_and_push(query_params, user_id)
        return
    
    # Parse user request (with AI if enabled)
    if USE_AI_PARSING:
        query_params = parse_user_request_with_ai(text)
    else:
        query_params = parse_user_request(text)
    
    # Debug log to help diagnose issues
    print(f"Query params after parsing: {query_params}")
    
    # If no location in parameters, check if user has saved location
    if "location" not in query_params or not query_params["location"]:
        # Get user's location directly in the correct format
        location = get_user_location_for_search(user_id)
        print(f"Retrieved location from database: {location}")
        
        if location:
            # Use the stored location
            query_params['location'] = location
            print(f"Using saved location: {location}")
        else:
            # If no location, ask user to share location
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="Please share your location so I can find restaurants nearby")
            )
            return
    
    # Ensure location is not None
    if "location" not in query_params or not query_params["location"]:
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text="I couldn't determine your location. Please share your location and try again.")
        )
        return
    
    # First acknowledge the request with a reply
    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text="Searching for restaurants matching your criteria...")
    )
    
    # Final debug log before search
    print(f"Final query params before search: {query_params}")
    
    # Then search and push results
    search_and_push(query_params, user_id)

@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    """Handle location messages, save to DB and ask for restaurant preferences"""
    user_id = event.source.user_id
    reply_token = event.reply_token
    latitude = event.message.latitude
    longitude = event.message.longitude
    address = event.message.address if hasattr(event.message, 'address') else None
    
    print(f"Received location from user {user_id}: {latitude}, {longitude}")
    
    # Save user location to database (will update if exists)
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

def search_and_push(query_params, user_id):
    """Search for restaurants and push only the first result to user"""
    try:
        # Search for restaurants without sending progress message
        results = search_restaurants(query_params)
        
        # If no results found
        if not results or len(results) == 0:
            line_bot_api.push_message(
                user_id,
                TextSendMessage(text="Sorry, I couldn't find any restaurants matching your criteria.")
            )
            return
        
        # Only take the first result
        first_restaurant = results[0]
        print(f"Sending first restaurant result: {first_restaurant['name']}")
        
        # Create a single restaurant message instead of a carousel
        restaurant_message = create_single_restaurant_message(first_restaurant)
        
        # Use push message to send response with just the first restaurant
        line_bot_api.push_message(
            user_id,
            FlexSendMessage(alt_text=f"Found restaurant: {first_restaurant['name']}", contents=restaurant_message)
        )
    except Exception as e:
        print(f"Error searching restaurants: {str(e)}")
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=f"I encountered an error while searching: {str(e)}")
        )

def create_single_restaurant_message(restaurant):
    """Create a Flex Message for a single restaurant result"""
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
                                    "text": f"Address: {restaurant.get('address', 'N/A')}"
                                }
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "baseline",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": f"Price level: {restaurant.get('price_level', 'N/A')}"
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
    
    return bubble
