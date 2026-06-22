# Project Context: Kyrgyzstan Energy Intelligence Dashboard

## Purpose

This project is a Streamlit-based energy intelligence and policy decision-support dashboard for Kyrgyzstan. It is designed for policymakers, energy planners, and non-technical Ministry staff who need a clear view of electricity security, production-demand balance, import dependency, regional risk, and seasonal forecast uncertainty.

The project has moved beyond a basic analytics dashboard. It now includes an explainable policy layer, auditable rules, recommended actions, scenario forecasting, and a downloadable executive PDF briefing.

## Current Architecture

```text
app.py                         Streamlit entry point and page composition
energy_dashboard/
  data_sources.py              Public data loaders, starter fallback data, derived national/regional metrics
  forecasting.py               Monthly demand history construction and scenario forecast logic
  policy.py                    Energy Security Index, policy rules, regional risk, actions, briefing text
  reporting.py                 One-page PDF briefing generator using ReportLab
  ui.py                        Plotly chart builders and Streamlit CSS/theme helpers
data/
  regional_energy_starter.csv  Transparent starter regional dataset for demonstration
docs/
  MINISTRY_ONE_PAGER.md        Non-technical ministry handoff document
tests/
  test_data_contract.py        Data, forecast, and policy-logic contract tests
requirements.txt               Streamlit Cloud/runtime dependencies
requirements-dev.txt           Dev/test dependencies
runtime.txt                    Streamlit Cloud Python runtime setting
.streamlit/config.toml         Streamlit UI config
```

## Application Flow

1. `app.py` configures Streamlit and applies the custom theme from `energy_dashboard/ui.py`.
2. `get_data()` loads national and regional data through `energy_dashboard/data_sources.py`.
3. `ensure_national_metrics()` defensively creates missing derived columns such as `domestic_gap_twh`, `net_balance_twh`, `net_imports_twh`, `solar_twh`, and `wind_twh`.
4. Sidebar controls choose the year range, hydropower planning scenario, and forecast horizon.
5. `forecast_demand()` creates monthly demand forecasts.
6. `policy.py` computes the Energy Security Index, policy rules, regional risk, recommended actions, situation briefing, and time-intelligence indicators.
7. `ui.py` renders Plotly charts with explanatory hover definitions.
8. `reporting.py` generates a downloadable executive energy briefing PDF.

## Main User-Facing Sections

- Executive situation panel:
  - Today's energy status
  - Main risk driver
  - Key concern
  - Outlook
- Top KPI row:
  - Total production
  - Total consumption
  - Surplus/deficit before trade
  - Balance after imports/exports
  - Net imports
  - Energy Security Index
- Definitions expander:
  - Domestic gap
  - Net balance
  - Net imports
  - Security index
  - Reserve margin
  - Hydro vulnerability
  - Scenario spread
- Download Executive Energy Briefing button
- Tabs:
  - Situation briefing
  - Policy rules
  - National monitoring
  - Regional view
  - Forecast uncertainty
  - Data and handoff

## Current Functionality

### National Monitoring

The dashboard compares:

- Electricity production
- Electricity consumption
- Domestic production gap before trade
- Net balance after imports and exports
- Net imports
- Hydropower share
- Generation mix by source

Key formulas:

```python
domestic_gap_twh = production_twh - consumption_twh
net_balance_twh = production_twh + imports_twh - consumption_twh - exports_twh
net_imports_twh = imports_twh - exports_twh
hydro_share_pct = hydro_twh / production_twh * 100
```

### Regional View

The regional view uses `data/regional_energy_starter.csv`. It includes:

- Regional map
- Production vs consumption comparison
- Risk ranking by region
- Regional risk table

Important: regional data is explicitly marked as a transparent starter/demo dataset. It is not official operational data and should be replaced with Ministry regional feeds before real use.

### Forecasting

Forecasting lives in `energy_dashboard/forecasting.py`.

Available scenarios:

```python
SCENARIOS = {
    "Normal year": {"demand_multiplier": 1.00, "hydro_multiplier": 1.00},
    "Dry year": {"demand_multiplier": 1.04, "hydro_multiplier": 0.88},
    "Wet year": {"demand_multiplier": 0.98, "hydro_multiplier": 1.08},
}
```

Forecast method:

