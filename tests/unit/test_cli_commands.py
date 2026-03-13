"""Unit tests for CLI commands."""

import os
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from specspectacle.cli.commands.config import config
from specspectacle.cli.commands.scaffold import scaffold
from specspectacle.cli.commands.validate import validate
from specspectacle.cli.main import cli


class TestCLIMain:
    """Tests for main CLI group."""

    def test_cli_help(self):
        """Test CLI shows help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "SpecSpectacle" in result.output
        assert "validate" in result.output
        assert "scaffold" in result.output
        assert "config" in result.output
        assert "run" in result.output

    def test_cli_version(self):
        """Test CLI shows version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "specspectacle" in result.output.lower()


class TestConfigCommand:
    """Tests for config command."""

    def test_config_displays_info(self):
        """Test config command displays configuration info."""
        runner = CliRunner()
        result = runner.invoke(config)
        assert result.exit_code == 0
        assert "Configuration" in result.output or "SpecSpectacle" in result.output

    def test_config_shows_ffmpeg_status(self):
        """Test config command shows FFmpeg status."""
        runner = CliRunner()
        result = runner.invoke(config)
        assert result.exit_code == 0
        # Should show FFmpeg status (either found or not found)
        assert "FFmpeg" in result.output or "ffmpeg" in result.output.lower()

    def test_config_shows_paths(self):
        """Test config command shows path information."""
        runner = CliRunner()
        result = runner.invoke(config)
        assert result.exit_code == 0
        # Should show path-related information
        assert "Path" in result.output or "Directory" in result.output

    @patch.dict(os.environ, {"SPECSPECTACLE_TTS_API_KEY": "test_api_key_1234567890"})
    def test_config_shows_env_vars(self):
        """Test config command shows environment variables."""
        runner = CliRunner()
        result = runner.invoke(config)
        assert result.exit_code == 0
        # Should show environment variable section
        assert "Environment" in result.output or "Variable" in result.output

    @patch("shutil.which", return_value=None)
    def test_config_ffmpeg_not_found(self, mock_which):
        """Test config command when FFmpeg is not installed."""
        runner = CliRunner()
        result = runner.invoke(config)
        assert result.exit_code == 0
        # Should show warning about FFmpeg
        assert "not found" in result.output.lower() or "Not found" in result.output


class TestValidateCommand:
    """Tests for validate command."""

    def test_validate_valid_yaml(self, tmp_path):
        """Test validating a valid YAML file."""
        # Create a valid YAML spec
        yaml_content = """
name: "Test Spec"
description: "A test specification"
version: "0.1.0"
config:
  target_app: "https://example.com"
  viewport:
    width: 1280
    height: 720
output:
  filename: "test.mp4"
flows:
  - name: "Test Flow"
    steps:
      - action: "navigate"
        url: "https://example.com"
"""
        yaml_file = tmp_path / "valid_spec.yaml"
        yaml_file.write_text(yaml_content)

        runner = CliRunner()
        result = runner.invoke(validate, [str(yaml_file)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower() or "Valid" in result.output

    def test_validate_invalid_yaml(self, tmp_path):
        """Test validating an invalid YAML file."""
        # Create an invalid YAML spec (missing required fields)
        yaml_content = """
name: "Test Spec"
# Missing required fields
"""
        yaml_file = tmp_path / "invalid_spec.yaml"
        yaml_file.write_text(yaml_content)

        runner = CliRunner()
        result = runner.invoke(validate, [str(yaml_file)])
        assert result.exit_code == 1
        assert "failed" in result.output.lower() or "error" in result.output.lower()

    def test_validate_file_not_found(self):
        """Test validating a non-existent file."""
        runner = CliRunner()
        result = runner.invoke(validate, ["nonexistent_file.yaml"])
        # Click's exists=True should handle this
        assert result.exit_code != 0

    def test_validate_malformed_yaml(self, tmp_path):
        """Test validating a malformed YAML file."""
        yaml_content = """
name: "Test: "Invalid: Syntax
  - broken
    indentation
"""
        yaml_file = tmp_path / "malformed.yaml"
        yaml_file.write_text(yaml_content)

        runner = CliRunner()
        result = runner.invoke(validate, [str(yaml_file)])
        assert result.exit_code == 1


class TestScaffoldCommand:
    """Tests for scaffold command."""

    def test_scaffold_creates_file(self, tmp_path):
        """Test scaffold creates a YAML template file."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(scaffold, ["my-demo.yaml"])
            assert result.exit_code == 0
            assert Path("my-demo.yaml").exists()
            assert "Created" in result.output or "created" in result.output

    def test_scaffold_default_filename(self, tmp_path):
        """Test scaffold uses default filename."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(scaffold)
            assert result.exit_code == 0
            assert Path("demo-spec.yaml").exists()

    def test_scaffold_no_overwrite_without_force(self, tmp_path):
        """Test scaffold doesn't overwrite existing file without --force."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create existing file
            Path("existing.yaml").write_text("existing content")

            result = runner.invoke(scaffold, ["existing.yaml"])
            assert result.exit_code == 1
            assert "exists" in result.output.lower() or "force" in result.output.lower()

            # File should still have original content
            assert Path("existing.yaml").read_text() == "existing content"

    def test_scaffold_overwrite_with_force(self, tmp_path):
        """Test scaffold overwrites existing file with --force."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create existing file
            Path("existing.yaml").write_text("existing content")

            result = runner.invoke(scaffold, ["existing.yaml", "--force"])
            assert result.exit_code == 0

            # File should have new content
            new_content = Path("existing.yaml").read_text()
            assert new_content != "existing content"
            assert "SpecSpectacle" in new_content

    def test_scaffold_template_contains_all_actions(self, tmp_path):
        """Test scaffold template includes all supported actions."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(scaffold)
            assert result.exit_code == 0

            content = Path("demo-spec.yaml").read_text()
            # Check for all action types
            assert "navigate" in content
            assert "click" in content
            assert "type" in content
            assert "wait" in content
            assert "scroll" in content
            assert "hover" in content
            assert "screenshot" in content
            assert "select" in content
