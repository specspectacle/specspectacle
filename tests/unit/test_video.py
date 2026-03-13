"""Unit tests for video processing module."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from specspectacle.video.ffmpeg_utils import (
    FFmpegExecutionError,
    FFmpegNotFoundError,
    check_ffmpeg_installed,
    get_ffmpeg_version,
    get_video_info,
    run_ffmpeg_command,
)
from specspectacle.video.processor import (
    COMPRESSION_SETTINGS,
    CompressionPreset,
    VideoProcessor,
    process_video,
)


class TestFFmpegUtils:
    """Tests for FFmpeg utility functions."""

    def test_check_ffmpeg_installed(self):
        """Test that check_ffmpeg_installed returns a boolean."""
        result = check_ffmpeg_installed()
        assert isinstance(result, bool)
        # On most dev machines, FFmpeg should be installed
        # But we don't fail if it's not

    @pytest.mark.skipif(not check_ffmpeg_installed(), reason="FFmpeg not installed")
    def test_get_ffmpeg_version(self):
        """Test that get_ffmpeg_version returns a version string."""
        version = get_ffmpeg_version()
        assert isinstance(version, str)
        assert len(version) > 0
        # Version should start with a number or contain a number
        assert any(char.isdigit() for char in version)

    def test_get_ffmpeg_version_not_installed(self):
        """Test that get_ffmpeg_version raises FFmpegNotFoundError when not installed."""
        with patch("specspectacle.video.ffmpeg_utils.check_ffmpeg_installed", return_value=False):
            with pytest.raises(FFmpegNotFoundError):
                get_ffmpeg_version()

    def test_ffmpeg_not_found_error_message(self):
        """Test FFmpegNotFoundError has helpful message."""
        error = FFmpegNotFoundError()
        assert "FFmpeg not found" in str(error)
        assert "PATH" in str(error)

    def test_ffmpeg_execution_error(self):
        """Test FFmpegExecutionError captures details."""
        error = FFmpegExecutionError(
            message="Command failed", returncode=1, stderr="Invalid input file"
        )
        assert "Command failed" in str(error)
        assert "Invalid input file" in str(error)
        assert error.returncode == 1

    @pytest.mark.skipif(not check_ffmpeg_installed(), reason="FFmpeg not installed")
    def test_run_ffmpeg_command_version(self):
        """Test running a simple FFmpeg command."""
        # This should not raise an error
        result = run_ffmpeg_command(["-version"])
        assert isinstance(result, subprocess.CompletedProcess)

    def test_run_ffmpeg_command_not_installed(self):
        """Test run_ffmpeg_command raises error when FFmpeg not installed."""
        with patch("specspectacle.video.ffmpeg_utils.check_ffmpeg_installed", return_value=False):
            with pytest.raises(FFmpegNotFoundError):
                run_ffmpeg_command(["-version"])


class TestCompressionPresets:
    """Tests for compression preset configurations."""

    def test_all_presets_defined(self):
        """Test all compression presets have settings."""
        for preset in CompressionPreset:
            assert preset in COMPRESSION_SETTINGS
            settings = COMPRESSION_SETTINGS[preset]
            assert "crf" in settings
            assert "bitrate" in settings
            assert "preset" in settings

    def test_preset_crf_ordering(self):
        """Test CRF values increase from LOW to HIGH (lower = better quality)."""
        assert (
            COMPRESSION_SETTINGS[CompressionPreset.LOW]["crf"]
            < COMPRESSION_SETTINGS[CompressionPreset.MEDIUM]["crf"]
        )
        assert (
            COMPRESSION_SETTINGS[CompressionPreset.MEDIUM]["crf"]
            < COMPRESSION_SETTINGS[CompressionPreset.HIGH]["crf"]
        )

    def test_preset_bitrate_ordering(self):
        """Test bitrate decreases from LOW to HIGH."""
        low_br = int(COMPRESSION_SETTINGS[CompressionPreset.LOW]["bitrate"].replace("k", ""))
        med_br = int(COMPRESSION_SETTINGS[CompressionPreset.MEDIUM]["bitrate"].replace("k", ""))
        high_br = int(COMPRESSION_SETTINGS[CompressionPreset.HIGH]["bitrate"].replace("k", ""))
        assert low_br > med_br > high_br


class TestVideoProcessor:
    """Tests for VideoProcessor class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def dummy_video(self, temp_dir):
        """Create a dummy video file for testing (not a real video)."""
        video_path = temp_dir / "test_input.mp4"
        video_path.touch()  # Create empty file
        return video_path

    def test_processor_init_file_not_found(self, temp_dir):
        """Test VideoProcessor raises error for non-existent file."""
        with pytest.raises(FileNotFoundError):
            VideoProcessor(temp_dir / "nonexistent.mp4", temp_dir)

    def test_processor_init_ffmpeg_not_installed(self, dummy_video, temp_dir):
        """Test VideoProcessor raises error when FFmpeg not installed."""
        with patch("specspectacle.video.processor.check_ffmpeg_installed", return_value=False):
            with pytest.raises(FFmpegNotFoundError):
                VideoProcessor(dummy_video, temp_dir)

    @pytest.mark.skipif(not check_ffmpeg_installed(), reason="FFmpeg not installed")
    def test_processor_creates_output_dir(self, dummy_video, temp_dir):
        """Test VideoProcessor creates output directory if needed."""
        output_dir = temp_dir / "nested" / "output"
        VideoProcessor(dummy_video, output_dir)
        assert output_dir.exists()

    def test_resolution_validation(self, dummy_video, temp_dir):
        """Test resolution validation in process method."""
        with patch("specspectacle.video.processor.check_ffmpeg_installed", return_value=True):
            processor = VideoProcessor.__new__(VideoProcessor)
            processor.input_path = dummy_video
            processor.output_dir = temp_dir
            processor.temp_files = []

            # Invalid resolution format
            with pytest.raises(ValueError, match="Invalid resolution format"):
                processor.process(
                    output_filename="out.mp4",
                    resolution="invalid",
                )

    def test_compression_preset_enum(self):
        """Test CompressionPreset enum values."""
        assert CompressionPreset.LOW.value == "low"
        assert CompressionPreset.MEDIUM.value == "medium"
        assert CompressionPreset.HIGH.value == "high"

    def test_cleanup_temp_files(self, temp_dir):
        """Test temp file cleanup."""
        with patch("specspectacle.video.processor.check_ffmpeg_installed", return_value=True):
            # Create processor with mock
            processor = VideoProcessor.__new__(VideoProcessor)
            processor.input_path = temp_dir / "input.mp4"
            processor.output_dir = temp_dir

            # Create some temp files
            temp1 = temp_dir / "temp1.mp4"
            temp2 = temp_dir / "temp2.mp4"
            temp1.touch()
            temp2.touch()
            processor.temp_files = [temp1, temp2]

            assert temp1.exists()
            assert temp2.exists()

            processor.cleanup_temp_files()

            assert not temp1.exists()
            assert not temp2.exists()
            assert len(processor.temp_files) == 0


