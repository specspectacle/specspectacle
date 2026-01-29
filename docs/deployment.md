# Deployment Guide

This guide describes how to build, test, and release the `specspectacle` package to PyPI.

## Prerequisites

Ensure you have the following installed:
- `pip`
- `twine`
- `build`

You can install them via:
```bash
pip install twine build
```

## 1. Build the Package

Before uploading, you must build the "source distribution" and the "wheel".

```bash
# Make sure your virtual environment is active
source venv/bin/activate

# Build the package
python setup.py sdist bdist_wheel
```

This will create a `dist/` directory containing:
- `specspectacle-x.y.z.tar.gz` (Source distribution)
- `specspectacle-x.y.z-py3-none-any.whl` (Wheel)

## 2. Test Locally

It is highly recommended to test the built package in a clean environment before uploading.

```bash
# Create a temporary environment
python3 -m venv test_env
source test_env/bin/activate

# Install the newly built wheel
pip install dist/specspectacle-*.whl

# Verify it runs
specspectacle --help

# Deactivate and cleanup
deactivate
rm -rf test_env
```

## 3. Upload to TestPyPI

TestPyPI is a separate instance of PyPI for testing and validation.

### Step 3a: Get Credentials
1. Go to [TestPyPI](https://test.pypi.org/).
2. Register for an account if you don't have one.
3. Verify your email!
4. Go to **Account Settings** -> **API Tokens**.
5. Create a new token. Scope it to "Entire account" (for your first upload).
6. **Copy the token** (it starts with `pypi-`).

### Step 3b: Upload
Use `twine` to upload the artifacts.

```bash
twine upload --repository testpypi dist/*
```
When prompted for:
- **Username**: Enter `__token__`
- **Password**: Enter your API token (including the `pypi-` prefix).

*Pro Tip: You can set `TWINE_USERNAME=__token__` and `TWINE_PASSWORD=pypi-...` environment variables to skip the interactive prompt.*

## 4. Verify TestPyPI Installation

Try installing from TestPyPI to make sure everything looks right.

```bash
# Create a fresh temp env
python3 -m venv test_pypi_env
source test_pypi_env/bin/activate

# Install from TestPyPI (extra-index-url is needed for dependencies that are on main PyPI)
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ specspectacle

# Verify
specspectacle --version
```

## 5. Upload to Production PyPI

Once you are confident, repeat the process for the real PyPI.

1. Go to [PyPI.org](https://pypi.org/).
2. Login/Register and generate an API Token.
3. Upload:
   ```bash
   twine upload dist/*
   ```
   (Note: `twine upload` defaults to the production PyPI repository).
4. Users can now install via `pip install specspectacle`.
