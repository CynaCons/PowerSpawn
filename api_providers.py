"""
API-Based Agent Providers

Direct API integrations for models that don't have CLI tools:
- X.ai Grok (OpenAI-compatible API)
- Google Gemini
- Mistral AI

These complement the CLI-based providers in spawner.py.

API Key Resolution (in priority order):
1. Environment variables (XAI_API_KEY, GEMINI_API_KEY, MISTRAL_API_KEY)
2. Local file: api_keys.json in PowerSpawn directory
3. Error with setup instructions
"""

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from logger import log_spawn_complete, log_spawn_start

# Lazy imports to avoid ImportError if SDK not installed
_openai_client = None
_genai = None
_mistral_client = None

# Cache for loaded API keys from file
_api_keys_cache: Optional[dict] = None
_API_KEYS_FILE = Path(__file__).parent / "api_keys.json"


def _load_api_keys_file() -> dict:
    """Load API keys from local file, with caching."""
    global _api_keys_cache
    if _api_keys_cache is not None:
        return _api_keys_cache

    if _API_KEYS_FILE.exists():
        try:
            with open(_API_KEYS_FILE, "r") as f:
                _api_keys_cache = json.load(f)
                return _api_keys_cache
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load {_API_KEYS_FILE}: {e}")

    _api_keys_cache = {}
    return _api_keys_cache


def _get_api_key(env_vars: str | list[str], provider_name: str, help_url: str) -> str:
    """
    Get API key with fallback: local file -> env vars -> error.

    Local file takes priority (allows overriding env vars).
    Checks multiple possible env var names to handle common aliases.

    Args:
        env_vars: Environment variable name(s) to check (e.g., "XAI_API_KEY" or ["XAI_API_KEY", "GROK_API_KEY"])
        provider_name: Human-readable provider name for error messages
        help_url: URL where user can get an API key

    Returns:
        The API key string

    Raises:
        ValueError: If no API key found anywhere
    """
    # Normalize to list
    if isinstance(env_vars, str):
        env_vars = [env_vars]

    # 1. Check local file FIRST (allows overriding env vars)
    keys = _load_api_keys_file()
    for env_var in env_vars:
        api_key = keys.get(env_var)
        if api_key:
            return api_key

    # 2. Check environment variables (try all aliases)
    for env_var in env_vars:
        api_key = os.getenv(env_var)
        if api_key:
            return api_key

    # 3. No key found - provide helpful error
    primary_var = env_vars[0]
    raise ValueError(
        f"{provider_name} API key not found.\n"
        f"Set it via:\n"
        f"  1. Local file: {_API_KEYS_FILE} (takes priority)\n"
        f"  2. Environment variable: {primary_var}\n"
        f"Get your key from: {help_url}"
    )


@dataclass
class AgentResult:
    """Result from an API-based agent invocation."""
    success: bool
    text: str
    structured_output: Optional[dict] = None
    spawn_id: Optional[str] = None
    duration_ms: int = 0
    cost_usd: float = 0.0
    usage: dict = field(default_factory=dict)
    error: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None


# =============================================================================
# GROK (X.AI) - OpenAI-Compatible API
# =============================================================================

# Available Grok models (as of Jan 2026)
# See: https://docs.x.ai/docs/models
GROK_MODELS = {
    # Grok 4.1 family (latest - Dec 2025)
    "grok-4.1": "grok-4-1-fast-non-reasoning",  # Default - best tool-calling
    "grok-4.1-reasoning": "grok-4-1-fast-reasoning",  # With extended thinking
    # Grok 4 family
    "grok-4": "grok-4-fast-non-reasoning",
    "grok-4-reasoning": "grok-4-fast-reasoning",
    # Grok 3 family (legacy)
    "grok-3": "grok-3-beta",
    "grok-3-fast": "grok-3-fast-beta",
    "grok-3-mini": "grok-3-mini-beta",
    # Specialized
    "grok-code": "grok-code-fast-1",  # Best for agentic coding
}

