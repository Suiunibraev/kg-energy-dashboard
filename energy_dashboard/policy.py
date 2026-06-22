from __future__ import annotations

import numpy as np
import pandas as pd


POLICY_RULES = {
    "high_deficit_pct": 15,
    "moderate_deficit_pct": 5,
    "high_import_dependency_pct": 20,
    "moderate_import_dependency_pct": 10,
    "hydro_vulnerability_pct": 75,
    "high_demand_growth_pct": 4,
    "moderate_demand_growth_pct": 2,
    "low_reserve_margin_pct": 5,
}


def _clip(value: float, lower: float, upper: float) -> float:
    return float(max(lower, min(upper, value)))


def security_band(score: float) -> tuple[str, str]:
    if score >= 75:
        return "Secure", "green"
    if score >= 50:
        return "Moderate Risk", "amber"
    return "High Risk", "red"


def calculate_security_index(national: pd.DataFrame, forecast: pd.DataFrame) -> dict[str, float | str]:
    latest = national.sort_values("year").iloc[-1]
    recent = national.sort_values("year").tail(6)
    future = forecast[forecast["period"].eq("Forecast")].head(12)

    balance_ratio = latest["production_twh"] / latest["consumption_twh"]
    balance_score = _clip(balance_ratio / 1.05, 0, 1) * 35

    hydro_share = float(latest.get("hydro_share_pct", 0))
    hydro_score = _clip(1 - max(0, hydro_share - 55) / 40, 0, 1) * 20

    if len(recent) >= 2:
        demand_growth = recent["consumption_twh"].pct_change().tail(5).mean()
    else:
        demand_growth = 0.0
    growth_score = _clip((0.065 - demand_growth) / 0.055, 0, 1) * 20

    forecast_demand = float(future["forecast_twh"].sum()) if not future.empty else float(latest["consumption_twh"])
    reserve_margin = (float(latest["production_twh"]) - forecast_demand) / forecast_demand
    reserve_score = _clip((reserve_margin + 0.20) / 0.35, 0, 1) * 25

    score = round(balance_score + hydro_score + growth_score + reserve_score, 1)
    label, color = security_band(score)
    return {
        "score": score,
        "label": label,
        "color": color,
        "demand_growth_pct": round(demand_growth * 100, 1),
        "reserve_margin_pct": round(reserve_margin * 100, 1),
        "hydro_share_pct": round(hydro_share, 1),
        "production_coverage_pct": round(balance_ratio * 100, 1),
    }


def evaluate_policy_rules(national: pd.DataFrame, security: dict) -> pd.DataFrame:
    latest = national.sort_values("year").iloc[-1]
    demand = float(latest["consumption_twh"])
    deficit_pct = max(0, -float(latest["domestic_gap_twh"]) / demand * 100)
    import_dependency_pct = max(0, float(latest["net_imports_twh"]) / demand * 100)
    hydro_share = float(latest["hydro_share_pct"])
    demand_growth = float(security["demand_growth_pct"])
    reserve_margin = float(security["reserve_margin_pct"])

    rows = [
        {
            "Policy rule": "Domestic deficit",
            "Trigger": f"High > {POLICY_RULES['high_deficit_pct']}%, Moderate > {POLICY_RULES['moderate_deficit_pct']}%",
            "Current value": f"{deficit_pct:.1f}%",
            "Status": _risk_label(deficit_pct, POLICY_RULES["high_deficit_pct"], POLICY_RULES["moderate_deficit_pct"]),
        },
        {
            "Policy rule": "Import dependency",
            "Trigger": f"High > {POLICY_RULES['high_import_dependency_pct']}%, Moderate > {POLICY_RULES['moderate_import_dependency_pct']}%",
            "Current value": f"{import_dependency_pct:.1f}%",
            "Status": _risk_label(
                import_dependency_pct,
                POLICY_RULES["high_import_dependency_pct"],
                POLICY_RULES["moderate_import_dependency_pct"],
            ),
        },
        {
            "Policy rule": "Hydropower seasonal vulnerability",
            "Trigger": f"Flag if hydro share > {POLICY_RULES['hydro_vulnerability_pct']}%",
            "Current value": f"{hydro_share:.1f}%",
            "Status": "Flagged" if hydro_share > POLICY_RULES["hydro_vulnerability_pct"] else "Normal",
        },
        {
            "Policy rule": "Demand growth pressure",
            "Trigger": f"High > {POLICY_RULES['high_demand_growth_pct']}%, Moderate > {POLICY_RULES['moderate_demand_growth_pct']}%",
            "Current value": f"{demand_growth:.1f}%",
            "Status": _risk_label(
                demand_growth,
                POLICY_RULES["high_demand_growth_pct"],
                POLICY_RULES["moderate_demand_growth_pct"],
            ),
        },
        {
            "Policy rule": "Forecast reserve margin",
            "Trigger": f"Flag if reserve margin < {POLICY_RULES['low_reserve_margin_pct']}%",
            "Current value": f"{reserve_margin:.1f}%",
            "Status": "Flagged" if reserve_margin < POLICY_RULES["low_reserve_margin_pct"] else "Normal",
        },
    ]
    return pd.DataFrame(rows)


