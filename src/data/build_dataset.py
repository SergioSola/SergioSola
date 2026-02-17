"""
Data pipeline: load raw data, clean, merge, and produce analysis-ready panels.

This module expects CSV/Excel files in data/raw/ with the following conventions:
  - returns.csv        : daily equity/CDS returns (columns = institution tickers)
  - institutions.csv   : metadata (ticker, name, sector, country, ...)
  - exposures.csv      : bilateral bank-NBFI exposures (source, target, amount, date)
  - macro.csv          : macro/financial variables (VIX, policy rates, spreads)
  - nbfi_sizes.csv     : country-level NBFI sector sizes from FSB data
  - fund_flows.csv     : fund-level AUM and net flows

When real data is unavailable, `generate_synthetic_data()` produces a realistic
simulated dataset for development and testing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

from src.utils.config import (
    RAW_DIR,
    PROCESSED_DIR,
    SAMPLE_START,
    SAMPLE_END,
    SECTOR_LABELS,
)


# ── Synthetic data generation ─────────────────────────────────────────────

def _generate_institution_metadata(
    n_banks: int = 30,
    n_nbfi: int = 50,
    seed: int = 42,
) -> pd.DataFrame:
    """Create a synthetic institution metadata table."""
    rng = np.random.default_rng(seed)

    sectors_nbfi = list(SECTOR_LABELS.keys() - {"bank"})
    countries = ["US", "GB", "DE", "FR", "JP", "CH", "CN", "CA", "AU", "BR"]

    rows = []
    for i in range(n_banks):
        rows.append({
            "ticker": f"BANK_{i:03d}",
            "name": f"Bank {i}",
            "sector": "bank",
            "country": rng.choice(countries),
        })
    for i in range(n_nbfi):
        rows.append({
            "ticker": f"NBFI_{i:03d}",
            "name": f"NBFI {i}",
            "sector": rng.choice(sectors_nbfi),
            "country": rng.choice(countries),
        })
    return pd.DataFrame(rows)


def _generate_returns(
    institutions: pd.DataFrame,
    start: str = SAMPLE_START,
    end: str = SAMPLE_END,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Simulate correlated daily returns with a common factor structure.

    Returns have:
      - a global factor (mimics VIX-linked risk-on/risk-off)
      - a sector factor
      - an idiosyncratic component
    Banks have lower vol than hedge funds; correlations increase in stress.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, end)
    n_dates = len(dates)
    n_inst = len(institutions)

    # sector volatility scales
    vol_map = {
        "bank": 0.015,
        "investment_fund": 0.012,
        "hedge_fund": 0.025,
        "pension_fund": 0.008,
        "insurance": 0.012,
        "mmf": 0.002,
        "direct_credit": 0.010,
        "broker_dealer": 0.020,
    }

    # global factor (regime-switching-like: sometimes high vol)
    global_factor = np.zeros(n_dates)
    regime = 0  # 0 = calm, 1 = stress
    for t in range(n_dates):
        if regime == 0 and rng.random() < 0.005:
            regime = 1
        elif regime == 1 and rng.random() < 0.03:
            regime = 0
        vol = 0.008 if regime == 0 else 0.025
        global_factor[t] = rng.normal(0, vol)

    # sector factors
    unique_sectors = institutions["sector"].unique()
    sector_factors = {
        s: rng.normal(0, 0.005, n_dates) for s in unique_sectors
    }

    # build return matrix
    returns = np.zeros((n_dates, n_inst))
    for j, row in institutions.iterrows():
        s = row["sector"]
        base_vol = vol_map.get(s, 0.015)
        beta_global = rng.uniform(0.5, 1.5)
        beta_sector = rng.uniform(0.3, 0.8)
        idio = rng.normal(0, base_vol, n_dates)
        returns[:, j] = (
            beta_global * global_factor
            + beta_sector * sector_factors[s]
            + idio
        )

    df = pd.DataFrame(returns, index=dates, columns=institutions["ticker"])
    df.index.name = "date"
    return df


def _generate_exposures(
    institutions: pd.DataFrame,
    n_quarters: int = 80,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Simulate bilateral bank → NBFI exposure data (quarterly).

    Each bank has random exposures to a subset of NBFIs. Exposures grow
    over time and increase during calm periods (procyclical leverage).
    """
    rng = np.random.default_rng(seed)
    banks = institutions.loc[institutions["sector"] == "bank", "ticker"].tolist()
    nbfis = institutions.loc[institutions["sector"] != "bank", "ticker"].tolist()

    dates = pd.date_range(SAMPLE_START, periods=n_quarters, freq="QE")
    rows = []
    for date in dates:
        for bank in banks:
            n_links = rng.integers(3, min(15, len(nbfis)))
            targets = rng.choice(nbfis, size=n_links, replace=False)
            for nbfi in targets:
                trend = 1 + 0.02 * (dates.get_loc(date))  # growing over time
                amount = rng.lognormal(mean=5, sigma=1.5) * trend
                rows.append({
                    "date": date,
                    "source": bank,
                    "target": nbfi,
                    "exposure_usd_mn": round(amount, 2),
                })
    return pd.DataFrame(rows)


