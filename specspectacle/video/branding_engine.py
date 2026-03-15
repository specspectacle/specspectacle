"""
HTML/CSS Branding Engine for SpecSpectacle.
Renders branding frames (intro, outro, overlays) using Playwright and Jinja2 templates.
"""

import logging
from pathlib import Path
from typing import Any

import jinja2
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class TemplateRenderer:
    """
    Renders HTML/CSS templates to high-resolution images using Playwright.
    """

    def __init__(self, templates_dir: Path | None = None):
        """
        Initialize the template renderer.

        Args:
            templates_dir: Directory containing HTML templates.
        """
        if templates_dir is None:
            # Default templates directory relative to this file
            templates_dir = Path(__file__).parent / "templates"

        self.templates_dir = Path(templates_dir)
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.templates_dir)),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )

    async def render_to_file(
        self,
        template_name: str,
        context: dict[str, Any],
        output_path: Path,
        viewport_size: dict[str, int] = None
    ) -> Path:
        """
        Render a template and take a screenshot.

        Args:
            template_name: Name of the template file in templates_dir.
            context: Data to pass to the Jinja2 template.
            output_path: Where to save the resulting screenshot.
            viewport_size: Viewport resolution (width, height).

        Returns:
            Path to the saved image.
        """
        if viewport_size is None:
            viewport_size = {"width": 1920, "height": 1080}
        logger.info(f"Rendering branding template {template_name} to {output_path}")

        # 1. Render HTML with Jinja2
        template = self.env.get_template(template_name)
        html_content = template.render(**context)

        # 2. Use Playwright to capture the frame
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context_browser = await browser.new_context(
                viewport=viewport_size,
                device_scale_factor=2  # High resolution
            )
            page = await context_browser.new_page()

            # Use data URI or temporary file
            # Data URI is simpler for small HTML
            import base64
            html_b64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
            data_uri = f"data:text/html;base64,{html_b64}"

            await page.goto(data_uri)
            # Wait for any fonts/images to load if possible
            # Since we use data URIs for images in context usually, it's fast
            await page.wait_for_load_state("networkidle")

            # Take full page screenshot
            await page.screenshot(path=str(output_path), full_page=True, omit_background=True)

            await browser.close()

        return output_path

class BrandingEngine:
    """
    Higher-level engine to manage branding lifecycle and MoviePy integration.
    """

    def __init__(self, templates_dir: Path | None = None):
        self.renderer = TemplateRenderer(templates_dir)

    async def generate_intro_outro(
        self,
        branding_config: Any,
        intro_text: str,
        outro_text: str,
        output_dir: Path,
        resolution: str = "1280x720"
    ) -> dict[str, Path]:
        """
        Generate intro and outro images based on branding config.
        """
        width, height = map(int, resolution.split("x"))
        viewport = {"width": width, "height": height}

        results = {}

        # Prepare context
        common_context = {
            "primary_color": getattr(branding_config, "primary_color", "#3b82f6"),
            "text_color": getattr(branding_config, "text_color", "#ffffff"),
            "background_color": getattr(branding_config, "background_color", "#0f172a"),
            "logo_url": None
        }

        # Convert local logo path to base64 URI if exists
        logo_path = getattr(branding_config, "logo", None)
        if logo_path:
            logo_abs = Path(logo_path).absolute()
            if logo_abs.exists():
                import base64
                import mimetypes
                
                mime_type, _ = mimetypes.guess_type(str(logo_abs))
                if not mime_type:
                    mime_type = "image/png"
                    
                with open(logo_abs, "rb") as f:
                    logo_b64 = base64.b64encode(f.read()).decode("utf-8")
                    common_context["logo_url"] = f"data:{mime_type};base64,{logo_b64}"

        # Generate Intro
        intro_path = output_dir / "branding_intro.png"
        intro_context = {**common_context, "title": intro_text}
        await self.renderer.render_to_file("default-theme.html", intro_context, intro_path, viewport)
        results["intro"] = intro_path

        # Generate Outro
        outro_path = output_dir / "branding_outro.png"
        outro_context = {**common_context, "title": outro_text}
        await self.renderer.render_to_file("default-theme.html", outro_context, outro_path, viewport)
        results["outro"] = outro_path

        return results
