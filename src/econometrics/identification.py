"""
Structural identification schemes for the Bayesian QVAR.

Implements:
  1. Cholesky decomposition of the co-exceedance matrix (Schüler 2020,
     Beutel et al. 2025) — the baseline approach in the JIMF paper
  2. Sign restrictions via QR decomposition (Rubio-Ramírez, Waggoner & Zha
     2010)
  3. Zero and sign restrictions via the column-by-column null-space algorithm
     (Arias, Rubio-Ramírez & Waggoner 2018, Econometrica)

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
# 3. Zero and sign restrictions (Arias, Rubio-Ramírez & Waggoner 2018)
# ═══════════════════════════════════════════════════════════════════════════

def _build_zero_restriction_matrices(
    zero_restrictions: dict,
    k: int,
    P_tau: np.ndarray,
    companion: np.ndarray,
) -> dict[int, np.ndarray]:
    """
    Build the zero-restriction matrix Z_j for each shock j.

    For shock j, Z_j collects rows such that Z_j @ (P_tau @ q_j) = 0,
    meaning the IRF of certain variables to shock j is exactly zero.

    Parameters
    ----------
    zero_restrictions : Dict with keys (shock_idx, response_var_idx, horizon)
        and values 0 (for zero restriction).
    k : Number of variables.
    P_tau : (k, k) Cholesky factor.
    companion : (kp, kp) companion matrix.

    Returns
    -------
    Dict mapping shock_idx -> (n_zeros_j, k) restriction matrix.
    """
    dim = companion.shape[0]

    # Group zero restrictions by shock
    restrictions_by_shock: dict[int, list] = {}
    for (shock_idx, var_idx, h), val in zero_restrictions.items():
        if shock_idx not in restrictions_by_shock:
            restrictions_by_shock[shock_idx] = []
        restrictions_by_shock[shock_idx].append((var_idx, h))

    Z_matrices = {}
    for shock_idx, var_horizon_pairs in restrictions_by_shock.items():
        rows = []
        for var_idx, h in var_horizon_pairs:
            # e_i' @ Phi_h @ P_tau @ q_j = 0
            # => (e_i' @ Phi_h @ P_tau) @ q_j = 0
            # This row constrains q_j
            e_i = np.zeros(k)
            e_i[var_idx] = 1.0

            if h == 0:
                Phi_h = np.eye(k)
            else:
                power = np.linalg.matrix_power(companion, h)
                Phi_h = power[:k, :k]

            row = e_i @ Phi_h @ P_tau  # (k,) — a row constraining q_j
            rows.append(row)

        Z_matrices[shock_idx] = np.array(rows)  # (n_zeros_j, k)

    return Z_matrices


def draw_orthogonal_column_in_nullspace(
    Z_j: Optional[np.ndarray],
    prev_columns: list[np.ndarray],
    k: int,
    rng: np.random.Generator,
) -> Optional[np.ndarray]:
    """
    Draw a random unit vector in the intersection of:
      (a) the null space of Z_j (zero restrictions for shock j)
      (b) the orthogonal complement of previously drawn columns

    This is the core of the Arias et al. (2018) column-by-column algorithm.

    Parameters
    ----------
    Z_j : (n_zeros_j, k) zero-restriction matrix for shock j, or None.
    prev_columns : List of previously drawn (k,) column vectors.
    k : Dimension.
    rng : Random generator.

    Returns
    -------
    (k,) unit vector, or None if the subspace is empty.
    """
    # Start with the full space
    constraints = []

    # Add zero-restriction rows
    if Z_j is not None and Z_j.shape[0] > 0:
        constraints.append(Z_j)

    # Add orthogonality constraints from previous columns
    if prev_columns:
        constraints.append(np.array(prev_columns))

    if constraints:
        C = np.vstack(constraints)  # (m, k) where m = n_zeros + n_prev
    else:
        C = np.zeros((0, k))

    if C.shape[0] >= k:
        # No degrees of freedom left — subspace is trivial or empty
        return None

    if C.shape[0] == 0:
        # No constraints: draw uniformly on the unit sphere
        x = rng.standard_normal(k)
        return x / np.linalg.norm(x)

    # Find the null space of C: the subspace where q_j must lie
    # C @ q_j = 0  =>  q_j in null(C)
    U, S, Vt = np.linalg.svd(C, full_matrices=True)
    # Null space = rows of Vt corresponding to zero (or near-zero) singular values
    rank = np.sum(S > 1e-10)
    null_basis = Vt[rank:].T  # (k, d) where d = k - rank

    d = null_basis.shape[1]
    if d == 0:
        return None

    # Draw uniformly on the d-dimensional unit sphere within the null space
    x = rng.standard_normal(d)
    x = x / np.linalg.norm(x)

    # Map back to k-dimensional space
    q_j = null_basis @ x
    return q_j


def draw_orthogonal_matrix_with_zeros(
    k: int,
    zero_restriction_matrices: dict[int, np.ndarray],
    rng: np.random.Generator,
) -> Optional[np.ndarray]:
    """
    Draw an orthogonal matrix Q column by column, respecting zero restrictions.

    Algorithm (Arias, Rubio-Ramírez & Waggoner 2018, Algorithm 2):
    For j = 1, ..., k:
      1. Let N_j = null(Z_j) intersected with orth(q_1, ..., q_{j-1})
      2. Draw q_j uniformly on the unit sphere within N_j

    Parameters
    ----------
    k : Dimension.
    zero_restriction_matrices : Dict mapping shock_idx -> (n_zeros_j, k) matrix.
    rng : Random generator.

    Returns
    -------
    (k, k) orthogonal matrix Q, or None if construction fails.
    """
    Q = np.zeros((k, k))
    prev_columns = []

    for j in range(k):
        Z_j = zero_restriction_matrices.get(j, None)
        q_j = draw_orthogonal_column_in_nullspace(Z_j, prev_columns, k, rng)

        if q_j is None:
            return None  # Failed: subspace empty

        Q[:, j] = q_j
        prev_columns.append(q_j)

    return Q


def zero_sign_restriction_identification(
    residuals: np.ndarray,
    tau: np.ndarray,
    zero_restrictions: dict,
    sign_restrictions: dict,
    companion: np.ndarray,
    n_rotations: int = 10000,
    max_horizon_check: int = 0,
    seed: int = 42,
) -> dict:
    """
    Identify structural shocks using zero AND sign restrictions.

    Algorithm (Arias, Rubio-Ramírez & Waggoner 2018):
    1. Compute Cholesky P_tau of co-exceedance matrix
    2. Build zero-restriction matrices Z_j for each shock
    3. Draw Q column-by-column in the null space of Z_j
    4. Candidate impact: A0 = P_tau @ Q
    5. Check sign restrictions on IRFs
    6. Accept if all satisfied

    Parameters
    ----------
    residuals : (T, k) reduced-form residuals.
    tau : (k,) quantile levels.
    zero_restrictions : Dict with keys (shock_idx, var_idx, horizon), values 0.
        Specifies that IRF[h, var_idx, shock_idx] = 0 exactly.
    sign_restrictions : Dict with keys (shock_idx, var_idx, horizon), values +1/-1.
    companion : (kp, kp) companion matrix.
    n_rotations : Number of draws to attempt.
    max_horizon_check : Max horizon for checking sign restrictions.
    seed : Random seed.

    Returns
    -------
    Dict with accepted rotations, IRFs, and acceptance diagnostics.
    """
    rng = np.random.default_rng(seed)
    k = residuals.shape[1]

    chol_result = cholesky_identification(residuals, tau)
    P_tau = chol_result["P_tau"]

    # Build zero-restriction matrices
    Z_matrices = _build_zero_restriction_matrices(
        zero_restrictions, k, P_tau, companion)

    max_h = max(
        (h for (_, _, h) in {**zero_restrictions, **sign_restrictions}.keys()),
        default=0,
    )
    max_h = max(max_h, max_horizon_check)

    accepted_rotations = []
    accepted_irfs = []
    n_failed_construction = 0

    for _ in range(n_rotations):
        Q = draw_orthogonal_matrix_with_zeros(k, Z_matrices, rng)

        if Q is None:
            n_failed_construction += 1
            continue

        A0 = P_tau @ Q

        irfs = _compute_irfs_for_rotation(A0, companion, k, max_h)

        # Verify zero restrictions hold (they should by construction, but check)
        zeros_ok = True
        for (shock_idx, var_idx, h), val in zero_restrictions.items():
            if h < irfs.shape[0] and abs(irfs[h, var_idx, shock_idx]) > 1e-8:
                zeros_ok = False
                break

        if not zeros_ok:
            continue

        # Check sign restrictions
        if check_sign_restrictions(irfs, sign_restrictions, max_h):
            accepted_rotations.append(Q)
            accepted_irfs.append(irfs)

    n_accepted = len(accepted_rotations)

    return {
        "P_tau": P_tau,
        "Omega_tau": chol_result["Omega_tau"],
        "n_accepted": n_accepted,
        "n_tried": n_rotations,
        "n_failed_construction": n_failed_construction,
        "acceptance_rate": n_accepted / n_rotations if n_rotations > 0 else 0,
        "accepted_rotations": accepted_rotations,
        "accepted_irfs": accepted_irfs,
        "zero_restrictions": zero_restrictions,
        "sign_restrictions": sign_restrictions,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Combined identification interface
# ═══════════════════════════════════════════════════════════════════════════

def identify_shocks(
    residuals: np.ndarray,
    tau: np.ndarray,
    method: str = "cholesky",
    companion: Optional[np.ndarray] = None,
    sign_restrictions: Optional[dict] = None,
    zero_restrictions: Optional[dict] = None,
    **kwargs,
) -> dict:
    """
    Unified interface for structural identification.

    Parameters
    ----------
    residuals : (T, k) reduced-form residuals.
    tau : (k,) quantile levels.
    method : "cholesky", "sign_restrictions", or "zero_sign_restrictions".
    companion : Required for sign/zero restrictions.
    sign_restrictions : For sign or zero+sign restriction methods.
    zero_restrictions : For zero+sign restriction method.
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

    elif method == "zero_sign_restrictions":
        if companion is None:
            raise ValueError("companion matrix required")
        if zero_restrictions is None:
            raise ValueError("zero_restrictions dict required")
        if sign_restrictions is None:
            sign_restrictions = {}
        return zero_sign_restriction_identification(
            residuals, tau, zero_restrictions, sign_restrictions,
            companion, **kwargs)

    else:
        raise ValueError(f"Unknown identification method: {method}")
