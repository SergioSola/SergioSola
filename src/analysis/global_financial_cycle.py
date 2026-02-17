"""
Global Financial Cycle analysis.

Implements the methodology from Miranda-Agrippino & Rey (2020) and Rey (2015)
to extract a global factor from risky asset prices and test whether non-bank
financial intermediation amplifies its transmission.

Modules:
  1. Dynamic factor extraction (PCA / Bayesian DFM) from asset returns
  2. Tests of GFC transmission: local credit/asset prices on global factor
  3. Interaction with NBFI penetration and bank-NBFI connectedness
  4. IV estimation using US monetary policy shocks
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm
from statsmodels.tsa.api import VAR
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════
# 1. Global Factor Extraction
# ═══════════════════════════════════════════════════════════════════════════

def extract_global_factor(
    returns: pd.DataFrame,
    n_components: int = 1,
    standardize: bool = True,
) -> dict:
    """
    Extract the global financial cycle factor using PCA on a panel of
    risky asset returns (Miranda-Agrippino & Rey 2020).

    Parameters
    ----------
    returns : DataFrame of returns (rows = time, columns = assets/countries).
    n_components : Number of principal components to extract.
    standardize : Whether to standardize returns before PCA.

    Returns
    -------
    dict with:
      - global_factor: DataFrame with extracted factor(s)
      - explained_variance_ratio: variance share explained
      - loadings: factor loadings for each asset
      - pca_model: fitted PCA object
    """
    clean = returns.dropna()
    if standardize:
        scaler = StandardScaler()
        data = scaler.fit_transform(clean)
    else:
        scaler = None
        data = clean.values

    pca = PCA(n_components=n_components)
    factors = pca.fit_transform(data)

    factor_df = pd.DataFrame(
        factors,
        index=clean.index,
        columns=[f"GFC_{i+1}" for i in range(n_components)],
    )

    loadings = pd.DataFrame(
        pca.components_.T,
        index=clean.columns,
        columns=[f"GFC_{i+1}" for i in range(n_components)],
    )

    return {
        "global_factor": factor_df,
        "explained_variance_ratio": pca.explained_variance_ratio_,
        "loadings": loadings,
        "pca_model": pca,
        "scaler": scaler,
    }


def rolling_global_factor(
    returns: pd.DataFrame,
    window: int = 252,
    step: int = 21,
) -> pd.DataFrame:
    """
    Compute rolling-window first principal component to track the
    time-varying global financial cycle.

    Returns DataFrame with the rolling GFC factor and its explained
    variance share over time.
    """
    records = []
    dates = returns.index

    for end in range(window, len(dates), step):
        start = end - window
        window_data = returns.iloc[start:end].dropna(axis=1, how="any")
        if window_data.shape[1] < 3:
            continue

        result = extract_global_factor(window_data, n_components=1)
        # Take the last observation of the factor as the "current" value
        records.append({
            "date": dates[end - 1],
            "gfc_factor": result["global_factor"].iloc[-1, 0],
            "explained_variance": result["explained_variance_ratio"][0],
        })

    return pd.DataFrame(records).set_index("date")


# ═══════════════════════════════════════════════════════════════════════════
# 2. GFC Transmission Regressions
# ═══════════════════════════════════════════════════════════════════════════

def gfc_transmission_regression(
    local_variable: pd.Series,
    global_factor: pd.Series,
    nbfi_penetration: pd.Series,
    controls: Optional[pd.DataFrame] = None,
    interaction: bool = True,
) -> sm.regression.linear_model.RegressionResultsWrapper:
    """
    Test whether NBFI penetration amplifies GFC transmission:

        y_{c,t} = α + β₁ GFC_t + β₂ NBFI_{c,t}
                  + β₃ (GFC_t × NBFI_{c,t}) + γ X_{c,t} + ε_{c,t}

    If β₃ > 0 (or < 0 depending on sign conventions), NBFI penetration
    amplifies the global financial cycle.

    Parameters
    ----------
    local_variable : Local credit growth or asset returns (panel, by country).
    global_factor : Global financial cycle factor.
    nbfi_penetration : NBFI assets as % of GDP (by country).
    controls : Additional controls (policy rate, trade openness, etc.).
    interaction : Whether to include the GFC × NBFI interaction term.

    Returns
    -------
    OLS regression result.
    """
    # Align all series on common index
    df = pd.DataFrame({
        "y": local_variable,
        "gfc": global_factor,
        "nbfi": nbfi_penetration,
    }).dropna()

    if interaction:
        df["gfc_x_nbfi"] = df["gfc"] * df["nbfi"]
        X = df[["gfc", "nbfi", "gfc_x_nbfi"]]
    else:
        X = df[["gfc", "nbfi"]]

    if controls is not None:
        controls_aligned = controls.reindex(df.index).dropna()
        common = df.index.intersection(controls_aligned.index)
        df = df.loc[common]
        X = X.loc[common]
        X = pd.concat([X, controls_aligned.loc[common]], axis=1)

    X = sm.add_constant(X)
    y = df["y"]

    model = sm.OLS(y, X)
    return model.fit(cov_type="HC1")


def panel_gfc_regression(
    panel: pd.DataFrame,
    y_col: str = "credit_growth",
    gfc_col: str = "gfc_factor",
    nbfi_col: str = "nbfi_assets_pct_gdp",
    country_col: str = "country",
    date_col: str = "date",
    controls: Optional[list[str]] = None,
) -> sm.regression.linear_model.RegressionResultsWrapper:
    """
    Panel regression of local outcomes on the global factor interacted
    with NBFI penetration, with country fixed effects.

        y_{c,t} = α_c + β₁ GFC_t + β₂ NBFI_{c,t}
                  + β₃ (GFC_t × NBFI_{c,t}) + γ X_{c,t} + ε_{c,t}

    Parameters
    ----------
    panel : Long-format panel DataFrame.
    """
    df = panel.copy()
    df["gfc_x_nbfi"] = df[gfc_col] * df[nbfi_col]

    # Country dummies (fixed effects)
    country_dummies = pd.get_dummies(
        df[country_col], prefix="fe", drop_first=True, dtype=float,
    )

    X_cols = [gfc_col, nbfi_col, "gfc_x_nbfi"]
    if controls:
        X_cols += controls

    X = pd.concat([df[X_cols].astype(float), country_dummies], axis=1)
    X = sm.add_constant(X)
    y = df[y_col].astype(float)

    mask = y.notna() & X.notna().all(axis=1)
    model = sm.OLS(y[mask], X[mask])
    return model.fit(cov_type="cluster", cov_kwds={"groups": df.loc[mask, country_col]})


# ═══════════════════════════════════════════════════════════════════════════
# 3. Connectedness × GFC Amplification
# ═══════════════════════════════════════════════════════════════════════════

def connectedness_amplification_test(
    panel: pd.DataFrame,
    y_col: str = "credit_growth",
    gfc_col: str = "gfc_factor",
    connect_col: str = "bank_nbfi_connectedness",
    country_col: str = "country",
    controls: Optional[list[str]] = None,
) -> sm.regression.linear_model.RegressionResultsWrapper:
    """
    Test whether bank-NBFI connectedness amplifies GFC transmission:

        y_{c,t} = α_c + β₁ GFC_t + β₂ Connect_{c,t}
                  + β₃ (GFC_t × Connect_{c,t}) + ε_{c,t}

    This directly tests whether the network structure (not just NBFI size)
    matters for global cycle amplification.
    """
    df = panel.copy()
    df["gfc_x_connect"] = df[gfc_col] * df[connect_col]

    country_dummies = pd.get_dummies(
        df[country_col], prefix="fe", drop_first=True, dtype=float,
    )

    X_cols = [gfc_col, connect_col, "gfc_x_connect"]
    if controls:
        X_cols += controls

    X = pd.concat([df[X_cols].astype(float), country_dummies], axis=1)
    X = sm.add_constant(X)
    y = df[y_col].astype(float)

    mask = y.notna() & X.notna().all(axis=1)
    model = sm.OLS(y[mask], X[mask])
    return model.fit(cov_type="cluster", cov_kwds={"groups": df.loc[mask, country_col]})


# ═══════════════════════════════════════════════════════════════════════════
# 4. IV Estimation (US Monetary Policy Shocks)
# ═══════════════════════════════════════════════════════════════════════════

def iv_gfc_regression(
    panel: pd.DataFrame,
    y_col: str = "credit_growth",
    gfc_col: str = "gfc_factor",
    nbfi_col: str = "nbfi_assets_pct_gdp",
    instrument_col: str = "us_mp_shock",
    country_col: str = "country",
) -> dict:
    """
    IV/2SLS estimation to address endogeneity of the global factor.

    First stage:  GFC_t = π₀ + π₁ USMPshock_t + v_t
    Second stage: y_{c,t} = α_c + β₁ GFC_hat_t + β₂ NBFI_{c,t}
                            + β₃ (GFC_hat_t × NBFI_{c,t}) + ε_{c,t}

    Uses US monetary policy shocks as instrument for the GFC factor
    (Miranda-Agrippino & Rey 2020; Bruno & Shin 2015).
    """
    df = panel.dropna(subset=[y_col, gfc_col, nbfi_col, instrument_col]).copy()

    # First stage
    X_1 = sm.add_constant(df[[instrument_col]])
    first_stage = sm.OLS(df[gfc_col], X_1).fit()
    df["gfc_hat"] = first_stage.fittedvalues

    # Interaction with predicted GFC
    df["gfc_hat_x_nbfi"] = df["gfc_hat"] * df[nbfi_col]

    # Second stage with country FE
    country_dummies = pd.get_dummies(df[country_col], prefix="fe", drop_first=True)
    X_2 = pd.concat([
        df[["gfc_hat", nbfi_col, "gfc_hat_x_nbfi"]],
        country_dummies,
    ], axis=1)
    X_2 = sm.add_constant(X_2)

    second_stage = sm.OLS(df[y_col], X_2).fit(cov_type="HC1")

    return {
        "first_stage": first_stage,
        "second_stage": second_stage,
        "first_stage_f_stat": first_stage.fvalue,
        "first_stage_f_pval": first_stage.f_pvalue,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 5. Synthetic Panel Construction for Testing
# ═══════════════════════════════════════════════════════════════════════════

def build_synthetic_gfc_panel(
    n_countries: int = 10,
    n_periods: int = 80,
    true_amplification: float = 0.5,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate a synthetic panel dataset for testing GFC regressions.

    The DGP embeds a true amplification effect:
        y_{c,t} = α_c + β₁ GFC_t + β₂ NBFI_{c,t}
                  + β₃ (GFC_t × NBFI_{c,t}) + ε_{c,t}

    where β₃ = true_amplification controls the NBFI amplification channel.
    """
    rng = np.random.default_rng(seed)
    countries = [f"Country_{i}" for i in range(n_countries)]
    dates = pd.date_range("2000-01-01", periods=n_periods, freq="QE")

    # Global factor (AR(1) process)
    gfc = np.zeros(n_periods)
    for t in range(1, n_periods):
        gfc[t] = 0.7 * gfc[t - 1] + rng.normal(0, 1)

    # US monetary policy shock (instrument for GFC)
    us_mp = rng.normal(0, 0.5, n_periods)
    gfc += 0.6 * us_mp  # GFC responds to US MP

    rows = []
    for c_idx, country in enumerate(countries):
        alpha_c = rng.normal(0, 0.5)  # country FE
        nbfi_base = rng.uniform(30, 150)  # baseline NBFI penetration

        for t_idx, date in enumerate(dates):
            nbfi = nbfi_base + 0.5 * t_idx + rng.normal(0, 3)
            connect = rng.uniform(0.1, 0.9) + 0.2 * nbfi / 100

            # True DGP
            credit_growth = (
                alpha_c
                + 0.8 * gfc[t_idx]           # β₁: GFC effect
                + 0.01 * nbfi                 # β₂: NBFI level
                + true_amplification * gfc[t_idx] * (nbfi / 100)  # β₃: amplification
                + rng.normal(0, 1.5)          # noise
            )

            rows.append({
                "date": date,
                "country": country,
                "credit_growth": credit_growth,
                "gfc_factor": gfc[t_idx],
                "nbfi_assets_pct_gdp": nbfi,
                "bank_nbfi_connectedness": connect,
                "us_mp_shock": us_mp[t_idx],
            })

    return pd.DataFrame(rows)