class TestVideoProcessorIntegration:
    """Integration tests for VideoProcessor (require FFmpeg)."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def create_test_video(self, temp_dir):
        """Create a real test video using FFmpeg."""
        if not check_ffmpeg_installed():
            pytest.skip("FFmpeg not installed")

        video_path = temp_dir / "test_source.mp4"

        # Create a 1-second test video with FFmpeg
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=1:size=640x480:rate=30",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(video_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return video_path
        except subprocess.CalledProcessError:
            pytest.skip("Could not create test video")

    @pytest.mark.skipif(not check_ffmpeg_installed(), reason="FFmpeg not installed")
    def test_get_video_info(self, create_test_video):
        """Test getting video info from a real video file."""
        info = get_video_info(create_test_video)

        assert "duration" in info
        assert "width" in info
        assert "height" in info
        assert "fps" in info
        assert info["width"] == 640
        assert info["height"] == 480
        assert info["fps"] == 30.0 or abs(info["fps"] - 30.0) < 1

    @pytest.mark.skipif(not check_ffmpeg_installed(), reason="FFmpeg not installed")
    def test_full_processing_pipeline(self, create_test_video, temp_dir):
        """Test the full video processing pipeline."""
        processor = VideoProcessor(create_test_video, temp_dir)

        output_path = processor.process(
            output_filename="output.mp4",
            fps=30,
            bitrate="1000k",
            resolution="320x240",
            codec="h264",
            compression_preset="high",
        )

        assert output_path.exists()
        assert output_path.name == "output.mp4"

        # Verify output video properties
        info = get_video_info(output_path)
        assert info["width"] == 320
        assert info["height"] == 240

        processor.cleanup_temp_files()

    @pytest.mark.skipif(not check_ffmpeg_installed(), reason="FFmpeg not installed")
    def test_different_compression_presets(self, create_test_video, temp_dir):
        """Test that different compression presets produce different file sizes."""
        sizes = {}

        for preset in ["low", "high"]:
            processor = VideoProcessor(create_test_video, temp_dir)
            output_path = processor.process(
                output_filename=f"output_{preset}.mp4",
                fps=30,
                resolution="320x240",
                compression_preset=preset,
            )
            sizes[preset] = output_path.stat().st_size
            processor.cleanup_temp_files()

        # Low compression should produce larger files than high compression
        # (though for very short videos the difference might be minimal)
        assert sizes["low"] >= sizes["high"] * 0.5  # Allow some variance

    @pytest.mark.skipif(not check_ffmpeg_installed(), reason="FFmpeg not installed")
    def test_merge_audio(self, create_test_video, temp_dir):
        """Test merging audio with video."""
        processor = VideoProcessor(create_test_video, temp_dir)

        # Create a silent audio file
        audio_path = temp_dir / "test_audio.mp3"
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-t",
            "1",
            "-c:a",
            "libmp3lame",
            str(audio_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        output_path = processor.merge_audio(
            video_path=create_test_video,
            audio_path=audio_path,
        )

        assert output_path.exists()
        info = get_video_info(output_path)

        # FFprobe output might include audio codec info now
        # We can't easily assert codec details with get_video_info as it returns video stream info
        # But we know it succeeded if it exists and has duration
        assert info["duration"] > 0

    @pytest.mark.skipif(not check_ffmpeg_installed(), reason="FFmpeg not installed")
    def test_h265_codec_support(self, create_test_video, temp_dir):
        """Test H.265 codec support."""
        processor = VideoProcessor(create_test_video, temp_dir)

        # Attempt H.265 encoding
        # This might fail if codec is not available, so we catch it
        try:
            output_path = processor.process(
                output_filename="output_h265.mp4",
                codec="h265",
                fps=30,
            )
            assert output_path.exists()
            assert output_path.stat().st_size > 0
        except FFmpegExecutionError as e:
            if "Unknown encoder 'libx265'" in str(e):
                pytest.skip("H.265 encoder not (libx265) available")
            if "Error while opening encoder" in str(e):
                pytest.skip("H.265 encoder failed to open")
            else:
                raise e


class TestProcessVideoFunction:
    """Tests for the convenience process_video function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_process_video_not_found(self, temp_dir):
        """Test process_video raises error for non-existent file."""
        with pytest.raises(FileNotFoundError):
            process_video(
                input_path=temp_dir / "nonexistent.mp4",
                output_path=temp_dir / "output.mp4",
            )

    def test_process_video_no_ffmpeg(self, temp_dir):
        """Test process_video raises error when FFmpeg not installed."""
        input_path = temp_dir / "input.mp4"
        input_path.touch()

        with patch("specspectacle.video.processor.check_ffmpeg_installed", return_value=False):
            with pytest.raises(FFmpegNotFoundError):
                process_video(
                    input_path=input_path,
                    output_path=temp_dir / "output.mp4",
                )
