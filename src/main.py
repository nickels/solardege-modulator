import asyncio
import logging
import signal
import sys

from config import Config
from controller import Controller
from evcc import EvccClient
from modbus import InverterClient

log = logging.getLogger("solaredge-controller")


async def run(cfg: Config) -> None:
    evcc = EvccClient(cfg.evcc_url)
    inverter = InverterClient(cfg.inverter_host, cfg.inverter_port)
    controller = Controller(cfg.step_size)

    inverter.connect()

    loop = asyncio.get_event_loop()
    stop = asyncio.Event()

    def _shutdown(sig: signal.Signals) -> None:
        log.info("Received %s, shutting down", sig.name)
        stop.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _shutdown, sig)

    last_limit: int | None = None

    try:
        while not stop.is_set():
            try:
                state = await evcc.fetch_state()
                limit = controller.update(state)
                if limit != last_limit:
                    inverter.write_power_limit(limit)
                    last_limit = limit
                log.info(
                    "mode=%s grid=%.0fW feedin=%.4f€ grid_tariff=%.4f€ limit=%d%%",
                    controller.mode.value,
                    state.grid_power,
                    state.tariff_feed_in,
                    state.tariff_grid,
                    limit,
                )
            except Exception:
                log.exception("Control loop error, holding last state")

            try:
                await asyncio.wait_for(stop.wait(), timeout=cfg.poll_interval)
            except asyncio.TimeoutError:
                pass
    finally:
        inverter.close()
        await evcc.close()


def main() -> None:
    cfg = Config.from_env()
    logging.basicConfig(
        level=cfg.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    log.info(
        "Starting: inverter=%s:%d evcc=%s interval=%ds step=%d%%",
        cfg.inverter_host,
        cfg.inverter_port,
        cfg.evcc_url,
        cfg.poll_interval,
        cfg.step_size,
    )
    asyncio.run(run(cfg))


if __name__ == "__main__":
    main()
