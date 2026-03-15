"""
Tests for branding schema models.

This module contains unit tests for the BrandingModel and BrandingColorsModel
classes in specspectacle.parser.schema.
"""

import pytest
from pydantic import ValidationError

from specspectacle.parser.schema import BrandingColorsModel, BrandingModel


class TestBrandingColorsModel:
    """Tests for BrandingColorsModel."""

    def test_default_values(self):
        """Test that default color values are set correctly."""
        colors = BrandingColorsModel()
        assert colors.primary == "#3B82F6"
        assert colors.background == "#000000"
        assert colors.text == "#FFFFFF"

    def test_custom_values(self):
        """Test that custom color values are set correctly."""
        colors = BrandingColorsModel(
            primary="#FF0000",
            background="#00FF00",
            text="#0000FF",
        )
        assert colors.primary == "#FF0000"
        assert colors.background == "#00FF00"
        assert colors.text == "#0000FF"

    def test_valid_hex_colors(self):
        """Test various valid hex color formats."""
        # 3-digit hex
        colors = BrandingColorsModel(primary="#F00", background="#0F0", text="#00F")
        assert colors.primary == "#F00"

        # 4-digit hex (with alpha)
        colors = BrandingColorsModel(primary="#F008", background="#0F08", text="#00F8")
        assert colors.primary == "#F008"

        # 6-digit hex
        colors = BrandingColorsModel(primary="#FF0000", background="#00FF00", text="#0000FF")
        assert colors.primary == "#FF0000"

        # 8-digit hex (with alpha)
        colors = BrandingColorsModel(primary="#FF000080", background="#00FF0080", text="#0000FF80")
        assert colors.primary == "#FF000080"

    def test_invalid_hex_color_too_short(self):
        """Test that colors with too few digits are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BrandingColorsModel(primary="#FF")
        assert "Invalid hex color" in str(exc_info.value)

    def test_invalid_hex_color_too_long(self):
        """Test that colors with too many digits are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BrandingColorsModel(primary="#FF00000")
        assert "Invalid hex color" in str(exc_info.value)

    def test_invalid_hex_color_invalid_chars(self):
        """Test that colors with invalid characters are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BrandingColorsModel(primary="#GGGGGG")
        assert "Invalid hex color" in str(exc_info.value)

    def test_invalid_hex_color_missing_hash(self):
        """Test that colors without hash prefix are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BrandingColorsModel(primary="FF0000")
        assert "Invalid hex color" in str(exc_info.value)

    def test_case_insensitive_hex(self):
        """Test that hex colors are case-insensitive."""
        colors = BrandingColorsModel(primary="#ff0000", background="#00ff00", text="#0000ff")
        assert colors.primary == "#ff0000"

        colors = BrandingColorsModel(primary="#FF0000", background="#00FF00", text="#0000FF")
        assert colors.primary == "#FF0000"


class TestBrandingModel:
    """Tests for BrandingModel."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        branding = BrandingModel()
        assert branding.logo is None
        assert isinstance(branding.colors, BrandingColorsModel)
        assert branding.colors.primary == "#3B82F6"

    def test_with_logo_only(self):
        """Test branding with only logo specified."""
        branding = BrandingModel(logo="/path/to/logo.png")
        assert branding.logo == "/path/to/logo.png"
        assert isinstance(branding.colors, BrandingColorsModel)

    def test_with_colors_only(self):
        """Test branding with only colors specified."""
        branding = BrandingModel(
            colors=BrandingColorsModel(
                primary="#FF0000",
                background="#000000",
                text="#FFFFFF",
            )
        )
        assert branding.logo is None
        assert branding.colors.primary == "#FF0000"

    def test_with_logo_and_colors(self):
        """Test branding with both logo and colors specified."""
        branding = BrandingModel(
            logo="/path/to/logo.png",
            colors=BrandingColorsModel(
                primary="#FF0000",
                background="#000000",
                text="#FFFFFF",
            ),
        )
        assert branding.logo == "/path/to/logo.png"
        assert branding.colors.primary == "#FF0000"
        assert branding.colors.background == "#000000"
        assert branding.colors.text == "#FFFFFF"

    def test_logo_none_explicit(self):
        """Test that logo can be explicitly set to None."""
        branding = BrandingModel(logo=None)
        assert branding.logo is None

    def test_colors_default_factory(self):
        """Test that colors uses default factory."""
        branding1 = BrandingModel()
        branding2 = BrandingModel()
        # Each instance should have its own colors object
        assert branding1.colors is not branding2.colors

    def test_invalid_logo_path(self):
        """Test that any string is accepted as logo path (validation is at runtime)."""
        # Logo path validation happens at runtime when the file is accessed
        branding = BrandingModel(logo="/nonexistent/path/logo.png")
        assert branding.logo == "/nonexistent/path/logo.png"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        branding = BrandingModel(
            logo="/path/to/logo.png",
            colors=BrandingColorsModel(
                primary="#FF0000",
                background="#000000",
                text="#FFFFFF",
            ),
        )
        data = branding.model_dump()
        assert data["logo"] == "/path/to/logo.png"
        assert data["colors"]["primary"] == "#FF0000"
        assert data["colors"]["background"] == "#000000"
        assert data["colors"]["text"] == "#FFFFFF"

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "logo": "/path/to/logo.png",
            "colors": {
                "primary": "#FF0000",
                "background": "#000000",
                "text": "#FFFFFF",
            },
        }
        branding = BrandingModel(**data)
        assert branding.logo == "/path/to/logo.png"
        assert branding.colors.primary == "#FF0000"
        assert branding.colors.background == "#000000"
        assert branding.colors.text == "#FFFFFF"
