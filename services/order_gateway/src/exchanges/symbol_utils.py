"""Symbol mapping utilities for exchange-specific formats."""


def to_bingx_symbol(normalized_symbol: str) -> str:
    """
    Convert a normalized symbol like 'BTCUSDT' or 'LIGHTUSDT' into
    BingX format 'BTC-USDT' / 'LIGHT-USDT'.
    
    For now, handle USDT and USDC by inserting a '-' before the quote asset.
    If the symbol already contains a '-', return it unchanged.
    If the pattern does not match, return the original symbol.
    
    Args:
        normalized_symbol: Normalized symbol (e.g., "BTCUSDT", "LIGHTUSDT", "BTC-USDT")
        
    Returns:
        BingX-formatted symbol (e.g., "BTC-USDT", "LIGHT-USDT")
    """
    # If already formatted (contains '-'), return as-is
    if "-" in normalized_symbol:
        return normalized_symbol
    
    # Try to insert '-' before quote asset
    for quote in ("USDT", "USDC"):
        if normalized_symbol.endswith(quote) and len(normalized_symbol) > len(quote):
            base = normalized_symbol[:-len(quote)]
            return f"{base}-{quote}"
    return normalized_symbol

