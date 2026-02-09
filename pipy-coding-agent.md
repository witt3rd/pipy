# pipy-coding-agent: AI Coding Assistant Spec

**Goal**: Port pi-mono/packages/coding-agent to Python, building on pipy-ai, pipy-agent, and pipy-tui.

---

## Scale Assessment

### pi-mono/coding-agent Stats

```
Files:        109 TypeScript files
Total lines:  ~14,370 lines (core logic)
              + 4,308 lines (interactive-mode.ts)
              + 12,815 lines (components + theme)
              ≈ 31,500 lines total
```

### Major Subsystems

| Subsystem | Lines | Files | Description |
|-----------|-------|-------|-------------|
| **AgentSession** | 2,697 | 1 | Core session lifecycle, events, compaction |
| **SessionManager** | 1,394 | 1 | Session persistence, tree structure, entries |
| **PackageManager** | 1,596 | 1 | Extension/skill/theme package management |
| **ResourceLoader** | 871 | 1 | Skills, prompts, themes, context files |
| **InteractiveMode** | 4,308 | 1 | TUI rendering, user interaction |
| **SettingsManager** | 710 | 1 | User settings, defaults |
| **ModelRegistry** | 594 | 1 | Model discovery, API key management |
| **Tools** | ~1,500 | 8 | read, bash, edit, write, grep, find, ls |
| **Extensions** | ~1,000 | 5 | Extension loader, runner, types |
| **Compaction** | ~800 | 4 | Context window management |
| **Components** | ~4,000 | 20+ | UI components for interactive mode |
| **CLI** | ~800 | 5 | Argument parsing, selectors |
| **Theme** | 1,100 | 1 | Color themes, syntax highlighting |
| **RPC Mode** | ~500 | 3 | JSON-RPC server mode |
| **Print Mode** | ~120 | 1 | Non-interactive output mode |
| **Utilities** | ~1,000 | 10+ | Shell, clipboard, frontmatter, etc. |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLI / main.ts                               │
│  • Argument parsing                                                      │
│  • Mode selection (interactive / print / rpc)                           │
│  • Session picker                                                        │
└───────────────────────────────────────┬─────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
              ┌─────▼─────┐       ┌─────▼─────┐       ┌─────▼─────┐
              │Interactive│       │   Print   │       │    RPC    │
              │   Mode    │       │   Mode    │       │   Mode    │
              └─────┬─────┘       └─────┬─────┘       └─────┬─────┘
                    │                   │                   │
                    └───────────────────┼───────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────┐
│                           AgentSession                                   │
│  • Agent lifecycle (prompt, abort, retry)                               │
│  • Event subscription                                                    │
│  • Model/thinking level management                                       │
│  • Compaction (manual + auto)                                           │
│  • Session switching/branching                                          │
│  • Extension runner coordination                                         │
└───────────────────────────────────────┬─────────────────────────────────┘
                                        │
        ┌───────────────┬───────────────┼───────────────┬─────────────────┐
        │               │               │               │                 │
┌───────▼───────┐┌──────▼──────┐┌───────▼───────┐┌──────▼──────┐┌─────────▼─────────┐
│SessionManager ││SettingsMan. ││ResourceLoader ││ModelRegistry││  ExtensionRunner  │
│• Persistence  ││• User prefs ││• Skills       ││• API keys   ││• Tool wrapping    │
│• Tree struct  ││• Defaults   ││• Prompts      ││• Model list ││• Event dispatch   │
│• Entries      ││• Packages   ││• Themes       ││• OAuth      ││• Command registry │
└───────────────┘└─────────────┘└───────────────┘└─────────────┘└───────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
              ┌─────▼─────┐       ┌─────▼─────┐       ┌─────▼─────┐
              │   Tools   │       │   Agent   │       │ Compaction│
              │read,bash, │       │(pipy-agent│       │ Summarize │
              │edit,write │       │  core)    │       │ & prune   │
              └───────────┘       └───────────┘       └───────────┘
