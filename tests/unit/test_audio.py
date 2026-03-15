"""Unit tests for audio module (TTS client and audio timeline builder)."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
    TTSError,
)
from specspectacle.executor.timeline import Timeline, TimelineEvent


class TestTTSConfig:
    """Tests for TTSConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TTSConfig()
        assert config.voice_name == "en-US-AriaNeural"
        assert config.rate == "+0%"
        assert config.volume == "+0%"
        assert config.pitch == "+0Hz"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = TTSConfig(voice_name="en-GB-SoniaNeural", rate="+50%", volume="+10%", pitch="+5Hz")
        assert config.voice_name == "en-GB-SoniaNeural"
        assert config.rate == "+50%"
        assert config.volume == "+10%"
        assert config.pitch == "+5Hz"


class TestTTSClient:
    """Tests for TTSClient class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_init_default(self):
        """Test client initialization with defaults."""
        client = TTSClient()
        assert client.config.voice_name == "en-US-AriaNeural"

    def test_init_with_voice_override(self):
        """Test client initialization with voice override."""
        client = TTSClient(voice="en-GB-SoniaNeural")
        assert client.config.voice_name == "en-GB-SoniaNeural"

    def test_init_with_custom_config(self):
        """Test client initialization with custom config."""
        config = TTSConfig(voice_name="en-US-GuyNeural", rate="+50%")
        client = TTSClient(config=config)
        assert client.config.voice_name == "en-US-GuyNeural"
        assert client.config.rate == "+50%"

    def test_generate_speech_empty_text_raises_error(self, temp_dir):
        """Test generate_speech raises error for empty text."""
        client = TTSClient()
        with pytest.raises(ValueError, match="Text input cannot be empty"):
            client.generate_speech("", temp_dir / "output.mp3")

    def test_generate_speech_whitespace_text_raises_error(self, temp_dir):
        """Test generate_speech raises error for whitespace-only text."""
        client = TTSClient()
        with pytest.raises(ValueError, match="Text input cannot be empty"):
            client.generate_speech("   ", temp_dir / "output.mp3")

    @patch("edge_tts.Communicate")
    def test_generate_speech_success(self, mock_communicate_class, temp_dir):
        """Test successful speech generation."""
        output_path = temp_dir / "output.mp3"

        # Mock the Communicate instance and its save method
        async def mock_save(path):
            # Create the file to simulate success
            Path(path).touch()

        mock_communicate = MagicMock()
        mock_communicate.save = mock_save
        mock_communicate_class.return_value = mock_communicate

        client = TTSClient()
        result = client.generate_speech("Hello, world!", output_path)

        # Both paths should be equal when resolved
        assert result.resolve() == output_path.resolve()
        assert output_path.exists()
        mock_communicate_class.assert_called_once()

    @patch("edge_tts.Communicate")
    @patch("asyncio.sleep", new_callable=AsyncMock)
    def test_generate_speech_retry_on_failure(self, mock_sleep, mock_communicate_class, temp_dir):
        """Test retry logic on API failure."""
        output_path = temp_dir / "output.mp3"

        # Track call count
        call_count = 0

        async def mock_save_with_retries(path):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"API Error {call_count}")
            # Success on third try
            Path(path).touch()

        mock_communicate = MagicMock()
        mock_communicate.save = mock_save_with_retries
        mock_communicate_class.return_value = mock_communicate

        client = TTSClient()
        result = client.generate_speech("Hello!", output_path)

        assert result.resolve() == output_path.resolve()
        assert call_count == 3

    @patch("edge_tts.Communicate")
    def test_generate_speech_max_retries_exceeded(self, mock_communicate_class, temp_dir):
        """Test TTSError raised after max retries."""
        output_path = temp_dir / "output.mp3"

        async def mock_save_always_fails(path):
            raise Exception("Persistent API Error")

        mock_communicate = MagicMock()
        mock_communicate.save = mock_save_always_fails
        mock_communicate_class.return_value = mock_communicate

        client = TTSClient()

        with pytest.raises(TTSError, match="Failed to generate audio"):
            client.generate_speech("Hello!", output_path)

    def test_is_available(self):
        """Test is_available returns True for Edge TTS."""
        client = TTSClient()
        assert client.is_available() is True


class TestAudioSegment:
    """Tests for AudioSegment dataclass."""

    def test_segment_creation(self):
        """Test creating an audio segment."""
        segment = AudioSegment(
            text="Hello, world!",
            timing="during",
            offset=0.5,
            flow_name="Login Flow",
            flow_index=1,
            step_index=2,
        )
        assert segment.text == "Hello, world!"
        assert segment.timing == "during"
        assert segment.offset == 0.5
        assert segment.flow_name == "Login Flow"
        assert segment.flow_index == 1
        assert segment.step_index == 2

    def test_segment_defaults(self):
        """Test segment default values."""
        segment = AudioSegment(
            text="Test",
            timing="before",
            offset=0.0,
            flow_name="Flow",
            flow_index=1,
        )
        assert segment.step_index == 0
        assert segment.start_time is None
        assert segment.end_time is None
        assert segment.output_path is None
        assert segment.duration is None

    def test_segment_to_dict(self):
        """Test segment serialization to dictionary."""
        segment = AudioSegment(
            text="Test text",
            timing="after",
            offset=1.0,
            flow_name="Test Flow",
            flow_index=2,
            step_index=3,
            start_time=5.0,
            end_time=7.0,
            output_path=Path("/tmp/test.mp3"),
            duration=2.0,
        )
        d = segment.to_dict()

        assert d["text"] == "Test text"
        assert d["timing"] == "after"
        assert d["offset"] == 1.0
        assert d["flow_index"] == 2
        assert d["step_index"] == 3
        assert d["start_time"] == 5.0
        assert d["end_time"] == 7.0
        assert d["output_path"] == "/tmp/test.mp3"
        assert d["duration"] == 2.0


class TestAudioTimeline:
    """Tests for AudioTimeline class."""

    @pytest.fixture
    def mock_spec(self):
        """Create a mock spec with narrations."""
        # Mock NarrationModel
        flow_narration = MagicMock()
        flow_narration.text = "This is the login flow."
        flow_narration.timing = "before"
        flow_narration.offset = 0.0

        step_narration = MagicMock()
        step_narration.text = "Click the login button."
        step_narration.timing = "during"
        step_narration.offset = 0.5

        # Mock step with narration
        step = MagicMock()
        step.narration = step_narration

        # Mock step without narration
        step_no_narration = MagicMock()
        step_no_narration.narration = None

        # Mock flow
        flow = MagicMock()
        flow.name = "Login Flow"
        flow.narration = flow_narration
        flow.steps = [step_no_narration, step]  # Step with narration is at index 2 (1-indexed)

        # Mock spec
        spec = MagicMock()
        spec.name = "Demo Spec"
        spec.flows = [flow]

        return spec

    @pytest.fixture
    def mock_timeline(self):
        """Create a mock execution timeline."""
        timeline = Timeline(spec_name="Demo Spec")
        timeline.started_at = 0.0

        # Add events for the steps
        timeline.add_event(
            TimelineEvent(
                step_name="Step 1",
                action="click",
                start_time=1.0,
                end_time=2.0,
                duration=1.0,
                flow_name="Login Flow",
                flow_index=1,
                step_index=1,
            )
        )
        timeline.add_event(
            TimelineEvent(
                step_name="Step 2",
                action="click",
                start_time=2.5,
                end_time=3.5,
                duration=1.0,
                flow_name="Login Flow",
                flow_index=1,
                step_index=2,
            )
        )

        timeline.completed_at = 4.0
        return timeline

    def test_from_spec_and_timeline_basic(self, mock_spec, mock_timeline):
        """Test building audio timeline from spec and execution timeline."""
        audio_timeline = AudioTimeline.from_spec_and_timeline(mock_spec, mock_timeline)

        assert audio_timeline.spec_name == "Demo Spec"
        assert len(audio_timeline.segments) == 2  # Flow narration + step narration

    def test_from_spec_and_timeline_flow_narration(self, mock_spec, mock_timeline):
        """Test flow-level narration is captured."""
        audio_timeline = AudioTimeline.from_spec_and_timeline(mock_spec, mock_timeline)

        flow_segments = [s for s in audio_timeline.segments if s.step_index == 0]
        assert len(flow_segments) == 1
        assert flow_segments[0].text == "This is the login flow."
        assert flow_segments[0].timing == "before"

    def test_from_spec_and_timeline_step_narration(self, mock_spec, mock_timeline):
        """Test step-level narration is captured."""
        audio_timeline = AudioTimeline.from_spec_and_timeline(mock_spec, mock_timeline)

        step_segments = [s for s in audio_timeline.segments if s.step_index > 0]
        assert len(step_segments) == 1
        assert step_segments[0].text == "Click the login button."
        assert step_segments[0].timing == "during"
        assert step_segments[0].step_index == 2

    def test_timing_calculation_before(self, mock_spec, mock_timeline):
        """Test 'before' timing calculates correct start time."""
        audio_timeline = AudioTimeline.from_spec_and_timeline(mock_spec, mock_timeline)

        # Flow narration with timing="before" should start at first event's start_time
        flow_segment = [s for s in audio_timeline.segments if s.step_index == 0][0]
        assert flow_segment.start_time == 1.0  # First event starts at 1.0

    def test_timing_calculation_during_with_offset(self, mock_spec, mock_timeline):
        """Test 'during' timing with offset calculates correct start time."""
        audio_timeline = AudioTimeline.from_spec_and_timeline(mock_spec, mock_timeline)

        # Step narration with timing="during", offset=0.5
        step_segment = [s for s in audio_timeline.segments if s.step_index == 2][0]
        # Step 2 starts at 2.5, offset is 0.5
        assert step_segment.start_time == 3.0

    def test_get_segments_sorted(self, mock_spec, mock_timeline):
        """Test get_segments returns segments sorted by start time."""
        audio_timeline = AudioTimeline.from_spec_and_timeline(mock_spec, mock_timeline)
        segments = audio_timeline.get_segments()

        start_times = [s.start_time for s in segments]
        assert start_times == sorted(start_times)

    def test_to_dict(self, mock_spec, mock_timeline):
        """Test timeline serialization to dictionary."""
        audio_timeline = AudioTimeline.from_spec_and_timeline(mock_spec, mock_timeline)
        d = audio_timeline.to_dict()

        assert d["spec_name"] == "Demo Spec"
        assert d["total_segments"] == 2
        assert len(d["segments"]) == 2

    def test_empty_spec_no_narrations(self, mock_timeline):
        """Test handling spec with no narrations."""
        # Mock spec with no narrations
        step = MagicMock()
        step.narration = None

        flow = MagicMock()
        flow.name = "Empty Flow"
        flow.narration = None
        flow.steps = [step]

        spec = MagicMock()
        spec.name = "Empty Spec"
        spec.flows = [flow]

        audio_timeline = AudioTimeline.from_spec_and_timeline(spec, mock_timeline)
        assert len(audio_timeline.segments) == 0


class TestAudioGenerator:
    """Tests for AudioGenerator class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_tts_client(self):
        """Create a mock TTS client."""
        client = MagicMock(spec=TTSClient)
        client.generate_speech.return_value = Path("/tmp/test.mp3")
        return client

    @pytest.fixture
    def sample_audio_timeline(self):
        """Create a sample audio timeline with segments."""
        timeline = AudioTimeline(spec_name="Test Spec")
        timeline.segments = [
            AudioSegment(
                text="First narration",
                timing="before",
                offset=0.0,
                flow_name="Flow 1",
                flow_index=1,
                step_index=0,
                start_time=0.0,
            ),
            AudioSegment(
                text="Second narration",
                timing="during",
                offset=0.0,
                flow_name="Flow 1",
                flow_index=1,
                step_index=1,
                start_time=2.0,
            ),
        ]
        return timeline

    def test_generator_initialization(self, mock_tts_client, temp_dir):
        """Test AudioGenerator initialization."""
        generator = AudioGenerator(mock_tts_client, temp_dir)
        assert generator.tts_client == mock_tts_client
        assert generator.output_dir == temp_dir

    def test_generator_creates_output_dir(self, mock_tts_client, temp_dir):
        """Test AudioGenerator creates output directory."""
        nested_dir = temp_dir / "nested" / "audio"
        AudioGenerator(mock_tts_client, nested_dir)
        assert nested_dir.exists()

    @patch.object(AudioGenerator, "_get_audio_duration", return_value=2.5)
    def test_generate_audio_segments(
        self, mock_duration, mock_tts_client, temp_dir, sample_audio_timeline
    ):
        """Test generating audio for all segments."""
        generator = AudioGenerator(mock_tts_client, temp_dir)
        segments = generator.generate_audio_segments(sample_audio_timeline)

        assert len(segments) == 2
        assert mock_tts_client.generate_speech.call_count == 2

        # Check segments have been updated
        for segment in segments:
            assert segment.output_path is not None
            assert segment.duration == 2.5

    def test_generate_audio_segments_skip_generation(
        self, mock_tts_client, temp_dir, sample_audio_timeline
    ):
        """Test skipping audio generation with --no-narration flag."""
        generator = AudioGenerator(mock_tts_client, temp_dir)
        segments = generator.generate_audio_segments(sample_audio_timeline, skip_generation=True)

        assert len(segments) == 2
        mock_tts_client.generate_speech.assert_not_called()

    @patch.object(AudioGenerator, "_get_audio_duration", return_value=2.0)
    def test_generate_audio_segments_handles_tts_error(
        self, mock_duration, mock_tts_client, temp_dir, sample_audio_timeline
    ):
        """Test error handling when TTS fails for a segment."""
        # First call succeeds, second fails
        mock_tts_client.generate_speech.side_effect = [
            temp_dir / "success.mp3",
            TTSAPIError("API Error"),
        ]

        generator = AudioGenerator(mock_tts_client, temp_dir)
        segments = generator.generate_audio_segments(sample_audio_timeline)

        # Only one segment should be returned (the successful one)
        assert len(segments) == 1
        assert segments[0].text == "First narration"

    def test_get_audio_duration_fallback(self, mock_tts_client, temp_dir):
        """Test audio duration fallback when ffprobe fails."""
        generator = AudioGenerator(mock_tts_client, temp_dir)

        # Create a dummy file (not a real audio file)
        dummy_file = temp_dir / "dummy.mp3"
        dummy_file.touch()

        # Should return fallback duration
        duration = generator._get_audio_duration(dummy_file)
        assert duration == 2.0  # Default fallback


