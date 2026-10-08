"""
Configuration Settings Provider

Centralizes configuration loading from environment variables and files.
Prioritizes api_keys.json (workspace .powerspawn/, user config dir, package dir)
over environment variables.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

from .paths import PACKAGE_DIR, config_candidates


def _read_json(path: Path) -> Optional[Any]:
    """Parse a JSON file, or return None if it is missing or invalid."""
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        # stderr: stdout is the MCP stdio channel.
        print(f"Warning: Failed to load {path}: {e}", file=sys.stderr)
        return None

class Settings:
    def __init__(self):
        self._api_keys = {}
        self._models = {}
        self._load_api_keys()
        self._load_models()

    def _load_api_keys(self):
        """Load API keys from api_keys.json files (workspace > user config > package)."""
        for key_file in reversed(config_candidates("api_keys.json")):
            data = _read_json(key_file)
            if isinstance(data, dict):
                self._api_keys.update(data)

    def _load_models(self):
        """Load the packaged models.json, then overlay user/workspace overrides.

        An override file only needs the providers (and aliases) it changes.
        """
        self._models = _read_json(PACKAGE_DIR / "models.json") or {}
        if not self._models:
            print("Warning: models.json not found. Using empty model registry.", file=sys.stderr)
        for override in reversed(config_candidates("models.json")[:-1]):
            for provider, cfg in (_read_json(override) or {}).items():
                base = self._models.setdefault(provider, {"aliases": {}})
                base.setdefault("aliases", {}).update(cfg.get("aliases", {}))
                if "default" in cfg:
                    base["default"] = cfg["default"]

    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a provider.
        Priority: 1. api_keys.json, 2. Env Vars (checking aliases)
        """
        provider_key_map = {
            "grok": ["XAI_API_KEY", "GROK_API_KEY", "X_API_KEY"],
            "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_KEY"],
            "mistral": ["MISTRAL_API_KEY"],
        }
        
        possible_vars = provider_key_map.get(provider.lower(), [])
        
        # 1. Check file cache
        for var_name in possible_vars:
            if var_name in self._api_keys:
                return self._api_keys[var_name]
                
        # 2. Check environment variables
        for var_name in possible_vars:
            val = os.getenv(var_name)
            if val:
                return val
                
        return None

    def get_model_alias(self, provider: str, model_name: Optional[str]) -> str:
        """
        Resolve a model alias to its full name for a specific provider.
        If model_name is None, returns the default model for that provider.
        """
        provider_config = self._models.get(provider.lower(), {})
        
        if not model_name:
            return provider_config.get("default", model_name)
            
        aliases = provider_config.get("aliases", {})
        return aliases.get(model_name, model_name)
    
    def get_model_list(self, provider: str) -> list[str]:
        """Get list of available aliases for a provider."""
        provider_config = self._models.get(provider.lower(), {})
        return list(provider_config.get("aliases", {}).keys())

# Singleton instance
settings = Settings()
