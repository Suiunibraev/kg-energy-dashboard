# Project Status: Kyrgyzstan Energy Intelligence Dashboard

## Purpose of This File

This document is the current development handoff for the Kyrgyzstan Energy Intelligence Dashboard. It summarizes the implemented architecture, user-facing features, methodologies, limitations, and recommended priorities so work can continue in a new session without rescanning the repository.

Current repository state when this file was created:

- Branch: `main`
- HEAD: `4c1b175` (`Update app.py`)
- Working tree: clean before adding this file

## Current Architecture

```text
app.py
  Streamlit entry point, sidebar navigation, page composition,
  page-scoped controls, tables, and PDF download

energy_dashboard/
  data_sources.py
    Public national data loaders, fallback data, derived national metrics,
    official 2024 ПЭС useful-supply loader, regional population mapping,
    provenance fields, and derived planning indicators

  forecasting.py
    Synthetic monthly history, Holt-Winters demand forecasting,
    confidence bands, and Dry/Normal/Wet scenario assumptions

  policy.py
    Energy Security Index, index breakdown, policy rules,
    year-over-year insights, scenario impact analysis,
    recommended actions, and evidence

  reporting.py
    One-page A4 Executive Energy Briefing PDF using ReportLab

  ui.py
    Plotly chart builders, dashboard theme, and styled sidebar navigation

data/
  regional_useful_supply_2024.csv
    Official annual useful electricity supply by ПЭС service territory

docs/
  MINISTRY_ONE_PAGER.md
    Non-technical Ministry handoff document

tests/
  test_data_contract.py
    National, regional, forecast, Security Index, policy-rule,
    and recommended-action contract checks

README.md
  Professional project overview for Ministry and technical audiences

requirements.txt
requirements-dev.txt
runtime.txt
.streamlit/config.toml
  Runtime, development, and Streamlit Cloud configuration
```

### Application flow

1. `app.py` loads national and regional data through `data_sources.py`.
2. National derived metrics are created defensively in `ensure_national_metrics()`.
3. Official ПЭС useful supply is enriched with population and clearly labeled derived planning indicators.
4. The latest national data is used for current factual indicators.
5. Forecast and policy functions create forecast-informed security assessments.
6. Sidebar navigation determines which page is rendered.
7. Page-specific controls affect only the relevant page.
8. The Executive Energy Briefing PDF is generated from the selected Energy Security Assessment assumptions.

## Completed Features

### Current national monitoring

- Electricity production and consumption
- Domestic production gap before trade
- Balance after imports and exports
- Imports, exports, and net imports
- Hydropower share
- Generation mix and generation-mix shares
- Historical year-range filtering on the National Monitoring page
- Time-intelligence chart and year-over-year indicators

### Executive Overview

The Executive Overview is intentionally factual and current-data focused. It shows:

- Production
- Consumption
- Domestic deficit
- Net imports
- Balance after trade
- Plain-English definitions and policy relevance for each metric

It does not show the Security Index, recommendations, or forecast-driven metrics.

### Energy Security Assessment

- Forecast Scenario control
- Forecast Horizon control
- Current Security Assessment
- Energy Security Index and risk level
- Main driver, key concern, and outlook
- Four-component Security Index breakdown
- Scenario Sensitivity Analysis for Dry, Normal, and Wet years
- Recommended actions
- Trigger/evidence for every recommendation
- “What Changed Since Last Year?” metrics and summary
- Downloadable Executive Energy Briefing PDF

The page explicitly states that the Security Index combines current conditions with future planning assumptions.

### Policy and audit layer

- Auditable policy thresholds
- Current values and statuses for each rule
- Domestic-deficit rule
- Import-dependency rule
- Hydropower-vulnerability rule
- Demand-growth rule
- Forecast reserve-margin rule
- Explainable recommended actions linked to actual trigger evidence

### Scenario planning

- Forecast-demand chart with confidence band
- Winter and summer peak indicators
- Scenario-spread chart
- Dry, Normal, and Wet scenario comparison
- Forecast table

