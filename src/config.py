import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    inverter_host: str
    inverter_port: int
    evcc_url: str
    poll_interval: int
    step_size: int
    inverter_device_id: int
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            inverter_host=os.environ["INVERTER_HOST"],
            inverter_port=int(os.environ.get("INVERTER_PORT", "502")),
            evcc_url=os.environ["EVCC_URL"],
            poll_interval=int(os.environ.get("POLL_INTERVAL", "15")),
            step_size=int(os.environ.get("STEP_SIZE", "5")),
            inverter_device_id=int(os.environ.get("INVERTER_DEVICE_ID", "1")),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )
