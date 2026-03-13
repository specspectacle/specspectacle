"""
Integration tests for the executor module.

Tests browser actions, timeline tracking, and error handling.
Requires Playwright and Chromium to be installed.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from specspectacle.executor.actions import (
    assert_action,
    browser_back_action,
    browser_forward_action,
    check_action,
    click_action,
    click_first_visible_action,
    drag_and_drop_action,
    file_upload_action,
    hover_action,
    navigate_action,
    press_key_action,
    screenshot_action,
    scroll_action,
    select_action,
    select_first_non_placeholder_action,
    type_action,
    uncheck_action,
    wait_action,
    wait_for_selector_action,
)
from specspectacle.executor.errors import (
    ActionError,
    ElementNotFoundError,
    NavigationError,
    SelectorTimeoutError,
)
from specspectacle.executor.timeline import Timeline, TimelineEvent
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


class TestTimelineEvent:
    """Tests for TimelineEvent data class."""

    def test_create_event(self):
        """Test creating a timeline event."""
        event = TimelineEvent(
            step_name="Navigate to home",
            action="navigate",
            start_time=1000.0,
            end_time=1002.5,
            duration=2.5,
            flow_name="Login Flow",
            flow_index=1,
            step_index=1,
            success=True,
            error_message=None,
        )

        assert event.step_name == "Navigate to home"
        assert event.action == "navigate"
        assert event.duration == 2.5
        assert event.success is True

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = TimelineEvent(
            step_name="Click button",
            action="click",
            start_time=1000.0,
            end_time=1001.0,
            duration=1.0,
            flow_name="Test Flow",
            flow_index=1,
            step_index=2,
            success=False,
            error_message="Element not found",
        )

        data = event.to_dict()
        assert data["step_name"] == "Click button"
        assert data["action"] == "click"
        assert data["success"] is False
        assert data["error_message"] == "Element not found"


class TestTimeline:
    """Tests for Timeline class."""

    def test_create_timeline(self):
        """Test creating a timeline."""
        timeline = Timeline(spec_name="Test Spec")
        assert timeline.spec_name == "Test Spec"
        assert len(timeline.events) == 0

    def test_add_event(self):
        """Test adding events to timeline."""
        timeline = Timeline(spec_name="Test Spec")
        event = TimelineEvent(
            step_name="Step 1",
            action="navigate",
            start_time=1000.0,
            end_time=1002.0,
            duration=2.0,
            flow_name="Flow 1",
            flow_index=1,
            step_index=1,
        )
        timeline.add_event(event)

        assert len(timeline.events) == 1
        assert timeline.events[0].step_name == "Step 1"

    def test_record_event(self):
        """Test recording a new event."""
        timeline = Timeline(spec_name="Test Spec")
        event = timeline.record_event(
            step_name="Step 1",
            action="click",
            flow_name="Flow 1",
            flow_index=1,
            step_index=1,
            start_time=1000.0,
            end_time=1001.5,
        )

        assert len(timeline.events) == 1
        assert event.duration == 1.5
        assert event.success is True

    def test_total_duration(self):
        """Test calculating total duration."""
        timeline = Timeline(spec_name="Test Spec")
        timeline.start()
        timeline.record_event(
            step_name="Step 1",
            action="navigate",
            flow_name="Flow 1",
            flow_index=1,
            step_index=1,
            start_time=1000.0,
            end_time=1002.0,
        )
        timeline.record_event(
            step_name="Step 2",
            action="click",
            flow_name="Flow 1",
            flow_index=1,
            step_index=2,
            start_time=1002.0,
            end_time=1003.0,
        )
        timeline.complete()

        # Total duration should be calculated from started_at to completed_at
        assert timeline.total_duration >= 0

    def test_successful_and_failed_events(self):
        """Test filtering successful and failed events."""
        timeline = Timeline(spec_name="Test Spec")
        timeline.record_event(
            step_name="Success Step",
            action="click",
            flow_name="Flow 1",
            flow_index=1,
            step_index=1,
            start_time=1000.0,
            end_time=1001.0,
            success=True,
        )
        timeline.record_event(
            step_name="Failed Step",
            action="type",
            flow_name="Flow 1",
            flow_index=1,
            step_index=2,
            start_time=1001.0,
            end_time=1002.0,
            success=False,
            error_message="Timeout",
        )

        assert len(timeline.successful_events) == 1
        assert len(timeline.failed_events) == 1
        assert timeline.successful_events[0].step_name == "Success Step"
        assert timeline.failed_events[0].step_name == "Failed Step"

    def test_to_dict(self):
        """Test converting timeline to dictionary."""
        timeline = Timeline(spec_name="Test Spec")
        timeline.start()
        timeline.record_event(
            step_name="Step 1",
            action="navigate",
            flow_name="Flow 1",
            flow_index=1,
            step_index=1,
            start_time=1000.0,
            end_time=1002.0,
        )
        timeline.complete()

        data = timeline.to_dict()
        assert data["spec_name"] == "Test Spec"
        assert data["total_events"] == 1
        assert data["successful_events"] == 1
        assert data["failed_events"] == 0
        assert len(data["events"]) == 1

    def test_save_and_load(self):
        """Test saving and loading timeline from JSON."""
        timeline = Timeline(spec_name="Test Spec")
        timeline.start()
        timeline.record_event(
            step_name="Step 1",
            action="navigate",
            flow_name="Flow 1",
            flow_index=1,
            step_index=1,
            start_time=1000.0,
            end_time=1002.0,
        )
        timeline.complete()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            timeline_path = Path(f.name)

        try:
            timeline.save(timeline_path)

            # Load and verify
            loaded = Timeline.load(timeline_path)
            assert loaded.spec_name == "Test Spec"
            assert len(loaded.events) == 1
            assert loaded.events[0].step_name == "Step 1"
        finally:
            timeline_path.unlink(missing_ok=True)


class TestCustomExceptions:
    """Tests for custom exception classes."""

    def test_selector_timeout_error(self):
        """Test SelectorTimeoutError with context."""
        error = SelectorTimeoutError(
            selector="#submit-btn",
            timeout_ms=10000,
            page_url="https://example.com/login",
            action="click",
        )

        assert error.selector == "#submit-btn"
        assert error.timeout_ms == 10000
        assert "click" in str(error)
        assert "#submit-btn" in str(error)

    def test_navigation_error(self):
        """Test NavigationError with context."""
        error = NavigationError(
            url="https://invalid-domain.test",
            page_url="https://example.com",
            reason="net::ERR_NAME_NOT_RESOLVED",
        )

        assert error.url == "https://invalid-domain.test"
        assert "net::ERR_NAME_NOT_RESOLVED" in str(error)

    def test_element_not_found_error(self):
        """Test ElementNotFoundError with context."""
        error = ElementNotFoundError(
            selector=".missing-class",
            page_url="https://example.com",
            action="hover",
        )

        assert error.selector == ".missing-class"
        assert "hover" in str(error)

    def test_action_error(self):
        """Test ActionError with context."""
        error = ActionError(
            action="select",
            reason="Option not found",
            selector="#dropdown",
            page_url="https://example.com",
        )

        assert "select" in str(error)
        assert "Option not found" in str(error)


class TestWaitAction:
    """Tests for wait action - doesn't require browser."""

    @pytest.mark.asyncio
    async def test_wait_action(self):
        """Test that wait action waits for specified duration."""
        import time

        mock_page = MagicMock()
        step = WaitStepModel(action="wait", duration=0.1)

        start = time.time()
        await wait_action(mock_page, step)
        elapsed = time.time() - start

        assert elapsed >= 0.1


