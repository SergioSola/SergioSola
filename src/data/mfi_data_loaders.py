"""
Data loaders for the Monetary-Fiscal Interactions (MFI) research programme.

Handles downloading and processing data from:
  1. IMF World Economic Outlook (WEO) — debt, fiscal balance, GDP growth
  2. FRED — Treasury yields, macro variables
  3. BIS — Government bond yields, credit to private sector
  4. Sovereign CDS / spreads

Each loader returns a clean DataFrame ready for calibration or estimation.
When data sources require manual download, functions provide instructions
and fall back to synthetic data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional
import urllib.request
import io

from src.utils.config import RAW_DIR, PROCESSED_DIR, EXTERNAL_DIR


# ═══════════════════════════════════════════════════════════════════════════
# 1. IMF WEO Data
# ═══════════════════════════════════════════════════════════════════════════

def load_imf_weo_data(
    filepath: Optional[Path] = None,
    countries: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Load IMF World Economic Outlook data for calibration targets.

    Variables: real GDP growth, inflation, debt-to-GDP, fiscal balance,
    current account balance.

    If pre-downloaded CSV is available, loads it. Otherwise provides
    download instructions and returns synthetic calibration targets.

    Parameters
    ----------
    filepath : Path to pre-downloaded WEO CSV
    countries : list of ISO3 country codes to filter

    Returns
    -------
    DataFrame with columns: country, year, gdp_growth, inflation,
    debt_gdp, fiscal_balance_gdp, current_account_gdp
    """
    raw_path = filepath or RAW_DIR / "imf_weo.csv"
    if raw_path.exists():
        df = pd.read_csv(raw_path)
        if countries:
            df = df[df["country"].isin(countries)]
        return df

    print(
        "IMF WEO data not found.\n"
        "To download:\n"
        "  1. Visit https://www.imf.org/en/Publications/WEO/weo-database\n"
        "  2. Select variables: NGDP_RPCH, PCPIPCH, GGXWDG_NGDP, GGXCNL_NGDP, BCA_NGDPD\n"
        "  3. Select countries of interest\n"
        "  4. Export as CSV and save to data/raw/imf_weo.csv\n\n"
        "Returning synthetic calibration targets."
    )
    return _synthetic_weo_data(countries)


