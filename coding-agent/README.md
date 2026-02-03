# pipy-coding-agent

AI coding assistant - Python port of [@mariozechner/pi-coding-agent](https://github.com/mariozechner/pi-mono/tree/main/packages/coding-agent).

## Installation

```bash
pip install pipy-coding-agent
```

## Features

### Phase 1: Coding Tools (Current)

Seven coding tools for file operations and command execution:

- **read** - Read file contents (text files and images)
- **bash** - Execute shell commands with timeout support
- **edit** - Precise find-and-replace editing
- **write** - Create and write files
- **grep** - Search file contents by pattern
- **find** - Find files by glob pattern
- **ls** - List directory contents

### Coming Soon

- Session management and persistence
- Context compaction for long sessions
- Interactive TUI mode
- Settings and configuration
- Extension system

## Usage

### As Library

```python
from pipy_coding_agent import create_coding_tools, create_read_only_tools

# Create tools for a specific directory
tools = create_coding_tools("/path/to/project")

# Or use read-only tools for exploration
tools = create_read_only_tools("/path/to/project")
```

### Individual Tools

```python
from pipy_coding_agent import create_read_tool, create_bash_tool

# Create tools
read = create_read_tool("/path/to/project")
bash = create_bash_tool("/path/to/project")

# Execute
result = await read.execute("call_1", {"path": "README.md"})
print(result.content[0].text)

result = await bash.execute("call_1", {"command": "ls -la"})
print(result.content[0].text)
```

## Development

```bash
# Clone and setup
git clone https://github.com/witt3rd/pipy-coding-agent
cd pipy-coding-agent

# Install with dev dependencies
uv sync --extra dev

# Run tests
uv run pytest tests/ -v
```

## Architecture

```
┌─────────────────────────────────────────┐
│           pipy-coding-agent             │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │            Tools                 │   │
│  │  read, bash, edit, write,       │   │
│  │  grep, find, ls                 │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │     (Future) Session Mgmt       │   │
│  │     (Future) Compaction         │   │
│  │     (Future) Interactive TUI    │   │
│  └─────────────────────────────────┘   │
│                                         │
├─────────────────────────────────────────┤
│              Dependencies               │
│  pipy-ai, pipy-agent, pipy-tui         │
└─────────────────────────────────────────┘
```

## Acknowledgments

This project is a Python port of the excellent [pi-mono](https://github.com/mariozechner/pi-mono) TypeScript packages by [Mario Zechner](https://github.com/badlogic) (@badlogic). The design, architecture, and much of the implementation logic comes directly from his work.

## License

MIT
