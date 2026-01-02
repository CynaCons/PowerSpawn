#!/usr/bin/env python3
"""
API Agent Examples for PowerSpawn

Demonstrates spawning API-based agents (Grok, Gemini, Mistral).
These agents return text responses only - they cannot modify files.

Use API agents for:
- Research and analysis
- Getting second opinions from different models
- Drafting content (coordinator applies results)
- Parallel queries for comparison

KEY DIFFERENCE: CLI vs API Agents
---------------------------------
CLI Agents (spawn_claude, spawn_codex):
  - Can execute tools (Bash, Read, Write, Glob, etc.)
  - Can modify files and run commands
  - Have access to the local filesystem
  - Use the CLI tooling (claude, codex)

API Agents (spawn_grok, spawn_gemini, spawn_mistral):
  - Text-only responses
  - Cannot access filesystem or execute commands
  - Useful for analysis, drafting, research
  - The coordinator must apply any suggested changes
"""

import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api_providers import (
    spawn_grok,
    spawn_gemini,
    spawn_mistral,
    spawn_api,
    get_available_api_providers,
    GROK_MODELS,
    GEMINI_MODELS,
    MISTRAL_MODELS,
)


# =============================================================================
# Example 1: Basic Grok Usage
# =============================================================================

def example_grok_basic():
    """Basic Grok (X.ai) invocation."""
    print("=" * 60)
    print("Example 1: Basic Grok (X.ai) invocation")
    print("=" * 60)

    result = spawn_grok(
        "What are the top 3 considerations when migrating a Python 2 "
        "codebase to Python 3? Be concise.",
        model="grok-4",
        task_summary="Python migration advice",
    )

    print(f"Success: {result.success}")
    if result.success:
        print(f"Model: {result.model}")
        print(f"Response:\n{result.text[:500]}...")
        print(f"Duration: {result.duration_ms}ms")
        if result.usage:
            print(f"Tokens: {result.usage.get('total_tokens', 'N/A')}")
    else:
        print(f"Error: {result.error}")
    print()


# =============================================================================
# Example 2: Basic Gemini Usage
# =============================================================================

def example_gemini_basic():
    """Basic Gemini (Google) invocation."""
    print("=" * 60)
    print("Example 2: Basic Gemini (Google) invocation")
    print("=" * 60)

    result = spawn_gemini(
        "Explain the difference between async/await and threads in Python. "
        "Include a brief code example.",
        model="gemini-3-pro",
        task_summary="Async vs threads explanation",
    )

    print(f"Success: {result.success}")
    if result.success:
        print(f"Model: {result.model}")
        print(f"Response:\n{result.text[:500]}...")
        print(f"Duration: {result.duration_ms}ms")
    else:
        print(f"Error: {result.error}")
    print()


# =============================================================================
# Example 3: Basic Mistral Usage
# =============================================================================

def example_mistral_basic():
    """Basic Mistral AI invocation."""
    print("=" * 60)
    print("Example 3: Basic Mistral AI invocation")
    print("=" * 60)

    result = spawn_mistral(
        "What are the key differences between REST and GraphQL APIs? "
        "When should you use each?",
        model="mistral-large",
        task_summary="REST vs GraphQL comparison",
    )

    print(f"Success: {result.success}")
    if result.success:
        print(f"Model: {result.model}")
        print(f"Response:\n{result.text[:500]}...")
        print(f"Duration: {result.duration_ms}ms")
    else:
        print(f"Error: {result.error}")
    print()


# =============================================================================
# Example 4: Parallel Spawning - Query All Providers
# =============================================================================

