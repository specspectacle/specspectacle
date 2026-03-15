"""
Tests for branding timeline functionality.

This module contains unit tests for the BrandingSegment dataclass
and Timeline enhancements for branding segments.
"""

from specspectacle.executor.timeline import BrandingSegment, Timeline


class TestBrandingSegment:
    """Tests for BrandingSegment dataclass."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        segment = BrandingSegment(
            segment_type="intro",
            start_time=0.0,
            duration=2.0,
        )
        assert segment.segment_type == "intro"
        assert segment.start_time == 0.0
        assert segment.duration == 2.0
        assert segment.logo_path is None
        assert segment.logo_position == "top-left"
        assert segment.logo_scale == 0.15
        assert segment.primary_color == "#3B82F6"
        assert segment.background_color == "#000000"
        assert segment.text_color == "#FFFFFF"
        assert segment.title == ""

    def test_custom_values(self):
        """Test that custom values are set correctly."""
        segment = BrandingSegment(
            segment_type="outro",
            start_time=10.0,
            duration=3.0,
            logo_path="/path/to/logo.png",
            logo_position="bottom-right",
            logo_scale=0.2,
            primary_color="#FF0000",
            background_color="#000000",
            text_color="#FFFFFF",
            title="Thanks for watching!",
        )
        assert segment.segment_type == "outro"
        assert segment.start_time == 10.0
        assert segment.duration == 3.0
        assert segment.logo_path == "/path/to/logo.png"
        assert segment.logo_position == "bottom-right"
        assert segment.logo_scale == 0.2
        assert segment.primary_color == "#FF0000"
        assert segment.background_color == "#000000"
        assert segment.text_color == "#FFFFFF"
        assert segment.title == "Thanks for watching!"

    def test_intro_type(self):
        """Test that 'intro' is a valid segment type."""
        segment = BrandingSegment(segment_type="intro", start_time=0.0, duration=2.0)
        assert segment.segment_type == "intro"

    def test_outro_type(self):
        """Test that 'outro' is a valid segment type."""
        segment = BrandingSegment(segment_type="outro", start_time=10.0, duration=3.0)
        assert segment.segment_type == "outro"

    def test_invalid_segment_type(self):
        """Test that invalid segment types are accepted (type checking is optional in Python)."""
        # Dataclasses don't enforce types by default, so this is allowed
        # The Literal type is for documentation and IDE support
        segment = BrandingSegment(segment_type="invalid", start_time=0.0, duration=2.0)  # type: ignore
        assert segment.segment_type == "invalid"

    def test_logo_path_optional(self):
        """Test that logo_path is optional."""
        segment = BrandingSegment(segment_type="intro", start_time=0.0, duration=2.0)
        assert segment.logo_path is None

    def test_logo_position_default(self):
        """Test that logo_position defaults to top-left."""
        segment = BrandingSegment(segment_type="intro", start_time=0.0, duration=2.0)
        assert segment.logo_position == "top-left"

    def test_logo_scale_default(self):
        """Test that logo_scale defaults to 0.15."""
        segment = BrandingSegment(segment_type="intro", start_time=0.0, duration=2.0)
        assert segment.logo_scale == 0.15

    def test_colors_default(self):
        """Test that color defaults are set correctly."""
        segment = BrandingSegment(segment_type="intro", start_time=0.0, duration=2.0)
        assert segment.primary_color == "#3B82F6"
        assert segment.background_color == "#000000"
        assert segment.text_color == "#FFFFFF"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        segment = BrandingSegment(
            segment_type="intro",
            start_time=0.0,
            duration=2.0,
            logo_path="/path/to/logo.png",
            logo_position="top-right",
            logo_scale=0.2,
            primary_color="#FF0000",
            background_color="#000000",
            text_color="#FFFFFF",
            title="Welcome!",
        )
        data = segment.to_dict()
        assert data["segment_type"] == "intro"
        assert data["start_time"] == 0.0
        assert data["duration"] == 2.0
        assert data["logo_path"] == "/path/to/logo.png"
        assert data["logo_position"] == "top-right"
        assert data["logo_scale"] == 0.2
        assert data["primary_color"] == "#FF0000"
        assert data["background_color"] == "#000000"
        assert data["text_color"] == "#FFFFFF"
        assert data["title"] == "Welcome!"


class TestTimelineBranding:
    """Tests for Timeline branding segment methods."""

    def test_empty_branding_segments(self):
        """Test that empty timeline has no branding segments."""
        timeline = Timeline(spec_name="test")
        assert timeline.get_intro_segment() is None
        assert timeline.get_outro_segment() is None

    def test_add_intro_segment(self):
        """Test adding an intro segment."""
        timeline = Timeline(spec_name="test")
        segment = BrandingSegment(
            segment_type="intro",
            start_time=0.0,
            duration=2.0,
        )
        timeline.add_branding_segment(segment)
        assert timeline.get_intro_segment() == segment
        assert timeline.get_outro_segment() is None

    def test_add_outro_segment(self):
        """Test adding an outro segment."""
        timeline = Timeline(spec_name="test")
        segment = BrandingSegment(
            segment_type="outro",
            start_time=10.0,
            duration=3.0,
        )
        timeline.add_branding_segment(segment)
        assert timeline.get_intro_segment() is None
        assert timeline.get_outro_segment() == segment

    def test_add_both_segments(self):
        """Test adding both intro and outro segments."""
        timeline = Timeline(spec_name="test")
        intro = BrandingSegment(segment_type="intro", start_time=0.0, duration=2.0)
        outro = BrandingSegment(segment_type="outro", start_time=10.0, duration=3.0)
        timeline.add_branding_segment(intro)
        timeline.add_branding_segment(outro)
        assert timeline.get_intro_segment() == intro
        assert timeline.get_outro_segment() == outro

    def test_multiple_intro_segments(self):
        """Test that get_intro_segment returns the first intro segment."""
        timeline = Timeline(spec_name="test")
        intro1 = BrandingSegment(segment_type="intro", start_time=0.0, duration=2.0)
        intro2 = BrandingSegment(segment_type="intro", start_time=5.0, duration=2.0)
        timeline.add_branding_segment(intro1)
        timeline.add_branding_segment(intro2)
        assert timeline.get_intro_segment() == intro1
        assert timeline.get_outro_segment() is None

    def test_multiple_outro_segments(self):
        """Test that get_outro_segment returns the first outro segment."""
        timeline = Timeline(spec_name="test")
        outro1 = BrandingSegment(segment_type="outro", start_time=10.0, duration=3.0)
        outro2 = BrandingSegment(segment_type="outro", start_time=15.0, duration=3.0)
        timeline.add_branding_segment(outro1)
        timeline.add_branding_segment(outro2)
        assert timeline.get_outro_segment() == outro1

    def test_branding_segments_list(self):
        """Test that branding_segments list is maintained."""
        timeline = Timeline(spec_name="test")
        intro = BrandingSegment(segment_type="intro", start_time=0.0, duration=2.0)
        outro = BrandingSegment(segment_type="outro", start_time=10.0, duration=3.0)
        timeline.add_branding_segment(intro)
        timeline.add_branding_segment(outro)
        assert len(timeline.branding_segments) == 2
        assert timeline.branding_segments[0] == intro
        assert timeline.branding_segments[1] == outro

    def test_branding_segments_empty(self):
        """Test that branding_segments list is empty by default."""
        timeline = Timeline(spec_name="test")
        assert len(timeline.branding_segments) == 0

    def test_branding_segment_with_logo(self):
        """Test branding segment with logo configuration."""
        timeline = Timeline(spec_name="test")
        segment = BrandingSegment(
            segment_type="intro",
            start_time=0.0,
            duration=2.0,
            logo_path="/path/to/logo.png",
            logo_position="top-right",
            logo_scale=0.2,
        )
        timeline.add_branding_segment(segment)
        retrieved = timeline.get_intro_segment()
        assert retrieved is not None
        assert retrieved.logo_path == "/path/to/logo.png"
        assert retrieved.logo_position == "top-right"
        assert retrieved.logo_scale == 0.2

    def test_branding_segment_with_colors(self):
        """Test branding segment with custom colors."""
        timeline = Timeline(spec_name="test")
        segment = BrandingSegment(
            segment_type="intro",
            start_time=0.0,
            duration=2.0,
            primary_color="#FF0000",
            background_color="#000000",
            text_color="#FFFFFF",
        )
        timeline.add_branding_segment(segment)
        retrieved = timeline.get_intro_segment()
        assert retrieved is not None
        assert retrieved.primary_color == "#FF0000"
        assert retrieved.background_color == "#000000"
        assert retrieved.text_color == "#FFFFFF"
