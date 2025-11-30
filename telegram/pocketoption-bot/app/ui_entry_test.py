"""CLI script to test PocketOption UI entry trade placement."""

import sys

from app.config import get_settings
from app.env_loader import load_local_env
from app.logging_config import get_logger
from app.models.pocketoption import PocketOptionDirection
from app.ui_driver.playwright_driver import PocketOptionUIDriver

logger = get_logger("ui-entry-test")


def main() -> int:
    """Main entry point for UI entry test."""
    try:
        # Load .env for local CLI usage
        load_local_env()

        settings = get_settings()

        # Simple sanity check: make sure UI is enabled
        if not settings.ui_enabled:
            msg = "POCKETOPTION_UI_ENABLED is false; enable it in .env to run UI entry test."
            logger.error(msg)
            print(msg, file=sys.stderr)
            return 1

        logger.info("Creating PocketOptionUIDriver")
        try:
            driver = PocketOptionUIDriver(settings)
        except RuntimeError as e:
            error_msg = f"Failed to create UI driver: {e}"
            print(error_msg, file=sys.stderr)
            logger.error(error_msg)
            return 1

        # 1) Login
        logger.info("Starting login flow")
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
        
        logger.info("Login successful")

        # 2) Place a single ENTRY trade
        asset = "GBP/USD OTC"
        duration_minutes = 5
        direction = PocketOptionDirection.DOWN  # LOWER maps to DOWN
        stake = 1.0  # demo stake

        logger.info(
            "Placing ENTRY trade",
            extra={
                "asset": asset,
                "duration_minutes": duration_minutes,
                "direction": direction.value,
                "stake": stake,
            }
        )

        try:
            driver.place_entry_trade(
                asset=asset,
                duration_minutes=duration_minutes,
                direction=direction,
                stake=stake,
            )
            logger.info("ENTRY trade flow executed successfully")
            print("PocketOption UI entry test completed.")
            return 0
        except Exception as e:
            error_msg = f"PocketOption UI entry trade failed: {e}"
            print(error_msg, file=sys.stderr)
            logger.error(error_msg, exc_info=True)
            return 1

    except Exception as e:
        error_msg = f"Unexpected error during UI entry test: {e}"
        print(error_msg, file=sys.stderr)
        logger.error(error_msg, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

