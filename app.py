from __future__ import annotations

import pandas as pd
import streamlit as st

from energy_dashboard.data_sources import (
    REGIONAL_POPULATION_SOURCE_URL,
    add_regional_planning_metrics,
    load_energy_dataset,
    load_regional_dataset,
)
from energy_dashboard.forecasting import SCENARIOS, forecast_demand
from energy_dashboard.policy import (
    calculate_security_index,
    executive_summary,
    evaluate_policy_rules,
    peak_demand_summary,
    recommended_actions,
    regional_risk_ranking,
    scenario_impact_analysis,
    security_index_breakdown,
    situation_briefing,
    time_intelligence,
    year_over_year_summary,
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
    regional = add_regional_planning_metrics(load_regional_dataset(), national)
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
security_breakdown = security_index_breakdown(filtered, forecast_df)
peaks = peak_demand_summary(forecast_df)
regional_risk = regional_risk_ranking(regional_df)
time_df, changes = time_intelligence(filtered)
changes_summary = year_over_year_summary(changes)
rules = evaluate_policy_rules(filtered, security)
briefing = situation_briefing(security, rules, changes)
actions = recommended_actions(filtered, regional_risk, rules, peaks, security)
summary_text = executive_summary(filtered, forecast_df, scenario, security)
scenario_forecast_outputs = {
    name: forecast_demand(national_df, months=months, scenario=name)
    for name in SCENARIOS
}
scenario_forecasts = pd.concat(
    [forecast.query("period == 'Forecast'") for forecast in scenario_forecast_outputs.values()],
    ignore_index=True,
)
scenario_impacts, scenario_impact_summary = scenario_impact_analysis(filtered, scenario_forecast_outputs)

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

briefing_pdf = build_ministry_briefing_pdf(
    latest,
    security,
    briefing,
    summary_text,
    actions,
    rules,
    scenario_impacts,
    scenario_impact_summary,
    security_breakdown,
    changes,
    changes_summary,
)
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
        "Methodology",
        "Data and handoff",
    ]
)

