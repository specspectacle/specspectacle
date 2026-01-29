# SpecSpectacle Troubleshooting Guide

This guide covers common issues you may encounter when using SpecSpectacle and how to resolve them.

## Table of Contents

- [YAML Validation Errors](#yaml-validation-errors)
- [Selector Not Found Errors](#selector-not-found-errors)
- [FFmpeg Installation Issues](#ffmpeg-installation-issues)
- [TTS / Narration Errors](#tts--narration-errors)
- [Video Quality Issues](#video-quality-issues)
- [Performance Tips](#performance-tips)
- [Additional Resources](#additional-resources)

---

## YAML Validation Errors

When SpecSpectacle fails to parse your YAML specification, it provides detailed error messages. Here are the most common issues and solutions:

### File Not Found

**Error:**
```
YAML file not found: path/to/demo.yaml
```

**Solution:**
- Verify the file path is correct
- Check for typos in the filename
- Ensure you're running the command from the correct directory

### Empty YAML File

**Error:**
```
Empty YAML file
```

**Solution:**
- Add required content to your YAML file
- Use `specspectacle scaffold demo.yaml` to generate a template

### YAML Syntax Errors

**Error:**
```
Error parsing YAML: ...
```

**Common Causes & Solutions:**

| Issue | Example | Fix |
|-------|---------|-----|
| Incorrect indentation | Mixing tabs and spaces | Use spaces only (2 or 4 space indent) |
| Missing quotes | `text: Click here:` | `text: "Click here:"` |
| Unescaped special chars | `selector: [data-id]` | `selector: "[data-id]"` |
| Invalid YAML structure | Missing `:` after key | Check syntax around the error line |

**Tip:** Use a YAML validator like [yamllint](https://www.yamllint.com/) to check syntax before running.

### Schema Validation Errors

**Error:**
```
Validation error at config.viewport.width: Input should be greater than or equal to 800
```

**Common Validation Issues:**

| Field | Error | Valid Range/Values |
|-------|-------|-------------------|
| `viewport.width` | Below minimum | 800 - 3840 |
| `viewport.height` | Below minimum | 600 - 2160 |
| `output.fps` | Out of range | 15 - 60 |
| `overlay.font_size` | Out of range | 8 - 72 |
| `timeout` | Below minimum | ≥ 1000ms |

**Invalid target_app URL:**
```yaml
# ❌ Invalid
config:
  target_app: "example.com"

# ✅ Valid
config:
  target_app: "https://example.com"
```

**Invalid overlay position:**
```yaml
# ❌ Invalid positions
position: "topleft"    # Wrong format
position: "middle"     # Not a valid option

# ✅ Valid positions
position: "top-left"
position: "center"
position: "bottom-right"
```

**Valid positions:** `top`, `bottom`, `center`, `top-left`, `top-right`, `bottom-left`, `bottom-right`, `left`, `right`

**Invalid hex color:**
```yaml
# ❌ Invalid
background_color: "red"
background_color: "#FFF"

# ✅ Valid
background_color: "#FF5733"
background_color: "#000000AA"  # With alpha channel
```

### Missing Required Fields

**Error:**
```
Field required at flows.0.steps.0.action
```

**Solution:** Ensure all required fields are present:

```yaml
# Required top-level fields
name: "Demo Name"           # Required
version: "0.1.0"            # Required
config:                     # Required
  target_app: "https://..."
output:                     # Required
  filename: "output.mp4"
flows:                      # Required (at least 1)
  - name: "Flow 1"         # Required
    steps:                 # Required (at least 1)
      - action: navigate   # Required per step
        url: "..."         # Action-specific requirements
```

---

## Selector Not Found Errors

Selector errors are the most common runtime issues. They occur when SpecSpectacle cannot find an element on the page.

### SelectorTimeoutError

**Error:**
```
SelectorTimeoutError: Timeout waiting for selector "#login-button"
Details:
  Selector: #login-button
  Timeout: 5000ms
  Flow: Login Flow
  Step: click (step 3)
```

**Common Causes:**

1. **Element doesn't exist** - The selector is wrong or the element isn't on the page
2. **Page hasn't loaded** - Need to wait for the page to fully load
3. **Dynamic content** - Element is loaded via JavaScript and takes time
4. **Element is hidden** - Element exists but isn't visible/interactable

### Solutions by Cause

**1. Verify the selector exists:**

```bash
# Open browser DevTools (F12) and test your selector in Console:
document.querySelector("#login-button")

# If returns null, the selector is wrong
```

**2. Wait for page to load:**

```yaml
steps:
  - action: navigate
    url: "https://example.com"
  
  # Add wait_for_selector before interacting
  - action: wait_for_selector
    selector: "#main-content"
    timeout: 10000
  
  - action: click
    selector: "#login-button"
```

**3. Increase timeout for slow pages:**

```yaml
# Global timeout
config:
  timeout: 10000  # 10 seconds

# Or per-action timeout
- action: wait_for_selector
  selector: ".slow-loading-element"
  timeout: 15000
```

**4. Use more reliable selectors:**

| Selector Type | Reliability | Example |
|---------------|-------------|---------|
| `id` | ✅ Best | `#submit-btn` |
| `data-*` attributes | ✅ Good | `[data-testid="login"]` |
| `class` (unique) | ⚠️ OK | `.unique-button` |
| `class` (common) | ❌ Fragile | `.btn` |
| Complex CSS | ⚠️ Fragile | `div > ul > li:first-child` |

**Best practices for selectors:**

```yaml
# ✅ Preferred: ID selectors
selector: "#submit-button"

# ✅ Preferred: data-test attributes
selector: "[data-testid='login-btn']"
selector: "[data-cy='submit']"

# ⚠️ OK: Unique class names
selector: ".product-add-to-cart"

# ❌ Avoid: Generic or complex selectors
selector: ".btn.btn-primary"
selector: "div.container > form > button"
```

### NavigationError

**Error:**
```
NavigationError: Failed to navigate to https://invalid-url.test
```

**Solutions:**
- Verify the URL is correct and accessible
- Check internet connectivity
- Ensure the target server is running (for local development)
- Check for CORS or authentication requirements

---

## FFmpeg Installation Issues

FFmpeg is required for video processing, compression, and audio mixing.

### FFmpeg Not Found

**Error:**
```
FFmpeg not found. Please install FFmpeg and ensure it's in your PATH.
```

**Check if FFmpeg is installed:**
```bash
ffmpeg -version
```

### Installation by Platform

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**RHEL/CentOS/Fedora:**
```bash
sudo dnf install ffmpeg
# or
sudo yum install ffmpeg
```

**Windows (Chocolatey):**
```powershell
choco install ffmpeg
```

**Windows (Manual):**
1. Download from [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Extract to a folder (e.g., `C:\Program Files\ffmpeg`)
3. Add `C:\Program Files\ffmpeg\bin` to your PATH environment variable

### Verifying FFmpeg Installation

After installation, verify it's working:

```bash
# Check version
ffmpeg -version

# Should output something like:
# ffmpeg version 6.1.1 Copyright (c) 2000-2024 the FFmpeg developers
```

You can also use SpecSpectacle to check:
```bash
specspectacle config
```

This will show whether FFmpeg is found and its path.

### FFmpeg Execution Errors

**Error:**
```
FFmpegExecutionError: FFmpeg command failed with exit code 1
```

**Common Causes:**
- Insufficient disk space
- Invalid input files
- Codec not available
- Permission issues on output directory

**Solutions:**
- Check available disk space
- Ensure input files exist and are valid
- Try a different codec in output settings
- Check write permissions on the output directory

---

## TTS / Narration Errors

SpecSpectacle uses **Edge TTS** for text-to-speech, which runs locally and requires no API key.

### Silent Video / No Audio

**Possible Causes:**
1. TTS generation failed silently
2. Audio file wasn't created
3. Audio mixing failed

**Solutions:**

**Check if narration is enabled:**
```yaml
narration:
  enabled: true  # Must be true for narration
```

**Generate a silent video intentionally:**
```bash
specspectacle run demo.yaml --no-narration
```

### TTS Connectivity Issues

Edge TTS requires internet connectivity to function. If you're offline:

```bash
# Generate video without narration
specspectacle run demo.yaml --no-narration
```

### Audio Generation Failures

**Error:**
```
RuntimeError: Audio concatenation failed
```

**Solutions:**
1. Ensure FFmpeg is installed (required for audio processing)
2. Check available disk space for temp files
3. Run with `--keep-artifacts` to inspect intermediate audio files:
   ```bash
   specspectacle run demo.yaml --keep-artifacts --verbose
   ```

### Voice Configuration

**Available voices:** Edge TTS supports many voices. The default voice is `en-US-AriaNeural`.

```yaml
narration:
  enabled: true
  voice: "en-US-AriaNeural"     # Default female voice
  # voice: "en-US-GuyNeural"    # Male voice
  # voice: "en-GB-SoniaNeural"  # British English
```

---

## Video Quality Issues

### Video Appears Blurry

**Causes:**
- Low bitrate
- Resolution mismatch
- Source content quality

**Solutions:**

**Increase bitrate:**
```yaml
output:
  filename: "demo.mp4"
  bitrate: "8000k"  # Increase from default 5000k
```

**Match resolution to viewport:**
```yaml
config:
  viewport:
    width: 1920
    height: 1080

output:
  resolution: "1920x1080"  # Match viewport
```

**Recommended settings for high quality:**
```yaml
output:
  filename: "high_quality_demo.mp4"
  fps: 60
  bitrate: "10000k"
  resolution: "1920x1080"
```

### Video File Too Large

**Solutions:**

**Reduce bitrate:**
```yaml
output:
  bitrate: "3000k"  # Lower bitrate = smaller file
```

**Reduce FPS:**
```yaml
output:
  fps: 24  # Standard film rate, reduced from 30 or 60
```

**Use compression preset:**
```bash
specspectacle run demo.yaml --compression high
```

**Compression presets:**
| Preset | Description |
|--------|-------------|
| `low` | Minimal compression, highest quality |
| `medium` | Balanced (default) |
| `high` | Maximum compression, smaller file |

**Reduce resolution:**
```yaml
output:
  resolution: "1280x720"  # 720p instead of 1080p
```

### Video/Audio Sync Issues

**Causes:**
- Incorrect timing in overlays
- Very long narration vs short actions

**Solutions:**

**Add pauses to allow narration to complete:**
```yaml
- action: click
  selector: "#button"
  pause: 2.0  # Wait 2 seconds after action
  narration:
    text: "This is a longer explanation that needs time."
```

**Use appropriate timing for overlays:**
```yaml
overlay:
  text: "Important info"
  timing: "during"  # before, during, after
  duration: 3.0     # Show for 3 seconds
```

---

## Performance Tips

### Optimize for Faster Execution

**1. Use headless mode (default):**
```yaml
config:
  headless: true  # Browser runs in background
```

**2. Use `wait_for_selector` instead of fixed waits:**
```yaml
# ❌ Slow: Fixed wait
- action: wait
  duration: 5.0

# ✅ Faster: Wait only until element is ready
- action: wait_for_selector
  selector: "#content-loaded"
  timeout: 5000
```

**3. Set appropriate timeouts:**
```yaml
config:
  timeout: 5000  # 5 seconds is usually enough
```

### Validate Before Running

Always validate your YAML before running to catch errors early:

```bash
specspectacle validate demo.yaml
```

This is much faster than discovering issues during video generation.

### Use Dry Run for Testing

Preview your execution plan without actually running:

```bash
specspectacle run demo.yaml --dry-run
```

### Debug with Verbose Mode

When troubleshooting, use verbose mode to see detailed logs:

```bash
specspectacle run demo.yaml --verbose
```

### Keep Artifacts for Debugging

Preserve intermediate files to diagnose issues:

```bash
specspectacle run demo.yaml --keep-artifacts
```

Intermediate files include:
- Individual audio segments
- Screenshots
- Temporary video files

### Use Headed Mode for Development

See what's happening in the browser:

```bash
specspectacle run demo.yaml --headed --verbose
```

### Minimize Overlay Transitions

Too many overlay changes can affect performance:

```yaml
# ❌ Many rapid overlays
steps:
  - action: click
    overlay: { text: "Step 1" }
  - action: click
    overlay: { text: "Step 2" }
  - action: click
    overlay: { text: "Step 3" }

# ✅ Group actions with fewer overlays
steps:
  - action: click
    selector: "#step1"
  - action: click
    selector: "#step2"
  - action: click
    selector: "#step3"
    overlay:
      text: "Completed steps 1-3"
      duration: 3.0
```

### Reduce Resolution for Faster Previews

During development, use lower resolution:

```yaml
# Development settings
output:
  filename: "preview.mp4"
  fps: 24
  resolution: "1280x720"
  bitrate: "3000k"
```

Then switch to higher quality for final output.

---

## Additional Resources

- [CLI Reference](cli_reference.md) - Complete command-line options
- [YAML Reference](yaml_reference.md) - Full YAML specification syntax
- [README](../README.md) - Installation and quick start

### Getting Help

If you encounter issues not covered here:

1. Run with `--verbose` to get detailed debug output
2. Check the [YAML Reference](yaml_reference.md) for correct syntax
3. Use `specspectacle validate` to catch schema errors early
4. Report issues with the verbose output for faster resolution

---

## Quick Reference: Error Solutions

| Error | Quick Solution |
|-------|----------------|
| YAML file not found | Check file path and current directory |
| Invalid target_app URL | Add `https://` prefix |
| SelectorTimeoutError | Add `wait_for_selector` before action |
| FFmpeg not found | `brew install ffmpeg` (macOS) |
| Silent video | Check `narration.enabled: true` |
| Blurry video | Increase `bitrate` to `8000k` |
| Large file size | Use `--compression high` |
| Slow execution | Use `headless: true` and `wait_for_selector` |
