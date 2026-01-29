"""Unit tests for YAML parser."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from specspectacle.parser.schema import SpecModel
from specspectacle.parser.yaml_parser import YAMLParser


class TestYAMLParser:
    """Test YAML parser functionality."""

    def test_load_valid_yaml(self, tmp_path):
        """Test loading valid YAML file."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("name: Test\nvalue: 123")

        data = YAMLParser.load_yaml(str(yaml_file))
        assert data == {"name": "Test", "value": 123}

    def test_load_nonexistent_file(self):
        """Test loading non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            YAMLParser.load_yaml("nonexistent.yaml")

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML syntax raises error."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("name: Test\n  invalid: indentation")

        with pytest.raises(yaml.YAMLError):
            YAMLParser.load_yaml(str(yaml_file))

    def test_load_empty_yaml(self, tmp_path):
        """Test loading empty YAML file raises error."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        with pytest.raises(yaml.YAMLError):
            YAMLParser.load_yaml(str(yaml_file))

    def test_parse_valid_spec(self, tmp_path):
        """Test parsing valid spec YAML."""
        yaml_content = """
name: "Test Demo"
description: "A test demo"
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
      - action: "wait"
        duration: 1.0
"""
        yaml_file = tmp_path / "spec.yaml"
        yaml_file.write_text(yaml_content)

        spec = YAMLParser.parse(str(yaml_file))

        assert isinstance(spec, SpecModel)
        assert spec.name == "Test Demo"
        assert spec.version == "0.1.0"
        assert len(spec.flows) == 1
        assert len(spec.flows[0].steps) == 2
        assert spec.flows[0].steps[0].action == "navigate"
        assert spec.flows[0].steps[1].action == "wait"

    def test_parse_invalid_spec_missing_required(self, tmp_path):
        """Test parsing spec with missing required fields raises ValidationError."""
        yaml_content = """
name: "Test Demo"
# Missing version and config
flows:
  - name: "Test"
    steps:
      - action: "wait"
        duration: 1.0
"""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValidationError) as exc_info:
            YAMLParser.parse(str(yaml_file))

        # Verify error mentions missing fields
        errors = exc_info.value.errors()
        assert any("version" in str(err) for err in errors)

    def test_format_validation_error(self):
        """Test formatting of validation errors."""
        # Create a simple validation error
        try:
            SpecModel(
                name="Test",
                version="invalid",  # Invalid version format
                config={"target_app": "not-a-url"},  # Invalid URL
                output={"filename": "test.mp4"},
                flows=[],  # Empty flows not allowed
            )
        except ValidationError as e:
            formatted = YAMLParser.format_validation_error(e)

            assert "Validation errors found:" in formatted
            assert "version" in formatted.lower() or "flows" in formatted.lower()
