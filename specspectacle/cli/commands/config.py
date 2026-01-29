"""Config command - Show system configuration."""

import os
import shutil
import sys
from pathlib import Path

import click
from rich.table import Table

from specspectacle import __version__
from specspectacle.utils.logger import console

try:
    import playwright

    PLAYWRIGHT_VERSION = playwright.__version__
except:
    PLAYWRIGHT_VERSION = "Not installed"


@click.command()
def config():
    """
    Display SpecSpectacle configuration and system information.

    Shows current settings, paths, and installed dependencies.
    Useful for troubleshooting and verifying installation.

    \b
    Example:
        specspectacle config
    """
    console.print()
    console.print("[bold cyan]SpecSpectacle Configuration[/bold cyan]")
    console.print()

    # Version info
    table = Table(title=" Package Information", show_header=True, header_style="bold cyan")
    table.add_column("Component", style="cyan")
    table.add_column("Version/Status", style="white")

    table.add_row("SpecSpectacle", __version__)
    table.add_row("Playwright", PLAYWRIGHT_VERSION)

    # Check ffmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        table.add_row("FFmpeg", f"✓ Found at {ffmpeg_path}")
    else:
        table.add_row("FFmpeg", "[red]✗ Not found in PATH[/red]")

    console.print(table)
    console.print()

    # Paths
    paths_table = Table(title="📁 Paths", show_header=True, header_style="bold cyan")
    paths_table.add_column("Path Type", style="cyan")
    paths_table.add_column("Location", style="white")

    config_dir = Path.home() / ".specspectacle"
    config_file = config_dir / "config.yaml"
    log_dir = config_dir / "logs"

    paths_table.add_row("Config Directory", str(config_dir))
    paths_table.add_row(
        "Config File",
        str(config_file)
        + (" [dim](exists)[/dim]" if config_file.exists() else " [dim](not created)[/dim]"),
    )
    paths_table.add_row(
        "Log Directory",
        str(log_dir)
        + (" [dim](exists)[/dim]" if log_dir.exists() else " [dim](not created)[/dim]"),
    )

    # Output directory from env or default
    output_dir = os.getenv("SPECSPECTACLE_OUTPUT_DIR", "./output")
    paths_table.add_row("Output Directory", output_dir)

    console.print(paths_table)
    console.print()

    # Environment variables
    env_table = Table(title="🔧 Environment Variables", show_header=True, header_style="bold cyan")
    env_table.add_column("Variable", style="cyan")
    env_table.add_column("Status", style="white")

    # TTS API Key
    tts_key = os.getenv("SPECSPECTACLE_TTS_API_KEY")
    if tts_key:
        # Mask the key for security
        masked = tts_key[:7] + "..." + tts_key[-4:] if len(tts_key) > 11 else "***"
        env_table.add_row("SPECSPECTACLE_TTS_API_KEY", f"✓ Set ({masked})")
    else:
        env_table.add_row(
            "SPECSPECTACLE_TTS_API_KEY",
            "[yellow]Not set (required for narration)[/yellow]",
        )

    # Log level
    log_level = os.getenv("SPECSPECTACLE_LOG_LEVEL", "INFO")
    env_table.add_row("SPECSPECTACLE_LOG_LEVEL", log_level)

    # Custom output dir
    if os.getenv("SPECSPECTACLE_OUTPUT_DIR"):
        env_table.add_row("SPECSPECTACLE_OUTPUT_DIR", os.getenv("SPECSPECTACLE_OUTPUT_DIR"))

    # Custom ffmpeg path
    if os.getenv("FFMPEG_PATH"):
        env_table.add_row("FFMPEG_PATH", os.getenv("FFMPEG_PATH"))

    console.print(env_table)
    console.print()

    # Installation check
    all_good = True

    if not ffmpeg_path:
        console.print(
            "[yellow]⚠ Warning:[/yellow] FFmpeg not found. Install from: https://ffmpeg.org/download.html"
        )
        all_good = False

    if PLAYWRIGHT_VERSION == "Not installed":
        console.print("[yellow]⚠ Warning:[/yellow] Playwright not installed properly")
        all_good = False

    if not tts_key:
        console.print(
            "[yellow]⚠ Info:[/yellow] TTS API key not set. Set in .env for narration features"
        )

    if all_good and tts_key:
        console.print("[green]✓ All systems ready![/green]")
    elif all_good:
        console.print("[green]✓ Core systems ready![/green] (TTS optional for Phase 1)")

    console.print()
    console.print("[dim]Config file location: ~/.specspectacle/config.yaml[/dim]")
    console.print("[dim]Logs location: ~/.specspectacle/logs/[/dim]")
    console.print()

    sys.exit(0)


__all__ = ["config"]
