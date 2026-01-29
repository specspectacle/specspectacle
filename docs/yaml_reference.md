# SpecSpectacle YAML Reference

Complete reference for writing SpecSpectacle YAML specification files.

## Table of Contents

- [Spec Structure Overview](#spec-structure-overview)
- [Config Section](#config-section)
- [Output Section](#output-section)
- [Narration Section](#narration-section)
- [Flows and Steps](#flows-and-steps)
- [Actions Reference](#actions-reference)
  - [navigate](#navigate)
  - [click](#click)
  - [type](#type)
  - [wait](#wait)
  - [wait_for_selector](#wait_for_selector)
  - [hover](#hover)
  - [scroll](#scroll)
  - [screenshot](#screenshot)
  - [select](#select)
- [Overlay Syntax](#overlay-syntax)
- [Step Narration](#step-narration)
- [Troubleshooting](#troubleshooting)

---

## Spec Structure Overview

Every SpecSpectacle YAML file follows this top-level structure:

```yaml
name: "Demo Name"              # Required: Display name for the demo
version: "0.1.0"               # Required: Semantic version (X.Y.Z)
description: "Description"     # Optional: Brief description

config:                        # Required: Browser configuration
  # ... see Config Section

output:                        # Required: Video output settings
  # ... see Output Section

narration:                     # Optional: Global narration settings
  # ... see Narration Section

flows:                         # Required: List of flows (min 1)
  - name: "Flow Name"
    steps:
      # ... list of actions
```

---

## Config Section

Controls browser behavior and target application.

```yaml
config:
  target_app: "https://example.com"   # Required: Base URL of target application
  viewport:                            # Optional: Browser viewport size
    width: 1280                        # Default: 1280 (min: 800, max: 3840)
    height: 720                        # Default: 720 (min: 600, max: 2160)
  timeout: 5000                        # Optional: Default timeout in ms (min: 1000)
  headless: true                       # Optional: Run browser headlessly (default: true)
  slow_motion: 0                       # Optional: Slow down actions by ms (default: 0)
```

### Example

```yaml
config:
  target_app: "https://www.saucedemo.com"
  viewport: {width: 1920, height: 1080}
  timeout: 10000
  headless: false
  slow_motion: 100
```

---

## Output Section

Controls video output settings.

```yaml
output:
  filename: "demo.mp4"         # Required: Output filename
  fps: 30                      # Optional: Frames per second (15-60, default: 30)
  bitrate: "5000k"             # Optional: Video bitrate (default: "5000k")
  codec: "h264"                # Optional: Video codec (default: "h264")
  resolution: "1280x720"       # Optional: Output resolution (default: "1280x720")
```

### Example

```yaml
output:
  filename: "product_demo.mp4"
  fps: 60
  bitrate: "8000k"
  resolution: "1920x1080"
```

---

## Narration Section

Global settings for text-to-speech narration.

```yaml
narration:
  enabled: true                # Optional: Enable narration (default: true)
  voice: "en-US-Neural2-F"     # Optional: Voice identifier
```

### Example

```yaml
narration:
  enabled: true
  voice: "en-US-Neural2-F"
```

---

## Flows and Steps

Flows are logical sections of your demo containing sequential steps.

```yaml
flows:
  - name: "Flow Name"           # Required: Flow identifier
    description: "Description"  # Optional: Flow description
    narration:                  # Optional: Flow-level narration
      text: "Narration text"
    steps:                      # Required: List of actions (min 1)
      - action: navigate
        url: "https://example.com"
```

---

## Actions Reference

SpecSpectacle supports 9 actions for browser automation.

### navigate

Navigate to a URL.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | - | URL to navigate to (absolute or relative) |
| `pause` | float | No | 0.0 | Pause after action (seconds) |
| `narration` | object | No | - | Step narration |
| `overlay` | object | No | - | Text overlay |

```yaml
- action: navigate
  url: "https://example.com/login"
  narration:
    text: "Navigating to the login page."
  overlay:
    text: "Opening Login Page"
    position: "top"
```

---

### click

Click an element on the page.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `selector` | string | Yes | - | CSS selector of element to click |
| `pause` | float | No | 0.0 | Pause after action (seconds) |
| `narration` | object | No | - | Step narration |
| `overlay` | object | No | - | Text overlay |

```yaml
- action: click
  selector: "#login-button"
  narration:
    text: "Click the login button."
  overlay:
    text: "Logging In..."
    position: "center"
```

---

### type

Type text into an input field.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `selector` | string | Yes | - | CSS selector of input element |
| `text` | string | Yes | - | Text to type |
| `delay` | int | No | 0 | Delay between keystrokes in ms |
| `pause` | float | No | 0.0 | Pause after action (seconds) |
| `narration` | object | No | - | Step narration |
| `overlay` | object | No | - | Text overlay |

```yaml
- action: type
  selector: "#email"
  text: "user@example.com"
  delay: 50
  narration:
    text: "Enter your email address."
```

---

### wait

Wait for a specified duration.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `duration` | float | Yes | - | Duration to wait in seconds (min: 0.1) |
| `narration` | object | No | - | Step narration |
| `overlay` | object | No | - | Text overlay |

```yaml
- action: wait
  duration: 2.0
  overlay:
    text: "Loading..."
    position: "center"
```

---

### wait_for_selector

Wait for an element to appear on the page.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `selector` | string | Yes | - | CSS selector to wait for |
| `timeout` | int | No | 5000 | Timeout in milliseconds (min: 1000) |
| `pause` | float | No | 0.0 | Pause after element found (seconds) |
| `narration` | object | No | - | Step narration |
| `overlay` | object | No | - | Text overlay |

```yaml
- action: wait_for_selector
  selector: ".dashboard-loaded"
  timeout: 10000
  narration:
    text: "Waiting for the dashboard to load."
```

---

### hover

Hover over an element.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `selector` | string | Yes | - | CSS selector of element to hover |
| `pause` | float | No | 0.0 | Pause after action (seconds) |
| `narration` | object | No | - | Step narration |
| `overlay` | object | No | - | Text overlay |

```yaml
- action: hover
  selector: ".menu-item"
  narration:
    text: "Hover to reveal the dropdown menu."
  overlay:
    text: "Menu Options"
    position: "center-right"
```

---

### scroll

Scroll the page or to a specific element.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `direction` | string | Conditional | - | One of: "up", "down", "left", "right" |
| `selector` | string | Conditional | - | CSS selector to scroll into view |
| `pause` | float | No | 0.0 | Pause after action (seconds) |
| `narration` | object | No | - | Step narration |
| `overlay` | object | No | - | Text overlay |

> **Note**: Must specify either `direction` OR `selector`, but not both.

**Direction-based scrolling:**
```yaml
- action: scroll
  direction: "down"
  narration:
    text: "Scrolling down to see more content."
```

**Scroll to element:**
```yaml
- action: scroll
  selector: "#footer"
  narration:
    text: "Scrolling to the footer section."
```

---

### screenshot

Capture a screenshot of the current page.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | string | No | auto-generated | Output path for screenshot |
| `pause` | float | No | 0.0 | Pause after action (seconds) |
| `narration` | object | No | - | Step narration |
| `overlay` | object | No | - | Text overlay |

```yaml
- action: screenshot
  path: "output/screenshots/login_page.png"
  narration:
    text: "Capturing the current state."
```

---

### select

Select an option from a dropdown.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `selector` | string | Yes | - | CSS selector of select element |
| `value` | string | Yes | - | Value attribute of option to select |
| `pause` | float | No | 0.0 | Pause after action (seconds) |
| `narration` | object | No | - | Step narration |
| `overlay` | object | No | - | Text overlay |

```yaml
- action: select
  selector: "#country-dropdown"
  value: "US"
  narration:
    text: "Select United States from the dropdown."
```

---

## Overlay Syntax

Text overlays appear on the video at specific timestamps.

### Overlay Properties

```yaml
overlay:
  text: "Overlay text"         # Required: Text to display
  position: "bottom"           # Optional: Position on screen (default: "bottom")
  duration: 2.0                # Optional: Display duration in seconds (default: 2.0)
  timing: "during"             # Optional: When to show (default: "during")
  style:                       # Optional: Styling options
    background_color: "#000000AA"  # Hex color with alpha (default)
    text_color: "#FFFFFF"          # Hex color (default: white)
    font_size: 22                  # Font size 8-72 (default: 22)
    font_family: "Arial"           # Font family (default: "Arial")
```

### Position Values

| Position | Description |
|----------|-------------|
| `top` | Top center |
| `bottom` | Bottom center |
| `center` | Center of screen |
| `top-left` | Top left corner |
| `top-right` | Top right corner |
| `bottom-left` | Bottom left corner |
| `bottom-right` | Bottom right corner |
| `left` | Center left |
| `right` | Center right |

### Timing Values

| Timing | Description |
|--------|-------------|
| `before` | Show before the action executes |
| `during` | Show while the action executes (default) |
| `after` | Show after the action completes |

### Overlay Examples

**Basic overlay:**
```yaml
overlay:
  text: "Welcome!"
  position: "center"
```

**Styled overlay:**
```yaml
overlay:
  text: "⚠️ Important Step"
  position: "top-right"
  duration: 3.0
  style:
    background_color: "#FF5733EE"
    text_color: "#FFFFFF"
    font_size: 28
```

---

## Step Narration

Add voice narration to any step.

### Narration Properties

```yaml
narration:
  text: "Narration text"       # Required: Text to speak
  timing: "during"             # Optional: When to speak (default: "during")
  offset: 0.0                  # Optional: Offset in seconds (default: 0.0)
```

### Example

```yaml
- action: click
  selector: "#submit"
  narration:
    text: "Click submit to complete the form."
    timing: "before"
    offset: 0.5
```

---

## Troubleshooting

### Common YAML Validation Errors

**"Invalid target_app URL"**
- Ensure `target_app` starts with `http://` or `https://`
- Check for typos in the URL

**"Invalid selector"**
- Verify CSS selector syntax is valid
- Use browser DevTools to test selectors
- Common selectors: `#id`, `.class`, `[data-test='value']`

**"Invalid hex color"**
- Use format `#RRGGBB` or `#RRGGBBAA` for transparency
- Example: `#FF5733` (red-orange) or `#000000AA` (semi-transparent black)

**"Invalid position"**
- Must be one of the 9 valid positions listed above
- Check for typos (e.g., "topleft" vs "top-left")

### Selector Not Found Errors

**"SelectorTimeoutError"**
- Element may not exist on the page
- Page may not have finished loading - add `wait_for_selector` first
- Selector may be dynamically generated - check for unique attributes
- Increase `timeout` value in config or action

**Tips:**
```yaml
# Wait for page to load before interacting
- action: wait_for_selector
  selector: "#main-content"
  timeout: 10000

# Then proceed with actions
- action: click
  selector: "#submit-button"
```

### FFmpeg Issues

**"FFmpeg not found"**
- Install FFmpeg: `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux)
- Ensure FFmpeg is in your system PATH
- Test with: `ffmpeg -version`

### TTS/Narration Issues

**"TTS API error" or silent video**
- Check your API key is set correctly in `.env`
- Verify internet connectivity
- Use `--no-narration` flag to skip narration and generate silent video

### Video Quality Issues

**Video appears blurry:**
- Increase `bitrate` in output settings (try "8000k" or higher)
- Match `resolution` to `viewport` size
- Ensure source content is high quality

**Video is too large:**
- Reduce `bitrate` (try "3000k")
- Reduce `fps` to 24 or 25
- Use smaller `resolution`

### Performance Tips

1. **Use headless mode** for faster execution: `headless: true`
2. **Minimize waits** - use `wait_for_selector` instead of fixed `wait` durations
3. **Batch overlays** - avoid excessive overlay transitions
4. **Test incrementally** - validate YAML before full runs: `specspectacle validate demo.yaml`

---

## Complete Example

```yaml
name: "Complete Demo Example"
version: "0.1.0"
description: "Demonstrates all YAML features"

config:
  target_app: "https://www.saucedemo.com"
  viewport: {width: 1280, height: 720}
  timeout: 5000
  headless: false

output:
  filename: "complete_demo.mp4"
  fps: 30
  resolution: "1280x720"

narration:
  enabled: true
  voice: "en-US-Neural2-F"

flows:
  - name: "Login Flow"
    description: "Demonstrate login functionality"
    steps:
      - action: navigate
        url: "https://www.saucedemo.com"
        overlay:
          text: "Welcome to the Demo"
          position: "center"
          style: {font_size: 32}
        narration:
          text: "Let's log in to the application."

      - action: wait_for_selector
        selector: "#user-name"

      - action: type
        selector: "#user-name"
        text: "standard_user"
        delay: 50
        narration:
          text: "Enter the username."

      - action: type
        selector: "#password"
        text: "secret_sauce"
        delay: 50

      - action: click
        selector: "#login-button"
        overlay:
          text: "Logging in..."
          position: "center"
        narration:
          text: "Click to log in."

      - action: wait_for_selector
        selector: ".inventory_list"
        overlay:
          text: "Success!"
          position: "top"
          style: {background_color: "#28A745EE"}
        narration:
          text: "We are now logged in."
```