def example_parallel_spawning():
    """
    Spawn multiple API agents in parallel and compare responses.

    This is useful for:
    - Getting diverse perspectives on a problem
    - Comparing model outputs for quality assessment
    - Redundancy when one provider might fail
    """
    print("=" * 60)
    print("Example 4: Parallel spawning - Query all providers")
    print("=" * 60)

    prompt = "In one paragraph, explain what makes a good code review."

    # Check which providers are available
    available = get_available_api_providers()
    print(f"Available providers: {available}")

    # Define spawn tasks for available providers
    tasks = []
    if available.get("grok"):
        tasks.append(("Grok", lambda: spawn_grok(prompt, task_summary="Code review advice")))
    if available.get("gemini"):
        tasks.append(("Gemini", lambda: spawn_gemini(prompt, task_summary="Code review advice")))
    if available.get("mistral"):
        tasks.append(("Mistral", lambda: spawn_mistral(prompt, task_summary="Code review advice")))

    if not tasks:
        print("No API providers configured. Skipping parallel example.")
        print()
        return

    # Execute in parallel using ThreadPoolExecutor
    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_name = {executor.submit(fn): name for name, fn in tasks}

        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                result = future.result()
                results[name] = result
            except Exception as e:
                print(f"  {name} failed: {e}")

    # Display results
    for name, result in results.items():
        print(f"\n--- {name} ({result.duration_ms}ms) ---")
        if result.success:
            # Truncate for display
            text = result.text[:300] + "..." if len(result.text) > 300 else result.text
            print(text)
        else:
            print(f"Error: {result.error}")

    print()


# =============================================================================
# Example 5: Error Handling - Missing API Keys
# =============================================================================

def example_error_handling():
    """
    Demonstrate error handling for missing API keys.

    API agents fail gracefully when keys aren't configured.
    Always check result.success before using result.text.
    """
    print("=" * 60)
    print("Example 5: Error handling for API agents")
    print("=" * 60)

    # Check available providers first
    available = get_available_api_providers()
    print(f"Configured providers: {available}")
    print()

    # Demonstrate checking before spawning
    if not available.get("grok"):
        print("Grok not configured - would fail if we tried to spawn.")
        print("To configure: set XAI_API_KEY environment variable")
        print("             or add to PowerSpawn/api_keys.json")
    else:
        print("Grok is configured and ready to use.")

    if not available.get("gemini"):
        print("\nGemini not configured - would fail if we tried to spawn.")
        print("To configure: set GEMINI_API_KEY environment variable")
        print("             or add to PowerSpawn/api_keys.json")
    else:
        print("\nGemini is configured and ready to use.")

    if not available.get("mistral"):
        print("\nMistral not configured - would fail if we tried to spawn.")
        print("To configure: set MISTRAL_API_KEY environment variable")
        print("             or add to PowerSpawn/api_keys.json")
    else:
        print("\nMistral is configured and ready to use.")

    # Example of safe spawning pattern
    print("\n--- Safe spawning pattern ---")
    if available.get("grok"):
        result = spawn_grok("Hello!", task_summary="Test")
        if result.success:
            print(f"Grok responded: {result.text[:100]}...")
        else:
            print(f"Grok error: {result.error}")
    else:
        print("Skipping Grok (not configured)")

    print()


# =============================================================================
# Example 6: Different Models for Each Provider
# =============================================================================

