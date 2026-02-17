"""
Project configuration: paths, parameters, and shared constants.
"""

from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXTERNAL_DIR = DATA_DIR / "external"
OUTPUT_DIR = PROJECT_ROOT / "output"
FIGURES_DIR = OUTPUT_DIR / "figures"
TABLES_DIR = OUTPUT_DIR / "tables"
RESULTS_DIR = OUTPUT_DIR / "results"

# ── Sample period ──────────────────────────────────────────────────────────
SAMPLE_START = "2000-01-01"
SAMPLE_END = "2024-12-31"

# ── Systemic risk parameters ──────────────────────────────────────────────
COVAR_QUANTILE = 0.05          # 5 % left tail
MES_THRESHOLD_QUANTILE = 0.05  # bottom 5 % market days
SRISK_PRUDENTIAL_RATIO = 0.08  # 8 % capital ratio
SRISK_MARKET_DECLINE = -0.40   # 40 % six-month market decline

# ── VAR model parameters ──────────────────────────────────────────────────
VAR_LAGS = 4                   # quarterly lag order
ROLLING_WINDOW = 60            # 60-period rolling window for connectedness
FORECAST_HORIZON = 10          # h-step-ahead FEVD

# ── VaR constraint model ──────────────────────────────────────────────────
VAR_CONFIDENCE = 0.99          # 99 % VaR
GARCH_P = 1
GARCH_Q = 1

# ── Institution classification ────────────────────────────────────────────
SECTOR_LABELS = {
    "bank": "Banks",
    "investment_fund": "Investment Funds",
    "hedge_fund": "Hedge Funds",
    "pension_fund": "Pension Funds",
    "insurance": "Insurance Companies",
    "mmf": "Money Market Funds",
    "direct_credit": "Direct Credit / Private Debt",
    "broker_dealer": "Broker-Dealers",
}

BANK_SECTORS = {"bank"}
NBFI_SECTORS = set(SECTOR_LABELS.keys()) - BANK_SECTORS
