"""
FX Hedging as a Contagion Channel: How NBFI Currency Risk Management
Transmits Global Financial Shocks.

Project 4 — Standalone Research Module

Implements the empirical framework combining:
  - Rey, Stavrakeva & Tang (2024): Currency centrality in equity markets
  - Nenova, Schrimpf & Shin (2025): Global portfolio investments and FX derivatives

Modules:
  1. Synthetic data generation (FX swap basis, yield curves, equity returns,
     bond flows, hedging costs) with embedded tail asymmetries
  2. CIP deviation / hedging cost computation
  3. Quantile regressions of CIP basis on equity shocks, yield slopes, VIX
     (Layer 1 — offsetting forces test)
  4. Delta-CoVaR of bond flows conditional on FX hedging stress (Layer 2)
  5. Quantile connectedness across {equity, FX, CIP basis, bond flows}
     (Layer 3 — Ando, Greenwood-Nimmo & Shin 2022)
  6. Asymmetry test: do yield curve offsets vanish in the tails?

References
----------
- Rey, H., Stavrakeva, V. & Tang, J. (2024). Currency centrality in equity
  markets, exchange rates and global financial cycles. NBER WP 33003.
- Nenova, T., Schrimpf, A. & Shin, H.S. (2025). Global portfolio
  investments and FX derivatives. BIS Working Paper No. 1273.
- Ando, T., Greenwood-Nimmo, M. & Shin, Y. (2022). Quantile connectedness.
  Management Science, 68(4), 2401-2431.
- Adrian, T. & Brunnermeier, M. (2016). CoVaR. AER, 106(7), 1705-1741.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════
# 1. Synthetic Data Generation
# ═══════════════════════════════════════════════════════════════════════════

def build_synthetic_fx_hedging_panel(
    n_periods: int = 240,
    seed: int = 42,
) -> dict:
    """
    Generate synthetic data for the FX hedging contagion analysis.

    The DGP embeds the key economic mechanism:
    - In normal times: equity shocks move FX and yield curves in offsetting
      directions for hedging costs (self-stabilizing).
    - In the tails: the offset breaks down — USD appreciation, curve
      flattening, and CIP blowout reinforce each other (amplification).

    Returns
    -------
    dict with DataFrames:
      - ts_data: time series panel (monthly, 2005-2024)
      - currencies: list of currency pairs
      - country_panel: country-level panel with NBFI penetration
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2005-01-01", periods=n_periods, freq="ME")
    currencies = ["EUR/USD", "GBP/USD", "JPY/USD", "CHF/USD", "AUD/USD"]
    n_ccy = len(currencies)

    # ── Global factors ──────────────────────────────────────────────────
    # VIX (log-normal, AR(1))
    vix = np.zeros(n_periods)
    vix[0] = 15.0
    for t in range(1, n_periods):
        vix[t] = 0.85 * vix[t - 1] + 0.15 * 20.0 + rng.normal(0, 3)
    vix = np.clip(vix, 8, 80)

    # US monetary policy shock (quarterly, zero-mean)
    us_mp_shock = rng.normal(0, 0.25, n_periods)

    # Global risk appetite (inverse VIX, standardized)
    risk_appetite = -(vix - vix.mean()) / vix.std()

    # ── US variables ────────────────────────────────────────────────────
    # US equity returns (S&P 500 proxy)
    us_equity = rng.normal(0.007, 0.04, n_periods) + 0.3 * risk_appetite * 0.01

    # US yield curve slope (10Y - 2Y), affected by MP shocks
    us_slope = np.zeros(n_periods)
    us_slope[0] = 1.5
    for t in range(1, n_periods):
        us_slope[t] = (0.9 * us_slope[t - 1]
                       + 0.1 * 1.5
                       - 0.3 * us_mp_shock[t]
                       + 0.15 * us_equity[t] * 10  # equity boom → steeper
                       + rng.normal(0, 0.15))

    # US short rate
    us_short = np.zeros(n_periods)
    us_short[0] = 3.0
    for t in range(1, n_periods):
        us_short[t] = (0.95 * us_short[t - 1]
                       + 0.5 * us_mp_shock[t]
                       + rng.normal(0, 0.1))
    us_short = np.clip(us_short, 0, 8)

    # ── Per-currency variables ──────────────────────────────────────────
    records = []
    for c_idx, ccy in enumerate(currencies):
        # Foreign yield curve slope
        foreign_slope = np.zeros(n_periods)
        foreign_slope[0] = 1.0 + rng.normal(0, 0.3)
        for t in range(1, n_periods):
            foreign_slope[t] = (0.88 * foreign_slope[t - 1]
                                + 0.12 * 1.0
                                + rng.normal(0, 0.12))

        # Exchange rate change (foreign per USD)
        # Key mechanism from Rey et al.: equity shocks drive FX
        fx_return = np.zeros(n_periods)
        for t in range(n_periods):
            # Normal component: US equity strength → USD appreciates
            fx_return[t] = (0.3 * us_equity[t]
                            + 0.1 * us_mp_shock[t]
                            + rng.normal(0, 0.02))
            # Tail amplification: when VIX spikes, USD appreciates more
            if vix[t] > 30:
                fx_return[t] += 0.02 * (vix[t] - 30) / 10

        # CIP basis / FX swap basis (hedging cost)
        # The central variable — where offsetting forces meet
        cip_basis = np.zeros(n_periods)
        for t in range(n_periods):
            # Normal regime: yield slopes offset FX moves
            cip_basis[t] = (-0.05 * (us_slope[t] - foreign_slope[t])  # slope diff
                            + 0.3 * fx_return[t]         # FX pass-through
                            + 0.02 * vix[t] / 20         # risk premium
                            + rng.normal(0, 0.05))

            # Tail regime: ALL forces reinforce (amplification)
            if vix[t] > 35:
                stress_factor = (vix[t] - 35) / 20
                cip_basis[t] += (0.15 * stress_factor          # risk premium spikes
                                 + 0.1 * abs(fx_return[t])     # FX volatility adds
                                 + 0.05 * max(0, 2 - us_slope[t]))  # flat curve worsens

        # Foreign equity returns (correlated with US, more during stress)
        base_corr = 0.5 + 0.1 * c_idx  # varying correlations by currency
        foreign_equity = (base_corr * us_equity
                          + (1 - base_corr) * rng.normal(0, 0.04, n_periods))
        # Stress amplification: higher correlation during stress
        stress_mask = vix > 30
        foreign_equity[stress_mask] = (0.8 * us_equity[stress_mask]
                                       + 0.2 * rng.normal(0, 0.06,
                                                           stress_mask.sum()))

        # Bond flows (hedged cross-border bond investment)
        bond_flows = np.zeros(n_periods)
        for t in range(n_periods):
            # Flows driven by relative yield attractiveness minus hedging cost
            carry = us_slope[t] - cip_basis[t] * 100
            bond_flows[t] = (0.3 * carry / 100
                             + 0.1 * risk_appetite[t]
                             - 0.5 * abs(cip_basis[t])  # hedging cost deters
                             + rng.normal(0, 0.5))

        # NBFI FX swap notional (proxy for hedging volume)
        fx_swap_volume = np.zeros(n_periods)
        fx_swap_volume[0] = 50.0  # USD billions (notional)
        for t in range(1, n_periods):
            fx_swap_volume[t] = (0.95 * fx_swap_volume[t - 1]
                                 + 0.05 * 50
                                 + 2.0 * bond_flows[t]   # flows drive hedging
                                 + 0.5 * max(0, us_slope[t])  # steeper → more
                                 - 3.0 * cip_basis[t]     # costly → less
                                 + rng.normal(0, 2))
        fx_swap_volume = np.clip(fx_swap_volume, 5, 200)

        for t in range(n_periods):
            records.append({
                "date": dates[t],
                "currency": ccy,
                "us_equity_return": us_equity[t],
                "foreign_equity_return": foreign_equity[t],
                "fx_return": fx_return[t],
                "us_yield_slope": us_slope[t],
                "foreign_yield_slope": foreign_slope[t],
                "slope_differential": us_slope[t] - foreign_slope[t],
                "us_short_rate": us_short[t],
                "cip_basis": cip_basis[t],
                "bond_flows": bond_flows[t],
                "fx_swap_volume": fx_swap_volume[t],
                "vix": vix[t],
                "risk_appetite": risk_appetite[t],
                "us_mp_shock": us_mp_shock[t],
            })

    ts_data = pd.DataFrame(records)

    # ── Country-level panel (for NBFI penetration regressions) ──────────
    countries = ["Euro Area", "United Kingdom", "Japan", "Switzerland", "Australia"]
    country_records = []
    nbfi_base = {"Euro Area": 120, "United Kingdom": 180, "Japan": 90,
                 "Switzerland": 200, "Australia": 110}
    for c_idx, (country, ccy) in enumerate(zip(countries, currencies)):
        for t_idx, date in enumerate(dates):
            nb = nbfi_base[country] + 0.3 * t_idx + rng.normal(0, 5)
            country_records.append({
                "date": date,
                "country": country,
                "currency": ccy,
                "nbfi_assets_pct_gdp": nb,
                "fx_hedge_ratio": 0.5 + 0.2 * rng.random(),
                "cross_border_bond_holdings": (
                    50 + 0.2 * t_idx + 5 * risk_appetite[t_idx] + rng.normal(0, 3)
                ),
            })

    country_panel = pd.DataFrame(country_records)

    return {
        "ts_data": ts_data,
        "currencies": currencies,
        "country_panel": country_panel,
        "dates": dates,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 2. CIP Deviation / Hedging Cost Analysis
# ═══════════════════════════════════════════════════════════════════════════

def compute_hedging_cost_decomposition(
    ts_data: pd.DataFrame,
    currency: str,
) -> pd.DataFrame:
    """
    Decompose FX hedging costs into components:
      CIP_basis = f(slope_differential, fx_volatility, risk_premium)

    This follows the Nenova, Schrimpf & Shin (2025) insight that yield
    curve slopes are key determinants of hedging demand and costs.
    """
    df = ts_data[ts_data["currency"] == currency].copy()
    df = df.set_index("date")

    # Rolling FX volatility
    df["fx_volatility"] = df["fx_return"].rolling(12).std()

    # Decomposition regression
    df_clean = df.dropna()
    X = sm.add_constant(df_clean[[
        "slope_differential", "fx_volatility", "vix",
    ]])
    y = df_clean["cip_basis"]

    model = sm.OLS(y, X)
    result = model.fit(cov_type="HAC", cov_kwds={"maxlags": 6})

    # Fitted components
    df_clean["slope_component"] = (
        result.params.get("slope_differential", 0) * df_clean["slope_differential"]
    )
    df_clean["fx_vol_component"] = (
        result.params.get("fx_volatility", 0) * df_clean["fx_volatility"]
    )
    df_clean["risk_component"] = (
        result.params.get("vix", 0) * df_clean["vix"]
    )
    df_clean["residual"] = result.resid

    return df_clean, result


# ═══════════════════════════════════════════════════════════════════════════
# 3. Layer 1: Quantile Regression — Offsetting Forces Test
# ═══════════════════════════════════════════════════════════════════════════

def quantile_cip_regression(
    ts_data: pd.DataFrame,
    currency: str,
    taus: tuple = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95),
) -> pd.DataFrame:
    """
    Quantile regression of CIP basis on equity returns, yield slopes, and VIX.

    Core test of the "offsetting forces" hypothesis:
    - At the MEDIAN: equity returns and yield slopes have offsetting effects
      on CIP basis (self-stabilizing).
    - In the TAILS (tau=0.05, 0.95): the offset vanishes — all forces
      reinforce, creating amplification.

    Specification:
        Q_tau(CIP_basis) = a + b1*equity_return + b2*slope_diff
                           + b3*VIX + b4*(equity_return × VIX)

    Key prediction: b4 is insignificant at the median but large and
    significant in the tails (the interaction amplifies).
    """
    df = ts_data[ts_data["currency"] == currency].copy()
    df = df.set_index("date")

    # Interaction term (captures tail amplification)
    df["equity_x_vix"] = df["us_equity_return"] * df["vix"]

    df_clean = df.dropna(subset=[
        "cip_basis", "us_equity_return", "slope_differential",
        "vix", "equity_x_vix",
    ])

    X = sm.add_constant(df_clean[[
        "us_equity_return", "slope_differential", "vix", "equity_x_vix",
    ]])
    y = df_clean["cip_basis"]

    results = []
    for tau in taus:
        model = sm.QuantReg(y, X)
        res = model.fit(q=tau, max_iter=3000)
        row = {"tau": tau, "n_obs": int(res.nobs)}
        for var in res.params.index:
            row[f"beta_{var}"] = res.params[var]
            row[f"pval_{var}"] = res.pvalues[var]
            row[f"se_{var}"] = res.bse[var]
        results.append(row)

    return pd.DataFrame(results).set_index("tau")