@pytest.fixture
def browser_page():
    """Fixture to provide a Playwright page for testing."""

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        yield page
        context.close()
        browser.close()


class TestNavigateAction:
    """Tests for navigate action."""

    def test_navigate_to_valid_url(self):
        """Test navigation to a valid URL."""
        import asyncio

        # Create an async-compatible page wrapper
        async def run_test():
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                step = NavigateStepModel(action="navigate", url="https://example.com")
                await navigate_action(page, step)

                assert "example.com" in page.url

                await context.close()
                await browser.close()

        asyncio.run(run_test())

    def test_navigate_invalid_url_raises_error(self):
        """Test that navigating to invalid URL raises NavigationError."""
        import asyncio

        async def run_test():
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                step = NavigateStepModel(
                    action="navigate", url="https://invalid-domain-that-does-not-exist-12345.test"
                )

                with pytest.raises(NavigationError) as exc_info:
                    await navigate_action(page, step)

                assert "invalid-domain-that-does-not-exist-12345.test" in str(exc_info.value)

                await context.close()
                await browser.close()

        asyncio.run(run_test())


class TestClickAction:
    """Tests for click action."""

    def test_click_existing_element(self):
        """Test clicking an existing element."""
        import asyncio

        async def run_test():
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.goto("https://example.com")
                step = ClickStepModel(action="click", selector="a")
                await click_action(page, step)

                await context.close()
                await browser.close()

        asyncio.run(run_test())

    def test_click_missing_selector_raises_error(self):
        """Test that clicking a missing selector raises SelectorTimeoutError."""
        import asyncio

        async def run_test():
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.goto("https://example.com")
                step = ClickStepModel(action="click", selector="#non-existent-element-12345")

                with pytest.raises(SelectorTimeoutError) as exc_info:
                    await click_action(page, step)

                assert exc_info.value.selector == "#non-existent-element-12345"
                assert exc_info.value.action == "click"

                await context.close()
                await browser.close()

        asyncio.run(run_test())


