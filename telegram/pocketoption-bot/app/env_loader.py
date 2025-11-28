"""Environment variable loader for local CLI scripts."""

import os
from pathlib import Path
from typing import Optional


def load_local_env(env_filename: str = ".env") -> Optional[Path]:
    """
    Load environment variables from a .env file located in the
    pocketoption-bot directory, if present.

    This is primarily for local CLI usage (e.g., on Windows).
    Docker / prod still rely on their own env injection.

    Args:
        env_filename: Name of the .env file (default: ".env")

    Returns:
        Path to the loaded .env file if found, None otherwise
    """
    try:
        # env_loader.py is at:
        # <repo_root>/telegram/pocketoption-bot/app/env_loader.py
        # pocketoption-bot dir is parents[1]
        env_path = Path(__file__).resolve().parents[1] / env_filename
    except Exception:
        return None

    if not env_path.exists():
        return None

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
        return None

    return env_path

