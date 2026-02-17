"""
Systemic risk measures: CoVaR, MES, SRISK, and Diebold-Yilmaz connectedness.

Implements the core econometric tools for measuring tail-risk spillovers and
time-varying connectedness between banks and non-bank financial intermediaries.

References
----------
- Adrian & Brunnermeier (2016), "CoVaR", AER.
- Acharya, Pedersen, Philippon & Richardson (2017), "Measuring Systemic Risk", RFS.
- Brownlees & Engle (2017), "SRISK", RFS.
- Diebold & Yilmaz (2012, 2014), connectedness indices.
- Billio, Getmansky, Lo & Pelizzon (2012), Granger-causality networks.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
import statsmodels.api as sm
from statsmodels.tsa.api import VAR
from typing import Optional

from src.utils.config import (
    COVAR_QUANTILE,
    MES_THRESHOLD_QUANTILE,
    SRISK_PRUDENTIAL_RATIO,
    SRISK_MARKET_DECLINE,
    VAR_LAGS,
    ROLLING_WINDOW,
    FORECAST_HORIZON,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. CoVaR  (Adrian & Brunnermeier 2016)
# ═══════════════════════════════════════════════════════════════════════════

def estimate_covar(
    returns: pd.DataFrame,
    system_col: str,
    institution_col: str,
    state_vars: Optional[pd.DataFrame] = None,
    q: float = COVAR_QUANTILE,
) -> dict:
    """
    Estimate CoVaR via quantile regression.

    CoVaR_q^{sys|i} = VaR of the system conditional on institution i
    being at its VaR.

    ΔCoVaR = CoVaR_q^{sys|i=VaR} - CoVaR_q^{sys|i=median}

    Parameters
    ----------
    returns : DataFrame containing at least system_col and institution_col.
    system_col : Column name for system returns (e.g., market index).
    institution_col : Column name for the institution's returns.
    state_vars : Optional state variables (VIX, spread, etc.) to include.
    q : Quantile for the VaR (default 0.05).

    Returns
    -------
    dict with keys: covar, delta_covar, var_i, coefficients.
    """
    y = returns[system_col].values
    x_i = returns[institution_col].values

    if state_vars is not None:
        state = state_vars.reindex(returns.index).dropna()
        common = returns.index.intersection(state.index)
        y = returns.loc[common, system_col].values
        x_i = returns.loc[common, institution_col].values
        X = np.column_stack([x_i, state.loc[common].values])
    else:
        X = x_i.reshape(-1, 1)

    X = sm.add_constant(X)

    # Quantile regression at q
    model_q = sm.QuantReg(y, X)
    res_q = model_q.fit(q=q, max_iter=1000)

    # VaR of institution i (unconditional quantile)
    var_i = np.quantile(x_i, q)
    median_i = np.median(x_i)

    # CoVaR: predicted system quantile when institution is at its VaR
    if state_vars is not None:
        state_means = state.loc[common].mean().values
        x_at_var = np.array([1, var_i] + state_means.tolist())
        x_at_median = np.array([1, median_i] + state_means.tolist())
    else:
        x_at_var = np.array([1, var_i])
        x_at_median = np.array([1, median_i])

    covar = res_q.params @ x_at_var
    covar_median = res_q.params @ x_at_median
    delta_covar = covar - covar_median

    return {
        "covar": covar,
        "delta_covar": delta_covar,
        "var_i": var_i,
        "coefficients": res_q.params,
        "pvalues": res_q.pvalues,
    }


def compute_covar_panel(
    returns: pd.DataFrame,
    institutions: pd.DataFrame,
    system_col: str = "MARKET",
    state_vars: Optional[pd.DataFrame] = None,
    q: float = COVAR_QUANTILE,
) -> pd.DataFrame:
    """
    Compute CoVaR and ΔCoVaR for all institutions in the panel.

    Parameters
    ----------
    returns : DataFrame of daily returns (columns = tickers + system_col).
    institutions : DataFrame with 'ticker' and 'sector' columns.
    system_col : Name of the system/market return column.

    Returns
    -------
    DataFrame with columns: ticker, sector, covar, delta_covar, var_i.
    """
    # Create market return if not present
    inst_cols = [c for c in returns.columns if c != system_col]
    if system_col not in returns.columns:
        returns = returns.copy()
        returns[system_col] = returns[inst_cols].mean(axis=1)

    records = []
    for _, row in institutions.iterrows():
        ticker = row["ticker"]
        if ticker not in returns.columns:
            continue
        result = estimate_covar(
            returns[[system_col, ticker]].dropna(),
            system_col=system_col,
            institution_col=ticker,
            state_vars=state_vars,
            q=q,
        )
        records.append({
            "ticker": ticker,
            "sector": row["sector"],
            "covar": result["covar"],
            "delta_covar": result["delta_covar"],
            "var_i": result["var_i"],
        })
    return pd.DataFrame(records)


# ═══════════════════════════════════════════════════════════════════════════
# 2. MES — Marginal Expected Shortfall (Acharya et al. 2017)
# ═══════════════════════════════════════════════════════════════════════════

def compute_mes(
    returns: pd.DataFrame,
    institutions: pd.DataFrame,
    system_col: str = "MARKET",
    q: float = MES_THRESHOLD_QUANTILE,
) -> pd.DataFrame:
    """
    Compute MES: average return of institution i on the days when the
    market return is in the bottom q-quantile.

    MES_i = E[r_i | r_market <= VaR_q(r_market)]
    """
    inst_cols = [c for c in returns.columns if c != system_col]
    if system_col not in returns.columns:
        returns = returns.copy()
        returns[system_col] = returns[inst_cols].mean(axis=1)

    market = returns[system_col]
    threshold = market.quantile(q)
    crisis_days = market <= threshold

    records = []
    for _, row in institutions.iterrows():
        ticker = row["ticker"]
        if ticker not in returns.columns:
            continue
        mes = returns.loc[crisis_days, ticker].mean()
        records.append({
            "ticker": ticker,
            "sector": row["sector"],
            "mes": mes,
        })
    return pd.DataFrame(records)


# ═══════════════════════════════════════════════════════════════════════════
# 3. SRISK — Systemic Risk Index (Brownlees & Engle 2017)
# ═══════════════════════════════════════════════════════════════════════════

def compute_srisk(
    returns: pd.DataFrame,
    institutions: pd.DataFrame,
    market_cap: Optional[pd.Series] = None,
    debt: Optional[pd.Series] = None,
    system_col: str = "MARKET",
    k: float = SRISK_PRUDENTIAL_RATIO,
    market_decline: float = SRISK_MARKET_DECLINE,
    q: float = MES_THRESHOLD_QUANTILE,
) -> pd.DataFrame:
    """
    Compute SRISK = k * D_i - (1-k) * W_i * (1 - LRMES_i)

    where LRMES ≈ 1 - exp(log(1 + MES) * h) approximation for the
    long-run MES under a prolonged market decline.

    When market_cap and debt are not available, we use unit values
    and SRISK becomes a normalized measure.
    """
    mes_df = compute_mes(returns, institutions, system_col=system_col, q=q)

    records = []
    for _, row in mes_df.iterrows():
        ticker = row["ticker"]
        mes_val = row["mes"]

        # Approximate LRMES from daily MES
        # Under Brownlees & Engle: LRMES ≈ 1 - exp(log(1-d) * beta)
        # Simplified: use 1 - exp(h * log(1 + MES)) with h=126 (6 months)
        h = 126
        if mes_val < 0:
            lrmes = 1 - np.exp(h * np.log(1 + mes_val))
        else:
            lrmes = 0

        w_i = market_cap[ticker] if market_cap is not None else 1.0
        d_i = debt[ticker] if debt is not None else 1.0

        srisk = k * d_i - (1 - k) * w_i * (1 - lrmes)

        records.append({
            "ticker": ticker,
            "sector": row["sector"],
            "mes": mes_val,
            "lrmes": lrmes,
            "srisk": srisk,
        })
    return pd.DataFrame(records)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Diebold-Yilmaz Connectedness (2012, 2014)
# ═══════════════════════════════════════════════════════════════════════════

def _generalized_fevd(
    var_result,
    h: int = FORECAST_HORIZON,
) -> np.ndarray:
    """
    Compute generalized forecast-error variance decomposition (Pesaran &
    Shin 1998) from a fitted VAR model.

    Unlike Cholesky-based FEVD, the generalized version is invariant to
    variable ordering.

    Returns
    -------
    theta : (n x n) array where theta[i, j] = share of i's h-step
            forecast-error variance due to shocks to j.
            Rows are normalized to sum to 1.
    """
    n = var_result.neqs
    sigma = var_result.sigma_u  # residual covariance matrix
    sigma_diag = np.diag(sigma)

    # MA coefficient matrices (impulse responses)
    ma_coefs = var_result.ma_rep(maxn=h)  # shape (h+1, n, n)

    theta = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            # Numerator: sum of squared responses of i to shock j
            num = 0
            for s in range(h + 1):
                e_j = np.zeros(n)
                e_j[j] = 1
                response = ma_coefs[s] @ sigma @ e_j
                num += response[i] ** 2
            num /= sigma_diag[j]

            # Denominator: total FEV of variable i
            denom = 0
            for s in range(h + 1):
                contrib = ma_coefs[s] @ sigma @ ma_coefs[s].T
                denom += contrib[i, i]

            theta[i, j] = num / denom if denom > 0 else 0

    # Normalize rows to sum to 1
    row_sums = theta.sum(axis=1, keepdims=True)
    theta = theta / np.where(row_sums > 0, row_sums, 1)

    return theta


def compute_connectedness(
    returns: pd.DataFrame,
    lags: int = VAR_LAGS,
    h: int = FORECAST_HORIZON,
) -> dict:
    """
    Compute the Diebold-Yilmaz (2012, 2014) connectedness table.

    Parameters
    ----------
    returns : DataFrame of (possibly weekly/monthly) returns for N entities.
    lags : VAR lag order.
    h : Forecast horizon for FEVD.

    Returns
    -------
    dict with keys:
      - theta: (N x N) normalized GFEVD matrix
      - total_connectedness: scalar (0-100 scale)
      - to_others: series of directional TO connectedness
      - from_others: series of directional FROM connectedness
      - net: series of net directional connectedness (TO - FROM)
      - names: list of variable names
    """
    returns = returns.dropna()
    names = returns.columns.tolist()
    n = len(names)

    model = VAR(returns)
    result = model.fit(maxlags=lags, ic=None)

    theta = _generalized_fevd(result, h=h)

    # Off-diagonal shares
    to_others = np.zeros(n)
    from_others = np.zeros(n)
    for i in range(n):
        for j in range(n):
            if i != j:
                to_others[j] += theta[i, j]    # j's shock → others
                from_others[i] += theta[i, j]   # i receives from others

    total = from_others.sum() / n * 100  # average pairwise spillover (%)

    return {
        "theta": pd.DataFrame(theta, index=names, columns=names),
        "total_connectedness": total,
        "to_others": pd.Series(to_others * 100, index=names),
        "from_others": pd.Series(from_others * 100, index=names),
        "net": pd.Series((to_others - from_others) * 100, index=names),
        "names": names,
    }


def rolling_connectedness(
    returns: pd.DataFrame,
    window: int = ROLLING_WINDOW,
    lags: int = VAR_LAGS,
    h: int = FORECAST_HORIZON,
    step: int = 1,
) -> pd.DataFrame:
    """
    Compute rolling-window total connectedness index over time.

    Returns DataFrame with columns: date, total_connectedness.
    """
    dates = returns.index
    records = []

    for end in range(window, len(dates), step):
        start = end - window
        window_returns = returns.iloc[start:end]
        try:
            result = compute_connectedness(window_returns, lags=lags, h=h)
            records.append({
                "date": dates[end - 1],
                "total_connectedness": result["total_connectedness"],
            })
        except Exception:
            continue

    return pd.DataFrame(records).set_index("date")


# ═══════════════════════════════════════════════════════════════════════════
# 5. Granger-Causality Network (Billio et al. 2012)
# ═══════════════════════════════════════════════════════════════════════════

def granger_causality_network(
    returns: pd.DataFrame,
    lags: int = 4,
    significance: float = 0.05,
) -> pd.DataFrame:
    """
    Build a Granger-causality network following Billio et al. (2012).

    For each pair (i, j), test whether j Granger-causes i at the given
    significance level. Returns an adjacency matrix (1 = significant link).
    """
    names = returns.columns.tolist()
    n = len(names)
    adj = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            y = returns.iloc[:, i]
            x = returns.iloc[:, j]
            data = pd.concat([y, x], axis=1).dropna()
            if len(data) < lags + 10:
                continue
            try:
                result = sm.tsa.stattools.grangercausalitytests(
                    data.values, maxlag=lags, verbose=False,
                )
                # Use F-test p-value at the specified lag
                p_value = result[lags][0]["ssr_ftest"][1]
                if p_value < significance:
                    adj[j, i] = 1  # j → i
            except Exception:
                continue

    return pd.DataFrame(adj, index=names, columns=names)


# ═══════════════════════════════════════════════════════════════════════════
# 6. Sector-level aggregation
# ═══════════════════════════════════════════════════════════════════════════

def aggregate_connectedness_by_sector(
    theta: pd.DataFrame,
    institutions: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregate the pairwise GFEVD matrix to sector-level connectedness.

    Returns a sector × sector matrix showing average spillovers
    between institution types (bank → hedge fund, etc.).
    """
    ticker_to_sector = dict(
        zip(institutions["ticker"], institutions["sector"])
    )
    available = [c for c in theta.columns if c in ticker_to_sector]
    theta_sub = theta.loc[available, available]

    sectors = sorted(set(ticker_to_sector[t] for t in available))
    result = pd.DataFrame(0.0, index=sectors, columns=sectors)
    counts = pd.DataFrame(0, index=sectors, columns=sectors)

    for i in available:
        for j in available:
            if i == j:
                continue
            si = ticker_to_sector[i]
            sj = ticker_to_sector[j]
            result.loc[si, sj] += theta_sub.loc[i, j]
            counts.loc[si, sj] += 1

    # Average
    counts = counts.replace(0, np.nan)
    result = result / counts
    return result.fillna(0)