class TestTypeAction:
    """Tests for type action."""

    def test_type_missing_selector_raises_error(self):
        """Test that typing into a missing selector raises SelectorTimeoutError."""
        import asyncio

        async def run_test():
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.goto("https://example.com")
                step = TypeStepModel(
                    action="type",
                    selector="#non-existent-input-12345",
                    text="test text",
                )

                with pytest.raises(SelectorTimeoutError) as exc_info:
                    await type_action(page, step)

                assert exc_info.value.selector == "#non-existent-input-12345"
                assert exc_info.value.action == "type"

                await context.close()
                await browser.close()

        asyncio.run(run_test())


class TestWaitForSelectorAction:
    """Tests for wait_for_selector action."""

    def test_wait_for_existing_selector(self):
        """Test waiting for an existing selector."""
        import asyncio

        async def run_test():
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.goto("https://example.com")
                step = WaitForSelectorStepModel(
                    action="wait_for_selector",
                    selector="h1",
                    timeout=5000,
                )
                await wait_for_selector_action(page, step)

                await context.close()
                await browser.close()

        asyncio.run(run_test())

    def test_wait_timeout_raises_error(self):
        """Test that timeout waiting for selector raises SelectorTimeoutError."""
        import asyncio

        async def run_test():
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.goto("https://example.com")
                step = WaitForSelectorStepModel(
                    action="wait_for_selector",
                    selector="#non-existent-12345",
                    timeout=1000,
                )

                with pytest.raises(SelectorTimeoutError) as exc_info:
                    await wait_for_selector_action(page, step)

                assert exc_info.value.timeout_ms == 1000

                await context.close()
                await browser.close()

        asyncio.run(run_test())


class TestScrollAction:
    """Tests for scroll action."""

    def test_scroll_direction(self):
        """Test scrolling by direction."""
        import asyncio

        async def run_test():
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.goto("https://example.com")
                step = ScrollStepModel(action="scroll", direction="down")
                await scroll_action(page, step)

                await context.close()
                await browser.close()

        asyncio.run(run_test())


class TestHoverAction:
    """Tests for hover action."""

    def test_hover_missing_selector_raises_error(self):
        """Test that hovering over missing selector raises SelectorTimeoutError."""
        import asyncio

        async def run_test():
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.goto("https://example.com")
                step = HoverStepModel(action="hover", selector="#non-existent-12345")

                with pytest.raises(SelectorTimeoutError) as exc_info:
                    await hover_action(page, step)

                assert exc_info.value.action == "hover"

                await context.close()
                await browser.close()

        asyncio.run(run_test())


