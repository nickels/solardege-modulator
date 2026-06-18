# Contributing

## Getting started

```bash
git clone <repo-url>
cd solaredge-moduleren
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running tests

```bash
pytest tests/ -v
```

Tests run without hardware — Modbus calls are mocked, EVCC responses are stubbed with pytest-httpx.

## Code structure

```
src/
├── config.py       # Environment variable parsing
├── evcc.py         # EVCC REST API client
├── controller.py   # Mode resolver + stepping logic
├── modbus.py       # SolarEdge Modbus writer
└── main.py         # Async control loop entry point
```

## Making changes

1. Create a feature branch from `main`
2. Write tests first, then implementation
3. Run `pytest tests/ -v` and confirm all tests pass
4. Use conventional commits: `feat(scope):`, `fix(scope):`, `test(scope):`

## Building the Docker image

```bash
docker build -t solaredge-controller .
```

For Synology NAS (amd64):

```bash
docker build --platform linux/amd64 -t solaredge-controller .
docker save solaredge-controller | gzip > solaredge-controller.tar.gz
```
