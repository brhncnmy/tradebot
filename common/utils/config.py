from typing import Dict, List, Literal, Optional

from pydantic import BaseModel


class AccountConfig(BaseModel):
    """Trading account configuration."""
    account_id: str
    exchange: str
    mode: Literal["DRY_RUN", "LIVE"]
    api_key_env: Optional[str] = None
    secret_key_env: Optional[str] = None
    source_key_env: Optional[str] = None


# In-memory account registry
_accounts: Dict[str, AccountConfig] = {
    "bingx_primary": AccountConfig(
        account_id="bingx_primary",
        exchange="bingx",
        mode="DRY_RUN",
        api_key_env="BINGX_PRIMARY_API_KEY",
        secret_key_env="BINGX_PRIMARY_SECRET_KEY",
        source_key_env="BINGX_PRIMARY_SOURCE_KEY"
    )
}

# In-memory routing profiles
_routing_profiles: Dict[str, List[str]] = {
    "default": ["bingx_primary"]
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
