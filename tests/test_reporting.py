from energy_dashboard.data_sources import _fallback_national_data
from energy_dashboard.forecasting import SCENARIOS, forecast_demand
from energy_dashboard.policy import (
    calculate_security_index,
    evaluate_policy_rules,
    executive_summary,
    peak_demand_summary,
    recommended_actions,
    scenario_impact_analysis,
    security_index_breakdown,
    situation_briefing,
    time_intelligence,
    year_over_year_summary,
)
from energy_dashboard.reporting import build_ministry_briefing_pdf


def test_briefing_pdf_builds_with_metadata():
    national = _fallback_national_data()
    national["domestic_gap_twh"] = national["production_twh"] - national["consumption_twh"]
    national["hydro_share_pct"] = national["hydro_twh"] / national["production_twh"] * 100
    national["net_imports_twh"] = national["imports_twh"] - national["exports_twh"]

    forecasts = {name: forecast_demand(national, months=12, scenario=name) for name in SCENARIOS}
    forecast = forecasts["Normal year"]
    security = calculate_security_index(national, forecast)
    rules = evaluate_policy_rules(national, security)
    national, changes = time_intelligence(national)
    impacts, impact_summary = scenario_impact_analysis(national, forecasts)

    pdf = build_ministry_briefing_pdf(
        national.iloc[-1],
        security,
        situation_briefing(security, rules, changes),
        executive_summary(national, forecast, "Normal year", security),
        recommended_actions(national, rules, peak_demand_summary(forecast), security),
        rules,
        impacts,
        impact_summary,
        security_index_breakdown(national, forecast),
        changes,
        year_over_year_summary(changes),
    )

    assert pdf.startswith(b"%PDF")
    assert b"Kyrgyzstan Energy Situation Briefing 2024" in pdf