```

---

## Dependency Map

### What We Already Have

| pipy package | Provides | Maps to pi-mono |
|--------------|----------|-----------------|
| **pipy-ai** | LLM streaming, types, models.dev | @mariozechner/pi-ai |
| **pipy-agent** | Agent loop, tool execution | @mariozechner/pi-agent-core |
| **pipy-tui** | Editor, autocomplete, fuzzy | @mariozechner/pi-tui |

### What We Need to Build

| Component | Depends On | Complexity |
|-----------|------------|------------|
| **Tools** (read, bash, edit, write) | pipy-agent | Medium |
| **SessionManager** | filesystem | Medium |
| **SettingsManager** | filesystem | Low |
| **ResourceLoader** | filesystem | Medium |
| **ModelRegistry** | pipy-ai | Low (uses pipy-ai registry) |
| **Compaction** | pipy-ai | Medium |
| **AgentSession** | All above | High |
| **InteractiveMode** | pipy-tui, AgentSession | High |
| **CLI** | Click/Typer | Low |
| **Extensions** | AgentSession | High (defer?) |

---

## Phased Implementation Plan

### Phase 1: Core Tools (Week 1)

Build the coding tools as pipy-agent tools:

```python
# pipy_coding_agent/tools/read.py
@tool(name="Read", description="Read file contents", parameters={...})
async def read_tool(tool_call_id, params, signal, on_update):
    path = params["path"]
    # Handle text files, images, truncation, line limits
    ...
    return AgentToolResult(content=[TextContent(text=content)])
```

**Tools to implement:**
- [ ] `read` - Read files (text + images, with truncation)
- [ ] `bash` - Execute shell commands (with timeout, working dir)
- [ ] `edit` - Edit files (oldText → newText replacement)
- [ ] `write` - Write/create files
- [ ] `grep` - Search file contents (ripgrep-style)
- [ ] `find` - Find files by pattern
- [ ] `ls` - List directory contents

**Deliverable:** Working tools that can be used with pipy-agent.

### Phase 2: Session Management (Week 1-2)

```python
# pipy_coding_agent/session/manager.py
class SessionManager:
    """Manages session persistence and tree structure."""
    
    def __init__(self, sessions_dir: Path, cwd: Path):
        ...
    
    # Session lifecycle
    def create_session(self) -> str: ...
    def load_session(self, session_id: str) -> SessionContext: ...
    def get_sessions(self) -> list[SessionInfo]: ...
    
    # Entry management (append-only log)
    def append_message(self, message: AgentMessage) -> None: ...
    def append_model_change(self, provider: str, model_id: str) -> None: ...
    def append_compaction(self, result: CompactionResult) -> None: ...
    
    # Tree operations
    def fork(self, from_entry_id: str) -> str: ...
    def switch_branch(self, session_id: str) -> None: ...
    def get_tree(self) -> SessionTree: ...
```

**Entry types:**
- `message` - User/assistant messages
- `model_change` - Model switches
- `thinking_level_change` - Thinking level changes
- `compaction` - Compaction summaries
- `branch_summary` - Fork point summaries
- `custom` - Extension data
- `custom_message` - Extension messages in context

**Deliverable:** Session persistence that survives restarts.

### Phase 3: Settings & Resources (Week 2)

```python
# pipy_coding_agent/settings.py
class SettingsManager:
    """User settings with project/global hierarchy."""
    
    def get_default_model(self) -> str | None: ...
    def get_default_thinking_level(self) -> ThinkingLevel: ...
    def get_compaction_settings(self) -> CompactionSettings: ...
    def get_retry_settings(self) -> RetrySettings: ...

# pipy_coding_agent/resources/loader.py
class ResourceLoader:
    """Loads skills, prompts, themes from filesystem."""
    
    def load_skills(self) -> list[Skill]: ...
    def load_prompt_templates(self) -> dict[str, PromptTemplate]: ...
    def get_system_prompt(self) -> str: ...
```

**Skills** are markdown files with frontmatter:
```markdown
---
name: git-commit
description: Commit changes with good messages
---

When committing changes:
1. Write clear, descriptive commit messages
2. Use conventional commits format
...
```

**Deliverable:** Configuration and skill loading.

### Phase 4: Compaction (Week 2-3)

```python
# pipy_coding_agent/compaction/compaction.py
async def compact(
    messages: list[AgentMessage],
    entries: list[SessionEntry],
    model: str,
    settings: CompactionSettings,
    get_api_key: Callable,
) -> CompactionResult:
    """Summarize old messages to fit context window."""
    
    # Find cut point (where to summarize from)
    cut_point = find_cut_point(entries, settings)
    
    # Serialize conversation for summarization
    conversation = serialize_conversation(messages[:cut_point])
    
    # Generate summary via LLM
    summary = await generate_summary(conversation, model, get_api_key)
    
    return CompactionResult(
        summary=summary,
        first_kept_entry_id=entries[cut_point].id,
        tokens_before=calculate_tokens(messages),
    )
