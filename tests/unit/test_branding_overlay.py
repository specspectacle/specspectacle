"""
Tests for branding overlay functionality.

This module contains unit tests for the LogoConfig dataclass and
OverlayRenderer enhancements for logo overlays.
"""


import pytest

from specspectacle.video.overlay import LOGO_POSITION_MAP, LogoConfig


class TestLogoConfig:
    """Tests for LogoConfig dataclass."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        logo = LogoConfig(logo_path="/path/to/logo.png")
        assert logo.logo_path == "/path/to/logo.png"
        assert logo.position == "top-left"
        assert logo.start_time == 0.0
        assert logo.duration == 2.0
        assert logo.scale == 0.15

    def test_custom_values(self):
        """Test that custom values are set correctly."""
        logo = LogoConfig(
            logo_path="/path/to/logo.png",
            position="bottom-right",
            start_time=5.0,
            duration=3.0,
            scale=0.25,
        )
        assert logo.logo_path == "/path/to/logo.png"
        assert logo.position == "bottom-right"
        assert logo.start_time == 5.0
        assert logo.duration == 3.0
        assert logo.scale == 0.25

    def test_valid_positions(self):
        """Test all valid logo positions."""
        for position in LOGO_POSITION_MAP.keys():
            logo = LogoConfig(logo_path="/path/to/logo.png", position=position)
            assert logo.position == position

    def test_invalid_position(self):
        """Test that invalid positions are rejected."""
        with pytest.raises(ValueError) as exc_info:
            LogoConfig(logo_path="/path/to/logo.png", position="center")
        assert "Invalid position" in str(exc_info.value)
        assert "top-left" in str(exc_info.value)

    def test_valid_scale_values(self):
        """Test valid scale values."""
        # Minimum scale
        logo = LogoConfig(logo_path="/path/to/logo.png", scale=0.01)
        assert logo.scale == 0.01

        # Maximum scale
        logo = LogoConfig(logo_path="/path/to/logo.png", scale=1.0)
        assert logo.scale == 1.0

        # Common scale values
        logo = LogoConfig(logo_path="/path/to/logo.png", scale=0.1)
        assert logo.scale == 0.1

        logo = LogoConfig(logo_path="/path/to/logo.png", scale=0.15)
        assert logo.scale == 0.15

        logo = LogoConfig(logo_path="/path/to/logo.png", scale=0.5)
        assert logo.scale == 0.5

    def test_invalid_scale_too_small(self):
        """Test that scale values below 0.01 are rejected."""
        with pytest.raises(ValueError) as exc_info:
            LogoConfig(logo_path="/path/to/logo.png", scale=0.001)
        assert "Scale must be between" in str(exc_info.value)

    def test_invalid_scale_too_large(self):
        """Test that scale values above 1.0 are rejected."""
        with pytest.raises(ValueError) as exc_info:
            LogoConfig(logo_path="/path/to/logo.png", scale=1.1)
        assert "Scale must be between" in str(exc_info.value)

    def test_to_dict(self):
        """Test serialization to dictionary."""
        logo = LogoConfig(
            logo_path="/path/to/logo.png",
            position="bottom-right",
            start_time=5.0,
            duration=3.0,
            scale=0.25,
        )
        data = logo.to_dict()
        assert data["logo_path"] == "/path/to/logo.png"
        assert data["position"] == "bottom-right"
        assert data["start_time"] == 5.0
        assert data["duration"] == 3.0
        assert data["scale"] == 0.25


class TestLogoPositionMap:
    """Tests for LOGO_POSITION_MAP."""

    def test_position_count(self):
        """Test that all 4 positions are defined."""
        assert len(LOGO_POSITION_MAP) == 4

    def test_position_expressions(self):
        """Test that position expressions are valid FFmpeg expressions."""
        # top-left: x=10, y=10
        x_expr, y_expr = LOGO_POSITION_MAP["top-left"]
        assert x_expr == "10"
        assert y_expr == "10"

        # top-right: x=w-logo_w-10, y=10
        x_expr, y_expr = LOGO_POSITION_MAP["top-right"]
        assert "w-logo_w" in x_expr
        assert y_expr == "10"

        # bottom-left: x=10, y=h-logo_h-10
        x_expr, y_expr = LOGO_POSITION_MAP["bottom-left"]
        assert x_expr == "10"
        assert "h-logo_h" in y_expr

        # bottom-right: x=w-logo_w-10, y=h-logo_h-10
        x_expr, y_expr = LOGO_POSITION_MAP["bottom-right"]
        assert "w-logo_w" in x_expr
        assert "h-logo_h" in y_expr


class TestLogoConfigValidation:
    """Tests for LogoConfig validation logic."""

    def test_logo_path_required(self):
        """Test that logo_path is required."""
        with pytest.raises(TypeError):
            LogoConfig()  # Missing required logo_path

    def test_logo_path_type(self):
        """Test that logo_path accepts any value (type checking is optional in Python)."""
        # Dataclasses don't enforce types by default, so this is allowed
        logo = LogoConfig(logo_path=123)  # type: ignore
        assert logo.logo_path == 123

    def test_position_type(self):
        """Test that position must be a string."""
        logo = LogoConfig(logo_path="/path/to/logo.png", position="top-left")
        assert isinstance(logo.position, str)

    def test_start_time_type(self):
        """Test that start_time must be a number."""
        logo = LogoConfig(logo_path="/path/to/logo.png", start_time=0.0)
        assert isinstance(logo.start_time, float)

    def test_duration_type(self):
        """Test that duration must be a number."""
        logo = LogoConfig(logo_path="/path/to/logo.png", duration=2.0)
        assert isinstance(logo.duration, float)

    def test_scale_type(self):
        """Test that scale must be a number."""
        logo = LogoConfig(logo_path="/path/to/logo.png", scale=0.15)
        assert isinstance(logo.scale, float)
