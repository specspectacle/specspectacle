"""
MoviePy-based video processor for SpecSpectacle.
Modern replacement for the FFmpeg-based processor.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from specspectacle.executor.timeline import SoundEvent

# Monkeypatch PIL.Image.ANTIALIAS for moviepy compatibility with Pillow 10+
import PIL.Image

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
)

from specspectacle.video.processor import COMPRESSION_SETTINGS, CompressionPreset

logger = logging.getLogger(__name__)

def _get_position(pos_name: str, clip_size: tuple, video_size: tuple) -> tuple:
    """
    Convert position names to (x, y) coordinates for MoviePy.
    MoviePy supports 'center', 'top', 'bottom', 'left', 'right'.
    """
    vw, vh = video_size
    cw, ch = clip_size

    if pos_name == "center":
        return ("center", "center")
    elif pos_name == "top":
        return ("center", 20)
    elif pos_name == "bottom":
        return ("center", vh - ch - 30)
    elif pos_name == "top-left":
        return (20, 20)
    elif pos_name == "top-right":
        return (vw - cw - 20, 20)
    elif pos_name == "bottom-left":
        return (20, vh - ch - 30)
    elif pos_name == "bottom-right":
        return (vw - cw - 20, vh - ch - 30)
    elif pos_name == "left":
        return (20, "center")
    elif pos_name == "right":
        return (vw - cw - 20, "center")

    return ("center", "center")

def _get_logo_position(pos_name: str, logo_size: tuple, video_size: tuple) -> tuple:
    vw, vh = video_size
    lw, lh = logo_size

    if pos_name == "top-left":
        return (10, 10)
    elif pos_name == "top-right":
        return (vw - lw - 10, 10)
    elif pos_name == "bottom-left":
        return (10, vh - lh - 10)
    elif pos_name == "bottom-right":
        return (vw - lw - 10, vh - lh - 10)

    return (vw - lw - 10, 10) # Default top-right


class MoviePyOverlayRenderer:
    """
    Renders text overlays, logos, and backgrounds on video using MoviePy.
    """

    def __init__(self, video_path: Path):
        self.video_path = Path(video_path)
        self.overlays = []
        self.logos = []
        self.backgrounds = []
        self.full_frames = []

    def add_overlay(self, config: Any) -> None:
        self.overlays.append(config)

    def add_logo(self, config: Any) -> None:
        self.logos.append(config)

    def add_background(self, config: Any) -> None:
        self.backgrounds.append(config)

    def add_full_frame_image(self, image_path: Path, start_time: float, duration: float) -> None:
        self.full_frames.append({
            "path": image_path,
            "start_time": start_time,
            "duration": duration
        })

    def render(self, output_path: Path) -> Path:
        logger.info(f"Rendering overlays with MoviePy to {output_path}")

        video = VideoFileClip(str(self.video_path))
        video_size = video.size

        clips = [video]

        # 1. Add Backgrounds
        for bg in self.backgrounds:
            bg_clip = (ColorClip(size=video_size, color=self._hex_to_rgb(bg.color))
                       .set_start(bg.start_time)
                       .set_duration(bg.duration)
                       .set_opacity(bg.opacity))
            clips.append(bg_clip)

        # 1.5 Add Full Frame Branding Images
        for frame in self.full_frames:
            if not frame["path"].exists():
                logger.warning(f"Branding frame not found: {frame['path']}")
                continue
            f_clip = (ImageClip(str(frame["path"]))
                      .set_start(frame["start_time"])
                      .set_duration(frame["duration"])
                      .set_position("center"))
            # Ensure it fits the video size
            f_clip = f_clip.resize(newsize=video_size)
            clips.append(f_clip)

        # 2. Add Logos
        for logo in self.logos:
            if not os.path.exists(logo.logo_path):
                logger.warning(f"Logo not found: {logo.logo_path}")
                continue

            l_clip = ImageClip(logo.logo_path)
            # Scale logo
            target_width = video_size[0] * logo.scale
            l_clip = l_clip.resize(width=target_width)

            pos = _get_logo_position(logo.position, l_clip.size, video_size)
            l_clip = (l_clip.set_start(logo.start_time)
                      .set_duration(logo.duration)
                      .set_position(pos))
            clips.append(l_clip)

        # 3. Add Text Overlays
        for ov in self.overlays:
            # MoviePy TextClip
            t_clip = TextClip(
                ov.text,
                fontsize=ov.font_size,
                color=ov.font_color,
                font=ov.font_family or "Arial",
                bg_color=ov.background_color,
                method='caption', # Handles wrapping
                size=(video_size[0] * 0.8, None) # 80% width max
            )

            pos = _get_position(ov.position, t_clip.size, video_size)
            t_clip = (t_clip.set_start(ov.start_time)
                      .set_duration(ov.duration)
                      .set_position(pos))
            clips.append(t_clip)

        final_video = CompositeVideoClip(clips)
        final_video.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            logger=None
        )

        video.close()
        final_video.close()
        return output_path

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 8: # RGBA
            hex_color = hex_color[:6]
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


class MoviePyProcessor:
    """
    Process videos using MoviePy for a more object-oriented pipeline.
    """

    def __init__(self, input_path: Path, output_dir: Path):
        self.input_path = Path(input_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_files: list[Path] = []

        if not self.input_path.exists():
            raise FileNotFoundError(f"Input video not found: {self.input_path}")

    def process(
        self,
        output_filename: str,
        fps: int = 30,
        resolution: str = "1280x720",
        bitrate: str = "5000k",
        codec: str = "libx264",
        compression_preset: str | None = None,
    ) -> Path:
        """
        Main processing pipeline using MoviePy.
        """
        logger.info(f"Processing video {self.input_path} with MoviePy")

        # Parse resolution
        width, height = map(int, resolution.split("x"))

        # Load clip
        clip = VideoFileClip(str(self.input_path))

        # Apply normalization and resizing
        processed_clip = clip.resize(newsize=(width, height)).set_fps(fps)

        final_output = self.output_dir / output_filename

        # Determine compression settings
        if compression_preset:
            preset_enum = CompressionPreset(compression_preset)
            settings = COMPRESSION_SETTINGS[preset_enum]
            ffmpeg_params = ["-crf", str(settings["crf"]), "-preset", settings["preset"]]
            actual_bitrate = settings["bitrate"]
        else:
            ffmpeg_params = ["-crf", "23", "-preset", "medium"]
            actual_bitrate = bitrate

        logger.info(f"Writing video to {final_output}")
        processed_clip.write_videofile(
            str(final_output),
            codec=codec,
            bitrate=actual_bitrate,
            audio_codec="aac",
            temp_audiofile=str(self.output_dir / "temp-audio.m4a"),
            remove_temp=True,
            ffmpeg_params=ffmpeg_params,
            logger=None
        )

        clip.close()
        processed_clip.close()

        return final_output

    def merge_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path | None = None,
    ) -> Path:
        """
        Merge an audio track with a video file.
        """
        video_path = Path(video_path)
        audio_path = Path(audio_path)

        if output_path is None:
            output_path = self._create_temp_file(".mp4")
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Merging audio ({audio_path}) with video ({video_path}) using MoviePy")

        video_clip = VideoFileClip(str(video_path))
        audio_clip = AudioFileClip(str(audio_path))

        final_clip = video_clip.set_audio(audio_clip)

        final_clip.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            logger=None
        )

        video_clip.close()
        audio_clip.close()
        final_clip.close()

        return output_path

    def apply_sfx(
        self,
        video_path: Path,
        events: list["SoundEvent"],
        click_sfx_path: str | None,
        key_sfx_path: str | None,
        output_path: Path | None = None,
    ) -> Path:
        """
        Apply sound effects to video using MoviePy timeline composition.
        """
        video_path = Path(video_path)
        if output_path is None:
            output_path = self._create_temp_file(".mp4")
        else:
            output_path = Path(output_path)

        logger.info(f"Applying {len(events)} SFX events to {video_path}")

        video_clip = VideoFileClip(str(video_path))

        # Collect all audio clips
        audio_tracks = []
        if video_clip.audio:
            audio_tracks.append(video_clip.audio)

        for event in events:
            sfx_file = click_sfx_path if event.type == "click" else key_sfx_path
            if sfx_file and os.path.exists(sfx_file):
                sfx_clip = AudioFileClip(sfx_file).set_start(event.timestamp)
                audio_tracks.append(sfx_clip)

        if not audio_tracks:
            return video_path

        final_audio = CompositeAudioClip(audio_tracks)
        final_video = video_clip.set_audio(final_audio)

        final_video.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            logger=None
        )

        video_clip.close()
        final_video.close()

        return output_path

    def full_render(
        self,
        output_filename: str,
        timeline: Any,
        spec: Any,
        no_narration: bool = False,
        no_overlays: bool = False,
        compression_preset: str | None = None,
    ) -> Path:
        """
        Perform a unified render pass using MoviePy.
        This builds a complete timeline in memory and exports once.
        """
        import asyncio

        from specspectacle.audio.audio_mixer import AudioTimeline
        from specspectacle.audio.sfx import resolve_sfx_path
        from specspectacle.video.branding_engine import BrandingEngine
        from specspectacle.video.overlay import OverlayTimestampCalculator

        logger.info(f"Starting unified render for {output_filename}")

        # 1. Load Main Video
        main_clip = VideoFileClip(str(self.input_path))

        # 2. Resizing & FPS Normalization
        width, height = map(int, spec.output.resolution.split("x"))
        main_clip = main_clip.resize(newsize=(width, height)).set_fps(spec.output.fps)
        
        # Trim main clip to the actual timeline duration (prevents recording leak after outro)
        main_clip = main_clip.subclip(0, timeline.total_duration)
        video_size = main_clip.size

        # Create a black background to ensure no demo leak behind intro/outro if they have transparency
        # or if sizing is slightly off.
        # Strip all audio from video clips to avoid conflicts with our custom audio mix
        bg_clip = ColorClip(size=video_size, color=(0, 0, 0)).set_duration(timeline.total_duration)
        main_clip = main_clip.without_audio()
        
        clips = [bg_clip, main_clip]

        # 3. Audio Construction
        audio_tracks = []

        # 3a. Narration
        if not no_narration and spec.narration.enabled:
            audio_timeline = AudioTimeline.from_spec_and_timeline(spec, timeline)
            if audio_timeline.segments:
                # We need to ensure narration files exist.
                audio_dir = self.output_dir / "audio_segments"
                for segment in audio_timeline.segments:
                    pattern = f"narration_{segment.flow_index:02d}_{segment.step_index:02d}_*.mp3"
                    matches = sorted(list(audio_dir.glob(pattern))) # Sort to get consistent results
                    if matches:
                        try:
                            # Use AudioFileClip for each segment
                            a_clip = AudioFileClip(str(matches[0])).set_start(segment.start_time or 0)
                            audio_tracks.append(a_clip)
                        except Exception as e:
                            logger.warning(f"Failed to load narration clip {matches[0]}: {e}")

        # 3b. SFX
        if spec.config.sfx and timeline.sound_events:
            click_path = resolve_sfx_path(spec.config.sfx.click, "click")
            key_path = resolve_sfx_path(spec.config.sfx.key, "key")
            for event in timeline.sound_events:
                sfx_file = click_path if event.type == "click" else key_path
                if sfx_file and os.path.exists(sfx_file):
                    try:
                        # Sound events use milliseconds
                        s_clip = AudioFileClip(sfx_file).set_start(event.time_ms / 1000.0)
                        audio_tracks.append(s_clip)
                    except Exception as e:
                        logger.warning(f"Failed to load SFX clip {sfx_file}: {e}")

        # 4. Visual Overlays (Branding Intro/Outro/Logo)
        branding_config = spec.config.branding
        if branding_config:
            engine = BrandingEngine()
            intro_segment = timeline.get_intro_segment()
            outro_segment = timeline.get_outro_segment()

            if intro_segment or outro_segment:
                branding_frames = asyncio.run(engine.generate_intro_outro(
                    branding_config=branding_config,
                    intro_text=intro_segment.title if intro_segment else "",
                    outro_text=outro_segment.title if outro_segment else "",
                    output_dir=self.output_dir,
                    resolution=spec.output.resolution
                ))

                if intro_segment and "intro" in branding_frames:
                    # Intro frame - ensure it's on top and opaque
                    f_clip = (ImageClip(str(branding_frames["intro"]))
                              .set_start(intro_segment.start_time)
                              .set_duration(intro_segment.duration)
                              .set_position("center")
                              .resize(newsize=video_size))
                    clips.append(f_clip)
                    self.temp_files.append(branding_frames["intro"])

                if outro_segment and "outro" in branding_frames:
                    # Outro frame - ensure it's on top and opaque
                    f_clip = (ImageClip(str(branding_frames["outro"]))
                              .set_start(outro_segment.start_time)
                              .set_duration(outro_segment.duration)
                              .set_position("center")
                              .resize(newsize=video_size))
                    clips.append(f_clip)
                    self.temp_files.append(branding_frames["outro"])

            # Persistent Watermark Logo
            if branding_config.logo:
                l_clip = ImageClip(branding_config.logo)
                target_width = video_size[0] * branding_config.logo_scale
                l_clip = l_clip.resize(width=target_width)

                # We need a helper for logo position
                pos = _get_logo_position(branding_config.logo_position, l_clip.size, video_size)
                l_clip = (l_clip.set_start(0)
                          .set_duration(timeline.total_duration)
                          .set_position(pos))
                clips.append(l_clip)

        # 5. Text Overlays
        if not no_overlays:
            overlays = OverlayTimestampCalculator.calculate_overlays(spec, timeline, branding_config)
            for ov in overlays:
                # Use label method for shorter text to avoid massive black boxes
                is_long = len(ov.text) > 40
                t_clip = TextClip(
                    ov.text,
                    fontsize=ov.font_size,
                    color=ov.font_color,
                    font=ov.font_family or "Arial",
                    bg_color=ov.background_color,
                    method='caption' if is_long else 'label',
                    size=(video_size[0] * 0.8, None) if is_long else None
                )
                pos = _get_position(ov.position, t_clip.size, video_size)
                t_clip = (t_clip.set_start(ov.start_time)
                          .set_duration(ov.duration)
                          .set_position(pos))
                clips.append(t_clip)

        # 6. Final Composition & Export
        # CompositeVideoClip will layer clips in order (bg at bottom, overlays at top)
        final_video = CompositeVideoClip(clips, size=video_size).set_duration(timeline.total_duration)
        
        if audio_tracks:
            # Create a single composite audio track and set it on the final video
            final_audio = CompositeAudioClip(audio_tracks).set_duration(timeline.total_duration)
            final_video = final_video.set_audio(final_audio)
        
        final_output = self.output_dir / output_filename

        # Compression settings
        if compression_preset:
            preset_enum = CompressionPreset(compression_preset)
            settings = COMPRESSION_SETTINGS[preset_enum]
            ffmpeg_params = ["-crf", str(settings["crf"]), "-preset", settings["preset"]]
            bitrate = settings["bitrate"]
        else:
            ffmpeg_params = ["-crf", "23", "-preset", "medium"]
            bitrate = spec.output.bitrate

        logger.info(f"Writing final video to {final_output}")
        final_video.write_videofile(
            str(final_output),
            codec=spec.output.codec,
            bitrate=bitrate,
            audio_codec="aac",
            temp_audiofile=str(self.output_dir / "temp-audio.m4a"),
            remove_temp=True,
            ffmpeg_params=ffmpeg_params,
            logger=None
        )

        # Cleanup
        for clip in clips:
            clip.close()
        final_video.close()

        return final_output

    def _create_temp_file(self, suffix: str) -> Path:
        """Create a temporary file and track it for cleanup."""
        fd, path = tempfile.mkstemp(suffix=suffix, dir=self.output_dir)
        os.close(fd)
        temp_path = Path(path)
        self.temp_files.append(temp_path)
        return temp_path

    def cleanup_temp_files(self):
        """Remove all temporary files created during processing."""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except OSError as e:
                logger.warning(f"Failed to remove temp file {temp_file}: {e}")
        self.temp_files.clear()
