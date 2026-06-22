from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing


SCENARIOS = {
    "Normal year": {"demand_multiplier": 1.00, "hydro_multiplier": 1.00},
    "Dry year": {"demand_multiplier": 1.04, "hydro_multiplier": 0.88},
    "Wet year": {"demand_multiplier": 0.98, "hydro_multiplier": 1.08},
}


def build_monthly_history(national: pd.DataFrame) -> pd.DataFrame:
    latest_year = int(national["year"].max())
    start_year = max(int(national["year"].min()), latest_year - 9)
    annual = national[national["year"].between(start_year, latest_year)].copy()

    rows: list[dict[str, float | int | pd.Timestamp]] = []
    winter_weights = np.array([1.22, 1.15, 1.04, 0.92, 0.82, 0.75, 0.72, 0.74, 0.86, 0.98, 1.12, 1.28])
    winter_weights = winter_weights / winter_weights.sum()
    hydro_weights = np.array([0.055, 0.052, 0.061, 0.078, 0.102, 0.122, 0.126, 0.118, 0.098, 0.076, 0.060, 0.052])
    hydro_weights = hydro_weights / hydro_weights.sum()

    for _, row in annual.iterrows():
        for month in range(1, 13):
            rows.append(
                {
                    "date": pd.Timestamp(int(row["year"]), month, 1),
                    "year": int(row["year"]),
                    "month": month,
                    "consumption_twh": row["consumption_twh"] * winter_weights[month - 1],
                    "hydro_twh": row["hydro_twh"] * hydro_weights[month - 1],
                }
            )
    return pd.DataFrame(rows)


def forecast_demand(national: pd.DataFrame, months: int, scenario: str) -> pd.DataFrame:
    monthly = build_monthly_history(national)
    series = monthly.set_index("date")["consumption_twh"].asfreq("MS")
    params = SCENARIOS.get(scenario, SCENARIOS["Normal year"])

    try:
        model = ExponentialSmoothing(
            series,
            trend="add",
            seasonal="mul",
            seasonal_periods=12,
            initialization_method="estimated",
        ).fit(optimized=True)
        forecast = model.forecast(months)
        fitted = model.fittedvalues
        residual_std = float((series - fitted).dropna().std())
    except Exception:  # noqa: BLE001 - fallback keeps the dashboard usable.
        seasonal_pattern = series.groupby(series.index.month).mean()
        last_value = series.iloc[-1]
        future_index = pd.date_range(series.index[-1] + pd.offsets.MonthBegin(1), periods=months, freq="MS")
        trend = np.linspace(1.0, 1.04, months)
        forecast = pd.Series(
            [seasonal_pattern.loc[date.month] * trend[i] for i, date in enumerate(future_index)],
            index=future_index,
        )
        residual_std = float(series.diff(12).dropna().std() or last_value * 0.08)

    forecast = forecast * params["demand_multiplier"]
    future = forecast.reset_index()
    future.columns = ["date", "forecast_twh"]
    future["lower_twh"] = (future["forecast_twh"] - 1.64 * residual_std).clip(lower=0)
    future["upper_twh"] = future["forecast_twh"] + 1.64 * residual_std
    future["scenario"] = scenario
    future["hydro_availability_index"] = params["hydro_multiplier"]
    future["period"] = "Forecast"

    history = monthly[["date", "consumption_twh"]].rename(columns={"consumption_twh": "forecast_twh"})
    history["lower_twh"] = np.nan
    history["upper_twh"] = np.nan
    history["scenario"] = "Observed"
    history["hydro_availability_index"] = 1.0
    history["period"] = "Observed"
    return pd.concat([history, future], ignore_index=True)
