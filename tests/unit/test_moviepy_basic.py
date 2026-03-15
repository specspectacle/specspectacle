import os

import pytest
from moviepy.editor import ColorClip, VideoFileClip


def test_moviepy_installation():
    """Verify that moviepy is installed and can be imported."""
    import moviepy.editor as mpy
    assert mpy.VideoFileClip is not None

def test_video_load_moviepy():
    """Verify that moviepy can load an existing video file."""
    # Use an existing video from the output directory
    video_path = "output/videos/login_demo.mp4"
    if not os.path.exists(video_path):
        pytest.skip(f"Test video {video_path} not found")

    clip = VideoFileClip(video_path)
    assert clip.duration > 0
    clip.close()

def test_color_clip_generation():
    """Verify that moviepy can generate and save a basic clip."""
    clip = ColorClip(size=(640, 480), color=(255, 0, 0), duration=2)
    assert clip.duration == 2
    assert tuple(clip.size) == (640, 480)
    # Check if we can get a frame (verifies numpy/pillow integration)
    frame = clip.get_frame(0)
    assert frame.shape == (480, 640, 3)
    clip.close()
