"""CLI script to test PocketOption UI login."""

import sys

from app.config import get_settings
from app.env_loader import load_local_env
from app.logging_config import get_logger
from app.ui_driver.playwright_driver import PocketOptionUIDriver

logger = get_logger("ui-login-test")


def main() -> int:
    """Main entry point for UI login test."""
    try:
        load_local_env()
        settings = get_settings()
        
        # Check if UI is enabled
        if not settings.ui_enabled:
            error_msg = (
                "POCKETOPTION_UI_ENABLED is false; enable it in .env to run UI login test."
            )
            print(error_msg, file=sys.stderr)
            logger.error(error_msg)
            return 1
        
        # Attempt to create driver
        try:
            driver = PocketOptionUIDriver(settings)
        except RuntimeError as e:
            error_msg = f"Failed to create UI driver: {e}"
            print(error_msg, file=sys.stderr)
            logger.error(error_msg)
            return 1
        
        # Attempt login
        try:
            driver.login()
        except RuntimeError as e:
            error_msg = f"PocketOption UI login failed: {e}"
            print(error_msg, file=sys.stderr)
            logger.error(error_msg)
            return 1
        except Exception as e:
            error_msg = f"PocketOption UI login failed: {e}"
            print(error_msg, file=sys.stderr)
            logger.error(error_msg, exc_info=True)
            return 1
        
        success_msg = "PocketOption UI login successful."
        print(success_msg)
        logger.info(success_msg)
        return 0
            
    except Exception as e:
        error_msg = f"Unexpected error during UI login test: {e}"
        print(error_msg, file=sys.stderr)
        logger.error(error_msg, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

