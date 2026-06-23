import pytest

from energy_dashboard.data_sources import (
    SourceStatus,
    _fallback_national_data,
    add_regional_planning_metrics,
    load_energy_dataset,
    load_regional_dataset,
    national_data_mode,
)
from energy_dashboard.forecasting import forecast_demand
from energy_dashboard.policy import (
    calculate_security_index,
    executive_summary,
    evaluate_policy_rules,
    peak_demand_summary,
    recommended_actions,
    security_index_breakdown,
)
from energy_dashboard.ui import forecast_chart


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
    required = {
        "year",
        "region",
        "source_region_label",
        "territory_type",
        "lat",
        "lon",
        "useful_supply_gwh",
        "metric",
        "data_quality",
        "data_provenance",
        "source_organization",
        "source_document",
        "source_url",
    }
    assert required.issubset(regional.columns)
    assert len(regional) == 8
    assert regional["year"].eq(2024).all()
    assert regional["territory_type"].eq("PES service territory").all()
    assert regional["data_quality"].eq("Official").all()
    assert regional["data_provenance"].str.len().gt(0).all()
    assert regional["source_url"].str.startswith("https://esep.energo.kg/").all()
    assert regional["source_organization"].eq("Kyrgyz Electricity Settlement Center").all()
    assert regional["metric"].eq("Useful electricity supply through PES networks").all()
    assert abs(regional["useful_supply_gwh"].sum() - 12_597.767126) < 1e-6
    assert "consumption_gwh" not in regional.columns
    assert "Osh service territory" in set(regional["region"])
    assert "Osh City" not in set(regional["region"])
    assert regional["production_gwh"].isna().all()
    assert regional["distribution_losses_pct"].isna().all()
    assert regional["balance_gwh"].isna().all()
    assert regional["status"].eq("Not available").all()

    national, _ = load_energy_dataset()
    planning = add_regional_planning_metrics(regional, national)
    assert {
        "population",
        "demand_per_capita_kwh",
        "demand_share_pct",
        "population_data_quality",
        "useful_supply_data_quality",
        "production_data_quality",
        "distribution_losses_data_quality",
        "balance_data_quality",
        "demand_per_capita_data_quality",
        "demand_share_data_quality",
        "risk_data_quality",
    }.issubset(planning.columns)
    assert planning["population"].notna().all()
    assert planning["population_data_quality"].eq("Official source / mapped").all()
    assert planning["population_alignment_note"].str.contains("boundary alignment may be approximate").all()
    assert planning["useful_supply_data_quality"].eq("Official").all()
    assert planning["production_data_quality"].eq("Not available").all()
    assert planning["distribution_losses_data_quality"].eq("Not available").all()
    assert planning["balance_data_quality"].eq("Not available").all()
    assert planning["risk_data_quality"].eq("Not available").all()
    assert planning["demand_per_capita_data_quality"].eq("Derived").all()
    assert planning["demand_share_data_quality"].eq("Derived").all()


def test_forecast_contract():
    national, _ = load_energy_dataset()
    forecast = forecast_demand(national, months=12, scenario="Dry year")
    future = forecast[forecast["period"].eq("Forecast")]
    assert len(future) == 12
    assert (future["upper_twh"] >= future["forecast_twh"]).all()
    assert (future["lower_twh"] <= future["forecast_twh"]).all()


def test_forecast_credibility_labels_preserve_numeric_output():
    national = _fallback_national_data()
    forecast = forecast_demand(national, months=12, scenario="Normal year")
    future = forecast[forecast["period"].eq("Forecast")]
    history = forecast[forecast["period"].eq("Estimated history")]

    assert len(history) == 120
    assert "Observed" not in set(forecast["period"])
    assert future["forecast_twh"].sum() == pytest.approx(16.491413435686457)
    assert future.iloc[0]["forecast_twh"] == pytest.approx(1.7356400545579889)

    figure = forecast_chart(forecast)
    trace_names = [trace.name for trace in figure.data]
    assert "Estimated monthly history" in trace_names
    assert "Illustrative upper model range" in trace_names
    assert "Illustrative lower model range" in trace_names
    assert not any("confidence" in (trace.name or "").lower() for trace in figure.data)
    assert not any("likely" in (trace.name or "").lower() for trace in figure.data)