def asymmetry_test(
    quantile_results: pd.DataFrame,
) -> dict:
    """
    Formal test of tail asymmetry: are the coefficients at tau=0.05 and
    tau=0.95 significantly different from the median (tau=0.50)?

    Tests H0: beta(tau=0.05) = beta(tau=0.50) for the interaction term.
    Uses bootstrap-based Wald test approximation.
    """
    if 0.05 not in quantile_results.index or 0.50 not in quantile_results.index:
        return {"error": "Need tau=0.05 and tau=0.50 in results"}

    interaction_var = "beta_equity_x_vix"
    if interaction_var not in quantile_results.columns:
        return {"error": f"{interaction_var} not found in results"}

    beta_05 = quantile_results.loc[0.05, interaction_var]
    beta_50 = quantile_results.loc[0.50, interaction_var]
    beta_95 = quantile_results.loc[0.95, interaction_var]
    se_05 = quantile_results.loc[0.05, "se_equity_x_vix"]
    se_50 = quantile_results.loc[0.50, "se_equity_x_vix"]
    se_95 = quantile_results.loc[0.95, "se_equity_x_vix"]

    # Approximate Wald statistic for difference
    diff_left = beta_05 - beta_50
    se_diff_left = np.sqrt(se_05**2 + se_50**2)
    z_left = diff_left / se_diff_left if se_diff_left > 0 else 0

    diff_right = beta_95 - beta_50
    se_diff_right = np.sqrt(se_95**2 + se_50**2)
    z_right = diff_right / se_diff_right if se_diff_right > 0 else 0

    from scipy import stats
    p_left = 2 * (1 - stats.norm.cdf(abs(z_left)))
    p_right = 2 * (1 - stats.norm.cdf(abs(z_right)))

    return {
        "beta_05": beta_05,
        "beta_50": beta_50,
        "beta_95": beta_95,
        "diff_left_tail": diff_left,
        "z_stat_left": z_left,
        "p_value_left": p_left,
        "diff_right_tail": diff_right,
        "z_stat_right": z_right,
        "p_value_right": p_right,
        "conclusion": (
            "Tail asymmetry detected" if (p_left < 0.10 or p_right < 0.10)
            else "No significant tail asymmetry"
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 4. Layer 2: Delta-CoVaR of Bond Flows | FX Hedging Stress
# ═══════════════════════════════════════════════════════════════════════════

def covar_fx_hedging(
    ts_data: pd.DataFrame,
    currency: str,
    tau: float = 0.05,
) -> dict:
    """
    Estimate Delta-CoVaR: how much does the VaR of cross-border bond flows
    increase when FX hedging conditions move from median to stressed?

    CoVaR(bond_flows | CIP_basis = VaR_tau)
      vs
    CoVaR(bond_flows | CIP_basis = median)

    Delta-CoVaR = difference = systemic risk contribution of FX hedging channel.

    Following Adrian & Brunnermeier (2016).
    """
    df = ts_data[ts_data["currency"] == currency].copy()
    df = df.set_index("date").dropna(
        subset=["bond_flows", "cip_basis", "vix", "us_equity_return"]
    )

    # Step 1: VaR of CIP basis
    cip_var_model = sm.QuantReg(
        df["cip_basis"],
        sm.add_constant(df[["vix", "us_equity_return"]]),
    )
    cip_var_res = cip_var_model.fit(q=tau, max_iter=3000)

    # Step 2: CoVaR — bond flows conditioned on CIP basis
    X_covar = sm.add_constant(df[["cip_basis", "vix", "us_equity_return"]])
    covar_model = sm.QuantReg(df["bond_flows"], X_covar)
    covar_res = covar_model.fit(q=tau, max_iter=3000)

    # Step 3: Compute Delta-CoVaR
    # At stress: CIP basis at its tau-quantile
    cip_stressed = df["cip_basis"].quantile(1 - tau)  # upper tail = stress
    cip_median = df["cip_basis"].median()

    # Predict bond flows at stressed vs median CIP
    X_stress = pd.DataFrame({
        "const": [1],
        "cip_basis": [cip_stressed],
        "vix": [df["vix"].mean()],
        "us_equity_return": [df["us_equity_return"].mean()],
    })
    X_normal = X_stress.copy()
    X_normal["cip_basis"] = cip_median

    covar_stressed = covar_res.predict(X_stress).iloc[0]
    covar_normal = covar_res.predict(X_normal).iloc[0]
    delta_covar = covar_stressed - covar_normal

    return {
        "covar_stressed": covar_stressed,
        "covar_normal": covar_normal,
        "delta_covar": delta_covar,
        "cip_basis_stressed": cip_stressed,
        "cip_basis_median": cip_median,
        "covar_regression": covar_res,
        "cip_var_regression": cip_var_res,
        "tau": tau,
        "currency": currency,
    }


def delta_covar_all_currencies(
    ts_data: pd.DataFrame,
    currencies: list,
    tau: float = 0.05,
) -> pd.DataFrame:
    """Compute Delta-CoVaR for all currency pairs."""
    results = []
    for ccy in currencies:
        res = covar_fx_hedging(ts_data, ccy, tau=tau)
        results.append({
            "currency": ccy,
            "delta_covar": res["delta_covar"],
            "covar_stressed": res["covar_stressed"],
            "covar_normal": res["covar_normal"],
            "cip_stressed": res["cip_basis_stressed"],
            "cip_median": res["cip_basis_median"],
        })
    return pd.DataFrame(results).set_index("currency")


# ═══════════════════════════════════════════════════════════════════════════
# 5. Layer 3: Quantile Connectedness (Equity, FX, CIP, Bond Flows)
# ═══════════════════════════════════════════════════════════════════════════

def build_connectedness_system(
    ts_data: pd.DataFrame,
    currency: str,
) -> pd.DataFrame:
    """
    Build the 4-variable system for quantile connectedness:
      [US equity, FX return, CIP basis, Bond flows]

    This captures the full transmission chain from Rey et al. through
    Nenova et al.
    """
    df = ts_data[ts_data["currency"] == currency].copy()
    df = df.set_index("date")

    system = df[[
        "us_equity_return", "fx_return", "cip_basis", "bond_flows",
    ]].dropna()

    return system


def fx_hedging_quantile_connectedness(
    ts_data: pd.DataFrame,
    currency: str,
    tau: float = 0.05,
    lags: int = 4,
    h: int = 10,
) -> dict:
    """
    Compute quantile connectedness across the FX hedging transmission
    chain for a single currency.

    Uses the Ando, Greenwood-Nimmo & Shin (2022) methodology applied
    to the system: {equity → FX → CIP basis → bond flows}.

    The key prediction: connectedness at tau=0.05 >> connectedness at
    tau=0.50 (contagion activates in stress).
    """
    system = build_connectedness_system(ts_data, currency)
    k = system.shape[1]
    names = system.columns.tolist()
    arr = system.values

    # Build VAR matrices
    T = arr.shape[0]
    Y = arr[lags:]
    X_parts = [arr[lags - lag: T - lag] for lag in range(1, lags + 1)]
    X = np.column_stack([np.ones(T - lags)] + X_parts)

    # Estimate QVAR equation-by-equation
    B = np.zeros((k, X.shape[1]))
    residuals = np.zeros((T - lags, k))
    for i in range(k):
        model = sm.QuantReg(Y[:, i], X)
        res = model.fit(q=tau, max_iter=3000)
        B[i, :] = res.params
        residuals[:, i] = Y[:, i] - X @ res.params

    # Companion matrix
    B_no_intercept = B[:, 1:]
    companion = np.zeros((k * lags, k * lags))
    companion[:k, :] = B_no_intercept
    if lags > 1:
        companion[k:, :k * (lags - 1)] = np.eye(k * (lags - 1))

    # FEVD
    sigma = np.cov(residuals.T) + 1e-8 * np.eye(k)
    sigma_diag = np.diag(sigma)

    theta = np.zeros((k, k))
    dim = companion.shape[0]
    for i in range(k):
        for j in range(k):
            num = 0.0
            denom = 0.0
            power = np.eye(dim)
            for s in range(h + 1):
                if s > 0:
                    power = power @ companion
                Phi_s = power[:k, :k]
                e_j = np.zeros(k)
                e_j[j] = 1.0
                response = Phi_s @ sigma @ e_j
                num += response[i] ** 2
                contrib = Phi_s @ sigma @ Phi_s.T
                denom += contrib[i, i]
            num /= sigma_diag[j] if sigma_diag[j] > 0 else 1.0
            theta[i, j] = num / denom if denom > 0 else 0.0

    row_sums = theta.sum(axis=1, keepdims=True)
    theta = theta / np.where(row_sums > 0, row_sums, 1.0)

    # Connectedness measures
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
        "currency": currency,
    }


def tail_connectedness_comparison(
    ts_data: pd.DataFrame,
    currency: str,
    taus: tuple = (0.05, 0.50, 0.95),
    lags: int = 4,
    h: int = 10,
) -> pd.DataFrame:
    """
    Compare total connectedness across quantiles for a currency.

    The key test: if total connectedness at tau=0.05 >> tau=0.50,
    then contagion through the FX hedging channel is asymmetric
    and activates primarily during stress.
    """
    records = []
    for tau in taus:
        result = fx_hedging_quantile_connectedness(
            ts_data, currency, tau=tau, lags=lags, h=h,
        )
        record = {
            "tau": tau,
            "total_connectedness": result["total_connectedness"],
        }
        for name in result["to_others"].index:
            record[f"to_{name}"] = result["to_others"][name]
            record[f"from_{name}"] = result["from_others"][name]
            record[f"net_{name}"] = result["net"][name]
        records.append(record)

    return pd.DataFrame(records).set_index("tau")


def cross_currency_connectedness(
    ts_data: pd.DataFrame,
    currencies: list,
    taus: tuple = (0.05, 0.50, 0.95),
) -> pd.DataFrame:
    """
    Compute tail connectedness across all currencies and quantiles.

    Returns a summary showing which currency pairs exhibit the
    strongest tail amplification in the FX hedging channel.
    """
    records = []
    for ccy in currencies:
        for tau in taus:
            try:
                result = fx_hedging_quantile_connectedness(
                    ts_data, ccy, tau=tau,
                )
                records.append({
                    "currency": ccy,
                    "tau": tau,
                    "total_connectedness": result["total_connectedness"],
                })
            except Exception:
                continue

    return pd.DataFrame(records)


# ═══════════════════════════════════════════════════════════════════════════
# 6. NBFI Penetration × FX Hedging Amplification
# ═══════════════════════════════════════════════════════════════════════════

def nbfi_fx_hedging_panel_regression(
    ts_data: pd.DataFrame,
    country_panel: pd.DataFrame,
) -> dict:
    """
    Panel regression testing whether NBFI penetration amplifies the
    FX hedging contagion channel:

        bond_flows_{c,t} = alpha_c + b1*cip_basis_{c,t}
                           + b2*NBFI_{c,t}
                           + b3*(cip_basis × NBFI)
                           + controls + epsilon

    If b3 < 0 and significant: higher NBFI penetration amplifies the
    negative effect of hedging cost shocks on bond flows.
    """
    # Merge time series with country panel
    merged = ts_data.merge(
        country_panel[["date", "currency", "nbfi_assets_pct_gdp"]],
        on=["date", "currency"],
        how="inner",
    )

    # Interaction
    merged["cip_x_nbfi"] = (
        merged["cip_basis"] * merged["nbfi_assets_pct_gdp"] / 100
    )

    # Country fixed effects
    country_dummies = pd.get_dummies(
        merged["currency"], prefix="fe", drop_first=True, dtype=float,
    )

    X = pd.concat([
        merged[["cip_basis", "nbfi_assets_pct_gdp", "cip_x_nbfi", "vix"]],
        country_dummies,
    ], axis=1)
    X = sm.add_constant(X)
    y = merged["bond_flows"]

    mask = y.notna() & X.notna().all(axis=1)
    model = sm.OLS(y[mask], X[mask])
    ols_result = model.fit(
        cov_type="cluster",
        cov_kwds={"groups": merged.loc[mask, "currency"]},
    )

    return {
        "ols_result": ols_result,
        "interaction_coef": ols_result.params.get("cip_x_nbfi", np.nan),
        "interaction_pval": ols_result.pvalues.get("cip_x_nbfi", np.nan),
        "n_obs": int(ols_result.nobs),
    }


def iv_fx_hedging_regression(
    ts_data: pd.DataFrame,
    country_panel: pd.DataFrame,
) -> dict:
    """
    IV estimation using monetary policy shocks as instruments for
    yield curve slopes / CIP basis.

    First stage:  CIP_basis = f(us_mp_shock, slope_diff)
    Second stage: bond_flows = f(CIP_hat, NBFI, CIP_hat × NBFI)

    Addresses endogeneity: FX hedging costs are driven by monetary
    policy, which is exogenous to individual currency-pair bond flows.
    """
    merged = ts_data.merge(
        country_panel[["date", "currency", "nbfi_assets_pct_gdp"]],
        on=["date", "currency"],
        how="inner",
    ).dropna(subset=["bond_flows", "cip_basis", "us_mp_shock",
                      "nbfi_assets_pct_gdp"])

    # First stage
    X_1 = sm.add_constant(merged[["us_mp_shock", "slope_differential"]])
    first_stage = sm.OLS(merged["cip_basis"], X_1).fit()
    merged["cip_hat"] = first_stage.fittedvalues

    # Interaction with predicted CIP
    merged["cip_hat_x_nbfi"] = (
        merged["cip_hat"] * merged["nbfi_assets_pct_gdp"] / 100
    )

    # Second stage
    country_dummies = pd.get_dummies(
        merged["currency"], prefix="fe", drop_first=True, dtype=float,
    )
    X_2 = pd.concat([
        merged[["cip_hat", "nbfi_assets_pct_gdp", "cip_hat_x_nbfi", "vix"]],
        country_dummies,
    ], axis=1)
    X_2 = sm.add_constant(X_2)

    second_stage = sm.OLS(merged["bond_flows"], X_2).fit(cov_type="HC1")

    return {
        "first_stage": first_stage,
        "second_stage": second_stage,
        "first_stage_f_stat": first_stage.fvalue,
        "first_stage_f_pval": first_stage.f_pvalue,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 7. Cascade Simulation
# ═══════════════════════════════════════════════════════════════════════════

def simulate_fx_hedging_cascade(
    initial_equity_shock: float = -0.10,
    n_rounds: int = 8,
    fx_passthrough: float = 0.3,
    cip_sensitivity_to_fx: float = 0.5,
    cip_sensitivity_to_vix: float = 0.02,
    bond_flow_sensitivity: float = -2.0,
    feedback_equity: float = 0.15,
    vix_response: float = 5.0,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Simulate a multi-round cascade through the FX hedging channel:

    Round 1: Equity shock → USD appreciates → CIP basis widens
    Round 2: CIP blowout → NBFIs reduce hedged positions → bond sell-off
    Round 3: Bond sell-off → further equity decline → VIX spike
    Round 4-N: Feedback loop with dampening

    Returns per-round state of all variables.
    """
    rng = np.random.default_rng(seed)

    state = {
        "equity_return": initial_equity_shock,
        "fx_move": 0.0,
        "cip_basis_change": 0.0,
        "bond_flow_change": 0.0,
        "vix_change": 0.0,
        "cumulative_loss": 0.0,
    }

    records = [{"round": 0, **state}]

    for r in range(1, n_rounds + 1):
        # Dampening factor (geometric decay)
        dampen = 0.7 ** (r - 1)

        # 1. Equity → FX (Rey et al. channel)
        fx = fx_passthrough * state["equity_return"] * dampen
        fx += rng.normal(0, 0.005)

        # 2. FX + VIX → CIP basis (Nenova et al. channel)
        cip = (cip_sensitivity_to_fx * abs(fx)
               + cip_sensitivity_to_vix * state["vix_change"]
               ) * dampen

        # 3. CIP → Bond flows (hedging cost channel)
        flows = bond_flow_sensitivity * cip * dampen

        # 4. Bond flows → Equity feedback
        equity_fb = feedback_equity * flows * dampen

        # 5. VIX response to equity
        vix_ch = -vix_response * equity_fb

        # Update state
        state["equity_return"] = equity_fb
        state["fx_move"] = fx
        state["cip_basis_change"] = cip
        state["bond_flow_change"] = flows
        state["vix_change"] = vix_ch
        state["cumulative_loss"] += equity_fb

        records.append({"round": r, **state})

    return pd.DataFrame(records).set_index("round")
