"""
Base handler for LINE Bot message processing.
Provides shared functionality for all bot handlers following Clean Architecture principles.
"""
from abc import ABC, abstractmethod
from typing import Union, List
from linebot.exceptions import LineBotApiError
from linebot.models import SendMessage

from src.bot_registry import BotInstance
from src.handlers.message_utils import EventDeduplicationManager


class BaseLineHandler(ABC):
    """
    Abstract base class for LINE Bot message handlers.

    Implements:
    - Event deduplication
    - Safe message sending (reply with push fallback)
    - Common utilities

    Subclasses should implement:
    - handle_text_message()
    - handle_location_message()
    - register_handlers()
    """

    def __init__(self, bot_instance: BotInstance):
        """
        Initialize base handler.

        Args:
            bot_instance: The bot instance this handler manages
        """
        self.bot_instance = bot_instance
        self.event_manager = EventDeduplicationManager(expiry_seconds=300)

    @property
    def bot_id(self) -> str:
        """Get bot ID"""
        return self.bot_instance.bot_id

    @property
    def api(self):
        """Get LINE Bot API client"""
        return self.bot_instance.api

    @property
    def handler(self):
        """Get webhook handler"""
        return self.bot_instance.handler

    def safe_reply_or_push(
        self,
        event,
        messages: Union[SendMessage, List[SendMessage]]
    ) -> None:
        """
        Safely send messages to user with automatic fallback.

        Strategy:
        1. Check for duplicate events using event ID
        2. Try to reply using reply token (faster, preferred)
        3. If reply token invalid/expired, fall back to push message

        Args:
            event: LINE webhook event
            messages: Message(s) to send (single or list)

        Returns:
            None
        """
        user_id = event.source.user_id
        reply_token = event.reply_token

        # Extract event ID for deduplication
        event_id = self._get_event_id(event)

        # Check for duplicate events
        if self.event_manager.is_duplicate(event_id):
            return

        # Try reply first, fall back to push if needed
        try:
            self.api.reply_message(reply_token, messages)
            print(f"Successfully replied to event {event_id}")
        except LineBotApiError as e:
            self._handle_reply_error(e, user_id, messages, event_id)

    def _get_event_id(self, event) -> str:
        """Extract event ID from event object"""
        return getattr(event, 'id', None) or getattr(event.message, 'id', None) or ''

    def _handle_reply_error(
        self,
        error: LineBotApiError,
        user_id: str,
        messages: Union[SendMessage, List[SendMessage]],
        event_id: str
    ) -> None:
        """
        Handle reply token errors by falling back to push messages.

        Args:
            error: The LINE API error
            user_id: Target user ID
            messages: Messages to send
            event_id: Event identifier for logging
        """
        if "Invalid reply token" in str(error):
            print(f"Reply token invalid for event {event_id}, using push message")
            try:
                self._push_messages(user_id, messages)
                print(f"Successfully pushed message to {user_id}")
            except Exception as push_error:
                print(f"Error sending push message: {str(push_error)}")
        else:
            print(f"LINE API Error for event {event_id}: {str(error)}")

    def _push_messages(
        self,
        user_id: str,
        messages: Union[SendMessage, List[SendMessage]]
    ) -> None:
        """
        Send messages using push API.

        Args:
            user_id: Target user ID
            messages: Message(s) to send
        """
        if isinstance(messages, list):
            for message in messages:
                self.api.push_message(user_id, message)
        else:
            self.api.push_message(user_id, messages)

    @abstractmethod
    def handle_text_message(self, event) -> None:
        """
        Handle text messages. Must be implemented by subclasses.

        Args:
            event: LINE MessageEvent with TextMessage
        """
        pass

    @abstractmethod
    def handle_location_message(self, event) -> None:
        """
        Handle location messages. Must be implemented by subclasses.

        Args:
            event: LINE MessageEvent with LocationMessage
        """
        pass

    @abstractmethod
    def register_handlers(self):
        """
        Register message handlers with the webhook handler.
        Must be implemented by subclasses.

        Returns:
            WebhookHandler: The configured handler
        """
        pass
