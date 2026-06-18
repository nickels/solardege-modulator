import os
from dataclasses import dataclass


@dataclass(frozen=True)
class InverterConfig:
    host: str
    port: int
    device_id: int


@dataclass(frozen=True)
class Config:
    inverters: tuple[InverterConfig, ...]
    evcc_url: str
    poll_interval: int
    step_size: int
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            inverters=cls._parse_inverters(os.environ["INVERTERS"]),
            evcc_url=os.environ["EVCC_URL"],
            poll_interval=int(os.environ.get("POLL_INTERVAL", "15")),
            step_size=int(os.environ.get("STEP_SIZE", "5")),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )

    @staticmethod
    def _parse_inverters(raw: str) -> tuple[InverterConfig, ...]:
        result = []
        for entry in raw.split(","):
            parts = entry.strip().split(":")
            if len(parts) != 3:
                raise ValueError(f"Invalid inverter format '{entry}', expected host:port:device_id")
            result.append(InverterConfig(parts[0], int(parts[1]), int(parts[2])))
        return tuple(result)
