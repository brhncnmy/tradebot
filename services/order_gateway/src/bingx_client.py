import hashlib
import hmac
import time
from typing import Any, Dict

import httpx

from common.models.order_request import OpenOrderRequest
from common.utils.logging import get_logger

logger = get_logger("bingx-client")


class BingxClient:
    """Client for BingX USDT-M Perpetual Futures API."""
    
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        base_url: str = "https://open-api.bingx.com",
        source_key: str | None = None
    ) -> None:
        """
        Initialize BingX client.
        
        Args:
            api_key: BingX API key
            secret_key: BingX secret key
            base_url: Base URL for BingX API
            source_key: Optional source key for API requests
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self.source_key = source_key
    
    def _build_query(self, params: Dict[str, Any]) -> str:
        """
        Build query string from parameters.
        
        Args:
            params: Dictionary of parameters
            
        Returns:
            Query string in format "key1=value1&key2=value2"
        """
        items = sorted(params.items())
        return "&".join(f"{k}={v}" for k, v in items)
    
    def _sign(self, query: str) -> str:
        """
        Sign query string using HMAC-SHA256.
        
        Args:
            query: Query string to sign
            
        Returns:
            Hexadecimal signature
        """
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    async def create_perpetual_order(self, order: OpenOrderRequest) -> Dict[str, Any]:
        """
        Create a perpetual futures order on BingX.
        
        Args:
            order: OpenOrderRequest with order details
            
        Returns:
            Response data from BingX API
            
        Raises:
            RuntimeError: If API returns an error code
            httpx.HTTPError: If HTTP request fails
        """
        path = "/openApi/swap/v2/trade/order"
        
        # Build BingX parameters
        params: Dict[str, Any] = {
            "symbol": order.symbol,
            "side": "BUY" if order.side == "long" else "SELL",
            "positionSide": "BOTH",
            "type": "MARKET" if order.entry_type == "market" else "LIMIT",
            "quantity": order.quantity,
        }
        
        # Add price for limit orders
        if order.price is not None and order.entry_type == "limit":
            params["price"] = order.price
        
        # Add leverage if provided
        if order.leverage is not None:
            params["leverage"] = str(int(order.leverage))
        
        # Add timestamp
        params["timestamp"] = int(time.time() * 1000)
        
        # Build query string and sign
        query = self._build_query(params)
        signature = self._sign(query)
        
        # Build full URL
        url = f"{self.base_url}{path}?{query}&signature={signature}"
        
        # Build headers
        headers = {
            "X-BX-APIKEY": self.api_key
        }
        if self.source_key:
            headers["X-SOURCE-KEY"] = self.source_key
        
        # Make request
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API error codes
            code = data.get("code")
            if code not in (0, "0"):
                error_msg = data.get("msg") or data.get("message", "Unknown error")
                logger.error(f"BingX API error: code={code}, message={error_msg}")
                raise RuntimeError(f"BingX API error: {error_msg} (code: {code})")
            
            return data