class TestScreenshotAction:
    """Tests for screenshot action."""

    def test_screenshot_saves_file(self):
        """Test that screenshot saves a file."""
        import asyncio

        async def run_test():
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.goto("https://example.com")

                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                    screenshot_path = f.name

                try:
                    step = ScreenshotStepModel(action="screenshot", path=screenshot_path)
                    await screenshot_action(page, step)

                    assert Path(screenshot_path).exists()
                    assert Path(screenshot_path).stat().st_size > 0
                finally:
                    Path(screenshot_path).unlink(missing_ok=True)

                await context.close()
                await browser.close()

        asyncio.run(run_test())


class TestSelectAction:
    """Tests for select action."""

    def test_select_missing_selector_raises_error(self):
        """Test that selecting from missing selector raises SelectorTimeoutError."""
        import asyncio

        async def run_test():
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.goto("https://example.com")
                step = SelectStepModel(
                    action="select",
                    selector="#non-existent-select-12345",
                    value="option1",
                )

                with pytest.raises(SelectorTimeoutError) as exc_info:
                    await select_action(page, step)

                assert exc_info.value.action == "select"

                await context.close()
                await browser.close()

        asyncio.run(run_test())


class TestPressKeyAction:
    """Tests for the press_key action handler."""

    def test_press_key_enter_submits_form(self):
        """Test that pressing Enter on a focused input fires submit-like behavior."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content(
                    "<input id='q' type='text'/><span id='out'></span>"
                    "<script>document.getElementById('q').addEventListener('keydown', e => {"
                    "  if (e.key === 'Enter') document.getElementById('out').textContent = 'submitted';"
                    "});</script>"
                )
                await page.focus("#q")
                step = PressKeyStepModel(key="Enter")
                await press_key_action(page, step)

                result = await page.text_content("#out")
                assert result == "submitted"

                await context.close()
                await browser.close()

        asyncio.run(run_test())

    def test_press_key_raises_action_error_on_failure(self):
        """Test that press_key wraps unexpected errors in ActionError."""

        async def run_test():
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                await context.new_page()

                # Close the page to simulate a failure
                await context.close()
                await browser.close()

                # Use a fresh mock-based approach to force an error
                mock_page = MagicMock()
                mock_page.url = "about:blank"
                mock_page.keyboard = AsyncMock()
                mock_page.keyboard.press.side_effect = Exception("keyboard error")

                step = PressKeyStepModel(key="Enter")
                with pytest.raises(ActionError):
                    await press_key_action(mock_page, step)

        asyncio.run(run_test())


class TestBrowserBackAction:
    """Tests for the browser_back action handler."""

    def test_browser_back_navigates_back(self):
        """Test that browser_back returns to the previous page."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.goto("https://example.com")
                await page.goto("https://example.org")

                step = BrowserBackStepModel()
                await browser_back_action(page, step)

                assert "example.com" in page.url

                await context.close()
                await browser.close()

        asyncio.run(run_test())

    def test_browser_back_timeout_raises_navigation_error(self):
        """Test that go_back timeout raises NavigationError."""
        mock_page = MagicMock()
        mock_page.url = "https://example.com"
        mock_page.go_back = AsyncMock(side_effect=PlaywrightTimeoutError("timeout"))

        step = BrowserBackStepModel(timeout=1000)

        async def run():
            with pytest.raises(NavigationError):
                await browser_back_action(mock_page, step)

        asyncio.run(run())


