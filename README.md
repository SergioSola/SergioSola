# Research Repository: Financial Stability, Systemic Risk, and Policy Interactions

This repository contains two research programmes:

1. **Programme I — Bank–NBFI Interlinkages and Systemic Risk:** Empirical analysis
   of how bank–non-bank interconnections create and propagate systemic risk.
2. **Programme II — Monetary-Fiscal Interactions:** Structural DSGE modelling of
   how government debt limits, central bank autonomy, and sovereign risk shape
   macroeconomic outcomes.

---

# Programme I: Bank–Non-Bank Interlinkages, Systemic Risk, and the Global Financial Cycle

## Overview

This programme analyzes how interconnections between banks and non-bank financial
intermediaries (NBFIs)—investment funds, pension funds, direct credit firms, hedge
funds, money market funds, and insurance companies—create and propagate systemic
risk. It examines three core questions:

1. **Interlinkage mapping**: What is the structure and evolution of exposures
   between banks and non-banks across asset classes and funding channels?
2. **Systemic risk amplification**: How do VaR constraints and mark-to-market
   accounting in the non-bank sector amplify fire-sale externalities and funding
   spirals?
3. **Global financial cycle**: Do non-bank intermediaries strengthen the
   co-movement of asset prices, capital flows, and credit conditions across
   countries—and through which channels?

## Literature Foundations

The project builds on several strands of the literature:

- **Leverage and VaR constraints** (Adrian & Shin 2010, 2014; Brunnermeier &
  Pedersen 2009): Procyclical leverage driven by Value-at-Risk rules amplifies
  asset-price movements and generates endogenous volatility.
- **Systemic risk measurement** (Adrian & Brunnermeier 2016 CoVaR; Acharya et al.
  2017 SRISK/MES; Brownlees & Engle 2017): Tail-risk spillover metrics that
  capture how distress in one institution affects the system.
- **Network connectedness** (Diebold & Yilmaz 2012, 2014; Demirer et al. 2018):
  Variance-decomposition-based connectedness indices that track time-varying
  directional spillovers across institutions.
- **Non-bank financial intermediation** (FSB Global Monitoring Report; Stein 2012;
  Claessens et al. 2012): Growth of shadow banking, regulatory arbitrage, and
  funding fragility outside the banking perimeter.
- **Global financial cycle** (Rey 2015; Miranda-Agrippino & Rey 2020; Bruno &
  Shin 2015): A single global factor in risky asset prices driven by US monetary
  policy and leverage of global intermediaries.

## Project Structure

```
├── data/
│   ├── raw/              # Original downloaded datasets
│   ├── processed/        # Cleaned, merged panel data
│   └── external/         # Third-party indices (VIX, GFC factor, etc.)
├── src/
│   ├── data/             # Data ingestion, cleaning, panel construction
│   ├── models/           # VaR-constraint model, GARCH/DCC estimation
│   ├── analysis/         # Systemic risk measures, connectedness, GFC
│   ├── visualization/    # Plotting and table generation
│   └── utils/            # Shared helpers (config, logging, IO)
├── notebooks/            # Exploratory analysis and narrative walkthroughs
├── docs/                 # Literature review, methodology notes
├── tests/                # Unit tests
└── output/
    ├── figures/
    ├── tables/
    └── results/
```

## Methodology

### 1. Data

| Source | Variables | Coverage |
|--------|-----------|----------|
| BIS Locational Banking Statistics | Cross-border bank claims on NBFIs | 2000–present, quarterly |
| ECB Statistical Data Warehouse | Euro-area bank-NBFI exposures | 2004–present |
| FSB Global Monitoring Report | NBFI sector sizes by jurisdiction | 2002–present |
| FRED / BIS | Policy rates, VIX, credit spreads | Daily/monthly |
| Datastream / Bloomberg | Equity returns, CDS spreads for major banks and NBFIs | Daily |
| SEC EDGAR / EFAMA | Fund-level AUM, flows, leverage | Quarterly |

### 2. Interlinkage Network

- Construct bipartite (bank ↔ NBFI) and full weighted networks from bilateral
  exposures (loans, repo, derivatives, bond holdings).
