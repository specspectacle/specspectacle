import os
from pathlib import Path

import pytest


@pytest.fixture
def temp_output_dir(tmp_path):
    d = tmp_path / "output"
    d.mkdir()
    return d

@pytest.fixture
def sample_video():
    video_path = "output/videos/login_demo.mp4"
    if not os.path.exists(video_path):
        pytest.skip(f"Sample video {video_path} not found")
    return Path(video_path)

def test_processor_initialization(sample_video, temp_output_dir):
    from specspectacle.video.moviepy_processor import MoviePyProcessor
    processor = MoviePyProcessor(sample_video, temp_output_dir)
    assert processor.input_path == sample_video
    assert processor.output_dir == temp_output_dir

def test_process_pipeline_basic(sample_video, temp_output_dir):
    from specspectacle.video.moviepy_processor import MoviePyProcessor
    processor = MoviePyProcessor(sample_video, temp_output_dir)
    output_filename = "test_output.mp4"

    # Process with basic settings
    # We use a very short subclip if possible to speed up tests
    output_path = processor.process(
        output_filename=output_filename,
        fps=10,
        resolution="320x180"
    )

    assert output_path.exists()
    assert output_path.name == output_filename

    # Verify properties of output video
    from moviepy.editor import VideoFileClip
    clip = VideoFileClip(str(output_path))
    assert clip.fps == 10
    assert tuple(clip.size) == (320, 180)
    clip.close()

def test_merge_audio(sample_video, temp_output_dir):
    from specspectacle.video.moviepy_processor import MoviePyProcessor
    processor = MoviePyProcessor(sample_video, temp_output_dir)

    # Create a dummy audio file using moviepy
    audio_path = temp_output_dir / "test_audio.mp3"
    import numpy as np
    from moviepy.audio.AudioClip import AudioArrayClip

    # Generate 1 second of silence/tone (stereo)
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration))
    # Create a 2D array for stereo (samples, channels)
    audio_array = np.sin(2 * np.pi * 440 * t).reshape(-1, 1)
    audio_array = np.column_stack((audio_array, audio_array))

    audio_clip = AudioArrayClip(audio_array, fps=sr)
    audio_clip.write_audiofile(str(audio_path), logger=None)

    output_path = temp_output_dir / "merged_output.mp4"
    result_path = processor.merge_audio(sample_video, audio_path, output_path)

    assert result_path.exists()
    from moviepy.editor import VideoFileClip
    clip = VideoFileClip(str(result_path))
    assert clip.audio is not None
    clip.close()
