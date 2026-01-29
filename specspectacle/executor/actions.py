"""
Action handlers for executing YAML spec steps using Playwright.

Each action handler is an async function that takes a Playwright Page object
and a typed step model from the schema.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from specspectacle.executor.errors import (
    ActionError,
    ElementNotFoundError,
    NavigationError,
    SelectorTimeoutError,
)
from specspectacle.parser.schema import (
    ClickStepModel,
    HoverStepModel,
    NavigateStepModel,
    ScreenshotStepModel,
    ScrollStepModel,
    SelectStepModel,
    TypeStepModel,
    WaitForSelectorStepModel,
    WaitStepModel,
)

logger = logging.getLogger(__name__)


async def navigate_action(page: Page, step: NavigateStepModel) -> None:
    """
    Navigate to a URL.

    Args:
        page: Playwright page object
        step: Navigate step configuration
    """
    logger.info(f"Navigating to: {step.url}")
    current_url = page.url if page.url != "about:blank" else None
    try:
        await page.goto(step.url, wait_until="networkidle", timeout=30000)
        logger.info(f"✓ Navigated to {step.url}")

        if step.pause > 0:
            await asyncio.sleep(step.pause)
    except PlaywrightTimeoutError:
        logger.error(f"Navigation timeout for {step.url}")
        raise NavigationError(
            url=step.url,
            page_url=current_url,
            reason="Navigation timed out after 30 seconds",
        )
    except Exception as e:
        logger.error(f"Navigation failed for {step.url}: {e}")
        raise NavigationError(
            url=step.url,
            page_url=current_url,
            reason=str(e),
        )


async def wait_action(page: Page, step: WaitStepModel) -> None:
    """
    Wait for a specified duration.

    Args:
        page: Playwright page object
        step: Wait step configuration
    """
    logger.info(f"Waiting for {step.duration} seconds...")
    await asyncio.sleep(step.duration)
    logger.info(f"✓ Wait completed")


async def click_action(page: Page, step: ClickStepModel) -> None:
    """
    Click an element.

    Args:
        page: Playwright page object
        step: Click step configuration
    """
    logger.info(f"Clicking: {step.selector}")
    try:
        # Wait for element to be visible before clicking
        await page.wait_for_selector(step.selector, state="visible", timeout=10000)
        await page.click(step.selector)
        logger.info(f"✓ Clicked {step.selector}")

        if step.pause > 0:
            await asyncio.sleep(step.pause)
    except PlaywrightTimeoutError:
        logger.error(f"Timeout waiting for selector '{step.selector}' on page: {page.url}")
        raise SelectorTimeoutError(
            selector=step.selector,
            timeout_ms=10000,
            page_url=page.url,
            action="click",
        )
    except Exception as e:
        logger.error(f"Click failed for '{step.selector}': {e}")
        raise ActionError(
            action="click",
            reason=str(e),
            selector=step.selector,
            page_url=page.url,
        )


async def type_action(page: Page, step: TypeStepModel) -> None:
    """
    Type text into a field.

    Args:
        page: Playwright page object
        step: Type step configuration
    """
    logger.info(f"Typing into: {step.selector}")
    try:
        # Wait for input element to be visible
        await page.wait_for_selector(step.selector, state="visible", timeout=10000)

        # Clear existing text first
        await page.fill(step.selector, "")

        # Type with delay if specified
        if step.delay > 0:
            await page.type(step.selector, step.text, delay=step.delay)
        else:
            await page.fill(step.selector, step.text)

        logger.info(f"✓ Typed into {step.selector}")

        if step.pause > 0:
            await asyncio.sleep(step.pause)
    except PlaywrightTimeoutError:
        logger.error(f"Timeout waiting for selector '{step.selector}' on page: {page.url}")
        raise SelectorTimeoutError(
            selector=step.selector,
            timeout_ms=10000,
            page_url=page.url,
            action="type",
        )
    except Exception as e:
        logger.error(f"Type failed for '{step.selector}': {e}")
        raise ActionError(
            action="type",
            reason=str(e),
            selector=step.selector,
            page_url=page.url,
        )


async def wait_for_selector_action(page: Page, step: WaitForSelectorStepModel) -> None:
    """
    Wait for an element to appear.

    Args:
        page: Playwright page object
        step: Wait for selector step configuration
    """
    logger.info(f"Waiting for selector: {step.selector}")
    try:
        await page.wait_for_selector(step.selector, timeout=step.timeout)
        logger.info(f"✓ Element appeared: {step.selector}")

        if step.pause > 0:
            await asyncio.sleep(step.pause)
    except PlaywrightTimeoutError:
        logger.error(
            f"Timeout ({step.timeout}ms) waiting for selector '{step.selector}' on page: {page.url}"
        )
        raise SelectorTimeoutError(
            selector=step.selector,
            timeout_ms=step.timeout,
            page_url=page.url,
            action="wait_for_selector",
        )
    except Exception as e:
        logger.error(f"Wait for selector failed for '{step.selector}': {e}")
        raise ActionError(
            action="wait_for_selector",
            reason=str(e),
            selector=step.selector,
            page_url=page.url,
        )


async def hover_action(page: Page, step: HoverStepModel) -> None:
    """
    Hover over an element.

    Args:
        page: Playwright page object
        step: Hover step configuration
    """
    logger.info(f"Hovering over: {step.selector}")
    try:
        await page.wait_for_selector(step.selector, state="visible", timeout=10000)
        await page.hover(step.selector)
        logger.info(f"✓ Hovered over {step.selector}")

        if step.pause > 0:
            await asyncio.sleep(step.pause)
    except PlaywrightTimeoutError:
        logger.error(f"Timeout waiting for selector '{step.selector}' on page: {page.url}")
        raise SelectorTimeoutError(
            selector=step.selector,
            timeout_ms=10000,
            page_url=page.url,
            action="hover",
        )
    except Exception as e:
        logger.error(f"Hover failed for '{step.selector}': {e}")
        raise ActionError(
            action="hover",
            reason=str(e),
            selector=step.selector,
            page_url=page.url,
        )


async def scroll_action(page: Page, step: ScrollStepModel) -> None:
    """
    Scroll the page.

    Supports two modes:
    1. Direction mode: scroll by a fixed amount (up/down/left/right)
    2. Selector mode: scroll to bring an element into view

    Args:
        page: Playwright page object
        step: Scroll step configuration
    """
    if step.direction:
        logger.info(f"Scrolling {step.direction}")

        # Map direction to pixel amounts
        scroll_amounts = {
            "down": (0, 500),
            "up": (0, -500),
            "right": (500, 0),
            "left": (-500, 0),
        }

        x, y = scroll_amounts[step.direction]
        await page.evaluate(f"window.scrollBy({x}, {y})")
        logger.info(f"✓ Scrolled {step.direction}")

    elif step.selector:
        logger.info(f"Scrolling to element: {step.selector}")
        try:
            await page.wait_for_selector(step.selector, timeout=10000)
            await page.locator(step.selector).scroll_into_view_if_needed()
            logger.info(f"✓ Scrolled to {step.selector}")
        except PlaywrightTimeoutError:
            logger.error(f"Timeout waiting for selector '{step.selector}' on page: {page.url}")
            raise SelectorTimeoutError(
                selector=step.selector,
                timeout_ms=10000,
                page_url=page.url,
                action="scroll",
            )
        except Exception as e:
            logger.error(f"Scroll to selector failed for '{step.selector}': {e}")
            raise ActionError(
                action="scroll",
                reason=str(e),
                selector=step.selector,
                page_url=page.url,
            )

    if step.pause > 0:
        await asyncio.sleep(step.pause)


async def screenshot_action(page: Page, step: ScreenshotStepModel) -> None:
    """
    Capture a screenshot.

    Args:
        page: Playwright page object
        step: Screenshot step configuration
    """
    # Determine output path
    if step.path:
        output_path = Path(step.path)
    else:
        # Default to output/screenshots/{timestamp}.png
        screenshots_dir = Path("output/screenshots")
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_path = screenshots_dir / f"screenshot_{timestamp}.png"

    logger.info(f"Taking screenshot: {output_path}")

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    await page.screenshot(path=str(output_path), full_page=False)
    logger.info(f"✓ Screenshot saved to {output_path}")

    if step.pause > 0:
        await asyncio.sleep(step.pause)


async def select_action(page: Page, step: SelectStepModel) -> None:
    """
    Select an option from a dropdown.

    Args:
        page: Playwright page object
        step: Select step configuration
    """
    logger.info(f"Selecting '{step.value}' from: {step.selector}")
    try:
        await page.wait_for_selector(step.selector, state="visible", timeout=10000)
        await page.select_option(step.selector, value=step.value)
        logger.info(f"✓ Selected '{step.value}' from {step.selector}")

        if step.pause > 0:
            await asyncio.sleep(step.pause)
    except PlaywrightTimeoutError:
        logger.error(f"Timeout waiting for selector '{step.selector}' on page: {page.url}")
        raise SelectorTimeoutError(
            selector=step.selector,
            timeout_ms=10000,
            page_url=page.url,
            action="select",
        )
    except Exception as e:
        logger.error(f"Select failed for '{step.selector}': {e}")
        raise ActionError(
            action="select",
            reason=str(e),
            selector=step.selector,
            page_url=page.url,
        )


ACTION_HANDLERS = {
    "navigate": navigate_action,
    "wait": wait_action,
    "click": click_action,
    "type": type_action,
    "wait_for_selector": wait_for_selector_action,
    "hover": hover_action,
    "scroll": scroll_action,
    "screenshot": screenshot_action,
    "select": select_action,
}


def get_action_handler(action_name: str):
    """
    Get the action handler function for a given action name.

    Args:
        action_name: Name of the action (e.g., "click", "type")

    Returns:
        The corresponding action handler function

    Raises:
        KeyError: If action name is not recognized
    """
    return ACTION_HANDLERS[action_name]
