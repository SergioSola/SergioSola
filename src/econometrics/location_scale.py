"""
Location-Scale models for tail-risk dynamics.

Implements location-scale specifications that replicate and extend quantile
regressions using conditional mean + conditional variance models:

  1. Two-step location-scale (Engle & Manganelli 2004 style)
     — Model both E[y|X] and Var[y|X], then construct conditional quantiles
  2. Conditional heteroskedasticity regressions
     — Separate regressions for the mean and log-variance
  3. Skew-t location-scale (Adrian et al. 2019, 2022)
     — Full conditional density using skewed-t distribution
  4. Tail-risk amplification tests
     — Whether NBFI variables amplify the variance/skewness of outcomes

References
----------
- Engle, R. & Manganelli, S. (2004). CAViaR. JBES.
- Adrian, T., Boyarchenko, N. & Giannone, D. (2019). Vulnerable growth. AER.
- Adrian, T. et al. (2022). The term structure of growth-at-risk. AEJ Macro.
- Delle Monache, D., De Polis, A. & Petrella, I. (2024). Modeling and
  forecasting macroeconomic downside risk. JBF.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats as sp_stats
from scipy.optimize import minimize
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════
# 1. Two-step location-scale model
# ═══════════════════════════════════════════════════════════════════════════

def location_scale_model(
    y: pd.Series,
    X: pd.DataFrame,
    z_vars: Optional[pd.DataFrame] = None,
) -> dict:
    """
    Two-step location-scale model.

    Step 1 (Location): y_t = X_t' beta + e_t               (OLS)
    Step 2 (Scale):    log(e_t^2) = Z_t' gamma + v_t       (OLS)

    Then conditional quantile:
        Q_tau(y_t | X_t, Z_t) = X_t' beta + sigma_t * F^{-1}(tau)

    where sigma_t = exp(Z_t' gamma / 2) and F is the standard normal
    (or t-distribution) CDF.

    Parameters
    ----------
    y : Dependent variable.
    X : Regressors for the location (mean) equation.
    z_vars : Regressors for the scale (variance) equation.
             If None, uses same regressors as location equation.

    Returns
    -------
    dict with location and scale regression results, conditional
    quantile function, and fitted moments.
    """
    df = pd.DataFrame({"y": y}).join(X).dropna()
    if z_vars is not None:
        df = df.join(z_vars, rsuffix="_z").dropna()

    y_vals = df["y"]
    X_loc = sm.add_constant(df[X.columns])

    # Step 1: Location (mean)
    loc_model = sm.OLS(y_vals, X_loc)
    loc_result = loc_model.fit(cov_type="HC1")
    residuals = loc_result.resid

    # Step 2: Scale (log-variance)
    log_sq_resid = np.log(residuals ** 2 + 1e-10)
    if z_vars is not None:
        Z_cols = [c for c in df.columns if c.endswith("_z") or c in z_vars.columns]
        Z_scale = sm.add_constant(df[Z_cols])
    else:
        Z_scale = X_loc.copy()

    scale_model = sm.OLS(log_sq_resid, Z_scale)
    scale_result = scale_model.fit(cov_type="HC1")

    # Fitted conditional standard deviation
    sigma_hat = np.exp(scale_result.fittedvalues / 2)

    # Conditional quantiles at various taus
    taus = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
    cond_quantiles = {}
    for tau in taus:
        z_score = sp_stats.norm.ppf(tau)
        cond_quantiles[tau] = loc_result.fittedvalues + sigma_hat * z_score

    return {
        "location_result": loc_result,
        "scale_result": scale_result,
        "conditional_mean": loc_result.fittedvalues,
        "conditional_sigma": sigma_hat,
        "conditional_quantiles": cond_quantiles,
        "residuals": residuals,
        "standardized_residuals": residuals / sigma_hat,
    }


def location_scale_gar(
    y: pd.Series,
    financial_conditions: pd.Series,
    nbfi_variable: Optional[pd.Series] = None,
    controls: Optional[pd.DataFrame] = None,
    horizon: int = 4,
) -> dict:
    """
    Location-scale Growth-at-Risk with NBFI amplification.

    Location: E[y_{t+h}] = alpha + beta_1 * FCI_t + beta_2 * NBFI_t + ...
    Scale: log Var[y_{t+h}] = delta_0 + delta_1 * FCI_t + delta_2 * NBFI_t + ...

    If delta_2 > 0, NBFI penetration increases the conditional variance
    of future growth (i.e., amplifies tail risks).

    Parameters
    ----------
    y : Target variable (GDP growth, credit growth, etc.).
    financial_conditions : FCI index.
    nbfi_variable : NBFI size or leverage measure (the amplifier).
    controls : Additional controls.
    horizon : Forecast horizon.

    Returns
    -------
    dict with location/scale results and conditional quantile paths.
    """
    y_forward = y.shift(-horizon)

    X_dict = {"fci": financial_conditions}
    if nbfi_variable is not None:
        X_dict["nbfi"] = nbfi_variable
        X_dict["fci_x_nbfi"] = financial_conditions * nbfi_variable

    X = pd.DataFrame(X_dict)

    if controls is not None:
        X = pd.concat([X, controls], axis=1)

    df = pd.DataFrame({"y_forward": y_forward}).join(X).dropna()

    result = location_scale_model(
        df["y_forward"],
        df[X.columns],
    )
    result["horizon"] = horizon

    return result


# ═══════════════════════════════════════════════════════════════════════════
# 2. Skewed-t location-scale density (Adrian et al. 2022)
# ═══════════════════════════════════════════════════════════════════════════

def _skewt_logpdf(x, mu, sigma, alpha, nu):
    """
    Log-PDF of Hansen's (1994) skewed-t distribution.

    Parameters: mu (location), sigma (scale), alpha (skewness), nu (df).
    """
    z = (x - mu) / sigma
    if nu <= 2:
        return -1e10

    a = nu / 2
    b = 0.5
    c = np.exp(sp_stats.special.gammaln(a + b) - sp_stats.special.gammaln(a)) / np.sqrt(np.pi * nu)

    if z < -alpha / (1 + alpha):
        adjusted_z = z * (1 + alpha)
    else:
        adjusted_z = z * (1 - alpha)

    logpdf = np.log(c / sigma) - (a + b) * np.log(1 + adjusted_z ** 2 / nu)
    return logpdf


def skewt_location_scale_fit(
    y: np.ndarray,
    X: np.ndarray,
    X_scale: Optional[np.ndarray] = None,
) -> dict:
    """
    Fit a skewed-t location-scale model by MLE.

    y_t ~ SkewT(mu_t, sigma_t, alpha, nu)
    mu_t = X_t' beta
    log(sigma_t) = Z_t' gamma

    Parameters
    ----------
    y : (T,) array of dependent variable.
    X : (T, p) array of location regressors.
    X_scale : (T, q) array of scale regressors. Defaults to X.

    Returns
    -------
    dict with fitted parameters and conditional moments.
    """
    if X_scale is None:
        X_scale = X.copy()

    T = len(y)
    p = X.shape[1]
    q = X_scale.shape[1]

    def neg_loglik(params):
        beta = params[:p]
        gamma = params[p:p + q]
        alpha = params[p + q]      # skewness
        nu = np.exp(params[p + q + 1]) + 2.01  # df > 2

        mu = X @ beta
        log_sigma = X_scale @ gamma
        sigma = np.exp(log_sigma)

        ll = 0.0
        for t in range(T):
            z = (y[t] - mu[t]) / sigma[t]
            # Simplified skew-t log-likelihood
            if z < 0:
                effective_z = z * (1 + alpha)
            else:
                effective_z = z * (1 - alpha)
            ll += sp_stats.t.logpdf(effective_z, df=nu) - np.log(sigma[t])

        return -ll

    # Initial values
    beta0 = np.linalg.lstsq(X, y, rcond=None)[0]
    resid0 = y - X @ beta0
    gamma0 = np.zeros(q)
    gamma0[0] = np.log(np.std(resid0))
    x0 = np.concatenate([beta0, gamma0, [0.0, np.log(5)]])

    result = minimize(neg_loglik, x0, method="Nelder-Mead",
                      options={"maxiter": 10000, "xatol": 1e-6})

    params = result.x
    beta_hat = params[:p]
    gamma_hat = params[p:p + q]
    alpha_hat = params[p + q]
    nu_hat = np.exp(params[p + q + 1]) + 2.01

    mu_hat = X @ beta_hat
    sigma_hat = np.exp(X_scale @ gamma_hat)

    return {
        "beta": beta_hat,
        "gamma": gamma_hat,
        "alpha": alpha_hat,
        "nu": nu_hat,
        "conditional_mean": mu_hat,
        "conditional_sigma": sigma_hat,
        "loglik": -result.fun,
        "converged": result.success,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 3. Tail-risk amplification tests
# ═══════════════════════════════════════════════════════════════════════════

def tail_risk_amplification(
    y: pd.Series,
    stress_indicator: pd.Series,
    amplifier: pd.Series,
    controls: Optional[pd.DataFrame] = None,
    taus: tuple = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95),
) -> pd.DataFrame:
    """
    Test whether an amplifier variable (e.g. NBFI leverage, connectedness)
    makes the tails of the outcome worse during stress.

    For each quantile tau:
        Q_tau(y_t) = alpha + beta_1 * Stress_t + beta_2 * Amplifier_t
                     + beta_3 * (Stress_t * Amplifier_t) + gamma * X_t

    If beta_3 < 0 at tau=0.05 (left tail), the amplifier worsens downside
    outcomes during stress. If beta_3 > 0 at tau=0.05, it buffers.

    Parameters
    ----------
    y : Outcome variable (returns, growth, spreads).
    stress_indicator : Stress measure (VIX, spread, crisis dummy).
    amplifier : The variable hypothesized to amplify (NBFI leverage, etc.).
    controls : Additional control variables.
    taus : Quantiles at which to estimate.

    Returns
    -------
    DataFrame with coefficients and p-values across quantiles.
    """
    df = pd.DataFrame({
        "y": y,
        "stress": stress_indicator,
        "amplifier": amplifier,
        "interaction": stress_indicator * amplifier,
    }).dropna()

    if controls is not None:
        df = pd.concat([df, controls.reindex(df.index)], axis=1).dropna()

    X_cols = ["stress", "amplifier", "interaction"]
    if controls is not None:
        X_cols += controls.columns.tolist()

    X = sm.add_constant(df[X_cols])

    records = []
    for tau in taus:
        model = sm.QuantReg(df["y"], X)
        res = model.fit(q=tau, max_iter=2000)

        record = {"tau": tau}
        for name in X.columns:
            record[f"coef_{name}"] = res.params.get(name, np.nan)
            record[f"pval_{name}"] = res.pvalues.get(name, np.nan)
        records.append(record)

    return pd.DataFrame(records).set_index("tau")


def variance_ratio_test(
    y: pd.Series,
    group_var: pd.Series,
    threshold: float = None,
) -> dict:
    """
    Test whether the conditional variance of y differs across groups.

    Split sample by group_var (above/below median or threshold) and
    test for equal variances using Levene's test and Brown-Forsythe test.

    This is useful for checking if, e.g., countries with larger NBFI
    sectors have more volatile outcomes.
    """
    df = pd.DataFrame({"y": y, "group": group_var}).dropna()

    if threshold is None:
        threshold = df["group"].median()

    high = df.loc[df["group"] > threshold, "y"]
    low = df.loc[df["group"] <= threshold, "y"]

    levene_stat, levene_p = sp_stats.levene(high, low)
    bf_stat, bf_p = sp_stats.levene(high, low, center="median")

    return {
        "var_high_group": high.var(),
        "var_low_group": low.var(),
        "variance_ratio": high.var() / low.var() if low.var() > 0 else np.inf,
        "levene_stat": levene_stat,
        "levene_pval": levene_p,
        "brown_forsythe_stat": bf_stat,
        "brown_forsythe_pval": bf_p,
        "n_high": len(high),
        "n_low": len(low),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 4. Conditional quantile functions from location-scale
# ═══════════════════════════════════════════════════════════════════════════

def conditional_quantile_from_ls(
    loc_result: sm.regression.linear_model.RegressionResultsWrapper,
    scale_result: sm.regression.linear_model.RegressionResultsWrapper,
    X_new: pd.DataFrame,
    Z_new: Optional[pd.DataFrame] = None,
    taus: tuple = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95),
    dist: str = "normal",
    df: float = 5.0,
) -> pd.DataFrame:
    """
    Compute conditional quantiles from fitted location-scale model.

    Q_tau(y | X, Z) = mu(X) + sigma(Z) * F^{-1}(tau)

    Parameters
    ----------
    loc_result : Fitted OLS for the location (mean).
    scale_result : Fitted OLS for the log-variance.
    X_new : New regressors for location prediction.
    Z_new : New regressors for scale prediction (defaults to X_new).
    taus : Quantiles to compute.
    dist : Distribution for z-scores ('normal' or 't').
    df : Degrees of freedom if dist='t'.

    Returns
    -------
    DataFrame with conditional quantiles (columns) for each observation (rows).
    """
    X_pred = sm.add_constant(X_new)
    mu = loc_result.predict(X_pred)

    if Z_new is not None:
        Z_pred = sm.add_constant(Z_new)
    else:
        Z_pred = X_pred
    log_var = scale_result.predict(Z_pred)
    sigma = np.exp(log_var / 2)

    result = pd.DataFrame(index=X_new.index)
    for tau in taus:
        if dist == "normal":
            z = sp_stats.norm.ppf(tau)
        elif dist == "t":
            z = sp_stats.t.ppf(tau, df=df)
        else:
            z = sp_stats.norm.ppf(tau)

        result[f"Q_{tau}"] = mu + sigma * z

    result["mu"] = mu
    result["sigma"] = sigma

    return result
