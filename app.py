from __future__ import annotations

import pandas as pd
import streamlit as st

from energy_dashboard.data_sources import load_energy_dataset, load_regional_dataset
from energy_dashboard.forecasting import SCENARIOS, forecast_demand
from energy_dashboard.policy import (
    calculate_security_index,
    executive_summary,
    evaluate_policy_rules,
    peak_demand_summary,
    recommended_actions,
    regional_risk_ranking,
    situation_briefing,
    time_intelligence,
)
from energy_dashboard.reporting import build_ministry_briefing_pdf
from energy_dashboard.ui import (
    apply_theme,
    balance_chart,
    energy_mix_share_chart,
    forecast_chart,
    generation_mix_chart,
    line_chart,
    regional_bar_chart,
    regional_risk_chart,
    scenario_spread_chart,
    security_gauge,
    time_intelligence_chart,
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


def stop_with_data_error(exc: Exception) -> None:
    st.error(
        "The dashboard could not load the required energy data. "
        "Please check the data files, required columns, and source connection settings."
    )
    with st.expander("Technical details"):
        st.exception(exc)
    st.stop()


@st.cache_data(ttl=3600)
def get_data() -> tuple[pd.DataFrame, pd.DataFrame, list]:
    national, statuses = load_energy_dataset()
    national = ensure_national_metrics(national)
    regional = load_regional_dataset()
    return national, regional, statuses


try:
    national_df, regional_df, source_statuses = get_data()
except Exception as exc:  # noqa: BLE001 - user-facing dashboard should fail clearly.
    stop_with_data_error(exc)

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
    if status.last_updated:
        st.sidebar.caption(f"Loaded at {status.last_updated}")

filtered = national_df[national_df["year"].between(selected_years[0], selected_years[1])].copy()
latest = filtered.iloc[-1]
forecast_df = forecast_demand(national_df, months=months, scenario=scenario)
future = forecast_df[forecast_df["period"].eq("Forecast")]
security = calculate_security_index(filtered, forecast_df)
peaks = peak_demand_summary(forecast_df)
regional_risk = regional_risk_ranking(regional_df)
time_df, changes = time_intelligence(filtered)
rules = evaluate_policy_rules(filtered, security)
briefing = situation_briefing(security, rules, changes)
actions = recommended_actions(filtered, regional_risk, rules, peaks, security)
summary_text = executive_summary(filtered, forecast_df, scenario, security)
scenario_forecasts = pd.concat(
    [forecast_demand(national_df, months=months, scenario=name).query("period == 'Forecast'") for name in SCENARIOS],
    ignore_index=True,
)

st.title("Kyrgyzstan Energy Intelligence Dashboard")
st.markdown(
    "For policymakers and energy planners: monitor Kyrgyzstan's electricity security, seasonal demand risk, imports, regional deficits, and forecast uncertainty."
)

st.markdown(
    f"""
    <div class="briefing-panel">
        <div class="briefing-grid">
            <div class="briefing-item">
                <div class="briefing-label">Today's energy status</div>
                <div class="briefing-value">{briefing["status"]}</div>
            </div>
            <div class="briefing-item">
                <div class="briefing-label">Main driver</div>
                <div class="briefing-value">{briefing["main_driver"]}</div>
            </div>
            <div class="briefing-item">
                <div class="briefing-label">Key concern</div>
                <div class="briefing-value">{briefing["key_concern"]}</div>
            </div>
            <div class="briefing-item">
                <div class="briefing-label">Outlook</div>
                <div class="briefing-value">{briefing["outlook"]}</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_cols = st.columns(6)
metric_cols[0].metric("Total production", f"{latest['production_twh']:.1f} TWh")
metric_cols[1].metric("Total consumption", f"{latest['consumption_twh']:.1f} TWh")
metric_cols[2].metric("Surplus / deficit before trade", f"{latest['domestic_gap_twh']:.1f} TWh")
metric_cols[3].metric("Balance after imports / exports", f"{latest['net_balance_twh']:.2f} TWh")
metric_cols[4].metric("Net imports", f"{latest['net_imports_twh']:.1f} TWh")
metric_cols[5].metric("Security index", f"{security['score']:.1f}/100", security["label"])
metric_cols[2].caption("Production minus consumption before imports and exports.")
metric_cols[5].caption("Composite 0-100 score based on balance, dependency, growth, and reserve margin.")

st.info(summary_text)
st.markdown(
    f"""
    - Current national risk: **{briefing["status"]}**
    - Main cause of risk: **{briefing["main_driver"]}**
    - Recommended next action: **{actions.iloc[0]["Recommended action"] if not actions.empty else "Continue monitoring system indicators."}**
    """
)

with st.expander("Definitions"):
    st.markdown(
        """
        - **Domestic gap:** domestic electricity production minus consumption before imports and exports.
        - **Net balance:** production plus imports minus consumption and exports.
        - **Net imports:** imports minus exports; higher values indicate stronger import dependence.
        - **Security index:** 0-100 score based on production coverage, hydropower dependency, demand growth, and forecast reserve margin.
        - **Reserve margin:** estimated supply cushion relative to forecast demand.
        - **Hydro vulnerability:** risk flag when the generation mix depends heavily on hydropower.
        - **Scenario spread:** difference between dry, normal, and wet hydropower demand scenarios.
        """
    )

briefing_pdf = build_ministry_briefing_pdf(latest, security, briefing, summary_text, actions, rules)
st.download_button(
    "Download Executive Energy Briefing",
    briefing_pdf,
    file_name="kyrgyzstan_energy_situation_briefing.pdf",
    mime="application/pdf",
)

tabs = st.tabs(
    [
        "Situation briefing",
        "Policy rules",
        "National monitoring",
        "Regional view",
        "Forecast uncertainty",
        "Data and handoff",
    ]
)

with tabs[0]:
    st.subheader("Energy security overview")
    left, right = st.columns([0.9, 1.4])
    left.plotly_chart(security_gauge(security["score"], security["label"]), width="stretch")
    right.subheader("Recommended actions")
    right.dataframe(actions, width="stretch", hide_index=True)
    st.subheader("What changed in the latest year")
    change_cols = st.columns(5)
    change_cols[0].metric("Demand YoY", f"{changes['demand_yoy_pct']:.1f}%")
    change_cols[1].metric("Production YoY", f"{changes['production_yoy_pct']:.1f}%")
    change_cols[2].metric("Net imports YoY", f"{changes['imports_yoy_pct']:.1f}%")
    change_cols[3].metric("Hydro share change", f"{changes['hydro_share_change_pct']:.1f} pp")
    change_cols[4].metric("Demand trend deviation", f"{changes['seasonal_deviation_index']:.1f}%")
    change_cols[4].caption("Latest demand compared with its 3-year rolling trend.")

with tabs[1]:
    st.subheader("Policy rules and audit trail")
    st.markdown(
        '<p class="section-note">These thresholds make the index explainable and keep risk interpretation stable over time.</p>',
        unsafe_allow_html=True,
    )
    st.dataframe(rules, width="stretch", hide_index=True)
    st.plotly_chart(time_intelligence_chart(time_df), width="stretch")

with tabs[2]:
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
    st.plotly_chart(trade_chart(filtered), width="stretch")

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

with tabs[3]:
    st.subheader("Regional electricity picture")
    st.markdown(
        '<p class="section-note">Regional ranking highlights where demand, deficits, and distribution losses create planning pressure.</p>',
        unsafe_allow_html=True,
    )
    st.warning(
        "Regional values use a transparent starter dataset for demonstration and workflow design. "
        "Replace them with official Ministry regional feeds before operational use."
    )
    map_df = regional_df.copy()
    map_df["marker_size"] = (map_df["consumption_gwh"] / map_df["consumption_gwh"].max() * 28 + 8).round(1)
    map_df["color"] = "#2563eb"
    st.map(map_df, latitude="lat", longitude="lon", size="marker_size", color="color")

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

with tabs[4]:
    st.subheader("Forecast uncertainty and peak demand")
    st.markdown(
        '<p class="section-note">Forecasts include confidence bands and scenario spread so planning decisions are not treated as certain. Monthly patterns are estimated from annual data and should be recalibrated with official monthly demand, reservoir, weather, and plant availability data.</p>',
        unsafe_allow_html=True,
    )
    peak_cols = st.columns(3)
    peak_cols[0].metric("Winter peak demand", f"{peaks['winter_peak_twh']:.2f} TWh")
    peak_cols[1].metric("Summer peak demand", f"{peaks['summer_peak_twh']:.2f} TWh")
    peak_cols[2].metric("Forecast demand", f"{future['forecast_twh'].sum():.1f} TWh")
    st.plotly_chart(forecast_chart(forecast_df), width="stretch")
    st.plotly_chart(scenario_spread_chart(scenario_forecasts), width="stretch")

    forecast_total = future["forecast_twh"].sum()
    st.info(
        f"{scenario}: projected demand over the next {months} months is {forecast_total:.1f} TWh. "
        f"Hydropower availability index: {future['hydro_availability_index'].iloc[0]:.2f}."
    )
    with st.expander("View forecast table"):
        st.dataframe(future, width="stretch", hide_index=True)

with tabs[5]:
    st.subheader("Data sources and implementation notes")
    source_html = "".join(
        f'<span class="source-pill">{status.name}: {"live" if status.status == "live" else "fallback"}'
        f'{f" | loaded at {status.last_updated}" if status.last_updated else ""}</span>'
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

st.divider()
st.caption(
    "Data sources: Our World in Data, World Bank, packaged regional starter data. "
    "Built with Streamlit, Plotly, Pandas, and Statsmodels. "
    "GitHub: https://github.com/Suiunibraev/kg-energy-dashboard"
)
