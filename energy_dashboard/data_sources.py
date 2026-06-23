from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
REGIONAL_USEFUL_SUPPLY_PATH = ROOT / "data" / "regional_useful_supply_2024.csv"
REGIONAL_POPULATION_SOURCE_URL = (
    "https://stat.gov.kg/media/files/4c29e08a-580e-42d4-92c6-65cdf5a1554c.pptx"
)
REGIONAL_POPULATION_SOURCE_LABEL = (
    "National Statistical Committee of the Kyrgyz Republic, population estimates as of January 1, 2025"
)
REGIONAL_POPULATION_2025 = {
    "Bishkek City": 1_321_900,
    "Chuy": 971_300,
    "Osh service territory": 1_890_200,
    "Jalal-Abad": 1_358_500,
    "Batken": 594_700,
    "Talas": 280_500,
    "Naryn": 314_900,
    "Issyk-Kul": 549_800,
}

OWID_ENERGY_CSV = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"
WORLD_BANK_API = "https://api.worldbank.org/v2/country/KGZ/indicator/{indicator}?format=json&per_page=200"


@dataclass(frozen=True)
class SourceStatus:
    name: str
    status: str
    detail: str
    last_updated: str = ""


def national_data_mode(statuses: list[SourceStatus]) -> str:
    """Return the credibility mode for the core national electricity series."""
    owid = next((status for status in statuses if status.name == "Our World in Data"), None)
    return "live" if owid is not None and owid.status == "live" else "fallback"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _fallback_national_data() -> pd.DataFrame:
    years = np.arange(2000, 2025)
    demand = 9.1 + (years - 2000) * 0.32 + 0.65 * np.sin((years - 2000) / 2.4)
    hydro = 10.7 + 1.4 * np.sin((years - 2000) / 1.8) - 0.05 * (years - 2012)
    thermal = 1.15 + 0.035 * (years - 2000)
    imports = np.maximum(0.15, demand - hydro - thermal + 0.8)
    exports = np.maximum(0.05, hydro + thermal - demand - 0.45)
    production = hydro + thermal
    population = 4.9 + (years - 2000) * 0.085

    return pd.DataFrame(
        {
            "year": years,
            "production_twh": production.round(2),
            "consumption_twh": demand.round(2),
            "hydro_twh": hydro.round(2),
            "thermal_twh": thermal.round(2),
            "imports_twh": imports.round(2),
            "exports_twh": exports.round(2),
            "population_m": population.round(2),
            "electricity_access_pct": np.minimum(100, 98.4 + (years - 2000) * 0.07).round(2),
            "source": "Packaged starter data",
        }
    )


def _read_owid_energy(timeout: int = 12) -> tuple[pd.DataFrame | None, SourceStatus]:
    try:
        response = requests.get(OWID_ENERGY_CSV, timeout=timeout)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        kg = df[df["iso_code"].eq("KGZ")].copy()
        if kg.empty:
            raise ValueError("KGZ rows were not found in OWID energy dataset")

        mapped = pd.DataFrame(
            {
                "year": kg["year"],
                "production_twh": kg.get("electricity_generation"),
                "consumption_twh": kg.get("electricity_demand"),
                "hydro_twh": kg.get("hydro_electricity"),
                "thermal_twh": kg.get("fossil_electricity"),
                "imports_twh": kg.get("net_elec_imports"),
                "exports_twh": np.nan,
                "population_m": kg.get("population") / 1_000_000,
                "electricity_access_pct": np.nan,
                "source": "Our World in Data",
            }
        )
        mapped = mapped.dropna(subset=["year"]).sort_values("year")
        net_imports = mapped["imports_twh"].copy()
        mapped["imports_twh"] = net_imports.clip(lower=0)
        mapped["exports_twh"] = (-net_imports).clip(lower=0)
        for column in ["production_twh", "consumption_twh", "hydro_twh", "thermal_twh"]:
            if column in mapped:
                mapped[column] = mapped[column].interpolate(limit_direction="both")

        mapped = mapped[mapped["year"].between(2000, 2025)]
        if mapped["production_twh"].notna().sum() < 8:
            raise ValueError("OWID returned too few usable electricity observations")

        return mapped.reset_index(drop=True), SourceStatus(
            "Our World in Data",
            "live",
            "Loaded country-level annual electricity data for Kyrgyzstan.",
            _utc_now(),
        )
    except Exception as exc:  # noqa: BLE001 - app should degrade gracefully.
        return None, SourceStatus("Our World in Data", "fallback", str(exc), _utc_now())


