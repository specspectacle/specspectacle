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
    AssertStepModel,
    BrowserBackStepModel,
    BrowserForwardStepModel,
    CheckStepModel,
    ClickFirstVisibleStepModel,
    ClickStepModel,
    DragAndDropStepModel,
    FileUploadStepModel,
    HoverStepModel,
    NavigateStepModel,
    PressKeyStepModel,
    ScreenshotStepModel,
    ScrollStepModel,
    SelectFirstNonPlaceholderStepModel,
    SelectStepModel,
    TypeStepModel,
    UncheckStepModel,
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
    logger.info("✓ Wait completed")


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


async def press_key_action(page: Page, step: PressKeyStepModel) -> None:
    """
    Press a keyboard key or key combination.

    Args:
        page: Playwright page object
        step: PressKey step configuration
    """
    logger.info(f"Pressing key: {step.key}")
    try:
        await page.keyboard.press(step.key)
        logger.info(f"✓ Pressed key: {step.key}")

        if step.pause > 0:
            await asyncio.sleep(step.pause)
    except Exception as e:
        logger.error(f"press_key failed for '{step.key}': {e}")
        raise ActionError(
            action="press_key",
            reason=str(e),
            page_url=page.url,
        )


async def browser_back_action(page: Page, step: BrowserBackStepModel) -> None:
    """
    Navigate the browser back in history.

    Args:
        page: Playwright page object
        step: BrowserBack step configuration
    """
    logger.info("Navigating back")
    try:
        await page.go_back(timeout=step.timeout)
        logger.info("✓ Navigated back")

        if step.pause > 0:
            await asyncio.sleep(step.pause)
    except PlaywrightTimeoutError:
        raise NavigationError(
            url="(back)",
            page_url=page.url,
            reason=f"go_back timed out after {step.timeout}ms",
        )
    except Exception as e:
        raise ActionError(
            action="browser_back",
            reason=str(e),
            page_url=page.url,
        )


async def browser_forward_action(page: Page, step: BrowserForwardStepModel) -> None:
    """
    Navigate the browser forward in history.

    Args:
        page: Playwright page object
        step: BrowserForward step configuration
    """
    logger.info("Navigating forward")
    try:
        await page.go_forward(timeout=step.timeout)
        logger.info("✓ Navigated forward")

        if step.pause > 0:
            await asyncio.sleep(step.pause)
    except PlaywrightTimeoutError:
        raise NavigationError(
            url="(forward)",
            page_url=page.url,
            reason=f"go_forward timed out after {step.timeout}ms",
        )
    except Exception as e:
        raise ActionError(
            action="browser_forward",
            reason=str(e),
            page_url=page.url,
        )


async def check_action(page: Page, step: CheckStepModel) -> None:
    """
    Check a checkbox element.

    Args:
        page: Playwright page object
        step: Check step configuration
    """
    logger.info(f"Checking: {step.selector}")
    try:
        await page.wait_for_selector(step.selector, state="visible", timeout=10000)
        await page.check(step.selector)
        logger.info(f"✓ Checked {step.selector}")

        if step.pause > 0:
            await asyncio.sleep(step.pause)
    except PlaywrightTimeoutError:
        raise SelectorTimeoutError(
            selector=step.selector,
            timeout_ms=10000,
            page_url=page.url,
            action="check",
        )
    except Exception as e:
        raise ActionError(
            action="check",
            reason=str(e),
            selector=step.selector,
            page_url=page.url,
        )


async def uncheck_action(page: Page, step: UncheckStepModel) -> None:
    """
    Uncheck a checkbox element.

    Args:
        page: Playwright page object
        step: Uncheck step configuration
    """
    logger.info(f"Unchecking: {step.selector}")
    try:
        await page.wait_for_selector(step.selector, state="visible", timeout=10000)
        await page.uncheck(step.selector)
        logger.info(f"✓ Unchecked {step.selector}")

        if step.pause > 0:
            await asyncio.sleep(step.pause)
    except PlaywrightTimeoutError:
        raise SelectorTimeoutError(
            selector=step.selector,
            timeout_ms=10000,
            page_url=page.url,
            action="uncheck",
        )
    except Exception as e:
        raise ActionError(
            action="uncheck",
            reason=str(e),
            selector=step.selector,
            page_url=page.url,
        )


async def assert_action(page: Page, step: AssertStepModel) -> None:
    """
    Assert element visibility and/or text content.

    Raises ActionError if the assertion fails.

    Args:
        page: Playwright page object
        step: Assert step configuration
    """
    logger.info(f"Asserting: {step.selector}")
    try:
        locator = page.locator(step.selector)

        if step.visible is not None:
            expected_state = "visible" if step.visible else "hidden"
            await locator.wait_for(state=expected_state, timeout=step.timeout)
            logger.info(f"  ✓ Element is {expected_state}: {step.selector}")

        if step.text is not None:
            # Ensure the element exists first
            await locator.wait_for(state="attached", timeout=step.timeout)
            actual_text = await locator.text_content()
            if step.text not in (actual_text or ""):
                raise ActionError(
                    action="assert",
                    reason=f"Expected text '{step.text}' not found in '{actual_text}'",
                    selector=step.selector,
                    page_url=page.url,
                )
            logger.info(f"  ✓ Text matched: '{step.text}'")

        logger.info(f"✓ Assert passed for {step.selector}")

        if step.pause > 0:
            await asyncio.sleep(step.pause)
    except ActionError:
        raise
    except PlaywrightTimeoutError:
        raise SelectorTimeoutError(
            selector=step.selector,
            timeout_ms=step.timeout,
            page_url=page.url,
            action="assert",
        )
    except Exception as e:
        raise ActionError(
            action="assert",
            reason=str(e),
            selector=step.selector,
            page_url=page.url,
        )


