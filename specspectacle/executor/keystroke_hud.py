"""
Keystroke HUD overlay — injects and controls a key-label overlay in the browser.

A fixed-position div (#__demo-keys) is injected into the page via page.evaluate().
show_keys / hide_keys toggle its content and visibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

    from specspectacle.parser.schema import KeystrokeHudThemeModel


def generate_hud_inject_script(theme: KeystrokeHudThemeModel) -> str:
    """
    Generate a JS IIFE that creates the #__demo-keys element with CSS styling.

    The script is idempotent (guarded by window.__hudInjected).
    """
    # Determine position CSS based on theme.position
    if theme.position == "top":
        position_css = "top: 40px;"
    else:
        position_css = "bottom: 40px;"

    return f"""(() => {{
  if (window.__hudInjected) return;
  window.__hudInjected = true;

  const style = document.createElement('style');
  style.textContent = `
    .__demo-key {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: {theme.color};
      font-family: {theme.font_family};
      font-size: {theme.font_size}px;
      font-weight: 500;
      white-space: nowrap;
    }}
  `;
  document.head.appendChild(style);

  const el = document.createElement('div');
  el.id = '__demo-keys';
  el.style.cssText = `
    position: fixed;
    {position_css}
    left: 50%;
    transform: translateX(-50%);
    background: {theme.background};
    border-radius: {theme.border_radius}px;
    padding: 16px 36px;
    z-index: 2147483646;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.15s ease-out;
    display: flex;
    gap: 14px;
    align-items: center;
  `;
  const attach = () => {{
    if (!document.body) {{ requestAnimationFrame(attach); return; }}
    document.body.appendChild(el);
  }};
  attach();
}})()"""


def generate_show_keys_script(labels: list[str]) -> str:
    """
    Generate JS that populates the HUD with key labels and makes it visible.

    Each label is rendered inside a <kbd>-style span.
    """
    spans = " + ".join(
        f"'<span class=\"__demo-key\">{label}</span>'"
        for label in labels
    )
    return f"""(() => {{
  const el = document.getElementById('__demo-keys');
  if (!el) return;
  el.innerHTML = {spans};
  el.style.opacity = '1';
}})()"""


def generate_hide_keys_script() -> str:
    """Generate JS that hides the HUD overlay."""
    return """(() => {
  const el = document.getElementById('__demo-keys');
  if (!el) return;
  el.style.opacity = '0';
})()"""


async def inject_hud_overlay(page: Page, theme: KeystrokeHudThemeModel) -> None:
    """Inject the HUD overlay element into the current page."""
    script = generate_hud_inject_script(theme)
    await page.evaluate(script)


async def show_keys(page: Page, labels: list[str]) -> None:
    """Show the given key labels in the HUD overlay."""
    script = generate_show_keys_script(labels)
    await page.evaluate(script)


async def hide_keys(page: Page) -> None:
    """Hide the HUD overlay."""
    script = generate_hide_keys_script()
    await page.evaluate(script)
