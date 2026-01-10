"""
Configuration Settings Provider

Centralizes configuration loading from environment variables and files.
Prioritizes local file (api_keys.json) over environment variables.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

class Settings:
    def __init__(self):
        self._api_keys = {}
        self._models = {}
        self._load_api_keys()
        self._load_models()

    def _load_api_keys(self):
        """Load API keys from api_keys.json if it exists."""
        key_file = Path(__file__).parent / "api_keys.json"
        if key_file.exists():
            try:
                with open(key_file, "r") as f:
                    self._api_keys = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load api_keys.json: {e}")

    def _load_models(self):
        """Load model configurations from models.json."""
        model_file = Path(__file__).parent / "models.json"
        if model_file.exists():
            try:
                with open(model_file, "r") as f:
                    self._models = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load models.json: {e}")
        else:
            print("Warning: models.json not found. Using empty model registry.")

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
