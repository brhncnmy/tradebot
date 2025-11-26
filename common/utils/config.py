import os
from typing import Dict, List, Literal, Optional, Tuple

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
    # Optional: list of (api_key_env, secret_key_env) pairs to try in order
    # If provided, this takes precedence over api_key_env/secret_key_env
    env_pairs: Optional[List[Tuple[str, str]]] = None
    
    def get_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get API credentials for this account.
        
        Returns:
            Tuple of (api_key, secret_key) or (None, None) if not found
        """
        if self.env_pairs:
            for api_key_env, secret_key_env in self.env_pairs:
                api_key = os.getenv(api_key_env)
                secret_key = os.getenv(secret_key_env)
                if api_key and secret_key:
                    return api_key, secret_key
            return None, None
        if self.api_key_env and self.secret_key_env:
            api_key = os.getenv(self.api_key_env)
            secret_key = os.getenv(self.secret_key_env)
            return api_key, secret_key
        return None, None


# In-memory account registry
_accounts: Dict[str, AccountConfig] = {
    "bingx_primary": AccountConfig(
        account_id="bingx_primary",
        exchange="bingx",
        mode="test",  # Test mode: uses /order/test endpoint (no real orders)
        # Try numeric scheme first (BINGX_3_*), then fall back to legacy (BINGX_*)
        env_pairs=[
            ("BINGX_3_API_KEY", "BINGX_3_API_SECRET"),
            ("BINGX_API_KEY", "BINGX_API_SECRET"),
        ],
        source_key_env=None,  # Optional, not in .env by default
    ),
    "bingx_1": AccountConfig(
        account_id="bingx_1",
        exchange="bingx",
        mode="demo",  # Demo mode: uses VST host with virtual USDT
        api_key_env="BINGX_1_API_KEY",
        secret_key_env="BINGX_1_API_SECRET",
        source_key_env=None,  # Optional, not in .env by default
        supports_reduce_only=False,
    ),
    "bingx_2": AccountConfig(
        account_id="bingx_2",
        exchange="bingx",
        mode="demo",  # Demo mode: uses VST host with virtual USDT
        api_key_env="BINGX_2_API_KEY",
        secret_key_env="BINGX_2_API_SECRET",
        source_key_env=None,  # Optional, not in .env by default
        supports_reduce_only=False,
    )
}

def _is_account_available(account_id: str) -> bool:
    """Check if an account has required credentials available."""
    if account_id not in _accounts:
        return False
    account = _accounts[account_id]
    api_key, secret_key = account.get_credentials()
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
    "demo_1": ["bingx_1"],
    "demo_2": ["bingx_2"],
    "demo_1_2": ["bingx_1", "bingx_2"],
    "default": ["bingx_1"],  # default behaves like demo_1
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
    
    Resolves 'default' to 'demo_1' behavior.
    Filters accounts by availability (credentials present).
    
    Args:
        name: Routing profile name (e.g., "demo_1", "demo_2", "demo_1_2", "default")
        
    Returns:
        List of AccountConfig instances (only accounts with available credentials)
        
    Raises:
        ValueError: If profile name is not found
    """
    # Resolve 'default' to 'demo_1' behavior
    if name == "default":
        name = "demo_1"
    
    # Rebuild profile dynamically to account for current environment
    if name not in _routing_profile_definitions:
        raise ValueError(f"Unknown routing profile: {name}")
    
    # Filter by availability
    account_ids = _get_available_accounts(_routing_profile_definitions[name])
    
    # Return account configs (empty list if no accounts available)
    return [get_account(acc_id) for acc_id in account_ids]
