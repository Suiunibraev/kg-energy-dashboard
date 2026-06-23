# Project Context: Kyrgyzstan Energy Intelligence Dashboard

## Purpose

This project is a Streamlit-based energy intelligence and policy decision-support dashboard for Kyrgyzstan. It is designed for policymakers, energy planners, and non-technical Ministry staff who need a clear view of electricity security, production-demand balance, import dependency, ПЭС useful supply, and seasonal forecast uncertainty.

The project has moved beyond a basic analytics dashboard. It now includes an explainable policy layer, auditable rules, recommended actions, scenario forecasting, and a downloadable executive PDF briefing.

## Current Architecture

```text
app.py                         Streamlit entry point and page composition
energy_dashboard/
  data_sources.py              Public data loaders, national fallback data, official ПЭС supply and derived metrics
  forecasting.py               Monthly demand history construction and scenario forecast logic
  policy.py                    Energy Security Index, policy rules, actions, briefing text
  reporting.py                 One-page PDF briefing generator using ReportLab
  ui.py                        Plotly chart builders and Streamlit CSS/theme helpers
data/
  regional_useful_supply_2024.csv  Official 2024 useful supply by ПЭС service territory
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
4. Page-scoped controls choose the historical year range or forecast display horizon.
5. `forecast_demand()` creates monthly demand forecasts.
6. `policy.py` computes the Energy Security Index, policy rules, recommended actions, situation briefing, and time-intelligence indicators.
7. `ui.py` renders Plotly charts with explanatory hover definitions.
8. `reporting.py` generates a downloadable executive energy briefing PDF.

## Main User-Facing Sections

- Executive Overview with data year, source state, load time, current factual indicators, and recent-trend context
- Energy Security Assessment with a fixed 12-month scoring window, scenario sensitivity, actions, evidence, and PDF
- Policy Rules audit trail
- National Monitoring historical charts
- Regional Planning for official ПЭС useful supply and separately labeled derived context
- Scenario Planning for monthly energy forecasts
- Methodology
- Data & Handoff

## Current Functionality

### National Monitoring

The dashboard compares:

- Electricity production
- Electricity consumption
- Domestic production gap before trade
- Accounting reconciliation residual after imports and exports
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

The regional view uses `data/regional_useful_supply_2024.csv`. It includes:

- ПЭС service-territory map
- Official annual useful-supply comparison
- Population and derived per-capita/share indicators
- Source document and row-level provenance

Production, distribution losses, balance, status, and regional risk ranking are
unavailable and are not estimated. ПЭС territories are network service areas,
not guaranteed strict oblast boundaries.

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
- Illustrative model ranges use `1.64 * residual_std`; they are uncalibrated sensitivity bands, not probabilistic confidence intervals.

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

Production coverage and forecast reserve margin are related energy-coverage measures and together account for 60 of 100 points. The weights are unchanged, but this concentration is disclosed in the UI, PDF, and documentation.

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
- Highest forecast winter-month energy
- Flagged policy rules

Example actions include:

- Secure winter import or reserve contracts
- Prepare dry-year hydropower contingency schedule
- Target winter demand-response measures
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

### Official Regional Useful-Supply Data

File:

```text
data/regional_useful_supply_2024.csv
```

Columns:

- `year`
- `region`
- `source_region_label`
- `territory_type`
- `lat`
- `lon`
- `useful_supply_gwh`
- `metric`
- `data_quality`
- `data_provenance`
- `source_organization`
- `source_document`
- `source_url`

Production, distribution losses, balance, and status are unavailable. The
loader exposes null compatibility fields for these metrics and does not
calculate a regional surplus/deficit.

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
- Official ПЭС useful-supply bar chart
- Forecast chart with illustrative upper and lower model ranges

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
- unavailable-regional-risk and recommended-actions contract

Run compile checks:

```bash
python3 -m compileall app.py energy_dashboard tests
```

Run direct tests without pytest:

```bash
python3 -c "from tests.test_data_contract import test_national_data_contract, test_regional_data_contract, test_forecast_contract, test_security_index_contract, test_policy_rules_contract, test_actions_do_not_use_unavailable_regional_risk; test_national_data_contract(); test_regional_data_contract(); test_forecast_contract(); test_security_index_contract(); test_policy_rules_contract(); test_actions_do_not_use_unavailable_regional_risk(); print('checks passed')"
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

- Regional useful-supply data is official 2024 ПЭС service-territory data; production, losses, balance, and risk remain unavailable.
- Public national data is annual and country-level; it is not enough for dispatch-grade planning.
- Forecast monthly seasonality is estimated from annual data.
- Model ranges are uncalibrated sensitivity bands, not probabilistic confidence intervals.
- Energy Security Index weights and thresholds are prototype policy assumptions.
- The Security Index always uses a fixed 12-month demand assessment window; chart horizon does not change the score.
- Scenario hydropower multipliers affect scenario balance estimates but do not replace current production in the Security Index.
- Recommended actions are rule-based planning prompts, not binding operational recommendations.
- When core national data falls back to packaged starter data, the app shows a prominent warning and disables PDF export.
- Source "Loaded at" timestamps are app load/request times, not original source publication dates.
- Solar and wind are supported in the UI/data contract, but public source rows may be zero or unavailable depending on data source.
- The PDF briefing is text/table based; it does not yet embed charts.

## Pending Improvements

High priority:

- Add real monthly demand data if available.
- Extend the official ПЭС useful-supply series and obtain official production and loss data.
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

- Completed the Version 1 credibility pass: fixed 12-month assessment window, explicit scenario limitation, corrected monthly-energy terminology, non-prescriptive recommendations, executive source context, regional visual hierarchy, and fallback safeguards.
- Added policy decision-support layer in `energy_dashboard/policy.py`.
- Added PDF briefing generator in `energy_dashboard/reporting.py`.
- Added source load timestamps and safer load failure handling.
- Added definitions expander and explanatory Plotly hover templates.
- Added policy tests in `tests/test_data_contract.py`.
- Integrated official 2024 ПЭС useful supply and disabled unsupported regional calculations.
- Fixed the Security Index forecast assessment window at 12 months.
- Added explicit fallback-mode warnings and disabled PDF export in fallback mode.
- Renamed monthly forecast maxima to avoid implying instantaneous peak demand.
- Renamed synthetic monthly history from Observed to Estimated monthly history.
- Added exact forecast-period labels and warnings when part of the model period has elapsed.
- Removed the accounting reconciliation residual from Executive Overview KPIs.
- Reclassified regional population as Official source / mapped.
- Disclosed that related energy-coverage components account for 60 of 100 Security Index points.

## Practical Notes For Future Sessions

- Before changing behavior, inspect `app.py`, `energy_dashboard/policy.py`, and `energy_dashboard/ui.py`.
- Keep policy formulas centralized in `policy.py`; avoid scattering policy thresholds through `app.py`.
- Keep chart definitions centralized in `ui.py`; use hover templates for non-technical interpretation.
- Keep data loading/fallback behavior in `data_sources.py`.
- If adding dependencies, update `requirements.txt` and verify Streamlit Cloud compatibility.
- If changing tests, remember local `pytest` may not be installed; use `requirements-dev.txt`.
- After local commits, GitHub Desktop may be needed to push because terminal Git authentication may not be configured.
