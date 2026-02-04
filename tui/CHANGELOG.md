# Changelog

## [0.51.6] - 2026-02-04

**Upstream sync:** [pi-tui v0.51.6](https://github.com/badlogic/pi-mono/releases/tag/v0.51.6)  
**Upstream commit:** `9cf5758b`

### Not Applicable (vs upstream v0.51.3–v0.51.6)

- v0.51.4: Emoji surrogate pair scrolling fix → Textual handles Unicode rendering
- v0.51.6: Slash command menu on first line → Our `SlashCommandProvider` already allows this (no multi-line restriction)
- v0.51.6: Settings list narrow terminal crash fix → No settings list component yet

_No code changes - version bump only._

---

## [0.51.2] - 2026-02-02

**Upstream sync:** [pi-tui v0.51.2](https://github.com/badlogic/pi-mono/releases/tag/v0.51.2)  
**Upstream commit:** `ff9a3f06`

### Added

- Hidden file support in `@` file autocomplete - files like `.env`, `.gitignore` now appear in completions
- Exclude `.git` directory from autocomplete results

### Changed

- `FilePathProvider._search_with_fd()` now uses `--hidden` flag and excludes `.git` paths
- `FilePathProvider._search_directory()` now includes hidden files (except `.git`)

### Known Limitations (vs upstream)

The following upstream v0.51.1/v0.51.2 changes are **not applicable** to pipy-tui because Textual handles these concerns:

- `Terminal.drainInput()` for Kitty key release events - Textual manages stdin
- SSH stdin buffer race conditions - Textual handles
- `PI_DEBUG_REDRAW=1` env var - Textual has its own debug tools
- `clearOnShrink` setting - Textual's rendering model
- Terminal height redraw optimizations - Textual manages rendering
- Emoji cursor positioning - Textual handles cursor
- Legacy newline escape sequence handling - Textual parses keyboard input
- Submit fallback for backslash+enter - Textual keyboard abstraction

## [0.1.0] - 2026-02-02

**Initial release** - Python port of pi-tui concepts using Textual.

### Added

- `PiEditor` - Multi-line editor widget with autocomplete support
- `AutocompleteProvider` system with `SlashCommandProvider`, `FilePathProvider`, `CombinedProvider`
- `fuzzy_match()` and `fuzzy_filter()` utilities
- `KeybindingManager` for configurable editor keybindings
- `visible_width()`, `word_wrap_line()`, and other text utilities