def example_model_selection():
    """
    Demonstrate using different models from each provider.

    Each provider offers multiple models with different capabilities:
    - Larger models: More capable but slower/costlier
    - Smaller models: Faster and cheaper for simple tasks
    - Specialized models: Code-focused variants
    """
    print("=" * 60)
    print("Example 6: Model selection across providers")
    print("=" * 60)

    print("Available models by provider:")
    print(f"\nGrok (X.ai):   {list(GROK_MODELS.keys())}")
    print(f"Gemini:        {list(GEMINI_MODELS.keys())}")
    print(f"Mistral:       {list(MISTRAL_MODELS.keys())}")

    available = get_available_api_providers()

    # Example: Use code-focused models for code tasks
    code_prompt = "Write a Python function to check if a string is a palindrome."

    print("\n--- Code-focused models ---")

    if available.get("grok"):
        result = spawn_grok(
            code_prompt,
            model="grok-code-fast",  # Code-optimized model
            task_summary="Palindrome function",
        )
        if result.success:
            print(f"Grok (grok-code-fast): {result.duration_ms}ms")
            print(result.text[:200] + "...")

    if available.get("mistral"):
        result = spawn_mistral(
            code_prompt,
            model="codestral",  # Mistral's code model
            task_summary="Palindrome function",
        )
        if result.success:
            print(f"\nMistral (codestral): {result.duration_ms}ms")
            print(result.text[:200] + "...")

    # Example: Use fast models for simple queries
    simple_prompt = "What is 2 + 2?"

    print("\n--- Fast models for simple queries ---")

    if available.get("gemini"):
        result = spawn_gemini(
            simple_prompt,
            model="gemini-2.0-flash",  # Fast model
            task_summary="Simple math",
        )
        if result.success:
            print(f"Gemini (flash): {result.text.strip()} ({result.duration_ms}ms)")

    if available.get("mistral"):
        result = spawn_mistral(
            simple_prompt,
            model="mistral-small",  # Smaller, faster model
            task_summary="Simple math",
        )
        if result.success:
            print(f"Mistral (small): {result.text.strip()} ({result.duration_ms}ms)")

    print()


# =============================================================================
# Example 7: System Prompts for Role-Based Agents
# =============================================================================

def example_system_prompts():
    """
    Demonstrate using system prompts to create role-based agents.

    System prompts allow you to:
    - Define agent personality/expertise
    - Set response format requirements
    - Constrain behavior
    """
    print("=" * 60)
    print("Example 7: System prompts for role-based agents")
    print("=" * 60)

    available = get_available_api_providers()

    # Example: Security reviewer agent
    security_system_prompt = """You are a security-focused code reviewer.
Your role is to identify potential security vulnerabilities in code.
Focus on: injection attacks, authentication issues, data exposure, and unsafe operations.
Format your response as a bulleted list of findings with severity levels."""

    code_to_review = '''
def login(username, password):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    result = db.execute(query)
    if result:
        session['user'] = username
        return redirect('/dashboard')
    return "Login failed"
'''

    print("Code to review:")
    print(code_to_review)
    print("\n--- Security Review Agent ---")

    if available.get("grok"):
        result = spawn_grok(
            f"Review this code for security issues:\n{code_to_review}",
            system_prompt=security_system_prompt,
            task_summary="Security code review",
        )
        if result.success:
            print(f"Grok Security Review:\n{result.text}")
    elif available.get("gemini"):
        result = spawn_gemini(
            f"Review this code for security issues:\n{code_to_review}",
            system_prompt=security_system_prompt,
            task_summary="Security code review",
        )
        if result.success:
            print(f"Gemini Security Review:\n{result.text}")
    elif available.get("mistral"):
        result = spawn_mistral(
            f"Review this code for security issues:\n{code_to_review}",
            system_prompt=security_system_prompt,
            task_summary="Security code review",
        )
        if result.success:
            print(f"Mistral Security Review:\n{result.text}")
    else:
        print("No providers configured. Skipping example.")

    print()


# =============================================================================
# Example 8: Mixed Orchestration - CLI + API Agents
# =============================================================================

def example_mixed_orchestration():
    """
    Demonstrate combining CLI agents (can modify files) with API agents (analysis only).

    Workflow pattern:
    1. CLI agent reads/explores codebase
    2. API agents analyze and provide recommendations
    3. CLI agent applies the changes

    This example is conceptual - it shows the pattern without executing.
    """
    print("=" * 60)
    print("Example 8: Mixed orchestration pattern (conceptual)")
    print("=" * 60)

    print("""
MIXED ORCHESTRATION PATTERN
===========================

Step 1: Use CLI agent to gather code
--------------------------------------
from spawner import spawn_claude

result = spawn_claude(
    "Read the authentication module and return its contents",
    model="haiku",
    tools=["Read", "Glob"],
)
code_content = result.text

Step 2: Use API agents for analysis (parallel)
----------------------------------------------
from api_providers import spawn_grok, spawn_gemini, spawn_mistral

# Spawn in parallel for diverse perspectives
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {
        executor.submit(spawn_grok, f"Review this code: {code_content}"): "Grok",
        executor.submit(spawn_gemini, f"Review this code: {code_content}"): "Gemini",
        executor.submit(spawn_mistral, f"Review this code: {code_content}"): "Mistral",
    }
    reviews = {name: future.result() for future, name in futures.items()}

Step 3: Coordinator synthesizes and applies
-------------------------------------------
# Combine insights from all reviews
combined_review = synthesize_reviews(reviews)

# Use CLI agent to apply changes
result = spawn_claude(
    f"Apply these improvements to the auth module: {combined_review}",
    model="sonnet",
    tools=["Read", "Edit"],
)

KEY INSIGHT: API agents provide analysis, CLI agents execute changes.
""")

    print()


