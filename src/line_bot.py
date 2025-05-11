import os
import time
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, LocationMessage, 
    TextSendMessage, FlexSendMessage, CarouselContainer, BubbleContainer,
    BoxComponent, ButtonComponent, TextComponent, ImageComponent,
    URIAction
)
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from src.restaurant_finder import search_restaurants
from src.utils import parse_user_request, parse_user_request_with_ai, analyze_and_select_restaurants, is_restaurant_related
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

# Store event timestamps to avoid processing duplicates
processed_events = {}

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
    body_str = body.decode("utf-8")
    
    try:
        # Print webhook event for debugging
        print(f"Received LINE webhook: {body_str}")
        handler.handle(body_str, x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid LINE signature")
    except Exception as e:
        print(f"Error handling webhook: {str(e)}")
        # Don't raise exception here to always return 200 OK to LINE
    
    return {"status": "OK"}

def safe_reply_or_push(event, messages):
    """
    Attempt to reply to user, and if that fails, send a push message instead
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    
    # Check if we've already processed this event recently
    event_id = getattr(event, 'id', None) or getattr(event.message, 'id', None)
    current_time = time.time()
    
    if event_id and event_id in processed_events:
        # If we've seen this event in the last 5 minutes, skip it
        if current_time - processed_events[event_id] < 300:  # 5 minutes
            print(f"Skipping duplicate event: {event_id}")
        return
    
    if event_id:
        processed_events[event_id] = current_time
    
    # Clean up old events (older than 5 minutes)
    for eid in list(processed_events.keys()):
        if current_time - processed_events[eid] > 300:
            del processed_events[eid]
    
    try:
        # Try to use reply token first
        line_bot_api.reply_message(reply_token, messages)
        print(f"Successfully replied to message {event_id}")
    except LineBotApiError as e:
        # If reply token is invalid, use push message
        if "Invalid reply token" in str(e):
            print(f"Reply token invalid, using push message instead: {str(e)}")
            try:
                # If multiple messages, send them one by one
                if isinstance(messages, list):
                    for message in messages:
                        line_bot_api.push_message(user_id, message)
                else:
                    line_bot_api.push_message(user_id, messages)
                print(f"Successfully pushed message to {user_id}")
            except Exception as push_error:
                print(f"Error sending push message: {str(push_error)}")
        else:
            # For other LINE API errors, log them
            print(f"LINE API Error: {str(e)}")

def search_and_push(query_params, user_id, original_query=""):
    """Search for restaurants using ChatGPT to select and push to user as carousel"""
    try:
        # Search for restaurants
        all_results = search_restaurants(query_params)
        
        # If no results found
        if not all_results or len(all_results) == 0:
            line_bot_api.push_message(
                user_id,
                TextSendMessage(text="Sorry, I couldn't find any restaurants matching your criteria.")
            )
            return
        
        print(f"Found {len(all_results)} restaurants from Google Maps API")
        
        # Use ChatGPT to analyze and select top restaurants
        selected_results = analyze_and_select_restaurants(
            restaurants=all_results, 
            user_query=original_query or "Find a good restaurant nearby",
            max_results=3
        )
        
        # Check if we have selected restaurants
        if not selected_results:
            # Fallback to the original results
            print("No restaurants selected by AI, using top results")
            selected_results = [{"restaurant": r, "explanation": "", "highlight": ""} for r in all_results[:3]]
        
        # Create carousel with the selected restaurants
        carousel_message = create_restaurant_carousel(selected_results)
        
        # Use push message to send the carousel
        line_bot_api.push_message(
            user_id,
            FlexSendMessage(
                alt_text=f"Here are {len(selected_results)} recommended restaurants for you",
                contents=carousel_message
            )
        )
    except Exception as e:
        print(f"Error searching restaurants: {str(e)}")
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=f"I encountered an error while searching: {str(e)}")
        )

def create_restaurant_carousel(selected_restaurants):
    """Create a carousel message with the selected restaurants"""
    bubbles = []
    
    for selected in selected_restaurants:
        restaurant = selected.get("restaurant", {})
        explanation = selected.get("explanation", "")
        highlight = selected.get("highlight", "")
        
        # Create a bubble for each restaurant
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
                        "text": restaurant.get("name", "Restaurant"),
                        "weight": "bold",
                        "size": "xl",
                        "wrap": True
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
                            "label": "View in Google Maps",
                            "uri": f"https://www.google.com/maps/place/?q=place_id:{restaurant.get('place_id', '')}"
                        },
                        "style": "primary"
                    }
                ]
            }
        }
        
        # Add rating if available
        if "rating" in restaurant:
            bubble["body"]["contents"].append({
                "type": "box",
                "layout": "baseline",
                "margin": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": f"Rating: {restaurant.get('rating', 'N/A')} ⭐",
                        "size": "sm",
                        "color": "#999999",
                        "flex": 2
                    }
                ]
            })
        
        # Add price level if available
        if "price_level" in restaurant:
            price_level = restaurant.get("price_level")
            # Make sure price_level is not None and convert to int
            price_level = int(price_level) if price_level is not None else 0
            price_symbols = "💰" * price_level
            bubble["body"]["contents"].append({
                "type": "box",
                "layout": "baseline",
                "margin": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": f"Price: {price_symbols or 'N/A'}",
                        "size": "sm",
                        "color": "#999999",
                        "flex": 2
                    }
                ]
            })
            
        # Add address if available
        if "address" in restaurant:
            bubble["body"]["contents"].append({
                "type": "box",
                "layout": "baseline",
                "margin": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": f"Address: {restaurant.get('address', 'N/A')}",
                        "size": "sm",
                        "color": "#999999",
                        "wrap": True
                    }
                ]
            })
        
        # Add explanation if available
        if explanation:
            bubble["body"]["contents"].append({
                "type": "text",
                "text": explanation,
                "wrap": True,
                "size": "sm",
                "margin": "md",
                "color": "#666666"
            })
            
        # Add highlight if available
        if highlight:
            bubble["body"]["contents"].append({
                "type": "text",
                "text": f"✨ {highlight}",
                "wrap": True,
                "size": "sm",
                "margin": "md",
                "weight": "bold",
                "color": "#1DB446"
            })
            
        bubbles.append(bubble)
    
    # Create carousel with the bubbles
    carousel = {
        "type": "carousel",
        "contents": bubbles
    }
    
    return carousel

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """Handle text messages, parse user requests"""
    user_id = event.source.user_id
    text = event.message.text
    
    # Save original query for later use
    original_query = text
    
    # First, check if the message is related to finding a restaurant
    is_related, message = is_restaurant_related(text)
    if not is_related:
        safe_reply_or_push(
            event,
            TextSendMessage(text=message)
        )
        return
    
    # If we got a greeting message with a response, send it
    if message:
        safe_reply_or_push(
            event,
            TextSendMessage(text=message)
        )
        return
    
    # Check if text is "Any" (user wants generic recommendations)
    if text.lower() in ["any", "anything", "general"]:
        # Get user's location directly in the correct format for Google Maps API
        location = get_user_location_for_search(user_id)
        
        if not location:
            safe_reply_or_push(
                event,
                TextSendMessage(text="Please share your location first so I can find restaurants nearby.")
            )
            return
            
        # Use the user's location with default parameters
        query_params = {
            "location": location,
            "radius": 1000,
            "type": "restaurant"
        }
        
        # Inform user and search
        safe_reply_or_push(
            event,
            TextSendMessage(text="Looking for restaurants near your location...")
        )
        
        # Then search and push results
        search_and_push(query_params, user_id, original_query)
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
            safe_reply_or_push(
                event,
                TextSendMessage(text="Please share your location so I can find restaurants nearby")
            )
            return
    
    # Ensure location is not None
    if "location" not in query_params or not query_params["location"]:
        safe_reply_or_push(
            event,
            TextSendMessage(text="I couldn't determine your location. Please share your location and try again.")
        )
        return
    
    # First acknowledge the request
    safe_reply_or_push(
        event,
        TextSendMessage(text="Searching for restaurants matching your criteria...")
    )
    
    # Final debug log before search
    print(f"Final query params before search: {query_params}")
    
    # Then search and push results
    search_and_push(query_params, user_id, original_query)

@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    """Handle location messages, save to DB and ask for restaurant preferences"""
    user_id = event.source.user_id
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
    
    # Use safe reply method
    safe_reply_or_push(
        event,
        TextSendMessage(text="\n".join(preference_questions))
    )
