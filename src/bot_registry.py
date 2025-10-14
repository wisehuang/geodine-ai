"""
Bot registry for managing multiple LINE bot instances
"""
from typing import Dict, Optional
from linebot import LineBotApi, WebhookHandler
from src.bot_config import BotConfig, config_manager


class BotInstance:
    """
    Represents a single LINE bot instance with its API client and webhook handler
    """

    def __init__(self, config: BotConfig):
        self.config = config
        self.api = LineBotApi(config.channel_access_token)
        self.handler = WebhookHandler(config.channel_secret)

    @property
    def bot_id(self) -> str:
        return self.config.bot_id

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def webhook_path(self) -> str:
        return self.config.webhook_path

    @property
    def bot_type(self) -> str:
        return self.config.bot_type or "restaurant"

    @property
    def use_ai_parsing(self) -> bool:
        return self.config.use_ai_parsing


class BotRegistry:
    """
    Registry for managing multiple bot instances
    Uses singleton pattern to ensure single registry instance
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BotRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.bots: Dict[str, BotInstance] = {}
        self._initialized = True
        self._load_bots()

    def _load_bots(self):
        """Load all enabled bots from configuration"""
        for bot_config in config_manager.get_enabled_bots():
            try:
                bot_instance = BotInstance(bot_config)
                self.bots[bot_config.bot_id] = bot_instance
                print(f"Registered bot: {bot_config.bot_id} ({bot_config.name})")
            except Exception as e:
                print(f"Error loading bot {bot_config.bot_id}: {e}")

    def get_bot(self, bot_id: str) -> Optional[BotInstance]:
        """Get a bot instance by bot_id"""
        return self.bots.get(bot_id)

    def get_bot_by_webhook_path(self, path: str) -> Optional[BotInstance]:
        """Find a bot by its webhook path"""
        for bot in self.bots.values():
            if bot.webhook_path == path:
                return bot
        return None

    def get_all_bots(self) -> Dict[str, BotInstance]:
        """Get all registered bot instances"""
        return self.bots.copy()

    def register_bot(self, config: BotConfig) -> BotInstance:
        """Register a new bot instance"""
        bot_instance = BotInstance(config)
        self.bots[config.bot_id] = bot_instance
        return bot_instance

    def unregister_bot(self, bot_id: str) -> bool:
        """Unregister a bot instance"""
        if bot_id in self.bots:
            del self.bots[bot_id]
            return True
        return False

    def reload(self):
        """Reload all bots from configuration"""
        self.bots.clear()
        self._load_bots()


# Global bot registry instance
bot_registry = BotRegistry()
