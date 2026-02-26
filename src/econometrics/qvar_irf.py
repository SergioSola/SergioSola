"""
Quantile Impulse Response Functions (QIRFs) for the Bayesian QVAR.

Implements:
  - QIRFs following Beutel et al. (2025, JIMF) / Schüler (2020)
  - Path-dependent QIRFs with quantile-specific propagation
  - Bayesian credible bands from posterior draws
  - Forecast Error Variance Decomposition (FEVD) at quantiles

The key feature: the QVAR allows different coefficient matrices B_tau
for different quantiles tau. The QIRF traces how a structural shock
propagates through the system when the conditional distribution of
the response variable is at a specific quantile (e.g., 10% for tail risk).

QIRF(h, U*, tau_{t:t+h}) = B_{tau_{t+h}} @ B_{tau_{t+h-1}} @ ... @ B_{tau_{t+1}} @ U*

When tau is constant across horizons, this simplifies to:
    QIRF(h, U*, tau) = B_tau^h @ U*
"""

from __future__ import annotations

import numpy as np
from typing import Optional

from .identification import (
    cholesky_identification,
    compute_shock_vector,
    sign_restriction_identification,
    draw_orthogonal_matrix,
    check_sign_restrictions,
    _compute_irfs_for_rotation,
)


# ═══════════════════════════════════════════════════════════════════════════
# Core QIRF computation
# ═══════════════════════════════════════════════════════════════════════════

def compute_qirf(
    companion: np.ndarray,
    shock_vector: np.ndarray,
    k: int,
    horizon: int = 20,
) -> np.ndarray:
    """
    Compute QIRF for a constant quantile path.

    QIRF(h) = B_tau^h @ U*  (from Eq. 7 in the paper)

    Parameters
    ----------
    companion : (kp, kp) companion-form matrix for quantile tau.
    shock_vector : (k,) structural shock vector u*.
    k : Number of endogenous variables.
    horizon : IRF horizon.

    Returns
    -------
    (horizon+1, k) array of impulse responses.
    """
    dim = companion.shape[0]
    irfs = np.zeros((horizon + 1, k))

    # Initial shock in companion-form dimension
    U_star = np.zeros(dim)
    U_star[:k] = shock_vector

    # h = 0
    irfs[0] = U_star[:k]

    # h >= 1
    power = np.eye(dim)
    for h in range(1, horizon + 1):
        power = power @ companion
        state = power @ U_star
        irfs[h] = state[:k]

    return irfs


def compute_qirf_varying_quantile(
    companions: dict,
    shock_vector: np.ndarray,
    tau_path: list[float],
    k: int,
) -> np.ndarray:
    """
    Compute QIRF with a time-varying quantile path (Eq. 8).

    QIRF(h) = B_{tau_{t+h}} @ B_{tau_{t+h-1}} @ ... @ B_{tau_{t+1}} @ U*

    This allows, e.g., GDP to be at Q10% for 2 quarters then revert to Q50%.

    Parameters
    ----------
    companions : Dictionary mapping quantile -> companion matrix.
        E.g., {0.1: companion_q10, 0.5: companion_q50}
    shock_vector : (k,) structural shock vector.
    tau_path : List of quantile values for each horizon [tau_{t+1}, ..., tau_{t+H}].
    k : Number of variables.

    Returns
    -------
    (len(tau_path)+1, k) array of impulse responses.
    """
    horizon = len(tau_path)
    dim = list(companions.values())[0].shape[0]
    irfs = np.zeros((horizon + 1, k))

    U_star = np.zeros(dim)
    U_star[:k] = shock_vector
    irfs[0] = U_star[:k]

    state = U_star.copy()
    for h in range(1, horizon + 1):
        tau_h = tau_path[h - 1]
        # Find closest available companion
        available_taus = sorted(companions.keys())
        closest_tau = min(available_taus, key=lambda t: abs(t - tau_h))
        B_h = companions[closest_tau]
        state = B_h @ state
        irfs[h] = state[:k]

    return irfs


# ═══════════════════════════════════════════════════════════════════════════
# Bayesian QIRFs with credible bands (from posterior draws)
# ═══════════════════════════════════════════════════════════════════════════

