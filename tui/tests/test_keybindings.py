"""Tests for keybindings."""

from pipy_tui import (
    EditorAction,
    KeybindingConfig,
    KeybindingManager,
    get_default_keybindings,
)


class TestKeybindingConfig:
    def test_get_keys(self):
        config = KeybindingConfig(
            bindings={
                EditorAction.SUBMIT: ["enter"],
            }
        )
        assert config.get_keys(EditorAction.SUBMIT) == ["enter"]
        assert config.get_keys(EditorAction.UNDO) == []

    def test_set_keys(self):
        config = KeybindingConfig()
        config.set_keys(EditorAction.SUBMIT, ["enter", "ctrl+enter"])
        assert config.get_keys(EditorAction.SUBMIT) == ["enter", "ctrl+enter"]

    def test_add_key(self):
        config = KeybindingConfig(
            bindings={
                EditorAction.SUBMIT: ["enter"],
            }
        )
        config.add_key(EditorAction.SUBMIT, "ctrl+enter")
        assert "ctrl+enter" in config.get_keys(EditorAction.SUBMIT)

    def test_add_key_no_duplicate(self):
        config = KeybindingConfig(
            bindings={
                EditorAction.SUBMIT: ["enter"],
            }
        )
        config.add_key(EditorAction.SUBMIT, "enter")
        assert config.get_keys(EditorAction.SUBMIT) == ["enter"]


class TestKeybindingManager:
    def test_match_simple(self):
        manager = KeybindingManager(
            KeybindingConfig(
                bindings={
                    EditorAction.SUBMIT: ["enter"],
                }
            )
        )
        assert manager.match("enter") == EditorAction.SUBMIT

    def test_match_with_modifiers(self):
        manager = KeybindingManager(
            KeybindingConfig(
                bindings={
                    EditorAction.CURSOR_WORD_LEFT: ["ctrl+left"],
                }
            )
        )
        assert manager.match("ctrl+left") == EditorAction.CURSOR_WORD_LEFT

    def test_match_case_insensitive(self):
        manager = KeybindingManager(
            KeybindingConfig(
                bindings={
                    EditorAction.SUBMIT: ["Enter"],
                }
            )
        )
        assert manager.match("enter") == EditorAction.SUBMIT
        assert manager.match("ENTER") == EditorAction.SUBMIT

    def test_match_modifier_order(self):
        # Modifiers should be normalized
        manager = KeybindingManager(
            KeybindingConfig(
                bindings={
                    EditorAction.SELECT_ALL: ["ctrl+shift+a"],
                }
            )
        )
        assert manager.match("ctrl+shift+a") == EditorAction.SELECT_ALL
        assert manager.match("shift+ctrl+a") == EditorAction.SELECT_ALL

    def test_no_match(self):
        manager = KeybindingManager(
            KeybindingConfig(
                bindings={
                    EditorAction.SUBMIT: ["enter"],
                }
            )
        )
        assert manager.match("tab") is None

    def test_get_action_keys(self):
        manager = KeybindingManager(
            KeybindingConfig(
                bindings={
                    EditorAction.SUBMIT: ["enter", "ctrl+enter"],
                }
            )
        )
        keys = manager.get_action_keys(EditorAction.SUBMIT)
        assert "enter" in keys
        assert "ctrl+enter" in keys


class TestDefaultKeybindings:
    def test_has_common_bindings(self):
        config = get_default_keybindings()
        assert EditorAction.SUBMIT in config.bindings
        assert EditorAction.UNDO in config.bindings
        assert EditorAction.CURSOR_UP in config.bindings
        assert EditorAction.DELETE_CHAR_BEFORE in config.bindings

    def test_enter_submits(self):
        manager = KeybindingManager(get_default_keybindings())
        assert manager.match("enter") == EditorAction.SUBMIT

    def test_ctrl_z_undoes(self):
        manager = KeybindingManager(get_default_keybindings())
        assert manager.match("ctrl+z") == EditorAction.UNDO

    def test_arrows_move(self):
        manager = KeybindingManager(get_default_keybindings())
        assert manager.match("up") == EditorAction.CURSOR_UP
        assert manager.match("down") == EditorAction.CURSOR_DOWN
        assert manager.match("left") == EditorAction.CURSOR_LEFT
        assert manager.match("right") == EditorAction.CURSOR_RIGHT
