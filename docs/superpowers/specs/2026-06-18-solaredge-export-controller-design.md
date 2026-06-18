# SolarEdge Export Controller — Design Spec

## Purpose

A lightweight Python daemon that controls a SolarEdge inverter's power output based on real-time electricity prices from EVCC. The goal is to maximize self-consumption, allow export when profitable, and protect against negative price exposure.

## Operating Modes

The controller evaluates two price signals from EVCC every cycle and selects exactly one mode. Mode 1 takes priority over Mode 2.

### Mode 1: GRID_OFF — Grid consumption price < 0

- Set `ActivePowerLimit` to **0%** (kill PV output entirely)
- Rationale: when consumption price is negative, the grid pays you to consume. Maximizing grid draw is optimal. PV production would offset that benefit.

### Mode 2: THROTTLE — Feed-in tariff < 0 (and consumption price ≥ 0)

- Run a stepping control loop that adjusts `ActivePowerLimit` to keep grid export near 0W
- PV continues to serve local consumption; only surplus export is suppressed
- Stepping logic:
  - If `grid.power < -50W` (exporting): decrease `ActivePowerLimit` by `STEP_SIZE`%
  - If `grid.power > 50W` (importing) and limit < 100: increase by `STEP_SIZE`%
  - If `-50W ≤ grid.power ≤ 50W`: hold (dead band to prevent oscillation)
  - Clamp result to `[0, 100]`

### Mode 3: FULL — Both prices ≥ 0

- Set `ActivePowerLimit` to **100%**
- PV runs at full capacity; surplus exports to the grid and earns the Zonneplan feed-in tariff

## Data Sources

All data comes from the EVCC REST API at `GET {EVCC_URL}/api/state`.

| Data point | JSON path | Unit | Sign convention |
|---|---|---|---|
| Grid power | `grid.power` | W | positive = importing, negative = exporting |
| Feed-in tariff | `tariffFeedIn` | EUR/kWh | positive = you earn, negative = you pay |
| Grid consumption tariff | `tariffGrid` | EUR/kWh | positive = you pay, negative = you earn |
| PV power (informational) | `pvPower` | W | always positive |

## Inverter Control

### Register

- `0xF001` — `ActivePowerLimit` (Uint16, 0–100%)
- Takes effect immediately, no commit register needed
- Resets to 100% on inverter restart; the control loop re-asserts within one cycle

### Connection

- Persistent `ModbusTcpClient` connection via `pymodbus`
- Reconnect automatically on connection loss
- On Modbus write failure: log error, retry next cycle
- On EVCC API failure: hold last `ActivePowerLimit` unchanged

### Shutdown safeguard

On SIGTERM/SIGINT, write `ActivePowerLimit = 100%` before exiting to restore full PV output.

## Configuration

All via environment variables:

| Variable | Required | Default | Description |
|---|---|---|---|
| `INVERTER_HOST` | yes | — | SolarEdge inverter IP address |
| `INVERTER_PORT` | no | `1502` | Modbus TCP port |
| `EVCC_URL` | yes | — | EVCC base URL (e.g. `http://10.36.10.182:7070`) |
| `POLL_INTERVAL` | no | `15` | Seconds between control loop cycles |
| `STEP_SIZE` | no | `5` | ActivePowerLimit adjustment per cycle (%) |
| `LOG_LEVEL` | no | `INFO` | Python logging level |

## Architecture

Single Python process, one `asyncio` loop, three internal components:

```
┌─────────────────────────────────────────────┐
│         Control Loop (POLL_INTERVAL)        │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │ EVCC     │  │ Mode     │  │ SolarEdge │ │
│  │ Client   │→ │ Resolver │→ │ Modbus    │ │
│  │ (httpx)  │  │          │  │ Writer    │ │
│  └──────────┘  └──────────┘  └───────────┘ │
└─────────────────────────────────────────────┘
```

1. **EVCC Client** (`evcc.py`) — fetches `/api/state`, extracts grid power and tariffs
2. **Mode Resolver** (`controller.py`) — decides mode, calculates target ActivePowerLimit, tracks stepping state
3. **Modbus Writer** (`modbus.py`) — writes ActivePowerLimit to register 0xF001

## File Structure

```
solaredge-moduleren/
├── src/
│   ├── main.py           # Entry point, asyncio loop, signal handling
│   ├── evcc.py           # EVCC API client
│   ├── modbus.py         # SolarEdge Modbus writer
│   ├── controller.py     # Mode resolver + stepping logic
│   └── config.py         # Env var parsing
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── tests/
    └── test_controller.py
```

## Docker

```dockerfile
FROM python:3.13-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ .
CMD ["python", "main.py"]
```

Dependencies: `httpx`, `pymodbus`

## Logging

Structured logging to stdout (captured by Docker). Each cycle logs:
- Current mode
- Grid power, feed-in tariff, grid tariff
- ActivePowerLimit value written (if changed)

## Testing

Unit tests for `controller.py` covering:
- Mode selection priority (Mode 1 > Mode 2 > Mode 3)
- Stepping logic: decrease on export, increase on import, hold in dead band
- Clamping at 0% and 100%
- Mode transitions: entering Mode 2 from Mode 3 (start stepping), entering Mode 3 from Mode 2 (jump to 100%)

## Out of Scope

- 7,500 kWh Zonnebonus cap tracking (reconciled on Zonneplan annual bill)
- Sunrise/sunset detection (Zonneplan handles this server-side)
- Web UI or dashboards
- MQTT integration (future enhancement if EVCC MQTT is configured)
- Battery control
