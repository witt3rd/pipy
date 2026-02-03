"""Tests for extension loader."""

import json
import pytest
import tempfile
from pathlib import Path

from pipy_coding_agent.extensions import (
    Extension,
    ExtensionManifest,
    ExtensionLoader,
    load_extension,
    load_extensions_from_dir,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestExtensionManifest:
    def test_default_values(self):
        """Test default manifest values."""
        manifest = ExtensionManifest(name="test")

        assert manifest.name == "test"
        assert manifest.version == "0.0.0"
        assert manifest.description == ""
        assert manifest.skills == []
        assert manifest.hooks == {}


class TestLoadExtension:
    def test_load_from_json_manifest(self, temp_dir):
        """Test loading extension with JSON manifest."""
        ext_dir = temp_dir / "my-extension"
        ext_dir.mkdir()

        manifest = {
            "name": "my-extension",
            "version": "1.0.0",
            "description": "Test extension",
            "author": "Test Author",
        }
        (ext_dir / "extension.json").write_text(json.dumps(manifest))

        ext = load_extension(ext_dir)

        assert ext.loaded is True
        assert ext.manifest.name == "my-extension"
        assert ext.manifest.version == "1.0.0"
        assert ext.manifest.description == "Test extension"

    def test_load_from_package_json(self, temp_dir):
        """Test loading extension with package.json."""
        ext_dir = temp_dir / "npm-style"
        ext_dir.mkdir()

        package = {
            "name": "npm-style",
            "version": "2.0.0",
        }
        (ext_dir / "package.json").write_text(json.dumps(package))

        ext = load_extension(ext_dir)

        assert ext.loaded is True
        assert ext.manifest.name == "npm-style"
        assert ext.manifest.version == "2.0.0"

    def test_load_with_readme_frontmatter(self, temp_dir):
        """Test loading extension with README frontmatter."""
        ext_dir = temp_dir / "readme-ext"
        ext_dir.mkdir()

        readme = """---
name: readme-ext
version: 0.5.0
description: From README
---

# My Extension

Documentation here.
"""
        (ext_dir / "README.md").write_text(readme)

        ext = load_extension(ext_dir)

        assert ext.loaded is True
        assert ext.manifest.name == "readme-ext"
        assert ext.manifest.version == "0.5.0"

    def test_load_minimal(self, temp_dir):
        """Test loading extension with minimal files."""
        ext_dir = temp_dir / "minimal"
        ext_dir.mkdir()

        ext = load_extension(ext_dir)

        assert ext.loaded is True
        assert ext.manifest.name == "minimal"

    def test_load_nonexistent(self, temp_dir):
        """Test loading nonexistent extension."""
        ext = load_extension(temp_dir / "does-not-exist")

        assert ext.loaded is False
        assert ext.error is not None
        assert "does not exist" in ext.error

    def test_load_file_not_dir(self, temp_dir):
        """Test loading from file instead of directory."""
        file_path = temp_dir / "not-a-dir.txt"
        file_path.write_text("content")

        ext = load_extension(file_path)

        assert ext.loaded is False
        assert ext.error is not None
        assert "not a directory" in ext.error


class TestLoadExtensionsFromDir:
    def test_load_multiple(self, temp_dir):
        """Test loading multiple extensions."""
        for name in ["ext1", "ext2", "ext3"]:
            ext_dir = temp_dir / name
            ext_dir.mkdir()
            (ext_dir / "extension.json").write_text(
                json.dumps({"name": name})
            )

        extensions = load_extensions_from_dir(temp_dir)

        assert len(extensions) == 3
        names = {e.manifest.name for e in extensions}
        assert names == {"ext1", "ext2", "ext3"}

    def test_skip_hidden(self, temp_dir):
        """Test that hidden directories are skipped."""
        (temp_dir / ".hidden").mkdir()
        (temp_dir / "visible").mkdir()

        extensions = load_extensions_from_dir(temp_dir)

        assert len(extensions) == 1
        assert extensions[0].manifest.name == "visible"

    def test_empty_dir(self, temp_dir):
        """Test loading from empty directory."""
        extensions = load_extensions_from_dir(temp_dir)
        assert extensions == []

    def test_nonexistent_dir(self, temp_dir):
        """Test loading from nonexistent directory."""
        extensions = load_extensions_from_dir(temp_dir / "nope")
        assert extensions == []


class TestExtensionLoader:
    def test_create_loader(self, temp_dir):
        """Test creating extension loader."""
        loader = ExtensionLoader(cwd=temp_dir, agent_dir=temp_dir)

        extensions = loader.load_all()

        assert isinstance(extensions, list)

    def test_load_from_project(self, temp_dir):
        """Test loading from project directory."""
        ext_dir = temp_dir / ".pi" / "extensions" / "project-ext"
        ext_dir.mkdir(parents=True)
        (ext_dir / "extension.json").write_text(
            json.dumps({"name": "project-ext"})
        )

        loader = ExtensionLoader(cwd=temp_dir, agent_dir=temp_dir)
        extensions = loader.load_all()

        assert len(extensions) == 1
        assert extensions[0].manifest.name == "project-ext"

    def test_get_by_name(self, temp_dir):
        """Test getting extension by name."""
        ext_dir = temp_dir / ".pi" / "extensions" / "named-ext"
        ext_dir.mkdir(parents=True)
        (ext_dir / "extension.json").write_text(
            json.dumps({"name": "named-ext"})
        )

        loader = ExtensionLoader(cwd=temp_dir, agent_dir=temp_dir)
        loader.load_all()

        ext = loader.get("named-ext")
        assert ext is not None
        assert ext.manifest.name == "named-ext"

        assert loader.get("nonexistent") is None
