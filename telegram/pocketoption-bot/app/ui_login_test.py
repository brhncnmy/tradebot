"""CLI script to test PocketOption UI login."""

import os
import sys
from pathlib import Path

from app.config import get_settings
from app.logging_config import get_logger
from app.ui_driver.playwright_driver import PocketOptionUIDriver

logger = get_logger("ui-login-test")


def load_local_env() -> None:
    """
    Load environment variables from a .env file located in the
    pocketoption-bot directory, if present.

    This is primarily for local CLI usage (e.g., on Windows).
    Docker / prod still rely on their own env injection.
    """
    try:
        # ui_login_test.py is at:
        # <repo_root>/telegram/pocketoption-bot/app/ui_login_test.py
        # pocketoption-bot dir is parents[1]
        env_path = Path(__file__).resolve().parents[1] / ".env"
    except Exception:
        return

    if not env_path.exists():
        return

    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if not key:
                continue
            # Do not override existing env vars; Docker / shell should win.
            if key not in os.environ:
                os.environ[key] = value
    except Exception:
        # Fail silently here; any missing keys will be handled by settings validation.
        return


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
            success_msg = "PocketOption UI login successful."
            print(success_msg)
            logger.info(success_msg)
            return 0
        except Exception as e:
            error_msg = f"PocketOption UI login failed: {e}"
            print(error_msg, file=sys.stderr)
            logger.error(error_msg, exc_info=True)
            return 1
            
    except Exception as e:
        error_msg = f"Unexpected error during UI login test: {e}"
        print(error_msg, file=sys.stderr)
        logger.error(error_msg, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

