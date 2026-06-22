from __future__ import annotations

import numpy as np
import pandas as pd


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
