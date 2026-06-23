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

st.sidebar.title("Dashboard Navigation")
st.sidebar.subheader("Dashboard Sections")
dashboard_section = st.sidebar.radio(
    "Choose a section",
    [
        "Executive Overview",
        "Energy Security Assessment",
        "Policy Rules",
        "National Monitoring",
        "Regional Planning",
        "Scenario Planning",
        "Methodology",
        "Data & Handoff",
    ],
    label_visibility="collapsed",
)
st.sidebar.divider()
st.sidebar.caption("Data status")
for status in source_statuses:
    label = "Live" if status.status == "live" else "Fallback"
    st.sidebar.write(f"{status.name}: {label}")
    if status.last_updated:
        st.sidebar.caption(f"Loaded at {status.last_updated}")

latest = national_df.sort_values("year").iloc[-1]
baseline_scenario = "Normal year"
baseline_months = 18
baseline_forecast = forecast_demand(national_df, months=baseline_months, scenario=baseline_scenario)
baseline_peaks = peak_demand_summary(baseline_forecast)
security = calculate_security_index(national_df, baseline_forecast)
security_breakdown = security_index_breakdown(national_df, baseline_forecast)
time_df, changes = time_intelligence(national_df)
changes_summary = year_over_year_summary(changes)
rules = evaluate_policy_rules(national_df, security)
briefing = situation_briefing(security, rules, changes)
actions = recommended_actions(national_df, rules, baseline_peaks, security)
summary_text = executive_summary(national_df, baseline_forecast, baseline_scenario, security)
baseline_scenario_outputs = {
    name: forecast_demand(national_df, months=baseline_months, scenario=name)
    for name in SCENARIOS
}
scenario_impacts, scenario_impact_summary = scenario_impact_analysis(national_df, baseline_scenario_outputs)
baseline_scenario_forecasts = pd.concat(
    [forecast.query("period == 'Forecast'") for forecast in baseline_scenario_outputs.values()],
    ignore_index=True,
)

st.title("Kyrgyzstan Energy Intelligence Dashboard")
st.markdown(
    "For policymakers and energy planners: monitor Kyrgyzstan's electricity security, seasonal demand risk, imports, official ПЭС useful supply, and forecast uncertainty."
)

if dashboard_section == "Executive Overview":
    st.subheader("Current electricity situation")
    st.markdown(
        '<p class="section-note">Latest available factual national electricity indicators. '
        "This page does not include forecast-driven scores or recommendations.</p>",
        unsafe_allow_html=True,
    )
    metric_cols = st.columns(5)
    metric_cols[0].metric("Production", f"{latest['production_twh']:.1f} TWh")
    metric_cols[1].metric("Consumption", f"{latest['consumption_twh']:.1f} TWh")
    metric_cols[2].metric("Domestic deficit", f"{latest['domestic_gap_twh']:.1f} TWh")
    metric_cols[3].metric("Net imports", f"{latest['net_imports_twh']:.1f} TWh")
    metric_cols[4].metric("Balance after trade", f"{latest['net_balance_twh']:.2f} TWh")

    st.subheader("How to read these indicators")
    overview_explanations = pd.DataFrame(
        [
            [
                "Production",
                "Electricity generated domestically during the latest year.",
                "Shows the scale of domestic supply available to meet demand.",
            ],
            [
                "Consumption",
                "Total national electricity demand or final consumption.",
                "Shows how much electricity the system needs to serve.",
            ],
            [
                "Domestic deficit",
                "Production minus consumption before imports and exports.",
                "A negative value shows how much demand is not covered by domestic generation alone.",
            ],
            [
                "Net imports",
                "Electricity imports minus electricity exports.",
                "Shows how much the national balance relies on electricity trade.",
            ],
            [
                "Balance after trade",
                "Production plus imports minus consumption and exports.",
                "Shows whether recorded supply and trade balance recorded demand.",
            ],
        ],
        columns=["Indicator", "What it means", "Why it matters"],
    )
    st.dataframe(overview_explanations, width="stretch", hide_index=True)
    st.caption(
        f"Latest available national year: {int(latest['year'])}. "
        "Values reflect the currently loaded public or fallback national dataset."
    )

