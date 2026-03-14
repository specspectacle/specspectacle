"""
Natural character-by-character typing engine.

Implements human-like typing behaviour:
- Realistic inter-keystroke delays with jitter and occasional hesitation pauses
- Character-by-character dispatch via Playwright's keyboard API

Public interface (deep module — small surface, rich implementation):
    human_delay(base_ms)            → float
    type_text_naturally(page, text, base_delay_ms)  → coroutine
"""

import asyncio
import random
import time

from playwright.async_api import Page


def human_delay(base_ms: float) -> float:
    """
    Return a realistic inter-keystroke delay in milliseconds.

    Algorithm:
      - Normal case (88%): jitter between 0.6× and 1.5× of base
      - Hesitation pause (12%): jitter + an extra 1.5–3.5× burst

    Args:
        base_ms: Nominal delay in milliseconds between keystrokes.

    Returns:
        Actual delay in milliseconds (always >= 0).
    """
    jitter = base_ms * (0.6 + random.random() * 0.9)
    if random.random() < 0.12:
        return jitter + base_ms * 1.5 + random.random() * base_ms * 2
    return jitter


async def type_text_naturally(
    page: Page,
    text: str,
    base_delay_ms: float = 100,
) -> list[float]:
    """
    Type each character in *text* one at a time with human-like timing.

    For each character:
      1. Dispatch the keystroke via ``page.keyboard.type(char)``
         (Playwright fires the full keydown → keypress → input → keyup chain)
      2. Sleep for a ``human_delay``-randomised duration

    This produces realistic video output: characters appear at varied speeds,
    with occasional micro-hesitations, mirroring real human typing.

    Args:
        page: Active Playwright page object.
        text: The string to type.
        base_delay_ms: Nominal inter-keystroke delay; actual delay is jittered
            around this value. Default: 100 ms (≈ relaxed typing pace).
    """
    ts = []
    for char in text:
        await page.keyboard.down(char)
        ts.append(time.time())
        await page.keyboard.up(char)

        delay_s = human_delay(base_delay_ms) / 1000.0
        await asyncio.sleep(delay_s)
    return ts
