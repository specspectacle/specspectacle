"""Unit tests for Pydantic schema models."""

import pytest
from pydantic import ValidationError

from specspectacle.parser.schema import (
    ClickStepModel,
    ConfigModel,
    FlowModel,
    NarrationConfigModel,
    NarrationModel,
    NavigateStepModel,
    OutputModel,
    OverlayModel,
    OverlayStyleModel,
    ScrollStepModel,
    SpecModel,
    TypeStepModel,
    ViewportModel,
    WaitStepModel,
)


class TestViewportModel:
    """Test ViewportModel validation."""

    def test_default_values(self):
        """Test default viewport values."""
        viewport = ViewportModel()
        assert viewport.width == 1280
        assert viewport.height == 720

    def test_custom_values(self):
        """Test custom viewport values."""
        viewport = ViewportModel(width=1920, height=1080)
        assert viewport.width == 1920
        assert viewport.height == 1080

    def test_invalid_dimensions(self):
        """Test invalid dimensions raise ValidationError."""
        with pytest.raises(ValidationError):
            ViewportModel(width=500, height=720)  # Too small


class TestConfigModel:
    """Test ConfigModel validation."""

    def test_valid_config(self):
        """Test valid config model."""
        config = ConfigModel(target_app="https://example.com")
        assert config.target_app == "https://example.com"
        assert config.headless is True
        assert config.timeout == 5000

    def test_invalid_url(self):
        """Test invalid URL raises ValidationError."""
        with pytest.raises(ValidationError):
            ConfigModel(target_app="not-a-url")


class TestOutputModel:
    """Test OutputModel validation."""

    def test_valid_output(self):
        """Test valid output model."""
        output = OutputModel(filename="demo.mp4")
        assert output.filename == "demo.mp4"
        assert output.fps == 30
        assert output.bitrate == "5000k"

    def test_custom_values(self):
        """Test custom output values."""
        output = OutputModel(filename="custom.mp4", fps=60, bitrate="8000k", resolution="1920x1080")
        assert output.fps == 60
        assert output.bitrate == "8000k"
        assert output.resolution == "1920x1080"


class TestOverlayModel:
    """Test OverlayModel validation."""

    def test_valid_overlay(self):
        """Test valid overlay model."""
        overlay = OverlayModel(text="Test overlay")
        assert overlay.text == "Test overlay"
        assert overlay.position == "bottom"
        assert overlay.duration == 2.0

    def test_invalid_position(self):
        """Test invalid position raises ValidationError."""
        with pytest.raises(ValidationError):
            OverlayModel(text="Test", position="invalid-position")

    def test_custom_style(self):
        """Test overlay with custom style."""
        style = OverlayStyleModel(background_color="#FF0000AA", text_color="#FFFFFF", font_size=24)
        overlay = OverlayModel(text="Test", style=style)
        assert overlay.style.font_size == 24


class TestStepModels:
    """Test step action models."""

    def test_navigate_step(self):
        """Test navigate step model."""
        step = NavigateStepModel(url="https://example.com/login")
        assert step.action == "navigate"
        assert step.url == "https://example.com/login"

    def test_click_step(self):
        """Test click step model."""
        step = ClickStepModel(selector="#login-button")
        assert step.action == "click"
        assert step.selector == "#login-button"

    def test_type_step(self):
        """Test type step model."""
        step = TypeStepModel(selector="#email", text="user@example.com", delay=100)
        assert step.action == "type"
        assert step.text == "user@example.com"
        assert step.delay == 100

    def test_wait_step(self):
        """Test wait step model."""
        step = WaitStepModel(duration=2.5)
        assert step.action == "wait"
        assert step.duration == 2.5

    def test_scroll_step_with_direction(self):
        """Test scroll step with direction."""
        step = ScrollStepModel(direction="down")
        assert step.action == "scroll"
        assert step.direction == "down"

    def test_scroll_step_with_selector(self):
        """Test scroll step with selector."""
        step = ScrollStepModel(selector="#footer")
        assert step.action == "scroll"
        assert step.selector == "#footer"

    def test_scroll_step_without_params(self):
        """Test scroll step without direction or selector raises error."""
        with pytest.raises(ValidationError):
            ScrollStepModel()


class TestFlowModel:
    """Test FlowModel validation."""

    def test_valid_flow(self):
        """Test valid flow model."""
        flow = FlowModel(
            name="Test Flow",
            description="A test flow",
            steps=[
                NavigateStepModel(url="https://example.com"),
                WaitStepModel(duration=1.0),
            ],
        )
        assert flow.name == "Test Flow"
        assert len(flow.steps) == 2

    def test_empty_steps(self):
        """Test flow with empty steps raises ValidationError."""
        with pytest.raises(ValidationError):
            FlowModel(name="Test", steps=[])


class TestSpecModel:
    """Test top-level SpecModel validation."""

    def test_valid_spec(self):
        """Test valid spec model."""
        spec = SpecModel(
            name="Test Demo",
            version="0.1.0",
            config=ConfigModel(target_app="https://example.com"),
            output=OutputModel(filename="test.mp4"),
            flows=[
                FlowModel(
                    name="Test Flow",
                    steps=[NavigateStepModel(url="https://example.com")],
                )
            ],
        )
        assert spec.name == "Test Demo"
        assert spec.version == "0.1.0"
        assert len(spec.flows) == 1

    def test_invalid_version_format(self):
        """Test invalid version format raises ValidationError."""
        with pytest.raises(ValidationError):
            SpecModel(
                name="Test",
                version="1.0",  # Invalid, needs X.Y.Z
                config=ConfigModel(target_app="https://example.com"),
                output=OutputModel(filename="test.mp4"),
                flows=[FlowModel(name="Test", steps=[WaitStepModel(duration=1.0)])],
            )

    def test_empty_flows(self):
        """Test spec with empty flows raises ValidationError."""
        with pytest.raises(ValidationError):
            SpecModel(
                name="Test",
                version="0.1.0",
                config=ConfigModel(target_app="https://example.com"),
                output=OutputModel(filename="test.mp4"),
                flows=[],
            )
