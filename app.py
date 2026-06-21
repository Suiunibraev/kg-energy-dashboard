from __future__ import annotations

import pandas as pd
import streamlit as st

from energy_dashboard.data_sources import load_energy_dataset, load_regional_dataset
from energy_dashboard.forecasting import SCENARIOS, forecast_demand
from energy_dashboard.ui import (
    apply_theme,
    balance_chart,
    forecast_chart,
    generation_mix_chart,
    line_chart,
    regional_bar_chart,
)


st.set_page_config(
    page_title="Kyrgyzstan Energy Intelligence Dashboard",
    page_icon="KG",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


@st.cache_data(ttl=3600)
def get_data() -> tuple[pd.DataFrame, pd.DataFrame, list]:
    national, statuses = load_energy_dataset()
    regional = load_regional_dataset()
    return national, regional, statuses


national_df, regional_df, source_statuses = get_data()

st.sidebar.title("Dashboard controls")
year_min = int(national_df["year"].min())
year_max = int(national_df["year"].max())
selected_years = st.sidebar.slider("Years shown", year_min, year_max, (max(year_min, year_max - 12), year_max))
st.sidebar.divider()
st.sidebar.caption("Data status")
for status in source_statuses:
    label = "Live" if status.status == "live" else "Fallback"
    st.sidebar.write(f"{status.name}: {label}")

filtered = national_df[national_df["year"].between(selected_years[0], selected_years[1])].copy()
latest = filtered.iloc[-1]

st.title("Kyrgyzstan Energy Intelligence Dashboard")
st.markdown(
    "A Ministry-ready monitoring and forecasting tool for electricity production, consumption, regional demand, and seasonal planning."
)

metric_cols = st.columns(5)
metric_cols[0].metric("Total production", f"{latest['production_twh']:.1f} TWh")
metric_cols[1].metric("Total consumption", f"{latest['consumption_twh']:.1f} TWh")
metric_cols[2].metric("Surplus / deficit before trade", f"{latest['domestic_gap_twh']:.1f} TWh")
metric_cols[3].metric("Balance after imports / exports", f"{latest['net_balance_twh']:.2f} TWh")
metric_cols[4].metric("Hydropower share", f"{latest['hydro_share_pct']:.0f}%")

tabs = st.tabs(["National monitoring", "Regional view", "Seasonal forecast", "Data and handoff"])

with tabs[0]:
    st.subheader("National electricity trends")
    st.markdown(
        '<p class="section-note">Compare production, consumption, hydropower reliance, the domestic production gap, and the net balance after electricity trade.</p>',
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.35, 1])
    left.plotly_chart(line_chart(filtered), width="stretch")
    right.plotly_chart(balance_chart(filtered), width="stretch")
    st.plotly_chart(generation_mix_chart(filtered), width="stretch")

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
                    "domestic_gap_twh",
                    "net_balance_twh",
                    "hydro_share_pct",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

with tabs[1]:
    st.subheader("Regional electricity picture")
    st.markdown(
        '<p class="section-note">Starter regional data shows the intended Ministry workflow. Replace this file with official regional feeds for operational use.</p>',
        unsafe_allow_html=True,
    )
    map_df = regional_df.copy()
    map_df["marker_size"] = (map_df["consumption_gwh"] / map_df["consumption_gwh"].max() * 28 + 8).round(1)
    st.map(map_df, latitude="lat", longitude="lon", size="marker_size", color="#2563eb")

    left, right = st.columns([1.25, 1])
    left.plotly_chart(regional_bar_chart(regional_df), width="stretch")
    right.dataframe(
        regional_df[
            [
                "region",
                "status",
                "production_gwh",
                "consumption_gwh",
                "balance_gwh",
                "distribution_losses_pct",
            ]
        ].sort_values("consumption_gwh", ascending=False),
        width="stretch",
        hide_index=True,
    )

with tabs[2]:
    st.subheader("Seasonal demand forecast")
    st.markdown(
        '<p class="section-note">Forecasts use historical seasonality and scenario adjustments. They are planning estimates and should be recalibrated with Ministry reservoir, weather, and operational data.</p>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([1, 1])
    scenario = c1.selectbox("Hydropower scenario", list(SCENARIOS.keys()), index=0)
    months = c2.slider("Forecast horizon", 6, 36, 18, step=6)
    forecast_df = forecast_demand(national_df, months=months, scenario=scenario)
    st.plotly_chart(forecast_chart(forecast_df), width="stretch")

    future = forecast_df[forecast_df["period"].eq("Forecast")]
    forecast_total = future["forecast_twh"].sum()
    st.info(
        f"{scenario}: projected demand over the next {months} months is {forecast_total:.1f} TWh. "
        f"Hydropower availability index: {future['hydro_availability_index'].iloc[0]:.2f}."
    )
    with st.expander("View forecast table"):
        st.dataframe(future, width="stretch", hide_index=True)

with tabs[3]:
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
