import pytest

from apuestas.ml.xgboost.odds_utils import devig


def test_devig_handles_none():
    assert devig(None, None, None) == (None, None, None)


def test_devig_sums_to_one():
    fair = devig(2.0, 3.5, 4.0)
    total = sum(p for p in fair if p is not None)
    assert total == pytest.approx(1.0, abs=1e-3)