- Annual consumption is converted into synthetic monthly history using winter demand weights.
- Hydropower seasonality is approximated using separate monthly hydro weights.
- Holt-Winters exponential smoothing is used where possible:
  - additive trend
  - multiplicative seasonality
  - 12-month seasonal period
- If model fitting fails, the code falls back to a seasonal average plus simple trend.
- Confidence bands use `1.64 * residual_std`.

Known forecast caveat:

Monthly history is estimated from annual data, not actual monthly demand observations. The UI states this clearly. For operational forecasting, this should be recalibrated with official monthly demand, reservoir, weather, plant availability, and outage data.

### Policy Rules Layer

Policy logic lives in `energy_dashboard/policy.py`.

Current policy thresholds:

```python
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
```

Policy checks include:

- Domestic deficit
- Import dependency
- Hydropower seasonal vulnerability
- Demand growth pressure
- Forecast reserve margin

The point of this layer is interpretation consistency. It prevents the dashboard from feeling like a black-box score by showing exactly which thresholds are crossed.

### Energy Security Index

`calculate_security_index()` returns a 0-100 score and label:

- `Secure`: score >= 75
- `Moderate Risk`: score >= 50
- `High Risk`: score < 50

Index components:

- Production coverage: 35 points
- Hydropower dependency score: 20 points
- Recent demand growth score: 20 points
- Forecast reserve margin score: 25 points

Current score should be treated as a policy prototype, not an official Ministry methodology.

### Time Intelligence

`time_intelligence()` adds:

- Demand year-on-year growth
- Production year-on-year growth
- Demand 3-year rolling average
- Production 3-year rolling average
- Seasonal/trend deviation index
- Latest-year change summary

This supports the "what changed?" section.

### Recommended Actions

`recommended_actions()` generates a simplified action table based on:

- Domestic deficit
- Hydropower dependency
- Winter peak demand
- Highest regional risk score
- Flagged policy rules

Example actions include:

- Secure winter import or reserve contracts
- Prepare dry-year hydropower contingency schedule
- Target winter demand-response measures
- Prioritize grid reinforcement and loss reduction in the highest-risk region
- Review flagged policy rules in planning meetings

These actions are intentionally simplified and should be validated by energy-sector experts before operational use.

### PDF Briefing

`energy_dashboard/reporting.py` generates a one-page PDF using ReportLab.

The PDF includes:

- Current status
- Security index
- Executive summary
- Key metrics
- Situation panel
- Recommended actions
- Policy rule checks

Dependency:

```text
reportlab>=4.2,<5
```

## Data Sources

### Public National Data

Primary live source:

- Our World in Data energy dataset
- URL: `https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv`
- Used for:
  - electricity generation
  - electricity demand
  - hydropower generation
  - fossil/thermal generation
  - net electricity imports
  - population where available

World Bank source:

- World Bank Open Data API
- Used for:
  - electricity access
  - population

### Fallback Data

If public endpoints fail, `_fallback_national_data()` generates packaged starter national data from 2000-2024. This keeps the Streamlit app usable even when network/API access is unavailable.

### Regional Starter Data

File:

```text
data/regional_energy_starter.csv
```

Columns:

- `year`
- `region`
- `lat`
- `lon`
- `production_gwh`
- `consumption_gwh`
- `distribution_losses_pct`

Derived columns:

```python
balance_gwh = production_gwh - consumption_gwh
status = "Net producer" if balance_gwh >= 0 else "Net consumer"
```

### Source Freshness

The app currently displays "Loaded at" timestamps. These are request/load times, not original publication dates from source providers. This wording is intentional.

## UI and Charting

Charts are built in `energy_dashboard/ui.py` using Plotly.

Current charts:

- Production vs consumption line chart
- Domestic gap bar chart
- Generation mix area chart
- Generation mix share stacked bar chart
- Trade/import-export chart
- Time intelligence chart
- Scenario spread chart
- Security gauge
- Regional risk chart
- Regional production vs consumption bar chart
- Forecast chart with confidence band

Hover definitions have been added to chart traces so users see metric meaning, not only values.

The Streamlit UI uses custom CSS in `apply_theme()` for:

- light government/report style
- bordered KPI cards
- executive briefing panel
- source pills
- responsive briefing grid

## Testing

