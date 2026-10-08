"""
Provider availability: which spawn_* tools can actually run on this machine.

CLI providers need their binary on PATH (and a login, which we can't check
without running them); API providers need an API key. Each entry says what
is missing and where to get it.
"""

import os
import shutil
from typing import Any

from ..config import settings

# provider -> (tool, kind, binary or settings key, display name, where to get it)
PROVIDERS = {
    "claude": ("spawn_claude", "cli", "claude", "Claude Code CLI",
               "https://code.claude.com/docs"),
    "codex": ("spawn_codex", "cli", "codex", "OpenAI Codex CLI",
              "https://developers.openai.com/codex"),
    "copilot": ("spawn_copilot", "cli", "copilot", "GitHub Copilot CLI",
                "https://github.com/github/copilot-cli"),
    "cursor": ("spawn_cursor", "cli", os.environ.get("CURSOR_AGENT_BIN", "cursor-agent"),
               "Cursor CLI", "https://cursor.com/docs/cli"),
    "gemini_cli": ("spawn_gemini_cli", "cli", "gemini", "Gemini CLI",
                   "https://github.com/google-gemini/gemini-cli"),
    "grok": ("spawn_grok", "cli", "grok", "Grok Build CLI", "https://x.ai"),
    "grok_api": ("spawn_grok_api", "api", "grok", "xAI API (XAI_API_KEY)",
                 "https://console.x.ai"),
    "gemini": ("spawn_gemini", "api", "gemini", "Gemini API (GEMINI_API_KEY)",
               "https://aistudio.google.com/apikey"),
    "mistral": ("spawn_mistral", "api", "mistral", "Mistral API (MISTRAL_API_KEY)",
                "https://console.mistral.ai"),
}


def verify_providers_availability() -> dict[str, Any]:
    """Report which providers are usable, with a hint and link for each missing one."""
    providers = {}
    for key, (tool, kind, target, name, url) in PROVIDERS.items():
        if kind == "cli":
            available = shutil.which(target) is not None
            missing = f"'{target}' is not on PATH: install {name} and log in"
        else:
            available = settings.get_api_key(target) is not None
            missing = "no API key: set it in the MCP server's env or api_keys.json"
        providers[key] = {
            "tool": tool,
            "type": kind,
            "name": name,
            "available": available,
            "message": "ready" if available else missing,
            "install_url": url,
        }

    available = sum(p["available"] for p in providers.values())
    if available == 0:
        overall = "none"
        recommendation = "No providers found. Install at least one CLI (e.g. Claude Code or Codex) or set an API key."
    elif available < 3:
        overall = "limited"
        recommendation = "Only a few providers are available; add CLIs or API keys to spread work across subscriptions."
    else:
        overall = "good"
        recommendation = "Good coverage: use the spawn_* tools to spread work across your subscriptions."
    return {
        "overall": overall,
        "summary": {
            "total_providers": len(providers),
            "available": available,
            "cli_available": sum(p["available"] for p in providers.values() if p["type"] == "cli"),
            "api_available": sum(p["available"] for p in providers.values() if p["type"] == "api"),
        },
        "providers": providers,
        "recommendation": recommendation,
        "note": "CLI providers are checked on PATH only; a missing login shows up when you spawn.",
    }
