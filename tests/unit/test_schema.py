"""Unit tests for Pydantic schema models."""

import pytest
from pydantic import ValidationError

from specspectacle.parser.schema import (
    AssertStepModel,
    BrowserBackStepModel,
    BrowserForwardStepModel,
    CheckStepModel,
    ClickFirstVisibleStepModel,
    ClickStepModel,
    ConfigModel,
    DragAndDropStepModel,
    FileUploadStepModel,
    FlowModel,
    NavigateStepModel,
    OutputModel,
    OverlayModel,
    OverlayStyleModel,
    PressKeyStepModel,
    ScrollStepModel,
    SelectFirstNonPlaceholderStepModel,
    SpecModel,
    TypeStepModel,
    UncheckStepModel,
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


class TestNewActionStepModels:
    """Tests for the 8 new action step models."""

    # --- press_key ---

    def test_press_key_step_valid(self):
        step = PressKeyStepModel(key="Enter")
        assert step.action == "press_key"
        assert step.key == "Enter"

    def test_press_key_step_combo(self):
        step = PressKeyStepModel(key="Control+a")
        assert step.key == "Control+a"

    def test_press_key_step_missing_key(self):
        with pytest.raises(ValidationError):
            PressKeyStepModel()

    # --- browser_back ---

    def test_browser_back_step_valid(self):
        step = BrowserBackStepModel()
        assert step.action == "browser_back"
        assert step.timeout == 10000

    def test_browser_back_step_custom_timeout(self):
        step = BrowserBackStepModel(timeout=5000)
        assert step.timeout == 5000

    def test_browser_back_step_invalid_timeout(self):
        with pytest.raises(ValidationError):
            BrowserBackStepModel(timeout=500)  # below minimum of 1000

    # --- browser_forward ---

    def test_browser_forward_step_valid(self):
        step = BrowserForwardStepModel()
        assert step.action == "browser_forward"
        assert step.timeout == 10000

    # --- check ---

    def test_check_step_valid(self):
        step = CheckStepModel(selector="#agree")
        assert step.action == "check"
        assert step.selector == "#agree"

    def test_check_step_missing_selector(self):
        with pytest.raises(ValidationError):
            CheckStepModel()

    # --- uncheck ---

    def test_uncheck_step_valid(self):
        step = UncheckStepModel(selector="#agree")
        assert step.action == "uncheck"
        assert step.selector == "#agree"

    def test_uncheck_step_missing_selector(self):
        with pytest.raises(ValidationError):
            UncheckStepModel()

    # --- assert ---

    def test_assert_step_visible_true(self):
        step = AssertStepModel(selector="#banner", visible=True)
        assert step.action == "assert"
        assert step.visible is True
        assert step.text is None

    def test_assert_step_visible_false(self):
        step = AssertStepModel(selector="#banner", visible=False)
        assert step.visible is False

    def test_assert_step_text(self):
        step = AssertStepModel(selector="h1", text="Welcome")
        assert step.text == "Welcome"
        assert step.visible is None

    def test_assert_step_both_conditions(self):
        """Allow both visible and text to be set simultaneously."""
        step = AssertStepModel(selector="h1", visible=True, text="Hello")
        assert step.visible is True
        assert step.text == "Hello"

    def test_assert_step_no_condition_raises(self):
        with pytest.raises(ValidationError):
            AssertStepModel(selector="#banner")  # neither visible nor text

    def test_assert_step_missing_selector(self):
        with pytest.raises(ValidationError):
            AssertStepModel(visible=True)

    def test_assert_step_default_timeout(self):
        step = AssertStepModel(selector="#el", visible=True)
        assert step.timeout == 10000

    # --- click_first_visible ---

    def test_click_first_visible_step_valid(self):
        step = ClickFirstVisibleStepModel(selector=".btn")
        assert step.action == "click_first_visible"
        assert step.selector == ".btn"

    def test_click_first_visible_step_missing_selector(self):
        with pytest.raises(ValidationError):
            ClickFirstVisibleStepModel()

    # --- select_first_non_placeholder ---

    def test_select_first_non_placeholder_step_valid(self):
        step = SelectFirstNonPlaceholderStepModel(selector="select#country")
        assert step.action == "select_first_non_placeholder"
        assert step.selector == "select#country"

    def test_select_first_non_placeholder_missing_selector(self):
        with pytest.raises(ValidationError):
            SelectFirstNonPlaceholderStepModel()

    # --- file_upload ---

    def test_file_upload_step_single_file(self):
        step = FileUploadStepModel(selector="input[type=file]", file="/tmp/doc.pdf")
        assert step.action == "file_upload"
        assert step.file == "/tmp/doc.pdf"
        assert step.files is None

    def test_file_upload_step_multiple_files(self):
        step = FileUploadStepModel(
            selector="input[type=file]",
            files=["/tmp/a.pdf", "/tmp/b.pdf"],
        )
        assert step.files == ["/tmp/a.pdf", "/tmp/b.pdf"]
        assert step.file is None

    def test_file_upload_step_both_raises(self):
        with pytest.raises(ValidationError):
            FileUploadStepModel(
                selector="input[type=file]",
                file="/tmp/a.pdf",
                files=["/tmp/b.pdf"],
            )

    def test_file_upload_step_neither_raises(self):
        with pytest.raises(ValidationError):
            FileUploadStepModel(selector="input[type=file]")

    def test_file_upload_step_missing_selector(self):
        with pytest.raises(ValidationError):
            FileUploadStepModel(file="/tmp/doc.pdf")

    # --- drag_and_drop ---

    def test_drag_and_drop_step_valid(self):
        step = DragAndDropStepModel(source="#item-1", target="#bucket")
        assert step.action == "drag_and_drop"
        assert step.source == "#item-1"
        assert step.target == "#bucket"

    def test_drag_and_drop_step_missing_source(self):
        with pytest.raises(ValidationError):
            DragAndDropStepModel(target="#bucket")

    def test_drag_and_drop_step_missing_target(self):
        with pytest.raises(ValidationError):
            DragAndDropStepModel(source="#item-1")
