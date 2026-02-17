"""
Quantile Vector Autoregression (QVAR) and tail-risk econometrics.

Implements:
  1. Quantile VAR (Cecchetti & Li 2008, Montes-Rojas 2019)
     — VAR at different quantiles to capture asymmetric/tail dynamics
  2. Quantile Impulse Response Functions (QIRFs)
     — How shocks propagate through the tails of the distribution
  3. Quantile Connectedness (Ando, Greenwood-Nimmo, Shin 2022)
     — Diebold-Yilmaz connectedness computed at tail quantiles
  4. Growth-at-Risk (GaR) regressions (Adrian et al. 2019, IMF GFSR)
     — Quantile regressions of future growth on financial conditions

References
----------
- Cecchetti, S. & Li, H. (2008). Measuring the impact of asset price booms
  using quantile vector autoregressions. Unpublished.
- Montes-Rojas, G. (2019). Multivariate quantile impulse response functions.
  JBES.
- Ando, T., Greenwood-Nimmo, M. & Shin, Y. (2022). Quantile connectedness.
  JBES, 40(4).
- Adrian, T., Boyarchenko, N. & Giannone, D. (2019). Vulnerable growth. AER.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════
# 1. Quantile VAR estimation
# ═══════════════════════════════════════════════════════════════════════════

def _build_var_matrices(data: np.ndarray, lags: int):
    """Build Y and X matrices for a VAR(p) in matrix form."""
    T, k = data.shape
    Y = data[lags:]  # (T-p) x k
    X_parts = []
    for lag in range(1, lags + 1):
        X_parts.append(data[lags - lag: T - lag])
    X = np.hstack(X_parts)  # (T-p) x (k*p)
    X = np.column_stack([np.ones(T - lags), X])  # add intercept
    return Y, X


def estimate_quantile_var(
    data: pd.DataFrame,
    lags: int = 4,
    tau: float = 0.05,
    max_iter: int = 2000,
) -> dict:
    """
    Estimate a Quantile VAR(p) at quantile tau.

    For each equation i in the system:
        Q_{tau}(y_{i,t} | Y_{t-1}, ..., Y_{t-p}) = c_i + sum_j sum_l B_{ij}^l y_{j,t-l}

    Parameters
    ----------
    data : DataFrame of endogenous variables (T x k).
    lags : Number of lags.
    tau : Quantile level (e.g. 0.05 for left tail, 0.95 for right tail).
    max_iter : Maximum iterations for quantile regression solver.

    Returns
    -------
    dict with:
      - coefficients: (k x (1 + k*p)) matrix of quantile regression coefficients
      - companion: companion-form matrix for IRF computation
      - residuals: DataFrame of quantile regression residuals
      - tau: the quantile used
      - names: variable names
      - lags: lag order
    """
    arr = data.values
    T, k = arr.shape
    names = data.columns.tolist()

    Y, X = _build_var_matrices(arr, lags)
    n_obs = Y.shape[0]

    # Estimate each equation by quantile regression
    B = np.zeros((k, X.shape[1]))  # coefficient matrix
    residuals = np.zeros((n_obs, k))

    for i in range(k):
        model = sm.QuantReg(Y[:, i], X)
        res = model.fit(q=tau, max_iter=max_iter)
        B[i, :] = res.params
        residuals[:, i] = Y[:, i] - X @ res.params

    # Build companion matrix for IRFs
    # B has shape (k, 1 + k*p): first column is intercept
    B_no_intercept = B[:, 1:]  # (k, k*p)
    companion = np.zeros((k * lags, k * lags))
    companion[:k, :] = B_no_intercept
    if lags > 1:
        companion[k:, :k * (lags - 1)] = np.eye(k * (lags - 1))

    resid_df = pd.DataFrame(
        residuals, index=data.index[lags:], columns=names,
    )

    return {
        "coefficients": B,
        "companion": companion,
        "residuals": resid_df,
        "tau": tau,
        "names": names,
        "lags": lags,
        "n_vars": k,
    }


def estimate_quantile_var_grid(
    data: pd.DataFrame,
    lags: int = 4,
    taus: tuple = (0.05, 0.25, 0.50, 0.75, 0.95),
) -> dict:
    """
    Estimate QVAR at multiple quantiles, returning a dict keyed by tau.
    """
    results = {}
    for tau in taus:
        results[tau] = estimate_quantile_var(data, lags=lags, tau=tau)
    return results


# ═══════════════════════════════════════════════════════════════════════════
# 2. Quantile Impulse Response Functions (QIRFs)
# ═══════════════════════════════════════════════════════════════════════════

def quantile_irf(
    qvar_result: dict,
    shock_var: int = 0,
    shock_size: float = 1.0,
    horizon: int = 20,
) -> pd.DataFrame:
    """
    Compute quantile impulse response function from a fitted QVAR.

    Uses the companion-form representation to trace out the response
    of each variable to a unit shock in shock_var.

    Parameters
    ----------
    qvar_result : Output from estimate_quantile_var.
    shock_var : Index of the variable to shock.
    shock_size : Size of the shock (in units of the variable).
    horizon : Number of periods for the IRF.

    Returns
    -------
    DataFrame (horizon x k) of impulse responses.
    """
    companion = qvar_result["companion"]
    k = qvar_result["n_vars"]
    names = qvar_result["names"]

    # Initial shock vector
    shock = np.zeros(companion.shape[0])
    shock[shock_var] = shock_size

    irfs = np.zeros((horizon + 1, k))
    irfs[0, :] = shock[:k]

    state = shock.copy()
    for h in range(1, horizon + 1):
        state = companion @ state
        irfs[h, :] = state[:k]

    return pd.DataFrame(irfs, columns=names, index=range(horizon + 1))


def compare_quantile_irfs(
    qvar_grid: dict,
    shock_var: int = 0,
    response_var: int = 1,
    horizon: int = 20,
) -> pd.DataFrame:
    """
    Compare IRFs across quantiles for a given shock → response pair.

    Returns DataFrame with columns = quantile levels, rows = horizon.
    """
    results = {}
    for tau, qvar in qvar_grid.items():
        irf = quantile_irf(qvar, shock_var=shock_var, horizon=horizon)
        response_name = qvar["names"][response_var]
        results[f"tau={tau}"] = irf[response_name]

    return pd.DataFrame(results)


# ═══════════════════════════════════════════════════════════════════════════
# 3. Quantile Connectedness (Ando, Greenwood-Nimmo, Shin 2022)
# ═══════════════════════════════════════════════════════════════════════════

def _qvar_fevd(
    qvar_result: dict,
    h: int = 10,
) -> np.ndarray:
    """
    Compute generalized forecast-error variance decomposition from a QVAR.

    Adapts the Pesaran-Shin (1998) approach to the quantile setting by
    using the covariance of QVAR residuals.
    """
    companion = qvar_result["companion"]
    resids = qvar_result["residuals"].values
    k = qvar_result["n_vars"]

    sigma = np.cov(resids.T)
    sigma_diag = np.diag(sigma)

    # Compute MA representations: Phi_s = C^s where C is companion
    # But we only need the top-left k x k block
    dim = companion.shape[0]
    theta = np.zeros((k, k))

    for i in range(k):
        for j in range(k):
            num = 0.0
            denom = 0.0
            power = np.eye(dim)
            for s in range(h + 1):
                if s > 0:
                    power = power @ companion
                Phi_s = power[:k, :k]

                # Generalized: use sigma for scaling
                e_j = np.zeros(k)
                e_j[j] = 1.0
                response = Phi_s @ sigma @ e_j
                num += response[i] ** 2

                contrib = Phi_s @ sigma @ Phi_s.T
                denom += contrib[i, i]

            num /= sigma_diag[j] if sigma_diag[j] > 0 else 1.0
            theta[i, j] = num / denom if denom > 0 else 0.0

    # Normalize rows
    row_sums = theta.sum(axis=1, keepdims=True)
    theta = theta / np.where(row_sums > 0, row_sums, 1.0)
    return theta


def quantile_connectedness(
    data: pd.DataFrame,
    lags: int = 4,
    tau: float = 0.05,
    h: int = 10,
) -> dict:
    """
    Compute the Ando-Greenwood-Nimmo-Shin (2022) quantile connectedness.

    This extends Diebold-Yilmaz to the tails: connectedness is computed
    from a QVAR estimated at quantile tau, capturing tail spillovers.

    Parameters
    ----------
    data : DataFrame of returns/variables.
    lags : QVAR lag order.
    tau : Quantile (0.05 for left tail stress, 0.95 for right tail boom).
    h : Forecast horizon for FEVD.

    Returns
    -------
    dict with:
      - theta: (k x k) quantile FEVD matrix
      - total_connectedness: scalar (0-100)
      - to_others, from_others, net: directional measures
      - tau: the quantile
      - names: variable names
    """
    qvar = estimate_quantile_var(data, lags=lags, tau=tau)
    names = qvar["names"]
    k = len(names)

    theta = _qvar_fevd(qvar, h=h)

    to_others = np.zeros(k)
    from_others = np.zeros(k)
    for i in range(k):
        for j in range(k):
            if i != j:
                to_others[j] += theta[i, j]
                from_others[i] += theta[i, j]

    total = from_others.sum() / k * 100

    return {
        "theta": pd.DataFrame(theta, index=names, columns=names),
        "total_connectedness": total,
        "to_others": pd.Series(to_others * 100, index=names),
        "from_others": pd.Series(from_others * 100, index=names),
        "net": pd.Series((to_others - from_others) * 100, index=names),
        "tau": tau,
        "names": names,
    }


def tail_connectedness_comparison(
    data: pd.DataFrame,
    lags: int = 4,
    h: int = 10,
    taus: tuple = (0.05, 0.50, 0.95),
) -> pd.DataFrame:
    """
    Compare total and directional connectedness across quantiles.

    Returns a summary DataFrame showing how connectedness differs
    between the left tail (stress), median, and right tail (boom).
    """
    records = []
    for tau in taus:
        result = quantile_connectedness(data, lags=lags, tau=tau, h=h)
        record = {
            "tau": tau,
            "total_connectedness": result["total_connectedness"],
        }
        for name in result["names"]:
            record[f"to_{name}"] = result["to_others"][name]
            record[f"from_{name}"] = result["from_others"][name]
            record[f"net_{name}"] = result["net"][name]
        records.append(record)

    return pd.DataFrame(records).set_index("tau")


def rolling_quantile_connectedness(
    data: pd.DataFrame,
    window: int = 60,
    lags: int = 4,
    tau: float = 0.05,
    h: int = 10,
    step: int = 1,
) -> pd.DataFrame:
    """
    Rolling-window quantile connectedness over time.

    Tracks how tail connectedness evolves — e.g. does left-tail
    connectedness spike before/during crises?
    """
    dates = data.index
    records = []

    for end in range(window, len(dates), step):
        start = end - window
        window_data = data.iloc[start:end]
        try:
            result = quantile_connectedness(
                window_data, lags=lags, tau=tau, h=h,
            )
            records.append({
                "date": dates[end - 1],
                "total_connectedness": result["total_connectedness"],
                "tau": tau,
            })
        except Exception:
            continue

    return pd.DataFrame(records).set_index("date")


# ═══════════════════════════════════════════════════════════════════════════
# 4. Growth-at-Risk (Adrian et al. 2019)
# ═══════════════════════════════════════════════════════════════════════════

def growth_at_risk(
    y: pd.Series,
    financial_conditions: pd.Series,
    controls: Optional[pd.DataFrame] = None,
    horizon: int = 4,
    tau: float = 0.05,
) -> dict:
    """
    Growth-at-Risk regression (Adrian, Boyarchenko, Giannone 2019).

        Q_{tau}(y_{t+h}) = alpha + beta * FCI_t + gamma * X_t

    The left-tail quantile of future growth as a function of current
    financial conditions. Loose financial conditions (high FCI) predict
    worse left-tail outcomes at longer horizons.

    Parameters
    ----------
    y : Target variable (e.g., GDP growth, credit growth).
    financial_conditions : Financial conditions index (FCI).
    controls : Additional control variables.
    horizon : Forecast horizon (in periods).
    tau : Quantile for the GaR regression.

    Returns
    -------
    dict with regression results, fitted values, and GaR path.
    """
    # Build forward-looking dependent variable
    y_forward = y.shift(-horizon)

    df = pd.DataFrame({
        "y_forward": y_forward,
        "fci": financial_conditions,
    }).dropna()

    if controls is not None:
        df = pd.concat([df, controls.reindex(df.index)], axis=1).dropna()

    X_cols = ["fci"]
    if controls is not None:
        X_cols += controls.columns.tolist()

    X = sm.add_constant(df[X_cols])
    y_dep = df["y_forward"]

    model = sm.QuantReg(y_dep, X)
    res = model.fit(q=tau, max_iter=2000)

    return {
        "result": res,
        "coefficients": res.params,
        "pvalues": res.pvalues,
        "fitted": res.fittedvalues,
        "tau": tau,
        "horizon": horizon,
        "fci_beta": res.params.get("fci", res.params.iloc[1]),
        "n_obs": int(res.nobs),
    }


def growth_at_risk_term_structure(
    y: pd.Series,
    financial_conditions: pd.Series,
    controls: Optional[pd.DataFrame] = None,
    horizons: tuple = (1, 2, 4, 8, 12),
    taus: tuple = (0.05, 0.25, 0.50, 0.75, 0.95),
) -> pd.DataFrame:
    """
    Compute GaR across multiple horizons and quantiles.

    Returns a DataFrame showing how the quantile-specific effects
    of financial conditions change with the forecast horizon.
    This reveals the key Adrian et al. (2019) finding: loose
    financial conditions benefit the median but worsen the left tail
    at longer horizons.
    """
    records = []
    for h in horizons:
        for tau in taus:
            try:
                gar = growth_at_risk(
                    y, financial_conditions, controls=controls,
                    horizon=h, tau=tau,
                )
                records.append({
                    "horizon": h,
                    "tau": tau,
                    "fci_beta": gar["fci_beta"],
                    "n_obs": gar["n_obs"],
                    "pvalue_fci": gar["pvalues"].iloc[1]
                        if len(gar["pvalues"]) > 1 else np.nan,
                })
            except Exception:
                continue

    return pd.DataFrame(records)
