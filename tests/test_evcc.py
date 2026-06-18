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
