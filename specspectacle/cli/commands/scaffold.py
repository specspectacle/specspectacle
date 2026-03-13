"""Scaffold command - Generate YAML template."""

import sys
from pathlib import Path

import click

from specspectacle.utils.logger import console

# YAML template with comprehensive examples
YAML_TEMPLATE = """# SpecSpectacle Demo Specification
# Documentation: https://github.com/fedricknishant/specspectacle

name: "My Product Demo"
description: "A comprehensive demo of my application"
version: "0.1.0"

# ==================== CONFIGURATION ====================
config:
  # Base URL of your application
  target_app: "https://app.example.com"

  # Browser viewport size
  viewport:
    width: 1280
    height: 720

  # Default timeout for element waiting (milliseconds)
  timeout: 5000

  # Run in headless mode (no visible browser)
  headless: true

  # Slow motion delay for smoother recordings (milliseconds)
  slow_motion: 0

# ==================== OUTPUT SETTINGS ====================
output:
  filename: "demo.mp4"
  fps: 30
  bitrate: "5000k"  # Higher = better quality, larger file
  codec: "h264"
  resolution: "1280x720"

# ==================== NARRATION ====================
narration:
  enabled: true
  provider: "openai"
  voice: "en-default"
  speed: 1.0
  language: "en-US"

# ==================== FLOWS ====================
flows:
  # Flow 1: Login Example
  - name: "User Login"
    description: "Demonstrate the login process"

    # Optional: Flow-level narration (plays before flow starts)
    narration:
      text: "In this section, we'll demonstrate how to log into the application."
      timing: "before"
      offset: 0.0

    steps:
      # Example 1: Navigate to a page
      - action: "navigate"
        url: "https://app.example.com/login"
        pause: 2.0  # Pause after action (seconds)
        narration:
          text: "Navigate to the login page"
          timing: "during"
        overlay:
          text: "Step 1: Open Login Page"
          position: "bottom"
          duration: 2.0
          style:
            background_color: "#000000AA"
            text_color: "#FFFFFF"
            font_size: 22

      # Example 2: Click an element
      - action: "click"
        selector: "#email"
        pause: 0.5
        overlay:
          text: "Click email field"
          position: "bottom"
          duration: 1.5

      # Example 3: Type text
      - action: "type"
        selector: "#email"
        text: "demo@example.com"
        delay: 50  # Delay between keystrokes (ms)
        pause: 1.0
        narration:
          text: "Enter your email address"
          timing: "during"

      # Example 4: Another click
      - action: "click"
        selector: "#password"
        pause: 0.5

      # Example 5: Type with hidden password
      - action: "type"
        selector: "#password"
        text: "DemoPassword123"
        delay: 50
        pause: 1.0

      # Example 6: Submit form
      - action: "click"
        selector: "button[type='submit']"
        pause: 2.0
        overlay:
          text: "Submit login form"
          position: "bottom"
          duration: 2.0

      # Example 7: Wait for element to appear
      - action: "wait_for_selector"
        selector: ".dashboard-header"
        timeout: 5000
        pause: 1.5
        overlay:
          text: "Successfully logged in!"
          position: "bottom"
          duration: 2.0

  # Flow 2: Dashboard Navigation
  - name: "Dashboard Tour"
    description: "Explore the main dashboard"

    steps:
      # Example 8: Scroll down the page
      - action: "scroll"
        direction: "down"  # or "up", "left", "right"
        pause: 2.0
        narration:
          text: "Scroll down to view more content"
          timing: "during"

      # Alternative: Scroll to a specific element
      # - action: "scroll"
      #   selector: "#footer"
      #   pause: 2.0

      # Example 9: Hover over an element
      - action: "hover"
        selector: ".chart-widget"
        pause: 1.5
        overlay:
          text: "Hover to see details"
          position: "top-right"
          duration: 1.5

      # Example 10: Select from dropdown
      - action: "select"
        selector: "#time-range"
        value: "last-30-days"
        pause: 1.0
        overlay:
          text: "Change time range"
          position: "bottom"
          duration: 1.5

      # Example 11: Wait for a duration
      - action: "wait"
        duration: 2.0  # Wait 2 seconds
        narration:
          text: "Let the data load"
          timing: "during"

      # Example 12: Take a screenshot (optional)
      - action: "screenshot"
        path: "./screenshots/dashboard.png"  # Optional path
        pause: 0.5

# ==================== TIPS ====================
#
# 1. **Selectors**: Use CSS selectors (id, class, attribute, etc.)
#    - By ID: #my-element
#    - By class: .my-class
#    - By attribute: [data-testid="my-element"]
#    - Complex: div.container > button.primary
#
# 2. **Timing**:
#    - Use `pause` to add delays after actions
#    - Use `narration.timing` to control when narration plays
#    - Use `overlay.duration` to control overlay display time
#
# 3. **Validation**:
#    - Run: specspectacle validate this-file.yaml
#    - This checks your YAML before generating video
#
# 4. **Security**:
#    - Never commit YAML files with real credentials!
#    - Use environment variables: ${ENV_VAR_NAME}
#    - Add sensitive files to .gitignore
#
# 5. **Testing**:
#    - Start with `headless: false` to see the browser
#    - Use `--verbose` flag for debugging
#    - Test small sections before running full demos
#
"""


@click.command()
@click.argument("filename", default="demo-spec.yaml")
@click.option("--force", is_flag=True, help="Overwrite existing file")
def scaffold(filename: str, force: bool):
    """
    Generate a YAML specification template.

    Creates a comprehensive example YAML file with all supported actions,
    narration, and overlay configurations. Use this as a starting point
    for your own demo specifications.

    \b
    Examples:
        specspectacle scaffold
        specspectacle scaffold my-demo.yaml
        specspectacle scaffold test.yaml --force
    """
    output_path = Path(filename)

    # Check if file exists
    if output_path.exists() and not force:
        console.print(f"[red]✗ Error:[/red] File already exists: {filename}")
        console.print("  Use [bold]--force[/bold] to overwrite")
        sys.exit(1)

    # Write template
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(YAML_TEMPLATE)

        console.print(f"[green]✓ Created[/green] YAML template: [cyan]{filename}[/cyan]")
        console.print()
        console.print("Next steps:")
        console.print(f"  1. Edit [bold]{filename}[/bold] with your demo flow")
        console.print(f"  2. Validate: [bold]specspectacle validate {filename}[/bold]")
        console.print(f"  3. Generate: [bold]specspectacle run {filename}[/bold]")
        console.print()
        console.print("[dim]Tip: The template includes examples of all 9 supported actions[/dim]")

        sys.exit(0)

    except Exception as e:
        console.print(f"[red]✗ Error creating file:[/red] {e}")
        sys.exit(1)


__all__ = ["scaffold"]
