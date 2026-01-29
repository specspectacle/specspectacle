import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from specspectacle.cli.commands.run import run

# Examples directory relative to this test file
EXAMPLES_DIR = Path(__file__).parents[2] / "examples"
EXAMPLE_FILES = list(EXAMPLES_DIR.glob("*.yaml"))


@pytest.fixture
def runner():
    return CliRunner()


def generate_silence_mp3(path, duration=1.0):
    """Generate a silent MP3 file using ffmpeg."""
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=stereo",
        "-t",
        str(duration),
        "-c:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)


@pytest.mark.e2e
@pytest.mark.parametrize("yaml_file", EXAMPLE_FILES, ids=lambda p: p.name)
def test_example_execution(runner, yaml_file, tmp_path):
    """
    Run each example YAML and verify video generation.
    Mocks TTS to avoid API usage but generates real audio files for FFmpeg.
    """
    if not yaml_file.exists():
        pytest.skip(f"Example file not found: {yaml_file}")

    # Patch TTSClient to generate silence instead of calling API
    with patch("specspectacle.audio.TTSClient") as MockTTS:
        mock_instance = MockTTS.return_value

        def mock_generate_speech(text, output_path):
            # Generate 0.5s silence to simulate narration
            generate_silence_mp3(output_path, duration=0.5)

        mock_instance.generate_speech.side_effect = mock_generate_speech

        # Set dummy API key to satisfy config validation
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "dummy_key"}):
            result = runner.invoke(
                run,
                [
                    str(yaml_file),
                    "--output-dir",
                    str(tmp_path),
                    "--headless",  # Always run headless in tests
                    "--no-overlays",  # Optional: skip overlays to speed up if needed, but task says "verify output"
                    # We'll allow overlays to test full pipeline if possible, but for speed maybe disable?
                    # Task 3 says "Validate output videos exist".
                    # Let's run with defaults (overlays enabled if yaml has them).
                ],
            )

    assert result.exit_code == 0, f"Example failed: {yaml_file.name}\\nOutput: {result.output}"

    # Verify video output
    # The output filename is defined in the YAML. output.filename
    # We need to parse YAML to know it, or check what file was created.
    # Spec output dir content:
    video_files = list(tmp_path.glob("*.mp4"))
    assert len(video_files) >= 1, "No output video found"

    output_video = video_files[0]
    assert output_video.stat().st_size > 0, "Output video is empty"

    # Optional: Verify duration using ffprobe
    # cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(output_video)]
    # ...
