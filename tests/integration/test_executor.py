"""
Integration tests for the executor module.

Tests browser actions, timeline tracking, and error handling.
Requires Playwright and Chromium to be installed.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from specspectacle.executor.actions import (
    click_action,
    hover_action,
    navigate_action,
    screenshot_action,
    scroll_action,
    select_action,
    type_action,
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
    import asyncio

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
