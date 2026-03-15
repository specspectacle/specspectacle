"""Run command - Execute YAML spec and generate demo video."""

import contextlib
import sys
from pathlib import Path

import click
from pydantic import ValidationError

from specspectacle.parser.yaml_parser import YAMLParser
from specspectacle.utils.logger import console, logger


@click.command()
@click.argument("yaml_file", type=click.Path(exists=True))
@click.option("--output-dir", type=click.Path(), help="Override output directory")
@click.option("--headless/--headed", default=True, help="Run browser in headless mode")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
@click.option("--dry-run", is_flag=True, help="Validate and show execution plan without running")
@click.option("--keep-artifacts", is_flag=True, help="Keep intermediate files after processing")
@click.option(
    "--compression",
    type=click.Choice(["low", "medium", "high"]),
    default="medium",
    help="Video compression preset",
)
@click.option("--no-narration", is_flag=True, help="Skip TTS generation (silent video)")
@click.option("--no-overlays", is_flag=True, help="Skip text overlay rendering")
def run(
    yaml_file: str,
    output_dir: str,
    headless: bool,
    verbose: bool,
    dry_run: bool,
    keep_artifacts: bool,
    compression: str,
    no_narration: bool,
    no_overlays: bool,
):
    """
    Execute YAML specification and generate demo video.

    This command will orchestrate the entire video generation pipeline:
    parse YAML → execute browser steps → capture video → add narration
    → render overlays → output final MP4.

    \b
    Examples:
        specspectacle run demo.yaml
        specspectacle run demo.yaml --headed --verbose
        specspectacle run demo.yaml --dry-run
        specspectacle run demo.yaml --no-narration --compression high
    """
    if verbose:
        import logging

        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")

    logger.info(f"Processing YAML file: {yaml_file}")

    # Parse and validate YAML
    try:
        spec = YAMLParser.parse(yaml_file)
        console.print(f"[green]✓[/green] Loaded spec: [cyan]{spec.name}[/cyan] v{spec.version}")

    except FileNotFoundError as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        sys.exit(1)

    except ValidationError as e:
        console.print("[red]✗ YAML validation failed[/red]")
        console.print()
        console.print(YAMLParser.format_validation_error(e))
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]✗ Unexpected error:[/red] {e}")
        logger.exception("Unexpected error during parsing")
        sys.exit(1)

    # Dry run mode - show execution plan
    if dry_run:
        console.print()
        console.print("[bold cyan]Execution Plan (Dry Run)[/bold cyan]")
        console.print()

        total_steps = 0
        for flow in spec.flows:
            console.print(f"[bold]Flow:[/bold] {flow.name}")
            if flow.description:
                console.print(f"  [dim]{flow.description}[/dim]")

            for idx, step in enumerate(flow.steps, 1):
                action = step.action
                console.print(f"  {idx}. [cyan]{action}[/cyan]", end="")

                # Show step details based on action
                if hasattr(step, "url"):
                    console.print(f" → {step.url}", end="")
                if hasattr(step, "selector"):
                    console.print(f" [{step.selector}]", end="")
                if hasattr(step, "text") and action == "type":
                    console.print(f" → '{step.text}'", end="")
                if hasattr(step, "duration"):
                    console.print(f" ({step.duration}s)", end="")

                console.print()

                if step.narration:
                    console.print(f'     [dim]🎙️ "{step.narration.text}"[/dim]')
                if step.overlay:
                    console.print(f'     [dim]📝 "{step.overlay.text}"[/dim]')

                total_steps += 1

            console.print()

        console.print("[bold]Summary:[/bold]")
        console.print(f"  • Total flows: {len(spec.flows)}")
        console.print(f"  • Total steps: {total_steps}")
        console.print(f"  • Output: {spec.output.filename}")
        console.print(f"  • Resolution: {spec.output.resolution} @ {spec.output.fps} FPS")
        console.print()
        console.print("[yellow]Note:[/yellow] This is a dry run. No video will be generated.")
        console.print("[dim]Remove --dry-run to execute the spec[/dim]")

        sys.exit(0)

    # Full execution with BrowserRunner
    from specspectacle.executor.errors import (
        ExecutorError,
        NavigationError,
        SelectorTimeoutError,
    )
    from specspectacle.executor.playwright_runner import run_spec

    # Determine output directory
    if output_dir:
        out_path = Path(output_dir)
    else:
        out_path = Path("output/videos")

    console.print()
    console.print("[bold cyan]Starting Execution[/bold cyan]")
    console.print(f"  Output directory: {out_path}")
    console.print(f"  Headless mode: {headless}")
    console.print()

    try:
        # Execute the spec
        video_path, timeline_path = run_spec(
            spec,
            output_dir=str(out_path),
            headless_override=headless,
        )

        console.print()
        console.print("[bold green]✓ Execution Complete![/bold green]")
        console.print()

        # Process video if one was recorded
        final_video_path = None

        # Load timeline explicitly as it plays a key role in post-processing
        from specspectacle.executor.timeline import Timeline

        timeline = Timeline.load(timeline_path)

        if video_path and Path(video_path).exists():
            console.print(f"  [bold]Raw Video:[/bold] {video_path}")

            # Import video processing modules
            from specspectacle.video import (
                OverlayTimestampCalculator,
                VideoProcessor,
                check_ffmpeg_installed,
                render_overlays_on_video,
            )

            # Check if FFmpeg is available for video processing
            if check_ffmpeg_installed():
                console.print()
                console.print("[bold cyan]Processing Video...[/bold cyan]")
                console.print(f"  Compression: {compression}, Resolution: {spec.output.resolution}")

                try:
                    # Create video processor
                    raw_video_path = Path(video_path)
                    processor = VideoProcessor(raw_video_path, out_path)

                    # 1. Basic Video Processing (codec, resize, fps)
                    # We use a temp name first
                    intermediate_filename = f"processed_{spec.output.filename}"
                    current_video_path = processor.process(
                        output_filename=intermediate_filename,
                        fps=spec.output.fps,
                        bitrate=spec.output.bitrate,
                        resolution=spec.output.resolution,
                        codec=spec.output.codec,
                        compression_preset=compression,
                    )

                    # 2. Audio Generation & Merging
                    # Audio files are pre-generated during browser execution for accurate timing
                    if not no_narration and spec.narration.enabled:
                        console.print("  [bold]Processing Narration Audio...[/bold]")
                        try:
                            from specspectacle.audio import (
                                AudioConcatenator,
                                AudioTimeline,
                            )

                            audio_timeline = AudioTimeline.from_spec_and_timeline(spec, timeline)

                            if audio_timeline.segments:
                                # Audio files were pre-generated during execution
                                # Just need to update segment paths and durations from existing files
                                audio_dir = out_path / "audio_segments"

                                # Scan for pre-generated audio files and get their durations
                                import subprocess

                                for segment in audio_timeline.segments:
                                    # Find matching audio file
                                    pattern = f"narration_{segment.flow_index:02d}_{segment.step_index:02d}_*.mp3"
                                    matches = list(audio_dir.glob(pattern))
                                    if matches:
                                        audio_path = matches[0]
                                        segment.output_path = audio_path
                                        # Get actual duration
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
                                        segment.duration = float(result.stdout.strip())
                                        segment.end_time = (
                                            segment.start_time or 0
                                        ) + segment.duration

                                # Concatenate segments
                                concatenator = AudioConcatenator(out_path / "audio_temp")
                                final_audio = concatenator.concatenate_segments(
                                    audio_timeline.segments,
                                    timeline.total_duration,
                                    out_path / "narration_track.mp3",
                                )

                                # Merge with video
                                console.print("  Merging audio track...")
                                merged_video = processor.merge_audio(
                                    current_video_path, final_audio
                                )

                                # Cleanup intermediate video
                                if not keep_artifacts and current_video_path != raw_video_path:
                                    with contextlib.suppress(OSError):
                                        current_video_path.unlink()
                                current_video_path = merged_video

                                # Cleanup audio temps
                                if not keep_artifacts:
                                    concatenator.cleanup()

                            else:
                                console.print("    [dim]No narration segments active[/dim]")

                        except Exception as e:
                            console.print(f"    [yellow]⚠ Audio integration failed:[/yellow] {e}")
                            logger.exception("Audio processing error")

                    # 2.5 Sound Effects (SFX)
                    if spec.config.sfx and timeline.sound_events:
                        console.print(f"  [bold]Mixing {len(timeline.sound_events)} Sound Events...[/bold]")
                        try:
                            from specspectacle.audio.sfx import resolve_sfx_path
                            click_path = resolve_sfx_path(spec.config.sfx.click, "click")
                            key_path = resolve_sfx_path(spec.config.sfx.key, "key")

                            if click_path or key_path:
                                sfx_video = processor.apply_sfx(
                                    current_video_path,
                                    timeline.sound_events,
                                    click_path,
                                    key_path,
                                )
                                # Cleanup intermediate video
                                if not keep_artifacts and current_video_path != raw_video_path and current_video_path != sfx_video:
                                    with contextlib.suppress(OSError):
                                        current_video_path.unlink()
                                current_video_path = sfx_video
                        except Exception as e:
                            console.print(f"    [yellow]⚠ SFX integration failed:[/yellow] {e}")
                            logger.exception("SFX processing error")

                    # 3. Text Overlays
                    if not no_overlays:
                        overlays = OverlayTimestampCalculator.calculate_overlays(spec, timeline, spec.config.branding)
                        if overlays:
                            console.print(f"  [bold]Rendering {len(overlays)} Overlays...[/bold]")
                            try:
                                overlaid_video = render_overlays_on_video(
                                    current_video_path,
                                    out_path / f"overlaid_{spec.output.filename}",
                                    overlays,
                                )

                                # Cleanup intermediate video
                                if not keep_artifacts and current_video_path != raw_video_path:
                                    with contextlib.suppress(OSError):
                                        current_video_path.unlink()
                                current_video_path = overlaid_video

                            except Exception as e:
                                console.print(
                                    f"    [yellow]⚠ Overlay rendering failed:[/yellow] {e}"
                                )
                                logger.exception("Overlay rendering error")

                    # 3.5 Branding (Logo + Colors)
                    branding_applied = False
                    if spec.config.branding:
                        console.print("  [bold]Applying Branding...[/bold]")
                        try:
                            # Use current_video_path as input to apply_branding
                            # apply_branding will write to spec.output.filename
                            current_video_path = processor.apply_branding(
                                current_video_path,
                                timeline,
                                spec.config.branding,
                                spec.output.filename,
                            )
                            branding_applied = True

                        except Exception as e:
                            console.print(
                                f"    [yellow]⚠ Branding application failed:[/yellow] {e}"
                            )
                            logger.exception("Branding application error")

                    # Final cleanup and rename to target filename (skip if branding was applied)
                    if not branding_applied:
                        target_path = out_path / spec.output.filename
                        if target_path.exists():
                            target_path.unlink()

                        current_video_path.rename(target_path)
                        final_video_path = target_path
                    else:
                        final_video_path = current_video_path

                    console.print("[bold green]✓ Video Processing Complete![/bold green]")
                    console.print(f"  [bold]Final Video:[/bold] {final_video_path}")

                    # Clean up raw video unless --keep-artifacts
                    if not keep_artifacts:
                        try:
                            raw_video_path.unlink()
                            console.print("  [dim]Cleaned up raw video[/dim]")
                        except OSError as e:
                            logger.warning(f"Failed to clean up raw video: {e}")
                    else:
                        console.print(f"  [dim]Keeping raw video: {raw_video_path}[/dim]")

                    # Cleanup any processor temp files
                    processor.cleanup_temp_files()

                except Exception as e:
                    console.print(f"[yellow]⚠ Video processing failed:[/yellow] {e}")
                    console.print("[dim]Raw video saved, but final processing skipped.[/dim]")
                    final_video_path = video_path
                    logger.exception("Video processing error")
            else:
                console.print("[yellow]⚠ FFmpeg not found - skipping video processing[/yellow]")
                console.print(
                    "[dim]Install FFmpeg to enable video compression and processing.[/dim]"
                )
                final_video_path = video_path
        else:
            console.print("  [dim]No video recorded[/dim]")

        console.print(f"  [bold]Timeline:[/bold] {timeline_path}")
        console.print()

        # Show timeline summary

        console.print("[bold]Timeline Summary:[/bold]")
        console.print(f"  • Total duration: {timeline.total_duration:.2f}s")
        console.print(f"  • Total events: {len(timeline.events)}")
        console.print(f"  • Successful: {len(timeline.successful_events)}")
        console.print(f"  • Failed: {len(timeline.failed_events)}")

        if final_video_path:
            console.print()
            console.print(f"[bold green]🎬 Output:[/bold green] {final_video_path}")
        console.print()

        sys.exit(0)

    except SelectorTimeoutError as e:
        console.print()
        console.print("[bold red]✗ Selector Timeout Error[/bold red]")
        console.print(f"  Selector: [cyan]{e.selector}[/cyan]")
        console.print(f"  Timeout: {e.timeout_ms}ms")
        if e.page_url:
            console.print(f"  Page URL: {e.page_url}")
        console.print()
        console.print(
            "[dim]Tip: Check if the selector is correct and the element exists on the page.[/dim]"
        )
        sys.exit(1)

    except NavigationError as e:
        console.print()
        console.print("[bold red]✗ Navigation Error[/bold red]")
        console.print(f"  URL: [cyan]{e.url}[/cyan]")
        if e.reason:
            console.print(f"  Reason: {e.reason}")
        console.print()
        console.print("[dim]Tip: Verify the URL is accessible and the network is available.[/dim]")
        sys.exit(1)

    except ExecutorError as e:
        console.print()
        console.print(f"[bold red]✗ Execution Error:[/bold red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print()
        console.print(f"[bold red]✗ Unexpected Error:[/bold red] {e}")
        logger.exception("Unexpected error during execution")
        sys.exit(1)


__all__ = ["run"]
