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
                check_ffmpeg_installed,
            )

            # Check if FFmpeg is available for video processing
            if check_ffmpeg_installed():
                console.print()
                console.print("[bold cyan]Processing Video (Unified MoviePy Render)...[/bold cyan]")
                console.print(f"  Compression: {compression}, Resolution: {spec.output.resolution}")

                try:
                    # Create MoviePy video processor
                    from specspectacle.video.moviepy_processor import MoviePyProcessor

                    raw_video_path = Path(video_path)
                    processor = MoviePyProcessor(raw_video_path, out_path)

                    # Unified Render Pass
                    final_video_path = processor.full_render(
                        output_filename=spec.output.filename,
                        timeline=timeline,
                        spec=spec,
                        no_narration=no_narration,
                        no_overlays=no_overlays,
                        compression_preset=compression,
                    )

                    console.print("[bold green]✓ Unified Video Rendering Complete![/bold green]")
                    console.print(f"  [bold]Final Video:[/bold] {final_video_path}")

                    if not keep_artifacts:
                        with contextlib.suppress(OSError):
                            raw_video_path.unlink()

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
