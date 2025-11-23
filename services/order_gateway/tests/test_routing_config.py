"""Tests for routing configuration."""

from common.utils.config import get_routing_profile


def test_default_routing_uses_bingx_vst_demo():
    """Test that default routing profile uses bingx_vst_demo account."""
    accounts = get_routing_profile("default")
    account_ids = [acc.account_id for acc in accounts]
    
    assert "bingx_vst_demo" in account_ids
    assert "bingx_primary" not in account_ids
    assert len(accounts) == 1
    assert accounts[0].account_id == "bingx_vst_demo"
    assert accounts[0].mode == "demo"
    assert accounts[0].api_key_env == "BINGX_VST_API_KEY"
    assert accounts[0].secret_key_env == "BINGX_VST_API_SECRET"

