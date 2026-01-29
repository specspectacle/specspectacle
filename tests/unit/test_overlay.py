"""Unit tests for overlay module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specspectacle.executor.timeline import Timeline, TimelineEvent
from specspectacle.video.overlay import (
    POSITION_MAP,
    OverlayConfig,
    OverlayRenderer,
    OverlayTimestampCalculator,
    render_overlays_on_video,
)


class TestOverlayConfig:
    """Tests for OverlayConfig dataclass."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = OverlayConfig(text="Hello World")

        assert config.text == "Hello World"
        assert config.position == "bottom"
        assert config.start_time == 0.0
        assert config.duration == 2.0
        assert config.font_size == 22
        assert config.font_color == "#FFFFFF"
        assert config.background_color == "#000000AA"
        assert config.font_family == "Arial"

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = OverlayConfig(
            text="Custom Text",
            position="top-right",
            start_time=5.0,
            duration=3.5,
            font_size=36,
            font_color="#FF0000",
            background_color="#0000FF80",
            font_family="Helvetica",
        )

        assert config.text == "Custom Text"
        assert config.position == "top-right"
        assert config.start_time == 5.0
        assert config.duration == 3.5
        assert config.font_size == 36
        assert config.font_color == "#FF0000"
        assert config.background_color == "#0000FF80"
        assert config.font_family == "Helvetica"

    def test_invalid_position_raises_error(self):
        """Test that invalid position raises ValueError."""
        with pytest.raises(ValueError, match="Invalid position"):
            OverlayConfig(text="Test", position="invalid-position")

    def test_invalid_font_color_raises_error(self):
        """Test that invalid font color raises ValueError."""
        with pytest.raises(ValueError, match="Invalid font_color"):
            OverlayConfig(text="Test", font_color="not-a-color")

    def test_invalid_background_color_raises_error(self):
        """Test that invalid background color raises ValueError."""
        with pytest.raises(ValueError, match="Invalid background_color"):
            OverlayConfig(text="Test", background_color="invalid")

    def test_font_size_too_small(self):
        """Test that font size below 8 raises ValueError."""
        with pytest.raises(ValueError, match="Font size must be between"):
            OverlayConfig(text="Test", font_size=5)

    def test_font_size_too_large(self):
        """Test that font size above 200 raises ValueError."""
        with pytest.raises(ValueError, match="Font size must be between"):
            OverlayConfig(text="Test", font_size=250)

    def test_to_dict(self):
        """Test serialization to dictionary."""
        config = OverlayConfig(
            text="Test",
            position="center",
            start_time=1.5,
            duration=2.5,
        )

        d = config.to_dict()

        assert d["text"] == "Test"
        assert d["position"] == "center"
        assert d["start_time"] == 1.5
        assert d["duration"] == 2.5

    def test_all_valid_positions(self):
        """Test that all positions in POSITION_MAP are valid."""
        for position in POSITION_MAP.keys():
            config = OverlayConfig(text="Test", position=position)
            assert config.position == position

    def test_color_with_alpha(self):
        """Test that colors with alpha channel are valid."""
        config = OverlayConfig(
            text="Test",
            font_color="#FFFFFF",
            background_color="#000000AA",
        )
        assert config.font_color == "#FFFFFF"
        assert config.background_color == "#000000AA"


class TestPositionMap:
    """Tests for position mapping."""

    def test_all_nine_positions_exist(self):
        """Test all 9 position values are defined."""
        expected_positions = {
            "top",
            "bottom",
            "center",
            "top-left",
            "top-right",
            "bottom-left",
            "bottom-right",
            "left",
            "right",
        }

        assert set(POSITION_MAP.keys()) == expected_positions

    def test_positions_have_xy_expressions(self):
        """Test all positions have x and y expressions."""
        for position, (x_expr, y_expr) in POSITION_MAP.items():
            assert x_expr, f"Missing x expression for {position}"
            assert y_expr, f"Missing y expression for {position}"