```

**Key concepts:**
- Auto-compaction when context threshold hit
- Manual compaction via command
- File operation tracking (read/modified files)
- Turn-aware cut points

**Deliverable:** Sessions that don't overflow context.

### Phase 5: AgentSession (Week 3)

```python
# pipy_coding_agent/session/agent_session.py
class AgentSession:
    """Core session orchestration."""
    
    def __init__(
        self,
        agent: Agent,
        session_manager: SessionManager,
        settings_manager: SettingsManager,
        resource_loader: ResourceLoader,
        model_registry: ModelRegistry,
        tools: list[AgentTool],
        cwd: Path,
    ):
        ...
    
    # Main interaction
    async def prompt(self, text: str, images: list[ImageContent] = None) -> None: ...
    def abort(self) -> None: ...
    
    # Events
    def subscribe(self, listener: AgentSessionEventListener) -> Callable: ...
    
    # Model management
    def set_model(self, model: str) -> None: ...
    def cycle_model(self) -> ModelCycleResult: ...
    
    # Session operations
    async def compact(self, manual: bool = False) -> CompactionResult: ...
    def fork(self, from_entry_id: str) -> str: ...
    def switch_session(self, session_id: str) -> None: ...
```

**Events:**
- `agent_start`, `agent_end`
- `turn_start`, `turn_end`
- `message_start`, `message_update`, `message_end`
- `tool_execution_start`, `tool_execution_end`
- `auto_compaction_start`, `auto_compaction_end`
- `auto_retry_start`, `auto_retry_end`

**Deliverable:** Full agent lifecycle management.

### Phase 6: Interactive Mode (Week 3-4)

```python
# pipy_coding_agent/modes/interactive.py
class InteractiveMode:
    """TUI mode using pipy-tui."""
    
    def __init__(self, session: AgentSession):
        self.session = session
        self.app = CodingAgentApp(session)
    
    async def run(self) -> None:
        await self.app.run_async()

# Using Textual + pipy-tui
class CodingAgentApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield MessageList(id="messages")
        yield PiEditor(
            autocomplete=CombinedProvider([
                SlashCommandProvider(self.get_commands()),
                FilePathProvider(self.cwd),
            ]),
        )
        yield Footer()
    
    def get_commands(self) -> list[SlashCommand]:
        return [
            SlashCommand("help", "Show help"),
            SlashCommand("model", "Change model"),
            SlashCommand("clear", "Clear chat"),
            SlashCommand("compact", "Compact context"),
            SlashCommand("sessions", "Switch session"),
            SlashCommand("fork", "Fork session"),
            SlashCommand("tree", "Show session tree"),
            ...
        ]
```

**Slash commands:**
- `/help` - Show help
- `/model` - Change model
- `/thinking` - Change thinking level
- `/clear` - Clear chat
- `/compact` - Manual compaction
- `/sessions` - Session picker
- `/fork` - Fork from entry
- `/tree` - Session tree view
- `/settings` - Settings editor
- `/login` - Provider authentication
- `/export` - Export to HTML

**Deliverable:** Full interactive TUI.

### Phase 7: CLI & Modes (Week 4)

```python
# pipy_coding_agent/cli.py
@click.group()
def cli():
    """pipy-coding-agent - AI coding assistant"""
    pass

@cli.command()
@click.option("--model", "-m", help="Model to use")
@click.option("--prompt", "-p", help="Initial prompt")
@click.option("--continue", "-c", is_flag=True, help="Continue last session")
@click.option("--print", is_flag=True, help="Print mode (non-interactive)")
@click.option("--rpc", is_flag=True, help="RPC server mode")
def run(model, prompt, continue_, print_, rpc):
    """Run the coding agent."""
    ...
```

**Modes:**
- `interactive` - Full TUI (default)
- `print` - Non-interactive, stream to stdout
- `rpc` - JSON-RPC server for IDE integration

**Deliverable:** Complete CLI with all modes.

### Phase 8: Extensions (Future)

The extension system is complex. Defer to v0.2.0:

```python
# Future: pipy_coding_agent/extensions/
class Extension(Protocol):
    def on_load(self, ctx: ExtensionContext) -> None: ...
    def on_agent_start(self, event: AgentStartEvent) -> None: ...
    def on_tool_call(self, event: ToolCallEvent) -> ToolCallResult | None: ...
    ...
