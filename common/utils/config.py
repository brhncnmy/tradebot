import os
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel

# Import logger for warnings (lazy import to avoid circular dependencies)
_logger = None


def _get_logger():
    """Lazy import logger to avoid circular dependencies."""
    global _logger
    if _logger is None:
        from common.utils.logging import get_logger
        _logger = get_logger("config")
    return _logger


class AccountConfig(BaseModel):
    """Trading account configuration."""
    account_id: str
    exchange: str
    mode: Literal["dry", "test", "demo", "live"] = "dry"
    api_key_env: Optional[str] = None
    secret_key_env: Optional[str] = None
    source_key_env: Optional[str] = None
    supports_reduce_only: bool = True


# In-memory account registry
_accounts: Dict[str, AccountConfig] = {
    "bingx_primary": AccountConfig(
        account_id="bingx_primary",
        exchange="bingx",
        mode="test",  # Test mode: uses /order/test endpoint (no real orders)
        api_key_env="BINGX_API_KEY",
        secret_key_env="BINGX_API_SECRET",
        source_key_env=None,  # Optional, not in .env by default
    ),
    "bingx_vst_demo": AccountConfig(
        account_id="bingx_vst_demo",
        exchange="bingx",
        mode="demo",  # Demo mode: uses VST host with virtual USDT
        api_key_env="BINGX_VST_API_KEY",
        secret_key_env="BINGX_VST_API_SECRET",
        source_key_env=None,  # Optional, not in .env by default
        supports_reduce_only=False,
    ),
    "bingx_vst_demo_secondary": AccountConfig(
        account_id="bingx_vst_demo_secondary",
        exchange="bingx",
        mode="demo",  # Demo mode: uses VST host with virtual USDT
        api_key_env="BINGX_SECOND_API_KEY",
        secret_key_env="BINGX_SECOND_SECRET_KEY",
        source_key_env=None,  # Optional, not in .env by default
        supports_reduce_only=False,
    )
}

def _is_account_available(account_id: str) -> bool:
    """Check if an account has required credentials available."""
    if account_id not in _accounts:
        return False
    account = _accounts[account_id]
    if not account.api_key_env or not account.secret_key_env:
        return False
    api_key = os.getenv(account.api_key_env)
    secret_key = os.getenv(account.secret_key_env)
    return bool(api_key and secret_key)


def _get_available_accounts(account_ids: List[str]) -> List[str]:
    """Filter account list to only include accounts with available credentials."""
    available = []
    logger = _get_logger()
    for acc_id in account_ids:
        if _is_account_available(acc_id):
            available.append(acc_id)
        else:
            logger.warning(
                "Skipping unavailable account: account=%s reason=credentials_missing",
                acc_id,
            )
    return available


# Routing profile definitions (before availability filtering)
_routing_profile_definitions: Dict[str, List[str]] = {
    "demo_primary_only": ["bingx_vst_demo"],
    "demo_secondary_only": ["bingx_vst_demo_secondary"],
    "demo_both": ["bingx_vst_demo", "bingx_vst_demo_secondary"],
    "default": ["bingx_vst_demo"],  # default behaves like demo_primary_only
}


def _build_routing_profile(profile_name: str) -> List[str]:
    """Build routing profile account list, filtering by availability."""
    if profile_name not in _routing_profile_definitions:
        return []
    account_ids = _routing_profile_definitions[profile_name]
    return _get_available_accounts(account_ids)


# In-memory routing profiles (dynamically built based on availability)
_routing_profiles: Dict[str, List[str]] = {
    name: _build_routing_profile(name) for name in _routing_profile_definitions.keys()
}


def get_account(account_id: str) -> AccountConfig:
    """
    Get account configuration by ID.
    
    Args:
        account_id: Account identifier
        
    Returns:
        AccountConfig instance
        
    Raises:
        ValueError: If account_id is not found
    """
    if account_id not in _accounts:
        raise ValueError(f"Unknown account_id: {account_id}")
    return _accounts[account_id]


def get_routing_profile(name: str) -> List[AccountConfig]:
    """
    Get list of account configs for a routing profile.
    
    Resolves 'default' to 'demo_primary_only' behavior.
    Filters accounts by availability (credentials present).
    
    Args:
        name: Routing profile name (e.g., "demo_primary_only", "demo_both", "default")
        
    Returns:
        List of AccountConfig instances (only accounts with available credentials)
        
    Raises:
        ValueError: If profile name is not found
    """
    # Resolve 'default' to 'demo_primary_only' behavior
    if name == "default":
        name = "demo_primary_only"
    
    # Rebuild profile dynamically to account for current environment
    if name not in _routing_profile_definitions:
        raise ValueError(f"Unknown routing profile: {name}")
    
    # Filter by availability
    account_ids = _get_available_accounts(_routing_profile_definitions[name])
    
    # Return account configs (empty list if no accounts available)
    return [get_account(acc_id) for acc_id in account_ids]