def _read_world_bank_indicator(indicator: str) -> pd.Series:
    response = requests.get(WORLD_BANK_API.format(indicator=indicator), timeout=10)
    response.raise_for_status()
    payload = response.json()
    rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
    records = {int(row["date"]): row["value"] for row in rows if row.get("value") is not None}
    return pd.Series(records, dtype="float64").sort_index()


def _merge_world_bank(national: pd.DataFrame) -> tuple[pd.DataFrame, SourceStatus]:
    try:
        access = _read_world_bank_indicator("EG.ELC.ACCS.ZS")
        population = _read_world_bank_indicator("SP.POP.TOTL") / 1_000_000
        out = national.copy()
        out = out.set_index("year")
        out["electricity_access_pct"] = out["electricity_access_pct"].fillna(access)
        out["population_m"] = out["population_m"].fillna(population)
        out = out.reset_index()
        return out, SourceStatus(
            "World Bank",
            "live",
            "Merged electricity access and population indicators.",
            _utc_now(),
        )
    except Exception as exc:  # noqa: BLE001
        return national, SourceStatus("World Bank", "fallback", str(exc), _utc_now())


def load_energy_dataset() -> tuple[pd.DataFrame, list[SourceStatus]]:
    national, owid_status = _read_owid_energy()
    statuses = [owid_status]
    if national is None:
        national = _fallback_national_data()

    national, wb_status = _merge_world_bank(national)
    statuses.append(wb_status)

    numeric_columns = [
        "production_twh",
        "consumption_twh",
        "hydro_twh",
        "thermal_twh",
        "imports_twh",
        "exports_twh",
        "population_m",
        "electricity_access_pct",
    ]
    for column in numeric_columns:
        national[column] = pd.to_numeric(national[column], errors="coerce")
    national[numeric_columns] = national[numeric_columns].interpolate(limit_direction="both")
    national["domestic_gap_twh"] = national["production_twh"] - national["consumption_twh"]
    national["net_balance_twh"] = (
        national["production_twh"] + national["imports_twh"] - national["consumption_twh"] - national["exports_twh"]
    )
    national["surplus_deficit_twh"] = national["net_balance_twh"]
    national["hydro_share_pct"] = np.where(
        national["production_twh"].gt(0),
        national["hydro_twh"] / national["production_twh"] * 100,
        np.nan,
    )
    return national.sort_values("year").reset_index(drop=True), statuses


def load_official_regional_dataset() -> pd.DataFrame:
    """Load official annual useful electricity supply by ПЭС service territory."""
    return pd.read_csv(REGIONAL_USEFUL_SUPPLY_PATH)


def load_regional_dataset() -> pd.DataFrame:
    regional = load_official_regional_dataset()
    regional["production_gwh"] = np.nan
    regional["distribution_losses_pct"] = np.nan
    regional["balance_gwh"] = np.nan
    regional["status"] = "Not available"
    return regional


def add_regional_planning_metrics(regional: pd.DataFrame, national: pd.DataFrame) -> pd.DataFrame:
    """Add transparent derived indicators to official ПЭС useful-supply data."""
    out = regional.copy()
    out["population"] = out["region"].map(REGIONAL_POPULATION_2025)
    out["demand_per_capita_kwh"] = np.where(
        out["population"].gt(0),
        out["useful_supply_gwh"] * 1_000_000 / out["population"],
        np.nan,
    )

    regional_year = int(out["year"].max())
    matching_national = national[national["year"].eq(regional_year)]
    national_row = matching_national.iloc[-1] if not matching_national.empty else national.sort_values("year").iloc[-1]
    national_demand_gwh = float(national_row["consumption_twh"]) * 1_000
    out["demand_share_pct"] = np.where(
        national_demand_gwh > 0,
        out["useful_supply_gwh"] / national_demand_gwh * 100,
        np.nan,
    )

    out["population_data_quality"] = "Official source / mapped"
    out["useful_supply_data_quality"] = "Official"
    out["production_data_quality"] = "Not available"
    out["distribution_losses_data_quality"] = "Not available"
    out["balance_data_quality"] = "Not available"
    out["demand_per_capita_data_quality"] = "Derived"
    out["demand_share_data_quality"] = "Derived"
    out["risk_data_quality"] = "Not available"
    out["population_source"] = REGIONAL_POPULATION_SOURCE_LABEL
    out["population_alignment_note"] = (
        "Official administrative population mapped to ПЭС territory; boundary alignment may be approximate."
    )
    return out