The Scenario Planning page currently displays the standard Normal-year, 18-month baseline. Interactive forecast controls are located on the Energy Security Assessment page.

### Regional planning layer

- ПЭС service-territory map
- Official useful-supply chart
- Official useful-supply and provenance table
- Official regional population
- Derived useful supply per capita
- Derived share of national electricity demand
- Per-metric data-quality labels
- Visible source, assumption, and confidence notes
- Production, losses, balance, and risk ranking explicitly unavailable

### Reporting

The one-page Executive Energy Briefing PDF includes:

- Current status and summary
- Current national metrics
- Situation panel
- Scenario Impact Analysis
- Security Index breakdown
- What Changed Since Last Year
- Recommended actions with evidence
- Policy-rule checks
- Methodology and use note
- Ministry-style layout, footer, and page number

### Documentation and user guidance

- Professional README
- Architecture diagram
- Methodology page in the dashboard
- Definitions and interpretation guidance
- Clear appropriate-use and prohibited-use guidance
- Ministry handoff roadmap
- Sidebar data-source status

## Current Navigation Structure

Navigation uses a styled sidebar radio selector under **Dashboard Sections**:

1. **Executive Overview**
   - Latest factual national electricity situation
   - No forecast-informed security assessment

2. **Energy Security Assessment**
   - Forecast Scenario and Forecast Horizon controls
   - Current Security Assessment
   - Scenario Sensitivity Analysis
   - Actions, evidence, changes, and PDF

3. **Policy Rules**
   - Thresholds, current values, statuses, and time-intelligence chart

4. **National Monitoring**
   - Historical charts and national data table
   - Owns the Years Shown control

5. **Regional Planning**
   - ПЭС service-territory map, official useful supply, population,
     derived indicators, provenance, data quality, and territorial caveats

6. **Scenario Planning**
   - Forecast charts and standard planning-baseline outputs

7. **Methodology**
   - Plain-English explanation of formulas, forecast assumptions,
     sources, limitations, and interpretation

8. **Data & Handoff**
   - Source status, implementation notes, and dataset downloads

The sidebar keeps Data Status below navigation. Historical and forecast controls are not global.

## Security Index Methodology

The Energy Security Index is an explainable 0–100 policy prototype implemented in `energy_dashboard/policy.py`.

### Components

| Component | Maximum points | Current method |
| --- | ---: | --- |
| Production coverage | 35 | Current production-to-consumption ratio; full points at 105% coverage |
| Hydropower dependency | 20 | Full points up to 55% hydro share, declining as reliance rises |
| Recent demand growth | 20 | Uses average recent annual consumption growth; faster growth lowers the score |
| Forecast reserve margin | 25 | Compares current annual production with up to the first 12 forecast months |

### Formula summary

```python
security_index = (
    production_coverage_score
    + hydropower_dependency_score
    + demand_growth_score
    + forecast_reserve_margin_score
)
```

### Risk bands

- `Secure`: score >= 75
- `Moderate Risk`: score >= 50 and < 75
- `High Risk`: score < 50

### Current policy thresholds

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

These weights, thresholds, and bands are prototypes. They have not been formally adopted as a Ministry methodology and require expert calibration.

## Forecasting Methodology

Forecasting is implemented in `energy_dashboard/forecasting.py`.

### Monthly-history construction

The available public national series is annual. The application converts recent annual consumption into estimated monthly history using winter demand weights. Hydropower uses a separate monthly seasonal pattern.

This monthly history is synthetic; it is not observed monthly demand.

### Primary model

Holt-Winters exponential smoothing:

- Additive trend
- Multiplicative seasonality
- 12-month seasonal period
- Estimated initialization

### Fallback model

If Holt-Winters fitting fails, the application uses:

- Historical monthly seasonal averages
- A simple trend
- Residual variation estimated from annual seasonal differences

### Confidence bands

```python
lower = forecast - 1.64 * residual_std
upper = forecast + 1.64 * residual_std
```

