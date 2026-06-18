# evcc Based SolarEdge Modulator

A lightweight Python daemon that controls SolarEdge inverter power output based on real-time electricity prices from [evcc](https://evcc.io). Works with any energy provider and tariff configuration that evcc supports (Tibber, aWATTar, Zonneplan, Octopus, ENTSO-E, custom, etc.).

## How it works

The controller reads two price signals from evcc's REST API every cycle:

- **Grid import tariff** (`tariffGrid`) — what you pay to consume from the grid
- **Feed-in tariff** (`tariffFeedIn`) — what you earn (or pay) to export to the grid

Based on these prices and the current grid meter reading, it selects one of three modes:

| Mode | Condition | Action |
|---|---|---|
| **GRID_OFF** | Import tariff < 0 | PV to 0% — maximize cheap grid draw |
| **THROTTLE** | Feed-in tariff < 0 | Step PV down to keep grid export near 0W |
| **FULL** | Both tariffs >= 0 | PV at 100% — export surplus and earn feed-in tariff |

GRID_OFF takes priority: if both tariffs are negative, PV is killed to maximize grid draw.

The target ActivePowerLimit percentage is written to all configured inverters via Modbus TCP (SunSpec register `0xF001`).

## Requirements

- SolarEdge inverter(s) with Modbus TCP enabled
- [evcc](https://evcc.io) instance with a grid tariff and feed-in tariff configured
- Docker host (tested on Synology DS720+ with Container Manager)

## Quick start

```yaml
services:
  solaredge-controller:
    image: ghcr.io/nickels/solardege-modulator:main
    container_name: solaredge-controller
    restart: unless-stopped
    network_mode: host
    environment:
      INVERTERS: "192.168.1.10:502:1"
      EVCC_URL: "http://192.168.1.20:7070"
```

Replace `INVERTERS` with your inverter's Modbus TCP address (`host:port:device_id`) and `EVCC_URL` with your evcc instance URL.

## Configuration

All via environment variables:

| Variable | Required | Default | Description |
|---|---|---|---|
| `INVERTERS` | yes | — | Comma-separated list of `host:port:device_id` |
| `EVCC_URL` | yes | — | evcc base URL (e.g. `http://192.168.1.20:7070`) |
| `POLL_INTERVAL` | no | `15` | Seconds between control loop cycles |
| `STEP_SIZE` | no | `5` | ActivePowerLimit adjustment per cycle in THROTTLE mode (%) |
| `LOG_LEVEL` | no | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Multiple inverters

Each inverter gets the same ActivePowerLimit percentage. The grid meter (read from evcc) reflects combined production, so the feedback loop self-corrects.

```
INVERTERS=192.168.1.10:502:1,192.168.1.11:502:2
```

## How THROTTLE mode works

When the feed-in tariff goes negative, exporting costs money. The controller steps the inverter power limit to keep grid export near zero:

- Grid exporting (< -50W): decrease limit by `STEP_SIZE`%
- Grid importing (> 50W): increase limit by `STEP_SIZE`%
- Within dead band (-50W to 50W): hold steady

PV continues to serve local consumption — only surplus export is suppressed.

## Error handling

- **evcc API unreachable**: the controller holds the last ActivePowerLimit unchanged and logs the error. It retries on the next cycle.
- **Modbus write failure**: logged, retried next cycle. The inverter continues at its last known limit.
- **Shutdown (SIGTERM/SIGINT)**: the controller restores ActivePowerLimit to 100% before exiting.
- **Container crash**: the inverter resets to 100% on its own restart cycle.

## evcc tariff setup

This controller reads `tariffGrid` and `tariffFeedIn` from evcc's `/api/state` endpoint. These values come from your evcc tariff configuration. Any tariff source evcc supports will work — the controller is provider-agnostic.

See the [evcc tariff documentation](https://docs.evcc.io/docs/reference/configuration/tariffs) for how to configure your energy provider.

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

Tested on DS720+ (DSM 7.4) with Container Manager.

### 1. Create a project

In Container Manager, go to **Project** > **Create**:

- **Project name**: `solaredge-controller`
- **Path**: `/docker/solaredge-controller`
- **Source**: Upload docker-compose.yml
- Paste the following compose configuration, replacing the environment values with your own:

```yaml
services:
  solaredge-controller:
    image: ghcr.io/nickels/solardege-modulator:main
    container_name: solaredge-controller
    restart: unless-stopped
    network_mode: host
    environment:
      INVERTERS: "192.168.1.20:1502:1"
      EVCC_URL: "http://192.168.1.20:7070"
      POLL_INTERVAL: "15"
      STEP_SIZE: "5"
      LOG_LEVEL: "INFO"
```

Click **Next**, then **Done**. Container Manager will pull the image from GHCR and start the container automatically.

> **Note:** Synology Container Manager does not support `env_file:` references — environment variables must be inline in the compose YAML.

`network_mode: host` gives the container direct LAN access to reach the inverter via Modbus TCP without port mapping.

### Updating the image

To pull a newer version, go to **Project** > select `solaredge-controller` > **Action** > **Build** (this re-pulls the image and recreates the container).

### Using evcc's Modbus Proxy

SolarEdge inverters accept only a single Modbus TCP connection. If evcc is already connected to the inverter directly, adding a second connection from this controller will cause conflicts.

evcc provides a [Modbus Proxy](https://docs.evcc.io/docs/reference/configuration/modbusproxy) feature that multiplexes a single connection to the inverter and exposes it to multiple clients. To use it:

1. In evcc, go to **Configuration** > **Modbus Proxy**
2. Set the proxy **Port** (e.g. `1502`), **Readonly** to `no` (write access needed), device connection to **Network / TCP** pointing at the inverter's real IP and port (e.g. `192.168.1.10:502`)
3. Point both evcc's own PV meter and this controller at the proxy address instead of the inverter directly:
   - evcc PV meter: `192.168.1.20:1502` (the evcc host + proxy port)
   - This controller's `INVERTERS`: `192.168.1.20:1502:1`

This ensures all Modbus traffic goes through a single managed connection to the inverter.

## License

MIT
