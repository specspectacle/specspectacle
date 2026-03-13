import math

from specspectacle.executor.cursor_motion import (
    bezier_control,
    compute_eased_path,
    compute_move_timing,
    human_ease,
)


def test_human_ease():
    assert math.isclose(human_ease(0.0), 0.0)
    assert math.isclose(human_ease(1.0), 1.0)
    assert 0.0 <= human_ease(0.5) <= 1.0

def test_bezier_control():
    cx, cy = bezier_control(0, 0, 100, 100, 141.4)
    assert cx != 50 or cy != 50  # Should have an offset for large distance

def test_compute_eased_path():
    path = compute_eased_path(0, 0, 100, 100, 10)
    assert len(path) == 10
    assert path[-1] == (100, 100)

def test_compute_move_timing():
    timing = compute_move_timing(100.0)
    assert timing["steps"] >= 6
    assert timing["delay_ms"] > 0
