# SolarEdge Export Controller — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python daemon that controls SolarEdge inverter power output based on EVCC electricity prices to maximize self-consumption and protect against negative prices.

**Architecture:** Single asyncio loop polling EVCC REST API every N seconds, resolving one of three operating modes (GRID_OFF / THROTTLE / FULL), and writing ActivePowerLimit (0–100%) to the inverter via Modbus TCP register 0xF001.

**Tech Stack:** Python 3.13, asyncio, httpx, pymodbus, pytest, Docker Alpine

## Global Constraints

- Python 3.13 on Alpine
- Only two runtime dependencies: `httpx`, `pymodbus`
- Test dependency: `pytest`
- All configuration via environment variables
- Conventional commits: `type(scope): description`
- Modbus register `0xF001` is Uint16, range 0–100
- EVCC API endpoint: `GET {EVCC_URL}/api/state`
- Dead band constant: 50W (not configurable)

---

### Task 1: Project scaffolding + config

**Files:**
- Create: `requirements.txt`
- Create: `src/config.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing
- Produces: `Config` dataclass with fields `inverter_host: str`, `inverter_port: int`, `evcc_url: str`, `poll_interval: int`, `step_size: int`, `log_level: str`. Factory method `Config.from_env()` reads `os.environ`.

- [ ] **Step 1: Create requirements.txt**

```
httpx>=0.28,<1
pymodbus>=3.8,<4
pytest>=8,<9
```

- [ ] **Step 2: Create virtual environment and install dependencies**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 3: Write the failing test for Config**

Create `tests/test_config.py`:

```python
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
    assert cfg.log_level == "INFO"


def test_from_env_overrides(monkeypatch):
    monkeypatch.setenv("INVERTER_HOST", "10.0.0.1")
    monkeypatch.setenv("INVERTER_PORT", "502")
    monkeypatch.setenv("EVCC_URL", "http://evcc:7070")
    monkeypatch.setenv("POLL_INTERVAL", "30")
    monkeypatch.setenv("STEP_SIZE", "10")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    cfg = Config.from_env()
    assert cfg.inverter_port == 502
    assert cfg.poll_interval == 30
    assert cfg.step_size == 10
    assert cfg.log_level == "DEBUG"


def test_from_env_missing_required(monkeypatch):
    monkeypatch.delenv("INVERTER_HOST", raising=False)
    monkeypatch.delenv("EVCC_URL", raising=False)
    try:
        Config.from_env()
        assert False, "Should have raised"
    except (KeyError, ValueError):
        pass
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
PYTHONPATH=src pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 5: Implement config.py**

Create `src/config.py`:

```python
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    inverter_host: str
    inverter_port: int
    evcc_url: str
    poll_interval: int
    step_size: int
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            inverter_host=os.environ["INVERTER_HOST"],
            inverter_port=int(os.environ.get("INVERTER_PORT", "1502")),
            evcc_url=os.environ["EVCC_URL"],
            poll_interval=int(os.environ.get("POLL_INTERVAL", "15")),
            step_size=int(os.environ.get("STEP_SIZE", "5")),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
PYTHONPATH=src pytest tests/test_config.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add requirements.txt src/config.py tests/test_config.py
git commit -m "feat(config): add Config dataclass with env var parsing"
```

---

### Task 2: EVCC client

**Files:**
- Create: `src/evcc.py`
- Create: `tests/test_evcc.py`

**Interfaces:**
- Consumes: `Config.evcc_url`
- Produces: `EvccState` dataclass with `grid_power: float`, `tariff_feed_in: float`, `tariff_grid: float`, `pv_power: float`. Class `EvccClient` with `async def fetch_state() -> EvccState`.

- [ ] **Step 1: Write the failing test for EvccClient**

Create `tests/test_evcc.py`:

```python
import httpx
import pytest
from evcc import EvccClient, EvccState


SAMPLE_RESPONSE = {
    "grid": {"power": -1500},
    "tariffFeedIn": -0.02,
    "tariffGrid": 0.15,
    "pvPower": 4000,
}


@pytest.mark.asyncio
async def test_fetch_state(httpx_mock):
    httpx_mock.add_response(json=SAMPLE_RESPONSE)
    client = EvccClient("http://test:7070")
    state = await client.fetch_state()
    assert state == EvccState(
        grid_power=-1500.0,
        tariff_feed_in=-0.02,
        tariff_grid=0.15,
        pv_power=4000.0,
    )


@pytest.mark.asyncio
async def test_fetch_state_http_error(httpx_mock):
    httpx_mock.add_response(status_code=500)
    client = EvccClient("http://test:7070")
    with pytest.raises(httpx.HTTPStatusError):
        await client.fetch_state()
```