class TestAudioModuleIntegration:
    """Integration tests for the audio module."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_full_audio_pipeline_mocked(self, temp_dir):
        """Test full audio pipeline with mocked TTS."""
        # Create mock spec with narration
        narration = MagicMock()
        narration.text = "Welcome to the demo."
        narration.timing = "before"
        narration.offset = 0.0

        step = MagicMock()
        step.narration = None

        flow = MagicMock()
        flow.name = "Demo Flow"
        flow.narration = narration
        flow.steps = [step]

        spec = MagicMock()
        spec.name = "Demo"
        spec.flows = [flow]

        # Create execution timeline
        timeline = Timeline(spec_name="Demo")
        timeline.started_at = 0.0
        timeline.add_event(
            TimelineEvent(
                step_name="Step 1",
                action="navigate",
                start_time=1.0,
                end_time=2.0,
                duration=1.0,
                flow_name="Demo Flow",
                flow_index=1,
                step_index=1,
            )
        )
        timeline.completed_at = 2.0

        # Build audio timeline
        audio_timeline = AudioTimeline.from_spec_and_timeline(spec, timeline)
        assert len(audio_timeline.segments) == 1

        # Mock TTS client
        mock_client = MagicMock(spec=TTSClient)
        audio_path = temp_dir / "narration.mp3"
        audio_path.touch()
        mock_client.generate_speech.return_value = audio_path

        # Generate audio
        generator = AudioGenerator(mock_client, temp_dir)
        with patch.object(generator, "_get_audio_duration", return_value=3.0):
            segments = generator.generate_audio_segments(audio_timeline)

        assert len(segments) == 1
        assert segments[0].duration == 3.0
        assert segments[0].end_time == 1.0 + 3.0  # start_time + duration


class TestAudioConcatenator:
    """Tests for AudioConcatenator class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess.run."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            mock_run.return_value.returncode = 0
            yield mock_run

    def test_concatenate_segments_empty(self, temp_dir, mock_subprocess):
        """Test concatenating empty list of segments."""
        concatenator = AudioConcatenator(temp_dir)
        output_path = temp_dir / "output.mp3"

        result = concatenator.concatenate_segments([], 10.0, output_path)

        # Should generate silence
        assert result == output_path
        # Verify silence generation command was called
        args = mock_subprocess.call_args[0][0]
        assert "anullsrc" in str(args)
        assert "-t" in args
        assert "10.0" in args

    def test_concatenate_segments_with_gaps(self, temp_dir):
        """Test concatenating segments with gaps between them."""
        concatenator = AudioConcatenator(temp_dir)
        output_path = temp_dir / "output.mp3"

        # Create dummy segment files
        seg1_path = temp_dir / "seg1.mp3"
        seg1_path.touch()
        seg2_path = temp_dir / "seg2.mp3"
        seg2_path.touch()

        segments = [
            AudioSegment(
                text="First",
                timing="before",
                offset=0.0,
                flow_name="Flow",
                flow_index=1,
                start_time=1.0,
                duration=2.0,
                output_path=seg1_path,
            ),
            AudioSegment(
                text="Second",
                timing="during",
                offset=0.0,
                flow_name="Flow",
                flow_index=1,
                start_time=5.0,
                duration=3.0,
                output_path=seg2_path,
            ),
        ]

        with patch("specspectacle.audio.audio_mixer.AudioFileClip") as mock_afc, \
             patch("specspectacle.audio.audio_mixer.CompositeAudioClip") as mock_cac:

            mock_composite = MagicMock()
            mock_cac.return_value = mock_composite
            mock_composite.set_duration.return_value = mock_composite

            concatenator.concatenate_segments(segments, 10.0, output_path)

            # Should have loaded 2 audio clips
            assert mock_afc.call_count == 2
            # Should have composed them
            assert mock_cac.called
            # Should have written the output file
            assert mock_composite.write_audiofile.called

    def test_cleanup(self, temp_dir):
        """Test cleanup of temporary files (no-op in MoviePy version)."""
        concatenator = AudioConcatenator(temp_dir)
        # Just ensure it doesn't raise error
        concatenator.cleanup()
