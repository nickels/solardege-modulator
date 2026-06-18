import logging

from pymodbus.client import ModbusTcpClient

log = logging.getLogger(__name__)

ACTIVE_POWER_LIMIT = 0xF001


class InverterClient:
    def __init__(self, host: str, port: int, device_id: int = 1) -> None:
        self._host = host
        self._port = port
        self._device_id = device_id
        self._client: ModbusTcpClient | None = None

    def connect(self) -> None:
        self._client = ModbusTcpClient(self._host, port=self._port)
        self._client.connect()
        log.info("Connected to inverter at %s:%d", self._host, self._port)

    def write_power_limit(self, percent: int) -> None:
        percent = max(0, min(100, percent))
        self._client.write_register(ACTIVE_POWER_LIMIT, percent, device_id=self._device_id)
        log.debug("Wrote ActivePowerLimit = %d%%", percent)

    def close(self) -> None:
        if self._client:
            try:
                self._client.write_register(ACTIVE_POWER_LIMIT, 100, device_id=self._device_id)
                log.info("Restored ActivePowerLimit to 100%")
            except Exception:
                log.warning("Failed to restore ActivePowerLimit on shutdown")
            self._client.close()
