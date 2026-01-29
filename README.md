# SpecSpectacle

**Turn specs into spectacles** – YAML user journeys to live product demos.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-released%20v0.1.0-brightgreen.svg)]()

---

## What is SpecSpectacle?

SpecSpectacle is an open-source CLI tool that transforms YAML specifications into polished product demo videos. Write a YAML file describing your user journey, run a single command, and get an MP4 video with:

- 🎬 **Automated browser recording** via Playwright
- 🗣️ **English narration** with Text-to-Speech
- 📝 **On-screen text overlays** at precise timestamps
- 🔄 **Version-controlled demos** that live in your repo

Perfect for developers who want reproducible, code-driven demo videos without manual screen recording or video editing.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- ffmpeg installed ([installation guide](https://ffmpeg.org/download.html))

### Installation

```bash
# Install from PyPI (when v0.1.0 is released)
pip install specspectacle

# Install Chromium browser for Playwright
playwright install chromium
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/fedricknishant/specspectacle.git
cd specspectacle

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Install Playwright browser
playwright install chromium

# Set up environment variables
cp .env.example .env
# Edit .env and add your TTS API key
```

---

## 📖 Usage

### 1. Create a YAML Spec

```bash
specspectacle scaffold demo.yaml
```

This generates a template YAML with commented examples.

### 2. Validate Your Spec

```bash
specspectacle validate demo.yaml
```

### 3. Generate Your Demo Video

```bash
specspectacle run demo.yaml
```

Your video will be saved to `./output/demo.mp4`!

---

### Future
- Multi-language support
- SaaS backend with cloud rendering
- GitHub Action integration
- Web UI for visual flow editing
- Template library

---

## 📚 Documentation

- [YAML Reference](https://github.com/fedricknishant/specspectacle/blob/main/docs/yaml_reference.md) - Complete YAML specification guide
- [Contributing Guide](https://github.com/fedricknishant/specspectacle/blob/main/CONTRIBUTING.md) - How to contribute to SpecSpectacle

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](https://github.com/fedricknishant/specspectacle/blob/main/CONTRIBUTING.md) for:
- Development environment setup
- How to run tests
- Code style guidelines (Black, isort, type hints)
- Pull request process

---

## 📜 License

Apache 2.0 - See [LICENSE](https://github.com/fedricknishant/specspectacle/blob/main/LICENSE) for details.

---

## 🎬 Example

```yaml
name: "Simple Login Demo"
version: "0.1.0"

config:
  target_app: "https://app.example.com"
  viewport:
    width: 1280
    height: 720

flows:
  - name: "Login"
    steps:
      - action: "navigate"
        url: "https://app.example.com/login"
        narration:
          text: "Navigate to the login page"
        overlay:
          text: "Step 1: Open login page"
          position: "bottom"
          
      - action: "type"
        selector: "#email"
        text: "user@example.com"
        narration:
          text: "Enter your email address"
```

Run with:
```bash
specspectacle run login-demo.yaml
```

---

## 🙏 Acknowledgments

Built with:
- [Playwright](https://playwright.dev/) - Browser automation
- [Click](https://click.palletsprojects.com/) - CLI framework
- [FFmpeg](https://ffmpeg.org/) - Video processing
- [Pydantic](https://pydantic.dev/) - Data validation

---

**Status**: ✅ Phase 1 complete! v0.1.0 release coming soon.
