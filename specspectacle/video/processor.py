"""
Video processor for converting, resizing, and compressing videos.

This module provides the VideoProcessor class for processing raw Playwright
recordings into polished, compressed videos with configurable quality settings.
"""

import logging
import os
import tempfile
from enum import Enum
from pathlib import Path
from typing import Optional

from specspectacle.video.ffmpeg_utils import (
    FFmpegNotFoundError,
    check_ffmpeg_installed,
    get_video_info,
    run_ffmpeg_command,
)

logger = logging.getLogger(__name__)


class CompressionPreset(Enum):
    """Video compression presets."""

    LOW = "low"  # High quality, larger file size
    MEDIUM = "medium"  # Balanced quality and file size (default)
    HIGH = "high"  # Lower quality, smaller file size


# Compression preset configurations
COMPRESSION_SETTINGS = {
    CompressionPreset.LOW: {
        "crf": 18,  # Lower CRF = higher quality
        "bitrate": "8000k",
        "preset": "slow",  # Slower = better compression
    },
    CompressionPreset.MEDIUM: {
        "crf": 23,
        "bitrate": "5000k",
        "preset": "medium",
    },
    CompressionPreset.HIGH: {
        "crf": 28,  # Higher CRF = lower quality
        "bitrate": "2500k",
        "preset": "fast",
    },
}