These are approximate planning bands, not calibrated probabilistic intervals.

### Scenario assumptions

```python
SCENARIOS = {
    "Normal year": {"demand_multiplier": 1.00, "hydro_multiplier": 1.00},
    "Dry year": {"demand_multiplier": 1.04, "hydro_multiplier": 0.88},
    "Wet year": {"demand_multiplier": 0.98, "hydro_multiplier": 1.08},
}
```

The Security Index reserve-margin component uses up to the first 12 forecast months, even when the selected display horizon is longer. This behavior is unchanged and is explained in the UI.

## Regional Planning Layer Status

### Official 2024 ПЭС useful-supply contract

```text
year
region
source_region_label
territory_type
lat
lon
useful_supply_gwh
metric
data_quality
data_provenance
source_organization
source_document
source_url
```

The source is the Kyrgyz Electricity Settlement Center's *Brief electricity
balance for the Kyrgyz power system for 2024*, section 6.3. Published values
in thousand kWh are converted directly to GWh without estimation.

The dataset contains eight ПЭС service territories. These are network operating
areas rather than guaranteed one-to-one administrative oblast boundaries.
Ошское ПЭС is one source row; Osh City is therefore not shown separately.

### Added planning indicators

`add_regional_planning_metrics()` adds:

- `population`
- `demand_per_capita_kwh`
- `demand_share_pct`
- Per-metric data-quality fields
- Population-source description

### Data quality

| Metric | Classification |
| --- | --- |
| Regional population | Official |
| ПЭС useful electricity supply | Official |
| Regional production | Not available |
| Distribution losses | Not available |
| Balance and producer/consumer status | Not available |
| Useful supply per capita | Derived |
| Share of national demand | Derived |
| Regional risk score and level | Not available |

Population values are official public estimates from the National Statistical Committee of the Kyrgyz Republic, reported for January 1, 2025 and used as the end-2024 population position.

Official useful supply totals 12,597.767126 GWh across the eight published ПЭС
rows. Production, distribution losses, balance, status, and regional risk are
not estimated. Their compatibility fields are null or marked `Not available`.
The previous demonstration regional CSV is no longer loaded.

## Known Limitations

### Data

- Public national electricity data is annual and country-level.
- Public endpoints can fail or revise historical values.
- Fallback national data is starter data, not official operational data.
- “Loaded at” timestamps are request times, not source-publication dates.
- ПЭС territories may not exactly match administrative oblast boundaries.
- Official regional production and distribution-loss data remain unavailable.
- Useful supply and national demand have different accounting scopes; their
  derived percentage is not an energy-balance reconciliation.
- Solar and wind fields may be zero or unavailable in public data.

### Forecasting

- Monthly demand history is estimated from annual data.
- Forecasts do not include observed weather, reservoir levels, inflows,
  snowpack, outages, plant availability, fuel constraints, or network constraints.
- Confidence bands are approximate.
- Scenario multipliers are planning assumptions rather than calibrated hydrological models.

### Policy assessment

- Security Index weights and thresholds are prototypes.
- Recommended actions are simplified rule-based prompts.
- Scenario net-balance estimates use current generation/trade values and scenario hydropower indices.
- Risk labels are decision-support signals, not official determinations.

### Regional analysis

- Regional production, losses, balance, status, and risk ranking are disabled.
- Per-capita useful supply is derived from official useful supply and mapped
  official population; territorial alignment may be approximate.
- Regional outputs must not be used for budgeting, dispatch, procurement,
  investment approval, or official performance assessment.

### Operational readiness

- No authentication or role-based access control
- No official Ministry database/API integration
- No automated scheduled data pipeline
- No data approval or revision workflow
- No real-time operations or dispatch capability
- No formal user-acceptance, security, or production-reliability testing

## Outstanding Work

### Data integration

- Extend the official ПЭС series beyond 2024 when additional annual Settlement
  Center publications are validated.
- Obtain official ПЭС production and distribution-loss fields before restoring
  regional balance or risk calculations.
