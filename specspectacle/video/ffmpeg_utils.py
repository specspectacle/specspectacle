"""
FFmpeg utility functions for video processing.

This module provides utilities for checking FFmpeg installation,
getting version information, and running FFmpeg commands.
"""

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    """Base exception for FFmpeg-related errors."""

    pass


class FFmpegNotFoundError(FFmpegError):
    """Raised when FFmpeg is not installed or not found in PATH."""

    def __init__(
        self,
        message: str = "FFmpeg not found. Please install FFmpeg and ensure it's in your PATH.",
    ):
        self.message = message
        # Add platform-specific installation instructions
        import platform

        system = platform.system()
        if system == "Darwin":  # macOS
            install_msg = "Install with: brew install ffmpeg"
        elif system == "Linux":
            install_msg = "Install with: sudo apt-get install ffmpeg (Ubuntu/Debian) or sudo yum install ffmpeg (RHEL/CentOS)"
        elif system == "Windows":
            install_msg = "Install with: choco install ffmpeg (or download from https://ffmpeg.org/download.html)"
        else:
            install_msg = "Visit https://ffmpeg.org/download.html for installation instructions"

        full_message = f"{message}\n💡 {install_msg}"
        super().__init__(full_message)


class FFmpegExecutionError(FFmpegError):
    """Raised when an FFmpeg command fails."""

    def __init__(self, message: str, returncode: int, stderr: str = ""):
        self.message = message
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"{message}: {stderr}" if stderr else message)


def check_ffmpeg_installed() -> bool:
    """
    Check if FFmpeg is installed and available in the system PATH.

    Returns:
        bool: True if FFmpeg is installed, False otherwise.

    Example:
        >>> if check_ffmpeg_installed():
        ...     print("FFmpeg is available")
    """
    return shutil.which("ffmpeg") is not None


def get_ffmpeg_version() -> str:
    """
    Get the installed FFmpeg version string.

    Returns:
        str: FFmpeg version string (e.g., "6.1.1").

    Raises:
        FFmpegNotFoundError: If FFmpeg is not installed.

    Example:
        >>> version = get_ffmpeg_version()
        >>> print(f"FFmpeg version: {version}")
    """
    if not check_ffmpeg_installed():
        raise FFmpegNotFoundError()

    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            check=True,
        )
        # Output is like: "ffmpeg version 6.1.1 Copyright..."
        # Extract just the version number
        first_line = result.stdout.split("\n")[0]
        parts = first_line.split()
        if len(parts) >= 3 and parts[0] == "ffmpeg" and parts[1] == "version":
            return parts[2]
        return first_line  # Return full line if parsing fails
    except subprocess.CalledProcessError as e:
        raise FFmpegExecutionError("Failed to get FFmpeg version", e.returncode, e.stderr)


def get_ffprobe_path() -> str | None:
    """
    Get the path to ffprobe executable.

    Returns:
        Optional[str]: Path to ffprobe or None if not found.
    """
    return shutil.which("ffprobe")


def run_ffmpeg_command(
    args: list[str],
    input_file: Path | None = None,
    output_file: Path | None = None,
    overwrite: bool = True,
) -> subprocess.CompletedProcess:
    """
    Execute an FFmpeg command with the given arguments.

    Args:
        args: List of FFmpeg arguments (excluding 'ffmpeg' itself).
        input_file: Optional input file path (will be prepended with -i).
        output_file: Optional output file path (will be appended).
        overwrite: Whether to overwrite output file if it exists (default: True).

    Returns:
        subprocess.CompletedProcess: The completed process result.

    Raises:
        FFmpegNotFoundError: If FFmpeg is not installed.
        FFmpegExecutionError: If the FFmpeg command fails.

    Example:
        >>> run_ffmpeg_command(
        ...     ["-c:v", "libx264", "-crf", "23"],
        ...     input_file=Path("input.mp4"),
        ...     output_file=Path("output.mp4"),
        ... )
    """
    if not check_ffmpeg_installed():
        raise FFmpegNotFoundError()

    cmd = ["ffmpeg"]

    # Add overwrite flag
    if overwrite:
        cmd.append("-y")

    # Add input file
    if input_file:
        cmd.extend(["-i", str(input_file)])

    # Add additional arguments
    cmd.extend(args)

    # Add output file
    if output_file:
        cmd.append(str(output_file))

    logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg command failed: {e.stderr}")
        raise FFmpegExecutionError(
            f"FFmpeg command failed: {' '.join(cmd)}", e.returncode, e.stderr
        )


def get_video_info(video_path: Path) -> dict:
    """
    Get video information using ffprobe.

    Args:
        video_path: Path to the video file.

    Returns:
        dict: Video information including duration, width, height, fps.

    Raises:
        FFmpegNotFoundError: If ffprobe is not found.
        FFmpegExecutionError: If ffprobe command fails.
    """
    ffprobe_path = get_ffprobe_path()
    if not ffprobe_path:
        raise FFmpegNotFoundError("ffprobe not found. Please install FFmpeg (includes ffprobe).")

    cmd = [
        ffprobe_path,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]

    try:
        import json

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        # Extract video stream info
        video_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
                break

        if not video_stream:
            return {"duration": 0, "width": 0, "height": 0, "fps": 0}

        # Parse fps (can be "30/1" or "30000/1001" format)
        fps_str = video_stream.get("r_frame_rate", "0/1")
        if "/" in fps_str:
            num, denom = fps_str.split("/")
            fps = float(num) / float(denom) if float(denom) > 0 else 0
        else:
            fps = float(fps_str)

        return {
            "duration": float(data.get("format", {}).get("duration", 0)),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "fps": round(fps, 2),
            "codec": video_stream.get("codec_name", ""),
            "bitrate": int(data.get("format", {}).get("bit_rate", 0)),
        }
    except subprocess.CalledProcessError as e:
        raise FFmpegExecutionError(
            f"Failed to get video info for {video_path}", e.returncode, e.stderr
        )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        raise FFmpegExecutionError(f"Failed to parse video info for {video_path}", 1, str(e))


__all__ = [
    "FFmpegError",
    "FFmpegNotFoundError",
    "FFmpegExecutionError",
    "check_ffmpeg_installed",
    "get_ffmpeg_version",
    "get_ffprobe_path",
    "run_ffmpeg_command",
    "get_video_info",
]