class TestBrowserForwardAction:
    """Tests for the browser_forward action handler."""

    def test_browser_forward_navigates_forward(self):
        """Test that browser_forward moves forward in history."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.goto("https://example.com")
                await page.goto("https://example.org")
                await page.go_back()

                step = BrowserForwardStepModel()
                await browser_forward_action(page, step)

                assert "example.org" in page.url

                await context.close()
                await browser.close()

        asyncio.run(run_test())


class TestCheckAction:
    """Tests for the check action handler."""

    def test_check_checks_checkbox(self):
        """Test that check action checks an unchecked checkbox."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content("<input id='cb' type='checkbox'/>")
                step = CheckStepModel(selector="#cb")
                await check_action(page, step)

                is_checked = await page.is_checked("#cb")
                assert is_checked is True

                await context.close()
                await browser.close()

        asyncio.run(run_test())

    def test_check_missing_selector_raises_error(self):
        """Test that check with missing selector raises SelectorTimeoutError."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content("<div>no checkboxes here</div>")
                step = CheckStepModel(selector="#non-existent-cb")

                with pytest.raises(SelectorTimeoutError) as exc_info:
                    await check_action(page, step)

                assert exc_info.value.action == "check"

                await context.close()
                await browser.close()

        asyncio.run(run_test())


class TestUncheckAction:
    """Tests for the uncheck action handler."""

    def test_uncheck_unchecks_checkbox(self):
        """Test that uncheck action unchecks a checked checkbox."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content("<input id='cb' type='checkbox' checked/>")
                step = UncheckStepModel(selector="#cb")
                await uncheck_action(page, step)

                is_checked = await page.is_checked("#cb")
                assert is_checked is False

                await context.close()
                await browser.close()

        asyncio.run(run_test())


