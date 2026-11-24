import pandas as pd
import pytest

from energy_dashboard.data_sources import _fallback_national_data
from energy_dashboard.forecasting import build_monthly_history, forecast_demand


def test_monthly_history_preserves_annual_totals():
    national = _fallback_national_data()
    monthly = build_monthly_history(national)
    annual = monthly.groupby("year")[["consumption_twh", "hydro_twh"]].sum()
    expected = national.set_index("year").loc[annual.index, ["consumption_twh", "hydro_twh"]]
    pd.testing.assert_frame_equal(annual, expected, check_dtype=False, atol=1e-9)
    assert monthly.groupby("year").size().eq(12).all()
    assert monthly["year"].nunique() <= 10


def test_forecast_shape_and_bounds():
    forecast = forecast_demand(_fallback_national_data(), months=18, scenario="Normal year")
    future = forecast[forecast["period"].eq("Forecast")]
    assert len(future) == 18
    assert future["date"].diff().dropna().dt.days.between(28, 31).all()
    assert (future["lower_twh"] >= 0).all()
    assert (future["lower_twh"] <= future["forecast_twh"]).all()
    assert (future["forecast_twh"] <= future["upper_twh"]).all()


def test_dry_scenario_raises_demand_and_lowers_hydro():
    national = _fallback_national_data()
    normal = forecast_demand(national, months=12, scenario="Normal year")
    dry = forecast_demand(national, months=12, scenario="Dry year")
    normal_future = normal[normal["period"].eq("Forecast")]
    dry_future = dry[dry["period"].eq("Forecast")]
    assert dry_future["forecast_twh"].sum() > normal_future["forecast_twh"].sum()
    assert dry_future["hydro_availability_index"].iloc[0] < 1


def test_unknown_scenario_falls_back_to_normal():
    national = _fallback_national_data()
    normal = forecast_demand(national, months=6, scenario="Normal year")
    unknown = forecast_demand(national, months=6, scenario="Unknown")
    assert normal["forecast_twh"].round(9).equals(unknown["forecast_twh"].round(9))


def test_non_positive_horizon_is_rejected():
    with pytest.raises(ValueError):
        forecast_demand(_fallback_national_data(), months=0, scenario="Normal year")