- [ ] **Step 2: Install test dependencies**

```bash
pip install pytest-asyncio pytest-httpx
```

Add to `requirements.txt` (append):

```
pytest-asyncio>=0.25,<1
pytest-httpx>=0.35,<1
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
PYTHONPATH=src pytest tests/test_evcc.py -v
```

Expected: `ModuleNotFoundError: No module named 'evcc'`

- [ ] **Step 4: Implement evcc.py**

Create `src/evcc.py`:

```python
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class EvccState:
    grid_power: float
    tariff_feed_in: float
    tariff_grid: float
    pv_power: float


class EvccClient:
    def __init__(self, base_url: str) -> None:
        self._url = f"{base_url.rstrip('/')}/api/state"
        self._client = httpx.AsyncClient(timeout=10.0)

    async def fetch_state(self) -> EvccState:
        resp = await self._client.get(self._url)
        resp.raise_for_status()
        data = resp.json()
        return EvccState(
            grid_power=float(data["grid"]["power"]),
            tariff_feed_in=float(data["tariffFeedIn"]),
            tariff_grid=float(data["tariffGrid"]),
            pv_power=float(data["pvPower"]),
        )

    async def close(self) -> None:
        await self._client.aclose()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
PYTHONPATH=src pytest tests/test_evcc.py -v
```

Expected: both tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/evcc.py tests/test_evcc.py requirements.txt
git commit -m "feat(evcc): add EVCC API client with state parsing"
```

---

### Task 3: Controller (mode resolver + stepping logic)

**Files:**
- Create: `src/controller.py`
- Create: `tests/test_controller.py`

**Interfaces:**
- Consumes: `EvccState` from `evcc.py`, `Config.step_size` from `config.py`
- Produces: `Mode` enum (`GRID_OFF`, `THROTTLE`, `FULL`). Class `Controller` with `def update(self, state: EvccState) -> int` that returns the target ActivePowerLimit (0–100). Property `mode` for the current mode.

- [ ] **Step 1: Write failing tests for mode resolution**

Create `tests/test_controller.py`:

```python
from controller import Controller, Mode
from evcc import EvccState


def _state(grid_power=0.0, tariff_feed_in=0.05, tariff_grid=0.15, pv_power=3000.0):
    return EvccState(
        grid_power=grid_power,
        tariff_feed_in=tariff_feed_in,
        tariff_grid=tariff_grid,
        pv_power=pv_power,
    )


def test_mode_full_both_positive():
    ctrl = Controller(step_size=5)
    limit = ctrl.update(_state(tariff_feed_in=0.05, tariff_grid=0.15))
    assert ctrl.mode == Mode.FULL
    assert limit == 100


def test_mode_grid_off_negative_consumption():
    ctrl = Controller(step_size=5)
    limit = ctrl.update(_state(tariff_grid=-0.05, tariff_feed_in=0.05))
    assert ctrl.mode == Mode.GRID_OFF
    assert limit == 0


def test_mode_grid_off_priority_over_throttle():
    ctrl = Controller(step_size=5)
    limit = ctrl.update(_state(tariff_grid=-0.05, tariff_feed_in=-0.02))
    assert ctrl.mode == Mode.GRID_OFF
    assert limit == 0


def test_mode_throttle_negative_feedin():
    ctrl = Controller(step_size=5)
    limit = ctrl.update(_state(tariff_feed_in=-0.02, tariff_grid=0.15, grid_power=0.0))
    assert ctrl.mode == Mode.THROTTLE


def test_throttle_decrease_on_export():
    ctrl = Controller(step_size=5)
    ctrl.update(_state(tariff_feed_in=0.05))  # start at FULL (100)
    limit = ctrl.update(_state(tariff_feed_in=-0.02, grid_power=-500.0))
    assert limit == 95


def test_throttle_increase_on_import():
    ctrl = Controller(step_size=5)
    ctrl._limit = 80
    limit = ctrl.update(_state(tariff_feed_in=-0.02, grid_power=500.0))
    assert limit == 85


def test_throttle_hold_in_dead_band():
    ctrl = Controller(step_size=5)
    ctrl._limit = 70
    limit = ctrl.update(_state(tariff_feed_in=-0.02, grid_power=30.0))
    assert limit == 70


def test_throttle_clamp_at_zero():
    ctrl = Controller(step_size=5)
    ctrl._limit = 2
    limit = ctrl.update(_state(tariff_feed_in=-0.02, grid_power=-500.0))
    assert limit == 0


def test_throttle_clamp_at_100():
    ctrl = Controller(step_size=5)
    ctrl._limit = 98
    limit = ctrl.update(_state(tariff_feed_in=-0.02, grid_power=500.0))
    assert limit == 100


