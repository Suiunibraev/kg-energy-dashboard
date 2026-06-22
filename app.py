from __future__ import annotations

import pandas as pd
import streamlit as st

from energy_dashboard.data_sources import load_energy_dataset, load_regional_dataset
from energy_dashboard.forecasting import SCENARIOS, forecast_demand
from energy_dashboard.policy import (
    calculate_security_index,
    executive_summary,
    peak_demand_summary,
    regional_risk_ranking,
)
from energy_dashboard.ui import (
    apply_theme,
    balance_chart,
    energy_mix_share_chart,
    forecast_chart,
    generation_mix_chart,
    line_chart,
    regional_bar_chart,
    regional_risk_chart,
    security_gauge,
    trade_chart,
)


st.set_page_config(
    page_title="Kyrgyzstan Energy Intelligence Dashboard",
    page_icon="KG",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


def ensure_national_metrics(national: pd.DataFrame) -> pd.DataFrame:
    national = national.copy()
    national["imports_twh"] = national.get("imports_twh", 0)
    national["exports_twh"] = national.get("exports_twh", 0)
    national["solar_twh"] = national.get("solar_twh", 0)
    national["wind_twh"] = national.get("wind_twh", 0)

    if "domestic_gap_twh" not in national:
        national["domestic_gap_twh"] = national["production_twh"] - national["consumption_twh"]
    if "net_balance_twh" not in national:
        national["net_balance_twh"] = (
            national["production_twh"] + national["imports_twh"] - national["consumption_twh"] - national["exports_twh"]
        )
    if "surplus_deficit_twh" not in national:
        national["surplus_deficit_twh"] = national["domestic_gap_twh"]
    if "hydro_share_pct" not in national:
        national["hydro_share_pct"] = national["hydro_twh"] / national["production_twh"] * 100
    national["net_imports_twh"] = national["imports_twh"] - national["exports_twh"]

    return national


@st.cache_data(ttl=3600)
def get_data() -> tuple[pd.DataFrame, pd.DataFrame, list]:
    national, statuses = load_energy_dataset()
    national = ensure_national_metrics(national)
    regional = load_regional_dataset()
    return national, regional, statuses


national_df, regional_df, source_statuses = get_data()

st.sidebar.title("Dashboard controls")
year_min = int(national_df["year"].min())
year_max = int(national_df["year"].max())
selected_years = st.sidebar.slider("Years shown", year_min, year_max, (max(year_min, year_max - 12), year_max))
scenario = st.sidebar.selectbox("Planning scenario", list(SCENARIOS.keys()), index=0)
months = st.sidebar.slider("Forecast horizon", 6, 36, 18, step=6)
st.sidebar.divider()
st.sidebar.caption("Data status")
for status in source_statuses:
    label = "Live" if status.status == "live" else "Fallback"
    st.sidebar.write(f"{status.name}: {label}")

filtered = national_df[national_df["year"].between(selected_years[0], selected_years[1])].copy()
latest = filtered.iloc[-1]
forecast_df = forecast_demand(national_df, months=months, scenario=scenario)
future = forecast_df[forecast_df["period"].eq("Forecast")]
security = calculate_security_index(filtered, forecast_df)
peaks = peak_demand_summary(forecast_df)
regional_risk = regional_risk_ranking(regional_df)

st.title("Kyrgyzstan Energy Intelligence Dashboard")
st.markdown(
    "A Ministry-ready monitoring and forecasting tool for electricity production, consumption, regional demand, and seasonal planning."
)

metric_cols = st.columns(6)
metric_cols[0].metric("Total production", f"{latest['production_twh']:.1f} TWh")
metric_cols[1].metric("Total consumption", f"{latest['consumption_twh']:.1f} TWh")
metric_cols[2].metric("Surplus / deficit before trade", f"{latest['domestic_gap_twh']:.1f} TWh")
metric_cols[3].metric("Balance after imports / exports", f"{latest['net_balance_twh']:.2f} TWh")
metric_cols[4].metric("Net imports", f"{latest['net_imports_twh']:.1f} TWh")
metric_cols[5].metric("Security index", f"{security['score']:.1f}/100", security["label"])

st.info(executive_summary(filtered, forecast_df, scenario, security))

tabs = st.tabs(["Policy overview", "National monitoring", "Regional view", "Seasonal forecast", "Data and handoff"])

with tabs[0]:
    st.subheader("Energy security overview")
    left, right = st.columns([0.9, 1.4])
    left.plotly_chart(security_gauge(security["score"], security["label"]), width="stretch")
    right.dataframe(
        pd.DataFrame(
            [
                {"Driver": "Production coverage", "Value": f"{security['production_coverage_pct']:.1f}%"},
                {"Driver": "Hydropower dependency", "Value": f"{security['hydro_share_pct']:.1f}%"},
                {"Driver": "Recent annual demand growth", "Value": f"{security['demand_growth_pct']:.1f}%"},
                {"Driver": "Forecast reserve margin", "Value": f"{security['reserve_margin_pct']:.1f}%"},
                {"Driver": "Winter peak demand", "Value": f"{peaks['winter_peak_twh']:.2f} TWh"},
                {"Driver": "Summer peak demand", "Value": f"{peaks['summer_peak_twh']:.2f} TWh"},
            ]
        ),
        width="stretch",
        hide_index=True,
    )
    st.plotly_chart(trade_chart(filtered), width="stretch")

with tabs[1]:
    st.subheader("National electricity trends")
    st.markdown(
        '<p class="section-note">Compare production, consumption, hydropower reliance, the domestic production gap, and the net balance after electricity trade.</p>',
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.35, 1])
    left.plotly_chart(line_chart(filtered), width="stretch")
    right.plotly_chart(balance_chart(filtered), width="stretch")
    mix_left, mix_right = st.columns(2)
    mix_left.plotly_chart(generation_mix_chart(filtered), width="stretch")
    mix_right.plotly_chart(energy_mix_share_chart(filtered), width="stretch")

    with st.expander("View national data table"):
        st.dataframe(
            filtered[
                [
                    "year",
                    "production_twh",
                    "consumption_twh",
                    "hydro_twh",
                    "thermal_twh",
                    "imports_twh",
                    "exports_twh",
                    "net_imports_twh",
                    "domestic_gap_twh",
                    "net_balance_twh",
                    "hydro_share_pct",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

with tabs[2]:
    st.subheader("Regional electricity picture")
    st.markdown(
        '<p class="section-note">Regional ranking highlights where demand, deficits, and distribution losses create planning pressure.</p>',
        unsafe_allow_html=True,
    )
    map_df = regional_df.copy()
    map_df["marker_size"] = (map_df["consumption_gwh"] / map_df["consumption_gwh"].max() * 28 + 8).round(1)
    st.map(map_df, latitude="lat", longitude="lon", size="marker_size", color="#2563eb")

    left, right = st.columns([1.15, 1])
    left.plotly_chart(regional_bar_chart(regional_df), width="stretch")
    right.plotly_chart(regional_risk_chart(regional_risk), width="stretch")
    st.dataframe(
        regional_risk[
            [
                "region",
                "risk",
                "risk_score",
                "status",
                "production_gwh",
                "consumption_gwh",
                "balance_gwh",
                "distribution_losses_pct",
            ]
        ],
        width="stretch",
        hide_index=True,
    )

with tabs[3]:
    st.subheader("Seasonal demand forecast")
    st.markdown(
        '<p class="section-note">Forecasts use historical seasonality and scenario adjustments. Peaks are highlighted because supply interruptions usually occur during high-load periods.</p>',
        unsafe_allow_html=True,
    )
    peak_cols = st.columns(3)
    peak_cols[0].metric("Winter peak demand", f"{peaks['winter_peak_twh']:.2f} TWh")
    peak_cols[1].metric("Summer peak demand", f"{peaks['summer_peak_twh']:.2f} TWh")
    peak_cols[2].metric("Forecast demand", f"{future['forecast_twh'].sum():.1f} TWh")
    st.plotly_chart(forecast_chart(forecast_df), width="stretch")

    forecast_total = future["forecast_twh"].sum()
    st.info(
        f"{scenario}: projected demand over the next {months} months is {forecast_total:.1f} TWh. "
        f"Hydropower availability index: {future['hydro_availability_index'].iloc[0]:.2f}."
    )
    with st.expander("View forecast table"):
        st.dataframe(future, width="stretch", hide_index=True)

with tabs[4]:
    st.subheader("Data sources and implementation notes")
    source_html = "".join(
        f'<span class="source-pill">{status.name}: {"live" if status.status == "live" else "fallback"}</span>'
        for status in source_statuses
    )
    st.markdown(source_html, unsafe_allow_html=True)
    st.write(
        "The app first attempts to load live national data from Our World in Data and World Bank. "
        "If a public endpoint is unavailable, it uses packaged starter data so the dashboard remains usable."
    )
    st.write(
        "To connect official Ministry systems, keep the documented column names and replace the loader functions in "
        "`energy_dashboard/data_sources.py` with a database query, secure API request, or scheduled CSV export."
    )
    st.download_button(
        "Download current national dataset",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="kyrgyzstan_energy_national.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download regional starter dataset",
        regional_df.to_csv(index=False).encode("utf-8"),
        file_name="kyrgyzstan_energy_regions_starter.csv",
        mime="text/csv",
    )