- Compute centrality measures (degree, eigenvector, betweenness) and community
  detection to identify systemically important links.

### 3. Systemic Risk Measures

- **CoVaR** (Adrian & Brunnermeier 2016): Quantile regression of system returns
  on individual institution returns.
- **MES / SRISK** (Acharya et al. 2017; Brownlees & Engle 2017): Expected
  shortfall of an institution conditional on a market crash; capital shortfall
  under stress.
- **Diebold-Yilmaz Connectedness** (2012, 2014): Generalized forecast-error
  variance decompositions from a VAR to measure total, directional, and pairwise
  spillovers.

### 4. VaR-Constraint Amplification

Following Adrian & Shin (2010, 2014) and extending to NBFIs:

- Estimate how non-bank leverage responds to changes in asset values
  (procyclicality regressions).
- Simulate a stylized model where VaR-constrained intermediaries must
  deleverage into falling markets, generating fire-sale spirals.
- Quantify the marginal amplification from adding non-banks to a bank-only
  system.

### 5. Global Financial Cycle

- Extract a global factor from a large panel of risky asset prices
  (Miranda-Agrippino & Rey 2020 approach using dynamic factor models).
- Test whether NBFI-sector size and bank-NBFI connectedness amplify the
  transmission of the global factor to local credit and asset prices.
- Instrument with US monetary policy shocks to establish causality.

## Requirements

```
python >= 3.10
numpy
pandas
scipy
statsmodels
arch           # GARCH / DCC models
networkx       # Network analysis
scikit-learn   # PCA / factor models
matplotlib
seaborn
```

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Run data pipeline
python -m src.data.build_dataset

# Compute systemic risk measures
python -m src.analysis.systemic_risk

# Run VaR amplification simulations
python -m src.models.var_amplification

# Generate all figures and tables
python -m src.visualization.generate_outputs
```

---

# Programme II: Monetary-Fiscal Interactions

## Overview

This programme investigates the joint determination of monetary and fiscal policy
and its consequences for macroeconomic stability, sovereign risk, and the financial
sector. It employs structural DSGE modelling enriched with banking frictions,
sovereign debt limits, and open-economy features.

## Projects

| Project | Title | Status |
|---------|-------|--------|
| MFI-P1 | Fiscal Dominance and the Policy Mix | In development |
| MFI-P2 | *To be defined* | Planned |
| MFI-P3 | *To be defined* | Planned |

### MFI-P1: Fiscal Dominance and the Policy Mix

A medium-scale DSGE model featuring:
- **Agents:** Households, firms (with default risk), banks, government, central bank, foreign sector
- **Key mechanism:** Government debt limit → central bank captivity → endogenous risk premia
- **Banking sector:** Lends to both government and private sector; sovereign stress transmits to corporate credit
- **Open economy:** Interest rate parity with time-varying foreign risk premium; balance of payments
- **Policy regimes:** (a) Active monetary / passive fiscal, (b) Passive monetary / active fiscal, (c) Active monetary / active fiscal

See `notebooks/00_monetary_fiscal_overview.ipynb` for the full programme overview
and `notebooks/mfi_project1_fiscal_dominance/` for the project notebook.

## Repository Structure

```
├── notebooks/
│   ├── 00_research_programme_overview.ipynb        # Programme I overview
│   ├── 00_monetary_fiscal_overview.ipynb            # Programme II overview
│   ├── project1_shadow_leverage/                    # Programme I projects
│   ├── project2_mp_transmission/
│   ├── project3_cross_border/
│   ├── project4_fx_hedging/
│   └── mfi_project1_fiscal_dominance/               # Programme II projects
├── src/
│   ├── analysis/                                    # Analysis modules (both programmes)
│   ├── data/                                        # Data loaders (both programmes)
│   ├── models/                                      # Model implementations
│   ├── visualization/                               # Plotting
│   └── utils/                                       # Shared config and helpers
├── docs/                                            # Literature reviews, stylized facts
├── tests/                                           # Unit tests
├── data/                                            # Raw, processed, external data
└── output/                                          # Figures, tables, results
```

## License

MIT
