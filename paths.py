"""
Filesystem locations used by PowerSpawn.

PowerSpawn runs as a standard stdio MCP server: the client (Claude Code, VS Code,
Cursor, ...) launches it with the current working directory set to the user's
project. That directory is the workspace spawned agents run in, regardless of
where the package itself is installed (site-packages, a uvx cache, or a vendored
``powerspawn/`` folder inside the project).

Overrides:
    POWERSPAWN_WORKSPACE   - workspace root (default: current working directory)
    POWERSPAWN_STATE_DIR   - where IAC.md is written
    POWERSPAWN_CONFIG_DIR  - user config dir holding api_keys.json / models.json
"""

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent


def get_workspace_dir() -> Path:
    """Project root that spawned agents work in."""
    override = os.environ.get("POWERSPAWN_WORKSPACE")
    return Path(override).resolve() if override else Path.cwd().resolve()


def _is_vendored() -> bool:
    """True when the package is a ``powerspawn/`` folder inside the workspace."""
    try:
        PACKAGE_DIR.relative_to(get_workspace_dir())
        return True
    except ValueError:
        return False


def get_state_dir() -> Path:
    """Directory for IAC.md.

    Vendored checkouts keep writing next to the package (historic behaviour);
    installed packages write to ``<workspace>/.powerspawn/`` instead of
    site-packages.
    """
    override = os.environ.get("POWERSPAWN_STATE_DIR")
    if override:
        return Path(override)
    if _is_vendored():
        return PACKAGE_DIR
    return get_workspace_dir() / ".powerspawn"


def get_user_config_dir() -> Path:
    """Per-user config dir (``%APPDATA%\\powerspawn`` or ``~/.config/powerspawn``)."""
    override = os.environ.get("POWERSPAWN_CONFIG_DIR")
    if override:
        return Path(override)
    if os.name == "nt" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "powerspawn"
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "powerspawn"


def config_candidates(filename: str) -> list[Path]:
    """Lookup order for a config file: workspace, user config dir, package."""
    return [
        get_workspace_dir() / ".powerspawn" / filename,
        get_user_config_dir() / filename,
        PACKAGE_DIR / filename,
    ]
