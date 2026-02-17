"""
Real data ingestion scripts for publicly available sources.

Handles downloading and processing data from:
  1. FRED (Federal Reserve Economic Data) — VIX, policy rates, spreads
  2. BIS Statistics — cross-border banking, NBFI sector sizes
  3. ECB Statistical Data Warehouse — euro area exposures
  4. Yahoo Finance / public equity data — institution-level returns

Each loader returns a clean DataFrame ready for the analysis pipeline.
When the data source requires API keys or manual downloads, the functions
provide clear instructions and fall back to sample data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional
import urllib.request
import io
import json

from src.utils.config import RAW_DIR, PROCESSED_DIR, EXTERNAL_DIR


# ═══════════════════════════════════════════════════════════════════════════
# 1. FRED Data (public, no API key needed for CSV downloads)
# ═══════════════════════════════════════════════════════════════════════════

FRED_SERIES = {
    "VIXCLS": "vix",                    # CBOE VIX
    "DFF": "fed_funds_rate",            # Fed Funds effective rate
    "BAMLH0A0HYM2": "hy_spread",       # ICE BofA US High Yield spread
    "BAMLC0A4CBBB": "bbb_spread",      # ICE BofA BBB Corporate spread
    "T10Y2Y": "term_spread_10y2y",     # 10Y-2Y Treasury spread
    "DTWEXBGS": "usd_broad_index",     # Trade-weighted USD index
    "TEDRATE": "ted_spread",           # TED spread (3m LIBOR - 3m T-bill)
}


def fetch_fred_series(
    series_id: str,
    start: str = "2000-01-01",
    end: str = "2025-12-31",
) -> Optional[pd.Series]:
    """
    Fetch a single FRED series via the public CSV endpoint.

    No API key required — uses the direct CSV download URL.
    """
    url = (
        f"https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={series_id}&cosd={start}&coed={end}"
    )
    try:
        response = urllib.request.urlopen(url, timeout=30)
        data = pd.read_csv(
            io.BytesIO(response.read()),
            parse_dates=["DATE"],
            index_col="DATE",
            na_values=".",
        )
        series = data.iloc[:, 0]
        series.name = series_id
        return series
    except Exception as e:
        print(f"  Warning: Could not fetch FRED/{series_id}: {e}")
        return None


def load_fred_macro(
    save: bool = True,
) -> pd.DataFrame:
    """
    Download all macro/financial variables from FRED.

    Returns DataFrame indexed by date with columns:
      vix, fed_funds_rate, hy_spread, bbb_spread, term_spread, usd_index, ted_spread
    """
    print("Downloading macro data from FRED...")
    series_dict = {}

    for fred_id, col_name in FRED_SERIES.items():
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
        df.to_csv(EXTERNAL_DIR / "fred_macro.csv")
        print(f"  Saved to {EXTERNAL_DIR / 'fred_macro.csv'}")

    return df


# ═══════════════════════════════════════════════════════════════════════════
# 2. BIS Statistics (public CSVs)
# ═══════════════════════════════════════════════════════════════════════════

BIS_URLS = {
    # BIS Locational Banking Statistics (cross-border positions)
    "lbs": "https://stats.bis.org/api/v2/data/BIS,WS_LBS_D_PUB,1.0/all?format=csv",
    # BIS Credit to the non-financial sector
    "credit": "https://stats.bis.org/api/v2/data/BIS,WS_TC,1.0/all?format=csv",
    # BIS Effective exchange rates
    "eer": "https://stats.bis.org/api/v2/data/BIS,WS_EER,1.0/all?format=csv",
}


def load_bis_locational_banking(
    filepath: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Load BIS Locational Banking Statistics.

    If a pre-downloaded CSV is available at `filepath`, load it directly.
    Otherwise, provide instructions for manual download.

    The LBS data contains:
      - Cross-border bank claims and liabilities
      - Breakdown by counterparty sector (banks, non-banks, official)
      - Breakdown by instrument (loans, debt securities, other)
      - Quarterly, from ~2000 onward
    """
    if filepath and filepath.exists():
        print(f"Loading BIS LBS data from {filepath}...")
        df = pd.read_csv(filepath)
        return df

    # Check RAW_DIR
    raw_path = RAW_DIR / "bis_lbs.csv"
    if raw_path.exists():
        print(f"Loading BIS LBS data from {raw_path}...")
        return pd.read_csv(raw_path)

    print(
        "BIS Locational Banking Statistics not found.\n"
        "To download:\n"
        "  1. Visit https://stats.bis.org/statx/srs/table/A6.1\n"
        "  2. Select counterparty sector: 'Non-bank financial'\n"
        "  3. Download as CSV and save to data/raw/bis_lbs.csv\n"
        "  Alternatively, use the BIS SDMX API for programmatic access."
    )
    return pd.DataFrame()


