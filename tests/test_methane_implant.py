import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_tea import load_project_params  # noqa: E402
from tea import methane_implant as m  # noqa: E402
from tea.inputs import base_values  # noqa: E402


@pytest.fixture
def v():
    return base_values(load_project_params(ROOT / "inputs" / "methane_implant.toml"))


def test_avoided_by_hand(v):
    assert m.avoided_t(v, "dairy") == pytest.approx(0.117 * 27 * 0.20)
    assert m.avoided_t(v, "beef") == pytest.approx(0.072 * 27 * 0.20)


def test_cost_per_t_by_hand(v):
    assert m.cost_per_t(v, "dairy") == pytest.approx((15 + 0.5) / (0.117 * 27 * 0.20))
    assert m.bovaer_cost_per_t(v) == pytest.approx(99 / (0.117 * 27 * 0.28))


def test_farmer_net_by_hand(v):
    credits = 0.117 * 27 * 0.20 * 30 * (1 - 0.15)
    assert m.farmer_net(v, "dairy") == pytest.approx(credits + 12 - (15 + 8 + 0.5))
    beef_credits = 0.072 * 27 * 0.20 * 15 * 0.85
    assert m.farmer_net(v, "beef") == pytest.approx(beef_credits - (4 + 0.5))


def test_share_ramp(v):
    assert m.share(v, "dairy", 0) == 0
    assert m.share(v, "dairy", 4) == pytest.approx(0.25 * 4 / 8)
    assert m.share(v, "dairy", 20) == pytest.approx(0.25)


def test_rd_years_have_no_revenue(v):
    r = m.run(v)
    assert all(y.revenue == 0 for y in r.years[: int(v["company.rd_years"])])


def test_first_sales_year_by_hand(v):
    y = m.run(v).years[int(v["company.rd_years"])]
    dairy, beef = 30e6 * 0.25 / 8, 100e6 * 0.10 / 8
    assert y.revenue_by_stream["implants"] == pytest.approx(dairy * 15 + beef * 4)
    assert y.revenue_by_stream["data"] == pytest.approx(dairy * 0.30 * 8)


def test_six_month_implant_doubles_doses_and_handling(v):
    v6 = {**v, "implant.duration_months": 6}
    assert m.doses_per_year(v6) == 2
    assert m.farmer_cost(v6, "beef") == pytest.approx(4 + 2 * 0.5)
    assert m.run(v6).npv < m.run(v).npv


def test_dairy_beats_bovaer_per_tonne(v):
    assert m.cost_per_t(v, "dairy") < m.bovaer_cost_per_t(v)
