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
