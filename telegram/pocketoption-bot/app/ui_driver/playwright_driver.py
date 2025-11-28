"""Playwright-based UI driver for PocketOption automation."""

import sys
from typing import Optional

# Guarded import: Playwright is optional
try:
    from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
    SYNC_PLAYWRIGHT = sync_playwright
except ImportError:
    SYNC_PLAYWRIGHT = None

from app.config import PocketOptionBotConfig
from app.logging_config import get_logger

logger = get_logger("ui-driver")


class PocketOptionUIDriver:
    """Playwright-based UI driver for PocketOption automation."""
    
    def __init__(self, settings: PocketOptionBotConfig):
        """
        Initialize the UI driver.
        
        Args:
            settings: PocketOption bot configuration
            
        Raises:
            RuntimeError: If Playwright is not installed or required settings are missing
        """
        if SYNC_PLAYWRIGHT is None:
            raise RuntimeError(
                "Playwright is not installed. Install 'playwright' and run 'playwright install'."
            )
        
        self.settings = settings
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    def login(self) -> None:
        """
        Perform login to PocketOption.
        
        Raises:
            RuntimeError: If required settings are missing or login fails
        """
        # Validate required settings
        required_settings = {
            "POCKETOPTION_LOGIN_URL": self.settings.login_url,
            "POCKETOPTION_USERNAME": self.settings.username,
            "POCKETOPTION_PASSWORD": self.settings.password,
            "POCKETOPTION_SELECTOR_USERNAME": self.settings.selector_username,
            "POCKETOPTION_SELECTOR_PASSWORD": self.settings.selector_password,
            "POCKETOPTION_SELECTOR_LOGIN_BUTTON": self.settings.selector_login_button,
        }
        
        missing = [key for key, value in required_settings.items() if not value]
        if missing:
            error_msg = f"Missing required UI settings: {', '.join(missing)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.info("Starting PocketOption login", extra={"login_url": self.settings.login_url})
        
        try:
            with SYNC_PLAYWRIGHT() as playwright:
                # Launch browser
                logger.info("Launching browser", extra={"headless": self.settings.headless})
                self.browser = playwright.chromium.launch(headless=self.settings.headless)
                
                # Create context
                self.context = self.browser.new_context()
                self.page = self.context.new_page()
                
                # Navigate to login page
                logger.info("Navigating to login page", extra={"url": self.settings.login_url})
                self.page.goto(self.settings.login_url)
                
                # Wait for page to load
                self.page.wait_for_load_state("networkidle")
                
                # Fill username
                logger.info("Filling username field", extra={"selector": self.settings.selector_username})
                self.page.fill(self.settings.selector_username, self.settings.username)
                
                # Fill password
                logger.info("Filling password field", extra={"selector": self.settings.selector_password})
                self.page.fill(self.settings.selector_password, self.settings.password)
                
                # Click login button
                logger.info("Clicking login button", extra={"selector": self.settings.selector_login_button})
                self.page.click(self.settings.selector_login_button)
                
                # Wait for post-login condition (simple timeout + URL check)
                logger.info("Waiting for login to complete")
                self.page.wait_for_timeout(2000)  # Wait 2 seconds for redirect/navigation
                
                # Check if URL changed (simple success indicator)
                current_url = self.page.url
                logger.info("Login completed", extra={"current_url": current_url})
                
                # Simple success check: URL should change from login page
                if "login" not in current_url.lower():
                    logger.info("PocketOption UI login successful")
                else:
                    logger.warning("Login may have failed - still on login page", extra={"url": current_url})
                
        except Exception as e:
            logger.error("PocketOption UI login failed", extra={"error": str(e)}, exc_info=True)
            raise
        finally:
            # Cleanup
            if self.page:
                try:
                    self.page.close()
                except Exception:
                    pass
            if self.context:
                try:
                    self.context.close()
                except Exception:
                    pass
            if self.browser:
                try:
                    self.browser.close()
                except Exception:
                    pass

