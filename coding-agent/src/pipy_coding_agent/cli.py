"""CLI for pipy-coding-agent.

Full-featured CLI matching upstream pi functionality.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .agent import AgentSession, AgentSessionConfig


# =============================================================================
# Argument Parsing
# =============================================================================

def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with full upstream compatibility."""
    parser = argparse.ArgumentParser(
        prog="pipy",
        description="AI coding assistant with read, bash, edit, write tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pipy                              Interactive mode
  pipy -p "explain this code"       Single prompt, exit
  pipy @file.py "explain this"      Include file content in prompt
  pipy -c                           Continue previous session
  pipy -r                           Resume (pick from sessions)
  pipy --model opus                 Use Claude Opus
  pipy --list-models anthropic     List Anthropic models

Model Aliases:
  sonnet  -> claude-sonnet-4
  opus    -> claude-3-opus
  haiku   -> claude-3.5-haiku
  gpt4o   -> gpt-4o
  gemini  -> gemini-2.0-flash
""",
    )

    # Model/Provider options
    model_group = parser.add_argument_group("Model Options")
    model_group.add_argument(
        "--provider",
        help="Provider name (anthropic, openai, google, etc.)",
    )
    model_group.add_argument(
        "-m", "--model",
        default="sonnet",
        help="Model name or alias (default: sonnet)",
    )
    model_group.add_argument(
        "--api-key",
        help="API key (default: from environment)",
    )
    model_group.add_argument(
        "--thinking",
        choices=["off", "minimal", "low", "medium", "high"],
        default="medium",
        help="Thinking level (default: medium)",
    )
    model_group.add_argument(
        "--list-models",
        nargs="?",
        const="",
        metavar="PATTERN",
        help="List available models (optionally filter by pattern)",
    )

    # Session options
    session_group = parser.add_argument_group("Session Options")
    session_group.add_argument(
        "-c", "--continue",
        dest="continue_session",
        action="store_true",
        help="Continue previous session",
    )
    session_group.add_argument(
        "-r", "--resume",
        action="store_true",
        help="Select a session to resume",
    )
    session_group.add_argument(
        "--session",
        metavar="PATH",
        help="Use specific session file",
    )
    session_group.add_argument(
        "--session-dir",
        metavar="DIR",
        help="Directory for session storage",
    )
    session_group.add_argument(
        "--no-session",
        action="store_true",
        help="Don't persist session (ephemeral)",
    )

    # Tool options
    tool_group = parser.add_argument_group("Tool Options")
    tool_group.add_argument(
        "--tools",
        metavar="LIST",
        help="Comma-separated list of tools to enable",
    )
    tool_group.add_argument(
        "--no-tools",
        action="store_true",
        help="Disable all tools",
    )

    # Prompt options
    prompt_group = parser.add_argument_group("Prompt Options")
    prompt_group.add_argument(
        "-p", "--print",
        dest="print_mode",
        action="store_true",
        help="Non-interactive mode: process prompt and exit",
    )
    prompt_group.add_argument(
        "--system-prompt",
        metavar="TEXT",
        help="Custom system prompt",
    )
    prompt_group.add_argument(
        "--append-system-prompt",
        metavar="TEXT",
        help="Append to system prompt",
    )

    # Resource options
    resource_group = parser.add_argument_group("Resource Options")
    resource_group.add_argument(
        "-e", "--extension",
        action="append",
        dest="extensions",
        metavar="PATH",
        help="Load extension (can be repeated)",
    )
    resource_group.add_argument(
        "--skill",
        action="append",
        dest="skills",
        metavar="PATH",
        help="Load skill file (can be repeated)",
    )
    resource_group.add_argument(
        "--prompt-template",
        action="append",
        dest="prompt_templates",
        metavar="PATH",
        help="Load prompt template (can be repeated)",
    )
    resource_group.add_argument(
        "--theme",
        metavar="NAME",
        help="UI theme name",
    )
    resource_group.add_argument(
        "--no-extensions",
        action="store_true",
        help="Disable extensions",
    )
    resource_group.add_argument(
        "--no-skills",
        action="store_true",
        help="Disable skills",
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--mode",
        choices=["text", "json", "rpc"],
        default="text",
        help="Output mode (default: text)",
    )
    output_group.add_argument(
        "--export",
        metavar="PATH",
        help="Export session to HTML file",
    )
    output_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    # Other
    parser.add_argument(
        "--cwd",
        metavar="DIR",
        help="Working directory",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit",
    )

    # Positional: messages and @file args
    parser.add_argument(
        "args",
        nargs="*",
        help="Messages and @file arguments",
    )

    return parser


def parse_message_args(args: list[str]) -> tuple[list[str], list[Path]]:
    """
    Parse positional arguments into messages and file paths.
    
    @file.txt -> read file content
    other -> message text
    """
    messages: list[str] = []
    files: list[Path] = []
    
    for arg in args:
        if arg.startswith("@"):
            file_path = Path(arg[1:])
            if file_path.exists():
                files.append(file_path)
            else:
                print(f"Warning: File not found: {file_path}", file=sys.stderr)
        else:
            messages.append(arg)
    
    return messages, files


def read_file_contents(files: list[Path]) -> str:
    """Read and format file contents for prompt."""
    if not files:
        return ""
    
    parts = []
    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8")
            parts.append(f"# Content of {file_path}\n\n```\n{content}\n```")
        except Exception as e:
            parts.append(f"# Error reading {file_path}: {e}")
    
    return "\n\n".join(parts)


# =============================================================================
# Version & Info
# =============================================================================

def print_version() -> None:
    """Print version information."""
    from . import __version__
    print(f"pipy-coding-agent v{__version__}")


def list_models(pattern: str = "") -> None:
    """List available models."""
    from pipy_ai import get_available_models
    
    try:
        models = get_available_models()
        
        if pattern:
            pattern_lower = pattern.lower()
            models = [m for m in models if pattern_lower in m.lower()]
        
        if not models:
            print("No models found" + (f" matching '{pattern}'" if pattern else ""))
            return
        
        print(f"Available models{f' matching {pattern!r}' if pattern else ''}:\n")
        for model in sorted(models):
            print(f"  {model}")
    except Exception as e:
        print(f"Error listing models: {e}", file=sys.stderr)


# =============================================================================
# Slash Commands
# =============================================================================

SLASH_COMMANDS = {}

def slash_command(name: str, description: str):
    """Decorator to register a slash command."""
    def decorator(func):
        SLASH_COMMANDS[name] = {"func": func, "description": description}
        return func
    return decorator


@slash_command("help", "Show available commands")
def cmd_help(session: AgentSession, args: str) -> bool:
    """Show help."""
    print("\nCommands:")
    for name, info in sorted(SLASH_COMMANDS.items()):
        print(f"  /{name:15} {info['description']}")
    print("\nModel Aliases:")
    print("  sonnet  -> claude-sonnet-4")
    print("  opus    -> claude-3-opus")
    print("  haiku   -> claude-3.5-haiku")
    print("  gpt4o   -> gpt-4o")
    print("  gemini  -> gemini-2.0-flash")
    print()
    return True


@slash_command("model", "Change model (e.g., /model opus)")
def cmd_model(session: AgentSession, args: str) -> bool:
    """Change model."""
    if not args:
        print(f"Current model: {session.model.model_id}")
        return True
    session.set_model(args)
    print(f"Model changed to: {session.model.model_id}")
    return True


@slash_command("thinking", "Set thinking level (off, low, medium, high)")
def cmd_thinking(session: AgentSession, args: str) -> bool:
    """Set thinking level."""
    if not args:
        print(f"Current thinking level: {session.thinking_level}")
        return True
    session.set_thinking_level(args)
    print(f"Thinking level: {args}")
    return True


@slash_command("clear", "Clear conversation and start fresh")
def cmd_clear(session: AgentSession, args: str) -> bool:
    """Clear conversation."""
    session.clear()
    print("Conversation cleared. Starting fresh.")
    return True


@slash_command("new", "Start a new session")
def cmd_new(session: AgentSession, args: str) -> bool:
    """Start new session."""
    session.clear()
    print("New session started.")
    return True


@slash_command("session", "Show session info")
def cmd_session(session: AgentSession, args: str) -> bool:
    """Show session info."""
    print(f"\nSession Info:")
    print(f"  Model: {session.model.model_id}")
    print(f"  Thinking: {session.thinking_level}")
    print(f"  CWD: {session.cwd}")
    print(f"  Messages: {len(session.get_messages())}")
    if session._session and session._session.session_file:
        print(f"  File: {session._session.session_file}")
    print()
    return True


@slash_command("compact", "Manually compact session context")
def cmd_compact(session: AgentSession, args: str) -> bool:
    """Trigger compaction."""
    print("Compaction not yet implemented in CLI.")
    # TODO: Implement manual compaction
    return True


@slash_command("export", "Export session to HTML")
def cmd_export(session: AgentSession, args: str) -> bool:
    """Export session."""
    if not args:
        args = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    
    html = session.export_html()
    Path(args).write_text(html, encoding="utf-8")
    print(f"Session exported to: {args}")
    return True


@slash_command("copy", "Copy last response to clipboard")
def cmd_copy(session: AgentSession, args: str) -> bool:
    """Copy last response."""
    messages = session.get_messages()
    if not messages:
        print("No messages to copy.")
        return True
    
    # Find last assistant message
    for msg in reversed(messages):
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
        if role == "assistant":
            content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", [])
            text = ""
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    break
                elif hasattr(block, "type") and block.type == "text":
                    text = block.text
                    break
            
            if text:
                try:
                    import subprocess
                    # Try different clipboard commands
                    for cmd in [["pbcopy"], ["xclip", "-selection", "clipboard"], ["clip"]]:
                        try:
                            subprocess.run(cmd, input=text.encode(), check=True)
                            print("Copied to clipboard.")
                            return True
                        except (FileNotFoundError, subprocess.CalledProcessError):
                            continue
                    print("Clipboard not available.")
                except Exception as e:
                    print(f"Failed to copy: {e}")
            return True
    
    print("No assistant message found.")
    return True


@slash_command("reload", "Reload extensions, skills, and prompts")
def cmd_reload(session: AgentSession, args: str) -> bool:
    """Reload resources."""
    session._resources = type(session._resources)(cwd=session._cwd)
    session._system_prompt = session._build_system_prompt()
    print("Resources reloaded.")
    return True


@slash_command("fork", "Fork from current point (creates new branch)")
def cmd_fork(session: AgentSession, args: str) -> bool:
    """Fork session."""
    print("Fork not yet implemented in CLI.")
    # TODO: Implement fork
    return True


@slash_command("tree", "Navigate session tree")  
def cmd_tree(session: AgentSession, args: str) -> bool:
    """Show session tree."""
    print("Tree navigation not yet implemented in CLI.")
    # TODO: Implement tree view
    return True


@slash_command("resume", "Resume a different session")
def cmd_resume(session: AgentSession, args: str) -> bool:
    """Resume session."""
    print("Resume not yet implemented in CLI (use --resume flag).")
    return True


@slash_command("login", "Login with API key or OAuth")
def cmd_login(session: AgentSession, args: str) -> bool:
    """Handle login — OAuth or API key."""
    import asyncio
    from pipy_ai.oauth import get_oauth_providers
    from .auth_storage import AuthStorage

    auth = AuthStorage()
    providers = get_oauth_providers()

    # If a specific provider was given, use it
    target = args.strip().lower() if args.strip() else None

    if target == "api-key" or target == "apikey":
        # Direct API key entry
        provider_name = input("Provider (e.g., anthropic, openai, google): ").strip()
        if not provider_name:
            print("Cancelled.")
            return True
        api_key = input(f"API key for {provider_name}: ").strip()
        if not api_key:
            print("Cancelled.")
            return True
        auth.set_api_key(provider_name, api_key)
        print(f"✓ API key saved for {provider_name}")
        return True

    # Show provider menu
    print("\nAvailable login methods:\n")
    print("  api-key          Enter an API key directly")
    for p in providers:
        marker = " ✓" if auth.get(p.id) else ""
        print(f"  {p.id:<20} {p.name}{marker}")
    print()

    if not target:
        target = input("Choose provider (or 'api-key'): ").strip().lower()

    if not target:
        print("Cancelled.")
        return True

    if target in ("api-key", "apikey"):
        provider_name = input("Provider (e.g., anthropic, openai, google): ").strip()
        if not provider_name:
            print("Cancelled.")
            return True
        api_key = input(f"API key for {provider_name}: ").strip()
        if not api_key:
            print("Cancelled.")
            return True
        auth.set_api_key(provider_name, api_key)
        print(f"✓ API key saved for {provider_name}")
        return True

    # Find OAuth provider
    provider = next((p for p in providers if p.id == target), None)
    if not provider:
        print(f"Unknown provider: {target}")
        return True

    # Run OAuth flow
    import webbrowser

    def on_auth(info):
        print(f"\nOpening browser: {info.url}")
        if info.instructions:
            print(f"  {info.instructions}")
        try:
            webbrowser.open(info.url)
        except Exception:
            print("  (Could not open browser — please open the URL manually)")

    async def on_prompt(prompt):
        return input(f"{prompt.message} ").strip()

    def on_progress(msg):
        print(f"  {msg}")

    try:
        credentials = asyncio.run(provider.login(
            on_auth=on_auth,
            on_prompt=on_prompt,
            on_progress=on_progress,
        ))
        auth.set_oauth(provider.id, credentials)
        print(f"\n✓ Logged in to {provider.name}")
    except KeyboardInterrupt:
        print("\nCancelled.")
    except Exception as e:
        print(f"\n✗ Login failed: {e}")

    return True


@slash_command("logout", "Logout (clear cached credentials)")
def cmd_logout(session: AgentSession, args: str) -> bool:
    """Handle logout — remove stored credentials."""
    from .auth_storage import AuthStorage

    auth = AuthStorage()
    stored = auth.get_providers_with_credentials()

    if not stored:
        print("No stored credentials.")
        return True

    target = args.strip().lower() if args.strip() else None

    if not target:
        print("\nStored credentials:")
        for p in stored:
            cred = auth.get(p)
            ctype = cred.get("type", "unknown") if cred else "unknown"
            print(f"  {p:<20} ({ctype})")
        print()
        target = input("Provider to logout (or 'all'): ").strip().lower()

    if not target:
        print("Cancelled.")
        return True

    if target == "all":
        for p in stored:
            auth.remove(p)
        print(f"✓ Removed credentials for {len(stored)} provider(s)")
    elif target in stored:
        auth.remove(target)
        print(f"✓ Removed credentials for {target}")
    else:
        print(f"No credentials found for: {target}")

    return True


@slash_command("quit", "Exit the agent")
def cmd_quit(session: AgentSession, args: str) -> bool:
    """Exit."""
    return False  # Signal to exit


@slash_command("exit", "Exit the agent")
def cmd_exit(session: AgentSession, args: str) -> bool:
    """Exit."""
    return False


def handle_slash_command(session: AgentSession, input_text: str) -> bool | None:
    """
    Handle a slash command.
    
    Returns:
        True - command handled, continue
        False - exit requested
        None - not a command
    """
    if not input_text.startswith("/"):
        return None
    
    parts = input_text[1:].split(maxsplit=1)
    cmd_name = parts[0].lower()
    cmd_args = parts[1] if len(parts) > 1 else ""
    
    if cmd_name in SLASH_COMMANDS:
        return SLASH_COMMANDS[cmd_name]["func"](session, cmd_args)
    
    print(f"Unknown command: /{cmd_name}. Type /help for available commands.")
    return True


# =============================================================================
# Interactive Mode
# =============================================================================

async def run_interactive_async(session: AgentSession, verbose: bool = False) -> None:
    """Run interactive mode."""
    from . import __version__
    
    print(f"pipy-coding-agent v{__version__}")
    print(f"Model: {session.model.model_id} | Thinking: {session.thinking_level}")
    print(f"CWD: {session.cwd}")
    print("Type /help for commands, /quit to exit")
    print()

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        # Handle slash commands
        cmd_result = handle_slash_command(session, user_input)
        if cmd_result is False:
            print("Goodbye!")
            break
        if cmd_result is True:
            continue

        # Regular prompt
        try:
            if verbose:
                print(f"[Sending to {session.model.model_id}...]")
            
            result = await session.aprompt(user_input)
            
            print()
            if result.response:
                print(result.response)
            else:
                print("[No response]")
            print()
            
            if verbose and result.tool_calls > 0:
                print(f"[{result.tool_calls} tool call(s)]")
                
        except Exception as e:
            print(f"Error: {e}")
            if verbose:
                import traceback
                traceback.print_exc()


def run_interactive(session: AgentSession, verbose: bool = False) -> None:
    """Run interactive mode (sync wrapper)."""
    asyncio.run(run_interactive_async(session, verbose))


# =============================================================================
# Print Mode (Non-Interactive)
# =============================================================================

async def run_print_mode_async(
    session: AgentSession,
    prompt: str,
    verbose: bool = False,
) -> int:
    """Run single prompt and exit."""
    try:
        if verbose:
            print(f"Model: {session.model.model_id}", file=sys.stderr)
            print(f"Thinking: {session.thinking_level}", file=sys.stderr)
            print(f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}", file=sys.stderr)
            print(file=sys.stderr)

        result = await session.aprompt(prompt)
        
        if result.response:
            print(result.response)
        
        if verbose:
            print(file=sys.stderr)
            print(f"Tool calls: {result.tool_calls}", file=sys.stderr)
            print(f"Tokens: {result.tokens_used}", file=sys.stderr)

        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def run_print_mode(session: AgentSession, prompt: str, verbose: bool = False) -> int:
    """Run single prompt and exit (sync wrapper)."""
    return asyncio.run(run_print_mode_async(session, prompt, verbose))


# =============================================================================
# Session Selection
# =============================================================================

def select_session_interactive(session_dir: Path) -> Path | None:
    """Interactive session selection."""
    from .session import list_sessions
    
    sessions = list_sessions(session_dir)
    if not sessions:
        print("No sessions found.")
        return None
    
    print("\nAvailable sessions:")
    for i, info in enumerate(sessions[:20], 1):
        name = info.name or info.first_message[:40] or "Unnamed"
        modified = info.modified.strftime("%Y-%m-%d %H:%M")
        print(f"  {i:2}. [{modified}] {name}")
    
    if len(sessions) > 20:
        print(f"  ... and {len(sessions) - 20} more")
    
    print()
    try:
        choice = input("Enter number (or Enter for most recent): ").strip()
        if not choice:
            return Path(sessions[0].path)
        
        idx = int(choice) - 1
        if 0 <= idx < len(sessions):
            return Path(sessions[idx].path)
        print("Invalid selection.")
        return None
    except (ValueError, KeyboardInterrupt):
        return None


# =============================================================================
# Main Entry Point
# =============================================================================

def main(args: list[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    parsed = parser.parse_args(args)

    # Version
    if parsed.version:
        print_version()
        return 0

    # List models
    if parsed.list_models is not None:
        list_models(parsed.list_models)
        return 0

    # Export existing session
    if parsed.export and parsed.session:
        print("Export not yet implemented.")
        return 1

    # Parse @file and message args
    messages, files = parse_message_args(parsed.args or [])
    file_content = read_file_contents(files)

    # Build prompt from args
    prompt_parts = []
    if file_content:
        prompt_parts.append(file_content)
    if messages:
        prompt_parts.append(" ".join(messages))
    initial_prompt = "\n\n".join(prompt_parts) if prompt_parts else None

    # Determine working directory
    cwd = Path(parsed.cwd) if parsed.cwd else Path.cwd()

    # Handle session selection
    session_file: Path | None = None
    if parsed.session:
        session_file = Path(parsed.session)
    elif parsed.resume:
        from .session import get_default_session_dir
        session_dir = Path(parsed.session_dir) if parsed.session_dir else get_default_session_dir(str(cwd))
        session_file = select_session_interactive(session_dir)
        if not session_file:
            return 1
    elif parsed.continue_session:
        from .session import get_default_session_dir, find_most_recent_session
        session_dir = Path(parsed.session_dir) if parsed.session_dir else get_default_session_dir(str(cwd))
        recent = find_most_recent_session(session_dir)
        if recent:
            session_file = Path(recent)
        else:
            print("No previous session found.", file=sys.stderr)

    # Build system prompt
    system_prompt = parsed.system_prompt
    if parsed.append_system_prompt:
        append_text = parsed.append_system_prompt
        # Check if it's a file
        append_path = Path(append_text)
        if append_path.exists():
            append_text = append_path.read_text(encoding="utf-8")
        system_prompt = (system_prompt or "") + "\n\n" + append_text

    # Determine tools
    tools = None
    if parsed.no_tools:
        tools = []
    elif parsed.tools:
        # TODO: Filter tools by name
        pass

    # Create session config
    config = AgentSessionConfig(
        model=parsed.model,
        thinking_level=parsed.thinking,
        cwd=str(cwd),
        system_prompt=system_prompt,
        persist_session=not parsed.no_session,
        tools=tools,
    )

    # Set API key if provided
    if parsed.api_key:
        # Determine provider from model
        provider = parsed.provider or "anthropic"
        env_var = f"{provider.upper()}_API_KEY"
        os.environ[env_var] = parsed.api_key

    # Create session
    try:
        session = AgentSession(config)
        
        # Load specific session file if requested
        if session_file and session._session:
            session._session.set_session_file(session_file)
            
    except Exception as e:
        print(f"Failed to create session: {e}", file=sys.stderr)
        if parsed.verbose:
            import traceback
            traceback.print_exc()
        return 1

    # Run mode
    if parsed.print_mode or initial_prompt:
        prompt = initial_prompt or ""
        if not prompt:
            # Read from stdin if piped
            try:
                if not sys.stdin.isatty():
                    prompt = sys.stdin.read().strip()
            except Exception:
                pass
        
        if not prompt:
            print("Error: No prompt provided for print mode.", file=sys.stderr)
            print("Usage: pipy -p 'your prompt' or echo 'prompt' | pipy -p", file=sys.stderr)
            return 1
            
        return run_print_mode(session, prompt, parsed.verbose)
    else:
        run_interactive(session, parsed.verbose)
        return 0


if __name__ == "__main__":
    sys.exit(main())
