"""
DCC-GARCH: Dynamic Conditional Correlations.

Estimates time-varying correlations between banks and NBFIs using the
Engle (2002) DCC model, built on top of univariate GARCH(1,1) volatilities.

This is the workhorse model for measuring how co-movement between banks
and non-banks changes over time — particularly whether correlations spike
during crises (contagion) and whether they have trended up as NBFI
interlinkages grew.

References
----------
- Engle, R. (2002). Dynamic conditional correlation. JBES, 20(3), 339–350.
- Engle & Sheppard (2001). Theoretical and empirical properties of DCC.
- Brownlees & Engle (2017). SRISK (uses DCC for LRMES estimation).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from arch import arch_model
from scipy.optimize import minimize
from typing import Optional

from src.utils.config import GARCH_P, GARCH_Q


# ═══════════════════════════════════════════════════════════════════════════
# 1. Univariate GARCH estimation
# ═══════════════════════════════════════════════════════════════════════════

def fit_univariate_garch(
    returns: pd.Series,
    p: int = GARCH_P,
    q: int = GARCH_Q,
    dist: str = "normal",
) -> dict:
    """
    Fit a univariate GARCH(p,q) model to a return series.

    Returns
    -------
    dict with:
      - model: fitted arch model
      - conditional_vol: Series of conditional volatilities
      - std_resid: standardized residuals (r_t / sigma_t)
      - params: estimated parameters
    """
    r = returns.dropna() * 100  # arch package works better in % scale

    am = arch_model(r, vol="Garch", p=p, q=q, dist=dist, mean="Constant")
    res = am.fit(disp="off", show_warning=False)

    cond_vol = res.conditional_volatility / 100  # back to decimal
    std_resid = res.resid / res.conditional_volatility  # standardized

    return {
        "model": res,
        "conditional_vol": cond_vol,
        "std_resid": std_resid,
        "params": res.params,
    }


def fit_all_garch(
    returns: pd.DataFrame,
    p: int = GARCH_P,
    q: int = GARCH_Q,
) -> dict:
    """
    Fit univariate GARCH models for all columns in a return DataFrame.

    Returns
    -------
    dict with:
      - conditional_vols: DataFrame of conditional volatilities
      - std_resids: DataFrame of standardized residuals
      - models: dict of fitted models keyed by column name
    """
    vols = {}
    resids = {}
    models = {}

    for col in returns.columns:
        r = returns[col].dropna()
        if len(r) < 50:
            continue
        try:
            result = fit_univariate_garch(r, p=p, q=q)
            vols[col] = result["conditional_vol"]
            resids[col] = result["std_resid"]
            models[col] = result["model"]
        except Exception:
            continue

    return {
        "conditional_vols": pd.DataFrame(vols),
        "std_resids": pd.DataFrame(resids),
        "models": models,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 2. DCC estimation (Engle 2002)
# ═══════════════════════════════════════════════════════════════════════════

def _dcc_loglikelihood(
    params: np.ndarray,
    std_resids: np.ndarray,
    Qbar: np.ndarray,
) -> float:
    """
    Negative log-likelihood for the DCC(1,1) model.

    Q_t = (1 - a - b) * Qbar + a * (e_{t-1} e_{t-1}') + b * Q_{t-1}
    R_t = diag(Q_t)^{-1/2} Q_t diag(Q_t)^{-1/2}

    Parameters
    ----------
    params : [a, b] with a > 0, b > 0, a + b < 1.
    std_resids : (T x N) array of standardized residuals.
    Qbar : (N x N) unconditional correlation matrix of std_resids.
    """
    a, b = params
    T, N = std_resids.shape

    if a < 0 or b < 0 or a + b >= 1:
        return 1e10

    Qt = Qbar.copy()
    loglik = 0.0

    for t in range(T):
        et = std_resids[t].reshape(-1, 1)

        # Update Q_t
        Qt = (1 - a - b) * Qbar + a * (et @ et.T) + b * Qt

        # Compute R_t from Q_t
        diag_inv_sqrt = np.diag(1.0 / np.sqrt(np.maximum(np.diag(Qt), 1e-10)))
        Rt = diag_inv_sqrt @ Qt @ diag_inv_sqrt

        # Ensure Rt is valid
        np.fill_diagonal(Rt, 1.0)

        # Log-likelihood contribution
        try:
            sign, logdet = np.linalg.slogdet(Rt)
            if sign <= 0:
                return 1e10
            Rt_inv = np.linalg.inv(Rt)
            loglik += -0.5 * (logdet + et.T @ Rt_inv @ et - et.T @ et).item()
        except np.linalg.LinAlgError:
            return 1e10

    return -loglik  # negative for minimization


def estimate_dcc(
    std_resids: pd.DataFrame,
    a0: float = 0.05,
    b0: float = 0.90,
) -> dict:
    """
    Estimate DCC(1,1) parameters and compute time-varying correlations.

    Parameters
    ----------
    std_resids : DataFrame of standardized residuals from GARCH step.
    a0, b0 : Initial values for DCC parameters.

    Returns
    -------
    dict with:
      - a, b: DCC parameters
      - dynamic_correlations: dict of pairwise correlation Series
      - Q_series: list of Q_t matrices over time
      - R_series: list of R_t matrices over time
    """
    clean = std_resids.dropna()
    data = clean.values
    T, N = data.shape
    names = clean.columns.tolist()

    # Unconditional correlation
    Qbar = np.corrcoef(data.T)

    # Optimize
    result = minimize(
        _dcc_loglikelihood,
        x0=[a0, b0],
        args=(data, Qbar),
        method="Nelder-Mead",
        options={"maxiter": 5000, "xatol": 1e-6, "fatol": 1e-6},
    )
    a, b = result.x

    # Compute full path of R_t
    Qt = Qbar.copy()
    R_series = []
    Q_series = []

    for t in range(T):
        et = data[t].reshape(-1, 1)
        Qt = (1 - a - b) * Qbar + a * (et @ et.T) + b * Qt
        diag_inv_sqrt = np.diag(1.0 / np.sqrt(np.maximum(np.diag(Qt), 1e-10)))
        Rt = diag_inv_sqrt @ Qt @ diag_inv_sqrt
        np.fill_diagonal(Rt, 1.0)
        R_series.append(Rt.copy())
        Q_series.append(Qt.copy())

    # Extract pairwise correlations as time series
    dynamic_corrs = {}
    for i in range(N):
        for j in range(i + 1, N):
            pair = f"{names[i]}__{names[j]}"
            corr_path = [R_series[t][i, j] for t in range(T)]
            dynamic_corrs[pair] = pd.Series(
                corr_path, index=clean.index, name=pair,
            )

    return {
        "a": a,
        "b": b,
        "persistence": a + b,
        "dynamic_correlations": dynamic_corrs,
        "R_series": R_series,
        "Q_series": Q_series,
        "names": names,
        "dates": clean.index,
        "loglik": -result.fun,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 3. Sector-level dynamic correlations
# ═══════════════════════════════════════════════════════════════════════════

def sector_average_correlation(
    dcc_result: dict,
    institutions: pd.DataFrame,
    sector_from: str = "bank",
    sector_to: str = "hedge_fund",
) -> pd.Series:
    """
    Compute the average DCC-based dynamic correlation between two sectors.

    For example, the average pairwise correlation between all banks and
    all hedge funds at each point in time.
    """
    ticker_to_sector = dict(zip(institutions["ticker"], institutions["sector"]))
    names = dcc_result["names"]

    relevant_pairs = []
    for pair_key, corr_series in dcc_result["dynamic_correlations"].items():
        name_i, name_j = pair_key.split("__")
        si = ticker_to_sector.get(name_i)
        sj = ticker_to_sector.get(name_j)
        if (si == sector_from and sj == sector_to) or \
           (si == sector_to and sj == sector_from):
            relevant_pairs.append(corr_series)

    if not relevant_pairs:
        return pd.Series(dtype=float)

    return pd.concat(relevant_pairs, axis=1).mean(axis=1)


def all_sector_pair_correlations(
    dcc_result: dict,
    institutions: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute average dynamic correlations for all sector pairs.

    Returns a DataFrame with columns = sector pairs, index = dates.
    """
    ticker_to_sector = dict(zip(institutions["ticker"], institutions["sector"]))
    sectors = sorted(set(ticker_to_sector.get(n) for n in dcc_result["names"]
                         if n in ticker_to_sector))

    result = {}
    for i, s1 in enumerate(sectors):
        for s2 in sectors[i:]:
            avg = sector_average_correlation(dcc_result, institutions, s1, s2)
            if len(avg) > 0:
                result[f"{s1}__{s2}"] = avg

    return pd.DataFrame(result)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Contagion test: correlation breakdown
# ═══════════════════════════════════════════════════════════════════════════

def correlation_breakdown_test(
    dynamic_corr: pd.Series,
    crisis_indicator: pd.Series,
    threshold: float = 0.0,
) -> dict:
    """
    Test whether correlations increase during crisis periods
    (Forbes & Rigobon 2002 style, but using DCC instead of raw).

    Parameters
    ----------
    dynamic_corr : DCC-based pairwise correlation over time.
    crisis_indicator : Indicator variable (1 = crisis, 0 = calm), or
                       continuous variable (e.g., VIX).
    threshold : If crisis_indicator is continuous, define crisis as > threshold.

    Returns
    -------
    dict with mean correlations in calm/crisis, difference, and t-test.
    """
    common = dynamic_corr.index.intersection(crisis_indicator.index)
    corr = dynamic_corr.loc[common]
    indicator = crisis_indicator.loc[common]

    if indicator.dtype == float:
        crisis = indicator > threshold
    else:
        crisis = indicator.astype(bool)

    calm_corr = corr[~crisis]
    crisis_corr = corr[crisis]

    from scipy import stats
    if len(calm_corr) > 5 and len(crisis_corr) > 5:
        t_stat, p_value = stats.ttest_ind(crisis_corr, calm_corr)
    else:
        t_stat, p_value = np.nan, np.nan

    return {
        "mean_calm": calm_corr.mean(),
        "mean_crisis": crisis_corr.mean(),
        "difference": crisis_corr.mean() - calm_corr.mean(),
        "t_stat": t_stat,
        "p_value": p_value,
        "n_calm": len(calm_corr),
        "n_crisis": len(crisis_corr),
    }
