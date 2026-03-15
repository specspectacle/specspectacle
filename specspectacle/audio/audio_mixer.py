"""
Audio timeline builder and generator for narration synchronization.

This module provides classes for building audio timelines from YAML specs
and generating audio segments synchronized with video execution.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from moviepy.editor import AudioFileClip, CompositeAudioClip

from specspectacle.audio.tts import TTSClient, TTSError
from specspectacle.executor.timeline import Timeline, TimelineEvent

logger = logging.getLogger(__name__)


@dataclass
class AudioSegment:
    """
    Represents a single audio narration segment.

    Attributes:
        text: Narration text to be converted to speech
        timing: When to play relative to action (before/during/after)
        offset: Time offset in seconds from the timing point
        flow_name: Name of the parent flow
        flow_index: Index of the flow (1-indexed)
        step_index: Index of the step within flow (0 if flow-level narration)
        start_time: Calculated absolute start time in seconds
        end_time: Calculated absolute end time in seconds (after audio generation)
        output_path: Path where the audio file is saved
        duration: Duration of the generated audio in seconds
    """

    text: str
    timing: str  # "before", "during", "after"
    offset: float
    flow_name: str
    flow_index: int
    step_index: int = 0  # 0 means flow-level narration
    start_time: float | None = None
    end_time: float | None = None
    output_path: Path | None = None
    duration: float | None = None

    @staticmethod
    def estimate_duration(text: str) -> float:
        """
        Estimate the duration of speech for given text.

        Uses an approximate speaking rate calibrated for Edge TTS neural voices.
        Edge TTS speaks at roughly ~120 words per minute (2 words/second).
        Adds buffer for pauses and intonation.

        Args:
            text: The text to estimate duration for

        Returns:
            Estimated duration in seconds
        """
        if not text:
            return 0.5

        # Count words (roughly)
        word_count = len(text.split())

        # Edge TTS speaking rate: ~120 words per minute = 2 words per second
        # This is slower than average human speech to ensure clear narration
        words_per_second = 2.0
        duration = word_count / words_per_second

        # Add buffer for pauses, intonation, and audio encoding overhead
        buffer = 0.3

        # Minimum duration for very short texts
        min_duration = 0.5
        return max(duration + buffer, min_duration)

    def to_dict(self) -> dict:
        """Convert segment to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "timing": self.timing,
            "offset": self.offset,
            "flow_name": self.flow_name,
            "flow_index": self.flow_index,
            "step_index": self.step_index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "output_path": str(self.output_path) if self.output_path else None,
            "duration": self.duration,
        }


