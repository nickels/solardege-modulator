# Contributing

## Getting started

```bash
git clone https://github.com/nickels/solardege-modulator.git
cd solardege-modulator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running tests

```bash
pytest tests/ -v
```

Tests run without hardware — Modbus calls are mocked, evcc responses are stubbed with pytest-httpx.

## Code structure

```
src/
├── config.py       # Environment variable parsing
├── evcc.py         # evcc REST API client
├── controller.py   # Mode resolver + stepping logic
├── modbus.py       # SolarEdge Modbus writer
└── main.py         # Async control loop entry point
```

## Branch flow

```
feature branch → PR → release/development → PR → main
```

- Create feature branches from `release/development`
- PRs to `release/development` require passing tests
- Only `release/development` can be merged into `main` (enforced by CI)
- All merges to `main` are squash merges

## Making changes

1. Create a feature branch from `release/development`
2. Write tests first, then implementation
3. Run `pytest tests/ -v` and confirm all tests pass
4. Use conventional commits: `feat(scope):`, `fix(scope):`, `test(scope):`

## Building the Docker image

```bash
docker build -t solaredge-controller .
```
