"""
Custom exceptions for the executor module.

Provides a hierarchy of exceptions with rich context for debugging
and user-friendly error messages.
"""

from typing import Optional


class ExecutorError(Exception):
    """
    Base exception for all executor errors.

    All executor-specific exceptions inherit from this class,
    making it easy to catch any executor error.
    """

    def __init__(self, message: str, page_url: Optional[str] = None):
        self.message = message
        self.page_url = page_url
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message with context."""
        parts = [self.message]
        if self.page_url:
            parts.append(f"Page URL: {self.page_url}")
        suggestion = self.get_suggestion()
        if suggestion:
            parts.append(f"💡 Suggestion: {suggestion}")
        return " | ".join(parts)

    def get_suggestion(self) -> Optional[str]:
        """Get actionable suggestion for fixing this error."""
        return None


class SelectorTimeoutError(ExecutorError):
    """
    Raised when waiting for a selector times out.

    Attributes:
        selector: The CSS/XPath selector that timed out
        timeout_ms: The timeout value in milliseconds
        page_url: The URL of the page where the timeout occurred
    """

    def __init__(
        self,
        selector: str,
        timeout_ms: int,
        page_url: Optional[str] = None,
        action: Optional[str] = None,
    ):
        self.selector = selector
        self.timeout_ms = timeout_ms
        self.action = action
        message = f"Timeout ({timeout_ms}ms) waiting for selector: '{selector}'"
        if action:
            message = f"[{action}] {message}"
        super().__init__(message, page_url)

    def get_suggestion(self) -> Optional[str]:
        """Get actionable suggestion for fixing this error."""
        return (
            "Check if the selector is correct. Try using browser DevTools (F12) to "
            "test the selector. Consider increasing the timeout or adding a wait step before this action."
        )


class NavigationError(ExecutorError):
    """
    Raised when navigation to a URL fails.

    Attributes:
        url: The URL that failed to load
        page_url: The URL of the page before navigation attempt
        reason: Optional reason for the failure
    """

    def __init__(
        self,
        url: str,
        page_url: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        self.url = url
        self.reason = reason
        message = f"Navigation failed for URL: '{url}'"
        if reason:
            message += f" - {reason}"
        super().__init__(message, page_url)

    def get_suggestion(self) -> Optional[str]:
        """Get actionable suggestion for fixing this error."""
        return (
            "Verify the URL is accessible in your browser. Check your internet connection. "
            "If behind a proxy or firewall, ensure the URL is whitelisted."
        )


class ElementNotFoundError(ExecutorError):
    """
    Raised when an element is not found on the page.

    This differs from SelectorTimeoutError in that it indicates
    the element doesn't exist at all, rather than timing out.

    Attributes:
        selector: The CSS/XPath selector that wasn't found
        page_url: The URL of the page where the element wasn't found
    """

    def __init__(
        self,
        selector: str,
        page_url: Optional[str] = None,
        action: Optional[str] = None,
    ):
        self.selector = selector
        self.action = action
        message = f"Element not found: '{selector}'"
        if action:
            message = f"[{action}] {message}"
        super().__init__(message, page_url)

    def get_suggestion(self) -> Optional[str]:
        """Get actionable suggestion for fixing this error."""
        return (
            "The element might not exist on the page. Use browser DevTools to verify the selector. "
            "The page structure might have changed, or you may need to wait for dynamic content to load."
        )


class ActionError(ExecutorError):
    """
    Raised when an action fails for reasons other than timeout or not found.

    Attributes:
        action: The action type that failed
        selector: The selector involved (if any)
        page_url: The URL of the page where the action failed
        reason: The reason for the failure
    """

    def __init__(
        self,
        action: str,
        reason: str,
        selector: Optional[str] = None,
        page_url: Optional[str] = None,
    ):
        self.action = action
        self.selector = selector
        self.reason = reason
        message = f"[{action}] Action failed: {reason}"
        if selector:
            message += f" (selector: '{selector}')"
        super().__init__(message, page_url)


__all__ = [
    "ExecutorError",
    "SelectorTimeoutError",
    "NavigationError",
    "ElementNotFoundError",
    "ActionError",
]
