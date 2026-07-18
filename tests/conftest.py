"""Pytest configuration for PowerSpawn tests."""
import importlib
import sys
from pathlib import Path

# Repo root so `import powerspawn` works (package lives at powerspawn/).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Tests historically import `PowerSpawn.*` while the on-disk package is
# lowercase `powerspawn`. On case-sensitive filesystems (and some pytest
# collectors) that breaks collection. Alias the package tree.
import powerspawn as _powerspawn  # noqa: E402

sys.modules.setdefault("PowerSpawn", _powerspawn)


def _alias_submodule(dotted: str) -> None:
    """Register PowerSpawn.<rest> -> powerspawn.<rest> if importable."""
    if not dotted.startswith("PowerSpawn."):
        return
    target = "powerspawn." + dotted[len("PowerSpawn.") :]
    try:
        mod = importlib.import_module(target)
    except Exception:
        return
    sys.modules.setdefault(dotted, mod)


# Pre-register common modules used by tests so `from PowerSpawn.X import Y` works.
for _name in (
    "PowerSpawn.config",
    "PowerSpawn.agent_manager",
    "PowerSpawn.logger",
    "PowerSpawn.mcp_server",
    "PowerSpawn.proc",
    "PowerSpawn.context",
    "PowerSpawn.providers",
    "PowerSpawn.providers.types",
    "PowerSpawn.providers.claude",
    "PowerSpawn.providers.codex",
    "PowerSpawn.providers.copilot",
    "PowerSpawn.providers.gemini",
    "PowerSpawn.providers.gemini_cli",
    "PowerSpawn.providers.grok",
    "PowerSpawn.providers.grok_api",
    "PowerSpawn.providers.mistral",
):
    _alias_submodule(_name)
