"""Unit tests for sound effects module."""


from specspectacle.audio.sfx import (
    ASSETS_DIR,
    SoundEvent,
    build_sfx_mix_args,
    resolve_sfx_path,
)


class TestResolveSfxPath:
    """Tests for resolve_sfx_path."""

    def test_variant_int_click(self):
        """Integer variant resolves to built-in click asset."""
        path = resolve_sfx_path(2, "click")
        assert path.endswith("click-2.mp3")
        assert str(ASSETS_DIR) in path

    def test_variant_int_key(self):
        """Integer variant resolves to built-in key asset."""
        path = resolve_sfx_path(3, "key")
        assert path.endswith("key-3.mp3")

    def test_custom_path_returned_as_is(self):
        """String path is returned unchanged."""
        path = resolve_sfx_path("/custom/sound.mp3", "click")
        assert path == "/custom/sound.mp3"

    def test_none_returns_none(self):
        """None value returns None (SFX disabled for this type)."""
        result = resolve_sfx_path(None, "click")
        assert result is None


class TestSoundEvent:
    """Tests for SoundEvent dataclass."""

    def test_creation(self):
        """SoundEvent stores type and time_ms."""
        event = SoundEvent(type="click", time_ms=1500.0)
        assert event.type == "click"
        assert event.time_ms == 1500.0

    def test_to_dict(self):
        """SoundEvent can be serialized to dict."""
        event = SoundEvent(type="key", time_ms=2300.0)
        d = event.to_dict()
        assert d == {"type": "key", "time_ms": 2300.0}


class TestBuildSfxMixArgs:
    """Tests for ffmpeg argument builder."""

    def test_empty_events_returns_none(self):
        """No events means no mixing needed."""
        result = build_sfx_mix_args(
            video_path="/tmp/video.mp4",
            events=[],
            click_sfx_path=str(ASSETS_DIR / "click-1.mp3"),
            key_sfx_path=str(ASSETS_DIR / "key-1.mp3"),
        )
        assert result is None

    def test_with_click_events(self):
        """Click events produce ffmpeg args with input files and filters."""
        events = [SoundEvent(type="click", time_ms=1000.0)]
        result = build_sfx_mix_args(
            video_path="/tmp/video.mp4",
            events=events,
            click_sfx_path=str(ASSETS_DIR / "click-1.mp3"),
            key_sfx_path=str(ASSETS_DIR / "key-1.mp3"),
        )
        assert result is not None
        assert "inputs" in result
        assert "filter_complex" in result
        assert len(result["inputs"]) > 0

    def test_with_key_events(self):
        """Key events produce ffmpeg args."""
        events = [SoundEvent(type="key", time_ms=500.0)]
        result = build_sfx_mix_args(
            video_path="/tmp/video.mp4",
            events=events,
            click_sfx_path=str(ASSETS_DIR / "click-1.mp3"),
            key_sfx_path=str(ASSETS_DIR / "key-1.mp3"),
        )
        assert result is not None
        assert "filter_complex" in result

    def test_mixed_events(self):
        """Mixed click and key events are both included."""
        events = [
            SoundEvent(type="click", time_ms=1000.0),
            SoundEvent(type="key", time_ms=1500.0),
            SoundEvent(type="key", time_ms=2000.0),
        ]
        result = build_sfx_mix_args(
            video_path="/tmp/video.mp4",
            events=events,
            click_sfx_path=str(ASSETS_DIR / "click-1.mp3"),
            key_sfx_path=str(ASSETS_DIR / "key-1.mp3"),
        )
        assert result is not None
        # Should have inputs for the video + unique SFX files
        assert len(result["inputs"]) >= 1

    def test_filter_contains_adelay(self):
        """Filter complex uses adelay for time-positioning audio."""
        events = [SoundEvent(type="click", time_ms=2500.0)]
        result = build_sfx_mix_args(
            video_path="/tmp/video.mp4",
            events=events,
            click_sfx_path=str(ASSETS_DIR / "click-1.mp3"),
            key_sfx_path=None,
        )
        assert result is not None
        assert "adelay" in result["filter_complex"]
