import asyncio
import logging
import signal

from config import Config
from controller import Controller
from evcc import EvccClient
from modbus import InverterClient

log = logging.getLogger("solaredge-controller")


async def run(cfg: Config) -> None:
    evcc = EvccClient(cfg.evcc_url)
    inverters = [
        InverterClient(inv.host, inv.port, inv.device_id)
        for inv in cfg.inverters
    ]
    controller = Controller(cfg.step_size)

    for inv in inverters:
        inv.connect()

    loop = asyncio.get_running_loop()
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
                    for inv in inverters:
                        inv.write_power_limit(limit)
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
        for inv in inverters:
            inv.close()
        await evcc.close()


def main() -> None:
    cfg = Config.from_env()
    logging.basicConfig(
        level=cfg.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    log.info(
        "Starting: %d inverter(s) evcc=%s interval=%ds step=%d%%",
        len(cfg.inverters),
        cfg.evcc_url,
        cfg.poll_interval,
        cfg.step_size,
    )
    for inv in cfg.inverters:
        log.info("  inverter=%s:%d device_id=%d", inv.host, inv.port, inv.device_id)
    asyncio.run(run(cfg))


if __name__ == "__main__":
    main()
