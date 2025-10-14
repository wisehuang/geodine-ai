"""
LINE Bot message handlers - Restaurant bot handler
Refactored to use clean architecture with base handler
"""
from linebot.models import (
    MessageEvent, TextMessage, LocationMessage,
    TextSendMessage, FlexSendMessage
)

from src.restaurant_finder import search_restaurants
from src.utils import parse_user_request, parse_user_request_with_ai, analyze_and_select_restaurants, is_restaurant_related
from src.translation import detect_language, translate_text
from src.database import save_user_location, get_user_location_for_search
from src.bot_registry import BotInstance
from src.handlers.base_handler import BaseLineHandler


class RestaurantBotHandler(BaseLineHandler):
    """
    Handler for restaurant finder bot.
    Extends BaseLineHandler with restaurant-specific functionality.
    """

    def __init__(self, bot_instance: BotInstance):
        """Initialize restaurant bot handler"""
        super().__init__(bot_instance)

    def handle_text_message(self, event):
        """Handle text messages, parse user requests"""
        user_id = event.source.user_id
        text = event.message.text

        # Detect language
        language = detect_language(text)
        print(f"Detected language: {language}")

        # Save original query for later use
        original_query = text

        # Define English messages (will be translated as needed)
        messages = {
            'not_restaurant_related': "Sorry, I can only help with food and drink related queries.",
            'greeting': "Hello! I'm a food & drink recommendation bot. What type of food or drink would you like to find today?",
            'location_needed': "Please share your location first so I can find food and drink places nearby.",
            'searching_generic': "Looking for food and drink places near your location...",
            'location_request': "Please share your location so I can find food and drink places nearby",
            'location_error': "I couldn't determine your location. Please share your location and try again.",
            'searching_criteria': "Searching for food and drink places matching your criteria..."
        }

        # First, check if the message is related to finding food or drink
        is_related, message = is_restaurant_related(text)
        if not is_related:
            response_text = message or messages['not_restaurant_related']
            # Translate if not English
            if language != 'en':
                response_text = translate_text(response_text, language)

            self.safe_reply_or_push(event, TextSendMessage(text=response_text))
            return

        # If we got a greeting message with a response, send it
        if message:
            # If no specific message in the result, use the default greeting
            response_text = message or messages['greeting']
            # Translate if not English
            if language != 'en':
                response_text = translate_text(response_text, language)

            self.safe_reply_or_push(event, TextSendMessage(text=response_text))
            return

        # Check if text is "Any" (user wants generic recommendations)
        # Define only English generic terms
        generic_terms_en = ["any", "anything", "general", "whatever", "any restaurant", "any food"]

        # Translate generic terms to the user's language if needed
        is_generic_query = False

        # First check if any English term is in the input (for English users)
        if language == 'en':
            for term in generic_terms_en:
                if term.lower() in text.lower():
                    is_generic_query = True
                    break
        else:
            # For non-English users, translate each generic term to their language
            # and check if any of those translations appear in their input
            for term in generic_terms_en:
                translated_term = translate_text(term, language).lower()
                if translated_term in text.lower():
                    is_generic_query = True
                    break

        if is_generic_query:
            # Get user's location directly in the correct format for Google Maps API
            location = get_user_location_for_search(user_id, self.bot_id)

            if not location:
                # Translate the message
                response_text = translate_text(messages['location_needed'], language)

                self.safe_reply_or_push(event, TextSendMessage(text=response_text))
                return

            # Use the user's location with default parameters
            query_params = {
                "location": location,
                "radius": 1000,
                "keyword": "food"  # Use keyword instead of type to find all food establishments
            }

            # Inform user and search
            response_text = translate_text(messages['searching_generic'], language)

            self.safe_reply_or_push(event, TextSendMessage(text=response_text))

            # Then search and push results
            self.search_and_push(query_params, user_id, original_query, language)
            return

        # Parse user request (with AI if enabled)
        if self.bot_instance.use_ai_parsing:
            query_params = parse_user_request_with_ai(text)
        else:
            query_params = parse_user_request(text)

        # Debug log to help diagnose issues
        print(f"Query params after parsing: {query_params}")

        # If no location in parameters, check if user has saved location
        if "location" not in query_params or not query_params["location"]:
            # Get user's location directly in the correct format
            location = get_user_location_for_search(user_id, self.bot_id)
            print(f"Retrieved location from database: {location}")

            if location:
                # Use the stored location
                query_params['location'] = location
                print(f"Using saved location: {location}")
            else:
                # If no location, ask user to share location
                response_text = translate_text(messages['location_request'], language)

                self.safe_reply_or_push(event, TextSendMessage(text=response_text))
                return

        # Ensure location is not None
        if "location" not in query_params or not query_params["location"]:
            response_text = translate_text(messages['location_error'], language)

            self.safe_reply_or_push(event, TextSendMessage(text=response_text))
            return

        # First acknowledge the request
        response_text = translate_text(messages['searching_criteria'], language)

        self.safe_reply_or_push(event, TextSendMessage(text=response_text))

        # Final debug log before search
        print(f"Final query params before search: {query_params}")

        # Then search and push results
        self.search_and_push(query_params, user_id, original_query, language)

    def handle_location_message(self, event):
        """Handle location messages, save to DB and ask for food/drink preferences"""
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
            address=address,
            bot_id=self.bot_id
        )

        # Detect language from address if available, otherwise default to English
        language = detect_language(address) if address else "en"

        # English templates for preference questions
        preference_questions = [
            "I've saved your location! What type of food or drink are you looking for?",
            "For example, you can say:",
            "- \"Japanese food\"",
            "- \"Bubble tea shop\"",
            "- \"Street food\"",
            "- \"Dessert place\"",
            "- \"Coffee shop\"",
            "- Or just say \"Any\" for general recommendations"
        ]

        # Translate each line if needed
        if language != 'en':
            translated_questions = []
            for question in preference_questions:
                translated_questions.append(translate_text(question, language))
            preference_questions = translated_questions

        # Use safe reply method
        self.safe_reply_or_push(event, TextSendMessage(text="\n".join(preference_questions)))

    def search_and_push(self, query_params, user_id, original_query="", language="en"):
        """Search for food/drink establishments and push results to user"""
        try:
            # Set language for search
            query_params["language"] = language

            # Common message templates (will be translated as needed)
            messages = {
                'no_results': "Sorry, I couldn't find any food or drink places matching your criteria.",
                'error': "I encountered an error while searching: "
            }

            # Search for food and drink establishments
            all_results = search_restaurants(query_params)

            # If no results found
            if not all_results or len(all_results) == 0:
                response_text = translate_text(messages['no_results'], language)

                self.api.push_message(
                    user_id,
                    TextSendMessage(text=response_text)
                )
                return

            print(f"Found {len(all_results)} places from Google Maps API")

            # Use ChatGPT to analyze and select top places
            selected_results = analyze_and_select_restaurants(
                restaurants=all_results,
                user_query=original_query or "Find a good place to eat or drink nearby",
                max_results=3,
                language=language
            )

            # Check if we have selected places
            if not selected_results:
                # Fallback to the original results
                print("No places selected by AI, using top results")
                selected_results = [{"restaurant": r, "explanation": "", "highlight": ""} for r in all_results[:3]]

            # Create carousel with the selected places
            carousel_message = self.create_restaurant_carousel(selected_results, language)

            # Use push message to send the carousel
            alt_text_template = f"Here are {len(selected_results)} recommended places for you"
            alt_text = translate_text(alt_text_template, language)

            self.api.push_message(
                user_id,
                FlexSendMessage(
                    alt_text=alt_text,
                    contents=carousel_message
                )
            )
        except Exception as e:
            print(f"Error searching places: {str(e)}")

            error_message = translate_text(messages['error'], language) + str(e)

            self.api.push_message(
                user_id,
                TextSendMessage(text=error_message)
            )

    def create_restaurant_carousel(self, selected_restaurants, language="en"):
        """Create a carousel message with the selected restaurants"""
        bubbles = []

        # English UI labels - will be translated as needed
        ui_labels = {
            'view_map': "View in Google Maps",
            'rating': "Rating",
            'reviews': "reviews",
            'price': "Price",
            'address': "Address"
        }

        # Translate all UI labels
        translated_labels = {}
        for key, value in ui_labels.items():
            translated_labels[key] = translate_text(value, language)

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
                                "label": translated_labels['view_map'],
                                "uri": f"https://www.google.com/maps/place/?q=place_id:{restaurant.get('place_id', '')}"
                            },
                            "style": "primary"
                        }
                    ]
                }
            }

            # Add rating if available
            if "rating" in restaurant:
                rating_text = f"{translated_labels['rating']}: {restaurant.get('rating', 'N/A')}"
                if restaurant.get('user_ratings_total'):
                    rating_text += f" ({restaurant.get('user_ratings_total')} {translated_labels['reviews']})"

                bubble["body"]["contents"].append({
                    "type": "box",
                    "layout": "baseline",
                    "margin": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": rating_text,
                            "size": "sm",
                            "color": "#999999",
                            "margin": "md",
                            "flex": 0
                        }
                    ]
                })

            # Add price level if available
            if "price_level" in restaurant:
                price_level = restaurant.get("price_level")
                # Make sure price_level is not None and convert to int
                price_level = int(price_level) if price_level is not None else 0
                price_symbols = "💰" * price_level

                price_text = f"{translated_labels['price']}: {price_symbols or 'N/A'}"

                bubble["body"]["contents"].append({
                    "type": "box",
                    "layout": "baseline",
                    "margin": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": price_text,
                            "size": "sm",
                            "color": "#999999",
                            "flex": 2
                        }
                    ]
                })

            # Add address if available
            if "address" in restaurant:
                address_text = f"{translated_labels['address']}: {restaurant.get('address', 'N/A')}"

                bubble["body"]["contents"].append({
                    "type": "box",
                    "layout": "baseline",
                    "margin": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": address_text,
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

    def register_handlers(self):
        """Register message handlers with the webhook handler"""
        @self.handler.add(MessageEvent, message=TextMessage)
        def text_message_handler(event):
            self.handle_text_message(event)

        @self.handler.add(MessageEvent, message=LocationMessage)
        def location_message_handler(event):
            self.handle_location_message(event)

        return self.handler


# Backward compatibility: Keep function-based API for existing code
def register_bot_handlers(bot_instance: BotInstance):
    """
    Register message handlers for a bot instance (backward compatibility wrapper)
    Returns the handler so it can be used in webhook processing
    """
    handler_instance = RestaurantBotHandler(bot_instance)
    return handler_instance.register_handlers()
