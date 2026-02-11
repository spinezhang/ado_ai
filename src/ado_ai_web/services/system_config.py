"""System-level configuration loader for server-wide settings."""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from ado_ai_cli.utils.logger import get_logger

logger = get_logger()


class SystemConfig:
    """
    Load system-level configuration from server config files.

    Checks for config files in this order:
    1. /etc/ado_ai/config.json (Linux/Mac system-wide)
    2. ~/.config/ado_ai/config.json (User-specific)
    3. ./server_config.json (Local development)
    """

    CONFIG_PATHS = [
        "/etc/ado_ai/config.json",
        Path.home() / ".config" / "ado_ai" / "config.json",
        Path("./server_config.json"),
    ]

    def __init__(self):
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from the first available config file."""
        for config_path in self.CONFIG_PATHS:
            config_path = Path(config_path)
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        logger.info(f"Loaded system config from: {config_path}")
                        return config
                except Exception as e:
                    logger.warning(f"Failed to load config from {config_path}: {str(e)}")

        logger.info("No system config file found. Using user-provided credentials only.")
        return {}

    def get_anthropic_api_key(self) -> Optional[str]:
        """Get Anthropic API key from system config."""
        return self._config.get("anthropic_api_key")

    def get_default_work_folder(self) -> Optional[str]:
        """Get default work folder from system config."""
        return self._config.get("default_work_folder")

    def has_anthropic_api_key(self) -> bool:
        """Check if system config provides an Anthropic API key."""
        return bool(self.get_anthropic_api_key())


# Global system config instance
_system_config = None


def get_system_config() -> SystemConfig:
    """Get or create the global system config instance."""
    global _system_config
    if _system_config is None:
        _system_config = SystemConfig()
    return _system_config
