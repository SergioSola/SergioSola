"""
Diagnostics and results storage for the Bayesian QVAR.

Implements:
  1. MCMC convergence diagnostics (trace plots data, effective sample size,
     Geweke test, R-hat)
  2. Quantile condition checks on residuals
  3. Stationarity checks across posterior draws
  4. Results packaging and export to disk
"""

from __future__ import annotations

import numpy as np
import json
import os
from typing import Optional
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
# MCMC Convergence diagnostics
# ═══════════════════════════════════════════════════════════════════════════

def effective_sample_size(chain: np.ndarray) -> float:
    """
    Compute effective sample size (ESS) for a 1D chain.

    Uses the initial positive sequence estimator for autocorrelation.
    """
    n = len(chain)
    if n < 10:
        return float(n)

    mean = np.mean(chain)
    var = np.var(chain, ddof=1)
    if var < 1e-15:
        return float(n)

    # Autocorrelation via FFT
    x = chain - mean
    fft_x = np.fft.fft(x, n=2 * n)
    acf_full = np.fft.ifft(fft_x * np.conj(fft_x)).real[:n] / (n * var)

    # Initial positive sequence estimator
    tau = 1.0
    for lag in range(1, n):
        if acf_full[lag] < 0:
            break
        tau += 2 * acf_full[lag]

    ess = n / tau
    return max(1.0, ess)


def geweke_test(chain: np.ndarray, frac_a: float = 0.1, frac_b: float = 0.5) -> dict:
    """
    Geweke (1992) convergence diagnostic.

    Compares the mean of the first frac_a of the chain to the last frac_b.
    Under convergence, the test statistic is standard normal.
    """
    n = len(chain)
    n_a = int(n * frac_a)
    n_b = int(n * frac_b)

    if n_a < 2 or n_b < 2:
        return {"z_score": np.nan, "p_value": np.nan}

    a = chain[:n_a]
    b = chain[-n_b:]

    mean_a, mean_b = np.mean(a), np.mean(b)
    var_a, var_b = np.var(a, ddof=1), np.var(b, ddof=1)

    se = np.sqrt(var_a / n_a + var_b / n_b)
    if se < 1e-15:
        return {"z_score": 0.0, "p_value": 1.0}

    z = (mean_a - mean_b) / se
    from scipy.stats import norm
    p = 2 * (1 - norm.cdf(abs(z)))

    return {"z_score": z, "p_value": p}


def compute_rhat(chains: list[np.ndarray]) -> float:
    """
    Gelman-Rubin R-hat statistic for multiple chains.

    Values close to 1.0 indicate convergence.
    Requires at least 2 chains.
    """
    m = len(chains)
    if m < 2:
        return np.nan

    n = min(len(c) for c in chains)
    chains = [c[:n] for c in chains]

    chain_means = np.array([np.mean(c) for c in chains])
    grand_mean = np.mean(chain_means)

    # Between-chain variance
    B = n / (m - 1) * np.sum((chain_means - grand_mean) ** 2)

    # Within-chain variance
    W = np.mean([np.var(c, ddof=1) for c in chains])

    if W < 1e-15:
        return 1.0

    var_hat = (1 - 1 / n) * W + (1 / n) * B
    rhat = np.sqrt(var_hat / W)

    return rhat


# ═══════════════════════════════════════════════════════════════════════════
# Quantile condition checks
# ═══════════════════════════════════════════════════════════════════════════