```

---

## Package Structure

```
~/src/witt3rd/pipy/coding-agent/
├── pyproject.toml
├── README.md
├── DESIGN.md
├── src/pipy_coding_agent/
│   ├── __init__.py
│   ├── cli.py                    # CLI entry point
│   ├── config.py                 # Paths, version, constants
│   │
│   ├── tools/                    # Coding tools
│   │   ├── __init__.py
│   │   ├── read.py
│   │   ├── bash.py
│   │   ├── edit.py
│   │   ├── write.py
│   │   ├── grep.py
│   │   ├── find.py
│   │   ├── ls.py
│   │   └── truncate.py
│   │
│   ├── session/                  # Session management
│   │   ├── __init__.py
│   │   ├── manager.py            # SessionManager
│   │   ├── entries.py            # Entry types
│   │   └── context.py            # SessionContext builder
│   │
│   ├── compaction/               # Context compaction
│   │   ├── __init__.py
│   │   ├── compaction.py
│   │   └── summarization.py
│   │
│   ├── resources/                # Resource loading
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   ├── skills.py
│   │   └── prompts.py
│   │
│   ├── settings/                 # Settings management
│   │   ├── __init__.py
│   │   └── manager.py
│   │
│   ├── modes/                    # Run modes
│   │   ├── __init__.py
│   │   ├── interactive/          # TUI mode
│   │   │   ├── __init__.py
│   │   │   ├── app.py            # Textual app
│   │   │   ├── components/       # UI components
│   │   │   └── commands.py       # Slash commands
│   │   ├── print.py              # Print mode
│   │   └── rpc.py                # RPC mode
│   │
│   ├── agent_session.py          # AgentSession
│   └── system_prompt.py          # System prompt builder
│
└── tests/
    ├── test_tools/
    ├── test_session/
    ├── test_compaction/
    └── test_modes/
```

---

## Dependencies

```toml
[project]
dependencies = [
    "pipy-ai>=0.1.0",
    "pipy-agent>=0.1.0",
    "pipy-tui>=0.1.0",
    "textual>=0.50.0",
    "click>=8.0",
    "pydantic>=2.0",
    "aiofiles>=23.0",        # Async file operations
    "watchfiles>=0.20",      # File watching
]
```

---

## Key Differences from pi-mono

| Aspect | pi-mono | pipy-coding-agent |
|--------|---------|-------------------|
| Language | TypeScript | Python |
| TUI | Custom pi-tui | Textual + pipy-tui |
| Async | Native async | asyncio |
| Config | JSON | TOML/YAML + Pydantic |
| Extensions | v0.1.0 | Defer to v0.2.0 |
| Package mgmt | npm-based | pip/uv-based |

---

## Incremental Build Strategy

### Week 1: Foundation
1. **Day 1-2**: Tools (read, write, bash)
2. **Day 3**: Tools (edit, grep, find, ls)
3. **Day 4-5**: Basic SessionManager (persistence)

### Week 2: Core
1. **Day 1-2**: SettingsManager + ResourceLoader
2. **Day 3-4**: Compaction
3. **Day 5**: Integration testing

### Week 3: AgentSession
1. **Day 1-3**: AgentSession implementation
2. **Day 4-5**: Event system, auto-compaction

### Week 4: Interactive Mode
1. **Day 1-3**: Textual app + pipy-tui integration
2. **Day 4**: Slash commands
3. **Day 5**: CLI + print mode

### Week 5: Polish
1. **Day 1-2**: RPC mode
2. **Day 3-4**: Testing, bug fixes
3. **Day 5**: Documentation, release

---

## Testing Strategy

Each phase should have tests before moving on:

```python
# tests/test_tools/test_read.py
@pytest.mark.asyncio
async def test_read_file():
    result = await read_tool.execute("call_1", {"path": "test.txt"}, None, None)
    assert "Hello" in result.content[0].text

# tests/test_session/test_manager.py
def test_session_persistence():
    manager = SessionManager(tmp_path, Path.cwd())
    session_id = manager.create_session()
    manager.append_message(user_msg)
    
    # Reload
    manager2 = SessionManager(tmp_path, Path.cwd())
    context = manager2.load_session(session_id)
    assert len(context.messages) == 1
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Scope creep | High | High | Strict phase boundaries |
| TUI complexity | Medium | High | Leverage Textual heavily |
| Session format | Low | Medium | Simple JSON lines format |
| Extension system | High | Medium | Defer to v0.2.0 |
| Cross-platform | Medium | Medium | Test on Windows early |

---

## Success Criteria

### v0.1.0 (MVP)
- [ ] All 7 tools working
- [ ] Session persistence
- [ ] Interactive mode with PiEditor
- [ ] Basic slash commands
- [ ] Compaction
- [ ] Print mode

### v0.2.0
- [ ] Extension system
- [ ] RPC mode
- [ ] Package manager
- [ ] Full feature parity

---

## Summary

**Estimated effort:** 4-5 weeks

**Strategy:** Build incrementally, test each phase, leverage existing pipy-* packages heavily.

**Key insight:** pi-mono/coding-agent is ~31K lines, but much of that is:
- UI components (use Textual)
- Extension system (defer)
- Package management (defer)

The core (tools + session + compaction + basic TUI) is achievable in ~5-6K lines of Python.

Let's start with Phase 1: Tools! 🚀
