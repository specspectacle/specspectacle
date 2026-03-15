"""
Sound effects module — resolves built-in/custom audio assets and builds
ffmpeg filter_complex arguments for mixing SFX into video.

"""

from __future__ import annotations

import random
from pathlib import Path

from specspectacle.executor.timeline import SoundEvent

# Built-in sound assets bundled with specspectacle
ASSETS_DIR = Path(__file__).parent / "assets"

# Re-export for convenience
__all__ = ["SoundEvent", "ASSETS_DIR", "resolve_sfx_path", "build_sfx_mix_args"]


def resolve_sfx_path(value: int | str | None, prefix: str) -> str | None:
    """
    Resolve an SFX config value to an absolute file path.

    Args:
        value: Built-in variant (1-4), custom file path string, or None
        prefix: Asset prefix — "click" or "key"

    Returns:
        Absolute path string, or None if disabled
    """
    if value is None:
        return None
    if isinstance(value, int):
        return str(ASSETS_DIR / f"{prefix}-{value}.mp3")
    return value  # custom file path


def build_sfx_mix_args(
    video_path: str,
    events: list[SoundEvent],
    click_sfx_path: str | None,
    key_sfx_path: str | None,
    has_audio: bool = False,
) -> dict | None:
    """
    Build ffmpeg arguments for mixing sound events into a video.

    Returns a dict with 'inputs' (list of -i paths) and 'filter_complex' string,
    or None if there are no events to mix.

    - Each SFX event becomes a separate audio stream
    - Each stream is adelayed to its correct timestamp
    - Volume/pitch are slightly randomized for natural feel
    - All streams are amixed into one output
    """
    if not events:
        return None

    # Resolve which SFX file to use per event type
    sfx_paths: dict[str, str | None] = {
        "click": click_sfx_path,
        "key": key_sfx_path,
    }

    # Filter to events that have a valid SFX file
    usable_events = [e for e in events if sfx_paths.get(e.type)]
    if not usable_events:
        return None

    # Collect unique input files
    unique_inputs: list[str] = []
    input_index_map: dict[str, int] = {}

    for evt in usable_events:
        path = sfx_paths[evt.type]
        if path and path not in input_index_map:
            input_index_map[path] = len(unique_inputs) + 1  # input 0 is the original video
            unique_inputs.append(path)

    # Build filter_complex
    filter_parts = []
    for i, evt in enumerate(usable_events):
        path = sfx_paths[evt.type]
        input_idx = input_index_map[path]
        delay_ms = int(evt.time_ms)

        # Randomize volume slightly (0.3-0.5) for natural feel
        volume = round(0.3 + random.random() * 0.2, 2)

        filter_parts.append(
            f"[{input_idx}:a]adelay={delay_ms}|{delay_ms},"
            f"volume={volume}[sfx{i}]"
        )

    # Mix all SFX streams together with original audio (if any)
    if has_audio:
        mix_inputs = "[0:a:0]" + "".join(f"[sfx{i}]" for i in range(len(usable_events)))
        filter_parts.append(
            f"{mix_inputs}amix=inputs={len(usable_events) + 1}:duration=longest[mixed_audio];"
            f"[mixed_audio]apad=pad_dur=2[final_audio]"
        )
    else:
        mix_inputs = "".join(f"[sfx{i}]" for i in range(len(usable_events)))
        filter_parts.append(
            f"{mix_inputs}amix=inputs={len(usable_events)}:duration=longest[mixed_audio];"
            f"[mixed_audio]apad=pad_dur=2[final_audio]"
        )

    return {
        "inputs": unique_inputs,
        "filter_complex": ";".join(filter_parts),
    }
