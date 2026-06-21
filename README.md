# Kyrgyzstan Energy Intelligence Dashboard

A production-oriented Streamlit dashboard for monitoring Kyrgyzstan's electricity system and presenting seasonal demand forecasts in a format that non-technical Ministry staff can use.

The application combines:

- National electricity monitoring using public data from Our World in Data and World Bank indicators.
- Regional comparison views with a clearly labeled starter regional dataset that can be replaced by Ministry feeds.
- Seasonal demand forecasting with dry, normal, and wet hydropower scenarios.
- A Ministry handoff one-pager in `docs/MINISTRY_ONE_PAGER.md`.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Data Sources

The app is designed to fetch public data at runtime and gracefully fall back to packaged starter data if a network request fails.

- Our World in Data energy dataset: annual electricity generation and demand fields for Kyrgyzstan.
- World Bank Open Data API: electricity access and population indicators.
- Starter regional data in `data/regional_energy_starter.csv`: estimated regional distribution values for demonstration and workflow design only.

The public sources provide strong country-level coverage. Public region-level operational data is not consistently available, so the bundled regional file is intentionally small, transparent, and easy to replace.

IEA and Kyrgyzstan National Statistics Committee data can be added through the same data contract when a stable public CSV/API or Ministry-provided extract is available. The current app keeps the live public loaders limited to endpoints that can run reliably on Streamlit Cloud without private credentials.

## How the Ministry Can Connect Internal Data

The app uses a narrow data contract so Ministry systems can be connected without redesigning the dashboard.

For national annual data, provide a CSV, database table, or API response with:

| column | meaning |
| --- | --- |
| `year` | calendar year |
| `production_twh` | total electricity produced |
| `consumption_twh` | total electricity demand or final consumption |
| `hydro_twh` | hydropower generation |
| `thermal_twh` | thermal generation |
| `imports_twh` | electricity imports |
| `exports_twh` | electricity exports |

For regional data, provide:

| column | meaning |
| --- | --- |
| `year` | calendar year |
| `region` | oblast or city name |
| `lat` / `lon` | map coordinates for the regional marker |
| `production_gwh` | regional electricity production |
| `consumption_gwh` | regional electricity consumption |
| `distribution_losses_pct` | estimated or measured losses |

Integration points:

- Replace `data/regional_energy_starter.csv` with official Ministry regional data using the same columns.
- Add database or API logic in `energy_dashboard/data_sources.py`.
- Keep the return shape of `load_energy_dataset()` unchanged so the Streamlit UI continues to work.
- Add credentials through Streamlit Cloud secrets, not hard-coded files.

## Deployment on Streamlit Cloud

1. Create a new GitHub repository.
2. From this folder, run:

```bash
git add .
git commit -m "Build Kyrgyzstan energy dashboard"
git branch -M main
git remote add origin https://github.com/<account>/<repo>.git
git push -u origin main
```

3. Go to [share.streamlit.io](https://share.streamlit.io).
4. Select the repository and set the main file path to `app.py`.
5. Deploy.

The included `requirements.txt`, `.streamlit/config.toml`, and `runtime.txt` are ready for Streamlit Cloud.

## Testing

```bash
python -m compileall app.py energy_dashboard tests
python -c "from tests.test_data_contract import test_national_data_contract, test_regional_data_contract, test_forecast_contract; test_national_data_contract(); test_regional_data_contract(); test_forecast_contract(); print('checks passed')"
```

If you prefer pytest:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## Project Structure

```text
app.py                         Streamlit app entry point
energy_dashboard/
  data_sources.py              Public API loading and starter fallback data
  forecasting.py               Seasonal forecast logic
  ui.py                        Chart and UI helper functions
data/
  regional_energy_starter.csv  Replaceable regional starter dataset
docs/
  MINISTRY_ONE_PAGER.md        Non-technical delivery handout
tests/
  test_data_contract.py        Basic data-contract checks
```

## Important Assumptions

- Public national data is suitable for the initial version and demonstration.
- Regional values in the starter file are not official operational records.
- Forecasts are planning aids, not dispatch instructions. They should be recalibrated with Ministry demand, reservoir, weather, and plant availability data before operational use.
