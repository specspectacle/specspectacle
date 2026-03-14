"""
Timeline tracking for executor step execution.

This module provides classes for recording the timing of each action
during spec execution, enabling audio/video synchronization and debugging.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class SoundEvent:
    """A single sound event recorded during spec execution."""

    type: Literal["click", "key"]
    time_ms: float

    def to_dict(self) -> dict:
        """Serialize to a plain dict."""
        return {"type": self.type, "time_ms": self.time_ms}



@dataclass
class TimelineEvent:
    """
    Represents a single action execution in the timeline.

    Attributes:
        step_name: Human-readable step identifier (e.g., "Navigate to login page")
        action: Action type (navigate, click, type, etc.)
        start_time: Unix timestamp when action started
        end_time: Unix timestamp when action completed
        duration: Duration in seconds
        flow_name: Name of the parent flow
        flow_index: Index of the flow (1-indexed)
        step_index: Index of the step within the flow (1-indexed)
        success: Whether the action completed successfully
        error_message: Error details if the action failed
        narration_start_time: Unix timestamp when narration should start (for audio sync)
    """

    step_name: str
    action: str
    start_time: float
    end_time: float
    duration: float
    flow_name: str
    flow_index: int
    step_index: int
    success: bool = True
    error_message: str | None = None
    narration_start_time: float | None = None  # Exact time when narration should play

    def to_dict(self) -> dict:
        """Convert event to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class Timeline:
    """
    Tracks the execution timeline of an entire spec.

    Provides methods to record events, calculate durations,
    and serialize to JSON for use in audio/video processing.

    Attributes:
        spec_name: Name of the spec being executed
        events: List of timeline events
        started_at: Unix timestamp when execution started
        completed_at: Unix timestamp when execution completed
    """

    spec_name: str
    events: list[TimelineEvent] = field(default_factory=list)
    sound_events: list[SoundEvent] = field(default_factory=list)
    started_at: float | None = None
    completed_at: float | None = None

    def start(self) -> None:
        """Mark the start of spec execution."""
        self.started_at = time.time()

    def complete(self) -> None:
        """Mark the completion of spec execution."""
        self.completed_at = time.time()

    def add_event(self, event: TimelineEvent) -> None:
        """
        Add an event to the timeline.

        Args:
            event: The timeline event to add
        """
        self.events.append(event)

    def add_sound_event(self, sound_type: str, time_ms: float) -> None:
        """
        Record a sound event (click or key) with its timestamp.

        Args:
            type: "click" or "key"
            time_ms: Milliseconds from timeline start
        """
        self.sound_events.append(SoundEvent(type=sound_type, time_ms=time_ms))

    def record_event(
        self,
        step_name: str,
        action: str,
        flow_name: str,
        flow_index: int,
        step_index: int,
        start_time: float,
        end_time: float,
        success: bool = True,
        error_message: str | None = None,
        narration_start_time: float | None = None,
    ) -> TimelineEvent:
        """
        Create and record a new timeline event.

        Args:
            step_name: Human-readable step name
            action: Action type
            flow_name: Name of the parent flow
            flow_index: Flow index (1-indexed)
            step_index: Step index (1-indexed)
            start_time: Unix timestamp when action started
            end_time: Unix timestamp when action completed
            success: Whether action succeeded
            error_message: Error details if failed
            narration_start_time: Unix timestamp when narration should start

        Returns:
            The created TimelineEvent
        """
        event = TimelineEvent(
            step_name=step_name,
            action=action,
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            flow_name=flow_name,
            flow_index=flow_index,
            step_index=step_index,
            success=success,
            error_message=error_message,
            narration_start_time=narration_start_time,
        )
        self.add_event(event)
        return event

    @property
    def total_duration(self) -> float:
        """
        Calculate total execution duration in seconds.

        Returns:
            Total duration from start to completion, or sum of event durations
        """
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return sum(event.duration for event in self.events)

    @property
    def successful_events(self) -> list[TimelineEvent]:
        """Get list of successful events."""
        return [e for e in self.events if e.success]

    @property
    def failed_events(self) -> list[TimelineEvent]:
        """Get list of failed events."""
        return [e for e in self.events if not e.success]

    def to_dict(self) -> dict:
        """
        Convert timeline to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the timeline
        """
        return {
            "spec_name": self.spec_name,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration": self.total_duration,
            "total_events": len(self.events),
            "successful_events": len(self.successful_events),
            "failed_events": len(self.failed_events),
            "events": [event.to_dict() for event in self.events],
            "sound_events": [se.to_dict() for se in self.sound_events],
        }

    def save(self, path: Path) -> None:
        """
        Save timeline to a JSON file.

        Args:
            path: Path to save the JSON file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "Timeline":
        """
        Load timeline from a JSON file.

        Args:
            path: Path to the JSON file

        Returns:
            Timeline instance
        """
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        timeline = cls(spec_name=data["spec_name"])
        timeline.started_at = data.get("started_at")
        timeline.completed_at = data.get("completed_at")

        for event_data in data.get("events", []):
            event = TimelineEvent(**event_data)
            timeline.add_event(event)

        for se_data in data.get("sound_events", []):
            timeline.sound_events.append(SoundEvent(**se_data))

        return timeline


__all__ = ["TimelineEvent", "Timeline"]
