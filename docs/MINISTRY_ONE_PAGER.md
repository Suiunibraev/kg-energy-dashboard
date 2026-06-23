# Kyrgyzstan Energy Intelligence Dashboard

## What This Tool Does

This dashboard gives Ministry staff a clear view of Kyrgyzstan's electricity situation in one place. It shows total production, total consumption, the domestic production gap, net imports, official 2024 useful supply by ПЭС service territory, and a seasonal demand forecast.

The regional layer uses the Settlement Center's official 2024 annual useful-supply figures. Production, distribution losses, regional balance, and risk ranking are unavailable and are not estimated.

## How To Use It

1. Open the dashboard URL.
2. Start with Executive Overview to confirm the data year, source status, load time, and latest factual indicators.
3. Use National Monitoring to choose a historical period and compare production and consumption.
4. Use Regional Planning to rank official useful supply across ПЭС service territories and review provenance.
5. Use Energy Security Assessment to compare Dry, Normal, and Wet planning assumptions.
6. Use Scenario Planning to review monthly energy forecasts; these are monthly TWh projections, not instantaneous MW peaks.

## What Staff Can Learn

- Whether domestic production is keeping pace with consumption.
- Whether imports and exports bring the overall electricity balance closer to zero.
- Which ПЭС service territories have the highest official useful supply.
- Which regional production and loss fields still require official data.
- How monthly electricity energy may change under different planning assumptions.

## How The Ministry Can Expand It

The Ministry can connect internal data without rebuilding the dashboard. The data team can replace the starter files or connect a database/API with these fields:

- Annual national production, consumption, hydro generation, thermal generation, imports, and exports.
- Additional annual ПЭС useful-supply records and compatible official production,
  network-input, and distribution-loss data.
- Optional future upgrades: monthly demand, reservoir levels, inflows, temperature, plant availability, and planned maintenance.

With official Ministry data, forecasts can become more accurate and regional analysis can expand only when compatible official fields are available.

## Practical Note

The Security Index always uses a fixed 12-month forecast assessment window. Dry and Wet hydropower multipliers affect the scenario balance estimate, but they do not replace current production inside the Index; scenario score differences therefore reflect demand assumptions. If packaged fallback national data is active, the dashboard shows a prominent warning and disables the executive PDF.

Production coverage and forecast reserve margin are related energy-coverage measures and together account for 60 of 100 Index points. Forecasts show their exact model period; when part of that period has elapsed, the dashboard says so. Monthly history is estimated from annual totals, and displayed model ranges are uncalibrated sensitivity bands rather than probabilistic confidence intervals.

Regional population uses official administrative statistics mapped to ПЭС territories. It is labeled **Official source / mapped** because service-territory and administrative boundaries may not align exactly.

Forecasts should support planning discussions. They should not replace engineering judgment, dispatch procedures, procurement methodology, or official Ministry reporting.