# =============================================================================
# Example 9: Universal spawn_api Function
# =============================================================================

def example_universal_spawn():
    """
    Demonstrate the universal spawn_api function for dynamic provider selection.

    Useful when you want to:
    - Select provider at runtime based on configuration
    - Build provider-agnostic orchestration logic
    - Route to fallback providers if primary fails
    """
    print("=" * 60)
    print("Example 9: Universal spawn_api function")
    print("=" * 60)

    available = get_available_api_providers()

    # Find first available provider
    provider = None
    if available.get("grok"):
        provider = "grok"
    elif available.get("gemini"):
        provider = "gemini"
    elif available.get("mistral"):
        provider = "mistral"

    if not provider:
        print("No API providers configured. Skipping example.")
        print()
        return

    print(f"Using first available provider: {provider}")

    # Use universal spawn function
    result = spawn_api(
        "What is the capital of France?",
        provider=provider,
        task_summary="Geography question",
    )

    if result.success:
        print(f"Provider: {result.provider}")
        print(f"Model: {result.model}")
        print(f"Response: {result.text}")
    else:
        print(f"Error: {result.error}")

    # Example: Fallback pattern
    print("\n--- Fallback pattern ---")
    print("""
def query_with_fallback(prompt: str) -> AgentResult:
    providers = ["grok", "gemini", "mistral"]
    available = get_available_api_providers()

    for provider in providers:
        if available.get(provider):
            result = spawn_api(prompt, provider=provider)
            if result.success:
                return result
            print(f"{provider} failed, trying next...")

    return AgentResult(success=False, text="", error="All providers failed")
""")

    print()


# =============================================================================
# Main - Run All Examples
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("API Agent Examples for PowerSpawn")
    print("=" * 60 + "\n")

    # First, check what's available
    available = get_available_api_providers()
    print("API Provider Status:")
    print(f"  Grok (X.ai): {'Configured' if available['grok'] else 'Not configured'}")
    print(f"  Gemini:      {'Configured' if available['gemini'] else 'Not configured'}")
    print(f"  Mistral:     {'Configured' if available['mistral'] else 'Not configured'}")
    print()

    if not any(available.values()):
        print("WARNING: No API providers are configured.")
        print("To configure providers, either:")
        print("  1. Set environment variables (XAI_API_KEY, GEMINI_API_KEY, MISTRAL_API_KEY)")
        print("  2. Create PowerSpawn/api_keys.json with your keys")
        print()
        print("Running examples anyway to show structure...")
        print()

    # Run examples based on what's available
    # Uncomment the examples you want to run

    # example_grok_basic()        # Requires XAI_API_KEY
    # example_gemini_basic()      # Requires GEMINI_API_KEY
    # example_mistral_basic()     # Requires MISTRAL_API_KEY
    # example_parallel_spawning() # Uses all available providers
    example_error_handling()      # Always works (shows status)
    example_model_selection()     # Uses available providers
    # example_system_prompts()    # Uses first available provider
    example_mixed_orchestration() # Conceptual - always works
    example_universal_spawn()     # Uses first available provider

    print("=" * 60)
    print("Examples complete!")
    print("=" * 60)
