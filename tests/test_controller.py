from controller import Controller, Mode
from evcc import EvccState


def _state(grid_power=0.0, tariff_feed_in=0.05, tariff_grid=0.15, pv_power=3000.0):
    return EvccState(
        grid_power=grid_power,
        tariff_feed_in=tariff_feed_in,
        tariff_grid=tariff_grid,
        pv_power=pv_power,
    )


def test_mode_full_both_positive():
    ctrl = Controller(step_size=5)
    limit = ctrl.update(_state(tariff_feed_in=0.05, tariff_grid=0.15))
    assert ctrl.mode == Mode.FULL
    assert limit == 100


def test_mode_grid_off_negative_consumption():
    ctrl = Controller(step_size=5)
    limit = ctrl.update(_state(tariff_grid=-0.05, tariff_feed_in=0.05))
    assert ctrl.mode == Mode.GRID_OFF
    assert limit == 0


def test_mode_grid_off_priority_over_throttle():
    ctrl = Controller(step_size=5)
    limit = ctrl.update(_state(tariff_grid=-0.05, tariff_feed_in=-0.02))
    assert ctrl.mode == Mode.GRID_OFF
    assert limit == 0


def test_mode_throttle_negative_feedin():
    ctrl = Controller(step_size=5)
    limit = ctrl.update(_state(tariff_feed_in=-0.02, tariff_grid=0.15, grid_power=0.0))
    assert ctrl.mode == Mode.THROTTLE


def test_throttle_decrease_on_export():
    ctrl = Controller(step_size=5)
    ctrl.update(_state(tariff_feed_in=0.05))
    limit = ctrl.update(_state(tariff_feed_in=-0.02, grid_power=-500.0))
    assert limit == 95


def test_throttle_increase_on_import():
    ctrl = Controller(step_size=5)
    ctrl._limit = 80
    limit = ctrl.update(_state(tariff_feed_in=-0.02, grid_power=500.0))
    assert limit == 85


def test_throttle_hold_in_dead_band():
    ctrl = Controller(step_size=5)
    ctrl._limit = 70
    limit = ctrl.update(_state(tariff_feed_in=-0.02, grid_power=30.0))
    assert limit == 70


def test_throttle_clamp_at_zero():
    ctrl = Controller(step_size=5)
    ctrl._limit = 2
    limit = ctrl.update(_state(tariff_feed_in=-0.02, grid_power=-500.0))
    assert limit == 0


def test_throttle_clamp_at_100():
    ctrl = Controller(step_size=5)
    ctrl._limit = 98
    limit = ctrl.update(_state(tariff_feed_in=-0.02, grid_power=500.0))
    assert limit == 100


def test_transition_throttle_to_full():
    ctrl = Controller(step_size=5)
    ctrl._limit = 60
    ctrl.update(_state(tariff_feed_in=-0.02, grid_power=0.0))
    assert ctrl.mode == Mode.THROTTLE

    limit = ctrl.update(_state(tariff_feed_in=0.05, tariff_grid=0.15))
    assert ctrl.mode == Mode.FULL
    assert limit == 100


def test_transition_full_to_throttle_starts_from_current():
    ctrl = Controller(step_size=5)
    ctrl.update(_state(tariff_feed_in=0.05))
    limit = ctrl.update(_state(tariff_feed_in=-0.02, grid_power=-500.0))
    assert ctrl.mode == Mode.THROTTLE
    assert limit == 95


def test_no_increase_at_100_in_throttle():
    ctrl = Controller(step_size=5)
    ctrl._limit = 100
    limit = ctrl.update(_state(tariff_feed_in=-0.02, grid_power=500.0))
    assert limit == 100