with tabs[0]:
    st.subheader("Energy security overview")
    left, right = st.columns([0.9, 1.4])
    left.plotly_chart(security_gauge(security["score"], security["label"]), width="stretch")
    right.subheader("Recommended actions")
    right.dataframe(actions, width="stretch", hide_index=True)
    st.subheader("How the Security Index is calculated")
    st.caption(
        "The final score is the sum of four weighted contributions. Higher component scores indicate stronger energy security."
    )
    breakdown_cols = st.columns(4)
    for column, (_, component) in zip(breakdown_cols, security_breakdown.iterrows()):
        column.metric(
            component["Component"],
            component["Contribution"],
        )
        column.caption(f"Weight: {component['Weight']} · {component['Current indicator']}")
        column.write(component["Why it changed the score"])
    st.caption(
        f"Total: {security['score']:.1f}/100 = "
        + " + ".join(security_breakdown["Contribution"].str.split(" / ").str[0])
    )
    st.subheader("What Changed Since Last Year?")
    change_cols = st.columns(5)
    change_cols[0].metric("Demand YoY", f"{changes['demand_yoy_pct']:.1f}%")
    change_cols[1].metric("Production YoY", f"{changes['production_yoy_pct']:.1f}%")
    change_cols[2].metric("Net imports YoY", f"{changes['imports_yoy_pct']:.1f}%")
    change_cols[3].metric("Hydro share change", f"{changes['hydro_share_change_pct']:.1f} pp")
    change_cols[4].metric("Domestic gap change", f"{changes['domestic_gap_change_twh']:+.1f} TWh")
    st.info(changes_summary)

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
    st.subheader("Regional electricity planning layer")
    st.markdown(
        '<p class="section-note">Regional ranking highlights where demand, deficits, distribution losses, population, and demand concentration create planning pressure.</p>',
        unsafe_allow_html=True,
    )
    st.warning(
        "This is a mixed-quality planning layer. Population is official public data; electricity production, "
        "consumption, and losses remain demonstration-only starter values. Derived indicators are not official statistics."
    )
    with st.expander("Data sources, quality, and confidence notes", expanded=True):
        st.markdown(
            f"""
            - **Official:** Regional population estimates are from the
              [National Statistical Committee of the Kyrgyz Republic]({REGIONAL_POPULATION_SOURCE_URL}),
              reported for January 1, 2025 and used as the end-2024 population position.
            - **Estimated:** Demand per capita combines official population with demonstration electricity demand.
              Regional demand share divides demonstration regional demand by the currently loaded national demand value
              for the same year; the national source status is shown in the sidebar.
            - **Demonstration:** Regional production, consumption, distribution losses, balance, status, and risk ranking
              come from or depend on the packaged starter electricity dataset. They are workflow examples, not operational evidence.
            """
        )
        quality_rows = pd.DataFrame(
            [
                ["Population", "Official", "Public regional population estimate at January 1, 2025."],
                ["Production", "Demonstration", "Packaged starter electricity value."],
                ["Consumption", "Demonstration", "Packaged starter electricity value."],
                ["Distribution losses", "Demonstration", "Packaged starter electricity value."],
                ["Demand per capita", "Estimated", "Demonstration demand divided by official population."],
                ["Regional demand share", "Estimated", "Demonstration regional demand divided by national annual demand."],
                ["Balance and status", "Demonstration", "Derived from demonstration production and consumption."],
                ["Risk score and level", "Demonstration", "Derived from demonstration electricity and loss values."],
            ],
            columns=["Regional metric", "Data Quality", "Source or method"],
        )
        st.dataframe(quality_rows, width="stretch", hide_index=True)
        st.caption(
            "Confidence note: use population for broad planning context only. Do not use the regional electricity, "
            "per-capita, demand-share, balance, or risk values for budgeting, dispatch, procurement, or investment "
            "approval until they are replaced and validated against official Ministry regional feeds. The starter "
            "regional demand values are not reconciled to the national total."
        )
    map_df = regional_df.copy()
    map_df["marker_size"] = (map_df["consumption_gwh"] / map_df["consumption_gwh"].max() * 28 + 8).round(1)
    map_df["color"] = "#2563eb"
    st.map(map_df, latitude="lat", longitude="lon", size="marker_size", color="color")

    left, right = st.columns([1.15, 1])
    left.plotly_chart(regional_bar_chart(regional_df), width="stretch")
    right.plotly_chart(regional_risk_chart(regional_risk), width="stretch")
    regional_table = regional_risk[
            [
                "region",
                "risk",
                "risk_score",
                "status",
                "production_gwh",
                "consumption_gwh",
                "population",
                "demand_per_capita_kwh",
                "demand_share_pct",
                "balance_gwh",
                "distribution_losses_pct",
                "population_data_quality",
                "consumption_data_quality",
                "demand_per_capita_data_quality",
                "demand_share_data_quality",
                "risk_data_quality",
            ]
        ].rename(
            columns={
                "region": "Region",
                "risk": "Risk",
                "risk_score": "Risk score",
                "status": "Status",
                "production_gwh": "Production (GWh)",
                "consumption_gwh": "Demand (GWh)",
                "population": "Population",
                "demand_per_capita_kwh": "Demand per capita (kWh)",
                "demand_share_pct": "National demand share (%)",
                "balance_gwh": "Balance (GWh)",
                "distribution_losses_pct": "Distribution losses (%)",
                "population_data_quality": "Population quality",
                "consumption_data_quality": "Demand quality",
                "demand_per_capita_data_quality": "Per-capita quality",
                "demand_share_data_quality": "Demand-share quality",
                "risk_data_quality": "Risk quality",
            }
        )
    st.dataframe(
        regional_table,
        width="stretch",
        hide_index=True,
    )
    st.caption(
        f"Demonstration regional demand currently accounts for "
        f"{regional_risk['demand_share_pct'].sum():.1f}% of the loaded national demand. "
        "The difference confirms that the starter regional values are not a reconciled official allocation."
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

    st.subheader("Scenario Impact Analysis")
    st.caption(
        "Side-by-side comparison uses up to the first 12 forecast months, matching the unchanged "
        "Security Index calculation. The balance estimate prorates current generation and trade to "
        "the comparison period and adjusts hydropower using each scenario's existing availability index."
    )
    st.dataframe(scenario_impacts, width="stretch", hide_index=True)
    st.info(scenario_impact_summary)

    forecast_total = future["forecast_twh"].sum()
    st.info(
        f"{scenario}: projected demand over the next {months} months is {forecast_total:.1f} TWh. "
        f"Hydropower availability index: {future['hydro_availability_index'].iloc[0]:.2f}."
    )
    with st.expander("View forecast table"):
        st.dataframe(future, width="stretch", hide_index=True)

with tabs[5]:
    st.subheader("Dashboard methodology and interpretation")
    st.markdown(
        '<p class="section-note">This page explains how the dashboard turns available data into indicators, '
        "forecasts, risk labels, and planning prompts. The methods are transparent prototypes and should be "
        "validated with Ministry experts before operational adoption.</p>",
        unsafe_allow_html=True,
    )

    st.markdown("### Energy Security Index")
    st.write(
        "The Energy Security Index is a 0–100 composite score. It adds four weighted components; "
        "a higher score indicates stronger security under the current data and forecast assumptions."
    )
    methodology_index = security_breakdown[
        ["Component", "Weight", "Current indicator", "Why it changed the score"]
    ].rename(columns={"Why it changed the score": "Scoring interpretation"})
    st.dataframe(methodology_index, width="stretch", hide_index=True)
    st.code(
        "Security Index = Production coverage score (35) + Hydropower dependency score (20)\n"
        "               + Demand growth score (20) + Forecast reserve margin score (25)",
        language=None,
    )
    st.markdown(
        """
        - **Production coverage:** compares current domestic production with current consumption. Full points require production equal to 105% of consumption.
        - **Hydropower dependency:** full points apply up to a 55% hydro share; the score falls as dependence rises above that level.
        - **Demand growth:** uses average recent annual consumption growth. Faster growth lowers the contribution.
        - **Forecast reserve margin:** compares current annual production with demand forecast over up to the next 12 months.
        - **Risk labels:** Secure is 75 or higher; Moderate Risk is 50–74.9; High Risk is below 50.
        """
    )
    st.caption(
        "The weights and thresholds are prototype policy assumptions. They are not an officially adopted Ministry methodology."
    )

    st.markdown("### Forecasting approach and scenarios")
    st.write(
        "Public national electricity data is annual. The dashboard therefore estimates monthly history using "
        "winter demand weights and separate hydropower seasonality weights. It then applies Holt-Winters "
        "exponential smoothing with an additive trend, multiplicative seasonality, and a 12-month seasonal cycle."
    )
    scenario_methodology = pd.DataFrame(
        [
            [
                name,
                f"{parameters['demand_multiplier']:.2f}",
                f"{parameters['hydro_multiplier']:.2f}",
            ]
            for name, parameters in SCENARIOS.items()
        ],
        columns=["Scenario", "Demand multiplier", "Hydropower availability index"],
    )
    st.dataframe(scenario_methodology, width="stretch", hide_index=True)
    st.markdown(
        """
        - If the statistical model cannot be fitted, the dashboard uses a seasonal average with a simple trend.
        - Confidence bands use forecast residual variation and are planning ranges, not guaranteed limits.
        - Scenario Impact Analysis uses the same forecast outputs and unchanged Security Index calculation.
        - Monthly forecasts should be recalibrated when observed monthly demand, reservoir, weather, outage, and plant-availability data become available.
        """
    )

    st.markdown("### Data sources and fallback behavior")
    st.markdown(
        """
        - **Our World in Data:** available annual national electricity generation, demand, hydropower, thermal generation, trade, and population fields.
        - **World Bank:** electricity access and population indicators where available.
        - **National Statistical Committee:** official regional population estimates used in the regional planning layer.
        - **Packaged fallback:** if national public endpoints fail, starter national data keeps the application usable.
        - **Regional starter file:** packaged electricity production, consumption, and loss values support demonstration and workflow design only.
        """
    )
    st.info(
        "The sidebar reports whether national sources are live or fallback. “Loaded at” is the request time, "
        "not the source provider’s publication or revision date."
    )

    st.markdown("### Regional data limitations")
    st.markdown(
        """
        - Regional population is classified as **Official**.
        - Regional electricity production, consumption, losses, balance, and risk ranking are **Demonstration**.
        - Demand per capita and regional demand share are **Estimated** because they use demonstration demand.
        - Starter regional demand is not reconciled to the national electricity total.
        - Regional risk rankings should not determine funding or infrastructure priorities until official Ministry data replaces the starter values.
        """
    )

    st.markdown("### Key assumptions")
    st.markdown(
        """
        - The latest selected year represents the current national planning position.
        - Current annual production is used when estimating the forecast reserve margin.
        - Hydropower availability is represented by scenario multipliers rather than observed reservoir or inflow data.
        - Policy rules and recommended actions are simplified, auditable planning prompts.
        - Public annual data is sufficient for strategic demonstration, but not for real-time system operation.
        """
    )

    use_col, limit_col = st.columns(2)
    with use_col:
        st.markdown("### Appropriate uses")
        st.markdown(
            """
            - Strategic monitoring and policy discussion
            - Comparing transparent planning scenarios
            - Identifying questions for further analysis
            - Preparing executive briefings and meetings
            - Designing Ministry data-integration requirements
            """
        )
    with limit_col:
        st.markdown("### Do not use for")
        st.markdown(
            """
            - Real-time dispatch or grid operation
            - Binding procurement or import commitments
            - Budget or investment approval
            - Official regional performance assessment
            - Decisions requiring validated operational forecasts
            """
        )
    st.warning(
        "Interpret scores, forecasts, regional rankings, and recommended actions as decision-support signals—not final decisions."
    )

with tabs[6]:
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