@dataclass
class AudioTimeline:
    """
    Timeline of audio segments parsed from a spec.

    This class parses narrations from a YAML spec and calculates their
    timing based on the execution timeline.

    Attributes:
        segments: List of audio segments
        spec_name: Name of the spec
    """

    spec_name: str
    segments: list[AudioSegment] = field(default_factory=list)

    @classmethod
    def from_spec_and_timeline(
        cls,
        spec: Any,  # SpecModel from parser.schema
        execution_timeline: Timeline,
    ) -> "AudioTimeline":
        """
        Build an AudioTimeline from a parsed spec and execution timeline.

        Args:
            spec: Parsed SpecModel with flows and steps
            execution_timeline: Timeline from browser execution

        Returns:
            AudioTimeline with calculated segment timings
        """
        audio_timeline = cls(spec_name=spec.name)

        # Get the baseline time for normalization (convert absolute timestamps to relative)
        timeline_start = execution_timeline.started_at or 0

        # Build a lookup for timeline events by flow and step index
        event_lookup: dict[tuple, TimelineEvent] = {}
        for event in execution_timeline.events:
            key = (event.flow_index, event.step_index)
            event_lookup[key] = event

        # Process each flow
        for flow_idx, flow in enumerate(spec.flows, start=1):
            # Flow-level narration
            if flow.narration:
                segment = cls._create_segment_from_narration(
                    narration=flow.narration,
                    flow_name=flow.name,
                    flow_index=flow_idx,
                    step_index=0,
                    events=execution_timeline.events,
                    event_lookup=event_lookup,
                    is_flow_level=True,
                    timeline_start=timeline_start,
                )
                if segment:
                    audio_timeline.segments.append(segment)

            # Step-level narrations
            for step_idx, step in enumerate(flow.steps, start=1):
                if hasattr(step, "narration") and step.narration:
                    segment = cls._create_segment_from_narration(
                        narration=step.narration,
                        flow_name=flow.name,
                        flow_index=flow_idx,
                        step_index=step_idx,
                        events=execution_timeline.events,
                        event_lookup=event_lookup,
                        is_flow_level=False,
                        timeline_start=timeline_start,
                    )
                    if segment:
                        audio_timeline.segments.append(segment)

        return audio_timeline

    @classmethod
    def _create_segment_from_narration(
        cls,
        narration: Any,  # NarrationModel
        flow_name: str,
        flow_index: int,
        step_index: int,
        events: list[TimelineEvent],
        event_lookup: dict[tuple, TimelineEvent],
        is_flow_level: bool,
        timeline_start: float,
    ) -> AudioSegment | None:
        """
        Create an AudioSegment from a narration with calculated timing.

        Uses narration_start_time from timeline event when available for
        accurate synchronization with video recording that included wait times.
        """
        timing = narration.timing
        offset = narration.offset

        # Try to get exact narration start time from timeline event
        start_time = None
        if not is_flow_level:
            event = event_lookup.get((flow_index, step_index))
            if event and event.narration_start_time is not None:
                # Use the exact start time recorded during execution
                start_time = (event.narration_start_time - timeline_start) + offset
                logger.debug(
                    f"Using recorded narration_start_time for flow {flow_index} step {step_index}: {start_time:.2f}s"
                )

        # Fall back to calculation if not available
        if start_time is None:
            start_time = cls._calculate_start_time(
                timing=timing,
                offset=offset,
                flow_index=flow_index,
                step_index=step_index,
                events=events,
                event_lookup=event_lookup,
                is_flow_level=is_flow_level,
                timeline_start=timeline_start,
            )

        return AudioSegment(
            text=narration.text,
            timing=timing,
            offset=offset,
            flow_name=flow_name,
            flow_index=flow_index,
            step_index=step_index,
            start_time=start_time,
        )

    @classmethod
    def _calculate_start_time(
        cls,
        timing: str,
        offset: float,
        flow_index: int,
        step_index: int,
        events: list[TimelineEvent],
        event_lookup: dict[tuple, TimelineEvent],
        is_flow_level: bool,
        timeline_start: float,
    ) -> float:
        """
        Calculate the relative start time for a narration segment.

        Returns time in seconds relative to timeline start (not Unix timestamp).

        For flow-level narrations:
        - "before": Before the first step of the flow starts
        - "during": When the first step starts
        - "after": After the last step of the flow ends

        For step-level narrations:
        - "before": Before the step starts
        - "during": When the step starts
        - "after": After the step ends
        """
        if is_flow_level:
            # Find first and last events of this flow
            flow_events = [e for e in events if e.flow_index == flow_index]
            if not flow_events:
                return offset

            first_event = min(flow_events, key=lambda e: e.start_time)
            last_event = max(flow_events, key=lambda e: e.end_time)

            # Normalize timestamps to relative time (subtract timeline_start)
            if timing == "before" or timing == "during":
                return (first_event.start_time - timeline_start) + offset
            else:  # after
                return (last_event.end_time - timeline_start) + offset
        else:
            # Find the specific step event
            event = event_lookup.get((flow_index, step_index))
            if not event:
                return offset

            # Normalize timestamps to relative time (subtract timeline_start)
            if timing == "before" or timing == "during":
                return (event.start_time - timeline_start) + offset
            else:  # after
                return (event.end_time - timeline_start) + offset

    def get_segments(self) -> list[AudioSegment]:
        """Get all audio segments sorted by start time."""
        return sorted(self.segments, key=lambda s: s.start_time or 0)

    def to_dict(self) -> dict:
        """Convert timeline to dictionary for JSON serialization."""
        return {
            "spec_name": self.spec_name,
            "total_segments": len(self.segments),
            "segments": [s.to_dict() for s in self.get_segments()],
        }