# Default model for Grok (reasoning model for complex tasks)
GROK_DEFAULT_MODEL = "grok-4.1-reasoning"


def _get_openai_client_for_grok():
    """Get or create OpenAI client configured for X.ai."""
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        # Check multiple possible env var names
        api_key = _get_api_key(
            ["XAI_API_KEY", "GROK_API_KEY", "X_API_KEY"],
            "X.ai Grok",
            "https://console.x.ai"
        )
        _openai_client = OpenAI(
            base_url="https://api.x.ai/v1",
            api_key=api_key,
        )
    return _openai_client


def spawn_grok(
    prompt: str,
    *,
    model: str = None,  # Defaults to GROK_DEFAULT_MODEL
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: int = 300,
    task_summary: Optional[str] = None,
) -> AgentResult:
    """
    Spawn a Grok agent via X.ai API.

    Grok uses an OpenAI-compatible API, so we use the OpenAI SDK with a custom base_url.

    Args:
        prompt: The task/instruction for the agent
        model: Model to use (grok-4, grok-4.1, grok-code-fast)
        system_prompt: Optional system prompt
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens in response
        timeout: Timeout in seconds
        task_summary: Optional short description for logging

    Returns:
        AgentResult with the agent's response
    """
    start_time = time.time()

    # Use default model if not specified
    if model is None:
        model = GROK_DEFAULT_MODEL

    # Resolve model alias
    resolved_model = GROK_MODELS.get(model, model)

    # Log spawn start
    spawn_id = log_spawn_start(
        agent="Grok",
        model=resolved_model,
        prompt=prompt,
        tools=["api"],
        task_summary=task_summary,
    )

    try:
        client = _get_openai_client_for_grok()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

        duration = time.time() - start_time

        # Extract response text
        output_text = response.choices[0].message.content if response.choices else ""

        # Extract usage info
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        # Log completion
        log_spawn_complete(
            spawn_id=spawn_id,
            success=True,
            result_text=output_text,
            duration_seconds=duration,
            cost_usd=0.0,  # X.ai pricing not exposed in response
            error=None,
        )

        return AgentResult(
            success=True,
            text=output_text,
            spawn_id=spawn_id,
            duration_ms=int(duration * 1000),
            usage=usage,
            model=resolved_model,
            provider="xai",
        )

    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)
        log_spawn_complete(
            spawn_id=spawn_id,
            success=False,
            result_text="",
            duration_seconds=duration,
            error=error_msg,
        )
        return AgentResult(
            success=False,
            text="",
            spawn_id=spawn_id,
            error=error_msg,
            model=resolved_model,
            provider="xai",
        )


# =============================================================================
# GOOGLE GEMINI
# =============================================================================

# Available Gemini models (as of Jan 2026)
# See: https://ai.google.dev/gemini-api/docs/models
GEMINI_MODELS = {
    # Gemini 3 family (latest - Dec 2025)
    "gemini-3-pro": "gemini-3-pro-preview",  # Default - best reasoning
    "gemini-3-flash": "gemini-3-flash-preview",  # Fast & efficient
    # Gemini 2.x family
    "gemini-2.0-flash": "gemini-2.0-flash",
    "gemini-2.0-flash-lite": "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite": "gemini-2.5-flash-lite",
    # Aliases
    "gemini-pro": "gemini-3-pro-preview",  # Alias for latest pro
    "gemini-flash": "gemini-3-flash-preview",  # Alias for latest flash
}

# Default model for Gemini (best reasoning)
GEMINI_DEFAULT_MODEL = "gemini-3-pro"


def _get_gemini_model(model_name: str):
    """Get or create Gemini model instance."""
    global _genai
    if _genai is None:
        import google.generativeai as genai
        # Check multiple possible env var names
        api_key = _get_api_key(
            ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_KEY"],
            "Google Gemini",
            "https://aistudio.google.com/apikey"
        )
        genai.configure(api_key=api_key)
        _genai = genai
    return _genai.GenerativeModel(model_name)


