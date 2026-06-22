from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


PALETTE = {
    "ink": "#1f2933",
    "muted": "#5b6673",
    "blue": "#2563eb",
    "teal": "#0f766e",
    "amber": "#b7791f",
    "red": "#b42318",
    "green": "#15803d",
    "violet": "#7c3aed",
    "cyan": "#0891b2",
    "panel": "#f6f8fb",
}


def apply_theme() -> None:
    import streamlit as st

    st.markdown(
        """
        <style>
        .stApp { background: #f7f9fc; color: #1f2933; }
        .block-container { padding-top: 2rem; padding-bottom: 2.5rem; }
        [data-testid="stSidebar"] { background: #eef3f8; border-right: 1px solid #d9e2ec; }
        h1, h2, h3 { letter-spacing: 0; color: #17212b; }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #d9e2ec;
            border-radius: 8px;
            padding: 12px 14px;
            box-shadow: 0 1px 2px rgba(31, 41, 51, 0.05);
        }
        div[data-testid="stMetric"] label { color: #52606d; }
        .briefing-panel {
            background: #ffffff;
            border: 1px solid #d9e2ec;
            border-radius: 8px;
            padding: 18px 20px;
            margin: 14px 0 18px;
            box-shadow: 0 1px 3px rgba(31, 41, 51, 0.05);
        }
        .briefing-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 14px;
        }
        .briefing-item {
            border-left: 3px solid #2563eb;
            padding-left: 10px;
            min-height: 66px;
        }
        .briefing-label {
            color: #52606d;
            font-size: 0.78rem;
            text-transform: uppercase;
            font-weight: 700;
        }
        .briefing-value {
            color: #17212b;
            font-size: 1rem;
            line-height: 1.35;
            margin-top: 4px;
            font-weight: 650;
        }
        .section-note {
            color: #52606d;
            font-size: 0.95rem;
            line-height: 1.45;
        }
        .source-pill {
            display: inline-block;
            border: 1px solid #cbd5e1;
            border-radius: 999px;
            padding: 4px 10px;
            margin: 0 6px 6px 0;
            background: #fff;
            color: #334155;
            font-size: 0.82rem;
        }
        @media (max-width: 900px) {
            .briefing-grid { grid-template-columns: 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def line_chart(national: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=national["year"],
            y=national["production_twh"],
            name="Production",
            mode="lines+markers",
            line=dict(color=PALETTE["teal"], width=3),
            hovertemplate="<b>Year:</b> %{x}<br><b>Production:</b> %{y:.2f} TWh<extra>Electricity generated domestically in Kyrgyzstan.</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=national["year"],
            y=national["consumption_twh"],
            name="Consumption",
            mode="lines+markers",
            line=dict(color=PALETTE["blue"], width=3),
            hovertemplate="<b>Year:</b> %{x}<br><b>Consumption:</b> %{y:.2f} TWh<extra>Total electricity demand or final consumption.</extra>",
        )
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        height=420,
        yaxis_title="TWh",
        xaxis_title="Year",
        legend_title_text="",
        hovermode="x unified",
    )
    return fig


def balance_chart(national: pd.DataFrame) -> go.Figure:
    colors = [PALETTE["green"] if value >= 0 else PALETTE["red"] for value in national["domestic_gap_twh"]]
    fig = go.Figure(
        go.Bar(
            x=national["year"],
            y=national["domestic_gap_twh"],
            marker_color=colors,
            name="Domestic production gap",
            hovertemplate="<b>Year:</b> %{x}<br><b>Domestic gap:</b> %{y:.2f} TWh<extra>Production minus consumption before imports and exports.</extra>",
        )
    )
    fig.add_hline(y=0, line_color="#94a3b8", line_width=1)
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        height=320,
        yaxis_title="TWh",
        xaxis_title="Year",
        title="Domestic production gap before imports",
        showlegend=False,
    )
    return fig


def generation_mix_chart(national: pd.DataFrame) -> go.Figure:
    mix_columns = [column for column in ["hydro_twh", "thermal_twh", "solar_twh", "wind_twh"] if column in national]
    mix = national[["year", *mix_columns]].melt("year", var_name="source", value_name="twh")
    labels = {
        "hydro_twh": "Hydropower",
        "thermal_twh": "Fossil / thermal",
        "solar_twh": "Solar",
        "wind_twh": "Wind",
    }
    mix["source"] = mix["source"].map(labels)
    fig = px.area(
        mix,
        x="year",
        y="twh",
        color="source",
        color_discrete_map={
            "Hydropower": PALETTE["teal"],
            "Fossil / thermal": PALETTE["amber"],
            "Solar": PALETTE["cyan"],
            "Wind": PALETTE["violet"],
        },
    )
    fig.update_traces(
        hovertemplate="<b>Year:</b> %{x}<br><b>Generation:</b> %{y:.2f} TWh<extra>Annual electricity generation by source.</extra>"
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        height=340,
        yaxis_title="TWh",
        xaxis_title="Year",
        legend_title_text="",
    )
    return fig


def energy_mix_share_chart(national: pd.DataFrame) -> go.Figure:
    mix_columns = [column for column in ["hydro_twh", "thermal_twh", "solar_twh", "wind_twh"] if column in national]
    mix = national[["year", *mix_columns]].copy()
    total = mix[mix_columns].sum(axis=1).replace(0, pd.NA)
    for column in mix_columns:
        mix[column] = mix[column] / total * 100
    mix = mix.melt("year", var_name="source", value_name="share")
    labels = {
        "hydro_twh": "Hydropower",
        "thermal_twh": "Fossil / thermal",
        "solar_twh": "Solar",
        "wind_twh": "Wind",
    }
    mix["source"] = mix["source"].map(labels)
    fig = px.bar(
        mix,
        x="year",
        y="share",
        color="source",
        color_discrete_map={
            "Hydropower": PALETTE["teal"],
            "Fossil / thermal": PALETTE["amber"],
            "Solar": PALETTE["cyan"],
            "Wind": PALETTE["violet"],
        },
    )
    fig.update_traces(
        hovertemplate="<b>Year:</b> %{x}<br><b>Share:</b> %{y:.1f}%<extra>Share of annual electricity generation by source.</extra>"
    )
    fig.update_layout(
        barmode="stack",
        margin=dict(l=20, r=20, t=30, b=20),
        height=340,
        yaxis_title="Generation mix, %",
        xaxis_title="Year",
        legend_title_text="",
    )
    return fig


def trade_chart(national: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=national["year"],
            y=national["imports_twh"],
            name="Imports",
            marker_color=PALETTE["blue"],
            hovertemplate="<b>Year:</b> %{x}<br><b>Imports:</b> %{y:.2f} TWh<extra>Electricity brought into Kyrgyzstan from other systems.</extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=national["year"],
            y=-national["exports_twh"],
            name="Exports",
            marker_color=PALETTE["green"],
            hovertemplate="<b>Year:</b> %{x}<br><b>Exports:</b> %{customdata:.2f} TWh<extra>Electricity sent from Kyrgyzstan to other systems.</extra>",
            customdata=national["exports_twh"],
        )
    )
    fig.add_trace(
        go.Scatter(
            x=national["year"],
            y=national["imports_twh"] - national["exports_twh"],
            name="Net imports",
            mode="lines+markers",
            line=dict(color=PALETTE["ink"], width=3),
            hovertemplate="<b>Year:</b> %{x}<br><b>Net imports:</b> %{y:.2f} TWh<extra>Imports minus exports. Higher values indicate greater import dependence.</extra>",
        )
    )
    fig.add_hline(y=0, line_color="#94a3b8", line_width=1)
    fig.update_layout(
        barmode="relative",
        margin=dict(l=20, r=20, t=30, b=20),
        height=340,
        yaxis_title="TWh",
        xaxis_title="Year",
        title="Electricity trade and independence trend",
        legend_title_text="",
        hovermode="x unified",
    )
    return fig


def time_intelligence_chart(national: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=national["year"],
            y=national["demand_yoy_pct"],
            name="Demand YoY",
            marker_color=PALETTE["blue"],
            hovertemplate="<b>Year:</b> %{x}<br><b>Demand YoY:</b> %{y:.1f}%<extra>Year-on-year growth in electricity consumption.</extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=national["year"],
            y=national["production_yoy_pct"],
            name="Production YoY",
            marker_color=PALETTE["teal"],
            hovertemplate="<b>Year:</b> %{x}<br><b>Production YoY:</b> %{y:.1f}%<extra>Year-on-year growth in domestic electricity generation.</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=national["year"],
            y=national["seasonal_deviation_index"],
            name="Deviation from 3-year demand trend",
            mode="lines+markers",
            line=dict(color=PALETTE["ink"], width=3),
            hovertemplate="<b>Year:</b> %{x}<br><b>Trend deviation:</b> %{y:.1f}%<extra>Latest demand compared with the 3-year rolling demand trend.</extra>",
        )
    )
    fig.add_hline(y=0, line_color="#94a3b8", line_width=1)
    fig.update_layout(
        barmode="group",
        margin=dict(l=20, r=20, t=30, b=20),
        height=360,
        yaxis_title="Percent",
        xaxis_title="Year",
        title="Year-on-year change and trend deviation",
        legend_title_text="",
        hovermode="x unified",
    )
    return fig


def scenario_spread_chart(scenarios: pd.DataFrame) -> go.Figure:
    fig = px.line(
        scenarios,
        x="date",
        y="forecast_twh",
        color="scenario",
        color_discrete_map={
            "Dry year": PALETTE["red"],
            "Normal year": PALETTE["blue"],
            "Wet year": PALETTE["teal"],
        },
    )
    fig.update_traces(line=dict(width=3))
    fig.update_traces(
        hovertemplate="<b>Month:</b> %{x|%b %Y}<br><b>Forecast demand:</b> %{y:.2f} TWh<extra>Scenario-based monthly demand forecast.</extra>"
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        height=360,
        yaxis_title="Monthly demand, TWh",
        xaxis_title="",
        title="Scenario spread",
        legend_title_text="",
        hovermode="x unified",
    )
    return fig


def security_gauge(score: float, label: str) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100"},
            title={"text": label},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": PALETTE["ink"]},
                "steps": [
                    {"range": [0, 50], "color": "#fee2e2"},
                    {"range": [50, 75], "color": "#fef3c7"},
                    {"range": [75, 100], "color": "#dcfce7"},
                ],
                "threshold": {"line": {"color": PALETTE["red"], "width": 3}, "value": 50},
            },
        )
    )
    fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=260)
    return fig


def regional_risk_chart(regional_risk: pd.DataFrame) -> go.Figure:
    colors = {"High": PALETTE["red"], "Medium": PALETTE["amber"], "Low": PALETTE["green"]}
    ordered = regional_risk.sort_values("risk_score", ascending=True)
    fig = go.Figure(
        go.Bar(
            y=ordered["region"],
            x=ordered["risk_score"],
            orientation="h",
            marker_color=ordered["risk"].map(colors),
            text=ordered["risk"],
            textposition="inside",
            hovertemplate="<b>Region:</b> %{y}<br><b>Risk score:</b> %{x:.1f}<extra>Regional risk combines deficit, demand concentration, and distribution losses.</extra>",
        )
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        height=380,
        xaxis_title="Risk score",
        yaxis_title="",
        showlegend=False,
    )
    return fig


def regional_bar_chart(regional: pd.DataFrame) -> go.Figure:
    ordered = regional.sort_values("consumption_gwh", ascending=True)
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=ordered["region"],
            x=ordered["consumption_gwh"],
            orientation="h",
            name="Consumption",
            marker_color=PALETTE["blue"],
            hovertemplate="<b>Region:</b> %{y}<br><b>Consumption:</b> %{x:.0f} GWh<extra>Regional electricity consumption.</extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            y=ordered["region"],
            x=ordered["production_gwh"],
            orientation="h",
            name="Production",
            marker_color=PALETTE["teal"],
            hovertemplate="<b>Region:</b> %{y}<br><b>Production:</b> %{x:.0f} GWh<extra>Regional electricity production.</extra>",
        )
    )
    fig.update_layout(
        barmode="group",
        margin=dict(l=20, r=20, t=30, b=20),
        height=430,
        xaxis_title="GWh",
        yaxis_title="",
        legend_title_text="",
    )
    return fig


def forecast_chart(forecast: pd.DataFrame) -> go.Figure:
    observed = forecast[forecast["period"].eq("Observed")]
    future = forecast[forecast["period"].eq("Forecast")]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=observed["date"],
            y=observed["forecast_twh"],
            name="Observed demand",
            line=dict(color=PALETTE["ink"], width=2),
            hovertemplate="<b>Month:</b> %{x|%b %Y}<br><b>Observed pattern:</b> %{y:.2f} TWh<extra>Monthly pattern estimated from annual data for planning use.</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=future["date"],
            y=future["upper_twh"],
            name="Upper range",
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hovertemplate="<b>Month:</b> %{x|%b %Y}<br><b>Upper range:</b> %{y:.2f} TWh<extra>Upper confidence range around the forecast.</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=future["date"],
            y=future["lower_twh"],
            name="Likely range",
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(37, 99, 235, 0.16)",
            line=dict(width=0),
            hovertemplate="<b>Month:</b> %{x|%b %Y}<br><b>Lower range:</b> %{y:.2f} TWh<extra>Lower confidence range around the forecast.</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=future["date"],
            y=future["forecast_twh"],
            name="Forecast demand",
            line=dict(color=PALETTE["blue"], width=3),
            hovertemplate="<b>Month:</b> %{x|%b %Y}<br><b>Forecast demand:</b> %{y:.2f} TWh<extra>Scenario-adjusted demand forecast for planning, not dispatch.</extra>",
        )
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        height=460,
        yaxis_title="Monthly demand, TWh",
        xaxis_title="",
        hovermode="x unified",
        legend_title_text="",
    )
    return fig
