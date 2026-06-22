from energy_dashboard.data_sources import load_energy_dataset, load_regional_dataset
from energy_dashboard.forecasting import forecast_demand


def test_national_data_contract():
    national, statuses = load_energy_dataset()
    required = {
        "year",
        "production_twh",
        "consumption_twh",
        "hydro_twh",
        "thermal_twh",
        "imports_twh",
        "exports_twh",
        "domestic_gap_twh",
        "net_balance_twh",
        "surplus_deficit_twh",
        "hydro_share_pct",
    }
    assert required.issubset(national.columns)
    assert len(national) >= 10
    assert statuses


def test_regional_data_contract():
    regional = load_regional_dataset()
    assert {"region", "lat", "lon", "production_gwh", "consumption_gwh", "balance_gwh"}.issubset(regional.columns)
    assert regional["region"].nunique() >= 7


def test_forecast_contract():
    national, _ = load_energy_dataset()
    forecast = forecast_demand(national, months=12, scenario="Dry year")
    future = forecast[forecast["period"].eq("Forecast")]
    assert len(future) == 12
    assert (future["upper_twh"] >= future["forecast_twh"]).all()
    assert (future["lower_twh"] <= future["forecast_twh"]).all()