def spawn_gemini(
    prompt: str,
    *,
    model: str = None,  # Defaults to GEMINI_DEFAULT_MODEL
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: int = 300,
    task_summary: Optional[str] = None,
) -> AgentResult:
    """
    Spawn a Gemini agent via Google AI API.

    Args:
        prompt: The task/instruction for the agent
        model: Model to use (gemini-3-pro, gemini-2.5-pro, gemini-2.0-flash)
        system_prompt: Optional system prompt (prepended to user prompt)
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens in response
        timeout: Timeout in seconds (not directly supported, included for API consistency)
        task_summary: Optional short description for logging

    Returns:
        AgentResult with the agent's response
    """
    start_time = time.time()

    # Use default model if not specified
    if model is None:
        model = GEMINI_DEFAULT_MODEL

    # Resolve model alias
    resolved_model = GEMINI_MODELS.get(model, model)

    # Log spawn start
    spawn_id = log_spawn_start(
        agent="Gemini",
        model=resolved_model,
        prompt=prompt,
        tools=["api"],
        task_summary=task_summary,
    )

    try:
        gemini_model = _get_gemini_model(resolved_model)

        # Build prompt (Gemini doesn't have separate system prompt in basic API)
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        # Configure generation
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        response = gemini_model.generate_content(
            full_prompt,
            generation_config=generation_config,
        )

        duration = time.time() - start_time

        # Extract response text
        output_text = response.text if response.text else ""

        # Extract usage info (if available)
        usage = {}
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = {
                "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0),
                "completion_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0),
                "total_tokens": getattr(response.usage_metadata, 'total_token_count', 0),
            }

        # Log completion
        log_spawn_complete(
            spawn_id=spawn_id,
            success=True,
            result_text=output_text,
            duration_seconds=duration,
            cost_usd=0.0,
            error=None,
        )

        return AgentResult(
            success=True,
            text=output_text,
            spawn_id=spawn_id,
            duration_ms=int(duration * 1000),
            usage=usage,
            model=resolved_model,
            provider="google",
        )

    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)
        log_spawn_complete(
            spawn_id=spawn_id,
            success=False,
            result_text="",
            duration_seconds=duration,
            error=error_msg,
        )
        return AgentResult(
            success=False,
            text="",
            spawn_id=spawn_id,
            error=error_msg,
            model=resolved_model,
            provider="google",
        )


# =============================================================================
# MISTRAL AI
# =============================================================================

# Available Mistral models (as of Jan 2026)
# See: https://docs.mistral.ai/getting-started/models
MISTRAL_MODELS = {
    # Mistral 3 family (latest - Dec 2025)
    "mistral-large": "mistral-large-latest",  # Default - best reasoning
    "mistral-large-3": "mistral-large-3-25-12",  # Specific version
    "mistral-medium": "mistral-medium-latest",
    "mistral-small": "mistral-small-latest",
    # Coding models
    "devstral": "devstral-2-25-12",  # Best coding agent (123B)
    "devstral-2": "devstral-2-25-12",
    "devstral-small": "devstral-small-2-25-12",  # Runs locally (24B)
    "codestral": "codestral-latest",  # Code completion
    # Ministral family (small dense models)
    "ministral-14b": "ministral-3-14b-25-12",
    "ministral-8b": "ministral-3-8b-25-12",
    "ministral-3b": "ministral-3-3b-25-12",
    # Reasoning models
    "magistral": "magistral-medium-1-2-25-09",
    "magistral-small": "magistral-small-1-2-25-09",
    # Legacy
    "mixtral": "open-mixtral-8x22b",
    "mistral-nemo": "mistral-nemo-12b-24-07",
}

# Default model for Mistral (best general-purpose)
MISTRAL_DEFAULT_MODEL = "mistral-large"


def _get_mistral_client():
    """Get or create Mistral client."""
    global _mistral_client
    if _mistral_client is None:
        from mistralai import Mistral
        api_key = _get_api_key("MISTRAL_API_KEY", "Mistral AI", "https://console.mistral.ai")
        _mistral_client = Mistral(api_key=api_key)
    return _mistral_client


