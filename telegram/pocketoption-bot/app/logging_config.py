"""Logging configuration for pocketoption-bot service."""

import sys
from pathlib import Path

# Ensure repo root (the directory that contains 'common') is on sys.path
_here = Path(__file__).resolve()
# logging_config.py is at: <repo_root>/telegram/pocketoption-bot/app/logging_config.py
# So repo root should be three levels up: parents[3] -> <repo_root>
_repo_root = _here.parents[3]
if (_repo_root / "common").exists():
    repo_root_str = str(_repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

from common.utils.logging import get_logger

__all__ = ["get_logger"]

