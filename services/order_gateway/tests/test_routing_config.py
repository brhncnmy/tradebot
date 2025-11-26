"""Tests for routing configuration."""

import importlib
import os

import pytest

from common.utils import config as config_module


def _reload_config(monkeypatch, enable_account_1: bool = True, enable_account_2: bool = False):
    """Reload config module with desired env setup."""
    if enable_account_1:
        monkeypatch.setenv("BINGX_1_API_KEY", "demo_key_1")
        monkeypatch.setenv("BINGX_1_API_SECRET", "demo_secret_1")
    else:
        monkeypatch.delenv("BINGX_1_API_KEY", raising=False)
        monkeypatch.delenv("BINGX_1_API_SECRET", raising=False)
    
    if enable_account_2:
        monkeypatch.setenv("BINGX_2_API_KEY", "demo_key_2")
        monkeypatch.setenv("BINGX_2_API_SECRET", "demo_secret_2")
    else:
        monkeypatch.delenv("BINGX_2_API_KEY", raising=False)
        monkeypatch.delenv("BINGX_2_API_SECRET", raising=False)
    
    return importlib.reload(config_module)


def test_default_routing_uses_bingx_1(monkeypatch):
    """Default routing profile should route to bingx_1 when available."""
    cfg = _reload_config(monkeypatch, enable_account_1=True, enable_account_2=False)
    accounts = cfg.get_routing_profile("default")
    account_ids = [acc.account_id for acc in accounts]
    
    assert account_ids == ["bingx_1"]
    assert accounts[0].account_id == "bingx_1"
    assert accounts[0].mode == "demo"


def test_demo_1_routing(monkeypatch):
    """demo_1 routing profile should route to bingx_1 when available."""
    cfg = _reload_config(monkeypatch, enable_account_1=True, enable_account_2=False)
    accounts = cfg.get_routing_profile("demo_1")
    account_ids = [acc.account_id for acc in accounts]
    
    assert account_ids == ["bingx_1"]
    assert accounts[0].account_id == "bingx_1"
    assert accounts[0].mode == "demo"


def test_demo_2_routing(monkeypatch):
    """demo_2 routing profile should route to bingx_2 when available."""
    cfg = _reload_config(monkeypatch, enable_account_1=False, enable_account_2=True)
    accounts = cfg.get_routing_profile("demo_2")
    account_ids = [acc.account_id for acc in accounts]
    
    assert account_ids == ["bingx_2"]
    assert accounts[0].account_id == "bingx_2"
    assert accounts[0].mode == "demo"


def test_demo_1_2_routing(monkeypatch):
    """demo_1_2 routing profile should route to both accounts when both are available."""
    cfg = _reload_config(monkeypatch, enable_account_1=True, enable_account_2=True)
    accounts = cfg.get_routing_profile("demo_1_2")
    account_ids = [acc.account_id for acc in accounts]
    
    assert len(accounts) == 2
    assert "bingx_1" in account_ids
    assert "bingx_2" in account_ids
    assert accounts[0].mode == "demo"
    assert accounts[1].mode == "demo"


def test_demo_1_2_routing_with_only_account_1(monkeypatch):
    """demo_1_2 routing profile should route only to bingx_1 when bingx_2 is not available."""
    cfg = _reload_config(monkeypatch, enable_account_1=True, enable_account_2=False)
    accounts = cfg.get_routing_profile("demo_1_2")
    account_ids = [acc.account_id for acc in accounts]
    
    assert account_ids == ["bingx_1"]


def test_demo_1_2_routing_with_only_account_2(monkeypatch):
    """demo_1_2 routing profile should route only to bingx_2 when bingx_1 is not available."""
    cfg = _reload_config(monkeypatch, enable_account_1=False, enable_account_2=True)
    accounts = cfg.get_routing_profile("demo_1_2")
    account_ids = [acc.account_id for acc in accounts]
    
    assert account_ids == ["bingx_2"]


def test_demo_1_2_routing_with_no_accounts(monkeypatch):
    """demo_1_2 routing profile should return empty list when no accounts are available."""
    cfg = _reload_config(monkeypatch, enable_account_1=False, enable_account_2=False)
    accounts = cfg.get_routing_profile("demo_1_2")
    
    assert accounts == []


def test_bingx_1_credentials(monkeypatch):
    """Test that bingx_1 uses BINGX_1_API_KEY/SECRET."""
    cfg = _reload_config(monkeypatch, enable_account_1=True, enable_account_2=False)
    account = cfg.get_account("bingx_1")
    
    api_key, secret_key = account.get_credentials()
    assert api_key == "demo_key_1"
    assert secret_key == "demo_secret_1"


def test_bingx_2_credentials(monkeypatch):
    """Test that bingx_2 uses BINGX_2_API_KEY/SECRET."""
    cfg = _reload_config(monkeypatch, enable_account_1=False, enable_account_2=True)
    account = cfg.get_account("bingx_2")
    
    api_key, secret_key = account.get_credentials()
    assert api_key == "demo_key_2"
    assert secret_key == "demo_secret_2"


def test_bingx_primary_uses_numeric_scheme(monkeypatch):
    """Test that bingx_primary uses BINGX_3_* env vars."""
    monkeypatch.setenv("BINGX_3_API_KEY", "test_key_3")
    monkeypatch.setenv("BINGX_3_API_SECRET", "test_secret_3")
    monkeypatch.setenv("BINGX_API_KEY", "legacy_key")
    monkeypatch.setenv("BINGX_API_SECRET", "legacy_secret")
    
    cfg = _reload_config(monkeypatch, enable_account_1=False, enable_account_2=False)
    account = cfg.get_account("bingx_primary")
    
    api_key, secret_key = account.get_credentials()
    assert api_key == "test_key_3"
    assert secret_key == "test_secret_3"
