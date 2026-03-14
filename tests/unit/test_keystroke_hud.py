"""Unit tests for keystroke HUD overlay JS generation."""


from specspectacle.executor.keystroke_hud import (
    generate_hide_keys_script,
    generate_hud_inject_script,
    generate_show_keys_script,
)
from specspectacle.parser.schema import KeystrokeHudThemeModel


class TestGenerateHudInjectScript:
    """Tests for the HUD injection script generator."""

    def test_contains_element_id(self):
        """Inject script creates the __demo-keys element."""
        theme = KeystrokeHudThemeModel()
        script = generate_hud_inject_script(theme)
        assert "__demo-keys" in script

    def test_applies_default_theme(self):
        """Default theme values appear in the generated CSS."""
        theme = KeystrokeHudThemeModel()
        script = generate_hud_inject_script(theme)
        assert "rgba(0,0,0,0.5)" in script
        assert "rgba(255,255,255,0.85)" in script
        assert "56px" in script
        assert "18px" in script

    def test_applies_custom_theme(self):
        """Custom theme values appear in the generated CSS."""
        theme = KeystrokeHudThemeModel(
            background="red",
            color="blue",
            font_size=32,
            border_radius=8,
        )
        script = generate_hud_inject_script(theme)
        assert "red" in script
        assert "blue" in script
        assert "32px" in script
        assert "8px" in script

    def test_position_bottom(self):
        """Bottom position sets 'bottom' CSS property."""
        theme = KeystrokeHudThemeModel(position="bottom")
        script = generate_hud_inject_script(theme)
        assert "bottom:" in script

    def test_position_top(self):
        """Top position sets 'top' CSS property."""
        theme = KeystrokeHudThemeModel(position="top")
        script = generate_hud_inject_script(theme)
        assert "top:" in script

    def test_is_iife(self):
        """Script is an IIFE to avoid polluting global scope."""
        theme = KeystrokeHudThemeModel()
        script = generate_hud_inject_script(theme)
        assert script.strip().startswith("(() =>")
        assert script.strip().endswith(")()")

    def test_idempotent_guard(self):
        """Script has a guard so re-injection is safe."""
        theme = KeystrokeHudThemeModel()
        script = generate_hud_inject_script(theme)
        assert "__hudInjected" in script


class TestGenerateShowKeysScript:
    """Tests for the show-keys script generator."""

    def test_single_label(self):
        """Single label is embedded in the script."""
        script = generate_show_keys_script(["Enter"])
        assert "Enter" in script

    def test_multiple_labels(self):
        """Multiple labels are joined with the + separator."""
        script = generate_show_keys_script(["Ctrl", "S"])
        assert "Ctrl" in script
        assert "S" in script

    def test_sets_opacity_one(self):
        """Show script sets opacity to 1."""
        script = generate_show_keys_script(["A"])
        assert "opacity" in script
        assert "1" in script


class TestGenerateHideKeysScript:
    """Tests for the hide-keys script generator."""

    def test_sets_opacity_zero(self):
        """Hide script sets opacity to 0."""
        script = generate_hide_keys_script()
        assert "opacity" in script
        assert "0" in script

    def test_references_element(self):
        """Hide script references the __demo-keys element."""
        script = generate_hide_keys_script()
        assert "__demo-keys" in script
