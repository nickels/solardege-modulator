from config import Config, InverterConfig


def test_from_env_single_inverter(monkeypatch):
    monkeypatch.setenv("INVERTERS", "192.168.1.10:502:1")
    monkeypatch.setenv("EVCC_URL", "http://localhost:7070")
    cfg = Config.from_env()
    assert len(cfg.inverters) == 1
    assert cfg.inverters[0] == InverterConfig("192.168.1.10", 502, 1)
    assert cfg.evcc_url == "http://localhost:7070"


def test_from_env_multiple_inverters(monkeypatch):
    monkeypatch.setenv("INVERTERS", "192.168.1.10:502:1,192.168.1.11:502:2")
    monkeypatch.setenv("EVCC_URL", "http://localhost:7070")
    cfg = Config.from_env()
    assert len(cfg.inverters) == 2
    assert cfg.inverters[0] == InverterConfig("192.168.1.10", 502, 1)
    assert cfg.inverters[1] == InverterConfig("192.168.1.11", 502, 2)


def test_from_env_defaults(monkeypatch):
    monkeypatch.setenv("INVERTERS", "192.168.1.10:502:1")
    monkeypatch.setenv("EVCC_URL", "http://localhost:7070")
    cfg = Config.from_env()
    assert cfg.poll_interval == 15
    assert cfg.step_size == 5
    assert cfg.log_level == "INFO"


def test_from_env_overrides(monkeypatch):
    monkeypatch.setenv("INVERTERS", "10.0.0.1:502:1")
    monkeypatch.setenv("EVCC_URL", "http://evcc:7070")
    monkeypatch.setenv("POLL_INTERVAL", "30")
    monkeypatch.setenv("STEP_SIZE", "10")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    cfg = Config.from_env()
    assert cfg.poll_interval == 30
    assert cfg.step_size == 10
    assert cfg.log_level == "DEBUG"


def test_from_env_missing_required(monkeypatch):
    monkeypatch.delenv("INVERTERS", raising=False)
    monkeypatch.delenv("EVCC_URL", raising=False)
    try:
        Config.from_env()
        assert False, "Should have raised"
    except (KeyError, ValueError):
        pass


def test_from_env_bad_inverter_format(monkeypatch):
    monkeypatch.setenv("INVERTERS", "192.168.1.10")
    monkeypatch.setenv("EVCC_URL", "http://localhost:7070")
    try:
        Config.from_env()
        assert False, "Should have raised"
    except ValueError:
        pass