class VideoProcessor:
    """
    Process raw Playwright videos into polished, compressed videos.

    This class handles:
    - Codec conversion (to H.264 by default)
    - FPS normalization
    - Resolution resizing
    - Compression with configurable presets

    Attributes:
        input_path: Path to the input video file.
        output_dir: Directory where processed videos will be saved.
        temp_files: List of temporary files created during processing.

    Example:
        >>> processor = VideoProcessor(Path("raw.webm"), Path("output"))
        >>> output_path = processor.process(
        ...     output_filename="demo.mp4",
        ...     fps=30,
        ...     bitrate="5000k",
        ...     resolution="1280x720",
        ... )
    """

    def __init__(self, input_path: Path, output_dir: Path):
        """
        Initialize the video processor.

        Args:
            input_path: Path to the input video file.
            output_dir: Directory where processed videos will be saved.

        Raises:
            FFmpegNotFoundError: If FFmpeg is not installed.
            FileNotFoundError: If the input video file doesn't exist.
        """
        if not check_ffmpeg_installed():
            raise FFmpegNotFoundError()

        if not input_path.exists():
            raise FileNotFoundError(f"Input video not found: {input_path}")

        self.input_path = input_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_files: list[Path] = []

    def convert_codec(self, codec: str = "libx264", output_path: Optional[Path] = None) -> Path:
        """
        Convert the video to a specified codec.

        Args:
            codec: Target codec (default: libx264 for H.264).
            output_path: Optional output path. If None, a temp file is created.

        Returns:
            Path to the output video file.

        Raises:
            FFmpegExecutionError: If the conversion fails.
        """
        if output_path is None:
            output_path = self._create_temp_file(".mp4")

        logger.info(f"Converting video to codec: {codec}")

        args = [
            "-c:v",
            codec,
            "-c:a",
            "aac",  # Audio codec
            "-strict",
            "experimental",
        ]

        run_ffmpeg_command(args, input_file=self.input_path, output_file=output_path)

        return output_path

    def normalize_fps(self, fps: int = 30, input_path: Optional[Path] = None) -> Path:
        """
        Normalize video frame rate to the specified FPS.

        Args:
            fps: Target frames per second (default: 30).
            input_path: Optional input path. If None, uses self.input_path.

        Returns:
            Path to the output video file.

        Raises:
            FFmpegExecutionError: If the conversion fails.
        """
        source = input_path or self.input_path
        output_path = self._create_temp_file(".mp4")

        logger.info(f"Normalizing video FPS to: {fps}")

        args = [
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
        ]

        run_ffmpeg_command(args, input_file=source, output_file=output_path)

        return output_path

    def resize(
        self,
        resolution: str,
        input_path: Optional[Path] = None,
    ) -> Path:
        """
        Resize video to the target resolution.

        Args:
            resolution: Target resolution as "WIDTHxHEIGHT" (e.g., "1280x720").
            input_path: Optional input path. If None, uses self.input_path.

        Returns:
            Path to the output video file.

        Raises:
            FFmpegExecutionError: If the resize fails.
            ValueError: If resolution format is invalid.
        """
        # Validate resolution format
        if "x" not in resolution:
            raise ValueError(
                f"Invalid resolution format: {resolution}. Use WIDTHxHEIGHT (e.g., 1280x720)"
            )

        width, height = resolution.split("x")
        try:
            width = int(width)
            height = int(height)
        except ValueError:
            raise ValueError(f"Invalid resolution values: {resolution}")

        source = input_path or self.input_path
        output_path = self._create_temp_file(".mp4")

        logger.info(f"Resizing video to: {resolution}")

        # Use scale filter, ensure even dimensions for codec compatibility
        scale_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"

        args = [
            "-vf",
            scale_filter,
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
        ]

        run_ffmpeg_command(args, input_file=source, output_file=output_path)

        return output_path

    def compress(
        self,
        preset: CompressionPreset = CompressionPreset.MEDIUM,
        input_path: Optional[Path] = None,
    ) -> Path:
        """
        Apply compression preset to the video.

        Args:
            preset: Compression preset (LOW, MEDIUM, or HIGH).
            input_path: Optional input path. If None, uses self.input_path.

        Returns:
            Path to the output video file.

        Raises:
            FFmpegExecutionError: If compression fails.
        """
        source = input_path or self.input_path
        output_path = self._create_temp_file(".mp4")

        settings = COMPRESSION_SETTINGS[preset]
        logger.info(f"Compressing video with preset: {preset.value}")

        args = [
            "-c:v",
            "libx264",
            "-crf",
            str(settings["crf"]),
            "-preset",
            settings["preset"],
            "-b:v",
            settings["bitrate"],
            "-c:a",
            "aac",
            "-b:a",
            "128k",
        ]

        run_ffmpeg_command(args, input_file=source, output_file=output_path)

        return output_path

    def process(
        self,
        output_filename: str,
        fps: int = 30,
        bitrate: str = "5000k",
        resolution: str = "1280x720",
        codec: str = "h264",
        compression_preset: Optional[str] = None,
    ) -> Path:
        """
        Full video processing pipeline.

        Applies all processing steps in order:
        1. Convert to target codec
        2. Normalize FPS
        3. Resize to target resolution
        4. Apply compression

        Args:
            output_filename: Name for the final output file.
            fps: Target frames per second (default: 30).
            bitrate: Target bitrate (default: "5000k").
            resolution: Target resolution (default: "1280x720").
            codec: Target codec (default: "h264").
            compression_preset: Optional compression preset ("low", "medium", "high").

        Returns:
            Path to the final processed video file.

        Raises:
            FFmpegExecutionError: If any processing step fails.
        """
        logger.info(f"Starting video processing pipeline for: {self.input_path}")
        logger.info(f"Target: fps={fps}, resolution={resolution}, bitrate={bitrate}")

        final_output = self.output_dir / output_filename

        # Determine compression preset
        if compression_preset:
            preset = CompressionPreset(compression_preset)
            settings = COMPRESSION_SETTINGS[preset]
            crf = settings["crf"]
            actual_bitrate = settings["bitrate"]
            ffmpeg_preset = settings["preset"]
        else:
            # Use provided bitrate, default CRF and preset
            crf = 23
            actual_bitrate = bitrate
            ffmpeg_preset = "medium"

        # Validate resolution format
        if "x" not in resolution:
            raise ValueError(f"Invalid resolution format: {resolution}")

        width, height = resolution.split("x")
        try:
            width = int(width)
            height = int(height)
        except ValueError:
            raise ValueError(f"Invalid resolution values: {resolution}")

        # Map codec name to FFmpeg format
        codec_mapping = {
            "h264": "libx264",
            "H.264": "libx264",
            "libx264": "libx264",
            "h265": "libx265",
            "H.265": "libx265",
            "hevc": "libx265",
            "libx265": "libx265",
        }
        video_codec = codec_mapping.get(codec, codec)

        # Build FFmpeg filter chain
        scale_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"

        # Combined processing command
        args = [
            "-r",
            str(fps),  # Output FPS
            "-vf",
            scale_filter,  # Scale and pad
            "-c:v",
            video_codec,  # Video codec
            "-crf",
            str(crf),  # Quality
            "-preset",
            ffmpeg_preset,  # Encoding speed/quality
            "-b:v",
            actual_bitrate,  # Bitrate
            "-c:a",
            "aac",  # Audio codec
            "-b:a",
            "128k",  # Audio bitrate
            "-movflags",
            "+faststart",  # Optimize for web streaming
        ]

        # H.265 requires additional tags for compatibility
        if video_codec == "libx265":
            args.extend(["-tag:v", "hvc1"])

        logger.info(f"Processing video with FFmpeg...")
        run_ffmpeg_command(args, input_file=self.input_path, output_file=final_output)

        # Get output file info
        output_info = get_video_info(final_output)
        logger.info(
            f"Video processed successfully: {final_output} "
            f"({output_info['duration']:.1f}s, {output_info['width']}x{output_info['height']}, "
            f"{output_info['fps']} fps)"
        )

        return final_output

    def merge_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Merge an audio track with a video file.

        Args:
            video_path: Path to the input video file.
            audio_path: Path to the audio file to merge.
            output_path: Optional output path. If None, a temp file is created.

        Returns:
            Path to the output video with merged audio.

        Raises:
            FileNotFoundError: If input files don't exist.
            FFmpegExecutionError: If the merge fails.
        """
        import subprocess

        video_path = Path(video_path)
        audio_path = Path(audio_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if output_path is None:
            output_path = self._create_temp_file(".mp4")
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get video and audio durations for logging
        video_info = get_video_info(video_path)
        video_duration = float(video_info.get("duration", 0))

        try:
            audio_probe = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            audio_duration = float(audio_probe.stdout.strip())
        except (subprocess.CalledProcessError, ValueError) as e:
            logger.warning(f"Could not get audio duration: {e}")
            audio_duration = video_duration

        logger.info(f"Merging audio ({audio_path}) with video ({video_path})")
        logger.info(f"Video duration: {video_duration:.2f}s, Audio duration: {audio_duration:.2f}s")

        # Merge audio with video using shortest stream (video should match or exceed audio now)
        args = [
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",  # Video from first input
            "-map",
            "1:a:0",  # Audio from second input
            "-c:v",
            "copy",  # Copy video stream (no re-encoding)
            "-c:a",
            "aac",  # Encode audio as AAC
            "-b:a",
            "192k",
            "-shortest",  # Use shortest stream duration
        ]

        # Build the command
        cmd = ["ffmpeg", "-y"] + args + [str(output_path)]

        logger.debug(f"Running FFmpeg merge: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            logger.info(f"Audio-video merge complete: {output_path}")
            return output_path

        except subprocess.CalledProcessError as e:
            from specspectacle.video.ffmpeg_utils import FFmpegExecutionError

            raise FFmpegExecutionError(
                f"Audio-video merge failed",
                e.returncode,
                e.stderr,
            )

    def cleanup_temp_files(self):
        """Remove all temporary files created during processing."""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Removed temp file: {temp_file}")
            except OSError as e:
                logger.warning(f"Failed to remove temp file {temp_file}: {e}")
        self.temp_files.clear()

    def _create_temp_file(self, suffix: str) -> Path:
        """Create a temporary file and track it for cleanup."""
        fd, path = tempfile.mkstemp(suffix=suffix, dir=self.output_dir)
        os.close(fd)
        temp_path = Path(path)
        self.temp_files.append(temp_path)
        return temp_path


def process_video(
    input_path: Path,
    output_path: Path,
    fps: int = 30,
    bitrate: str = "5000k",
    resolution: str = "1280x720",
    codec: str = "h264",
    compression_preset: Optional[str] = None,
    keep_artifacts: bool = False,
) -> Path:
    """
    Convenience function to process a video file.

    Args:
        input_path: Path to the input video file.
        output_path: Path for the output video file.
        fps: Target frames per second.
        bitrate: Target bitrate.
        resolution: Target resolution.
        codec: Target codec.
        compression_preset: Optional compression preset.
        keep_artifacts: If True, keep intermediate files.

    Returns:
        Path to the processed video file.
    """
    processor = VideoProcessor(input_path, output_path.parent)

    try:
        result = processor.process(
            output_filename=output_path.name,
            fps=fps,
            bitrate=bitrate,
            resolution=resolution,
            codec=codec,
            compression_preset=compression_preset,
        )
        return result
    finally:
        if not keep_artifacts:
            processor.cleanup_temp_files()


__all__ = [
    "CompressionPreset",
    "COMPRESSION_SETTINGS",
    "VideoProcessor",
    "process_video",
]
