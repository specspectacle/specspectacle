"""
Text overlay rendering for videos using FFmpeg drawtext filter.

This module provides classes for calculating overlay positions and timestamps,
and rendering text overlays on video using FFmpeg's drawtext filter.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from specspectacle.executor.timeline import Timeline, TimelineEvent
from specspectacle.video.ffmpeg_utils import (
    FFmpegExecutionError,
    check_ffmpeg_installed,
    get_video_info,
)

logger = logging.getLogger(__name__)


# Position mapping: name -> (x_expression, y_expression)
# Expressions use FFmpeg syntax with w=video_width, h=video_height, tw=text_width, th=text_height
# Note: y coordinate is the TOP of the text box, so we add padding for 'top' positions
POSITION_MAP = {
    "top": ("(w-tw)/2", "20"),  # 20px from top, centered horizontally
    "bottom": ("(w-tw)/2", "h-th-30"),  # 30px from bottom (accounting for box padding)
    "center": ("(w-tw)/2", "(h-th)/2"),
    "top-left": ("20", "20"),  # 20px from top-left corner
    "top-right": ("w-tw-20", "20"),  # 20px from top-right corner
    "bottom-left": ("20", "h-th-30"),
    "bottom-right": ("w-tw-20", "h-th-30"),
    "left": ("20", "(h-th)/2"),
    "right": ("w-tw-20", "(h-th)/2"),
}


@dataclass
class OverlayConfig:
    """
    Configuration for a single text overlay.

    Attributes:
        text: The text to display
        position: Position on screen (top, bottom, center, top-left, etc.)
        start_time: When to start showing the overlay (seconds)
        duration: How long to show the overlay (seconds)
        font_size: Font size in pixels
        font_color: Text color (hex format, e.g., "#FFFFFF")
        background_color: Background color with alpha (e.g., "#000000AA")
        font_family: Font family name (default: Arial)
    """

    text: str
    position: str = "bottom"
    start_time: float = 0.0
    duration: float = 2.0
    font_size: int = 22
    font_color: str = "#FFFFFF"
    background_color: str = "#000000AA"
    font_family: str = "Arial"

    def __post_init__(self):
        """Validate overlay configuration."""
        # Validate position
        if self.position not in POSITION_MAP:
            valid_positions = ", ".join(POSITION_MAP.keys())
            raise ValueError(
                f"Invalid position '{self.position}'. Valid positions: {valid_positions}"
            )

        # Validate colors
        if not self._is_valid_color(self.font_color):
            raise ValueError(f"Invalid font_color: {self.font_color}")
        if not self._is_valid_color(self.background_color):
            raise ValueError(f"Invalid background_color: {self.background_color}")

        # Validate font size
        if not 8 <= self.font_size <= 200:
            raise ValueError(f"Font size must be between 8 and 200, got {self.font_size}")

    @staticmethod
    def _is_valid_color(color: str) -> bool:
        """Check if color is a valid hex color (with optional alpha)."""
        pattern = r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$"
        return bool(re.match(pattern, color))

    @classmethod
    def from_overlay_model(
        cls,
        overlay_model: Any,  # OverlayModel from parser.schema
        start_time: float,
        branding_colors: dict[str, str] | None = None,
        apply_branding: bool = True,
    ) -> "OverlayConfig":
        """
        Create OverlayConfig from a parsed OverlayModel.

        Args:
            overlay_model: OverlayModel from the schema
            start_time: Calculated start time for this overlay
            branding_colors: Optional dict with 'background' and 'text' keys for branding colors
            apply_branding: Whether to apply branding colors when style is not specified

        Returns:
            OverlayConfig with extracted values
        """
        style = overlay_model.style if hasattr(overlay_model, "style") else None

        # Default style values (from OverlayStyleModel)
        DEFAULT_BACKGROUND = "#000000AA"
        DEFAULT_TEXT = "#FFFFFF"
        DEFAULT_FONT_SIZE = 22
        DEFAULT_FONT_FAMILY = "Arial"

        # Determine colors - use style if explicitly specified, otherwise use branding colors if available
        if style:
            # Check if style has default values (meaning it wasn't explicitly set)
            is_default_style = (
                style.background_color == DEFAULT_BACKGROUND and
                style.text_color == DEFAULT_TEXT and
                style.font_size == DEFAULT_FONT_SIZE and
                style.font_family == DEFAULT_FONT_FAMILY
            )

            if is_default_style:
                # Style has defaults, check if we should apply branding
                if branding_colors and apply_branding:
                    font_color = branding_colors.get("text", DEFAULT_TEXT)
                    bg_color = branding_colors.get("background", "#000000")
                    background_color = bg_color + "CC"  # Add 80% opacity
                    font_size = DEFAULT_FONT_SIZE
                    font_family = DEFAULT_FONT_FAMILY
                else:
                    # No branding, use defaults
                    font_color = DEFAULT_TEXT
                    background_color = DEFAULT_BACKGROUND
                    font_size = DEFAULT_FONT_SIZE
                    font_family = DEFAULT_FONT_FAMILY
            else:
                # Style explicitly specified, use those colors
                font_color = style.text_color
                background_color = style.background_color
                font_size = style.font_size
                font_family = style.font_family
        else:
            # No style at all, use branding or defaults
            if branding_colors and apply_branding:
                font_color = branding_colors.get("text", DEFAULT_TEXT)
                bg_color = branding_colors.get("background", "#000000")
                background_color = bg_color + "CC"  # Add 80% opacity
                font_size = DEFAULT_FONT_SIZE
                font_family = DEFAULT_FONT_FAMILY
            else:
                font_color = DEFAULT_TEXT
                background_color = DEFAULT_BACKGROUND
                font_size = DEFAULT_FONT_SIZE
                font_family = DEFAULT_FONT_FAMILY

        return cls(
            text=overlay_model.text,
            position=overlay_model.position,
            start_time=start_time,
            duration=overlay_model.duration,
            font_size=font_size,
            font_color=font_color,
            background_color=background_color,
            font_family=font_family,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "position": self.position,
            "start_time": self.start_time,
            "duration": self.duration,
            "font_size": self.font_size,
            "font_color": self.font_color,
            "background_color": self.background_color,
            "font_family": self.font_family,
        }


# Logo position mapping: name -> (x_expression, y_expression)
# Expressions use FFmpeg syntax with main_w=video_width, main_h=video_height, overlay_w=logo_width, overlay_h=logo_height
LOGO_POSITION_MAP = {
    "top-left": ("10", "10"),
    "top-right": ("main_w-overlay_w-10", "10"),
    "bottom-left": ("10", "main_h-overlay_h-10"),
    "bottom-right": ("main_w-overlay_w-10", "main_h-overlay_h-10"),
}


@dataclass
class LogoConfig:
    """
    Configuration for a logo overlay.

    Attributes:
        logo_path: Path to the logo image file
        position: Position on screen (top-left, top-right, bottom-left, bottom-right)
        start_time: When to start showing the logo (seconds)
        duration: How long to show the logo (seconds)
        scale: Scale factor for the logo (e.g., 0.1 for 10% of video width)
    """

    logo_path: str
    position: str = "top-left"
    start_time: float = 0.0
    duration: float = 2.0
    scale: float = 0.15

    def __post_init__(self):
        """Validate logo configuration."""
        # Validate position
        if self.position not in LOGO_POSITION_MAP:
            valid_positions = ", ".join(LOGO_POSITION_MAP.keys())
            raise ValueError(
                f"Invalid position '{self.position}'. Valid positions: {valid_positions}"
            )

        # Validate scale
        if not 0.01 <= self.scale <= 1.0:
            raise ValueError(f"Scale must be between 0.01 and 1.0, got {self.scale}")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "logo_path": self.logo_path,
            "position": self.position,
            "start_time": self.start_time,
            "duration": self.duration,
            "scale": self.scale,
        }


class OverlayTimestampCalculator:
    """
    Calculates overlay timestamps from the execution timeline.
    """

    @classmethod
    def calculate_overlays(
        cls,
        spec: Any,  # SpecModel from parser.schema
        execution_timeline: Timeline,
        branding_config: Any | None = None,  # BrandingModel from parser.schema
    ) -> list[OverlayConfig]:
        """
        Extract and calculate timings for all overlays in a spec.

        Args:
            spec: Parsed SpecModel with flows and steps
            execution_timeline: Timeline from browser execution
            branding_config: Optional BrandingModel for applying brand colors

        Returns:
            List of OverlayConfig with calculated start times (video-relative)
        """
        overlays = []

        # Get branding colors if available
        branding_colors = None
        apply_branding = True
        if branding_config and hasattr(branding_config, "colors"):
            branding_colors = {
                "background": branding_config.colors.background,
                "text": branding_config.colors.text,
            }
            apply_branding = getattr(branding_config, "apply_to_overlays", True)

        # Get timeline start time for converting to video-relative timestamps
        # Timeline events store absolute Unix timestamps, but overlays need
        # video-relative times (0.0, 1.5, 3.0 seconds from start of video)
        timeline_start = execution_timeline.started_at or 0

        # Build event lookup
        event_lookup: dict[tuple, TimelineEvent] = {}
        for event in execution_timeline.events:
            key = (event.flow_index, event.step_index)
            event_lookup[key] = event

        # Process each flow and step
        for flow_idx, flow in enumerate(spec.flows, start=1):
            for step_idx, step in enumerate(flow.steps, start=1):
                if hasattr(step, "overlay") and step.overlay:
                    overlay_model = step.overlay

                    # Calculate start time based on timing (video-relative)
                    start_time = cls._calculate_start_time(
                        timing=overlay_model.timing,
                        offset=getattr(overlay_model, "offset", 0.0),
                        flow_index=flow_idx,
                        step_index=step_idx,
                        event_lookup=event_lookup,
                        timeline_start=timeline_start,
                    )

                    config = OverlayConfig.from_overlay_model(
                        overlay_model, start_time, branding_colors, apply_branding
                    )
                    overlays.append(config)

        return overlays

    @classmethod
    def _calculate_start_time(
        cls,
        timing: str,
        offset: float,
        flow_index: int,
        step_index: int,
        event_lookup: dict[tuple, TimelineEvent],
        timeline_start: float,
    ) -> float:
        """
        Calculate video-relative start time for an overlay.

        Args:
            timing: When to show ("before", "during", "after")
            offset: Additional offset in seconds
            flow_index: Flow index (1-indexed)
            step_index: Step index (1-indexed)
            event_lookup: Map of (flow_idx, step_idx) to TimelineEvent
            timeline_start: Unix timestamp when execution started (for conversion)

        Returns:
            Video-relative start time in seconds
        """
        event = event_lookup.get((flow_index, step_index))
        if not event:
            return offset

        # Convert absolute Unix timestamps to video-relative times
        event_start = event.start_time - timeline_start
        event_end = event.end_time - timeline_start

        if timing == "before":
            return max(0, event_start - 0.5 + offset)
        elif timing == "during":
            return event_start + offset
        else:  # after
            return event_end + offset


@dataclass
class BackgroundConfig:
    """
    Configuration for a full-screen background color overlay.

    Attributes:
        color: Background color (hex format, e.g., "#000000")
        start_time: When to start showing the background (seconds)
        duration: How long to show the background (seconds)
        opacity: Opacity from 0.0 to 1.0
    """

    color: str
    start_time: float
    duration: float
    opacity: float = 1.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "color": self.color,
            "start_time": self.start_time,
            "duration": self.duration,
            "opacity": self.opacity,
        }


class OverlayRenderer:
    """
    Renders text overlays, logos, and backgrounds on video using FFmpeg filters.

    This class builds FFmpeg filter chains for multiple overlays
    and applies them to a video file.
    """

    def __init__(self, video_path: Path, output_dir: Path):
        """
        Initialize the overlay renderer.

        Args:
            video_path: Path to the input video file
            output_dir: Directory for output files
        """
        if not check_ffmpeg_installed():
            from specspectacle.video.ffmpeg_utils import FFmpegNotFoundError

            raise FFmpegNotFoundError()

        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.overlays: list[OverlayConfig] = []
        self.logos: list[LogoConfig] = []
        self.backgrounds: list[BackgroundConfig] = []
        self._video_info = get_video_info(self.video_path)

    def add_overlay(self, config: OverlayConfig) -> None:
        """
        Add an overlay to be rendered.

        Args:
            config: OverlayConfig defining the overlay
        """
        self.overlays.append(config)

    def add_overlays(self, configs: list[OverlayConfig]) -> None:
        """
        Add multiple overlays to be rendered.

        Args:
            configs: List of OverlayConfig objects
        """
        self.overlays.extend(configs)

    def add_logo(self, config: LogoConfig) -> None:
        """
        Add a logo to be rendered.

        Args:
            config: LogoConfig defining the logo overlay
        """
        self.logos.append(config)

    def add_logos(self, configs: list[LogoConfig]) -> None:
        """
        Add multiple logos to be rendered.

        Args:
            configs: List of LogoConfig objects
        """
        self.logos.extend(configs)

    def add_background(self, config: BackgroundConfig) -> None:
        """
        Add a full-screen background color overlay.

        Args:
            config: BackgroundConfig defining the background
        """
        self.backgrounds.append(config)

    def render(self, output_path: Path) -> Path:
        """
        Render all overlays onto the video.

        Args:
            output_path: Path for the output video file

        Returns:
            Path to the rendered video
        """
        import subprocess

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.overlays and not self.logos and not self.backgrounds:
            logger.info("No overlays, logos, or backgrounds to render, copying video")
            # Just copy the video if no overlays
            import shutil

            shutil.copy(self.video_path, output_path)
            return output_path

        # Sort all items by start time
        sorted_overlays = sorted(self.overlays, key=lambda o: o.start_time)
        sorted_logos = sorted(self.logos, key=lambda logo: logo.start_time)
        sorted_backgrounds = sorted(self.backgrounds, key=lambda bg: bg.start_time)

        # Build filter complex
        filter_complex = self._build_filter_complex(
            sorted_overlays, sorted_logos, sorted_backgrounds
        )

        total_items = len(self.overlays) + len(self.logos) + len(self.backgrounds)
        logger.info(f"Rendering {total_items} item(s) on video")
        logger.debug(f"Filter complex: {filter_complex}")

        # Build FFmpeg command with -filter_complex for complex filter chains
        cmd = ["ffmpeg", "-y", "-i", str(self.video_path)]

        # Add logo inputs if any logos exist
        for logo in sorted_logos:
            logo_path = Path(logo.logo_path)
            if not logo_path.exists():
                raise FileNotFoundError(f"Logo not found: {logo_path}")
            cmd.extend(["-i", str(logo_path)])

        # Use -filter_complex instead of -vf for complex filter chains
        cmd.extend([
            "-filter_complex", filter_complex,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "copy",
            str(output_path)
        ])

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            logger.info(f"Overlay rendering complete: {output_path}")
            return output_path

        except subprocess.CalledProcessError as e:
            logger.error(f"Overlay rendering failed: {e.stderr}")
            raise FFmpegExecutionError(
                "Overlay rendering failed",
                e.returncode,
                e.stderr,
            )

    def _build_filter_complex(
        self,
        overlays: list[OverlayConfig],
        logos: list[LogoConfig],
        backgrounds: list[BackgroundConfig],
    ) -> str:
        """
        Build FFmpeg filter complex string for all backgrounds, logos, and text overlays.

        The order of application is:
        1. Full-screen backgrounds (drawbox)
        2. Logos (overlay)
        3. Text overlays (drawtext)

        Args:
            overlays: List of OverlayConfig sorted by start time
            logos: List of LogoConfig sorted by start time
            backgrounds: List of BackgroundConfig sorted by start time

        Returns:
            FFmpeg filter complex string
        """
        filter_parts = []

        # 1. Scale all logos first (pre-processing logo inputs)
        for idx, logo in enumerate(logos):
            logo_input_idx = idx + 1  # Logo inputs start at [1:v], [2:v], etc.
            filter_parts.append(
                f"[{logo_input_idx}:v]scale=iw*{logo.scale}:-1[logo{idx}]"
            )

        # Start chaining from the base video [0:v]
        current_v = "[0:v]"
        chain_idx = 0

        # 2. Add backgrounds
        for bg in backgrounds:
            bg_color, _ = self._hex_to_ffmpeg_color_with_alpha(bg.color)
            enable_expr = f"between(t,{bg.start_time:.2f},{bg.start_time + bg.duration:.2f})"

            # Use drawbox to fill the entire screen
            # color=COLOR@OPACITY
            next_v = f"[v_bg{chain_idx}]"
            filter_parts.append(
                f"{current_v}drawbox=x=0:y=0:w=iw:h=ih:color={bg_color}@{bg.opacity}:t=fill:enable='{enable_expr}'{next_v}"
            )
            current_v = next_v
            chain_idx += 1

        # 3. Add logos
        for idx, logo in enumerate(logos):
            x_expr, y_expr = LOGO_POSITION_MAP[logo.position]
            enable_expr = f"between(t,{logo.start_time:.2f},{logo.start_time + logo.duration:.2f})"

            next_v = f"[v_logo{chain_idx}]"
            filter_parts.append(
                f"{current_v}[logo{idx}]overlay={x_expr}:{y_expr}:enable='{enable_expr}'{next_v}"
            )
            current_v = next_v
            chain_idx += 1

        # 4. Add text overlays
        for overlay in overlays:
            drawtext_filter = self._build_drawtext_filter(overlay)

            next_v = f"[v_text{chain_idx}]"
            filter_parts.append(
                f"{current_v}{drawtext_filter}{next_v}"
            )
            current_v = next_v
            chain_idx += 1

        # Final output label is not needed for the very last filter if it's the only chain
        # but we use it for clarity and strip it from the very last part to let FFmpeg auto-map
        if filter_parts:
            # Strip the last output label so FFmpeg uses it as the final video stream
            last_part = filter_parts[-1]
            if last_part.endswith(f"[v_text{chain_idx-1}]"):
                filter_parts[-1] = last_part.replace(f"[v_text{chain_idx-1}]", "")
            elif last_part.endswith(f"[v_logo{chain_idx-1}]"):
                filter_parts[-1] = last_part.replace(f"[v_logo{chain_idx-1}]", "")
            elif last_part.endswith(f"[v_bg{chain_idx-1}]"):
                filter_parts[-1] = last_part.replace(f"[v_bg{chain_idx-1}]", "")

        # Join with semicolons for independent chains (logo scaling vs video processing)
        # Actually, logo scaling is independent, but video processing is one long chain.

        # Separate logo scaling from the main video chain
        logo_scaling = [p for p in filter_parts if p.startswith("[") and "scale=" in p]
        video_chain = [p for p in filter_parts if p not in logo_scaling]

        final_parts = []
        if logo_scaling:
            final_parts.append(";".join(logo_scaling))
        if video_chain:
            final_parts.append(",".join(video_chain))

        return ";".join(final_parts) if logo_scaling else ",".join(video_chain)

    def _build_drawtext_filter(self, config: OverlayConfig) -> str:
        """
        Build a single drawtext filter for an overlay.

        Args:
            config: OverlayConfig for this overlay

        Returns:
            FFmpeg drawtext filter string
        """
        # Get position expressions
        x_expr, y_expr = POSITION_MAP[config.position]

        # Calculate end time
        end_time = config.start_time + config.duration

        # Strip emojis since FFmpeg drawtext doesn't support colored emojis
        text_to_render, had_emojis = self._strip_emojis(config.text)
        if had_emojis:
            logger.warning(
                f"Emojis removed from overlay text (FFmpeg drawtext doesn't support colored emojis). "
                f"Original: '{config.text}' -> Rendered: '{text_to_render}'"
            )

        # Handle empty text after emoji removal
        if not text_to_render:
            text_to_render = config.text  # Keep original if only emojis
            logger.warning(f"Overlay text was only emojis, keeping original: '{config.text}'")

        # Escape special characters in text for FFmpeg
        escaped_text = self._escape_text(text_to_render)

        # Convert hex colors to FFmpeg format
        font_color = self._hex_to_ffmpeg_color(config.font_color)
        bg_color, bg_alpha = self._hex_to_ffmpeg_color_with_alpha(config.background_color)

        # Build drawtext filter
        # Using box=1 for background box
        filter_parts = [
            f"drawtext=text='{escaped_text}'",
            f"fontsize={config.font_size}",
            f"fontcolor={font_color}",
            "fontfile=/System/Library/Fonts/Helvetica.ttc",  # macOS default, fallback
            f"x={x_expr}",
            f"y={y_expr}",
            "box=1",
            f"boxcolor={bg_color}@{bg_alpha}",
            "boxborderw=10",
            f"enable='between(t,{config.start_time:.6f},{end_time:.6f})'",
        ]

        return ":".join(filter_parts)

    def _build_overlay_filter(self, config: LogoConfig, input_idx: int = 0) -> str:
        """
        Build a single overlay filter for a logo.

        Args:
            config: LogoConfig for this logo
            input_idx: Input index for this logo (0 for first logo, 1 for second, etc.)

        Returns:
            FFmpeg overlay filter string
        """
        # Get position expressions
        x_expr, y_expr = LOGO_POSITION_MAP[config.position]

        # Calculate end time
        end_time = config.start_time + config.duration

        # Build overlay filter with scale
        # First scale the logo, then overlay it
        # Use [N:v] where N is the input index (0-based, so logo 0 uses [1:v])
        logo_input_idx = input_idx + 1
        filter_parts = [
            f"[{logo_input_idx}:v]scale=iw*{config.scale}:-1[logo{input_idx}]",
            f"[video][logo{input_idx}]overlay={x_expr}:{y_expr}:enable='between(t,{config.start_time:.2f},{end_time:.2f})'",
        ]

        return ":".join(filter_parts)

    # Regex pattern for emoji detection (covers most common emoji ranges)
    EMOJI_PATTERN = re.compile(
        "["
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f680-\U0001f6ff"  # transport & map symbols
        "\U0001f1e0-\U0001f1ff"  # flags (iOS)
        "\U00002702-\U000027b0"  # dingbats
        "\U000024c2-\U0001f251"  # enclosed characters
        "\U0001f900-\U0001f9ff"  # supplemental symbols
        "\U0001fa00-\U0001fa6f"  # extended-A symbols
        "\U0001fa70-\U0001faff"  # extended-B symbols
        "\U00002600-\U000026ff"  # misc symbols
        "\U00002b50-\U00002b55"  # stars
        "]+",
        flags=re.UNICODE,
    )

    @classmethod
    def _strip_emojis(cls, text: str) -> tuple[str, bool]:
        """
        Strip emojis from text since FFmpeg drawtext doesn't support colored emojis.

        Args:
            text: Original text that may contain emojis

        Returns:
            Tuple of (cleaned text, whether emojis were removed)
        """
        cleaned = cls.EMOJI_PATTERN.sub("", text).strip()
        had_emojis = cleaned != text.strip()
        return cleaned, had_emojis

    @staticmethod
    def _escape_text(text: str) -> str:
        r"""
        Escape text for FFmpeg drawtext filter.

        FFmpeg drawtext requires escaping of special characters when using
        subprocess (not shell). For drawtext text parameter:
        - Single quotes: ' -> '' (two single quotes)
        - Backslashes: \ -> \\
        - Colons and other special chars need escaping with backslash
        """
        # Replace backslashes first (must be done before other escapes)
        text = text.replace("\\", "\\\\")
        # Escape single quotes for FFmpeg drawtext (use '' not shell \' style)
        text = text.replace("'", "''")
        # Escape colons (needed in drawtext as they're parameter separators)
        text = text.replace(":", "\\:")
        return text

    @staticmethod
    def _hex_to_ffmpeg_color(hex_color: str) -> str:
        """
        Convert hex color to FFmpeg format.

        Args:
            hex_color: Color in #RRGGBB or #RRGGBBAA format

        Returns:
            FFmpeg color string (hex without #)
        """
        # Remove # and return, FFmpeg accepts hex
        return hex_color.lstrip("#")[:6]

    @staticmethod
    def _hex_to_ffmpeg_color_with_alpha(hex_color: str) -> tuple[str, float]:
        """
        Convert hex color with alpha to FFmpeg format.

        Args:
            hex_color: Color in #RRGGBB or #RRGGBBAA format

        Returns:
            Tuple of (color_hex, alpha_float)
        """
        color = hex_color.lstrip("#")
        rgb = color[:6]

        if len(color) == 8:
            # Convert AA to float (0-1)
            alpha_hex = color[6:8]
            alpha = int(alpha_hex, 16) / 255.0
        else:
            alpha = 1.0

        return rgb, alpha


def render_overlays_on_video(
    video_path: Path,
    output_path: Path,
    overlays: list[OverlayConfig],
) -> Path:
    """
    Convenience function to render overlays on a video.

    Args:
        video_path: Path to input video
        output_path: Path for output video
        overlays: List of overlays to render

    Returns:
        Path to the rendered video
    """
    renderer = OverlayRenderer(video_path, output_path.parent)
    renderer.add_overlays(overlays)
    return renderer.render(output_path)


__all__ = [
    "OverlayConfig",
    "OverlayTimestampCalculator",
    "OverlayRenderer",
    "render_overlays_on_video",
    "POSITION_MAP",
]
