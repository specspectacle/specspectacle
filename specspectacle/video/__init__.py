"""
Video processing module for SpecSpectacle.

This module provides tools for:
- Checking FFmpeg installation
- Processing raw Playwright videos
- Converting codecs, normalizing FPS, resizing
- Applying compression presets
- Rendering text overlays
"""

from specspectacle.video.ffmpeg_utils import (
    FFmpegError,
    FFmpegExecutionError,
    FFmpegNotFoundError,
    check_ffmpeg_installed,
    get_ffmpeg_version,
    get_video_info,
    run_ffmpeg_command,
)
from specspectacle.video.overlay import (
    POSITION_MAP,
    OverlayConfig,
    OverlayRenderer,
    OverlayTimestampCalculator,
    render_overlays_on_video,
)
from specspectacle.video.processor import (
    COMPRESSION_SETTINGS,
    CompressionPreset,
    VideoProcessor,
    process_video,
)

__all__ = [
    "FFmpegError",
    "FFmpegNotFoundError",
    "FFmpegExecutionError",
    "check_ffmpeg_installed",
    "get_ffmpeg_version",
    "run_ffmpeg_command",
    "get_video_info",
    "CompressionPreset",
    "COMPRESSION_SETTINGS",
    "VideoProcessor",
    "process_video",
    "OverlayConfig",
    "OverlayTimestampCalculator",
    "OverlayRenderer",
    "render_overlays_on_video",
    "POSITION_MAP",
]
