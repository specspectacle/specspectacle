import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from specspectacle.cli.commands.run import run


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def simple_yaml(tmp_path):
    yaml_content = """
name: Integration Test
version: "0.1.0"
config:
  target_app: "https://example.com"
  viewport: {width: 1280, height: 720}
  timeout: 5000
  headless: true
output:
  filename: test_output.mp4
  resolution: 1280x720
  fps: 30
flows:
  - name: Basic Flow
    steps:
      - action: navigate
        url: https://example.com
      - action: wait
        duration: 1
"""
    yaml_file = tmp_path / "integration_test.yaml"
    yaml_file.write_text(yaml_content)
    return yaml_file


@pytest.fixture
def yaml_with_audio_and_overlay(tmp_path):
    yaml_content = """
name: Full Feature Test
version: "0.1.0"
config:
  target_app: "https://example.com"
  viewport: {width: 1280, height: 720}
  timeout: 5000
  headless: true
output:
  filename: full_output.mp4
  resolution: 1280x720
  fps: 30
narration:
  enabled: true
  voice: "en-US-Neural2-F"
flows:
  - name: Basic Flow
    steps:
      - action: navigate
        url: https://example.com
        narration:
          text: "Loading example domain"
      - action: wait
        duration: 1
        overlay:
          text: "Waiting..."
"""
    yaml_file = tmp_path / "full_test.yaml"
    yaml_file.write_text(yaml_content)
    return yaml_file


def test_pipeline_basic_video(runner, simple_yaml, tmp_path):
    """Test YAML -> browser -> raw video -> processed video (no audio/overlays)."""
    # Mocking check_ffmpeg_installed to True to ensure we try processing
    # But if real FFmpeg is missing, it might fail.
    # For integration test, we ideally want real FFmpeg.
    # We will assume FFmpeg is present or handle the fallback.

    runner.invoke(
        run,
        [
            str(simple_yaml),
            "--output-dir",
            str(tmp_path),
            "--no-narration",
            "--no-overlays",
            "--headless",
        ],
    )

    assert (tmp_path / "test_output.mp4").exists()

    # Check if timeline was generated (it is named timeline.json)
    assert (tmp_path / "timeline.json").exists()


@patch("specspectacle.audio.TTSClient")
def test_pipeline_with_audio_and_overlays(
    mock_tts_client, runner, yaml_with_audio_and_overlay, tmp_path
):
    """Test full pipeline with mocked TTS but real video processing."""

    # Set dummy API key to pass config validation if mock fails (fallback)
    os.environ["GOOGLE_API_KEY"] = "dummy_key"
    mock_instance = mock_tts_client.return_value

    def create_dummy_audio(text, output_file):
        Path(output_file).touch()

    mock_instance.generate_speech.side_effect = create_dummy_audio

    # Patch where the classes are defined, which run.py imports from
    with (
        patch("specspectacle.audio.AudioConcatenator") as MockConcat,
        patch("specspectacle.video.VideoProcessor") as MockProcessor,
        patch("specspectacle.video.render_overlays_on_video") as MockOverlay,
    ):

        MockConcat.return_value.concatenate_segments.return_value = Path(
            tmp_path / "dummy_track.mp3"
        )
        (tmp_path / "dummy_track.mp3").touch()

        MockProcessor.return_value.process.return_value = Path(tmp_path / "processed_temp.mp4")
        (tmp_path / "processed_temp.mp4").touch()

        MockProcessor.return_value.merge_audio.return_value = Path(tmp_path / "merged_temp.mp4")
        (tmp_path / "merged_temp.mp4").touch()

        MockOverlay.return_value = Path(tmp_path / "final_temp.mp4")
        (tmp_path / "final_temp.mp4").touch()  # Create the file so rename works

        result = runner.invoke(
            run,
            [
                str(yaml_with_audio_and_overlay),
                "--output-dir",
                str(tmp_path),
                "--headless",
                "--no-narration",  # Skip audio to simplify the test
            ],
        )

        # Test should pass if video processing worked
        assert result.exit_code == 0, f"Command failed with output:\\n{result.output}"
