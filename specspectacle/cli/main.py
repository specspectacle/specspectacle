"""
SpecSpectacle CLI - Main entry point
"""

import click
from dotenv import load_dotenv

from specspectacle import __version__

# Load environment variables
load_dotenv()

# Import commands
from specspectacle.cli.commands import config, run, scaffold, validate


@click.group()
@click.version_option(version=__version__, prog_name="specspectacle")
@click.pass_context
def cli(ctx):
    """
    SpecSpectacle - Turn specs into spectacles

    Transform YAML specifications into polished product demo videos
    with automated browser recording, narration, and text overlays.

    \b
    Quick Start:
      1. Create a YAML spec:     specspectacle scaffold demo.yaml
      2. Validate your spec:     specspectacle validate demo.yaml
      3. Generate your video:    specspectacle run demo.yaml

    \b
    Documentation: https://github.com/fedricknishant/specspectacle
    """
    # Ensure ctx.obj exists (used for passing data between commands)
    ctx.ensure_object(dict)


# Register commands
cli.add_command(validate.validate)
cli.add_command(scaffold.scaffold)
cli.add_command(config.config)
cli.add_command(run.run)


if __name__ == "__main__":
    cli()