class TestOverlayTimestampCalculator:
    """Tests for OverlayTimestampCalculator."""

    @pytest.fixture
    def mock_timeline(self):
        """Create a mock execution timeline."""
        timeline = Timeline(spec_name="test-spec")
        timeline.started_at = 0  # Set started_at for video-relative time conversion
        timeline.events = [
            TimelineEvent(
                step_name="Navigate",
                action="navigate",
                flow_index=1,
                step_index=1,
                start_time=0.0,
                end_time=2.0,
                duration=2.0,
                flow_name="Test Flow",
            ),
            TimelineEvent(
                step_name="Click",
                action="click",
                flow_index=1,
                step_index=2,
                start_time=2.0,
                end_time=3.0,
                duration=1.0,
                flow_name="Test Flow",
            ),
            TimelineEvent(
                step_name="Type",
                action="type",
                flow_index=1,
                step_index=3,
                start_time=3.0,
                end_time=5.0,
                duration=2.0,
                flow_name="Test Flow",
            ),
        ]
        return timeline

    @pytest.fixture
    def mock_spec(self):
        """Create a mock spec with overlays."""
        # Create mock overlay model
        overlay_mock = MagicMock()
        overlay_mock.text = "Test Overlay"
        overlay_mock.position = "bottom"
        overlay_mock.duration = 2.0
        overlay_mock.timing = "during"
        overlay_mock.offset = 0.0
        overlay_mock.style = MagicMock()
        overlay_mock.style.font_size = 22
        overlay_mock.style.text_color = "#FFFFFF"
        overlay_mock.style.background_color = "#000000AA"
        overlay_mock.style.font_family = "Arial"

        # Create mock step
        step_mock = MagicMock()
        step_mock.overlay = overlay_mock

        # Create mock flow
        flow_mock = MagicMock()
        flow_mock.name = "Test Flow"
        flow_mock.steps = [step_mock]

        # Create mock spec
        spec_mock = MagicMock()
        spec_mock.name = "Test Spec"
        spec_mock.flows = [flow_mock]

        return spec_mock

    def test_calculate_overlays(self, mock_spec, mock_timeline):
        """Test overlay calculation from spec and timeline."""
        overlays = OverlayTimestampCalculator.calculate_overlays(mock_spec, mock_timeline)

        assert len(overlays) == 1
        assert overlays[0].text == "Test Overlay"
        assert overlays[0].position == "bottom"
        assert overlays[0].start_time == 0.0  # First step starts at 0

    def test_calculate_start_time_during(self, mock_timeline):
        """Test start time calculation for 'during' timing."""
        event_lookup = {
            (1, 1): mock_timeline.events[0],
            (1, 2): mock_timeline.events[1],
        }

        start_time = OverlayTimestampCalculator._calculate_start_time(
            timing="during",
            offset=0.0,
            flow_index=1,
            step_index=2,
            event_lookup=event_lookup,
            timeline_start=0,
        )

        assert start_time == 2.0  # Second step starts at 2.0

    def test_calculate_start_time_before(self, mock_timeline):
        """Test start time calculation for 'before' timing."""
        event_lookup = {(1, 2): mock_timeline.events[1]}

        start_time = OverlayTimestampCalculator._calculate_start_time(
            timing="before",
            offset=0.0,
            flow_index=1,
            step_index=2,
            event_lookup=event_lookup,
            timeline_start=0,
        )

        # before = step_start - 0.5
        assert start_time == 1.5

    def test_calculate_start_time_after(self, mock_timeline):
        """Test start time calculation for 'after' timing."""
        event_lookup = {(1, 1): mock_timeline.events[0]}

        start_time = OverlayTimestampCalculator._calculate_start_time(
            timing="after",
            offset=0.0,
            flow_index=1,
            step_index=1,
            event_lookup=event_lookup,
            timeline_start=0,
        )

        assert start_time == 2.0  # First step ends at 2.0

    def test_calculate_start_time_with_offset(self, mock_timeline):
        """Test start time calculation with offset."""
        event_lookup = {(1, 1): mock_timeline.events[0]}

        start_time = OverlayTimestampCalculator._calculate_start_time(
            timing="during",
            offset=0.5,
            flow_index=1,
            step_index=1,
            event_lookup=event_lookup,
            timeline_start=0,
        )

        assert start_time == 0.5  # 0.0 + 0.5 offset