def _risk_label(value: float, high: float, moderate: float) -> str:
    if value > high:
        return "High"
    if value > moderate:
        return "Moderate"
    return "Normal"


def time_intelligence(national: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    out = national.sort_values("year").copy()
    out["demand_yoy_pct"] = out["consumption_twh"].pct_change() * 100
    out["production_yoy_pct"] = out["production_twh"].pct_change() * 100
    out["demand_3yr_avg_twh"] = out["consumption_twh"].rolling(3, min_periods=1).mean()
    out["production_3yr_avg_twh"] = out["production_twh"].rolling(3, min_periods=1).mean()
    out["seasonal_deviation_index"] = (
        (out["consumption_twh"] - out["demand_3yr_avg_twh"]) / out["demand_3yr_avg_twh"] * 100
    ).fillna(0)
    latest = out.iloc[-1]
    previous = out.iloc[-2] if len(out) > 1 else latest
    changes = {
        "demand_yoy_pct": round(float(latest["demand_yoy_pct"] if pd.notna(latest["demand_yoy_pct"]) else 0), 1),
        "production_yoy_pct": round(
            float(latest["production_yoy_pct"] if pd.notna(latest["production_yoy_pct"]) else 0), 1
        ),
        "imports_yoy_pct": round(_pct_change(float(previous["net_imports_twh"]), float(latest["net_imports_twh"])), 1),
        "hydro_share_change_pct": round(float(latest["hydro_share_pct"] - previous["hydro_share_pct"]), 1),
        "seasonal_deviation_index": round(float(latest["seasonal_deviation_index"]), 1),
    }
    return out, changes


def _pct_change(previous: float, current: float) -> float:
    if abs(previous) < 1e-9:
        return 0.0
    return (current / previous - 1) * 100


def situation_briefing(security: dict, rules: pd.DataFrame, changes: dict) -> dict[str, str]:
    flagged = rules[rules["Status"].isin(["High", "Flagged"])]["Policy rule"].tolist()
    main_driver = flagged[0] if flagged else "System balance"
    if changes["demand_yoy_pct"] > POLICY_RULES["moderate_demand_growth_pct"]:
        main_driver = "Rising demand"
    key_concern = "Hydropower variability" if "Hydropower seasonal vulnerability" in flagged else main_driver
    outlook = "Stable in normal conditions, risk increases under dry hydropower conditions"
    if security["label"] == "Secure":
        outlook = "Stable under current assumptions"
    elif security["label"] == "High Risk":
        outlook = "Elevated risk without imports, demand response, or additional dispatchable supply"

    return {
        "status": str(security["label"]),
        "main_driver": main_driver,
        "key_concern": key_concern,
        "outlook": outlook,
    }


def recommended_actions(
    national: pd.DataFrame,
    regional_risk: pd.DataFrame,
    rules: pd.DataFrame,
    peaks: dict,
    security: dict,
) -> pd.DataFrame:
    latest = national.sort_values("year").iloc[-1]
    demand = float(latest["consumption_twh"])
    deficit = max(0, -float(latest["domestic_gap_twh"]))
    winter_peak = float(peaks["winter_peak_twh"])
    high_region = regional_risk.iloc[0]["region"] if not regional_risk.empty else "highest-risk region"

    actions = []
    if deficit > 0:
        actions.append(
            {
                "Priority": "High",
                "Recommended action": f"Secure winter import or reserve contracts covering at least {deficit * 0.25:.1f} TWh.",
                "Reason": "Domestic generation is below current consumption before trade.",
            }
        )
    if float(security["hydro_share_pct"]) > POLICY_RULES["hydro_vulnerability_pct"]:
        actions.append(
            {
                "Priority": "High",
                "Recommended action": "Prepare dry-year hydropower contingency dispatch and maintenance schedule.",
                "Reason": "Hydropower dependency creates seasonal and climate vulnerability.",
            }
        )
    if winter_peak > demand / 12 * 1.15:
        actions.append(
            {
                "Priority": "Medium",
                "Recommended action": "Target winter demand-response measures for peak months.",
                "Reason": "Peak risk is concentrated in winter rather than annual totals.",
            }
        )
    actions.append(
        {
            "Priority": "Medium",
            "Recommended action": f"Prioritize grid reinforcement and loss reduction in {high_region}.",
            "Reason": "Regional ranking combines deficits, demand concentration, and distribution losses.",
        }
    )
    if not rules[rules["Status"].isin(["High", "Flagged"])].empty:
        actions.append(
            {
                "Priority": "Medium",
                "Recommended action": "Review flagged policy rules in the weekly system planning meeting.",
                "Reason": "Auditable thresholds show which risks crossed predefined limits.",
            }
        )
    return pd.DataFrame(actions)


def executive_summary(national: pd.DataFrame, forecast: pd.DataFrame, scenario: str, security: dict) -> str:
    latest = national.sort_values("year").iloc[-1]
    future = forecast[forecast["period"].eq("Forecast")].head(12)
    next_year_demand = float(future["forecast_twh"].sum()) if not future.empty else float(latest["consumption_twh"])
    demand_change = (next_year_demand / latest["consumption_twh"] - 1) * 100
    deficit = float(latest["domestic_gap_twh"])
    direction = "above" if deficit >= 0 else "below"
    risk_phrase = "elevated winter supply risk" if security["label"] != "Secure" else "manageable near-term supply risk"
    return (
        f"National electricity demand is projected to change by {demand_change:.1f}% over the next 12 months. "
        f"Domestic production is {abs(deficit):.1f} TWh {direction} current consumption before trade. "
        f"Under the {scenario.lower()} scenario, the energy security index is {security['score']:.1f}/100, "
        f"indicating {risk_phrase}."
    )


def peak_demand_summary(forecast: pd.DataFrame) -> dict[str, float | pd.Timestamp]:
    future = forecast[forecast["period"].eq("Forecast")].copy()
    if future.empty:
        return {"winter_peak_twh": 0.0, "summer_peak_twh": 0.0, "winter_peak_date": pd.NaT, "summer_peak_date": pd.NaT}

    winter = future[future["date"].dt.month.isin([12, 1, 2])]
    summer = future[future["date"].dt.month.isin([6, 7, 8])]
    winter_row = winter.loc[winter["forecast_twh"].idxmax()] if not winter.empty else future.loc[future["forecast_twh"].idxmax()]
    summer_row = summer.loc[summer["forecast_twh"].idxmax()] if not summer.empty else future.loc[future["forecast_twh"].idxmin()]
    return {
        "winter_peak_twh": round(float(winter_row["forecast_twh"]), 2),
        "summer_peak_twh": round(float(summer_row["forecast_twh"]), 2),
        "winter_peak_date": winter_row["date"],
        "summer_peak_date": summer_row["date"],
    }


def regional_risk_ranking(regional: pd.DataFrame) -> pd.DataFrame:
    ranked = regional.copy()
    deficit_ratio = ((ranked["consumption_gwh"] - ranked["production_gwh"]).clip(lower=0) / ranked["consumption_gwh"]).fillna(0)
    losses_score = (ranked["distribution_losses_pct"] / ranked["distribution_losses_pct"].max()).fillna(0)
    demand_score = (ranked["consumption_gwh"] / ranked["consumption_gwh"].max()).fillna(0)
    ranked["risk_score"] = (deficit_ratio * 60 + losses_score * 25 + demand_score * 15).round(1)
    ranked["risk"] = np.select(
        [ranked["risk_score"].ge(65), ranked["risk_score"].ge(35)],
        ["High", "Medium"],
        default="Low",
    )
    return ranked.sort_values(["risk_score", "consumption_gwh"], ascending=False).reset_index(drop=True)
