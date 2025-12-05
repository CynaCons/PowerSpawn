# PowerSpawn Tests

Unit tests for PowerSpawn MCP server.

## Running Tests

```bash
# From the powerspawn directory
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_logger.py -v

# Run with coverage (if pytest-cov is installed)
python -m pytest tests/ --cov=. --cov-report=html
```

## Test Structure

- `conftest.py` - Pytest configuration and shared fixtures
- `test_imports.py` - Tests for module import correctness
- `test_logger.py` - Tests for IAC.md logging functions
- `test_parser.py` - Tests for Claude/Codex response parsing
- `test_mcp_server.py` - Integration tests for MCP server structure

## Test Coverage

### Imports (`test_imports.py`)

- ✅ Spawner module imports (spawn_claude, spawn_codex, spawn_copilot, AgentResult)
- ✅ Logger module imports
- ✅ Parser module imports

### Logger Module (`test_logger.py`)

- ✅ Spawn ID generation (format and uniqueness)
- ✅ IAC.md entry creation
- ✅ Task summary auto-generation
- ✅ Spawn completion tracking
- ✅ Failure handling
- ✅ Newest-first ordering
- ✅ Entry limit enforcement (MAX_IAC_ENTRIES)
- ✅ CONTEXT.md active agent tracking
- ✅ Global logger functions

### Parser Module (`test_parser.py`)

- ✅ Claude JSON response parsing
- ✅ Claude error response handling
- ✅ Invalid JSON handling
- ✅ Codex JSONL event parsing
- ✅ Codex message event structure
- ✅ Codex invalid JSON handling

### MCP Server Integration (`test_mcp_server.py`)

- ✅ MCP server module imports correctly
- ✅ SERVER_VERSION constant exists and follows semver
- ✅ list_tools handler is defined
- ✅ call_tool handler is defined
- ✅ Spawn functions are callable
- ✅ AgentResult dataclass structure and defaults
- ✅ CodexEvent dataclass structure and properties
- ✅ MCP server global state variables
- ✅ Helper functions (sanitize_for_json, utc_now_iso, get_workspace_dir)
- ✅ COPILOT_MODELS constant mapping
- ✅ IS_WINDOWS platform constant

## Guidelines

- Tests use temporary directories via pytest's `tmp_path` fixture
- Tests are isolated and don't affect production files
- Use `encoding='utf-8'` when reading files to ensure cross-platform compatibility
- Mock `get_output_dir()` to redirect logger output to temp directories