def compute_bayesian_qirfs_cholesky(
    estimation_result: dict,
    shock_idx: int = 0,
    shock_size: float = 1.0,
    horizon: int = 20,
    credible_levels: tuple[float, ...] = (0.16, 0.84),
) -> dict:
    """
    Compute QIRFs with Bayesian credible bands using Cholesky identification.

    For each posterior draw of (beta, Sigma), computes:
    1. Companion matrix from the draw
    2. Co-exceedance matrix from the draw's residuals
    3. Cholesky factor P_tau
    4. Shock vector u* = P_tau @ e_{shock_idx} * shock_size
    5. QIRF

    Credible bands are constructed directly from the distribution of QIRFs
    across posterior draws (no bootstrap needed).

    Parameters
    ----------
    estimation_result : Output from BayesianQVAR.estimate().
    shock_idx : Index of structural shock.
    shock_size : Size of the shock (e.g., 1.0 for unit, or 1 std dev).
    horizon : IRF horizon.
    credible_levels : Quantiles for credible bands (default: 68% bands).

    Returns
    -------
    Dictionary with:
      - median: (horizon+1, k) median QIRF
      - bands: dict of quantile level -> (horizon+1, k) array
      - all_irfs: (n_draws, horizon+1, k) all QIRF draws
    """
    beta_draws = estimation_result["beta_draws"]
    residual_draws = estimation_result["residual_draws"]
    tau = estimation_result["tau"]
    k = estimation_result["k"]
    lags = estimation_result["lags"]
    n_draws = estimation_result["n_draws"]
    n_reg = beta_draws.shape[1] // k

    all_irfs = np.zeros((n_draws, horizon + 1, k))

    n_reg = estimation_result.get("n_regressors", beta_draws.shape[1] // k)

    for i in range(n_draws):
        B_tau = beta_draws[i].reshape(n_reg, k)

        # Build companion: B_tau is (n_reg, k), lag part is B_tau[1:,:].T = (k, k*p)
        B_lag = B_tau[1:, :].T  # (k, k*p)
        companion = np.zeros((k * lags, k * lags))
        companion[:k, :] = B_lag
        if lags > 1:
            companion[k:, :k * (lags - 1)] = np.eye(k * (lags - 1))

        # Identification
        residuals = residual_draws[i]
        try:
            id_result = cholesky_identification(residuals, tau)
            P_tau = id_result["P_tau"]
        except (np.linalg.LinAlgError, ValueError):
            all_irfs[i] = np.nan
            continue

        # Shock vector
        u_star = compute_shock_vector(P_tau, shock_idx, shock_size)

        # QIRF
        all_irfs[i] = compute_qirf(companion, u_star, k, horizon)

    # Remove NaN draws
    valid_mask = ~np.any(np.isnan(all_irfs.reshape(n_draws, -1)), axis=1)
    valid_irfs = all_irfs[valid_mask]

    if len(valid_irfs) == 0:
        raise RuntimeError("No valid posterior QIRF draws obtained.")

    median_irfs = np.median(valid_irfs, axis=0)
    bands = {}
    for q in credible_levels:
        bands[q] = np.percentile(valid_irfs, q * 100, axis=0)

    return {
        "median": median_irfs,
        "bands": bands,
        "all_irfs": valid_irfs,
        "n_valid": len(valid_irfs),
        "n_total": n_draws,
        "horizon": horizon,
        "shock_idx": shock_idx,
        "shock_size": shock_size,
        "var_names": estimation_result["var_names"],
    }


def compute_bayesian_qirfs_sign_restrictions(
    estimation_result: dict,
    sign_restrictions: dict,
    horizon: int = 20,
    n_rotations_per_draw: int = 200,
    max_horizon_check: int = 0,
    credible_levels: tuple[float, ...] = (0.16, 0.84),
    seed: int = 42,
    max_posterior_draws: Optional[int] = None,
) -> dict:
    """
    Compute QIRFs with sign restriction identification.

    For each posterior draw:
    1. Compute Cholesky of co-exceedance matrix
    2. Draw rotation matrices Q and check sign restrictions
    3. Store accepted IRFs

    The set of accepted IRFs across all draws forms the identified set,
    from which credible bands are computed.

    Parameters
    ----------
    estimation_result : Output from BayesianQVAR.estimate().
    sign_restrictions : Sign restriction dictionary.
    horizon : IRF horizon.
    n_rotations_per_draw : Number of Q draws per posterior draw.
    max_horizon_check : Maximum horizon for sign restriction checks.
    credible_levels : Quantiles for credible bands.
    seed : Random seed.
    max_posterior_draws : Limit on posterior draws to use (for speed).

    Returns
    -------
    Dictionary with median QIRFs, bands, and all accepted draws.
    """
    rng = np.random.default_rng(seed)
    beta_draws = estimation_result["beta_draws"]
    residual_draws = estimation_result["residual_draws"]
    tau = estimation_result["tau"]
    k = estimation_result["k"]
    lags = estimation_result["lags"]
    n_draws = estimation_result["n_draws"]
    n_reg = beta_draws.shape[1] // k

    n_reg = estimation_result.get("n_regressors", beta_draws.shape[1] // k)

    if max_posterior_draws is not None:
        n_draws = min(n_draws, max_posterior_draws)

    all_accepted = []  # List of (horizon+1, k, k) IRF arrays

    for i in range(n_draws):
        B_tau = beta_draws[i].reshape(n_reg, k)

        # Build companion: B_tau is (n_reg, k)
        B_lag = B_tau[1:, :].T  # (k, k*p)
        companion = np.zeros((k * lags, k * lags))
        companion[:k, :] = B_lag
        if lags > 1:
            companion[k:, :k * (lags - 1)] = np.eye(k * (lags - 1))

        # Cholesky of co-exceedance
        residuals = residual_draws[i]
        try:
            id_result = cholesky_identification(residuals, tau)
            P_tau = id_result["P_tau"]
        except (np.linalg.LinAlgError, ValueError):
            continue

        # Try rotations
        for _ in range(n_rotations_per_draw):
            Q = draw_orthogonal_matrix(k, rng)
            A0 = P_tau @ Q
            irfs = _compute_irfs_for_rotation(A0, companion, k, horizon)

            if check_sign_restrictions(
                irfs, sign_restrictions, max_horizon_check
            ):
                all_accepted.append(irfs)

    n_accepted = len(all_accepted)
    if n_accepted == 0:
        raise RuntimeError(
            "No rotation draws satisfied sign restrictions. "
            "Consider relaxing restrictions or increasing n_rotations_per_draw."
        )

    all_accepted = np.array(all_accepted)  # (n_accepted, horizon+1, k, k)

    # Compute summary statistics for each shock
    result = {
        "n_accepted": n_accepted,
        "n_posterior_draws_used": n_draws,
        "n_rotations_per_draw": n_rotations_per_draw,
        "sign_restrictions": sign_restrictions,
        "horizon": horizon,
        "var_names": estimation_result["var_names"],
        "shocks": {},
    }

    for shock_idx in range(k):
        irfs_this_shock = all_accepted[:, :, :, shock_idx]  # (n_acc, H+1, k)
        median_irfs = np.median(irfs_this_shock, axis=0)
        bands = {}
        for q in credible_levels:
            bands[q] = np.percentile(irfs_this_shock, q * 100, axis=0)

        result["shocks"][shock_idx] = {
            "median": median_irfs,
            "bands": bands,
            "all_irfs": irfs_this_shock,
        }

    return result


# ═══════════════════════════════════════════════════════════════════════════
# FEVD at quantiles
# ═══════════════════════════════════════════════════════════════════════════

def compute_qvar_fevd(
    companion: np.ndarray,
    P_tau: np.ndarray,
    k: int,
    horizon: int = 20,
) -> np.ndarray:
    """
    Forecast Error Variance Decomposition from the quantile VAR.

    FEVD_{i,j}(h) = sum_{s=0}^{h} (e_i' Phi_s P_tau e_j)^2
                    / sum_{s=0}^{h} (e_i' Phi_s Omega_tau Phi_s' e_i)

    Parameters
    ----------
    companion : (kp, kp) companion matrix.
    P_tau : (k, k) Cholesky factor of co-exceedance matrix.
    k : Number of variables.
    horizon : FEVD horizon.

    Returns
    -------
    (k, k) FEVD matrix where entry (i,j) = fraction of variable i's
    forecast error variance due to shock j at horizon h.
    """
    dim = companion.shape[0]
    Omega = P_tau @ P_tau.T
    fevd = np.zeros((k, k))

    numerator = np.zeros((k, k))
    denominator = np.zeros(k)

    power = np.eye(dim)
    for s in range(horizon + 1):
        if s > 0:
            power = power @ companion
        Phi_s = power[:k, :k]

        # For each shock j, response of variable i
        response = Phi_s @ P_tau  # (k, k)
        numerator += response ** 2

        # Total variance
        total = Phi_s @ Omega @ Phi_s.T
        denominator += np.diag(total)

    for i in range(k):
        if denominator[i] > 0:
            fevd[i, :] = numerator[i, :] / denominator[i]

    return fevd
