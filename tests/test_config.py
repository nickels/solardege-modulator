import os
from config import Config


def test_from_env_required_fields(monkeypatch):
    monkeypatch.setenv("INVERTER_HOST", "192.168.1.10")
    monkeypatch.setenv("EVCC_URL", "http://localhost:7070")
    cfg = Config.from_env()
    assert cfg.inverter_host == "192.168.1.10"
    assert cfg.evcc_url == "http://localhost:7070"


def test_from_env_defaults(monkeypatch):
    monkeypatch.setenv("INVERTER_HOST", "192.168.1.10")
    monkeypatch.setenv("EVCC_URL", "http://localhost:7070")
    cfg = Config.from_env()
    assert cfg.inverter_port == 1502
    assert cfg.poll_interval == 15
    assert cfg.step_size == 5
    assert cfg.inverter_device_id == 1
    assert cfg.log_level == "INFO"


def test_from_env_overrides(monkeypatch):
    monkeypatch.setenv("INVERTER_HOST", "10.0.0.1")
    monkeypatch.setenv("INVERTER_PORT", "502")
    monkeypatch.setenv("EVCC_URL", "http://evcc:7070")
    monkeypatch.setenv("POLL_INTERVAL", "30")
    monkeypatch.setenv("STEP_SIZE", "10")
    monkeypatch.setenv("INVERTER_DEVICE_ID", "2")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    cfg = Config.from_env()
    assert cfg.inverter_port == 502
    assert cfg.poll_interval == 30
    assert cfg.step_size == 10
    assert cfg.inverter_device_id == 2
    assert cfg.log_level == "DEBUG"


def test_from_env_missing_required(monkeypatch):
    monkeypatch.delenv("INVERTER_HOST", raising=False)
    monkeypatch.delenv("EVCC_URL", raising=False)
    try:
        Config.from_env()
        assert False, "Should have raised"
    except (KeyError, ValueError):
        pass
