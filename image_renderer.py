import asyncio
import os
from playwright.async_api import async_playwright
import traceback
import io

class BrowserManager:
    _instance = None
    _lock = asyncio.Lock()

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None

    @classmethod
    async def get_instance(cls):
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def start_browser(self):
        if self.browser:
            return

        print("[BrowserManager] Starting persistent Chromium instance...")
        try:
            self.playwright = await async_playwright().start()
            
            # Optimized for Jetson ARM64
            executable_path = "/usr/bin/chromium"
            if not os.path.exists(executable_path):
                executable_path = "/usr/bin/chromium-browser"
            
            self.browser = await self.playwright.chromium.launch(
                executable_path=executable_path if os.path.exists(executable_path) else None,
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-first-run',
                    '--no-zygote',
                    '--js-flags="--max-old-space-size=256"', 
                ]
            )
            # Default context
            self.context = await self.browser.new_context()
            print("[BrowserManager] Browser started successfully.")
        except Exception as e:
            print(f"[BrowserManager] Failed to start browser: {e}")
            traceback.print_exc()
            await self.stop_browser()

    async def stop_browser(self):
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()
        self.browser = None
        self.context = None
        self.playwright = None

    async def render_html_to_png(self, html: str, width: int = 800, height: int = 550, wait_for: str = "networkidle", selector: str = "body") -> bytes:
        """
        Renders HTML to PNG bytes. 
        Automatically handles browser startup and page cleanup.
        Captures the specified selector (default: body) to avoid extra space.
        """
        if not self.browser:
            await self.start_browser()
        
        if not self.browser:
            raise Exception("Browser failed to start.")

        # Create a new page for each render to avoid state leakage
        page = await self.context.new_page()
        try:
            # Set a large enough viewport height to avoid scrolling issues during layout
            await page.set_viewport_size({"width": width, "height": max(height, 3000)})
            await page.set_content(html, wait_until=wait_for)
            
            # Give a bit of extra time for fonts/images to finish rendering
            if wait_for == "networkidle":
                await asyncio.sleep(0.8)
                
            # Attempt to find the specific element
            try:
                element = page.locator(selector).first
                # Check if element actually has a size
                box = await element.bounding_box()
                if box and (box['width'] > 0 and box['height'] > 0):
                    # omit_background=True ensures we don't get browser default white bleeding through
                    screenshot_bytes = await element.screenshot(type="png", omit_background=True)
                else:
                    # Fallback to body if selector invalid or zero-sized
                    screenshot_bytes = await page.locator("body").screenshot(type="png", omit_background=True)
            except Exception:
                # Absolute fallback
                screenshot_bytes = await page.locator("body").screenshot(type="png", omit_background=True)
                
            return screenshot_bytes
        finally:
            await page.close()

async def html_to_png(html: str, width: int = 800, height: int = 550, wait_for: str = "networkidle", selector: str = "body") -> bytes:
    manager = await BrowserManager.get_instance()
    return await manager.render_html_to_png(html, width, height, wait_for, selector)
