"""pipy-coding-agent: AI coding assistant."""

__version__ = "0.51.6"

from pipy_coding_agent.tools import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    bash_tool,
    coding_tools,
    create_bash_tool,
    create_coding_tools,
    create_edit_tool,
    create_find_tool,
    create_grep_tool,
    create_ls_tool,
    create_read_only_tools,
    create_read_tool,
    create_write_tool,
    edit_tool,
    find_tool,
    grep_tool,
    ls_tool,
    read_only_tools,
    read_tool,
    write_tool,
)

from pipy_coding_agent.session import (
    SessionManager,
    SessionContext,
    SessionInfo,
    build_session_context,
)

from pipy_coding_agent.settings import (
    Settings,
    SettingsManager,
    CompactionSettings,
    RetrySettings,
)

from pipy_coding_agent.resources import (
    DefaultResourceLoader,
    Skill,
    PromptTemplate,
    ContextFile,
    load_skills,
    load_prompts,
    expand_prompt_template,
)

from pipy_coding_agent.compaction import (
    estimate_tokens,
    estimate_context_tokens,
    should_compact,
    prepare_compaction,
    compact,
    CompactionResult,
    CompactionPreparation,
)

from pipy_coding_agent.prompt import (
    build_system_prompt,
    BuildSystemPromptOptions,
)

from pipy_coding_agent.agent import (
    AgentSession,
    AgentSessionConfig,
    PromptOptions,
    PromptResult,
    ModelResolver,
    resolve_model,
)

from pipy_coding_agent.extensions import (
    Extension,
    ExtensionManifest,
    ExtensionLoader,
    ExtensionHooks,
    HookType,
)

from pipy_coding_agent.slash_commands import (
    BUILTIN_SLASH_COMMANDS,
    BuiltinSlashCommand,
    SlashCommandInfo,
    SlashCommandLocation,
    SlashCommandSource,
)

from pipy_coding_agent.settings.resolve_config_value import (
    resolve_config_value,
    resolve_headers,
    clear_config_value_cache,
)

from pipy_coding_agent.auth_storage import (
    AuthStorage,
)

__all__ = [
    # Tools
    "read_tool",
    "bash_tool",
    "edit_tool",
    "write_tool",
    "grep_tool",
    "find_tool",
    "ls_tool",
    # Tool collections
    "coding_tools",
    "read_only_tools",
    # Tool factories
    "create_read_tool",
    "create_bash_tool",
    "create_edit_tool",
    "create_write_tool",
    "create_grep_tool",
    "create_find_tool",
    "create_ls_tool",
    "create_coding_tools",
    "create_read_only_tools",
    # Constants
    "DEFAULT_MAX_LINES",
    "DEFAULT_MAX_BYTES",
    # Session management
    "SessionManager",
    "SessionContext",
    "SessionInfo",
    "build_session_context",
    # Settings
    "Settings",
    "SettingsManager",
    "CompactionSettings",
    "RetrySettings",
    # Resources
    "DefaultResourceLoader",
    "Skill",
    "PromptTemplate",
    "ContextFile",
    "load_skills",
    "load_prompts",
    "expand_prompt_template",
    # Compaction
    "estimate_tokens",
    "estimate_context_tokens",
    "should_compact",
    "prepare_compaction",
    "compact",
    "CompactionResult",
    "CompactionPreparation",
    # System Prompt
    "build_system_prompt",
    "BuildSystemPromptOptions",
    # Agent
    "AgentSession",
    "AgentSessionConfig",
    "PromptOptions",
    "PromptResult",
    "ModelResolver",
    "resolve_model",
    # Extensions
    "Extension",
    "ExtensionManifest",
    "ExtensionLoader",
    "ExtensionHooks",
    "HookType",
    # Slash Commands
    "BUILTIN_SLASH_COMMANDS",
    "BuiltinSlashCommand",
    "SlashCommandInfo",
    "SlashCommandLocation",
    "SlashCommandSource",
    # Config Value Resolution
    "resolve_config_value",
    "resolve_headers",
    "clear_config_value_cache",
    # Auth
    "AuthStorage",
]
