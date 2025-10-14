"""
Broadcast API Router

This router provides endpoints for daily weather broadcasts.
Designed to be called by cron jobs for automated daily messaging.
"""
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

from src.daily_broadcast_service import get_broadcast_service
from src.security import validate_api_key

# Load environment variables
load_dotenv()

# Create router
router = APIRouter(prefix="/broadcast", tags=["Broadcast"])


class BroadcastRequest(BaseModel):
    """Request model for broadcast endpoint"""
    bot_id: str = "weather-ootd"
    delay_between_users: float = 0.5  # Delay in seconds between users (rate limiting)


class TestBroadcastRequest(BaseModel):
    """Request model for test broadcast endpoint"""
    bot_id: str = "weather-ootd"
    test_user_id: str  # LINE user ID to send test to


class BroadcastResponse(BaseModel):
    """Response model for broadcast endpoint"""
    status: str
    message: str
    total_subscribers: int
    successful: int
    failed: int
    errors: Optional[list] = None


@router.post("/daily-weather", response_model=BroadcastResponse)
async def broadcast_daily_weather(
    request: BroadcastRequest,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None)
):
    """
    Broadcast daily weather and outfit recommendations to all subscribers

    This endpoint is designed to be called by a cron job once per day.

    **Authentication**: Requires API key in X-API-Key header

    **Parameters**:
    - bot_id: The weather bot ID to broadcast from (default: "weather-ootd")
    - delay_between_users: Seconds to wait between sending to each user (default: 0.5)

    **Returns**:
    - status: "success" or "partial_success" or "failed"
    - message: Human-readable status message
    - total_subscribers: Total number of subscribers found
    - successful: Number of successful sends
    - failed: Number of failed sends
    - errors: List of error messages (if any)

    **Example cURL**:
    ```bash
    curl -X POST "http://localhost:8000/broadcast/daily-weather" \\
      -H "X-API-Key: your_api_key" \\
      -H "Content-Type: application/json" \\
      -d '{"bot_id": "weather-ootd", "delay_between_users": 0.5}'
    ```

    **Example crontab entry (daily at 7 AM)**:
    ```
    0 7 * * * curl -X POST "http://your-server.com/broadcast/daily-weather" -H "X-API-Key: your_api_key" -H "Content-Type: application/json" -d '{"bot_id": "weather-ootd"}' >> /var/log/weather-broadcast.log 2>&1
    ```
    """
    # Validate API key
    if not validate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    try:
        # Get broadcast service
        broadcast_service = get_broadcast_service(request.bot_id)

        # Execute broadcast (synchronously to ensure it completes)
        result = broadcast_service.broadcast_daily_weather(
            delay_between_users=request.delay_between_users
        )

        # Determine status
        if result['failed'] == 0:
            status = "success"
            message = f"Successfully broadcast to all {result['successful']} subscribers"
        elif result['successful'] > 0:
            status = "partial_success"
            message = (
                f"Broadcast completed with some errors. "
                f"Successful: {result['successful']}, Failed: {result['failed']}"
            )
        else:
            status = "failed"
            message = f"Broadcast failed for all {result['failed']} subscribers"

        return BroadcastResponse(
            status=status,
            message=message,
            total_subscribers=result['total_subscribers'],
            successful=result['successful'],
            failed=result['failed'],
            errors=result['errors'] if result['errors'] else None
        )

    except ValueError as e:
        # Bot not found or configuration error
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        # Unexpected error
        raise HTTPException(status_code=500, detail=f"Broadcast failed: {str(e)}")


@router.post("/test", response_model=Dict[str, Any])
async def test_broadcast(
    request: TestBroadcastRequest,
    x_api_key: Optional[str] = Header(None)
):
    """
    Send a test broadcast to a single user

    Use this endpoint to test the broadcast functionality before scheduling cron jobs.

    **Authentication**: Requires API key in X-API-Key header

    **Parameters**:
    - bot_id: The weather bot ID to test with (default: "weather-ootd")
    - test_user_id: LINE user ID to send test message to

    **Returns**:
    - success: True if test successful, False otherwise
    - message: Status message
    - bot_id: Bot ID used for test

    **Example**:
    ```bash
    curl -X POST "http://localhost:8000/broadcast/test" \\
      -H "X-API-Key: your_api_key" \\
      -H "Content-Type: application/json" \\
      -d '{"bot_id": "weather-ootd", "test_user_id": "U1234567890abcdef"}'
    ```
    """
    # Validate API key
    if not validate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    try:
        # Get broadcast service
        broadcast_service = get_broadcast_service(request.bot_id)

        # Send test broadcast
        success = broadcast_service.send_test_broadcast(request.test_user_id)

        if success:
            return {
                "success": True,
                "message": f"Test broadcast sent successfully to user {request.test_user_id}",
                "bot_id": request.bot_id
            }
        else:
            return {
                "success": False,
                "message": "Test broadcast failed. Check server logs for details.",
                "bot_id": request.bot_id
            }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test broadcast failed: {str(e)}")


@router.get("/status/{bot_id}")
async def get_broadcast_status(
    bot_id: str,
    x_api_key: Optional[str] = Header(None)
):
    """
    Get broadcast status and subscriber count for a bot

    **Authentication**: Requires API key in X-API-Key header

    **Parameters**:
    - bot_id: The bot ID to check status for

    **Returns**:
    - bot_id: Bot ID
    - bot_type: Bot type (should be "weather")
    - subscriber_count: Number of subscribers
    - has_custom_prompt: Whether bot has custom image prompt configured

    **Example**:
    ```bash
    curl -X GET "http://localhost:8000/broadcast/status/weather-ootd" \\
      -H "X-API-Key: your_api_key"
    ```
    """
    # Validate API key
    if not validate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    try:
        # Get broadcast service to validate bot exists
        broadcast_service = get_broadcast_service(bot_id)

        # Get subscriber count
        from src.database import get_all_bot_subscribers
        subscribers = get_all_bot_subscribers(bot_id)

        return {
            "bot_id": bot_id,
            "bot_name": broadcast_service.bot_instance.name,
            "bot_type": broadcast_service.bot_instance.bot_type,
            "subscriber_count": len(subscribers),
            "subscribers_with_location": sum(1 for s in subscribers if s.get('latitude')),
            "has_custom_prompt": bool(broadcast_service.bot_instance.config.image_prompt_template),
            "status": "ready"
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
