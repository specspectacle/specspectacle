"""
Cursor motion algorithms for rendering human-like smooth mouse movements.
Provides bezier curves, easing functions, and micro-jitters.
"""

import asyncio
import math
import random

from playwright.async_api import Page


def move_duration(distance: float) -> float:
    """Fitts's law inspired duration: scales with sqrt of distance."""
    return 180 + 16 * math.sqrt(distance) + (random.random() - 0.5) * 30

def human_ease(t: float) -> float:
    """
    Asymmetric ease-in-out: reaches 50% progress at 40% of elapsed time.
    Acceleration is quadratic; deceleration is cubic.
    """
    mid = 0.4
    if t <= mid:
        s = t / mid
        return 0.5 * s * s
    s = (t - mid) / (1 - mid)
    return 0.5 + 0.5 * (1 - (1 - s) ** 3)

def bezier_control(x0: float, y0: float, x1: float, y1: float, dist: float) -> tuple[float, float]:
    """Calculate the control point for a quadratic bezier curve to add a natural arc."""
    mx = (x0 + x1) / 2
    my = (y0 + y1) / 2

    if dist < 80:
        return mx, my

    px = -(y1 - y0) / dist
    py = (x1 - x0) / dist

    sign = -1 if random.random() < 0.5 else 1
    offset = dist * (0.03 + random.random() * 0.07) * sign

    return mx + px * offset, my + py * offset

def eval_bezier(t: float, p0: tuple[float, float], p1: tuple[float, float], p2: tuple[float, float]) -> tuple[float, float]:
    """Evaluate quadratic bezier at t (0.0 to 1.0)."""
    m = 1 - t
    x = m * m * p0[0] + 2 * m * t * p1[0] + t * t * p2[0]
    y = m * m * p0[1] + 2 * m * t * p1[1] + t * t * p2[1]
    return x, y

def micro_jitter(t: float, dist: float) -> tuple[float, float]:
    """Add subtle structural noise (tremor) around the midpoint of the movement."""
    bell = math.exp(-8 * (t - 0.5) ** 2)
    mag = min(0.4, dist * 0.0004) * bell
    jx = (random.random() - 0.5) * 2 * mag
    jy = (random.random() - 0.5) * 2 * mag
    return jx, jy

def compute_move_timing(distance: float) -> dict[str, float]:
    """Compute number of steps and delay per step for a movement."""
    duration = 180 + 16 * math.sqrt(distance) + (random.random() - 0.5) * 30
    frame_ms = 16.6  # ~60fps
    steps = max(6, round(duration / frame_ms))
    return {"steps": steps, "delay_ms": duration / steps}

def compute_drag_timing(distance: float) -> dict[str, float]:
    """Compute drag timing which is generally slower than moving empty-handed."""
    duration = 300 + 20 * math.sqrt(distance) + (random.random() - 0.5) * 40
    steps = max(12, round(duration / 30.0))
    return {"steps": steps, "delay_ms": duration / steps}

def compute_eased_path(from_x: float, from_y: float, to_x: float, to_y: float, steps: int) -> list[tuple[float, float]]:
    """Compute an array of points for a smooth path without jitter."""
    dx = to_x - from_x
    dy = to_y - from_y
    dist = math.sqrt(dx * dx + dy * dy)

    if dist < 1:
        return [(to_x, to_y)]

    ctrl = bezier_control(from_x, from_y, to_x, to_y, dist)
    p0 = (from_x, from_y)
    p2 = (to_x, to_y)

    pts = []
    for i in range(1, steps + 1):
        raw_t = i / steps
        t = human_ease(raw_t)
        pts.append(eval_bezier(t, p0, ctrl, p2))

    pts[-1] = (to_x, to_y)
    return pts

async def move_cursor_smoothly(page: Page, from_x: float, from_y: float, to_x: float, to_y: float):
    """
    Animate the Playwright cursor smoothly using bezier curves and easing.
    """
    dx = to_x - from_x
    dy = to_y - from_y
    dist = math.sqrt(dx * dx + dy * dy)

    if dist < 1:
        await page.mouse.move(to_x, to_y)
        return

    timing = compute_move_timing(dist)
    steps = int(timing["steps"])
    delay_ms = timing["delay_ms"]

    # Pre-compute path with jitter
    ctrl = bezier_control(from_x, from_y, to_x, to_y, dist)
    p0 = (from_x, from_y)
    p2 = (to_x, to_y)

    positions = []
    for i in range(1, steps + 1):
        raw_t = i / steps
        t = human_ease(raw_t)
        pos_x, pos_y = eval_bezier(t, p0, ctrl, p2)
        if dist > 60:
            jx, jy = micro_jitter(raw_t, dist)
            pos_x += jx
            pos_y += jy
        positions.append((round(pos_x, 1), round(pos_y, 1)))

    positions[-1] = (to_x, to_y)

    duration_ms = steps * delay_ms

    try:
        # Animate visually in the browser using requestAnimationFrame for zero-lag 60fps
        await page.evaluate(
            "async ([pts, dur]) => { if (window.__animateCursor) await window.__animateCursor(pts, dur); }",
            [positions, duration_ms]
        )
    except Exception:
        # Fallback if script is missing
        await asyncio.sleep(duration_ms / 1000.0)

    # Move the real native Playwright cursor to the final destination
    await page.mouse.move(to_x, to_y)

async def get_element_center(page: Page, selector: str) -> tuple[float, float]:
    """Helper to get the visual center of an element."""
    box = await page.locator(selector).first.bounding_box()
    if box:
        return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    return 0, 0