- Connect observed monthly national demand and generation.
- Add reservoir, inflow, snowpack, precipitation, weather, outage,
  maintenance, and plant-availability data.
- Add source publication dates and revision metadata.
- Add reconciliation and missing-data validation.

### Methodology

- Validate Security Index weights, score scaling, thresholds, and risk bands.
- Validate recommended actions with electricity-sector experts.
- Define an approved regional-risk methodology.
- Calibrate forecast confidence using observed monthly forecast errors.
- Consider additional drought-severity scenarios after expert review.

### Testing

- Add focused automated tests for:
  - Security Index breakdown summing to the unchanged total
  - Scenario Impact Analysis
  - Year-over-year summary selection
  - Recommended-action evidence
  - Regional planning indicators and missing population
  - Empty or malformed regional data
  - Failed public-source loads
  - PDF content and page count
- Run the full pytest suite in a repeatable development environment.

### Product and deployment

- Add verified screenshots and a live deployment URL.
- Add Kyrgyz and Russian localization if required.
- Add secure credentials and access controls for private Ministry sources.
- Add audit logging and versioned methodology records.
- Add infrastructure, outage, maintenance, and project trackers.
- Conduct formal security, performance, and user-acceptance testing.

## Recommended Next Steps

Recommended order for the next development session:

1. **Run and visually inspect the full app**
   - Confirm all eight navigation pages render correctly.
   - Pay particular attention to Energy Security Assessment controls,
     Scenario Sensitivity Analysis, and the PDF download.

2. **Add focused tests for recent features**
   - Security breakdown equality
   - Scenario comparison columns and score consistency
   - Recommendation evidence completeness
   - Year-over-year domestic-gap change and summary
   - Regional data-quality classifications

3. **Review information architecture with a policy user**
   - Confirm the separation between factual Executive Overview and
     forecast-informed Energy Security Assessment is understood.
   - Confirm Scenario Planning versus Energy Security Assessment responsibilities.

4. **Extend official regional-data integration**
   - Add validated annual ПЭС useful-supply publications after 2024.
   - Request official production, network-input, useful-supply, and loss data
     before considering balance or risk calculations.

5. **Begin monthly-data integration**
   - Prioritize observed monthly demand and generation.
   - Recalibrate seasonality and confidence bands before adding more model complexity.

6. **Calibrate the policy methodology**
   - Review index components, thresholds, labels, and action triggers with experts.
   - Record approved changes in versioned methodology documentation.

## Development Notes for a New Session

- Read `PROJECT_CONTEXT.md`, `PROJECT_STATUS.md`, and `CURRENT_TASK.md` first.
- Avoid scanning the entire repository unless required.
- Keep calculations centralized:
  - Data and fallbacks in `data_sources.py`
  - Forecasts in `forecasting.py`
  - Policy formulas and actions in `policy.py`
  - Charts and CSS in `ui.py`
  - PDF layout in `reporting.py`
- Do not duplicate Security Index formulas in `app.py`.
- Preserve the distinction between factual current data and forecast-informed assessment.
- Preserve explicit Official / Derived / Not available labels in regional analysis.
- If adding dependencies, update `requirements.txt` and verify Streamlit Cloud compatibility.

## Verification Commands

Compile:

```bash
python3 -m compileall app.py energy_dashboard tests
```

Run current contract checks without pytest:

```bash
python3 -c "from tests.test_data_contract import test_national_data_contract, test_regional_data_contract, test_forecast_contract, test_security_index_contract, test_policy_rules_contract, test_actions_do_not_use_unavailable_regional_risk; test_national_data_contract(); test_regional_data_contract(); test_forecast_contract(); test_security_index_contract(); test_policy_rules_contract(); test_actions_do_not_use_unavailable_regional_risk(); print('checks passed')"
```

Run pytest after installing development dependencies:

```bash
pip install -r requirements-dev.txt
python3 -m pytest -q
```

Run locally:

```bash
streamlit run app.py
```
