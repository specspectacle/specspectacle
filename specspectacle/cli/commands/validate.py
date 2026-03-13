"""Validate command - Validate YAML spec against schema."""

import sys

import click
from pydantic import ValidationError

from specspectacle.parser.yaml_parser import YAMLParser
from specspectacle.utils.logger import console, logger


@click.command()
@click.argument("yaml_file", type=click.Path(exists=True))
def validate(yaml_file: str):
    """
    Validate a YAML specification file.

    Checks the YAML file against the SpecSpectacle schema and reports
    any validation errors. Useful for catching issues before running.

    \b
    Example:
        specspectacle validate demo.yaml
    """
    logger.debug(f"Validating YAML file: {yaml_file}")

    try:
        # Parse and validate
        spec = YAMLParser.parse(yaml_file)

        # Count flows and steps
        total_steps = sum(len(flow.steps) for flow in spec.flows)
        narration_count = sum(1 for flow in spec.flows for step in flow.steps if step.narration)
        overlay_count = sum(1 for flow in spec.flows for step in flow.steps if step.overlay)

        # Success output
        console.print("✓ [green]YAML is valid[/green]")
        console.print(f"✓ Spec: [cyan]{spec.name}[/cyan] v{spec.version}")
        console.print(
            f"✓ Found [cyan]{len(spec.flows)}[/cyan] flow(s) with [cyan]{total_steps}[/cyan] total step(s)"
        )

        if narration_count > 0:
            console.print(f"✓ Narration: [cyan]{narration_count}[/cyan] step(s) with narration")

        if overlay_count > 0:
            console.print(f"✓ Overlays: [cyan]{overlay_count}[/cyan] step(s) with text overlays")

        console.print(f"✓ Output: [cyan]{spec.output.filename}[/cyan]")
        console.print()
        console.print(
            f"[green]✓ Ready to run![/green] Use: [bold]specspectacle run {yaml_file}[/bold]"
        )

        sys.exit(0)

    except FileNotFoundError as e:
        console.print(f"[red]✗ Error:[/red] {e}", style="red")
        sys.exit(1)

    except ValidationError as e:
        console.print("[red]✗ YAML validation failed[/red]")
        console.print()
        console.print(YAMLParser.format_validation_error(e))
        console.print()
        console.print("[yellow]Tip:[/yellow] Check the YAML schema at: docs/yaml_reference.md")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]✗ Unexpected error:[/red] {e}")
        logger.exception("Unexpected error during validation")
        sys.exit(1)


__all__ = ["validate"]
