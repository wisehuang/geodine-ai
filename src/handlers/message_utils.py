"""
Shared utilities for LINE message handling
"""
import time
from typing import Dict


class EventDeduplicationManager:
    """
    Manages event deduplication to prevent processing the same event multiple times.
    Uses in-memory cache with automatic cleanup of old events.
    """

    def __init__(self, expiry_seconds: int = 300):
        """
        Initialize event deduplication manager.

        Args:
            expiry_seconds: How long to keep events in cache (default: 5 minutes)
        """
        self.processed_events: Dict[str, float] = {}
        self.expiry_seconds = expiry_seconds

    def is_duplicate(self, event_id: str) -> bool:
        """
        Check if an event has been processed recently.

        Args:
            event_id: The event identifier

        Returns:
            True if event was recently processed, False otherwise
        """
        if not event_id:
            return False

        current_time = time.time()

        # Check if event exists and hasn't expired
        if event_id in self.processed_events:
            if current_time - self.processed_events[event_id] < self.expiry_seconds:
                print(f"Skipping duplicate event: {event_id}")
                return True

        # Mark event as processed
        self.processed_events[event_id] = current_time

        # Clean up old events
        self._cleanup_old_events(current_time)

        return False

    def _cleanup_old_events(self, current_time: float):
        """Remove events older than expiry time from cache"""
        expired_ids = [
            event_id
            for event_id, timestamp in self.processed_events.items()
            if current_time - timestamp > self.expiry_seconds
        ]

        for event_id in expired_ids:
            del self.processed_events[event_id]

    def clear(self):
        """Clear all processed events from cache"""
        self.processed_events.clear()
