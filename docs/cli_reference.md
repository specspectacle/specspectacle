# SpecSpectacle CLI Reference

Complete reference for SpecSpectacle command-line interface.

## Table of Contents

- [Global Options](#global-options)
- [Commands](#commands)
  - [run](#run)
  - [validate](#validate)
  - [scaffold](#scaffold)
  - [config](#config)
- [Exit Codes](#exit-codes)
- [Environment Variables](#environment-variables)

---

## Global Options

These options are available for the main `specspectacle` command:

| Option | Description |
|--------|-------------|
| `--version` | Show version number and exit |
| `--help` | Show help message and exit |

**Usage:**

```bash
specspectacle --version
specspectacle --help
```

---

## Commands

### run

Execute a YAML specification and generate a demo video.

**Usage:**

```bash
specspectacle run <YAML_FILE> [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `YAML_FILE` | Path to the YAML specification file (required) |

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output-dir PATH` | path | `./output/videos` | Override output directory |
| `--headless/--headed` | flag | `--headless` | Run browser in headless or headed mode |
| `-v, --verbose` | flag | off | Enable debug logging |
| `--dry-run` | flag | off | Validate and show execution plan without running |
| `--keep-artifacts` | flag | off | Keep intermediate files after processing |
| `--compression` | choice | `medium` | Video compression preset (`low`, `medium`, `high`) |
| `--no-narration` | flag | off | Skip TTS generation (silent video) |
| `--no-overlays` | flag | off | Skip text overlay rendering |
| `--help` | - | - | Show help and exit |

**Examples:**

```bash
# Basic usage
specspectacle run demo.yaml

# Run with visible browser and debug output
specspectacle run demo.yaml --headed --verbose

# Preview execution plan without running
specspectacle run demo.yaml --dry-run

# Generate silent video with high compression
specspectacle run demo.yaml --no-narration --compression high

# Custom output directory and keep intermediate files
specspectacle run demo.yaml --output-dir ./output/my-demo --keep-artifacts
```

---

### validate

Validate a YAML specification file against the SpecSpectacle schema.

**Usage:**

```bash
specspectacle validate <YAML_FILE>
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `YAML_FILE` | Path to the YAML specification file to validate (required) |

**Options:**

| Option | Description |
|--------|-------------|
| `--help` | Show help and exit |

**Examples:**

```bash
# Validate a YAML file
specspectacle validate demo.yaml
```

**Output:**

On success, displays:
- Confirmation that YAML is valid
- Spec name and version
- Number of flows and steps
- Narration and overlay counts
- Output filename

On failure, displays:
- Detailed validation error messages
- Tip to check YAML schema documentation

---

### scaffold

Generate a YAML specification template with comprehensive examples.

**Usage:**

```bash
specspectacle scaffold [FILENAME] [OPTIONS]
```

**Arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `FILENAME` | `demo-spec.yaml` | Output filename for the template |

**Options:**

| Option | Description |
|--------|-------------|
| `--force` | Overwrite existing file |
| `--help` | Show help and exit |

**Examples:**

```bash
# Create default template (demo-spec.yaml)
specspectacle scaffold

# Create template with custom name
specspectacle scaffold my-demo.yaml

# Overwrite existing file
specspectacle scaffold test.yaml --force
```

**Template Contents:**

The generated template includes:
- Complete configuration section
- Output settings examples
- Narration configuration
- Example flows with all 9 supported actions
- Overlay examples with styling
- Tips and best practices

---

### config

Display SpecSpectacle configuration and system information.

**Usage:**

```bash
specspectacle config
```

**Options:**

| Option | Description |
|--------|-------------|
| `--help` | Show help and exit |

**Output:**

Displays three information tables:

1. **Package Information**
   - SpecSpectacle version
   - Playwright version
   - FFmpeg status and path

2. **Paths**
   - Config directory (`~/.specspectacle`)
   - Config file location
   - Log directory
   - Output directory

3. **Environment Variables**
   - TTS API key status (masked)
   - Log level
   - Custom output directory
   - FFmpeg path override

**Example:**

```bash
specspectacle config
```

---

## Exit Codes

SpecSpectacle commands use the following exit codes:

| Code | Meaning | Commands |
|------|---------|----------|
| `0` | Success | All commands |
| `1` | General error | All commands |

### Detailed Exit Conditions

**Exit Code 0 (Success):**
- `run`: Video generated successfully or dry-run completed
- `validate`: YAML validation passed
- `scaffold`: Template created successfully
- `config`: Configuration displayed

**Exit Code 1 (Error):**
- File not found
- YAML validation failed
- Selector timeout during execution
- Navigation error (unreachable URL)
- Execution error (generic)
- Unexpected error
- File already exists (scaffold without `--force`)
- Template creation failed

---

## Environment Variables

SpecSpectacle recognizes the following environment variables:

| Variable | Description | Status |
|----------|-------------|--------|
| `SPECSPECTACLE_LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | ✅ **Active** - Controls log verbosity |

> **Note:** The following variables are displayed by `specspectacle config` for informational purposes but are not currently wired into the application logic:
> - `SPECSPECTACLE_OUTPUT_DIR` - Use `--output-dir` flag instead
> - `FFMPEG_PATH` - FFmpeg is found via system PATH

### Setting Environment Variables

**Using a `.env` file:**

```bash
# .env
SPECSPECTACLE_LOG_LEVEL=DEBUG
```

**Using shell export:**

```bash
# Bash/Zsh
export SPECSPECTACLE_LOG_LEVEL="DEBUG"
```

### TTS / Narration

SpecSpectacle uses **Edge TTS** for text-to-speech, which runs locally and requires no API key. Use `--no-narration` flag to generate silent videos if needed.

---

## Quick Reference

```bash
# Show version
specspectacle --version

# Get help
specspectacle --help
specspectacle run --help

# Create a new spec template
specspectacle scaffold my-demo.yaml

# Validate before running
specspectacle validate my-demo.yaml

# Generate video
specspectacle run my-demo.yaml

# Debug mode with visible browser
specspectacle run my-demo.yaml --headed --verbose

# Silent video with no overlays
specspectacle run my-demo.yaml --no-narration --no-overlays

# Check system configuration
specspectacle config
```

---

## See Also

- [YAML Reference](yaml_reference.md) - Complete YAML specification syntax
- [README](../README.md) - Installation and quick start guide
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
