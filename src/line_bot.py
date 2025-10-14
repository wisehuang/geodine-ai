"""
LINE Bot webhook endpoints - refactored to support multiple bots
"""
import os
from fastapi import APIRouter, Request, HTTPException, Header
from linebot.exceptions import InvalidSignatureError
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

from src.database import init_db
from src.bot_registry import bot_registry
from src.line_bot_handler import register_bot_handlers
from src.weather_bot_handler import register_weather_bot_handlers

# Load environment variables
load_dotenv()

# Initialize database
init_db()

# Create router
router = APIRouter(prefix="/line", tags=["LINE Bot"])


class LineWebhookRequest(BaseModel):
    destination: str
    events: List[Dict[str, Any]]


def create_webhook_endpoint(bot_id: str, webhook_path: str):
    """
    Create a webhook endpoint for a specific bot
    """
    bot_instance = bot_registry.get_bot(bot_id)

    if not bot_instance:
        raise ValueError(f"Bot {bot_id} not found in registry")

    # Register handlers based on bot type
    if bot_instance.bot_type == "weather":
        handler = register_weather_bot_handlers(bot_instance)
    else:
        # Default to restaurant bot handlers
        handler = register_bot_handlers(bot_instance)

    async def webhook_handler(
        request: Request,
        x_line_signature: Optional[str] = Header(None)
    ):
        """
        Handle webhook events from the LINE platform for a specific bot
        """
        body = await request.body()
        body_str = body.decode("utf-8")

        try:
            # Print webhook event for debugging
            print(f"Received LINE webhook for bot {bot_id}: {body_str[:100]}...")
            handler.handle(body_str, x_line_signature)
        except InvalidSignatureError:
            raise HTTPException(status_code=400, detail="Invalid LINE signature")
        except Exception as e:
            print(f"Error handling webhook for bot {bot_id}: {str(e)}")
            # Don't raise exception here to always return 200 OK to LINE

        return {"status": "OK"}

    return webhook_handler


# Register webhook endpoints for all bots
for bot_id, bot_instance in bot_registry.get_all_bots().items():
    webhook_path = bot_instance.webhook_path
    # Remove '/line' prefix if present since router already has it
    if webhook_path.startswith('/line'):
        webhook_path = webhook_path[5:]

    endpoint_func = create_webhook_endpoint(bot_id, webhook_path)

    # Add route dynamically
    router.add_api_route(
        webhook_path,
        endpoint_func,
        methods=["POST"],
        operation_id=f"line_webhook_{bot_id}",
        name=f"LINE Webhook for {bot_instance.name}",
        summary=f"Webhook endpoint for {bot_instance.name}"
    )

    print(f"Registered webhook endpoint: /line{webhook_path} for bot {bot_id}")