class TestAssertAction:
    """Tests for the assert action handler."""

    def test_assert_visible_passes(self):
        """Test assert with visible=True passes for a visible element."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content("<h1 id='title'>Hello World</h1>")
                step = AssertStepModel(selector="#title", visible=True)
                # Should not raise
                await assert_action(page, step)

                await context.close()
                await browser.close()

        asyncio.run(run_test())

    def test_assert_text_passes_when_text_matches(self):
        """Test assert with text passes when element contains the text."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content("<p id='msg'>Welcome back!</p>")
                step = AssertStepModel(selector="#msg", text="Welcome")
                # Should not raise
                await assert_action(page, step)

                await context.close()
                await browser.close()

        asyncio.run(run_test())

    def test_assert_text_fails_when_text_mismatch(self):
        """Test assert with text raises ActionError on text mismatch."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content("<p id='msg'>Error: something went wrong</p>")
                step = AssertStepModel(selector="#msg", text="Welcome back!")

                with pytest.raises(ActionError) as exc_info:
                    await assert_action(page, step)

                assert "Welcome back!" in str(exc_info.value)

                await context.close()
                await browser.close()

        asyncio.run(run_test())

    def test_assert_hidden_passes_for_hidden_element(self):
        """Test assert with visible=False passes for a hidden element."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content("<div id='modal' style='display:none'>Hidden</div>")
                step = AssertStepModel(selector="#modal", visible=False)
                # Should not raise
                await assert_action(page, step)

                await context.close()
                await browser.close()

        asyncio.run(run_test())

    def test_assert_missing_selector_raises_selector_timeout(self):
        """Test assert times out when element doesn't exist."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content("<div>nothing here</div>")
                step = AssertStepModel(selector="#ghost", visible=True, timeout=1000)

                with pytest.raises(SelectorTimeoutError) as exc_info:
                    await assert_action(page, step)

                assert exc_info.value.action == "assert"

                await context.close()
                await browser.close()

        asyncio.run(run_test())


class TestClickFirstVisibleAction:
    """Tests for the click_first_visible action handler."""

    def test_click_first_visible_clicks_visible_element(self):
        """Test that click_first_visible clicks the first visible element."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content(
                    "<button class='btn' style='display:none'>Hidden</button>"
                    "<button class='btn' id='visible-btn'>Visible</button>"
                    "<span id='result'></span>"
                    "<script>document.querySelectorAll('.btn').forEach(b => {"
                    "  b.addEventListener('click', () => { document.getElementById('result').textContent = b.id; });"
                    "});</script>"
                )
                step = ClickFirstVisibleStepModel(selector=".btn")
                await click_first_visible_action(page, step)

                result = await page.text_content("#result")
                assert result == "visible-btn"

                await context.close()
                await browser.close()

        asyncio.run(run_test())

    def test_click_first_visible_raises_when_none_visible(self):
        """Test that click_first_visible raises ElementNotFoundError if none visible."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content(
                    "<button class='btn' style='display:none'>Hidden 1</button>"
                    "<button class='btn' style='display:none'>Hidden 2</button>"
                )
                step = ClickFirstVisibleStepModel(selector=".btn")

                with pytest.raises(ElementNotFoundError):
                    await click_first_visible_action(page, step)

                await context.close()
                await browser.close()

        asyncio.run(run_test())


class TestSelectFirstNonPlaceholderAction:
    """Tests for the select_first_non_placeholder action handler."""

    def test_selects_first_non_empty_option(self):
        """Test that the correct option is selected."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content(
                    "<select id='country'>"
                    "  <option value=''>-- select --</option>"
                    "  <option value='uk'>United Kingdom</option>"
                    "  <option value='us'>United States</option>"
                    "</select>"
                )
                step = SelectFirstNonPlaceholderStepModel(selector="#country")
                await select_first_non_placeholder_action(page, step)

                selected = await page.evaluate("document.querySelector('#country').value")
                assert selected == "uk"

                await context.close()
                await browser.close()

        asyncio.run(run_test())

    def test_raises_when_no_non_placeholder_option(self):
        """Test ElementNotFoundError when only placeholder options exist."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content(
                    "<select id='empty'>" "  <option value=''>-- select --</option>" "</select>"
                )
                step = SelectFirstNonPlaceholderStepModel(selector="#empty")

                with pytest.raises(ElementNotFoundError):
                    await select_first_non_placeholder_action(page, step)

                await context.close()
                await browser.close()

        asyncio.run(run_test())


class TestFileUploadAction:
    """Tests for the file_upload action handler."""

    def test_file_upload_single_file(self):
        """Test uploading a single file to a file input."""

        async def run_test():
            import os
            import tempfile

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content("<input id='uploader' type='file'/>")

                # Create a real temp file to upload
                with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
                    f.write(b"test content")
                    tmp_path = f.name

                try:
                    step = FileUploadStepModel(selector="#uploader", file=tmp_path)
                    await file_upload_action(page, step)

                    # Verify a file was set on the input
                    filename = await page.evaluate(
                        "document.querySelector('#uploader').files[0]?.name"
                    )
                    assert filename == os.path.basename(tmp_path)
                finally:
                    os.unlink(tmp_path)

                await context.close()
                await browser.close()

        asyncio.run(run_test())

    def test_file_upload_missing_selector_raises_error(self):
        """Test that file_upload with missing selector raises SelectorTimeoutError."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content("<div>no file input here</div>")
                step = FileUploadStepModel(selector="#ghost-uploader", file="/tmp/noop.txt")

                with pytest.raises(SelectorTimeoutError) as exc_info:
                    await file_upload_action(page, step)

                assert exc_info.value.action == "file_upload"

                await context.close()
                await browser.close()

        asyncio.run(run_test())


class TestDragAndDropAction:
    """Tests for the drag_and_drop action handler."""

    def test_drag_and_drop_moves_element(self):
        """Test that drag_and_drop calls the Playwright drag_and_drop API."""
        # Use a mock to verify the API call without needing a real draggable UI
        mock_page = MagicMock()
        mock_page.url = "about:blank"
        mock_page.wait_for_selector = AsyncMock()
        mock_page.drag_and_drop = AsyncMock()

        step = DragAndDropStepModel(source="#item", target="#bucket")

        async def run():
            await drag_and_drop_action(mock_page, step)
            mock_page.drag_and_drop.assert_called_once_with("#item", "#bucket")

        asyncio.run(run())

    def test_drag_and_drop_missing_source_raises_timeout(self):
        """Test that drag_and_drop raises SelectorTimeoutError when source not found."""

        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.set_content("<div id='target'>Drop Zone</div>")
                step = DragAndDropStepModel(source="#non-existent-item", target="#target")

                with pytest.raises(SelectorTimeoutError) as exc_info:
                    await drag_and_drop_action(page, step)

                assert exc_info.value.action == "drag_and_drop"

                await context.close()
                await browser.close()

        asyncio.run(run_test())
