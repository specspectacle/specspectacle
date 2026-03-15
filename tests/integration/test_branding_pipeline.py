"""
Integration tests for branding pipeline.

This module contains integration tests for the complete branding pipeline,
testing the interaction between schema, timeline, and video rendering.
"""

from unittest.mock import patch

from specspectacle.executor.timeline import BrandingSegment, Timeline
from specspectacle.parser.schema import BrandingColorsModel, BrandingModel, ConfigModel
from specspectacle.video.overlay import LOGO_POSITION_MAP, LogoConfig


class TestBrandingPipelineIntegration:
    """Integration tests for the complete branding pipeline."""

    def test_schema_to_timeline_conversion(self):
        """Test converting schema branding to timeline branding segments."""
        # Create branding config from schema
        branding_config = BrandingModel(
            logo="/path/to/logo.png",
            colors=BrandingColorsModel(
                primary="#FF0000",
                background="#000000",
                text="#FFFFFF",
            ),
        )

        # Create timeline with branding segments
        timeline = Timeline(spec_name="test-spec")

        # Convert schema to timeline segments
        intro_segment = BrandingSegment(
            segment_type="intro",
            start_time=0.0,
            duration=2.0,
            logo_path=branding_config.logo,
            logo_position="top-left",
            logo_scale=0.15,
            primary_color=branding_config.colors.primary,
            background_color=branding_config.colors.background,
            text_color=branding_config.colors.text,
        )
        timeline.add_branding_segment(intro_segment)

        # Verify conversion
        retrieved = timeline.get_intro_segment()
        assert retrieved is not None
        assert retrieved.logo_path == branding_config.logo
        assert retrieved.primary_color == branding_config.colors.primary
        assert retrieved.background_color == branding_config.colors.background
        assert retrieved.text_color == branding_config.colors.text

    def test_timeline_to_logo_config_conversion(self):
        """Test converting timeline branding segments to LogoConfig."""
        # Create timeline with branding segment
        timeline = Timeline(spec_name="test-spec")
        segment = BrandingSegment(
            segment_type="intro",
            start_time=0.0,
            duration=2.0,
            logo_path="/path/to/logo.png",
            logo_position="bottom-right",
            logo_scale=0.2,
        )
        timeline.add_branding_segment(segment)

        # Convert to LogoConfig
        logo_config = LogoConfig(
            logo_path=segment.logo_path,
            position=segment.logo_position,
            start_time=segment.start_time,
            duration=segment.duration,
            scale=segment.logo_scale,
        )

        # Verify conversion
        assert logo_config.logo_path == segment.logo_path
        assert logo_config.position == segment.logo_position
        assert logo_config.start_time == segment.start_time
        assert logo_config.duration == segment.duration
        assert logo_config.scale == segment.logo_scale

    def test_logo_position_mapping(self):
        """Test that logo positions map correctly to FFmpeg expressions."""
        # Verify all positions have valid expressions
        for position in LOGO_POSITION_MAP.keys():
            x_expr, y_expr = LOGO_POSITION_MAP[position]
            # Expressions should contain valid FFmpeg syntax
            assert isinstance(x_expr, str)
            assert isinstance(y_expr, str)
            assert len(x_expr) > 0
            assert len(y_expr) > 0

    def test_config_model_with_branding(self):
        """Test ConfigModel with branding configuration."""
        config = ConfigModel(
            target_app="https://example.com",
            branding=BrandingModel(
                logo="/path/to/logo.png",
                colors=BrandingColorsModel(
                    primary="#FF0000",
                    background="#000000",
                    text="#FFFFFF",
                ),
            ),
        )

        assert config.branding is not None
        assert config.branding.logo == "/path/to/logo.png"
        assert config.branding.colors.primary == "#FF0000"

    def test_config_model_without_branding(self):
        """Test ConfigModel without branding configuration."""
        config = ConfigModel(
            target_app="https://example.com",
        )

        assert config.branding is None

    def test_branding_segment_to_dict_roundtrip(self):
        """Test that BrandingSegment can be serialized and deserialized."""
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

        # Serialize
        data = segment.to_dict()

        # Deserialize
        restored = BrandingSegment(**data)

        # Verify
        assert restored.segment_type == segment.segment_type
        assert restored.start_time == segment.start_time
        assert restored.duration == segment.duration
        assert restored.logo_path == segment.logo_path
        assert restored.logo_position == segment.logo_position
        assert restored.logo_scale == segment.logo_scale
        assert restored.primary_color == segment.primary_color
        assert restored.background_color == segment.background_color
        assert restored.text_color == segment.text_color
        assert restored.title == segment.title

    def test_logo_config_to_dict_roundtrip(self):
        """Test that LogoConfig can be serialized and deserialized."""
        logo = LogoConfig(
            logo_path="/path/to/logo.png",
            position="bottom-left",
            start_time=5.0,
            duration=3.0,
            scale=0.25,
        )

        # Serialize
        data = logo.to_dict()

        # Deserialize
        restored = LogoConfig(**data)

        # Verify
        assert restored.logo_path == logo.logo_path
        assert restored.position == logo.position
        assert restored.start_time == logo.start_time
        assert restored.duration == logo.duration
        assert restored.scale == logo.scale

    def test_multiple_branding_segments_in_timeline(self):
        """Test handling multiple branding segments in a timeline."""
        timeline = Timeline(spec_name="test-spec")

        # Add intro
        intro = BrandingSegment(
            segment_type="intro",
            start_time=0.0,
            duration=2.0,
            logo_path="/path/to/logo.png",
        )
        timeline.add_branding_segment(intro)

        # Add outro
        outro = BrandingSegment(
            segment_type="outro",
            start_time=10.0,
            duration=3.0,
            logo_path="/path/to/logo.png",
        )
        timeline.add_branding_segment(outro)

        # Verify both segments are accessible
        assert timeline.get_intro_segment() == intro
        assert timeline.get_outro_segment() == outro
        assert len(timeline.branding_segments) == 2

    def test_branding_with_different_positions(self):
        """Test branding segments with different logo positions."""
        timeline = Timeline(spec_name="test-spec")

        # Intro with top-left logo
        intro = BrandingSegment(
            segment_type="intro",
            start_time=0.0,
            duration=2.0,
            logo_position="top-left",
        )
        timeline.add_branding_segment(intro)

        # Outro with bottom-right logo
        outro = BrandingSegment(
            segment_type="outro",
            start_time=10.0,
            duration=3.0,
            logo_position="bottom-right",
        )
        timeline.add_branding_segment(outro)

        assert timeline.get_intro_segment().logo_position == "top-left"
        assert timeline.get_outro_segment().logo_position == "bottom-right"

    def test_branding_with_different_scales(self):
        """Test branding segments with different logo scales."""
        timeline = Timeline(spec_name="test-spec")

        # Small logo
        intro = BrandingSegment(
            segment_type="intro",
            start_time=0.0,
            duration=2.0,
            logo_scale=0.1,
        )
        timeline.add_branding_segment(intro)

        # Large logo
        outro = BrandingSegment(
            segment_type="outro",
            start_time=10.0,
            duration=3.0,
            logo_scale=0.3,
        )
        timeline.add_branding_segment(outro)

        assert timeline.get_intro_segment().logo_scale == 0.1
        assert timeline.get_outro_segment().logo_scale == 0.3

    def test_branding_with_different_durations(self):
        """Test branding segments with different durations."""
        timeline = Timeline(spec_name="test-spec")

        # Short intro
        intro = BrandingSegment(
            segment_type="intro",
            start_time=0.0,
            duration=1.0,
        )
        timeline.add_branding_segment(intro)

        # Long outro
        outro = BrandingSegment(
            segment_type="outro",
            start_time=10.0,
            duration=5.0,
        )
        timeline.add_branding_segment(outro)

        assert timeline.get_intro_segment().duration == 1.0
        assert timeline.get_outro_segment().duration == 5.0

    def test_branding_with_custom_colors(self):
        """Test branding segments with custom color schemes."""
        timeline = Timeline(spec_name="test-spec")

        # Red theme
        intro = BrandingSegment(
            segment_type="intro",
            start_time=0.0,
            duration=2.0,
            primary_color="#FF0000",
            background_color="#000000",
            text_color="#FFFFFF",
        )
        timeline.add_branding_segment(intro)

        # Blue theme
        outro = BrandingSegment(
            segment_type="outro",
            start_time=10.0,
            duration=3.0,
            primary_color="#0000FF",
            background_color="#FFFFFF",
            text_color="#000000",
        )
        timeline.add_branding_segment(outro)

        assert timeline.get_intro_segment().primary_color == "#FF0000"
        assert timeline.get_outro_segment().primary_color == "#0000FF"

    @patch('pathlib.Path.exists')
    def test_logo_config_validation_with_mock_path(self, mock_exists):
        """Test LogoConfig validation with mocked path existence."""
        mock_exists.return_value = True

        # Valid logo config
        logo = LogoConfig(
            logo_path="/path/to/logo.png",
            position="top-left",
            start_time=0.0,
            duration=2.0,
            scale=0.15,
        )

        assert logo.logo_path == "/path/to/logo.png"
        assert logo.position == "top-left"

    def test_branding_pipeline_data_flow(self):
        """Test the complete data flow from schema to timeline to overlay config."""
        # Step 1: Schema level
        schema_branding = BrandingModel(
            logo="/path/to/logo.png",
            colors=BrandingColorsModel(
                primary="#FF0000",
                background="#000000",
                text="#FFFFFF",
            ),
        )

        # Step 2: Timeline level
        timeline = Timeline(spec_name="test-spec")
        timeline_segment = BrandingSegment(
            segment_type="intro",
            start_time=0.0,
            duration=2.0,
            logo_path=schema_branding.logo,
            logo_position="top-left",
            logo_scale=0.15,
            primary_color=schema_branding.colors.primary,
            background_color=schema_branding.colors.background,
            text_color=schema_branding.colors.text,
        )
        timeline.add_branding_segment(timeline_segment)

        # Step 3: Overlay level
        logo_config = LogoConfig(
            logo_path=timeline_segment.logo_path,
            position=timeline_segment.logo_position,
            start_time=timeline_segment.start_time,
            duration=timeline_segment.duration,
            scale=timeline_segment.logo_scale,
        )

        # Verify data flow
        assert logo_config.logo_path == schema_branding.logo
        assert logo_config.position == "top-left"
        assert logo_config.start_time == 0.0
        assert logo_config.duration == 2.0
        assert logo_config.scale == 0.15