def test_transition_throttle_to_full():
    ctrl = Controller(step_size=5)
    ctrl._limit = 60
    ctrl.update(_state(tariff_feed_in=-0.02, grid_power=0.0))
    assert ctrl.mode == Mode.THROTTLE

    limit = ctrl.update(_state(tariff_feed_in=0.05, tariff_grid=0.15))
    assert ctrl.mode == Mode.FULL
    assert limit == 100


def test_transition_full_to_throttle_starts_from_current():
    ctrl = Controller(step_size=5)
    ctrl.update(_state(tariff_feed_in=0.05))  # FULL → limit = 100
    limit = ctrl.update(_state(tariff_feed_in=-0.02, grid_power=-500.0))
    assert ctrl.mode == Mode.THROTTLE
    assert limit == 95  # stepped down from 100


def test_no_increase_at_100_in_throttle():
    ctrl = Controller(step_size=5)
    ctrl._limit = 100
    limit = ctrl.update(_state(tariff_feed_in=-0.02, grid_power=500.0))
    assert limit == 100
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src pytest tests/test_controller.py -v
```

Expected: `ModuleNotFoundError: No module named 'controller'`

- [ ] **Step 3: Implement controller.py**

Create `src/controller.py`:

```python
from enum import Enum

from evcc import EvccState

DEAD_BAND_W = 50


class Mode(Enum):
    GRID_OFF = "GRID_OFF"
    THROTTLE = "THROTTLE"
    FULL = "FULL"


class Controller:
    def __init__(self, step_size: int) -> None:
        self._step_size = step_size
        self._limit = 100
        self.mode = Mode.FULL

    def update(self, state: EvccState) -> int:
        if state.tariff_grid < 0:
            self.mode = Mode.GRID_OFF
            self._limit = 0
        elif state.tariff_feed_in < 0:
            self.mode = Mode.THROTTLE
            self._step(state.grid_power)
        else:
            self.mode = Mode.FULL
            self._limit = 100

        return self._limit

    def _step(self, grid_power: float) -> None:
        if grid_power < -DEAD_BAND_W:
            self._limit -= self._step_size
        elif grid_power > DEAD_BAND_W and self._limit < 100:
            self._limit += self._step_size
        self._limit = max(0, min(100, self._limit))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=src pytest tests/test_controller.py -v
```

Expected: all 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/controller.py tests/test_controller.py
git commit -m "feat(controller): add mode resolver with stepping logic"
```

---

### Task 4: Modbus writer

**Files:**
- Create: `src/modbus.py`
- Create: `tests/test_modbus.py`

**Interfaces:**
- Consumes: `Config.inverter_host`, `Config.inverter_port`
- Produces: Class `InverterClient` with `def write_power_limit(self, percent: int) -> None`, `def connect(self) -> None`, `def close(self) -> None`. Register address constant `ACTIVE_POWER_LIMIT = 0xF001`.

- [ ] **Step 1: Write the failing test for InverterClient**

Create `tests/test_modbus.py`:

```python
from unittest.mock import MagicMock, patch

from modbus import InverterClient, ACTIVE_POWER_LIMIT


def test_write_power_limit():
    client = InverterClient("192.168.1.10", 1502)
    mock_modbus = MagicMock()
    client._client = mock_modbus

    client.write_power_limit(75)

    mock_modbus.write_register.assert_called_once_with(
        ACTIVE_POWER_LIMIT, 75, slave=1
    )


def test_write_power_limit_clamps_range():
    client = InverterClient("192.168.1.10", 1502)
    mock_modbus = MagicMock()
    client._client = mock_modbus

    client.write_power_limit(150)
    mock_modbus.write_register.assert_called_with(ACTIVE_POWER_LIMIT, 100, slave=1)

    client.write_power_limit(-10)
    mock_modbus.write_register.assert_called_with(ACTIVE_POWER_LIMIT, 0, slave=1)


def test_connect_creates_client():
    with patch("modbus.ModbusTcpClient") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance

        client = InverterClient("192.168.1.10", 1502)
        client.connect()

        MockClient.assert_called_once_with("192.168.1.10", port=1502)
        mock_instance.connect.assert_called_once()


def test_close_writes_100_and_disconnects():
    client = InverterClient("192.168.1.10", 1502)
    mock_modbus = MagicMock()
    client._client = mock_modbus

    client.close()

    mock_modbus.write_register.assert_called_once_with(
        ACTIVE_POWER_LIMIT, 100, slave=1
    )
    mock_modbus.close.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src pytest tests/test_modbus.py -v
```

Expected: `ModuleNotFoundError: No module named 'modbus'`

