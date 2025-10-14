"""
Bot configuration management for supporting multiple LINE bots
"""
import os
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BotConfig:
    """Configuration for a single LINE bot"""
    bot_id: str  # Unique identifier for the bot
    name: str  # Human-readable name
    channel_access_token: str
    channel_secret: str
    description: Optional[str] = None
    webhook_path: Optional[str] = None  # Custom webhook path, defaults to /line/{bot_id}/webhook
    bot_type: Optional[str] = "restaurant"  # Bot type: "restaurant" or "weather"
    use_ai_parsing: bool = True
    default_radius: int = 1000
    default_language: str = "en"
    enabled: bool = True
    image_prompt_template: Optional[str] = None  # Custom prompt template for image generation

    def __post_init__(self):
        """Set default webhook path if not provided"""
        if not self.webhook_path:
            self.webhook_path = f"/line/{self.bot_id}/webhook"


class BotConfigManager:
    """Manages multiple bot configurations"""

    def __init__(self, config_dir: str = None):
        """
        Initialize the bot configuration manager

        Args:
            config_dir: Directory containing bot configuration files
        """
        if config_dir is None:
            # Default to 'bots' directory in project root
            config_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "bots"
            )

        self.config_dir = Path(config_dir)
        self.bots: Dict[str, BotConfig] = {}
        self._load_configs()

    def _load_configs(self):
        """Load all bot configurations from the config directory"""
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(exist_ok=True)

        # Check for legacy single-bot configuration in .env
        self._load_legacy_config()

        # Load configurations from YAML files
        if self.config_dir.exists():
            for config_file in self.config_dir.glob("*.yaml"):
                try:
                    self._load_config_file(config_file)
                except Exception as e:
                    print(f"Error loading bot config from {config_file}: {e}")

    def _load_legacy_config(self):
        """
        Load bot configuration from environment variables for backward compatibility
        Creates a default 'geodine-ai' bot from existing .env settings
        """
        token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        secret = os.getenv("LINE_CHANNEL_SECRET")

        if token and secret:
            # Check if we don't already have a geodine-ai bot configured
            if "geodine-ai" not in self.bots:
                legacy_config = BotConfig(
                    bot_id="geodine-ai",
                    name="GeoDine-AI",
                    channel_access_token=token,
                    channel_secret=secret,
                    description="Legacy bot from environment variables",
                    use_ai_parsing=os.getenv("USE_AI_PARSING", "False").lower() == "true",
                    webhook_path="/line/webhook"  # Keep original path for backward compatibility
                )
                self.bots["geodine-ai"] = legacy_config
                print(f"Loaded legacy bot configuration: {legacy_config.bot_id}")

    def _load_config_file(self, config_file: Path):
        """Load a single bot configuration from a YAML file"""
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)

        # Support environment variable substitution in config
        for key in ['channel_access_token', 'channel_secret']:
            if isinstance(data.get(key), str) and data[key].startswith('${') and data[key].endswith('}'):
                env_var = data[key][2:-1]
                data[key] = os.getenv(env_var, '')

        bot_config = BotConfig(**data)

        if bot_config.enabled:
            self.bots[bot_config.bot_id] = bot_config
            print(f"Loaded bot configuration: {bot_config.bot_id} from {config_file.name}")

    def get_bot(self, bot_id: str) -> Optional[BotConfig]:
        """Get a bot configuration by ID"""
        return self.bots.get(bot_id)

    def get_all_bots(self) -> Dict[str, BotConfig]:
        """Get all registered bot configurations"""
        return self.bots.copy()

    def get_bot_by_webhook_path(self, path: str) -> Optional[BotConfig]:
        """Find a bot by its webhook path"""
        for bot in self.bots.values():
            if bot.webhook_path == path:
                return bot
        return None

    def get_enabled_bots(self) -> List[BotConfig]:
        """Get list of enabled bots"""
        return [bot for bot in self.bots.values() if bot.enabled]

    def add_bot(self, bot_config: BotConfig):
        """Add a new bot configuration programmatically"""
        self.bots[bot_config.bot_id] = bot_config

    def save_config(self, bot_config: BotConfig):
        """Save a bot configuration to a YAML file"""
        config_file = self.config_dir / f"{bot_config.bot_id}.yaml"

        # Convert to dict for YAML serialization
        config_dict = {
            'bot_id': bot_config.bot_id,
            'name': bot_config.name,
            'channel_access_token': bot_config.channel_access_token,
            'channel_secret': bot_config.channel_secret,
            'description': bot_config.description,
            'webhook_path': bot_config.webhook_path,
            'use_ai_parsing': bot_config.use_ai_parsing,
            'default_radius': bot_config.default_radius,
            'default_language': bot_config.default_language,
            'enabled': bot_config.enabled
        }

        with open(config_file, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)

        print(f"Saved bot configuration to {config_file}")


# Global configuration manager instance
config_manager = BotConfigManager()