def _synthetic_weo_data(
    countries: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Generate synthetic WEO-style data for calibration."""
    if countries is None:
        countries = ["USA", "GBR", "DEU", "FRA", "ITA", "JPN", "CAN"]

    rng = np.random.default_rng(42)
    years = list(range(2000, 2025))
    rows = []

    # Country-specific baseline parameters
    baselines = {
        "USA": (2.2, 2.5, 80, -5.0, -3.0),
        "GBR": (1.8, 2.3, 75, -4.0, -3.5),
        "DEU": (1.5, 1.8, 60, -1.0, 6.0),
        "FRA": (1.6, 1.9, 85, -3.5, -1.0),
        "ITA": (0.5, 1.8, 120, -3.0, 1.5),
        "JPN": (0.8, 0.5, 200, -5.0, 3.0),
        "CAN": (2.0, 2.2, 70, -2.0, -2.5),
    }
    default_baseline = (1.5, 2.0, 80, -3.0, 0.0)

    for country in countries:
        base = baselines.get(country, default_baseline)
        for year in years:
            rows.append({
                "country": country,
                "year": year,
                "gdp_growth": base[0] + rng.normal(0, 1.5),
                "inflation": max(base[1] + rng.normal(0, 1.0), -1),
                "debt_gdp": base[3] + 2.0 * (year - 2000) + rng.normal(0, 3),
                "fiscal_balance_gdp": base[3] + rng.normal(0, 2.0),
                "current_account_gdp": base[4] + rng.normal(0, 1.5),
            })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Sovereign Bond Yields
# ═══════════════════════════════════════════════════════════════════════════

def load_sovereign_yields(
    filepath: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Load sovereign bond yields for calibration and estimation.

    Sources: FRED (US Treasuries), ECB SDW (Euro area), BIS.

    Returns DataFrame with columns: date, country, maturity, yield
    """
    raw_path = filepath or RAW_DIR / "sovereign_yields.csv"
    if raw_path.exists():
        return pd.read_csv(raw_path, parse_dates=["date"])

    print(
        "Sovereign yield data not found.\n"
        "For US Treasuries, data is fetched from FRED automatically.\n"
        "For other countries, download from:\n"
        "  - ECB SDW: https://sdw.ecb.europa.eu/\n"
        "  - BIS: https://stats.bis.org/\n"
        "Returning synthetic yield data."
    )
    return _synthetic_sovereign_yields()


def _synthetic_sovereign_yields() -> pd.DataFrame:
    """Generate synthetic sovereign yield data."""
    rng = np.random.default_rng(42)
    dates = pd.date_range("2000-01-01", "2024-12-31", freq="MS")
    countries = ["USA", "DEU", "ITA", "JPN", "GBR"]
    maturities = [2, 5, 10]

    base_yields = {
        "USA": {2: 2.5, 5: 3.0, 10: 3.5},
        "DEU": {2: 1.5, 5: 2.0, 10: 2.5},
        "ITA": {2: 2.5, 5: 3.5, 10: 4.5},
        "JPN": {2: 0.2, 5: 0.5, 10: 1.0},
        "GBR": {2: 2.0, 5: 2.5, 10: 3.0},
    }

    rows = []
    for country in countries:
        for maturity in maturities:
            base = base_yields[country][maturity]
            # Random walk with mean reversion
            y = base
            for date in dates:
                y = 0.99 * y + 0.01 * base + rng.normal(0, 0.1)
                y = max(y, -0.5)
                rows.append({
                    "date": date,
                    "country": country,
                    "maturity": maturity,
                    "yield": round(y, 4),
                })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
# 3. Calibration Targets
# ═══════════════════════════════════════════════════════════════════════════

def build_calibration_targets(
    country: str = "USA",
    period: tuple[int, int] = (2000, 2019),
) -> dict:
    """
    Build calibration targets from WEO and yield data.

    Returns a dict of steady-state targets for the DSGE model:
    debt_gdp, fiscal_balance_gdp, inflation, real_rate, growth,
    sovereign_spread, current_account_gdp.
    """
    weo = load_imf_weo_data(countries=[country])
    weo = weo[(weo["year"] >= period[0]) & (weo["year"] <= period[1])]

    yields = load_sovereign_yields()
    if len(yields) > 0:
        country_yields = yields[yields["country"] == country]
        yield_10y = country_yields[country_yields["maturity"] == 10]["yield"].mean()
    else:
        yield_10y = 3.5

    targets = {
        "debt_gdp": weo["debt_gdp"].mean() / 100,
        "fiscal_balance_gdp": weo["fiscal_balance_gdp"].mean() / 100,
        "inflation": weo["inflation"].mean() / 100,
        "gdp_growth": weo["gdp_growth"].mean() / 100,
        "sovereign_yield_10y": yield_10y / 100,
        "current_account_gdp": weo["current_account_gdp"].mean() / 100,
        "country": country,
        "period": f"{period[0]}-{period[1]}",
    }

    return targets


# ═══════════════════════════════════════════════════════════════════════════
# 4. FRED Fiscal/Monetary Data (extends existing FRED loader)
# ═══════════════════════════════════════════════════════════════════════════

MFI_FRED_SERIES = {
    "GFDEGDQ188S": "us_debt_gdp",           # Federal debt to GDP
    "FYFSGDA188S": "us_fiscal_surplus_gdp",  # Federal surplus/deficit to GDP
    "FEDFUNDS": "fed_funds",                 # Fed funds rate
    "GS10": "treasury_10y",                  # 10-year Treasury yield
    "GS2": "treasury_2y",                    # 2-year Treasury yield
    "T10YIE": "breakeven_10y",              # 10-year breakeven inflation
    "CPIAUCSL": "cpi",                       # CPI (for computing realised inflation)
}


def load_mfi_fred_data(save: bool = True) -> pd.DataFrame:
    """
    Download fiscal and monetary variables from FRED for the MFI programme.
    """
    from src.data.real_data_loaders import fetch_fred_series

    print("Downloading MFI-specific data from FRED...")
    series_dict = {}

    for fred_id, col_name in MFI_FRED_SERIES.items():
        s = fetch_fred_series(fred_id)
        if s is not None:
            series_dict[col_name] = s
            print(f"  {col_name}: {len(s)} observations")

    if not series_dict:
        print("  No FRED data available — check internet connection.")
        return pd.DataFrame()

    df = pd.DataFrame(series_dict)
    df.index.name = "date"

    if save:
        EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(EXTERNAL_DIR / "mfi_fred_data.csv")
        print(f"  Saved to {EXTERNAL_DIR / 'mfi_fred_data.csv'}")

    return df