class AudioGenerator:
    """
    Generates audio files for all segments in an AudioTimeline.

    This class uses the TTSClient to generate speech for each segment
    and tracks the output files and durations.
    """

    def __init__(
        self,
        tts_client: TTSClient,
        output_dir: Path,
    ):
        """
        Initialize the audio generator.

        Args:
            tts_client: TTS client for generating speech
            output_dir: Directory to save generated audio files
        """
        self.tts_client = tts_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_audio_segments(
        self,
        audio_timeline: AudioTimeline,
        skip_generation: bool = False,
    ) -> list[AudioSegment]:
        """
        Generate audio files for all segments in the timeline.

        Args:
            audio_timeline: Timeline with segments to generate
            skip_generation: If True, skip TTS generation (for --no-narration)

        Returns:
            List of AudioSegments with updated output paths and durations
        """
        if skip_generation:
            logger.info("Skipping audio generation (--no-narration flag)")
            return audio_timeline.segments

        generated_segments = []

        for idx, segment in enumerate(audio_timeline.get_segments()):
            try:
                output_path = self._generate_segment(segment, idx)
                segment.output_path = output_path
                segment.duration = self._get_audio_duration(output_path)
                segment.end_time = (segment.start_time or 0) + (segment.duration or 0)
                generated_segments.append(segment)
                logger.info(
                    f"Generated audio segment {idx + 1}/{len(audio_timeline.segments)}: "
                    f"{segment.text[:30]}..."
                )
            except TTSError as e:
                logger.warning(
                    f"Failed to generate audio for segment {idx + 1}: {e}. "
                    "Continuing without this segment."
                )
                # Don't add failed segments to the list

        return generated_segments

    def _generate_segment(self, segment: AudioSegment, index: int) -> Path:
        """Generate audio for a single segment."""
        filename = f"narration_{segment.flow_index:02d}_{segment.step_index:02d}_{index:03d}.mp3"
        output_path = self.output_dir / filename

        self.tts_client.generate_speech(
            text=segment.text,
            output_path=output_path,
        )

        return output_path

    def _get_audio_duration(self, audio_path: Path) -> float:
        """
        Get the duration of an audio file in seconds.

        Uses FFmpeg to probe the audio file.
        """
        try:
            import subprocess

            result = subprocess.run(
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
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError, FileNotFoundError) as e:
            logger.warning(f"Could not determine audio duration: {e}")
            # Estimate duration based on text length (rough approximation)
            # Average speaking rate is about 150 words per minute
            return 2.0  # Default fallback duration


class AudioConcatenator:
    """
    Concatenates audio segments into a single audio track using MoviePy.

    This class takes generated audio segments with their timing information
    and creates a single audio file that matches the video duration.
    """

    def __init__(self, output_dir: Path):
        """
        Initialize the audio concatenator.

        Args:
            output_dir: Directory for temporary and output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def concatenate_segments(
        self,
        segments: list[AudioSegment],
        video_duration: float,
        output_path: Path,
    ) -> Path:
        """
        Concatenate audio segments into a single audio track using MoviePy.

        Args:
            segments: List of AudioSegments with output_path and start_time set
            video_duration: Total duration of the video in seconds
            output_path: Path for the final concatenated audio file

        Returns:
            Path to the concatenated audio file
        """
        if not segments:
            logger.info("No audio segments to concatenate, generating silent track")
            return self._generate_silence_track(video_duration, output_path)

        # Sort segments by start time
        sorted_segments = sorted(segments, key=lambda s: s.start_time or 0)

        # Filter out segments without output files
        valid_segments = [
            s for s in sorted_segments if s.output_path and Path(s.output_path).exists()
        ]

        if not valid_segments:
            logger.warning("No valid audio segments found, generating silent track")
            return self._generate_silence_track(video_duration, output_path)

        logger.info(f"Mixing {len(valid_segments)} audio segments with MoviePy")

        # Create MoviePy AudioFileClips
        audio_clips = []
        for segment in valid_segments:
            try:
                clip = AudioFileClip(str(segment.output_path)).set_start(segment.start_time or 0)
                audio_clips.append(clip)
            except Exception as e:
                logger.warning(f"Failed to load audio segment {segment.output_path}: {e}")

        if not audio_clips:
            return self._generate_silence_track(video_duration, output_path)

        # Compose the audio timeline
        final_audio = CompositeAudioClip(audio_clips)

        # Ensure final audio is exactly video_duration
        # Note: CompositeAudioClip duration is the end of the last clip by default.
        # We can set the duration to video_duration.
        final_audio = final_audio.set_duration(video_duration)

        # Export the final audio
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Writing concatenated audio to {output_path}")
        final_audio.write_audiofile(
            str(output_path),
            fps=44100,
            nbytes=2,
            codec="libmp3lame",
            logger=None
        )

        # Close clips to free resources
        for clip in audio_clips:
            clip.close()
        final_audio.close()

        return output_path

    def _generate_silence_track(self, duration: float, output_path: Path) -> Path:
        """
        Generate a silent audio track of the specified duration using FFmpeg.

        Keep this as a fallback for generating long silence more efficiently.
        """
        import subprocess

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

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
            str(output_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to generate silence: {e.stderr}")
            raise RuntimeError(f"Silence generation failed: {e.stderr}")

    def cleanup(self) -> None:
        """Cleanup is now mostly handled by clip.close() but we can clean temp files if any."""
        pass


__all__ = [
    "AudioSegment",
    "AudioTimeline",
    "AudioGenerator",
    "AudioConcatenator",
]
