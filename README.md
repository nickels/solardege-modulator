# SolarEdge Moduleren

A lightweight Python daemon that controls SolarEdge inverter power output based on real-time electricity prices from [EVCC](https://evcc.io). Designed for the Dutch energy market with Zonneplan dynamic pricing.

## What it does

The controller polls EVCC every N seconds and operates in one of three modes:

| Mode | Condition | Action |
|---|---|---|
| **GRID_OFF** | Grid consumption price < 0 | PV output to 0% — maximize cheap grid draw |
| **THROTTLE** | Feed-in tariff < 0 | Step PV down to keep grid export near 0W — self-consume only |
| **FULL** | Both prices >= 0 | PV at 100% — export surplus and earn feed-in tariff |

The same percentage is written to all configured inverters via Modbus TCP (register `0xF001` ActivePowerLimit).

## Requirements

- SolarEdge inverter(s) with Modbus TCP enabled
- [EVCC](https://evcc.io) instance with dynamic tariff configured
- Docker (tested on Synology DS720+ with Container Manager)

## Quick start

1. Copy `docker-compose.yml` and `.env.example` to your Docker host
2. Create `.env` from the example:

```bash
cp .env.example .env
```

3. Edit `.env` with your values:

```
INVERTERS=192.168.1.10:502:1
EVCC_URL=http://your-evcc:7070
```

4. Load the image and start:

```bash
docker load < solaredge-controller.tar.gz
docker compose up -d
```

## Configuration

All via environment variables:

| Variable | Required | Default | Description |
|---|---|---|---|
| `INVERTERS` | yes | — | Comma-separated list of `host:port:device_id` |
| `EVCC_URL` | yes | — | EVCC base URL |
| `POLL_INTERVAL` | no | `15` | Seconds between control loop cycles |
| `STEP_SIZE` | no | `5` | ActivePowerLimit adjustment per cycle in THROTTLE mode (%) |
| `LOG_LEVEL` | no | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Multiple inverters

Each inverter gets the same ActivePowerLimit percentage. The grid meter (read from EVCC) reflects combined production, so the feedback loop self-corrects.

```
INVERTERS=192.168.1.10:502:1,192.168.1.11:502:1
```

## How THROTTLE mode works

When the feed-in tariff goes negative, exporting costs money. The controller steps the inverter power limit to keep grid export near zero:

- Grid exporting (< -50W): decrease limit by `STEP_SIZE`%
- Grid importing (> 50W): increase limit by `STEP_SIZE`%
- Within dead band (-50W to 50W): hold steady

PV continues to serve local consumption — only surplus export is suppressed.

## Shutdown safety

On SIGTERM/SIGINT, the controller restores ActivePowerLimit to 100% before exiting. If the container crashes, the inverter resets to 100% on its own restart cycle.

## Building from source

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Build Docker image
docker build -t solaredge-controller .
```

## Synology deployment

For Synology NAS with Container Manager:

1. Build the image: `docker build --platform linux/amd64 -t solaredge-controller .`
2. Export: `docker save solaredge-controller | gzip > solaredge-controller.tar.gz`
3. Copy tarball to NAS
4. In Container Manager: **Project** > Create > paste `docker-compose.yml` with inline environment variables
5. Use `network_mode: host` for LAN Modbus access

## License

MIT