def load_fsb_nbfi_sizes(
    filepath: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Load FSB Global Monitoring Report data on NBFI sector sizes.

    The FSB publishes an interactive data portal with:
      - NBFI assets by jurisdiction (29 jurisdictions)
      - Breakdown by entity type (OFIs, insurance, pension)
      - Narrow measure by economic function (EF1-EF5)
      - Quarterly/annual, from 2002 onward

    Data portal: https://www.fsb.org/work-of-the-fsb/financial-innovation-and-structural-change/non-bank-financial-intermediation/global-nbfi-monitoring-report-data/
    """
    if filepath and filepath.exists():
        return pd.read_csv(filepath, parse_dates=["date"])

    raw_path = RAW_DIR / "fsb_nbfi_sizes.csv"
    if raw_path.exists():
        return pd.read_csv(raw_path, parse_dates=["date"])

    print(
        "FSB NBFI sector size data not found.\n"
        "To download:\n"
        "  1. Visit the FSB interactive data portal (link above)\n"
        "  2. Select: Total financial assets, by jurisdiction and entity type\n"
        "  3. Export to CSV and save to data/raw/fsb_nbfi_sizes.csv"
    )
    return pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════
# 3. Institution-Level Equity Returns
# ═══════════════════════════════════════════════════════════════════════════

# Major G-SIBs and publicly listed NBFIs for return data
GSIB_TICKERS = {
    "JPM": ("JPMorgan Chase", "bank", "US"),
    "BAC": ("Bank of America", "bank", "US"),
    "C": ("Citigroup", "bank", "US"),
    "GS": ("Goldman Sachs", "bank", "US"),
    "MS": ("Morgan Stanley", "bank", "US"),
    "WFC": ("Wells Fargo", "bank", "US"),
    "HSBA.L": ("HSBC", "bank", "GB"),
    "BARC.L": ("Barclays", "bank", "GB"),
    "DBK.DE": ("Deutsche Bank", "bank", "DE"),
    "BNP.PA": ("BNP Paribas", "bank", "FR"),
    "SAN.MC": ("Santander", "bank", "ES"),
    "UBSG.SW": ("UBS", "bank", "CH"),
    "8306.T": ("MUFG", "bank", "JP"),
}

NBFI_TICKERS = {
    "BLK": ("BlackRock", "investment_fund", "US"),
    "BX": ("Blackstone", "hedge_fund", "US"),
    "KKR": ("KKR & Co", "direct_credit", "US"),
    "APO": ("Apollo Global", "direct_credit", "US"),
    "ARES": ("Ares Management", "direct_credit", "US"),
    "BN": ("Brookfield Corp", "investment_fund", "CA"),
    "IVZ": ("Invesco", "investment_fund", "US"),
    "TROW": ("T. Rowe Price", "investment_fund", "US"),
    "AMP": ("Ameriprise", "investment_fund", "US"),
    "MET": ("MetLife", "insurance", "US"),
    "PRU": ("Prudential Financial", "insurance", "US"),
    "AIG": ("AIG", "insurance", "US"),
    "ALL": ("Allstate", "insurance", "US"),
    "SCHW": ("Charles Schwab", "broker_dealer", "US"),
    "RJF": ("Raymond James", "broker_dealer", "US"),
}


def load_equity_returns(
    filepath: Optional[Path] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load daily equity returns for banks and NBFIs.

    If pre-downloaded data exists, load it. Otherwise provide instructions
    for downloading from Yahoo Finance or Bloomberg.

    Returns
    -------
    (returns_df, institutions_df) : tuple of DataFrames
    """
    raw_path = filepath or RAW_DIR / "equity_returns.csv"
    inst_path = RAW_DIR / "institution_metadata.csv"

    if raw_path.exists():
        returns = pd.read_csv(raw_path, index_col=0, parse_dates=True)
        institutions = pd.read_csv(inst_path) if inst_path.exists() else _build_institution_metadata()
        return returns, institutions

    print(
        "Equity return data not found.\n"
        "To download from Yahoo Finance (free):\n"
        "  pip install yfinance\n"
        "  Then use the helper function: download_yahoo_returns()\n\n"
        "For Bloomberg/Datastream access, export daily adjusted close\n"
        "prices for the tickers listed in GSIB_TICKERS and NBFI_TICKERS."
    )
    return pd.DataFrame(), _build_institution_metadata()


def _build_institution_metadata() -> pd.DataFrame:
    """Build institution metadata from the ticker dictionaries."""
    rows = []
    for ticker, (name, sector, country) in {**GSIB_TICKERS, **NBFI_TICKERS}.items():
        rows.append({
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "country": country,
        })
    return pd.DataFrame(rows)


def download_yahoo_returns(
    tickers: Optional[list[str]] = None,
    start: str = "2005-01-01",
    end: str = "2025-12-31",
    save: bool = True,
) -> pd.DataFrame:
    """
    Download daily adjusted close prices from Yahoo Finance and compute returns.

    Requires: pip install yfinance

    Parameters
    ----------
    tickers : List of tickers. If None, uses GSIB_TICKERS + NBFI_TICKERS.
    start, end : Date range.
    save : Whether to save to data/raw/.

    Returns
    -------
    DataFrame of daily log-returns.
    """
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed. Run: pip install yfinance")
        return pd.DataFrame()

    if tickers is None:
        tickers = list(GSIB_TICKERS.keys()) + list(NBFI_TICKERS.keys())

    print(f"Downloading returns for {len(tickers)} tickers from Yahoo Finance...")
    data = yf.download(tickers, start=start, end=end, auto_adjust=True)

    if "Close" in data.columns.get_level_values(0):
        prices = data["Close"]
    else:
        prices = data

    returns = np.log(prices / prices.shift(1)).dropna(how="all")

    if save:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        returns.to_csv(RAW_DIR / "equity_returns.csv")
        institutions = _build_institution_metadata()
        institutions.to_csv(RAW_DIR / "institution_metadata.csv", index=False)
        print(f"  Saved to {RAW_DIR}")

    return returns


# ═══════════════════════════════════════════════════════════════════════════
# 4. Master data loader
# ═══════════════════════════════════════════════════════════════════════════

def load_all_real_data() -> dict[str, pd.DataFrame]:
    """
    Attempt to load all real data sources.

    Returns dict with whatever data is available. Missing sources
    return empty DataFrames with instructions printed.
    """
    data = {}

    print("=" * 60)
    print("  Loading real data sources")
    print("=" * 60)

    # FRED macro data
    print("\n[1/4] FRED macro/financial data:")
    data["macro"] = load_fred_macro(save=True)

    # BIS data
    print("\n[2/4] BIS Locational Banking Statistics:")
    data["bis_lbs"] = load_bis_locational_banking()

    # FSB NBFI sizes
    print("\n[3/4] FSB NBFI sector sizes:")
    data["nbfi_sizes"] = load_fsb_nbfi_sizes()

    # Equity returns
    print("\n[4/4] Institution-level equity returns:")
    returns, institutions = load_equity_returns()
    data["returns"] = returns
    data["institutions"] = institutions

    available = sum(1 for v in data.values()
                    if isinstance(v, pd.DataFrame) and len(v) > 0)
    print(f"\n  {available}/{len(data)} data sources loaded successfully.")

    return data
