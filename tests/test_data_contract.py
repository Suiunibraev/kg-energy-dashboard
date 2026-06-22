from energy_dashboard.data_sources import load_energy_dataset, load_regional_dataset
from energy_dashboard.forecasting import forecast_demand
from energy_dashboard.policy import (
    calculate_security_index,
    evaluate_policy_rules,
    peak_demand_summary,
    recommended_actions,
    regional_risk_ranking,
)


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


def test_security_index_contract():
    national, _ = load_energy_dataset()
    national["net_imports_twh"] = national["imports_twh"] - national["exports_twh"]
    forecast = forecast_demand(national, months=12, scenario="Normal year")
    security = calculate_security_index(national, forecast)
    assert 0 <= security["score"] <= 100
    assert security["label"] in {"Secure", "Moderate Risk", "High Risk"}
    assert {"production_coverage_pct", "hydro_share_pct", "reserve_margin_pct"}.issubset(security)


def test_policy_rules_contract():
    national, _ = load_energy_dataset()
    national["net_imports_twh"] = national["imports_twh"] - national["exports_twh"]
    forecast = forecast_demand(national, months=12, scenario="Normal year")
    security = calculate_security_index(national, forecast)
    rules = evaluate_policy_rules(national, security)
    assert {"Policy rule", "Trigger", "Current value", "Status"}.issubset(rules.columns)
    assert len(rules) >= 5
    assert set(rules["Status"]).issubset({"Normal", "Moderate", "High", "Flagged"})


def test_regional_risk_and_actions_contract():
    national, _ = load_energy_dataset()
    national["net_imports_twh"] = national["imports_twh"] - national["exports_twh"]
    forecast = forecast_demand(national, months=12, scenario="Normal year")
    security = calculate_security_index(national, forecast)
    rules = evaluate_policy_rules(national, security)
    peaks = peak_demand_summary(forecast)
    regional_risk = regional_risk_ranking(load_regional_dataset())
    actions = recommended_actions(national, regional_risk, rules, peaks, security)
    assert {"region", "risk", "risk_score"}.issubset(regional_risk.columns)
    assert regional_risk["risk_score"].is_monotonic_decreasing
    assert {"Priority", "Recommended action", "Reason"}.issubset(actions.columns)
    assert len(actions) >= 1
