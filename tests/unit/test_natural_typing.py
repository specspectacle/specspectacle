"""
Unit tests for the natural_typing engine module.
Tests drive implementation via red-green-refactor (TDD vertical slices).
All tests mock the Playwright page to stay pure unit tests.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from specspectacle.executor.natural_typing import (
    human_delay,
    type_text_naturally,
)


class TestHumanDelay:
    """Behaviour: human_delay must return a positive, statistically realistic number."""

    def test_returns_positive_number(self):
        """human_delay is always > 0 for any positive base."""
        for _ in range(50):
            result = human_delay(100)
            assert result > 0

    def test_average_close_to_base(self):
        """
        Average over many samples should land within 0.5x–3x the base,
        accounting for the 12% hesitation probability.
        Statistical bound is deliberately wide to keep the test non-flaky.
        """
        samples = [human_delay(100) for _ in range(200)]
        avg = sum(samples) / len(samples)
        # With 12% hesitation at up to 3.5x: expected avg ≈ 0.6*100 + 0.12*250 = 90
        # Allow generous range: 50ms–350ms
        assert 50 <= avg <= 350

    def test_zero_base_returns_nonnegative(self):
        """human_delay(0) should not crash and should return >= 0."""
        result = human_delay(0)
        assert result >= 0


class TestTypeTextNaturally:
    """Behaviour: type_text_naturally calls keyboard once per character with delays."""

    def _make_page(self):
        """Return a mock Playwright page with async keyboard."""
        page = MagicMock()
        page.keyboard = MagicMock()
        page.keyboard.down = AsyncMock()
        page.keyboard.up = AsyncMock()
        page.keyboard.type = AsyncMock()
        return page

    @pytest.mark.asyncio
    async def test_each_character_triggers_keyboard_type(self):
        """type_text_naturally calls page.keyboard.type once per character."""
        page = self._make_page()
        with patch("specspectacle.executor.natural_typing.asyncio.sleep", new_callable=AsyncMock):
            await type_text_naturally(page, "hi", base_delay_ms=10)
        assert page.keyboard.type.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_string_produces_no_keyboard_calls(self):
        """Empty text → zero keyboard interactions."""
        page = self._make_page()
        with patch("specspectacle.executor.natural_typing.asyncio.sleep", new_callable=AsyncMock):
            await type_text_naturally(page, "", base_delay_ms=10)
        page.keyboard.type.assert_not_called()

    @pytest.mark.asyncio
    async def test_sleep_called_between_characters(self):
        """asyncio.sleep is called once per character (the inter-keystroke delay)."""
        page = self._make_page()
        with patch(
            "specspectacle.executor.natural_typing.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await type_text_naturally(page, "abc", base_delay_ms=50)
        # One sleep per character
        assert mock_sleep.call_count == 3

    @pytest.mark.asyncio
    async def test_correct_characters_typed_in_order(self):
        """page.keyboard.type is called with each character in the correct order."""
        page = self._make_page()
        with patch("specspectacle.executor.natural_typing.asyncio.sleep", new_callable=AsyncMock):
            await type_text_naturally(page, "OK", base_delay_ms=10)
        calls = [c.args[0] for c in page.keyboard.type.call_args_list]
        assert calls == ["O", "K"]
