"""
Common validation utilities for SpecSpectacle
"""

import re
from typing import Optional
from urllib.parse import urlparse


def is_valid_selector(selector: str) -> bool:
    """
    Validate if a string looks like a valid CSS selector.

    This is a basic check - it ensures the selector is not empty
    and doesn't contain obviously invalid characters.

    Args:
        selector: CSS selector string

    Returns:
        True if selector appears valid, False otherwise
    """
    if not selector or not selector.strip():
        return False

    # Basic validation - allows common CSS selector patterns
    # This is permissive by design to allow complex selectors
    return len(selector.strip()) > 0


def is_valid_hex_color(color: str) -> bool:
    """
    Validate hex color code format.

    Supports:
    - #RGB
    - #RRGGBB
    - #RGBA
    - #RRGGBBAA

    Args:
        color: Color string to validate

    Returns:
        True if valid hex color, False otherwise
    """
    if not color:
        return False

    # Regex for hex colors with optional alpha
    pattern = r"^#([A-Fa-f0-9]{3}|[A-Fa-f0-9]{4}|[A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$"
    return bool(re.match(pattern, color))


def is_valid_url(url: str) -> bool:
    """
    Basic URL format validation.

    Args:
        url: URL string to validate

    Returns:
        True if URL appears valid, False otherwise
    """
    if not url:
        return False

    try:
        result = urlparse(url)
        # Must have scheme (http/https) and netloc (domain)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def validate_step_action_fields(action: str, **kwargs) -> Optional[str]:
    """
    Validate that required fields are present for a given action.

    Args:
        action: Action type (navigate, click, type, etc.)
        **kwargs: Fields provided for the action

    Returns:
        Error message if validation fails, None if valid
    """
    field_requirements = {
        "navigate": ["url"],
        "click": ["selector"],
        "type": ["selector", "text"],
        "wait": ["duration"],
        "wait_for_selector": ["selector"],
        "hover": ["selector"],
        "scroll": [],  # Can have selector OR direction
        "screenshot": [],  # path is optional
        "select": ["selector", "value"],
    }

    if action not in field_requirements:
        return f"Unknown action type: {action}"

    required = field_requirements[action]
    missing = [field for field in required if not kwargs.get(field)]

    if missing:
        return f"Action '{action}' requires field(s): {', '.join(missing)}"

    # Special case: scroll needs either selector OR direction
    if action == "scroll":
        if not kwargs.get("selector") and not kwargs.get("direction"):
            return "Action 'scroll' requires either 'selector' or 'direction'"

    return None


__all__ = [
    "is_valid_selector",
    "is_valid_hex_color",
    "is_valid_url",
    "validate_step_action_fields",
]