def spawn_mistral(
    prompt: str,
    *,
    model: str = None,  # Defaults to MISTRAL_DEFAULT_MODEL
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: int = 300,
    task_summary: Optional[str] = None,
) -> AgentResult:
    """
    Spawn a Mistral agent via Mistral AI API.

    Args:
        prompt: The task/instruction for the agent
        model: Model to use (mistral-large, mistral-medium, mistral-small, mixtral, devstral, codestral)
        system_prompt: Optional system prompt
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens in response
        timeout: Timeout in seconds (not directly supported in SDK)
        task_summary: Optional short description for logging

    Returns:
        AgentResult with the agent's response
    """
    start_time = time.time()

    # Use default model if not specified
    if model is None:
        model = MISTRAL_DEFAULT_MODEL

    # Resolve model alias
    resolved_model = MISTRAL_MODELS.get(model, model)

    # Log spawn start
    spawn_id = log_spawn_start(
        agent="Mistral",
        model=resolved_model,
        prompt=prompt,
        tools=["api"],
        task_summary=task_summary,
    )

    try:
        client = _get_mistral_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.complete(
            model=resolved_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        duration = time.time() - start_time

        # Extract response text
        output_text = ""
        if response.choices and len(response.choices) > 0:
            output_text = response.choices[0].message.content or ""

        # Extract usage info
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        # Log completion
        log_spawn_complete(
            spawn_id=spawn_id,
            success=True,
            result_text=output_text,
            duration_seconds=duration,
            cost_usd=0.0,
            error=None,
        )

        return AgentResult(
            success=True,
            text=output_text,
            spawn_id=spawn_id,
            duration_ms=int(duration * 1000),
            usage=usage,
            model=resolved_model,
            provider="mistral",
        )

    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)
        log_spawn_complete(
            spawn_id=spawn_id,
            success=False,
            result_text="",
            duration_seconds=duration,
            error=error_msg,
        )
        return AgentResult(
            success=False,
            text="",
            spawn_id=spawn_id,
            error=error_msg,
            model=resolved_model,
            provider="mistral",
        )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _has_api_key(env_vars: str | list[str]) -> bool:
    """Check if an API key is available (env var or local file)."""
    if isinstance(env_vars, str):
        env_vars = [env_vars]

    for env_var in env_vars:
        if os.getenv(env_var):
            return True

    keys = _load_api_keys_file()
    for env_var in env_vars:
        if keys.get(env_var):
            return True

    return False


def get_available_api_providers() -> dict:
    """
    Check which API providers are configured (have API keys).

    Checks both environment variables and local api_keys.json file.
    Also checks common aliases for each provider.

    Returns:
        Dict with provider names and their availability status
    """
    return {
        "grok": _has_api_key(["XAI_API_KEY", "GROK_API_KEY", "X_API_KEY"]),
        "gemini": _has_api_key(["GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_KEY"]),
        "mistral": _has_api_key("MISTRAL_API_KEY"),
    }


def spawn_api(
    prompt: str,
    *,
    provider: str,
    model: Optional[str] = None,
    **kwargs,
) -> AgentResult:
    """
    Universal API spawn function - routes to the appropriate provider.

    Args:
        prompt: The task/instruction for the agent
        provider: Provider name (grok, gemini, mistral)
        model: Optional model override
        **kwargs: Additional arguments passed to provider function

    Returns:
        AgentResult from the selected provider
    """
    provider = provider.lower()

    if provider in ("grok", "xai", "x.ai"):
        return spawn_grok(prompt, model=model or "grok-4", **kwargs)
    elif provider in ("gemini", "google"):
        return spawn_gemini(prompt, model=model or "gemini-3-pro", **kwargs)
    elif provider in ("mistral",):
        return spawn_mistral(prompt, model=model or "mistral-large", **kwargs)
    else:
        return AgentResult(
            success=False,
            text="",
            error=f"Unknown provider: {provider}. Available: grok, gemini, mistral",
            provider=provider,
        )