async def click_first_visible_action(page: Page, step: ClickFirstVisibleStepModel) -> None:
    """
    Click the first visible element matching the selector.

    Iterates over all matching locators and clicks the first one that is
    currently visible, skipping hidden or detached elements.

    Args:
        page: Playwright page object
        step: ClickFirstVisible step configuration
    """
    logger.info(f"Clicking first visible: {step.selector}")
    try:
        await page.wait_for_selector(step.selector, state="attached", timeout=10000)
        locators = await page.locator(step.selector).all()

        for locator in locators:
            if await locator.is_visible():
                await locator.click()
                logger.info(f"✓ Clicked first visible {step.selector}")
                if step.pause > 0:
                    await asyncio.sleep(step.pause)
                return

        raise ElementNotFoundError(
            selector=step.selector,
            page_url=page.url,
            action="click_first_visible",
        )
    except (ActionError, ElementNotFoundError):
        raise
    except PlaywrightTimeoutError:
        raise SelectorTimeoutError(
            selector=step.selector,
            timeout_ms=10000,
            page_url=page.url,
            action="click_first_visible",
        )
    except Exception as e:
        raise ActionError(
            action="click_first_visible",
            reason=str(e),
            selector=step.selector,
            page_url=page.url,
        )


async def select_first_non_placeholder_action(
    page: Page, step: SelectFirstNonPlaceholderStepModel
) -> None:
    """
    Select the first non-placeholder option from a <select> element.

    A "placeholder" option is one with an empty value attribute (value='' or value='0'
    treated as placeholder, or options with empty visible text).

    Args:
        page: Playwright page object
        step: SelectFirstNonPlaceholder step configuration
    """
    logger.info(f"Selecting first non-placeholder from: {step.selector}")
    try:
        await page.wait_for_selector(step.selector, state="visible", timeout=10000)

        # Find the first option with a non-empty value
        first_value = await page.evaluate(
            """
            (selector) => {
                const select = document.querySelector(selector);
                if (!select) return null;
                for (const option of select.options) {
                    if (option.value !== '' && option.value !== null) {
                        return option.value;
                    }
                }
                return null;
            }
            """,
            step.selector,
        )

        if first_value is None:
            raise ElementNotFoundError(
                selector=step.selector,
                page_url=page.url,
                action="select_first_non_placeholder",
            )

        await page.select_option(step.selector, value=first_value)
        logger.info(f"✓ Selected first non-placeholder value '{first_value}' from {step.selector}")

        if step.pause > 0:
            await asyncio.sleep(step.pause)
    except (ActionError, ElementNotFoundError):
        raise
    except PlaywrightTimeoutError:
        raise SelectorTimeoutError(
            selector=step.selector,
            timeout_ms=10000,
            page_url=page.url,
            action="select_first_non_placeholder",
        )
    except Exception as e:
        raise ActionError(
            action="select_first_non_placeholder",
            reason=str(e),
            selector=step.selector,
            page_url=page.url,
        )


async def file_upload_action(page: Page, step: FileUploadStepModel) -> None:
    """
    Upload one or more files via a file input element.

    Args:
        page: Playwright page object
        step: FileUpload step configuration
    """
    files_to_upload = [step.file] if step.file else step.files
    logger.info(f"Uploading {len(files_to_upload)} file(s) to: {step.selector}")
    try:
        await page.wait_for_selector(step.selector, state="attached", timeout=10000)
        await page.locator(step.selector).set_input_files(files_to_upload)
        logger.info(f"✓ Uploaded file(s) to {step.selector}")

        if step.pause > 0:
            await asyncio.sleep(step.pause)
    except PlaywrightTimeoutError:
        raise SelectorTimeoutError(
            selector=step.selector,
            timeout_ms=10000,
            page_url=page.url,
            action="file_upload",
        )
    except Exception as e:
        raise ActionError(
            action="file_upload",
            reason=str(e),
            selector=step.selector,
            page_url=page.url,
        )


async def drag_and_drop_action(page: Page, step: DragAndDropStepModel) -> None:
    """
    Drag an element from source selector to target selector.

    Args:
        page: Playwright page object
        step: DragAndDrop step configuration
    """
    logger.info(f"Dragging {step.source} → {step.target}")
    try:
        await page.wait_for_selector(step.source, state="visible", timeout=10000)
        await page.wait_for_selector(step.target, state="visible", timeout=10000)
        await page.drag_and_drop(step.source, step.target)
        logger.info(f"✓ Dragged {step.source} → {step.target}")

        if step.pause > 0:
            await asyncio.sleep(step.pause)
    except PlaywrightTimeoutError:
        raise SelectorTimeoutError(
            selector=f"{step.source} → {step.target}",
            timeout_ms=10000,
            page_url=page.url,
            action="drag_and_drop",
        )
    except Exception as e:
        raise ActionError(
            action="drag_and_drop",
            reason=str(e),
            selector=step.source,
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
    "press_key": press_key_action,
    "browser_back": browser_back_action,
    "browser_forward": browser_forward_action,
    "check": check_action,
    "uncheck": uncheck_action,
    "assert": assert_action,
    "click_first_visible": click_first_visible_action,
    "select_first_non_placeholder": select_first_non_placeholder_action,
    "file_upload": file_upload_action,
    "drag_and_drop": drag_and_drop_action,
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