def test_security_index_contract():
    national, _ = load_energy_dataset()
    national["net_imports_twh"] = national["imports_twh"] - national["exports_twh"]
    forecast = forecast_demand(national, months=12, scenario="Normal year")
    security = calculate_security_index(national, forecast)
    assert 0 <= security["score"] <= 100
    assert security["label"] in {"Secure", "Moderate Risk", "High Risk"}
    assert {"production_coverage_pct", "hydro_share_pct", "reserve_margin_pct"}.issubset(security)


def test_security_index_uses_fixed_twelve_month_window():
    national, _ = load_energy_dataset()
    national["net_imports_twh"] = national["imports_twh"] - national["exports_twh"]
    forecast_12 = forecast_demand(national, months=12, scenario="Normal year")
    forecast_18 = forecast_demand(national, months=18, scenario="Normal year")

    security_12 = calculate_security_index(national, forecast_12)
    security_18 = calculate_security_index(national, forecast_18)
    assert security_12 == security_18

    breakdown = security_index_breakdown(national, forecast_18)
    assert round(breakdown["score"].sum(), 1) == security_18["score"]
    assert breakdown["weight"].tolist() == [35, 20, 20, 25]

    forecast_6 = forecast_demand(national, months=6, scenario="Normal year")
    with pytest.raises(ValueError, match="fixed 12-month"):
        calculate_security_index(national, forecast_6)


def test_executive_summary_uses_exact_model_period():
    national, _ = load_energy_dataset()
    national["net_imports_twh"] = national["imports_twh"] - national["exports_twh"]
    forecast = forecast_demand(national, months=12, scenario="Normal year")
    security = calculate_security_index(national, forecast)
    future = forecast[forecast["period"].eq("Forecast")]

    summary = executive_summary(national, forecast, "Normal year", security)
    expected_period = f"{future['date'].min():%B %Y} to {future['date'].max():%B %Y}"
    assert expected_period in summary
    assert "over the next 12 months" not in summary


def test_national_data_mode_distinguishes_fallback():
    live_statuses = [
        SourceStatus("Our World in Data", "live", "ok", "2026-01-01 00:00 UTC"),
        SourceStatus("World Bank", "fallback", "unavailable", "2026-01-01 00:00 UTC"),
    ]
    fallback_statuses = [
        SourceStatus("Our World in Data", "fallback", "unavailable", "2026-01-01 00:00 UTC"),
        SourceStatus("World Bank", "live", "ok", "2026-01-01 00:00 UTC"),
    ]
    assert national_data_mode(live_statuses) == "live"
    assert national_data_mode(fallback_statuses) == "fallback"
    assert national_data_mode([]) == "fallback"


def test_policy_rules_contract():
    national, _ = load_energy_dataset()
    national["net_imports_twh"] = national["imports_twh"] - national["exports_twh"]
    forecast = forecast_demand(national, months=12, scenario="Normal year")
    security = calculate_security_index(national, forecast)
    rules = evaluate_policy_rules(national, security)
    assert {"Policy rule", "Trigger", "Current value", "Status"}.issubset(rules.columns)
    assert len(rules) >= 5
    assert set(rules["Status"]).issubset({"Normal", "Moderate", "High", "Flagged"})


def test_actions_do_not_use_unavailable_regional_risk():
    national, _ = load_energy_dataset()
    national["net_imports_twh"] = national["imports_twh"] - national["exports_twh"]
    forecast = forecast_demand(national, months=12, scenario="Normal year")
    security = calculate_security_index(national, forecast)
    rules = evaluate_policy_rules(national, security)
    peaks = peak_demand_summary(forecast)
    actions = recommended_actions(national, rules, peaks, security)
    assert {"Priority", "Recommended action", "Reason"}.issubset(actions.columns)
    assert len(actions) >= 1
    action_text = " ".join(actions["Recommended action"].astype(str)).lower()
    assert "highest-risk region" not in action_text
    assert "loss reduction in" not in action_text
    assert "covering at least" not in action_text
