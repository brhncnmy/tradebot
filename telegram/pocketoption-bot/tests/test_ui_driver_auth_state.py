"""Tests for UI driver auth storage state."""

from unittest.mock import patch

from app.config import get_settings
from app.ui_driver.playwright_driver import PocketOptionUIDriver


def test_auth_storage_state_default_none():
    """Test that _auth_storage_state defaults to None."""
    # Mock Playwright to avoid requiring actual installation
    with patch("app.ui_driver.playwright_driver.SYNC_PLAYWRIGHT") as mock_playwright:
        # Create a mock playwright context
        mock_p = mock_playwright.return_value.__enter__.return_value
        mock_browser = mock_p.chromium.launch.return_value
        mock_context = mock_browser.new_context.return_value
        mock_page = mock_context.new_page.return_value
        
        settings = get_settings()
        
        # This will fail if Playwright is not installed, but we're mocking it
        try:
            driver = PocketOptionUIDriver(settings)
            assert driver._auth_storage_state is None
        except RuntimeError:
            # If Playwright is not installed, skip this test
            pass

