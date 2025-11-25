"""Tests for routing configuration."""

import importlib
import os

import pytest

from common.utils import config as config_module


def _reload_config(monkeypatch, enable_second: bool):
    """Reload config module with desired env setup."""
    if enable_second:
        monkeypatch.setenv("BINGX_SECOND_API_KEY", "demo_key_secondary")
        monkeypatch.setenv("BINGX_SECOND_SECRET_KEY", "demo_secret_secondary")
    else:
        monkeypatch.delenv("BINGX_SECOND_API_KEY", raising=False)
        monkeypatch.delenv("BINGX_SECOND_SECRET_KEY", raising=False)
    
    return importlib.reload(config_module)


def test_default_routing_uses_bingx_vst_demo(monkeypatch):
    """Default routing profile should always include the primary demo account."""
    cfg = _reload_config(monkeypatch, enable_second=False)
    accounts = cfg.get_routing_profile("default")
    account_ids = [acc.account_id for acc in accounts]
    
    assert account_ids == ["bingx_vst_demo"]
    assert accounts[0].account_id == "bingx_vst_demo"
    assert accounts[0].mode == "demo"
    assert accounts[0].api_key_env == "BINGX_VST_API_KEY"
    assert accounts[0].secret_key_env == "BINGX_VST_API_SECRET"


def test_default_routing_adds_secondary_when_env_present(monkeypatch):
    """When secondary credentials exist, default profile should route to both demo accounts."""
    cfg = _reload_config(monkeypatch, enable_second=True)
    accounts = cfg.get_routing_profile("default")
    account_ids = [acc.account_id for acc in accounts]
    
    assert account_ids == ["bingx_vst_demo", "bingx_vst_demo_secondary"]
    assert accounts[0].account_id == "bingx_vst_demo"
    assert accounts[0].mode == "demo"
    assert accounts[0].api_key_env == "BINGX_VST_API_KEY"
    assert accounts[0].secret_key_env == "BINGX_VST_API_SECRET"
    
    assert accounts[1].account_id == "bingx_vst_demo_secondary"
    assert accounts[1].mode == "demo"
    assert accounts[1].api_key_env == "BINGX_SECOND_API_KEY"
    assert accounts[1].secret_key_env == "BINGX_SECOND_SECRET_KEY"


