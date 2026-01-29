# Contributing to SpecSpectacle

Thank you for your interest in contributing to SpecSpectacle! This document provides guidelines and instructions to help you get started.

---

## 📋 Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Running Tests](#running-tests)
- [Code Style Guidelines](#code-style-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

---

## 🛠️ Development Environment Setup

### Prerequisites

- **Python 3.10+** – [Download Python](https://www.python.org/downloads/)
- **FFmpeg** – Required for video processing
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`
  - Windows: `choco install ffmpeg` or [download manually](https://ffmpeg.org/download.html)
- **Git** – For version control

### Step-by-Step Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/fedricknishant/specspectacle.git
   cd specspectacle
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment**:
   ```bash
   # macOS/Linux
   source venv/bin/activate
   
   # Windows
   venv\Scripts\activate
   ```

4. **Install development dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

5. **Install the package in editable mode**:
   ```bash
   pip install -e .
   ```

6. **Install Playwright browser**:
   ```bash
   playwright install chromium
   ```

7. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys (e.g., GOOGLE_API_KEY for TTS)
   ```

### Verify Your Setup

Run the following to verify everything is working:
```bash
specspectacle --help
```

---

## 🧪 Running Tests

SpecSpectacle uses **pytest** for testing with **pytest-cov** for coverage reporting.

### Before Running Tests

Always activate the virtual environment first:
```bash
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

### Run All Tests

```bash
pytest
```

This will:
- Run all tests in `tests/`
- Generate a coverage report
- Fail if coverage falls below 70%

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# End-to-end tests only
pytest tests/e2e/ -v

# Performance tests
pytest tests/performance/ -v
```

### Run a Single Test File

```bash
pytest tests/unit/test_schema.py -v
```

### Run Tests with Verbose Output

```bash
pytest -v --tb=short
```

### Generate Coverage Report

```bash
# Terminal report with missing lines
pytest --cov=specspectacle --cov-report=term-missing

# Generate HTML report (opens in browser)
pytest --cov=specspectacle --cov-report=html
open htmlcov/index.html  # macOS
```

### Test Markers

Tests are organized with markers:
- `@pytest.mark.unit` – Unit tests
- `@pytest.mark.integration` – Integration tests  
- `@pytest.mark.e2e` – End-to-end tests

Run tests by marker:
```bash
pytest -m "unit" -v
pytest -m "integration" -v
pytest -m "e2e" -v
```

---

## 📝 Code Style Guidelines

We use automated tools to maintain consistent code style.

### Formatting Tools

| Tool | Purpose | Config File |
|------|---------|-------------|
| **Black** | Code formatting | `pyproject.toml` |
| **isort** | Import sorting | `pyproject.toml` |
| **mypy** | Type checking | `pyproject.toml` |
| **flake8** | Linting | `pyproject.toml` |

### Format Your Code

Before committing, run:
```bash
# Format code with Black
black specspectacle/ tests/

# Sort imports with isort
isort specspectacle/ tests/

# Or format everything at once
black specspectacle/ tests/ && isort specspectacle/ tests/
```

### Type Checking

Run mypy to check type hints:
```bash
mypy specspectacle/
```

### Linting

```bash
flake8 specspectacle/ tests/
```

### Style Requirements

1. **Line length**: 100 characters max
2. **Type hints**: Add type hints to function signatures
3. **Docstrings**: Use docstrings for public functions and classes
4. **Imports**: Use absolute imports, sorted by isort

### Example Function

```python
def process_video(
    input_path: str,
    output_path: str,
    codec: str = "libx264",
    fps: int = 30,
) -> bool:
    """
    Process a video file with the specified codec and FPS.

    Args:
        input_path: Path to the input video file.
        output_path: Path for the output video file.
        codec: Video codec to use (default: libx264).
        fps: Target frames per second (default: 30).

    Returns:
        True if processing succeeded, False otherwise.

    Raises:
        FileNotFoundError: If input_path doesn't exist.
        FFmpegError: If video processing fails.
    """
    ...
```

---

## 🔄 Pull Request Process

### Before You Start

1. **Check existing issues**: Ensure the issue/feature isn't already being worked on
2. **Create an issue first**: For significant changes, open an issue to discuss

### Creating a Pull Request

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**:
   - Write clean, well-documented code
   - Add tests for new functionality
   - Update documentation if needed

3. **Ensure all checks pass**:
   ```bash
   # Activate venv first!
   source venv/bin/activate
   
   # Format code
   black specspectacle/ tests/
   isort specspectacle/ tests/
   
   # Run linting
   flake8 specspectacle/ tests/
   mypy specspectacle/
   
   # Run tests
   pytest
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add feature description"
   ```
   
   Follow [Conventional Commits](https://www.conventionalcommits.org/) format:
   - `feat:` – New feature
   - `fix:` – Bug fix
   - `docs:` – Documentation changes
   - `test:` – Adding/updating tests
   - `refactor:` – Code refactoring
   - `chore:` – Maintenance tasks

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```
   Then open a Pull Request on GitHub.

### PR Requirements

- [ ] All tests pass
- [ ] Code is formatted (Black, isort)
- [ ] No linting errors
- [ ] Type hints added where applicable
- [ ] Documentation updated if needed
- [ ] Changelog entry (for significant changes)

### Code Review

- PRs require at least one approving review
- Address all review comments
- Keep PRs focused and reasonably sized

---

## 🐛 Reporting Issues

### Bug Reports

Include:
- **Description**: Clear summary of the issue
- **Steps to reproduce**: Exact steps to trigger the bug
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Environment**: OS, Python version, SpecSpectacle version
- **Logs/Screenshots**: Any relevant output

### Feature Requests

Include:
- **Problem description**: What problem does this solve?
- **Proposed solution**: Your suggested implementation
- **Alternatives considered**: Other approaches you thought of
- **Additional context**: Use cases, examples, mockups

---

## 📚 Additional Resources

- [README.md](README.md) – Project overview
- [docs/yaml_reference.md](docs/yaml_reference.md) – YAML specification reference
- [PRD.md](PRD.md) – Product requirements

---

## 🙏 Thank You!

Your contributions help make SpecSpectacle better for everyone. We appreciate your time and effort!

If you have questions, feel free to open a GitHub Discussion or reach out to the maintainers.
