"""Tests for routing configuration."""

import importlib
import os

import pytest

from common.utils import config as config_module


def _reload_config(monkeypatch, enable_second: bool, primary_legacy: bool = False, primary_numeric: bool = False):
    """Reload config module with desired env setup."""
    # Set primary account credentials (legacy or numeric)
    if primary_numeric:
        monkeypatch.setenv("BINGX_1_API_KEY", "demo_key_primary")
        monkeypatch.setenv("BINGX_1_API_SECRET", "demo_secret_primary")
    elif primary_legacy:
        monkeypatch.setenv("BINGX_VST_API_KEY", "demo_key_primary")
        monkeypatch.setenv("BINGX_VST_API_SECRET", "demo_secret_primary")
    
    if enable_second:
        monkeypatch.setenv("BINGX_SECOND_API_KEY", "demo_key_secondary")
        monkeypatch.setenv("BINGX_SECOND_SECRET_KEY", "demo_secret_secondary")
    else:
        monkeypatch.delenv("BINGX_SECOND_API_KEY", raising=False)
        monkeypatch.delenv("BINGX_SECOND_SECRET_KEY", raising=False)
    
    return importlib.reload(config_module)


def test_default_routing_uses_bingx_vst_demo(monkeypatch):
    """Default routing profile should always include the primary demo account."""
    cfg = _reload_config(monkeypatch, enable_second=False, primary_legacy=True)
    accounts = cfg.get_routing_profile("default")
    account_ids = [acc.account_id for acc in accounts]
    
    assert account_ids == ["bingx_vst_demo"]
    assert accounts[0].account_id == "bingx_vst_demo"
    assert accounts[0].mode == "demo"


def test_default_routing_adds_secondary_when_env_present(monkeypatch):
    """When secondary credentials exist, default profile should route to both demo accounts."""
    cfg = _reload_config(monkeypatch, enable_second=True, primary_legacy=True)
    accounts = cfg.get_routing_profile("default")
    account_ids = [acc.account_id for acc in accounts]
    
    assert account_ids == ["bingx_vst_demo", "bingx_vst_demo_secondary"]
    assert accounts[0].account_id == "bingx_vst_demo"
    assert accounts[0].mode == "demo"
    
    assert accounts[1].account_id == "bingx_vst_demo_secondary"
    assert accounts[1].mode == "demo"


def test_numeric_scheme_primary_account(monkeypatch):
    """Test that BINGX_1_* env vars are preferred over legacy BINGX_VST_* for primary demo."""
    # Set numeric scheme vars
    monkeypatch.setenv("BINGX_1_API_KEY", "numeric_key_1")
    monkeypatch.setenv("BINGX_1_API_SECRET", "numeric_secret_1")
    # Also set legacy vars (should be ignored)
    monkeypatch.setenv("BINGX_VST_API_KEY", "legacy_key")
    monkeypatch.setenv("BINGX_VST_API_SECRET", "legacy_secret")
    
    cfg = _reload_config(monkeypatch, enable_second=False)
    accounts = cfg.get_routing_profile("demo_primary_only")
    assert len(accounts) == 1
    assert accounts[0].account_id == "bingx_vst_demo"
    
    # Verify numeric credentials are used
    api_key, secret_key = accounts[0].get_credentials()
    assert api_key == "numeric_key_1"
    assert secret_key == "numeric_secret_1"


def test_numeric_scheme_secondary_account(monkeypatch):
    """Test that BINGX_2_* env vars are preferred over legacy BINGX_SECOND_* for secondary demo."""
    # Set numeric scheme vars
    monkeypatch.setenv("BINGX_2_API_KEY", "numeric_key_2")
    monkeypatch.setenv("BINGX_2_API_SECRET", "numeric_secret_2")
    # Also set legacy vars (should be ignored)
    monkeypatch.setenv("BINGX_SECOND_API_KEY", "legacy_key_2")
    monkeypatch.setenv("BINGX_SECOND_SECRET_KEY", "legacy_secret_2")
    
    cfg = _reload_config(monkeypatch, enable_second=False)
    accounts = cfg.get_routing_profile("demo_secondary_only")
    assert len(accounts) == 1
    assert accounts[0].account_id == "bingx_vst_demo_secondary"
    
    # Verify numeric credentials are used
    api_key, secret_key = accounts[0].get_credentials()
    assert api_key == "numeric_key_2"
    assert secret_key == "numeric_secret_2"


def test_legacy_fallback_primary_account(monkeypatch):
    """Test that legacy BINGX_VST_* vars work when numeric scheme is not set."""
    # Only set legacy vars
    monkeypatch.setenv("BINGX_VST_API_KEY", "legacy_key")
    monkeypatch.setenv("BINGX_VST_API_SECRET", "legacy_secret")
    # Ensure numeric vars are not set
    monkeypatch.delenv("BINGX_1_API_KEY", raising=False)
    monkeypatch.delenv("BINGX_1_API_SECRET", raising=False)
    
    cfg = _reload_config(monkeypatch, enable_second=False)
    accounts = cfg.get_routing_profile("demo_primary_only")
    assert len(accounts) == 1
    assert accounts[0].account_id == "bingx_vst_demo"
    
    # Verify legacy credentials are used
    api_key, secret_key = accounts[0].get_credentials()
    assert api_key == "legacy_key"
    assert secret_key == "legacy_secret"


def test_legacy_fallback_secondary_account(monkeypatch):
    """Test that legacy BINGX_SECOND_* vars work when numeric scheme is not set."""
    # Only set legacy vars
    monkeypatch.setenv("BINGX_SECOND_API_KEY", "legacy_key_2")
    monkeypatch.setenv("BINGX_SECOND_SECRET_KEY", "legacy_secret_2")
    # Ensure numeric vars are not set
    monkeypatch.delenv("BINGX_2_API_KEY", raising=False)
    monkeypatch.delenv("BINGX_2_API_SECRET", raising=False)
    
    cfg = _reload_config(monkeypatch, enable_second=False)
    accounts = cfg.get_routing_profile("demo_secondary_only")
    assert len(accounts) == 1
    assert accounts[0].account_id == "bingx_vst_demo_secondary"
    
    # Verify legacy credentials are used
    api_key, secret_key = accounts[0].get_credentials()
    assert api_key == "legacy_key_2"
    assert secret_key == "legacy_secret_2"


def test_numeric_scheme_primary_account_bingx_3(monkeypatch):
    """Test that BINGX_3_* env vars work for bingx_primary account."""
    # Set numeric scheme vars
    monkeypatch.setenv("BINGX_3_API_KEY", "numeric_key_3")
    monkeypatch.setenv("BINGX_3_API_SECRET", "numeric_secret_3")
    # Also set legacy vars (should be ignored)
    monkeypatch.setenv("BINGX_API_KEY", "legacy_key_3")
    monkeypatch.setenv("BINGX_API_SECRET", "legacy_secret_3")
    
    cfg = _reload_config(monkeypatch, enable_second=False)
    account = cfg.get_account("bingx_primary")
    
    # Verify numeric credentials are used
    api_key, secret_key = account.get_credentials()
    assert api_key == "numeric_key_3"
    assert secret_key == "numeric_secret_3"


