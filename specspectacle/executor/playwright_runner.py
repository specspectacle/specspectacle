"""
Playwright-based browser automation runner for executing YAML specs.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, Tuple

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from specspectacle.executor.timeline import Timeline, TimelineEvent
from specspectacle.parser.schema import SpecModel

logger = logging.getLogger(__name__)


class BrowserRunner:
    """
    Manages browser lifecycle and executes YAML spec steps using Playwright.

    Attributes:
        spec: The parsed YAML specification
        output_dir: Directory to save recorded videos and timeline
        timeline: Timeline tracking execution events
        headless_override: Optional override for headless mode
    """

    def __init__(
        self,
        spec: SpecModel,
        output_dir: str = "output/videos",
        headless_override: Optional[bool] = None,
    ):
        """
        Initialize the browser runner.

        Args:
            spec: Parsed YAML specification
            output_dir: Directory to save recorded videos
            headless_override: Override headless setting from spec (None = use spec value)
        """
        self.spec = spec
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Override headless if specified
        self.headless = headless_override if headless_override is not None else spec.config.headless

        # Initialize timeline for tracking
        self.timeline = Timeline(spec_name=spec.name)

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def _inject_cursor_tracker(self) -> None:
        """
        Inject a custom cursor tracker that follows mouse movements.
        This makes the cursor visible in video recordings, even in headless mode.
        """
        cursor_script = """
        // Create cursor element
        if (!document.getElementById('playwright-cursor')) {
            const cursor = document.createElement('div');
            cursor.id = 'playwright-cursor';
            cursor.style.cssText = `
                position: fixed;
                width: 20px;
                height: 20px;
                border: 2px solid red;
                border-radius: 50%;
                pointer-events: none;
                z-index: 2147483647;
                transform: translate(-50%, -50%);
                transition: all 0.1s ease;
                background: rgba(255, 0, 0, 0.3);
                box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
            `;
            document.body.appendChild(cursor);
            
            // Track mouse movements
            document.addEventListener('mousemove', (e) => {
                cursor.style.left = e.pageX + 'px';
                cursor.style.top = e.pageY + 'px';
            });
            
            // Highlight on click
            document.addEventListener('mousedown', () => {
                cursor.style.background = 'rgba(255, 0, 0, 0.6)';
                cursor.style.transform = 'translate(-50%, -50%) scale(1.5)';
            });
            
            document.addEventListener('mouseup', () => {
                cursor.style.background = 'rgba(255, 0, 0, 0.3)';
                cursor.style.transform = 'translate(-50%, -50%) scale(1)';
            });
        }
        """

        try:
            await self.page.evaluate(cursor_script)
        except Exception as e:
            # Don't fail if cursor injection fails
            logger.debug(f"Could not inject cursor tracker: {e}")

    async def launch(self) -> None:
        """
        Launch the browser with video recording enabled.
        """
        logger.info("Launching browser...")

        self.playwright = await async_playwright().start()

        # Launch browser with configuration from YAML (or override)
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.spec.config.slow_motion,
        )

        # Create browser context with video recording
        video_dir = self.output_dir / "raw"
        video_dir.mkdir(parents=True, exist_ok=True)

        self.context = await self.browser.new_context(
            viewport={
                "width": self.spec.config.viewport.width,
                "height": self.spec.config.viewport.height,
            },
            record_video_dir=str(video_dir),
            record_video_size={
                "width": self.spec.config.viewport.width,
                "height": self.spec.config.viewport.height,
            },
        )

        # Create a new page
        self.page = await self.context.new_page()
        logger.info(
            f"Browser launched. Viewport: {self.spec.config.viewport.width}x{self.spec.config.viewport.height}"
        )

    async def close(self) -> Tuple[Optional[Path], Path]:
        """
        Close the browser and save the video and timeline.

        Returns:
            Tuple of (video_path, timeline_path)
        """
        logger.info("Closing browser...")

        # Mark timeline completion
        self.timeline.complete()

        video_path = None
        if self.page:
            # Get the video path before closing
            video = self.page.video
            if video:
                video_path = await video.path()
                logger.info(f"Video saved to: {video_path}")

        if self.context:
            await self.context.close()

        if self.browser:
            await self.browser.close()

        if self.playwright:
            await self.playwright.stop()

        # Save timeline to JSON
        timeline_path = self.output_dir / "timeline.json"
        self.timeline.save(timeline_path)
        logger.info(f"Timeline saved to: {timeline_path}")

        return Path(video_path) if video_path else None, timeline_path

    async def execute_spec(self) -> Tuple[Optional[Path], Path]:
        """
        Execute the entire YAML specification.

        Returns:
            Tuple of (video_path, timeline_path)
        """
        import subprocess

        from specspectacle.audio.tts import TTSClient
        from specspectacle.executor.actions import get_action_handler

        try:
            # Pre-generate all TTS audio files BEFORE browser execution
            # This gives us actual audio durations for accurate wait times
            narration_durations = await self._pre_generate_audio()

            await self.launch()

            # Start timeline tracking
            self.timeline.start()

            logger.info(f"Executing spec: {self.spec.name}")
            logger.info(f"Total flows: {len(self.spec.flows)}")

            # Execute each flow
            for flow_idx, flow in enumerate(self.spec.flows, 1):
                logger.info(f"\n→ Flow {flow_idx}/{len(self.spec.flows)}: {flow.name}")
                if flow.description:
                    logger.info(f"  {flow.description}")

                # Execute each step in the flow
                for step_idx, step in enumerate(flow.steps, 1):
                    step_action = step.action
                    step_name = getattr(step, "name", None) or f"{step_action} step {step_idx}"

                    logger.info(f"  Step {step_idx}/{len(flow.steps)}: {step_action}")

                    # Get actual narration duration from pre-generated audio
                    narration_wait_before = 0.0
                    narration_wait_after = 0.0
                    narration_during_duration = 0.0

                    narration_key = (flow_idx, step_idx)
                    if narration_key in narration_durations:
                        actual_duration = narration_durations[narration_key]["duration"]
                        narration_timing = narration_durations[narration_key]["timing"]
                        narration_offset = narration_durations[narration_key]["offset"]

                        # Add wait time based on timing mode
                        if narration_timing == "before":
                            narration_wait_before = actual_duration + narration_offset
                            logger.info(f"    🎙️ Narration (before): {narration_wait_before:.2f}s")
                        elif narration_timing == "after":
                            narration_wait_after = actual_duration + narration_offset
                            logger.info(f"    🎙️ Narration (after): {narration_wait_after:.2f}s")
                        else:  # "during"
                            narration_during_duration = actual_duration + narration_offset
                            logger.info(
                                f"    🎙️ Narration (during): {narration_during_duration:.2f}s"
                            )

                    # Record start time BEFORE wait (so wait is included in event duration)
                    start_time = time.time()
                    narration_actual_start_time = None

                    # For "before" timing: narration starts at beginning of event
                    if narration_wait_before > 0:
                        narration_actual_start_time = start_time
                        await asyncio.sleep(narration_wait_before)

                    # Record when action actually starts (for "during" calculation)
                    action_start_time = time.time()

                    # For "during" timing: narration starts when action starts
                    if narration_during_duration > 0:
                        narration_actual_start_time = action_start_time

                    success = True
                    error_message = None

                    try:
                        # Get and execute the action handler
                        handler = get_action_handler(step_action)
                        await handler(self.page, step)

                        # Inject cursor tracker after navigation to make mouse visible
                        if step_action == "navigate":
                            await self._inject_cursor_tracker()
                    except Exception as e:
                        success = False
                        error_message = str(e)
                        raise
                    finally:
                        # Calculate how long the action took
                        action_end_time = time.time()
                        action_duration = action_end_time - action_start_time

                        # For "during" timing: wait if narration is longer than action
                        if narration_during_duration > 0:
                            remaining_narration_time = narration_during_duration - action_duration
                            if remaining_narration_time > 0:
                                logger.debug(
                                    f"    Waiting {remaining_narration_time:.2f}s for narration"
                                )
                                await asyncio.sleep(remaining_narration_time)

                        # For "after" timing: narration starts after action completes
                        if narration_wait_after > 0:
                            narration_actual_start_time = action_end_time
                            await asyncio.sleep(narration_wait_after)

                        # Record end time AFTER wait and add event to timeline
                        end_time = time.time()
                        self.timeline.record_event(
                            step_name=step_name,
                            action=step_action,
                            flow_name=flow.name,
                            flow_index=flow_idx,
                            step_index=step_idx,
                            start_time=start_time,
                            end_time=end_time,
                            success=success,
                            error_message=error_message,
                            narration_start_time=narration_actual_start_time,
                        )

            logger.info(f"\n✓ Spec execution completed successfully")
            logger.info(f"  Total duration: {self.timeline.total_duration:.2f}s")
            logger.info(f"  Events recorded: {len(self.timeline.events)}")
            return await self.close()

        except Exception as e:
            logger.error(f"Error executing spec: {e}", exc_info=True)
            await self.close()
            raise

    async def _pre_generate_audio(self) -> dict:
        """
        Pre-generate all TTS audio files before browser execution.

        Returns:
            Dict mapping (flow_idx, step_idx) to {"duration": float, "timing": str, "offset": float, "path": Path}
        """
        import subprocess

        from specspectacle.audio.tts import TTSClient

        narration_durations = {}

        # Check if narration is enabled
        if not self.spec.narration.enabled:
            logger.info("Narration disabled, skipping TTS pre-generation")
            return narration_durations

        # Create audio output directory (clean it first to avoid contamination from previous runs)
        audio_dir = self.output_dir / "audio_segments"

        # Clear existing audio segments to prevent contamination from previous flows
        if audio_dir.exists():
            import shutil

            logger.debug(f"Cleaning audio_segments directory: {audio_dir}")
            shutil.rmtree(audio_dir)

        audio_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Pre-generating TTS audio for accurate timing...")

        tts_client = TTSClient()
        segment_idx = 0

        for flow_idx, flow in enumerate(self.spec.flows, 1):
            for step_idx, step in enumerate(flow.steps, 1):
                if hasattr(step, "narration") and step.narration:
                    narration = step.narration

                    # Generate audio file
                    filename = f"narration_{flow_idx:02d}_{step_idx:02d}_{segment_idx:03d}.mp3"
                    output_path = audio_dir / filename

                    try:
                        # Call async TTS method directly since we're in async context
                        await tts_client._generate_audio_with_retry(
                            text=narration.text,
                            voice_name=tts_client.config.voice_name,
                            output_path=output_path,
                        )

                        # Get actual duration using ffprobe
                        result = subprocess.run(
                            [
                                "ffprobe",
                                "-v",
                                "error",
                                "-show_entries",
                                "format=duration",
                                "-of",
                                "default=noprint_wrappers=1:nokey=1",
                                str(output_path),
                            ],
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                        actual_duration = float(result.stdout.strip())

                        narration_durations[(flow_idx, step_idx)] = {
                            "duration": actual_duration,
                            "timing": narration.timing,
                            "offset": getattr(narration, "offset", 0.0),
                            "path": output_path,
                        }

                        logger.info(f"  Generated: {filename} ({actual_duration:.2f}s)")
                        segment_idx += 1

                    except Exception as e:
                        logger.warning(
                            f"Failed to generate audio for flow {flow_idx} step {step_idx}: {e}"
                        )

        logger.info(f"Pre-generated {len(narration_durations)} audio segments")
        return narration_durations


def run_spec(
    spec: SpecModel,
    output_dir: str = "output/videos",
    headless_override: Optional[bool] = None,
) -> Tuple[Optional[Path], Path]:
    """
    Synchronous wrapper to execute a spec.

    Args:
        spec: Parsed YAML specification
        output_dir: Directory to save videos
        headless_override: Override headless setting (None = use spec value)

    Returns:
        Tuple of (video_path, timeline_path)
    """
    runner = BrowserRunner(spec, output_dir, headless_override)
    return asyncio.run(runner.execute_spec())
