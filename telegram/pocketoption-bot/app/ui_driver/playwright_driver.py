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
                
                # Navigate to login page with tolerant wait strategy
                logger.info("Navigating to login page", extra={"url": self.settings.login_url})
                self.page.goto(
                    self.settings.login_url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
                
                # Give the page a brief moment to settle (SPAs / analytics can keep network busy)
                logger.info("Waiting for page to settle")
                self.page.wait_for_timeout(1000)
                
                # Optional: try to wait for networkidle with short timeout, but don't fail if it times out
                try:
                    self.page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    logger.info("networkidle not reached, continuing anyway")
                
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
                    logger.info("PocketOption UI login flow executed successfully")
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
    
    def prepare_asset(self, asset: str) -> None:
        """
        Optionally ensure the given asset is selected in the UI.
        
        Args:
            asset: Asset symbol to prepare (e.g., "GBP/USD OTC")
            
        Raises:
            RuntimeError: If selector is not configured
        """
        logger.info("Preparing asset", extra={"asset": asset})
        
        if not self.settings.selector_asset_field:
            logger.warning("POCKETOPTION_SELECTOR_ASSET_FIELD not configured, skipping asset preparation")
            raise RuntimeError("POCKETOPTION_SELECTOR_ASSET_FIELD not configured")
        
        # Note: This assumes browser/page is already initialized (e.g., after login)
        # For now, this is a stub that logs the action
        # Full implementation would use page.fill() or page.select_option() based on DOM structure
        logger.info("Asset preparation requested", extra={"asset": asset, "selector": self.settings.selector_asset_field})
    
    def place_entry_trade(
        self,
        asset: str,
        duration_minutes: int,
        direction: "PocketOptionDirection",
        stake: float,
    ) -> None:
        """
        Place a single ENTRY trade on PocketOption UI using configured selectors.
        
        Args:
            asset: Asset symbol (e.g., "GBP/USD OTC")
            duration_minutes: Trade duration in minutes
            direction: Trade direction (UP/DOWN)
            stake: Trade stake amount
            
        Raises:
            RuntimeError: If required selectors are missing or trade execution fails
        """
        from app.models.pocketoption import PocketOptionDirection
        
        logger.info(
            "Placing ENTRY trade via UI",
            extra={
                "asset": asset,
                "duration_minutes": duration_minutes,
                "direction": direction.value if direction else None,
                "stake": stake,
            }
        )
        
        # Validate required selectors (BUY/SELL buttons act as both direction and place-trade)
        required_selectors = {
            "POCKETOPTION_SELECTOR_ASSET_FIELD": self.settings.selector_asset_field,
            "POCKETOPTION_SELECTOR_DURATION_FIELD": self.settings.selector_duration_field,
            "POCKETOPTION_SELECTOR_STAKE_FIELD": self.settings.selector_stake_field,
            "POCKETOPTION_SELECTOR_DIRECTION_UP": self.settings.selector_direction_up,
            "POCKETOPTION_SELECTOR_DIRECTION_DOWN": self.settings.selector_direction_down,
        }
        
        missing = [key for key, value in required_selectors.items() if not value]
        if missing:
            error_msg = f"Missing required trading selectors: {', '.join(missing)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        browser: Optional[Browser] = None
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None
        
        try:
            with SYNC_PLAYWRIGHT() as playwright:
                # Launch browser
                logger.info("Launching browser for trade execution", extra={"headless": self.settings.headless})
                browser = playwright.chromium.launch(headless=self.settings.headless)
                
                # Create context
                context = browser.new_context()
                page = context.new_page()
                
                # Navigate to trading page (assume authenticated session or navigate to main page)
                # For now, use login URL as base and assume redirect after login
                # This can be refined later with a dedicated trading URL
                trading_url = self.settings.login_url.replace("/login/", "/") if "/login/" in self.settings.login_url else "https://pocketoption.com/en/"
                logger.info("Navigating to trading page", extra={"url": trading_url})
                page.goto(
                    trading_url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
                page.wait_for_timeout(1000)  # Give page time to settle
                
                # Asset selection: click asset field to open panel, then search and select
                logger.info("Selecting asset", extra={"asset": asset, "selector": self.settings.selector_asset_field})
                page.click(self.settings.selector_asset_field)
                page.wait_for_timeout(500)  # Wait for asset panel to open
                
                # Search for asset using placeholder or generic search
                try:
                    search_locator = page.get_by_placeholder("Search")
                    search_locator.click()
                    search_locator.fill(asset)
                    page.wait_for_timeout(300)
                except Exception:
                    # Fallback: try to find search input by other means
                    logger.warning("Could not find search placeholder, attempting alternative search")
                
                # Select the asset from the list by text
                page.get_by_text(asset).first.click()
                page.wait_for_timeout(500)
                
                # Duration: click duration field and select preset (e.g., M5 for 5 minutes)
                logger.info("Setting duration", extra={"duration_minutes": duration_minutes, "selector": self.settings.selector_duration_field})
                page.click(self.settings.selector_duration_field)
                page.wait_for_timeout(200)
                
                # Map duration to preset labels (TODO: make this configurable)
                if duration_minutes == 5:
                    page.get_by_text("M5").click()
                elif duration_minutes == 1:
                    page.get_by_text("M1").click()
                elif duration_minutes == 15:
                    page.get_by_text("M15").click()
                elif duration_minutes == 30:
                    page.get_by_text("M30").click()
                else:
                    logger.warning(
                        "Unsupported duration, attempting to proceed without changing",
                        extra={"duration_minutes": duration_minutes}
                    )
                page.wait_for_timeout(200)
                
                # Stake: click amount field and fill
                logger.info("Setting stake", extra={"stake": stake, "selector": self.settings.selector_stake_field})
                stake_locator = page.locator(self.settings.selector_stake_field)
                stake_locator.click()
                stake_locator.fill(str(stake))
                page.wait_for_timeout(500)
                
                # Direction & place-trade: BUY/SELL buttons act as both direction and place-trade
                if direction in (PocketOptionDirection.UP, PocketOptionDirection.CALL, PocketOptionDirection.HIGHER):
                    logger.info("Clicking UP (BUY) button (direction + place trade)", extra={"selector": self.settings.selector_direction_up})
                    page.click(self.settings.selector_direction_up)
                elif direction in (PocketOptionDirection.DOWN, PocketOptionDirection.PUT, PocketOptionDirection.LOWER):
                    logger.info("Clicking DOWN (SELL) button (direction + place trade)", extra={"selector": self.settings.selector_direction_down})
                    page.click(self.settings.selector_direction_down)
                else:
                    raise RuntimeError(f"Unsupported direction: {direction}")
                
                # Wait for trade confirmation
                page.wait_for_timeout(1000)
                
                logger.info(
                    "ENTRY trade placed via UI",
                    extra={
                        "asset": asset,
                        "duration_minutes": duration_minutes,
                        "direction": direction.value if direction else None,
                        "stake": stake,
                    }
                )
                
        except Exception as e:
            logger.error("Failed to place ENTRY trade via UI", extra={"error": str(e)}, exc_info=True)
            raise RuntimeError(f"UI trade execution failed: {e}") from e
        finally:
            # Cleanup
            if page:
                try:
                    page.close()
                except Exception:
                    pass
            if context:
                try:
                    context.close()
                except Exception:
                    pass
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass

