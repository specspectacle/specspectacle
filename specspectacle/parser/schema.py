"""
Pydantic schema models for YAML specification validation
"""

from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from specspectacle.utils.validation import (
    is_valid_hex_color,
    is_valid_selector,
    is_valid_url,
)

# ==================== Configuration Models ====================


class ViewportModel(BaseModel):
    """Browser viewport dimensions."""

    width: int = Field(default=1280, ge=800, le=3840)
    height: int = Field(default=720, ge=600, le=2160)


class ConfigModel(BaseModel):
    """Global configuration for the demo."""

    target_app: str = Field(..., description="Base URL of the application")
    viewport: ViewportModel = Field(default_factory=ViewportModel)
    timeout: int = Field(default=5000, ge=1000, description="Default timeout in milliseconds")
    headless: bool = Field(default=True)
    slow_motion: int = Field(default=0, ge=0, description="Slow motion delay in milliseconds")

    @field_validator("target_app")
    @classmethod
    def validate_target_app(cls, v: str) -> str:
        if not is_valid_url(v):
            raise ValueError(f"Invalid target_app URL: {v}")
        return v


class OutputModel(BaseModel):
    """Video output configuration."""

    filename: str = Field(..., description="Output MP4 filename")
    fps: int = Field(default=30, ge=15, le=60)
    bitrate: str = Field(default="5000k", pattern=r"^\d+k$")
    codec: str = Field(default="h264")
    resolution: str = Field(default="1280x720", pattern=r"^\d+x\d+$")


class NarrationConfigModel(BaseModel):
    """Global narration settings."""

    enabled: bool = Field(default=True)
    provider: str = Field(default="openai")
    voice: str = Field(default="en-default")
    speed: float = Field(default=1.0, ge=0.25, le=4.0)
    language: str = Field(default="en-US")


# ==================== Narration \u0026 Overlay Models ====================


class NarrationModel(BaseModel):
    """Narration for a specific step or flow."""

    text: str = Field(..., description="Narration text")
    timing: Literal["before", "during", "after"] = Field(default="during")
    offset: float = Field(default=0.0, description="Offset in seconds")


class OverlayStyleModel(BaseModel):
    """Text overlay styling."""

    background_color: str = Field(default="#000000AA")
    text_color: str = Field(default="#FFFFFF")
    font_size: int = Field(default=22, ge=8, le=72)
    font_family: Optional[str] = Field(default="Arial")

    @field_validator("background_color", "text_color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not is_valid_hex_color(v):
            raise ValueError(f"Invalid hex color: {v}")
        return v


class OverlayModel(BaseModel):
    """Text overlay for a step."""

    text: str = Field(..., description="Overlay text")
    position: str = Field(default="bottom", description="top, bottom, center, top-left, etc.")
    duration: float = Field(default=2.0, ge=0.1)
    timing: Literal["before", "during", "after"] = Field(default="during")
    style: OverlayStyleModel = Field(default_factory=OverlayStyleModel)

    @field_validator("position")
    @classmethod
    def validate_position(cls, v: str) -> str:
        valid_positions = [
            "top",
            "bottom",
            "center",
            "top-left",
            "top-right",
            "bottom-left",
            "bottom-right",
            "left",
            "right",
        ]
        if v not in valid_positions:
            raise ValueError(f"Invalid position: {v}. Must be one of: {', '.join(valid_positions)}")
        return v


# ==================== Step Action Models ====================


class NavigateStepModel(BaseModel):
    """Navigate to a URL."""

    action: Literal["navigate"] = "navigate"
    url: str = Field(..., description="URL to navigate to")
    pause: float = Field(default=0.0, ge=0.0)
    narration: Optional[NarrationModel] = None
    overlay: Optional[OverlayModel] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        # Allow relative URLs or absolute URLs
        if not v.startswith("/") and not is_valid_url(v):
            raise ValueError(f"Invalid URL: {v}")
        return v


class ClickStepModel(BaseModel):
    """Click an element."""

    action: Literal["click"] = "click"
    selector: str = Field(..., description="CSS selector")
    pause: float = Field(default=0.0, ge=0.0)
    narration: Optional[NarrationModel] = None
    overlay: Optional[OverlayModel] = None

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: str) -> str:
        if not is_valid_selector(v):
            raise ValueError(f"Invalid selector: {v}")
        return v


class TypeStepModel(BaseModel):
    """Type text into a field."""

    action: Literal["type"] = "type"
    selector: str = Field(..., description="CSS selector")
    text: str = Field(..., description="Text to type")
    delay: int = Field(default=0, ge=0, description="Delay between keystrokes in ms")
    pause: float = Field(default=0.0, ge=0.0)
    narration: Optional[NarrationModel] = None
    overlay: Optional[OverlayModel] = None

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: str) -> str:
        if not is_valid_selector(v):
            raise ValueError(f"Invalid selector: {v}")
        return v


