"""
Structural identification schemes for the Bayesian QVAR.

Implements:
  1. Cholesky decomposition of the co-exceedance matrix (Schüler 2020,
     Beutel et al. 2025) — the baseline approach in the JIMF paper
  2. Sign restrictions via QR decomposition (Rubio-Ramírez, Waggoner & Zha
     2010; Arias, Rubio-Ramírez & Waggoner 2018)

The co-exceedance matrix Omega_tau replaces the standard covariance matrix
for orthogonalization in quantile VARs. It captures the co-variation of
residuals around their respective quantiles using the psi-operator:
    psi_{tau_i}(u_{it|tau_i}) = tau_i - 1(u_{it|tau_i} < 0)
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import cholesky, qr
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════
# Co-exceedance matrix (Eq. 9 in the paper)
# ═══════════════════════════════════════════════════════════════════════════

def psi_operator(residuals: np.ndarray, tau: np.ndarray) -> np.ndarray:
    """
    Apply the psi-operator to residuals.

    psi_{tau_i}(u_{it}) = tau_i - 1(u_{it} < 0)

    Parameters
    ----------
    residuals : (T, k) array of quantile VAR residuals.
    tau : (k,) vector of quantile levels.

    Returns
    -------
    (T, k) array of psi-transformed residuals.
    """
    indicator = (residuals < 0).astype(np.float64)
    return tau[np.newaxis, :] - indicator


def estimate_density_at_zero(residuals: np.ndarray, bandwidth: str = "silverman") -> np.ndarray:
    """
    Estimate f_{u_{it|tau_i}}(0) for each variable using kernel density estimation.

    Parameters
    ----------
    residuals : (T, k) array of residuals.
    bandwidth : Bandwidth selection method.

    Returns
    -------
    (k,) array of density values at zero.
    """
    T, k = residuals.shape
    f_at_zero = np.zeros(k)

    for i in range(k):
        u = residuals[:, i]
        std = np.std(u)
        if std < 1e-12:
            f_at_zero[i] = 1.0
            continue

        # Silverman's rule of thumb
        iqr = np.percentile(u, 75) - np.percentile(u, 25)
        h = 0.9 * min(std, iqr / 1.34) * T ** (-0.2)
        if h < 1e-12:
            h = std * T ** (-0.2)

        # Gaussian kernel density at 0
        kernel_vals = np.exp(-0.5 * (u / h) ** 2) / (h * np.sqrt(2 * np.pi))
        f_at_zero[i] = np.mean(kernel_vals)

    return f_at_zero


def compute_coexceedance_matrix(
    residuals: np.ndarray,
    tau: np.ndarray,
) -> np.ndarray:
    """
    Compute the co-exceedance matrix Omega_tau (Eq. 9).

    Omega_tau(i,j) = E[psi_{tau_i}(u_it) * psi_{tau_j}(u_jt)]
                     / (f_{u_it}(0) * f_{u_jt}(0))

    Parameters
    ----------
    residuals : (T, k) array of quantile VAR residuals.
    tau : (k,) vector of quantile levels.

    Returns
    -------
    (k, k) co-exceedance matrix.
    """
    T, k = residuals.shape
    psi = psi_operator(residuals, tau)
    f_zero = estimate_density_at_zero(residuals)

    # Normalize psi by density at zero
    psi_tilde = psi / f_zero[np.newaxis, :]  # (T, k)

    # Co-exceedance matrix
    Omega = (psi_tilde.T @ psi_tilde) / T

    return Omega


# ═══════════════════════════════════════════════════════════════════════════
# 1. Cholesky identification (Eqs. 10-11 in the paper)
# ═══════════════════════════════════════════════════════════════════════════

def cholesky_identification(
    residuals: np.ndarray,
    tau: np.ndarray,
) -> dict:
    """
    Identify structural shocks using Cholesky decomposition of
    the co-exceedance matrix.

    Omega_tau = P_tau P_tau'
    epsilon_{t|tau} = P_tau^{-1} psi_tilde(u_{t|tau})

    The variable ordering determines the recursive causal structure.
    Variables ordered first can affect all others contemporaneously;
    variables ordered last are affected by all others contemporaneously.

    Parameters
    ----------
    residuals : (T, k) array of reduced-form residuals.
    tau : (k,) vector of quantile levels.

    Returns
    -------
    Dictionary with:
      - P_tau: Lower-triangular Cholesky factor (k, k)
      - Omega_tau: Co-exceedance matrix (k, k)
      - structural_shocks: (T, k) identified structural shocks
      - f_at_zero: density estimates at zero
    """
    Omega = compute_coexceedance_matrix(residuals, tau)

    # Ensure positive definiteness
    eigvals = np.linalg.eigvalsh(Omega)
    if np.any(eigvals <= 0):
        # Regularize
        min_eig = np.min(eigvals)
        Omega += (-min_eig + 1e-6) * np.eye(Omega.shape[0])

    P_tau = cholesky(Omega, lower=True)
    P_tau_inv = np.linalg.inv(P_tau)

    # Structural shocks
    psi = psi_operator(residuals, tau)
    f_zero = estimate_density_at_zero(residuals)
    psi_tilde = psi / f_zero[np.newaxis, :]
    structural_shocks = (P_tau_inv @ psi_tilde.T).T

    return {
        "P_tau": P_tau,
        "P_tau_inv": P_tau_inv,
        "Omega_tau": Omega,
        "structural_shocks": structural_shocks,
        "f_at_zero": f_zero,
    }


def compute_shock_vector(
    P_tau: np.ndarray,
    shock_idx: int,
    shock_size: float = 1.0,
) -> np.ndarray:
    """
    Compute the reduced-form shock vector u* for a unit structural shock.

    u* = P_tau @ (delta, 0, ..., 0)' when shocking variable shock_idx.

    Following Eq. 11 in the paper.
    """
    k = P_tau.shape[0]
    eps = np.zeros(k)
    eps[shock_idx] = shock_size
    return P_tau @ eps


# ═══════════════════════════════════════════════════════════════════════════
# 2. Sign restrictions (Arias, Rubio-Ramírez & Waggoner 2018)
# ═══════════════════════════════════════════════════════════════════════════

def draw_orthogonal_matrix(k: int, rng: np.random.Generator) -> np.ndarray:
    """
    Draw a uniformly distributed orthogonal matrix Q from O(k).

    Uses the QR decomposition of a random standard normal matrix,
    following Rubio-Ramírez, Waggoner & Zha (2010) / Stewart (1980).

    The diagonal of R is normalized to be positive to ensure uniqueness.

    Parameters
    ----------
    k : Dimension.
    rng : NumPy random generator.

    Returns
    -------
    (k, k) orthogonal matrix Q.
    """
    Z = rng.standard_normal((k, k))
    Q, R = qr(Z)

    # Normalize: make diagonal of R positive
    signs = np.sign(np.diag(R))
    signs[signs == 0] = 1.0
    Q = Q * signs[np.newaxis, :]

    return Q


def check_sign_restrictions(
    irfs: np.ndarray,
    sign_restrictions: dict,
    horizon_check: int = 0,
) -> bool:
    """
    Check if impulse responses satisfy sign restrictions.

    Parameters
    ----------
    irfs : (horizon+1, k, k) array of impulse responses.
           irfs[h, i, j] = response of variable i to shock j at horizon h.
    sign_restrictions : Dictionary specifying restrictions.
        Keys: (shock_idx, response_var_idx, horizon) tuples.
        Values: +1 for positive restriction, -1 for negative restriction.
        Example: {(0, 1, 0): -1} means "shock 0 should decrease variable 1
                 at horizon 0".
    horizon_check : Maximum horizon to check restrictions at.
        If 0, only impact restrictions are checked.

    Returns
    -------
    True if all restrictions are satisfied.
    """
    for (shock_idx, var_idx, h), sign in sign_restrictions.items():
        if h > horizon_check:
            continue
        if h >= irfs.shape[0]:
            continue
        response = irfs[h, var_idx, shock_idx]
        if sign > 0 and response <= 0:
            return False
        if sign < 0 and response >= 0:
            return False
    return True


def sign_restriction_identification(
    residuals: np.ndarray,
    tau: np.ndarray,
    sign_restrictions: dict,
    companion: np.ndarray,
    n_rotations: int = 5000,
    max_horizon_check: int = 0,
    seed: int = 42,
) -> dict:
    """
    Identify structural shocks using sign restrictions.

    Algorithm (following Arias, Rubio-Ramírez & Waggoner 2018):
    1. Compute Cholesky factor P_tau of co-exceedance matrix
    2. Draw random orthogonal matrix Q from uniform distribution over O(k)
    3. Candidate impact matrix: A0 = P_tau @ Q
    4. Compute IRFs using A0 and check sign restrictions
    5. Accept if restrictions satisfied, reject otherwise
    6. Repeat until enough accepted draws

    Parameters
    ----------
    residuals : (T, k) reduced-form residuals.
    tau : (k,) quantile levels.
    sign_restrictions : Dictionary of sign restrictions.
        Keys: (shock_idx, response_var_idx, horizon).
        Values: +1 or -1.
    companion : Companion matrix from QVAR.
    n_rotations : Maximum number of rotation draws to try.
    max_horizon_check : Maximum horizon for checking sign restrictions.
    seed : Random seed.

    Returns
    -------
    Dictionary with accepted rotations and their IRFs.
    """
    rng = np.random.default_rng(seed)
    k = residuals.shape[1]

    # Get Cholesky factor
    chol_result = cholesky_identification(residuals, tau)
    P_tau = chol_result["P_tau"]

    accepted_rotations = []
    accepted_irfs = []

    dim = companion.shape[0]
    max_h = max(
        (h for (_, _, h) in sign_restrictions.keys()),
        default=0,
    )
    max_h = max(max_h, max_horizon_check)

    for _ in range(n_rotations):
        Q = draw_orthogonal_matrix(k, rng)
        A0 = P_tau @ Q

        # Compute IRFs with this rotation
        irfs = _compute_irfs_for_rotation(
            A0, companion, k, max_h)

        if check_sign_restrictions(irfs, sign_restrictions, max_h):
            accepted_rotations.append(Q)
            accepted_irfs.append(irfs)

    n_accepted = len(accepted_rotations)

    return {
        "P_tau": P_tau,
        "Omega_tau": chol_result["Omega_tau"],
        "n_accepted": n_accepted,
        "n_tried": n_rotations,
        "acceptance_rate": n_accepted / n_rotations if n_rotations > 0 else 0,
        "accepted_rotations": accepted_rotations,
        "accepted_irfs": accepted_irfs,
        "sign_restrictions": sign_restrictions,
    }


def _compute_irfs_for_rotation(
    A0: np.ndarray,
    companion: np.ndarray,
    k: int,
    max_horizon: int,
) -> np.ndarray:
    """
    Compute IRFs given impact matrix A0 and companion matrix.

    Parameters
    ----------
    A0 : (k, k) impact matrix.
    companion : (kp, kp) companion matrix.
    k : Number of variables.
    max_horizon : Maximum horizon.

    Returns
    -------
    (max_horizon+1, k, k) array of IRFs.
    """
    dim = companion.shape[0]
    irfs = np.zeros((max_horizon + 1, k, k))

    # Impact (h=0)
    irfs[0] = A0

    # Propagation
    power = np.eye(dim)
    for h in range(1, max_horizon + 1):
        power = power @ companion
        Phi_h = power[:k, :k]
        irfs[h] = Phi_h @ A0

    return irfs


# ═══════════════════════════════════════════════════════════════════════════
# Combined identification interface
# ═══════════════════════════════════════════════════════════════════════════

def identify_shocks(
    residuals: np.ndarray,
    tau: np.ndarray,
    method: str = "cholesky",
    companion: Optional[np.ndarray] = None,
    sign_restrictions: Optional[dict] = None,
    **kwargs,
) -> dict:
    """
    Unified interface for structural identification.

    Parameters
    ----------
    residuals : (T, k) reduced-form residuals.
    tau : (k,) quantile levels.
    method : "cholesky" or "sign_restrictions".
    companion : Required for sign restrictions.
    sign_restrictions : Required for sign restrictions method.
    **kwargs : Additional arguments passed to the specific method.

    Returns
    -------
    Identification results dictionary.
    """
    if method == "cholesky":
        return cholesky_identification(residuals, tau)

    elif method == "sign_restrictions":
        if companion is None:
            raise ValueError("companion matrix required for sign restrictions")
        if sign_restrictions is None:
            raise ValueError("sign_restrictions dict required")
        return sign_restriction_identification(
            residuals, tau, sign_restrictions, companion, **kwargs)

    else:
        raise ValueError(f"Unknown identification method: {method}")