Current tests are in:

```text
tests/test_data_contract.py
```

Coverage includes:

- national data contract
- regional data contract
- forecast contract
- security index contract
- policy rules contract
- regional risk and recommended actions contract

Run compile checks:

```bash
python3 -m compileall app.py energy_dashboard tests
```

Run direct tests without pytest:

```bash
python3 -c "from tests.test_data_contract import test_national_data_contract, test_regional_data_contract, test_forecast_contract, test_security_index_contract, test_policy_rules_contract, test_regional_risk_and_actions_contract; test_national_data_contract(); test_regional_data_contract(); test_forecast_contract(); test_security_index_contract(); test_policy_rules_contract(); test_regional_risk_and_actions_contract(); print('checks passed')"
```

Run pytest:

```bash
pip install -r requirements-dev.txt
python3 -m pytest -q
```

Note: in the local environment during development, `pytest` was not installed until dev dependencies are installed.

## Deployment Setup

Designed for Streamlit Cloud.

Important files:

- `requirements.txt`
- `.streamlit/config.toml`
- `runtime.txt`
- `app.py`

Local run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Streamlit Cloud:

1. Push repo to GitHub.
2. Create/select app on Streamlit Cloud.
3. Main file path: `app.py`.
4. Reboot app after dependency or file-structure changes.

GitHub repository used during development:

```text
https://github.com/Suiunibraev/kg-energy-dashboard
```

Current repo workflow:

- Use GitHub Desktop if command-line authentication is unavailable.
- If local branch says `main...origin/main [ahead 1]`, click **Push origin** in GitHub Desktop.

## Known Limitations

- Regional data is a starter/demo dataset, not official operational data.
- Public national data is annual and country-level; it is not enough for dispatch-grade planning.
- Forecast monthly seasonality is estimated from annual data.
- Confidence bands are statistical approximations, not calibrated probabilistic forecasts.
- Energy Security Index weights and thresholds are prototype policy assumptions.
- Recommended actions are rule-based planning prompts, not binding operational recommendations.
- Source "Loaded at" timestamps are app load/request times, not original source publication dates.
- Solar and wind are supported in the UI/data contract, but public source rows may be zero or unavailable depending on data source.
- The PDF briefing is text/table based; it does not yet embed charts.

## Pending Improvements

High priority:

- Add real monthly demand data if available.
- Replace regional starter data with official Ministry regional data.
- Calibrate Energy Security Index weights with domain experts.
- Add actual source publication/update dates if available from APIs.
- Add screenshots/GIFs and a live app link to README.
- Add chart images to the PDF briefing.

Medium priority:

- Add severe drought and moderate drought scenarios.
- Add infrastructure tracker for plants, capacity, and planned projects.
- Add plant/outage/maintenance data once available.
- Add climate/hydrology inputs such as reservoir levels, inflow, snowpack, or precipitation.
- Add more tests for edge cases: missing columns, all-zero imports, empty regional data, failed source loads.

Portfolio polish:

- Add a "Why this matters" visual section to README with screenshots.
- Add a concise architecture diagram.
- Add a sample generated PDF under `docs/` or a screenshot of it.
- Add deployment URL once Streamlit app is live.

## Recent Important Changes

- Added policy decision-support layer in `energy_dashboard/policy.py`.
- Added PDF briefing generator in `energy_dashboard/reporting.py`.
- Added source load timestamps and safer load failure handling.
- Added definitions expander and explanatory Plotly hover templates.
- Added policy tests in `tests/test_data_contract.py`.
- Clarified forecast and regional starter-data limitations in the UI.

## Practical Notes For Future Sessions

- Before changing behavior, inspect `app.py`, `energy_dashboard/policy.py`, and `energy_dashboard/ui.py`.
- Keep policy formulas centralized in `policy.py`; avoid scattering policy thresholds through `app.py`.
- Keep chart definitions centralized in `ui.py`; use hover templates for non-technical interpretation.
- Keep data loading/fallback behavior in `data_sources.py`.
- If adding dependencies, update `requirements.txt` and verify Streamlit Cloud compatibility.
- If changing tests, remember local `pytest` may not be installed; use `requirements-dev.txt`.
- After local commits, GitHub Desktop may be needed to push because terminal Git authentication may not be configured.