class WaitStepModel(BaseModel):
    """Wait for a specified duration."""

    action: Literal["wait"] = "wait"
    duration: float = Field(..., ge=0.1, description="Duration in seconds")
    narration: Optional[NarrationModel] = None
    overlay: Optional[OverlayModel] = None


class WaitForSelectorStepModel(BaseModel):
    """Wait for an element to appear."""

    action: Literal["wait_for_selector"] = "wait_for_selector"
    selector: str = Field(..., description="CSS selector")
    timeout: int = Field(default=5000, ge=1000, description="Timeout in milliseconds")
    pause: float = Field(default=0.0, ge=0.0)
    narration: Optional[NarrationModel] = None
    overlay: Optional[OverlayModel] = None

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: str) -> str:
        if not is_valid_selector(v):
            raise ValueError(f"Invalid selector: {v}")
        return v


class HoverStepModel(BaseModel):
    """Hover over an element."""

    action: Literal["hover"] = "hover"
    selector: str = Field(..., description="CSS selector")
    pause: float = Field(default=0.0, ge=0.0)
    narration: Optional[NarrationModel] = None
    overlay: Optional[OverlayModel] = None

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: str) -> str:
        if not is_valid_selector(v):
            raise ValueError(f"Invalid selector: {v}")
        return v


class ScrollStepModel(BaseModel):
    """Scroll page."""

    action: Literal["scroll"] = "scroll"
    direction: Optional[Literal["up", "down", "left", "right"]] = None
    selector: Optional[str] = Field(
        default=None, description="Scroll to element (alternative to direction)"
    )
    pause: float = Field(default=0.0, ge=0.0)
    narration: Optional[NarrationModel] = None
    overlay: Optional[OverlayModel] = None

    @model_validator(mode="after")
    def validate_scroll_params(self):
        if not self.direction and not self.selector:
            raise ValueError("scroll action requires either 'direction' or 'selector'")
        if self.direction and self.selector:
            raise ValueError("scroll action cannot have both 'direction' and 'selector'")
        if self.selector and not is_valid_selector(self.selector):
            raise ValueError(f"Invalid selector: {self.selector}")
        return self


class ScreenshotStepModel(BaseModel):
    """Capture a screenshot."""

    action: Literal["screenshot"] = "screenshot"
    path: Optional[str] = Field(default=None, description="Output path for screenshot")
    pause: float = Field(default=0.0, ge=0.0)
    narration: Optional[NarrationModel] = None
    overlay: Optional[OverlayModel] = None


class SelectStepModel(BaseModel):
    """Select an option from a dropdown."""

    action: Literal["select"] = "select"
    selector: str = Field(..., description="CSS selector")
    value: str = Field(..., description="Value to select")
    pause: float = Field(default=0.0, ge=0.0)
    narration: Optional[NarrationModel] = None
    overlay: Optional[OverlayModel] = None

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: str) -> str:
        if not is_valid_selector(v):
            raise ValueError(f"Invalid selector: {v}")
        return v


# Union of all step types with discriminated union based on 'action' field
# This ensures Pydantic only validates against the matching model, not all models
StepModel = Annotated[
    Union[
        NavigateStepModel,
        ClickStepModel,
        TypeStepModel,
        WaitStepModel,
        WaitForSelectorStepModel,
        HoverStepModel,
        ScrollStepModel,
        ScreenshotStepModel,
        SelectStepModel,
    ],
    Field(discriminator="action"),
]


# ==================== Flow \u0026 Spec Models ====================


class FlowModel(BaseModel):
    """A flow is a logical section of the demo with multiple steps."""

    name: str = Field(..., description="Flow name")
    description: Optional[str] = None
    narration: Optional[NarrationModel] = None
    steps: List[StepModel] = Field(..., min_length=1)


class SpecModel(BaseModel):
    """Top-level specification model."""

    name: str = Field(..., description="Demo name")
    description: Optional[str] = None
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    config: ConfigModel
    output: OutputModel
    narration: NarrationConfigModel = Field(default_factory=NarrationConfigModel)
    flows: List[FlowModel] = Field(..., min_length=1)


__all__ = [
    "ViewportModel",
    "ConfigModel",
    "OutputModel",
    "NarrationConfigModel",
    "NarrationModel",
    "OverlayStyleModel",
    "OverlayModel",
    "NavigateStepModel",
    "ClickStepModel",
    "TypeStepModel",
    "WaitStepModel",
    "WaitForSelectorStepModel",
    "HoverStepModel",
    "ScrollStepModel",
    "ScreenshotStepModel",
    "SelectStepModel",
    "StepModel",
    "FlowModel",
    "SpecModel",
]
