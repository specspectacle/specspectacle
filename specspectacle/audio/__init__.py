"""
Audio module for TTS and narration generation.

This module provides text-to-speech capabilities and audio timeline
building for synchronized narration in demo videos.
"""

from specspectacle.audio.audio_mixer import (
    AudioConcatenator,
    AudioGenerator,
    AudioSegment,
    AudioTimeline,
)
from specspectacle.audio.tts import (
    TTSAPIError,
    TTSClient,
    TTSConfig,
    TTSConfigError,
    TTSError,
)

__all__ = [
    # TTS Client
    "TTSClient",
    "TTSConfig",
    "TTSError",
    "TTSAPIError",
    "TTSConfigError",
    # Audio Timeline
    "AudioSegment",
    "AudioTimeline",
    "AudioGenerator",
    "AudioConcatenator",
]
