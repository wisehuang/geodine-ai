import os
import hmac
import hashlib
import time
from typing import Optional
from fastapi import HTTPException, Security, Header, Request
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv
from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError

# Load environment variables
load_dotenv()

# API Key header
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

# Get API key from environment
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable is not set")

# Get LINE channel secret from environment
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
if not LINE_CHANNEL_SECRET:
    raise ValueError("LINE_CHANNEL_SECRET environment variable is not set")

# Create LINE webhook handler
line_handler = WebhookHandler(LINE_CHANNEL_SECRET)

def verify_api_key(api_key: str = Security(api_key_header)) -> bool:
    """
    Verify the API key from the request header
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key is missing"
        )

    if not hmac.compare_digest(api_key, API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    return True

async def verify_line_signature(request: Request, x_line_signature: Optional[str] = Header(None)) -> bool:
    """
    Verify the LINE signature from the request header
    Returns True if signature is valid (actual verification done by LINE SDK in handlers)
    """
    if not x_line_signature:
        raise HTTPException(
            status_code=401,
            detail="LINE signature is missing"
        )

    # The actual signature verification is handled by the LINE SDK in the handlers
    # This is just a placeholder to ensure the header exists
    return True


def validate_api_key(api_key: Optional[str]) -> bool:
    """
    Validate API key for broadcast and other protected endpoints

    Args:
        api_key: API key from request header

    Returns:
        True if valid, False otherwise
    """
    if not api_key:
        return False

    return hmac.compare_digest(api_key, API_KEY)