def check_quantile_conditions(
    residual_draws: np.ndarray,
    tau: np.ndarray,
    tolerance: float = 0.05,
) -> dict:
    """
    Check that residuals satisfy quantile conditions.

    For each posterior draw, verify that the fraction of negative residuals
    is approximately equal to the quantile level tau for each variable.

    Parameters
    ----------
    residual_draws : (n_draws, T, k) posterior residual draws.
    tau : (k,) quantile levels.
    tolerance : Acceptable deviation from tau.

    Returns
    -------
    Dictionary with fraction of draws passing the check per variable.
    """
    n_draws, T, k = residual_draws.shape
    pass_rates = np.zeros(k)

    for j in range(k):
        passes = 0
        for i in range(n_draws):
            frac_negative = np.mean(residual_draws[i, :, j] < 0)
            if abs(frac_negative - tau[j]) < tolerance:
                passes += 1
        pass_rates[j] = passes / n_draws

    return {
        "pass_rates": pass_rates,
        "tau": tau,
        "tolerance": tolerance,
        "all_pass": np.all(pass_rates > 0.8),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Comprehensive diagnostics
# ═══════════════════════════════════════════════════════════════════════════

def run_diagnostics(estimation_result: dict) -> dict:
    """
    Run comprehensive MCMC diagnostics on the estimation output.

    Parameters
    ----------
    estimation_result : Output from BayesianQVAR.estimate().

    Returns
    -------
    Dictionary with all diagnostic results.
    """
    beta_draws = estimation_result["beta_draws"]
    residual_draws = estimation_result["residual_draws"]
    tau = estimation_result["tau"]
    k = estimation_result["k"]
    n_draws = estimation_result["n_draws"]
    var_names = estimation_result["var_names"]

    diagnostics = {
        "n_draws": n_draws,
        "tau": tau.tolist(),
        "var_names": var_names,
    }

    # 1. ESS for each coefficient
    n_params = beta_draws.shape[1]
    ess_values = np.array([
        effective_sample_size(beta_draws[:, j]) for j in range(n_params)
    ])
    diagnostics["ess"] = {
        "min": float(np.min(ess_values)),
        "median": float(np.median(ess_values)),
        "max": float(np.max(ess_values)),
        "values": ess_values.tolist(),
    }

    # 2. Geweke test for a subset of key coefficients
    n_check = min(20, n_params)
    indices = np.linspace(0, n_params - 1, n_check, dtype=int)
    geweke_results = []
    for j in indices:
        gt = geweke_test(beta_draws[:, j])
        geweke_results.append({
            "param_idx": int(j),
            "z_score": float(gt["z_score"]),
            "p_value": float(gt["p_value"]),
        })
    diagnostics["geweke"] = geweke_results
    diagnostics["geweke_pass_rate"] = np.mean(
        [g["p_value"] > 0.05 for g in geweke_results if not np.isnan(g["p_value"])]
    )

    # 3. Quantile conditions
    diagnostics["quantile_conditions"] = check_quantile_conditions(
        residual_draws, tau)

    # 4. MH acceptance rate
    diagnostics["mh_acceptance_rate"] = estimation_result.get(
        "mh_acceptance_rate", np.nan)

    # 5. Stationarity: fraction of posterior draws that are stationary
    lags = estimation_result["lags"]
    n_reg = estimation_result.get("n_regressors", beta_draws.shape[1] // k)
    n_stationary = 0
    for i in range(n_draws):
        B_tau = beta_draws[i].reshape(n_reg, k)
        B_lag = B_tau[1:, :].T  # (k, k*p)
        companion = np.zeros((k * lags, k * lags))
        companion[:k, :] = B_lag
        if lags > 1:
            companion[k:, :k * (lags - 1)] = np.eye(k * (lags - 1))
        eigvals = np.linalg.eigvals(companion)
        if np.all(np.abs(eigvals) < 1.0):
            n_stationary += 1
    diagnostics["stationarity_rate"] = n_stationary / n_draws

    # 6. Posterior summary for coefficients
    coef_summary = {
        "posterior_mean": np.mean(beta_draws, axis=0).tolist(),
        "posterior_median": np.median(beta_draws, axis=0).tolist(),
        "posterior_std": np.std(beta_draws, axis=0).tolist(),
        "posterior_q16": np.percentile(beta_draws, 16, axis=0).tolist(),
        "posterior_q84": np.percentile(beta_draws, 84, axis=0).tolist(),
    }
    diagnostics["coefficient_summary"] = coef_summary

    return diagnostics


# ═══════════════════════════════════════════════════════════════════════════
# Results storage
# ═══════════════════════════════════════════════════════════════════════════

def save_results(
    estimation_result: dict,
    diagnostics: dict,
    irf_results: dict,
    output_dir: str,
    prefix: str = "qvar",
) -> dict:
    """
    Save estimation results, diagnostics, and IRFs to disk.

    Parameters
    ----------
    estimation_result : Output from BayesianQVAR.estimate().
    diagnostics : Output from run_diagnostics().
    irf_results : Output from compute_bayesian_qirfs_*.
    output_dir : Directory to save files.
    prefix : Filename prefix.

    Returns
    -------
    Dictionary with paths to saved files.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    saved_files = {}

    # 1. Posterior draws (numpy)
    np.savez_compressed(
        os.path.join(output_dir, f"{prefix}_posterior_draws.npz"),
        beta_draws=estimation_result["beta_draws"],
        Sigma_draws=estimation_result["Sigma_draws"],
        C_draws=estimation_result["C_draws"],
        residual_draws=estimation_result["residual_draws"],
        tau=estimation_result["tau"],
    )
    saved_files["posterior_draws"] = os.path.join(
        output_dir, f"{prefix}_posterior_draws.npz")

    # 2. Diagnostics (JSON-safe)
    diag_safe = _make_json_safe(diagnostics)
    with open(os.path.join(output_dir, f"{prefix}_diagnostics.json"), "w") as f:
        json.dump(diag_safe, f, indent=2)
    saved_files["diagnostics"] = os.path.join(
        output_dir, f"{prefix}_diagnostics.json")

    # 3. IRFs (numpy)
    irf_save = {}
    if "median" in irf_results:
        irf_save["median"] = irf_results["median"]
        for q, arr in irf_results.get("bands", {}).items():
            irf_save[f"band_{q}"] = arr
    elif "shocks" in irf_results:
        for shock_idx, shock_data in irf_results["shocks"].items():
            irf_save[f"shock{shock_idx}_median"] = shock_data["median"]
            for q, arr in shock_data.get("bands", {}).items():
                irf_save[f"shock{shock_idx}_band_{q}"] = arr

    np.savez_compressed(
        os.path.join(output_dir, f"{prefix}_irfs.npz"),
        **irf_save,
    )
    saved_files["irfs"] = os.path.join(output_dir, f"{prefix}_irfs.npz")

    # 4. Model specification
    spec = {
        "tau": estimation_result["tau"].tolist(),
        "lags": estimation_result["lags"],
        "k": estimation_result["k"],
        "var_names": estimation_result["var_names"],
        "T_eff": estimation_result["T_eff"],
        "n_draws": estimation_result["n_draws"],
    }
    with open(os.path.join(output_dir, f"{prefix}_spec.json"), "w") as f:
        json.dump(spec, f, indent=2)
    saved_files["specification"] = os.path.join(
        output_dir, f"{prefix}_spec.json")

    return saved_files


def _make_json_safe(obj):
    """Convert numpy types to native Python for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_safe(v) for v in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    return obj
