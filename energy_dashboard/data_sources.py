from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
REGIONAL_STARTER_PATH = ROOT / "data" / "regional_energy_starter.csv"

OWID_ENERGY_CSV = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"
WORLD_BANK_API = "https://api.worldbank.org/v2/country/KGZ/indicator/{indicator}?format=json&per_page=200"


@dataclass(frozen=True)
class SourceStatus:
    name: str
    status: str
    detail: str


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
        )
    except Exception as exc:  # noqa: BLE001 - app should degrade gracefully.
        return None, SourceStatus("Our World in Data", "fallback", str(exc))


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
        )
    except Exception as exc:  # noqa: BLE001
        return national, SourceStatus("World Bank", "fallback", str(exc))


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
    national["surplus_deficit_twh"] = (
        national["production_twh"] + national["imports_twh"] - national["consumption_twh"] - national["exports_twh"]
    )
    national["hydro_share_pct"] = np.where(
        national["production_twh"].gt(0),
        national["hydro_twh"] / national["production_twh"] * 100,
        np.nan,
    )
    return national.sort_values("year").reset_index(drop=True), statuses


def load_regional_dataset() -> pd.DataFrame:
    regional = pd.read_csv(REGIONAL_STARTER_PATH)
    regional["balance_gwh"] = regional["production_gwh"] - regional["consumption_gwh"]
    regional["status"] = np.where(regional["balance_gwh"].ge(0), "Net producer", "Net consumer")
    return regional
