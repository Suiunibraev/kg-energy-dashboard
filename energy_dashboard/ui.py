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
    "panel": "#f6f8fb",
}


def apply_theme() -> None:
    import streamlit as st

    st.markdown(
        """
        <style>
        .stApp { background: #f8fafc; color: #1f2933; }
        [data-testid="stSidebar"] { background: #edf2f7; }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #d9e2ec;
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 1px 2px rgba(31, 41, 51, 0.04);
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
        )
    )
    fig.add_trace(
        go.Scatter(
            x=national["year"],
            y=national["consumption_twh"],
            name="Consumption",
            mode="lines+markers",
            line=dict(color=PALETTE["blue"], width=3),
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
    colors = [PALETTE["green"] if value >= 0 else PALETTE["red"] for value in national["surplus_deficit_twh"]]
    fig = go.Figure(
        go.Bar(
            x=national["year"],
            y=national["surplus_deficit_twh"],
            marker_color=colors,
            name="Surplus / deficit",
        )
    )
    fig.add_hline(y=0, line_color="#94a3b8", line_width=1)
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        height=320,
        yaxis_title="TWh",
        xaxis_title="Year",
        showlegend=False,
    )
    return fig


def generation_mix_chart(national: pd.DataFrame) -> go.Figure:
    mix = national[["year", "hydro_twh", "thermal_twh"]].melt("year", var_name="source", value_name="twh")
    labels = {"hydro_twh": "Hydropower", "thermal_twh": "Thermal"}
    mix["source"] = mix["source"].map(labels)
    fig = px.area(
        mix,
        x="year",
        y="twh",
        color="source",
        color_discrete_map={"Hydropower": PALETTE["teal"], "Thermal": PALETTE["amber"]},
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        height=340,
        yaxis_title="TWh",
        xaxis_title="Year",
        legend_title_text="",
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
        )
    )
    fig.add_trace(
        go.Bar(
            y=ordered["region"],
            x=ordered["production_gwh"],
            orientation="h",
            name="Production",
            marker_color=PALETTE["teal"],
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
        )
    )
    fig.add_trace(
        go.Scatter(
            x=future["date"],
            y=future["forecast_twh"],
            name="Forecast demand",
            line=dict(color=PALETTE["blue"], width=3),
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