elif dashboard_section == "Energy Security Assessment":
    st.subheader("Energy Security Assessment")
    st.markdown(
        '<p class="section-note">The Security Index combines current electricity conditions with future demand '
        "assumptions. Change the forecast scenario or horizon below to see how the assessment responds, using "
        "the unchanged forecasting and Security Index methods.</p>",
        unsafe_allow_html=True,
    )
    control_left, control_right = st.columns(2)
    assessment_scenario = control_left.selectbox(
        "Forecast Scenario",
        list(SCENARIOS.keys()),
        index=list(SCENARIOS.keys()).index(baseline_scenario),
    )
    assessment_months = control_right.slider(
        "Forecast Horizon (months)",
        6,
        36,
        baseline_months,
        step=6,
    )
    assessment_forecast = forecast_demand(
        national_df,
        months=assessment_months,
        scenario=assessment_scenario,
    )
    assessment_peaks = peak_demand_summary(assessment_forecast)
    security = calculate_security_index(national_df, assessment_forecast)
    security_breakdown = security_index_breakdown(national_df, assessment_forecast)
    rules = evaluate_policy_rules(national_df, security)
    briefing = situation_briefing(security, rules, changes)
    actions = recommended_actions(
        national_df,
        rules,
        assessment_peaks,
        security,
    )
    summary_text = executive_summary(
        national_df,
        assessment_forecast,
        assessment_scenario,
        security,
    )
    assessment_scenario_outputs = {
        name: forecast_demand(national_df, months=assessment_months, scenario=name)
        for name in SCENARIOS
    }
    scenario_impacts, scenario_impact_summary = scenario_impact_analysis(
        national_df,
        assessment_scenario_outputs,
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

    st.info(
        f"Current assessment uses the {assessment_scenario.lower()} assumption over a "
        f"{assessment_months}-month forecast horizon. The Security Index reserve-margin component "
        "uses up to the first 12 forecast months."
    )

    st.subheader("Current Security Assessment")
    assessment_cols = st.columns([0.9, 1.4])
    assessment_cols[0].plotly_chart(
        security_gauge(security["score"], security["label"]),
        width="stretch",
    )
    assessment_cols[1].metric(
        "Security Index",
        f"{security['score']:.1f}/100",
        security["label"],
    )
    assessment_cols[1].caption(
        "Risk level is derived from the unchanged Security Index bands: Secure, Moderate Risk, or High Risk."
    )

    st.markdown(
        f"""
        <div class="briefing-panel">
            <div class="briefing-grid">
                <div class="briefing-item">
                    <div class="briefing-label">Risk level</div>
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

    st.subheader("How the Security Index is calculated")
    st.caption(
        "The final score is the sum of four weighted contributions. Higher component scores indicate stronger energy security."
    )
    breakdown_cols = st.columns(4)
    for column, (_, component) in zip(breakdown_cols, security_breakdown.iterrows()):
        column.metric(component["Component"], component["Contribution"])
        column.caption(f"Weight: {component['Weight']} · {component['Current indicator']}")
        column.write(component["Why it changed the score"])
    st.caption(
        f"Total: {security['score']:.1f}/100 = "
        + " + ".join(security_breakdown["Contribution"].str.split(" / ").str[0])
    )

    st.subheader("Scenario Sensitivity Analysis")
    st.caption(
        f"Comparison holds the forecast horizon at {assessment_months} months and changes only the existing "
        "Dry, Normal, and Wet year assumptions. This shows how future assumptions influence the Security Index."
    )
    sensitivity_cols = st.columns(3)
    for column, (_, scenario_row) in zip(sensitivity_cols, scenario_impacts.iterrows()):
        column.metric(
            scenario_row["Scenario"],
            scenario_row["Security Index"],
        )
        column.write(f"**Risk level:** {scenario_row['Risk level']}")
        column.caption(
            f"Forecast demand: {scenario_row['Forecast demand']} · "
            f"Estimated balance: {scenario_row['Net balance estimate']}"
        )

    st.subheader("Recommended actions and evidence")
    st.dataframe(actions, width="stretch", hide_index=True)

    st.subheader("What Changed Since Last Year?")
    change_cols = st.columns(5)
    change_cols[0].metric("Demand YoY", f"{changes['demand_yoy_pct']:.1f}%")
    change_cols[1].metric("Production YoY", f"{changes['production_yoy_pct']:.1f}%")
    change_cols[2].metric("Net imports YoY", f"{changes['imports_yoy_pct']:.1f}%")
    change_cols[3].metric("Hydro share change", f"{changes['hydro_share_change_pct']:.1f} pp")
    change_cols[4].metric("Domestic gap change", f"{changes['domestic_gap_change_twh']:+.1f} TWh")
    st.info(changes_summary)

    st.download_button(
        "Download Executive Energy Briefing",
        briefing_pdf,
        file_name="kyrgyzstan_energy_situation_briefing.pdf",
        mime="application/pdf",
    )

elif dashboard_section == "Policy Rules":
    st.subheader("Policy rules and audit trail")
    st.markdown(
        '<p class="section-note">These thresholds make the index explainable and keep risk interpretation stable over time.</p>',
        unsafe_allow_html=True,
    )
    st.dataframe(rules, width="stretch", hide_index=True)
    st.plotly_chart(time_intelligence_chart(time_df), width="stretch")

elif dashboard_section == "National Monitoring":
    st.subheader("National electricity trends")
    st.markdown(
        '<p class="section-note">Compare production, consumption, hydropower reliance, the domestic production gap, and the net balance after electricity trade.</p>',
        unsafe_allow_html=True,
    )
    year_min = int(national_df["year"].min())
    year_max = int(national_df["year"].max())
    selected_years = st.slider(
        "Years shown",
        year_min,
        year_max,
        (max(year_min, year_max - 12), year_max),
    )
    filtered = national_df[national_df["year"].between(selected_years[0], selected_years[1])].copy()
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

elif dashboard_section == "Regional Planning":
    st.subheader("ПЭС service-territory electricity planning layer")
    st.markdown(
        '<p class="section-note">Official 2024 useful electricity supply through the eight ПЭС service territories, with transparent source provenance and derived planning context.</p>',
        unsafe_allow_html=True,
    )
    st.warning(
        "ПЭС service territories are electricity-network operating areas, not guaranteed one-to-one administrative "
        "oblast boundaries. The official source reports Osh as one Ошское ПЭС territory and does not publish a "
        "separate Osh City value."
    )
    with st.expander("Data sources, quality, and confidence notes", expanded=True):
        st.markdown(
            f"""
            - **Official useful supply:** The Kyrgyz Electricity Settlement Center's *Brief electricity balance
              for the Kyrgyz power system for 2024*, section 6.3, reports annual useful electricity supply by ПЭС.
              Values are converted from thousand kWh to GWh without estimation.
            - **Official population:** Population estimates are from the
              [National Statistical Committee of the Kyrgyz Republic]({REGIONAL_POPULATION_SOURCE_URL}),
              reported for January 1, 2025 and used as the end-2024 population position.
            - **Derived:** Per-capita supply divides official ПЭС useful supply by the mapped official population.
              The Osh denominator combines Osh oblast and Osh City population because the electricity source reports
              one Ошское ПЭС value. Demand share divides ПЭС useful supply by the loaded national annual demand.
            - **Not available:** Official ПЭС production, distribution losses, regional balance, and regional risk
              are not present in this dataset. They are not estimated or calculated from partial data.
            """
        )
        quality_rows = pd.DataFrame(
            [
                ["Population", "Official", "Public regional population estimate at January 1, 2025."],
                ["Useful electricity supply", "Official", "Settlement Center 2024 annual balance, section 6.3."],
                ["Production", "Not available", "No official ПЭС production field is used."],
                ["Distribution losses", "Not available", "No official ПЭС loss field is used."],
                ["Per-capita useful supply", "Derived", "Official useful supply divided by mapped official population."],
                ["Share of national demand", "Derived", "Official useful supply divided by loaded national annual demand."],
                ["Balance and status", "Not available", "Disabled because official production is unavailable."],
                ["Risk score and ranking", "Not available", "Disabled because production and losses are unavailable."],
            ],
            columns=["Regional metric", "Data Quality", "Source or method"],
        )
        st.dataframe(quality_rows, width="stretch", hide_index=True)
        st.caption(
            "Territorial caveat: values describe ПЭС network service territories. Per-capita supply is suitable only "
            "for broad planning context because mapped administrative populations may not exactly match network "
            "boundaries. Production, losses, surplus/deficit, and risk ranking remain unavailable."
        )
    map_df = regional_df.copy()
    map_df["marker_size"] = (map_df["useful_supply_gwh"] / map_df["useful_supply_gwh"].max() * 28 + 8).round(1)
    map_df["color"] = "#2563eb"
    st.map(map_df, latitude="lat", longitude="lon", size="marker_size", color="color")

    st.plotly_chart(regional_bar_chart(regional_df), width="stretch")
    regional_table = regional_df[
            [
                "region",
                "source_region_label",
                "territory_type",
                "year",
                "useful_supply_gwh",
                "population",
                "demand_per_capita_kwh",
                "demand_share_pct",
                "production_data_quality",
                "distribution_losses_data_quality",
                "balance_data_quality",
                "useful_supply_data_quality",
                "demand_per_capita_data_quality",
                "demand_share_data_quality",
                "source_document",
                "data_provenance",
                "source_url",
            ]
        ].rename(
            columns={
                "region": "ПЭС territory",
                "source_region_label": "Official source label",
                "territory_type": "Territory type",
                "year": "Source year",
                "useful_supply_gwh": "Useful supply (GWh)",
                "population": "Population",
                "demand_per_capita_kwh": "Derived supply per capita (kWh)",
                "demand_share_pct": "Derived share of national demand (%)",
                "production_data_quality": "Production",
                "distribution_losses_data_quality": "Losses",
                "balance_data_quality": "Balance",
                "useful_supply_data_quality": "Supply quality",
                "demand_per_capita_data_quality": "Per-capita quality",
                "demand_share_data_quality": "Demand-share quality",
                "source_document": "Source document",
                "data_provenance": "Data provenance",
                "source_url": "Source URL",
            }
        )
    st.dataframe(
        regional_table,
        width="stretch",
        hide_index=True,
    )
    st.caption(
        f"Official 2024 useful supply through the eight ПЭС networks totals "
        f"{regional_df['useful_supply_gwh'].sum():,.1f} GWh and represents "
        f"{regional_df['demand_share_pct'].sum():.1f}% of the loaded national demand series. "
        "The two measures have different accounting scopes, so the percentage is a derived comparison rather than reconciliation."
    )

elif dashboard_section == "Scenario Planning":
    st.subheader("Forecast uncertainty and peak demand")
    st.markdown(
        '<p class="section-note">Forecast charts use the standard Normal-year, 18-month planning baseline. '
        "Interactive Forecast Scenario and Forecast Horizon controls are available on the Energy Security Assessment page. "
        "Monthly patterns are estimated from annual data and should be recalibrated with official monthly demand, reservoir, weather, and plant availability data.</p>",
        unsafe_allow_html=True,
    )
    scenario = baseline_scenario
    months = baseline_months
    forecast_df = baseline_forecast
    future = forecast_df[forecast_df["period"].eq("Forecast")]
    peaks = baseline_peaks
    scenario_forecasts = baseline_scenario_forecasts
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

elif dashboard_section == "Methodology":
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
        - **Kyrgyz Electricity Settlement Center:** official 2024 useful electricity supply by ПЭС service territory.
        """
    )
    st.info(
        "The sidebar reports whether national sources are live or fallback. “Loaded at” is the request time, "
        "not the source provider’s publication or revision date."
    )

    st.markdown("### Regional data limitations")
    st.markdown(
        """
        - ПЭС useful electricity supply for 2024 is classified as **Official**.
        - ПЭС territories are network service areas and may not exactly match administrative oblast boundaries.
        - Production, distribution losses, regional balance, and regional risk ranking are **Not available**.
        - Per-capita supply and share of national demand are **Derived** and clearly labeled.
        - No missing regional production or loss values are estimated.
        """
    )

    st.markdown("### Key assumptions")
    st.markdown(
        """
        - The latest available year represents the current national planning position.
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
        "Interpret national scores, forecasts, and recommended actions as decision-support signals—not final decisions."
    )

elif dashboard_section == "Data & Handoff":
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
        national_df.to_csv(index=False).encode("utf-8"),
        file_name="kyrgyzstan_energy_national.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download official 2024 ПЭС useful supply dataset",
        regional_df.to_csv(index=False).encode("utf-8"),
        file_name="kyrgyzstan_pes_useful_supply_2024.csv",
        mime="text/csv",
    )

st.divider()
st.caption(
    "Data sources: Our World in Data, World Bank, National Statistical Committee, Kyrgyz Electricity Settlement Center. "
    "Built with Streamlit, Plotly, Pandas, and Statsmodels. "
    "GitHub: https://github.com/Suiunibraev/kg-energy-dashboard"
)