- [ ] **Step 3: Implement modbus.py**

Create `src/modbus.py`:

```python
import logging

from pymodbus.client import ModbusTcpClient

log = logging.getLogger(__name__)

ACTIVE_POWER_LIMIT = 0xF001


class InverterClient:
    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._client: ModbusTcpClient | None = None

    def connect(self) -> None:
        self._client = ModbusTcpClient(self._host, port=self._port)
        self._client.connect()
        log.info("Connected to inverter at %s:%d", self._host, self._port)

    def write_power_limit(self, percent: int) -> None:
        percent = max(0, min(100, percent))
        self._client.write_register(ACTIVE_POWER_LIMIT, percent, slave=1)
        log.debug("Wrote ActivePowerLimit = %d%%", percent)

    def close(self) -> None:
        if self._client:
            try:
                self._client.write_register(ACTIVE_POWER_LIMIT, 100, slave=1)
                log.info("Restored ActivePowerLimit to 100%%")
            except Exception:
                log.warning("Failed to restore ActivePowerLimit on shutdown")
            self._client.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=src pytest tests/test_modbus.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/modbus.py tests/test_modbus.py
git commit -m "feat(modbus): add SolarEdge Modbus writer for ActivePowerLimit"
```

---

### Task 5: Main loop + signal handling + Docker

**Files:**
- Create: `src/main.py`
- Create: `Dockerfile`
- Create: `docker-compose.yml`

**Interfaces:**
- Consumes: `Config.from_env()`, `EvccClient`, `Controller`, `InverterClient`
- Produces: runnable application entry point

- [ ] **Step 1: Implement main.py**

Create `src/main.py`:

```python
import asyncio
import logging
import signal
import sys

from config import Config
from controller import Controller
from evcc import EvccClient
from modbus import InverterClient

log = logging.getLogger("solaredge-controller")


async def run(cfg: Config) -> None:
    evcc = EvccClient(cfg.evcc_url)
    inverter = InverterClient(cfg.inverter_host, cfg.inverter_port)
    controller = Controller(cfg.step_size)

    inverter.connect()

    loop = asyncio.get_event_loop()
    stop = asyncio.Event()

    def _shutdown(sig: signal.Signals) -> None:
        log.info("Received %s, shutting down", sig.name)
        stop.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _shutdown, sig)

    last_limit: int | None = None

    try:
        while not stop.is_set():
            try:
                state = await evcc.fetch_state()
                limit = controller.update(state)
                if limit != last_limit:
                    inverter.write_power_limit(limit)
                    last_limit = limit
                log.info(
                    "mode=%s grid=%.0fW feedin=%.4f€ grid_tariff=%.4f€ limit=%d%%",
                    controller.mode.value,
                    state.grid_power,
                    state.tariff_feed_in,
                    state.tariff_grid,
                    limit,
                )
            except Exception:
                log.exception("Control loop error, holding last state")

            try:
                await asyncio.wait_for(stop.wait(), timeout=cfg.poll_interval)
            except asyncio.TimeoutError:
                pass
    finally:
        inverter.close()
        await evcc.close()


def main() -> None:
    cfg = Config.from_env()
    logging.basicConfig(
        level=cfg.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    log.info(
        "Starting: inverter=%s:%d evcc=%s interval=%ds step=%d%%",
        cfg.inverter_host,
        cfg.inverter_port,
        cfg.evcc_url,
        cfg.poll_interval,
        cfg.step_size,
    )
    asyncio.run(run(cfg))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create Dockerfile**

Create `Dockerfile`:

```dockerfile
FROM python:3.13-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ .
CMD ["python", "main.py"]
```

- [ ] **Step 3: Create docker-compose.yml**

Create `docker-compose.yml`:

```yaml
services:
  solaredge-controller:
    build: .
    restart: unless-stopped
    environment:
      INVERTER_HOST: ${INVERTER_HOST}
      INVERTER_PORT: ${INVERTER_PORT:-1502}
      EVCC_URL: ${EVCC_URL}
      POLL_INTERVAL: ${POLL_INTERVAL:-15}
      STEP_SIZE: ${STEP_SIZE:-5}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
```

- [ ] **Step 4: Run full test suite**

```bash
PYTHONPATH=src pytest tests/ -v
```

Expected: all tests PASS (config: 4, evcc: 2, controller: 12, modbus: 4 = 22 total)

- [ ] **Step 5: Build Docker image**

```bash
docker build -t solaredge-controller .
```

Expected: successful build

- [ ] **Step 6: Commit**

```bash
git add src/main.py Dockerfile docker-compose.yml
git commit -m "feat(main): add asyncio control loop, signal handling, and Docker setup"
```
