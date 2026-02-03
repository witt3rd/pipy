"""Tests for skill loading."""

import os
import tempfile
import pytest

from pipy_coding_agent.resources.skills import (
    Skill,
    LoadSkillsResult,
    parse_frontmatter,
    load_skill_from_file,
    load_skills_from_dir,
    load_skills,
    format_skills_for_prompt,
    validate_skill_name,
)
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestParseFrontmatter:
    def test_no_frontmatter(self):
        """Test content with no frontmatter."""
        content = "Just some content"
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter == {}
        assert body == "Just some content"

    def test_simple_frontmatter(self):
        """Test content with simple frontmatter."""
        content = """---
name: test-skill
description: A test skill
---

Skill content here."""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter["name"] == "test-skill"
        assert frontmatter["description"] == "A test skill"
        assert body == "Skill content here."

    def test_boolean_frontmatter(self):
        """Test boolean values in frontmatter."""
        content = """---
enabled: true
disabled: false
---

Content."""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter["enabled"] is True
        assert frontmatter["disabled"] is False

    def test_quoted_values(self):
        """Test quoted values in frontmatter."""
        content = """---
name: "quoted name"
desc: 'single quoted'
---

Content."""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter["name"] == "quoted name"
        assert frontmatter["desc"] == "single quoted"


class TestValidateSkillName:
    def test_valid_name(self):
        """Test valid skill name."""
        errors = validate_skill_name("my-skill", "my-skill")
        assert errors == []

    def test_name_mismatch(self):
        """Test name not matching directory."""
        errors = validate_skill_name("other-name", "my-skill")
        assert any("does not match" in e for e in errors)

    def test_invalid_characters(self):
        """Test invalid characters in name."""
        errors = validate_skill_name("My_Skill", "My_Skill")
        assert any("invalid characters" in e for e in errors)

    def test_leading_hyphen(self):
        """Test leading hyphen."""
        errors = validate_skill_name("-skill", "-skill")
        assert any("start or end with a hyphen" in e for e in errors)

    def test_consecutive_hyphens(self):
        """Test consecutive hyphens."""
        errors = validate_skill_name("my--skill", "my--skill")
        assert any("consecutive hyphens" in e for e in errors)


class TestLoadSkillFromFile:
    def test_load_valid_skill(self, temp_dir):
        """Test loading a valid skill file."""
        skill_path = Path(temp_dir) / "test-skill" / "SKILL.md"
        skill_path.parent.mkdir()
        skill_path.write_text("""---
name: test-skill
description: A test skill
---

This is the skill content.
It can have multiple lines.""")

        skill, diagnostics = load_skill_from_file(skill_path, skill_path.parent, "test")

        assert skill is not None
        assert skill.name == "test-skill"
        assert skill.description == "A test skill"
        assert "skill content" in skill.content

    def test_load_skill_no_frontmatter(self, temp_dir):
        """Test loading skill without frontmatter."""
        skill_path = Path(temp_dir) / "simple.md"
        skill_path.write_text("Just some content.")

        skill, diagnostics = load_skill_from_file(skill_path, Path(temp_dir), "test")

        assert skill is not None
        assert skill.name == "simple"

    def test_load_empty_skill(self, temp_dir):
        """Test loading skill with no content."""
        skill_path = Path(temp_dir) / "empty.md"
        skill_path.write_text("""---
name: empty
description: Empty skill
---
""")

        skill, diagnostics = load_skill_from_file(skill_path, Path(temp_dir), "test")

        assert skill is None
        assert any("no content" in d.message for d in diagnostics)


class TestLoadSkillsFromDir:
    def test_load_from_directory(self, temp_dir):
        """Test loading skills from a directory."""
        # Create skill files
        (Path(temp_dir) / "skill1.md").write_text("""---
name: skill1
description: First skill
---

Skill 1 content.""")

        (Path(temp_dir) / "skill2.md").write_text("""---
name: skill2
description: Second skill
---

Skill 2 content.""")

        result = load_skills_from_dir(temp_dir)

        assert len(result.skills) == 2
        names = {s.name for s in result.skills}
        assert "skill1" in names
        assert "skill2" in names

    def test_load_nested_skills(self, temp_dir):
        """Test loading SKILL.md from subdirectories."""
        skill_dir = Path(temp_dir) / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: my-skill
description: Nested skill
---

Nested content.""")

        result = load_skills_from_dir(temp_dir)

        assert len(result.skills) == 1
        assert result.skills[0].name == "my-skill"

    def test_skip_hidden_files(self, temp_dir):
        """Test that hidden files are skipped."""
        (Path(temp_dir) / ".hidden.md").write_text("Hidden content")
        (Path(temp_dir) / "visible.md").write_text("""---
name: visible
description: Visible skill
---
Content.""")

        result = load_skills_from_dir(temp_dir)

        assert len(result.skills) == 1
        assert result.skills[0].name == "visible"


class TestLoadSkills:
    def test_load_from_file_path(self, temp_dir):
        """Test loading from a file path."""
        skill_path = Path(temp_dir) / "skill.md"
        skill_path.write_text("""---
name: single
description: Single skill
---
Content.""")

        result = load_skills([skill_path])

        assert len(result.skills) == 1
        assert result.skills[0].name == "single"

    def test_load_from_multiple_paths(self, temp_dir):
        """Test loading from multiple paths."""
        dir1 = Path(temp_dir) / "dir1"
        dir2 = Path(temp_dir) / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "s1.md").write_text("---\nname: s1\ndescription: S1\n---\nContent.")
        (dir2 / "s2.md").write_text("---\nname: s2\ndescription: S2\n---\nContent.")

        result = load_skills([dir1, dir2])

        assert len(result.skills) == 2


class TestFormatSkillsForPrompt:
    def test_format_empty(self):
        """Test formatting empty skills list."""
        result = format_skills_for_prompt([])
        assert result == ""

    def test_format_single_skill(self):
        """Test formatting a single skill."""
        skills = [
            Skill(
                name="test-skill",
                description="A test skill",
                content="Do the thing.",
                file_path="/path/to/skill.md",
                base_dir="/path/to",
                source="test",
            )
        ]

        result = format_skills_for_prompt(skills)

        assert "<available_skills>" in result
        assert "**test-skill**:" in result
        assert "A test skill" in result
        assert "location: /path/to/skill.md" in result
