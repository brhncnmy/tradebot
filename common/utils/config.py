import os
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel


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

def _default_profile_accounts() -> List[str]:
    """Build default routing profile account list, enabling secondary demo if credentials exist."""
    account_ids = ["bingx_vst_demo"]
    # Add secondary account if credentials are present
    if os.getenv("BINGX_SECOND_API_KEY") and os.getenv("BINGX_SECOND_SECRET_KEY"):
        account_ids.append("bingx_vst_demo_secondary")
    return account_ids


# In-memory routing profiles
_routing_profiles: Dict[str, List[str]] = {
    "default": _default_profile_accounts()
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
    
    Args:
        name: Routing profile name
        
    Returns:
        List of AccountConfig instances
        
    Raises:
        ValueError: If profile name is not found or has no accounts
    """
    if name not in _routing_profiles:
        raise ValueError(f"Unknown routing profile: {name}")
    
    account_ids = _routing_profiles[name]
    if not account_ids:
        raise ValueError(f"Routing profile '{name}' has no accounts configured")
    
    return [get_account(acc_id) for acc_id in account_ids]
