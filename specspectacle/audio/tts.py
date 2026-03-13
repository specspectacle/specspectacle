"""
Text-to-Speech client using Edge TTS (Microsoft Edge's TTS service).

This module provides the TTSClient class for generating speech audio
from text using edge-tts, a free alternative to paid TTS services.
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

import edge_tts

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TTSConfig:
    """Configuration for TTS generation."""

    voice_name: str = "en-US-AriaNeural"  # Default voice (Microsoft Edge voice)
    rate: str = "+0%"  # Speech rate: -50% to +100%
    volume: str = "+0%"  # Volume: -50% to +50%
    pitch: str = "+0Hz"  # Pitch adjustment
    max_retries: int = 3
    retry_delay: float = 1.0
    max_text_length: int = 5000


class TTSError(Exception):
    """Base exception for TTS-related errors."""

    pass


class TTSConfigError(TTSError):
    """Raised when configuration is invalid."""

    pass


class TTSAPIError(TTSError):
    """Raised when the TTS API call fails."""

    pass


class TTSClient:
    """
    Production-grade Text-to-Speech generator using Edge TTS.

    Edge TTS is a free alternative that uses Microsoft Edge's online
    text-to-speech service. No API key required.
    """

    def __init__(self, voice: str | None = None, config: TTSConfig | None = None):
        """
        Initialize the TTS generator.

        Args:
            voice: Optional voice name override (e.g., "en-US-GuyNeural")
            config: Optional TTSConfig instance
        """
        # Default configuration
        self._config = config or TTSConfig()

        # Override voice if provided
        if voice:
            self._config = TTSConfig(
                voice_name=voice,
                rate=self._config.rate,
                volume=self._config.volume,
                pitch=self._config.pitch,
                max_retries=self._config.max_retries,
                retry_delay=self._config.retry_delay,
                max_text_length=self._config.max_text_length,
            )

        logger.info(f"TTSClient initialized with voice: {self._config.voice_name}")

    @property
    def config(self) -> TTSConfig:
        """Get the current TTS configuration."""
        return self._config

    def generate_speech(self, text: str, output_path: Path, voice: str | None = None) -> Path:
        """
        Generate speech audio from text.

        Args:
            text: Input text to convert to speech
            output_path: Destination path for output audio file
            voice: Optional voice name override

        Returns:
            Path to the generated audio file
        """
        if not text or not text.strip():
            raise ValueError("Text input cannot be empty")

        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Use configured voice or override
        voice_name = voice or self._config.voice_name

        logger.info(f"Generating speech for {len(text)} chars using voice {voice_name}")

        try:
            # Generate audio via Edge TTS (async wrapped in sync)
            asyncio.run(self._generate_audio_with_retry(text, voice_name, output_path))

            return output_path

        except Exception as e:
            # Cleanup output file on error
            if output_path.exists():
                output_path.unlink()
            logger.error(f"Speech generation failed: {e}")
            raise

    async def _generate_audio_with_retry(
        self, text: str, voice_name: str, output_path: Path
    ) -> None:
        """Generate audio with retry logic (async)."""
        last_exception = None

        for attempt in range(1, self._config.max_retries + 1):
            try:
                # Create Edge TTS communicator
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice_name,
                    rate=self._config.rate,
                    volume=self._config.volume,
                    pitch=self._config.pitch,
                )

                # Save audio to file
                await communicate.save(str(output_path))

                logger.info(f"Successfully generated audio: {output_path}")
                return

            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt} failed: {e}")
                if attempt < self._config.max_retries:
                    await asyncio.sleep(self._config.retry_delay * attempt)

        raise TTSError(
            f"Failed to generate audio after {self._config.max_retries} retries: {last_exception}"
        )

    def is_available(self) -> bool:
        """
        Check if Edge TTS is available.

        Returns:
            True if edge-tts can be used, False otherwise
        """
        try:
            # Simple check - edge_tts module is imported, so it's available
            # We could also test connectivity, but that adds latency
            return True
        except Exception as e:
            logger.error(f"Edge TTS not available: {e}")
            return False
