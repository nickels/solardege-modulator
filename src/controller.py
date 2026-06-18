from enum import Enum

from evcc import EvccState

DEAD_BAND_W = 50


class Mode(Enum):
    GRID_OFF = "GRID_OFF"
    THROTTLE = "THROTTLE"
    FULL = "FULL"


class Controller:
    def __init__(self, step_size: int) -> None:
        self._step_size = step_size
        self._limit = 100
        self.mode = Mode.FULL

    def update(self, state: EvccState) -> int:
        if state.tariff_grid < 0:
            self.mode = Mode.GRID_OFF
            self._limit = 0
        elif state.tariff_feed_in < 0:
            self.mode = Mode.THROTTLE
            self._step(state.grid_power)
        else:
            self.mode = Mode.FULL
            self._limit = 100

        return self._limit

    def _step(self, grid_power: float) -> None:
        if grid_power < -DEAD_BAND_W:
            self._limit -= self._step_size
        elif grid_power > DEAD_BAND_W and self._limit < 100:
            self._limit += self._step_size
        self._limit = max(0, min(100, self._limit))
