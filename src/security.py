import os
import hmac
import hashlib
import time
from typing import Optional
from fastapi import HTTPException, Security, Header
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Key header
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

# Get API key from environment
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable is not set")

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

def verify_line_signature(x_line_signature: Optional[str] = Header(None)) -> bool:
    """
    Verify the LINE signature from the request header
    """
    if not x_line_signature:
        raise HTTPException(
            status_code=401,
            detail="LINE signature is missing"
        )
    
    # The actual signature verification is handled by the LINE SDK
    # This is just a placeholder to ensure the header exists
    return True 