def _generate_macro(
    start: str = SAMPLE_START,
    end: str = SAMPLE_END,
    seed: int = 42,
) -> pd.DataFrame:
    """Simulate macro/financial variables (VIX, Fed Funds, credit spread)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, end)
    n = len(dates)

    vix = np.cumsum(rng.normal(0, 0.3, n)) + 20
    vix = np.clip(vix, 10, 80)

    fed_funds = np.cumsum(rng.normal(0, 0.01, n)) + 3.0
    fed_funds = np.clip(fed_funds, 0.0, 8.0)

    credit_spread = np.cumsum(rng.normal(0, 0.005, n)) + 1.5
    credit_spread = np.clip(credit_spread, 0.3, 10.0)

    return pd.DataFrame({
        "vix": vix,
        "fed_funds_rate": fed_funds,
        "credit_spread_bps": credit_spread * 100,
    }, index=dates)


def _generate_nbfi_sizes(seed: int = 42) -> pd.DataFrame:
    """Country-level NBFI sector sizes (% of GDP), quarterly."""
    rng = np.random.default_rng(seed)
    countries = ["US", "GB", "DE", "FR", "JP", "CH", "CN", "CA", "AU", "BR"]
    dates = pd.date_range(SAMPLE_START, SAMPLE_END, freq="QE")
    rows = []
    for country in countries:
        base = rng.uniform(30, 200)  # NBFI assets as % of GDP
        for date in dates:
            growth = 1 + 0.005 * dates.get_loc(date)
            noise = rng.normal(0, 2)
            rows.append({
                "date": date,
                "country": country,
                "nbfi_assets_pct_gdp": round(base * growth + noise, 2),
            })
    return pd.DataFrame(rows)


def generate_synthetic_data(seed: int = 42) -> dict[str, pd.DataFrame]:
    """Generate all synthetic datasets and save to data/processed/."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    institutions = _generate_institution_metadata(seed=seed)
    returns = _generate_returns(institutions, seed=seed)
    exposures = _generate_exposures(institutions, seed=seed)
    macro = _generate_macro(seed=seed)
    nbfi_sizes = _generate_nbfi_sizes(seed=seed)

    institutions.to_csv(PROCESSED_DIR / "institutions.csv", index=False)
    returns.to_csv(PROCESSED_DIR / "returns.csv")
    exposures.to_csv(PROCESSED_DIR / "exposures.csv", index=False)
    macro.to_csv(PROCESSED_DIR / "macro.csv")
    nbfi_sizes.to_csv(PROCESSED_DIR / "nbfi_sizes.csv", index=False)

    return {
        "institutions": institutions,
        "returns": returns,
        "exposures": exposures,
        "macro": macro,
        "nbfi_sizes": nbfi_sizes,
    }


# ── Real data loading ────────────────────────────────────────────────────

def load_processed_data() -> dict[str, pd.DataFrame]:
    """Load cleaned datasets from data/processed/."""
    data = {}

    inst_path = PROCESSED_DIR / "institutions.csv"
    if inst_path.exists():
        data["institutions"] = pd.read_csv(inst_path)

    ret_path = PROCESSED_DIR / "returns.csv"
    if ret_path.exists():
        data["returns"] = pd.read_csv(ret_path, index_col=0, parse_dates=True)

    exp_path = PROCESSED_DIR / "exposures.csv"
    if exp_path.exists():
        data["exposures"] = pd.read_csv(exp_path, parse_dates=["date"])

    macro_path = PROCESSED_DIR / "macro.csv"
    if macro_path.exists():
        data["macro"] = pd.read_csv(macro_path, index_col=0, parse_dates=True)

    nbfi_path = PROCESSED_DIR / "nbfi_sizes.csv"
    if nbfi_path.exists():
        data["nbfi_sizes"] = pd.read_csv(nbfi_path, parse_dates=["date"])

    return data


# ── Entry point ───────────────────────────────────────────────────────────

def main():
    """Build dataset: load raw data if available, otherwise generate synthetic."""
    raw_files = list(RAW_DIR.glob("*"))
    if raw_files:
        print(f"Found {len(raw_files)} raw files — loading real data pipeline.")
        # TODO: implement real data cleaning when files are available
        data = load_processed_data()
    else:
        print("No raw data found — generating synthetic dataset for development.")
        data = generate_synthetic_data()

    for name, df in data.items():
        print(f"  {name}: {df.shape}")
    print("Dataset build complete.")


if __name__ == "__main__":
    main()
