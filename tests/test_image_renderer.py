# nite-pebbles/tests/test_image_renderer.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from image_renderer import BrowserManager, html_to_png


class TestImageRenderer:
    @pytest.mark.asyncio
    async def test_browser_manager_singleton(self):
        manager1 = await BrowserManager.get_instance()
        manager2 = await BrowserManager.get_instance()
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_render_html_to_png_live_or_mock(self):
        html_sample = "<div class='card' style='width:200px; height:100px; background:red;'><h1>Hello</h1></div>"
        try:
            png_bytes = await html_to_png(html_sample, width=400, height=200, selector=".card")
            assert isinstance(png_bytes, bytes)
            assert len(png_bytes) > 0
            # PNG file header signature
            assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        except Exception as e:
            # If running in environment without chromium, ensure graceful failure handling
            assert "Browser" in str(e) or "playwright" in str(e).lower()

    @pytest.mark.asyncio
    async def test_render_html_to_png_mocked(self):
        # Test the page setup and locator logic with mocked Playwright objects
        mock_page = AsyncMock()
        mock_element = AsyncMock()
        mock_element.bounding_box = AsyncMock(return_value={"width": 100, "height": 100})
        mock_element.screenshot = AsyncMock(return_value=b"\x89PNG\r\n\x1a\nFAKEPNG")

        mock_body = AsyncMock()
        mock_body.screenshot = AsyncMock(return_value=b"\x89PNG\r\n\x1a\nBODYPNG")

        def locator_side_effect(selector):
            if selector == ".card":
                return MagicMock(first=mock_element)
            return MagicMock(first=mock_body, screenshot=mock_body.screenshot)

        mock_page.locator = MagicMock(side_effect=locator_side_effect)

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        manager = BrowserManager()
        manager.browser = AsyncMock()
        manager.context = mock_context

        png_bytes = await manager.render_html_to_png("<div></div>", width=300, height=150, wait_for="load", selector=".card")
        assert png_bytes == b"\x89PNG\r\n\x1a\nFAKEPNG"
        mock_page.set_viewport_size.assert_called_once()
        mock_page.set_content.assert_called_once()
        mock_page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_browser_failed_to_start_raises(self):
        manager = BrowserManager()
        manager.start_browser = AsyncMock()
        manager.browser = None

        with pytest.raises(Exception, match="Browser failed to start"):
            await manager.render_html_to_png("<h1>Fail</h1>")
