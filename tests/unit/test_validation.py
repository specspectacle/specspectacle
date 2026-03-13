"""Unit tests for validation utilities."""


from specspectacle.utils.validation import (
    is_valid_hex_color,
    is_valid_selector,
    is_valid_url,
    validate_step_action_fields,
)


class TestIsValidSelector:
    """Test CSS selector validation."""

    def test_valid_selectors(self):
        """Test various valid CSS selectors."""
        assert is_valid_selector("#my-id")
        assert is_valid_selector(".my-class")
        assert is_valid_selector("button")
        assert is_valid_selector('[data-testid="login"]')
        assert is_valid_selector("div.container > button.primary")

    def test_invalid_selectors(self):
        """Test invalid selectors."""
        assert not is_valid_selector("")
        assert not is_valid_selector("   ")


class TestIsValidHexColor:
    """Test hex color validation."""

    def test_valid_hex_colors(self):
        """Test various valid hex color formats."""
        assert is_valid_hex_color("#000")
        assert is_valid_hex_color("#FFF")
        assert is_valid_hex_color("#000000")
        assert is_valid_hex_color("#FFFFFF")
        assert is_valid_hex_color("#0000")  # RGBA short
        assert is_valid_hex_color("#00000000")  # RGBA long
        assert is_valid_hex_color("#FF00FFAA")

    def test_invalid_hex_colors(self):
        """Test invalid hex color formats."""
        assert not is_valid_hex_color("")
        assert not is_valid_hex_color("#")
        assert not is_valid_hex_color("#GG0000")  # Invalid hex chars
        assert not is_valid_hex_color("FF0000")  # Missing #
        assert not is_valid_hex_color("#00")  # Too short


class TestIsValidURL:
    """Test URL validation."""

    def test_valid_urls(self):
        """Test various valid URLs."""
        assert is_valid_url("https://example.com")
        assert is_valid_url("http://example.com")
        assert is_valid_url("https://example.com/path")
        assert is_valid_url("https://example.com:8080/path?query=value")

    def test_invalid_urls(self):
        """Test invalid URLs."""
        assert not is_valid_url("")
        assert not is_valid_url("not-a-url")
        assert not is_valid_url("ftp://example.com")  # Only http/https
        assert not is_valid_url("//example.com")  # Missing scheme


class TestValidateStepActionFields:
    """Test step action field validation."""

    def test_navigate_action(self):
        """Test navigate action validation."""
        # Valid
        assert validate_step_action_fields("navigate", url="https://example.com") is None

        # Missing url
        error = validate_step_action_fields("navigate")
        assert error is not None
        assert "url" in error

    def test_click_action(self):
        """Test click action validation."""
        # Valid
        assert validate_step_action_fields("click", selector="#button") is None

        # Missing selector
        error = validate_step_action_fields("click")
        assert error is not None
        assert "selector" in error

    def test_type_action(self):
        """Test type action validation."""
        # Valid
        assert validate_step_action_fields("type", selector="#input", text="hello") is None

        # Missing selector or text
        error = validate_step_action_fields("type", selector="#input")
        assert error is not None
        assert "text" in error

    def test_scroll_action(self):
        """Test scroll action validation."""
        # Valid with direction
        assert validate_step_action_fields("scroll", direction="down") is None

        # Valid with selector
        assert validate_step_action_fields("scroll", selector="#footer") is None

        # Missing both
        error = validate_step_action_fields("scroll")
        assert error is not None
        assert "selector" in error or "direction" in error

    def test_unknown_action(self):
        """Test unknown action type."""
        error = validate_step_action_fields("unknown_action")
        assert error is not None
        assert "Unknown" in error