class TestOverlayRenderer:
    """Tests for OverlayRenderer."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def dummy_video(self, temp_dir):
        """Create a dummy video file for testing."""
        video_path = temp_dir / "test_video.mp4"
        video_path.write_bytes(b"dummy video content")
        return video_path

    @patch("specspectacle.video.overlay.check_ffmpeg_installed")
    def test_renderer_init_ffmpeg_not_installed(self, mock_check, temp_dir, dummy_video):
        """Test renderer raises error when FFmpeg not installed."""
        mock_check.return_value = False

        with pytest.raises(Exception):  # FFmpegNotFoundError
            OverlayRenderer(dummy_video, temp_dir)

    @patch("specspectacle.video.overlay.check_ffmpeg_installed")
    @patch("specspectacle.video.overlay.get_video_info")
    def test_renderer_init_video_not_found(self, mock_info, mock_check, temp_dir):
        """Test renderer raises error when video not found."""
        mock_check.return_value = True

        with pytest.raises(FileNotFoundError):
            OverlayRenderer(temp_dir / "nonexistent.mp4", temp_dir)

    @patch("specspectacle.video.overlay.check_ffmpeg_installed")
    @patch("specspectacle.video.overlay.get_video_info")
    def test_add_overlay(self, mock_info, mock_check, temp_dir, dummy_video):
        """Test adding overlays to renderer."""
        mock_check.return_value = True
        mock_info.return_value = {"width": 1280, "height": 720}

        renderer = OverlayRenderer(dummy_video, temp_dir)

        config = OverlayConfig(text="Test", start_time=1.0, duration=2.0)
        renderer.add_overlay(config)

        assert len(renderer.overlays) == 1
        assert renderer.overlays[0].text == "Test"

    @patch("specspectacle.video.overlay.check_ffmpeg_installed")
    @patch("specspectacle.video.overlay.get_video_info")
    def test_add_multiple_overlays(self, mock_info, mock_check, temp_dir, dummy_video):
        """Test adding multiple overlays."""
        mock_check.return_value = True
        mock_info.return_value = {"width": 1280, "height": 720}

        renderer = OverlayRenderer(dummy_video, temp_dir)

        configs = [
            OverlayConfig(text="First", start_time=0.0),
            OverlayConfig(text="Second", start_time=2.0),
            OverlayConfig(text="Third", start_time=4.0),
        ]
        renderer.add_overlays(configs)

        assert len(renderer.overlays) == 3

    @patch("specspectacle.video.overlay.check_ffmpeg_installed")
    @patch("specspectacle.video.overlay.get_video_info")
    def test_build_drawtext_filter(self, mock_info, mock_check, temp_dir, dummy_video):
        """Test building drawtext filter string."""
        mock_check.return_value = True
        mock_info.return_value = {"width": 1280, "height": 720}

        renderer = OverlayRenderer(dummy_video, temp_dir)
        config = OverlayConfig(
            text="Hello World",
            position="bottom",
            start_time=1.0,
            duration=2.0,
        )

        filter_str = renderer._build_drawtext_filter(config)

        assert "drawtext" in filter_str
        assert "Hello World" in filter_str
        assert "enable='between(t,1.00,3.00)'" in filter_str

    @patch("specspectacle.video.overlay.check_ffmpeg_installed")
    @patch("specspectacle.video.overlay.get_video_info")
    def test_escape_text(self, mock_info, mock_check, temp_dir, dummy_video):
        """Test text escaping for FFmpeg."""
        mock_check.return_value = True
        mock_info.return_value = {"width": 1280, "height": 720}

        renderer = OverlayRenderer(dummy_video, temp_dir)

        # Test colon escaping
        escaped = renderer._escape_text("Hello: World")
        assert "\\:" in escaped

        # Test single quote escaping (use '' for FFmpeg drawtext)
        escaped = renderer._escape_text("It's a test")
        assert "''" in escaped
        assert escaped == "It''s a test"

    @patch("specspectacle.video.overlay.check_ffmpeg_installed")
    @patch("specspectacle.video.overlay.get_video_info")
    def test_hex_to_ffmpeg_color(self, mock_info, mock_check, temp_dir, dummy_video):
        """Test hex color conversion."""
        mock_check.return_value = True
        mock_info.return_value = {"width": 1280, "height": 720}

        renderer = OverlayRenderer(dummy_video, temp_dir)

        assert renderer._hex_to_ffmpeg_color("#FFFFFF") == "FFFFFF"
        assert renderer._hex_to_ffmpeg_color("#000000") == "000000"

    @patch("specspectacle.video.overlay.check_ffmpeg_installed")
    @patch("specspectacle.video.overlay.get_video_info")
    def test_hex_to_ffmpeg_color_with_alpha(self, mock_info, mock_check, temp_dir, dummy_video):
        """Test hex color with alpha conversion."""
        mock_check.return_value = True
        mock_info.return_value = {"width": 1280, "height": 720}

        renderer = OverlayRenderer(dummy_video, temp_dir)

        color, alpha = renderer._hex_to_ffmpeg_color_with_alpha("#000000AA")
        assert color == "000000"
        assert abs(alpha - 0.667) < 0.01  # AA = 170/255 ≈ 0.667

        color, alpha = renderer._hex_to_ffmpeg_color_with_alpha("#FFFFFF")
        assert color == "FFFFFF"
        assert alpha == 1.0


class TestRenderOverlaysConvenienceFunction:
    """Tests for render_overlays_on_video convenience function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @patch("specspectacle.video.overlay.OverlayRenderer")
    def test_render_overlays_on_video(self, mock_renderer_class, temp_dir):
        """Test convenience function creates renderer and calls render."""
        mock_renderer = MagicMock()
        mock_renderer_class.return_value = mock_renderer
        mock_renderer.render.return_value = temp_dir / "output.mp4"

        video_path = temp_dir / "input.mp4"
        output_path = temp_dir / "output.mp4"
        overlays = [
            OverlayConfig(text="Test 1"),
            OverlayConfig(text="Test 2"),
        ]

        result = render_overlays_on_video(video_path, output_path, overlays)

        mock_renderer.add_overlays.assert_called_once_with(overlays)
        mock_renderer.render.assert_called_once_with(output_path)
