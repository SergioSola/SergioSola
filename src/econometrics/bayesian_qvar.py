"""
Bayesian Quantile Vector Autoregression (QVAR).

Implements the Metropolis-within-Gibbs sampler for the quantile VAR following:
  - Beutel, Emter, Metiu, Prieto & Schüler (2025, JIMF)
  - Schüler (2020, Bundesbank Discussion Paper 2020/14)

The estimation exploits a multivariate Laplace distribution with a mixture
representation:
    u_{t|tau} ~ AL_k(C m_tau, C Sigma_tau C')

where m_tau and Sigma_tau embed the quantile level, and C is a diagonal
positive-definite scaling matrix.

The sampler iterates:
  1. Gibbs step for latent weights w_t  (Generalized Inverse Gaussian)
  2. Gibbs step for coefficients beta_tau  (Normal posterior)
  3. Gibbs step for correlation matrix in Sigma_tau  (Inverse-Wishart)
  4. MH step for scaling factors in C  (Random-walk Metropolis-Hastings)

Convention: B_tau is (n_reg, k) so that Y = X @ B_tau + U, where
  Y is (T_eff, k), X is (T_eff, n_reg), n_reg = 1 + k*p.
  beta = vec(B_tau) has length n_reg * k.
"""

from __future__ import annotations

import numpy as np
from scipy import stats
from scipy.linalg import cholesky
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════
# Generalized Inverse Gaussian sampler
# ═══════════════════════════════════════════════════════════════════════════

def _sample_gig(p: float, a: float, b: float, rng: np.random.Generator) -> float:
    """
    Sample from a Generalized Inverse Gaussian distribution GIG(p, a, b).

    For the special case p = -k/2 + 1 used in the QVAR sampler,
    this provides draws of the latent variable w_t.
    """
    if a <= 0 or b <= 0:
        if a <= 0 and b > 0:
            return rng.gamma(shape=max(-p, 0.01), scale=2.0 / b)
        if b <= 0 and a > 0:
            return 1.0 / rng.gamma(shape=max(p, 0.01), scale=2.0 / a)
        return 1.0

    lam = p
    omega = np.sqrt(a * b)
    swap = lam < 0
    if swap:
        lam = -lam
        a, b = b, a

    # Mode of the GIG
    x_m = (lam - 1 + np.sqrt((lam - 1)**2 + a * b)) / a if a > 0 else 1.0
    if x_m < 1e-12:
        x_m = 1.0

    # Rejection sampling
    for _ in range(10000):
        u = rng.uniform()
        if lam >= 1.0:
            proposal = rng.gamma(shape=lam, scale=x_m / lam)
        else:
            rate = np.sqrt(b / 2.0) if b > 0 else 1.0
            proposal = rng.exponential(scale=1.0 / rate)

        if proposal <= 0:
            continue

        log_f = (lam - 1) * np.log(proposal) - 0.5 * (a * proposal + b / proposal)
        log_f_mode = (lam - 1) * np.log(x_m) - 0.5 * (a * x_m + b / x_m)

        if np.log(u) <= log_f - log_f_mode:
            result = proposal
            if swap:
                result = 1.0 / result
            return result

    result = x_m
    if swap:
        result = 1.0 / result
    return result


def _sample_gig_array(
    p: float, a_vec: np.ndarray, b: float, rng: np.random.Generator
) -> np.ndarray:
    """Sample GIG for each element: GIG(p, a_vec[t], b)."""
    n = len(a_vec)
    result = np.empty(n)
    for t in range(n):
        result[t] = _sample_gig(p, a_vec[t], b, rng)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Build VAR matrices
# ═══════════════════════════════════════════════════════════════════════════

def build_var_matrices(data: np.ndarray, lags: int):
    """
    Build Y and X matrices for VAR(p).

    Returns
    -------
    Y : (T-p, k) dependent variable matrix.
    X : (T-p, 1+k*p) regressor matrix (intercept first).
    """
    T, k = data.shape
    Y = data[lags:]
    X_parts = [np.ones((T - lags, 1))]
    for lag in range(1, lags + 1):
        X_parts.append(data[lags - lag: T - lag])
    X = np.hstack(X_parts)
    return Y, X


# ═══════════════════════════════════════════════════════════════════════════
# Bayesian QVAR Estimation
# ═══════════════════════════════════════════════════════════════════════════

class BayesianQVAR:
    """
    Bayesian Quantile VAR estimated via Metropolis-within-Gibbs sampler.

    Convention: B_tau is (n_reg, k) so that Y = X @ B_tau + U.
    beta = vec(B_tau) = B_tau.ravel() has length n_reg * k.
    """

    def __init__(
        self,
        data: np.ndarray,
        lags: int = 2,
        tau: float | np.ndarray = 0.5,
        var_names: Optional[list[str]] = None,
    ):
        self.data = np.asarray(data, dtype=np.float64)
        self.T_full, self.k = self.data.shape
        self.lags = lags
        self.var_names = var_names or [f"y{i+1}" for i in range(self.k)]

        if np.isscalar(tau):
            self.tau = np.full(self.k, tau)
        else:
            self.tau = np.asarray(tau, dtype=np.float64)
            assert len(self.tau) == self.k

        self.Y, self.X = build_var_matrices(self.data, self.lags)
        self.T_eff = self.Y.shape[0]
        self.n_regressors = self.X.shape[1]  # 1 + k*p

        # Laplace distribution parameters (Eq. 15)
        self.m_tau = (1 - 2 * self.tau) / (self.tau * (1 - self.tau))
        self.sigma_diag = 2.0 / (self.tau * (1 - self.tau))

        self.beta_draws = None
        self.Sigma_draws = None
        self.C_draws = None
        self.residual_draws = None

    def _init_params(self, rng: np.random.Generator):
        """Initialize parameters with OLS starting values."""
        k = self.k
        n_reg = self.n_regressors

        # OLS: B_ols is (n_reg, k)
        B_ols = np.linalg.lstsq(self.X, self.Y, rcond=None)[0]
        beta_init = B_ols.ravel()  # vec(B_ols), length n_reg * k

        Sigma_init = np.diag(self.sigma_diag)
        C_init = np.ones(k)
        w_init = np.ones(self.T_eff)
        return beta_init, Sigma_init, C_init, w_init

    def _compute_b_tau(self, Sigma_tau: np.ndarray) -> float:
        """b_tau = 2 + m_tau' Sigma_tau^{-1} m_tau."""
        Sigma_inv = np.linalg.inv(Sigma_tau)
        return 2.0 + self.m_tau @ Sigma_inv @ self.m_tau

    def _compute_a_tau(
        self, B_tau: np.ndarray, C_vec: np.ndarray,
        Sigma_tau: np.ndarray
    ) -> np.ndarray:
        """
        a_{t|tau} for each t.
        B_tau is (n_reg, k).
        """
        C = np.diag(C_vec)
        Sigma_star = C @ Sigma_tau @ C.T
        Sigma_star_inv = np.linalg.inv(Sigma_star)

        residuals = self.Y - self.X @ B_tau  # (T_eff, k)
        a_vec = np.einsum('ti,ij,tj->t', residuals, Sigma_star_inv, residuals)
        return a_vec

    def _check_stationarity(self, B_tau: np.ndarray) -> bool:
        """Check eigenvalues of companion matrix. B_tau is (n_reg, k)."""
        k = self.k
        p = self.lags
        # B_tau row 0 = intercept, rows 1: = lag coefficients
        # For companion: need (k, k*p) from the lag part
        B_lag = B_tau[1:, :].T  # (k, k*p)

        companion = np.zeros((k * p, k * p))
        companion[:k, :] = B_lag
        if p > 1:
            companion[k:, :k * (p - 1)] = np.eye(k * (p - 1))

        eigenvalues = np.linalg.eigvals(companion)
        return np.all(np.abs(eigenvalues) < 1.0)

    def _gibbs_step_w(
        self, B_tau: np.ndarray, Sigma_tau: np.ndarray,
        C_vec: np.ndarray, rng: np.random.Generator
    ) -> np.ndarray:
        """Gibbs Step 1: Draw w_t from GIG(-k/2+1, a_{t|tau}, b_tau)."""
        k = self.k
        p_gig = -k / 2.0 + 1.0
        b_tau = self._compute_b_tau(Sigma_tau)
        a_vec = self._compute_a_tau(B_tau, C_vec, Sigma_tau)
        # Ensure a_vec is positive
        a_vec = np.clip(a_vec, 1e-12, None)
        return _sample_gig_array(p_gig, a_vec, b_tau, rng)

    def _gibbs_step_beta(
        self, Sigma_tau: np.ndarray, C_vec: np.ndarray,
        w: np.ndarray, V_prior: np.ndarray, beta_prior: np.ndarray,
        rng: np.random.Generator
    ) -> np.ndarray:
        """
        Gibbs Step 2: Draw beta_tau from Normal posterior (Eqs. 21-22).
        beta = vec(B_tau) where B_tau is (n_reg, k).
        """
        k = self.k
        n_reg = self.n_regressors
        C = np.diag(C_vec)
        Sigma_star = C @ Sigma_tau @ C.T
        Sigma_star_inv = np.linalg.inv(Sigma_star)

        W_inv_diag = 1.0 / w  # (T_eff,)

        # X' W^{-1} X  — use diagonal W_inv for efficiency
        XtWiX = self.X.T @ (self.X * W_inv_diag[:, np.newaxis])  # (n_reg, n_reg)

        # Posterior precision
        V_prior_inv = np.linalg.inv(V_prior)
        V_post_inv = V_prior_inv + np.kron(Sigma_star_inv, XtWiX)
        V_post = np.linalg.inv(V_post_inv)

        # Adjusted dependent variable: y - w * (C m_tau)'
        Cm = C @ self.m_tau  # (k,)
        y_adj = self.Y - np.outer(w, Cm)  # (T_eff, k)

        # X' W^{-1} y_adj
        XtWiy = self.X.T @ (y_adj * W_inv_diag[:, np.newaxis])  # (n_reg, k)

        # vec(X'W^{-1}y_adj) using kron structure
        # The posterior mean involves (Sigma_star_inv kron I_{n_reg}) @ vec(X'W^{-1}y_adj)
        # vec(X'W^{-1}y_adj) = XtWiy.ravel(order='F')  (column-major = stack columns)
        rhs = np.kron(Sigma_star_inv, np.eye(n_reg)) @ XtWiy.ravel(order='F')

        beta_hat = V_post @ (V_prior_inv @ beta_prior + rhs)

        # Draw from multivariate normal
        try:
            L = cholesky(V_post, lower=True)
            z = rng.standard_normal(len(beta_hat))
            beta_draw = beta_hat + L @ z
        except np.linalg.LinAlgError:
            V_post_reg = V_post + 1e-8 * np.eye(V_post.shape[0])
            L = cholesky(V_post_reg, lower=True)
            z = rng.standard_normal(len(beta_hat))
            beta_draw = beta_hat + L @ z

        return beta_draw

    def _gibbs_step_sigma(
        self, B_tau: np.ndarray, C_vec: np.ndarray,
        w: np.ndarray, nu_prior: float, S_prior: np.ndarray,
        rng: np.random.Generator
    ) -> np.ndarray:
        """Gibbs Step 3: Draw Sigma_tau (Eqs. 23-24, 29-30)."""
        k = self.k
        C = np.diag(C_vec)
        C_inv = np.diag(1.0 / C_vec)
        Cm = C @ self.m_tau

        residuals = self.Y - self.X @ B_tau  # (T_eff, k)
        adj_resid = residuals - np.outer(w, Cm)
        adj_resid_c = adj_resid @ C_inv.T

        W_inv_diag = 1.0 / w
        S_post = S_prior + adj_resid_c.T @ (adj_resid_c * W_inv_diag[:, np.newaxis])
        nu_post = nu_prior + self.T_eff

        # Ensure S_post is symmetric positive definite
        S_post = 0.5 * (S_post + S_post.T)
        eigvals = np.linalg.eigvalsh(S_post)
        if np.min(eigvals) < 1e-10:
            S_post += (1e-10 - np.min(eigvals) + 1e-10) * np.eye(k)

        Sigma_draw = stats.invwishart.rvs(df=nu_post, scale=S_post,
                                          random_state=rng)

        # Standardize: extract correlation, rebuild with fixed diagonal
        D = np.sqrt(np.diag(Sigma_draw))
        D[D < 1e-12] = 1e-12
        D_inv = np.diag(1.0 / D)
        R = D_inv @ Sigma_draw @ D_inv

        S_tau = np.diag(np.sqrt(self.sigma_diag))
        Sigma_new = S_tau @ R @ S_tau
        return Sigma_new

    def _mh_step_c(
        self, B_tau: np.ndarray, Sigma_tau: np.ndarray,
        C_vec_current: np.ndarray, w: np.ndarray,
        mh_scale: float, rng: np.random.Generator
    ) -> tuple[np.ndarray, bool]:
        """MH Step: Random-walk for C (Eq. 31)."""
        k = self.k
        v = rng.normal(0, mh_scale, size=k)
        C_proposed = C_vec_current + v

        if np.any(C_proposed <= 0):
            return C_vec_current, False

        log_lik_proposed = self._log_likelihood_c(B_tau, Sigma_tau, C_proposed, w)
        log_lik_current = self._log_likelihood_c(B_tau, Sigma_tau, C_vec_current, w)

        log_alpha = log_lik_proposed - log_lik_current
        if np.log(rng.uniform()) < log_alpha:
            return C_proposed, True
        return C_vec_current, False

    def _log_likelihood_c(
        self, B_tau: np.ndarray, Sigma_tau: np.ndarray,
        C_vec: np.ndarray, w: np.ndarray
    ) -> float:
        """Log-likelihood for the multivariate Laplace (Eq. 28)."""
        k = self.k
        C = np.diag(C_vec)
        Sigma_star = C @ Sigma_tau @ C.T

        try:
            Sigma_star_inv = np.linalg.inv(Sigma_star)
            log_det = np.linalg.slogdet(Sigma_star)[1]
        except np.linalg.LinAlgError:
            return -np.inf

        Cm = C @ self.m_tau
        Sigma_tau_inv = np.linalg.inv(Sigma_tau)
        b_tau = 2.0 + self.m_tau @ Sigma_tau_inv @ self.m_tau

        residuals = self.Y - self.X @ B_tau

        order = -k / 2.0 + 1.0
        log_lik = 0.0

        for t in range(self.T_eff):
            r = residuals[t]
            a_t = r @ Sigma_star_inv @ r
            if a_t <= 0:
                a_t = 1e-12

            arg = np.sqrt(b_tau * a_t)
            if arg > 700:
                log_bessel = -arg + 0.5 * np.log(np.pi / (2 * arg))
            elif arg < 1e-10:
                log_bessel = 0.0
            else:
                bessel_val = self._bessel_kv(order, arg)
                if bessel_val > 0:
                    log_bessel = np.log(bessel_val)
                else:
                    log_bessel = -500.0

            log_lik += (
                -0.5 * log_det
                + order * 0.5 * np.log(a_t)
                - order * 0.5 * np.log(b_tau)
                + r @ Sigma_star_inv @ Cm
                + log_bessel
            )

        return log_lik

    @staticmethod
    def _bessel_kv(v: float, z: float) -> float:
        """Modified Bessel function of the second kind."""
        from scipy.special import kv
        try:
            val = kv(v, z)
            if np.isnan(val) or np.isinf(val):
                return 0.0
            return val
        except Exception:
            return 0.0

    def estimate(
        self,
        n_draws: int = 10000,
        n_burnin: int = 5000,
        mh_scale: float = 0.1,
        seed: int = 42,
        verbose: bool = True,
    ) -> dict:
        """
        Run the Metropolis-within-Gibbs sampler.

        Returns dictionary with posterior draws and diagnostics.
        beta_draws: each row is vec(B_tau) where B_tau is (n_reg, k).
        """
        rng = np.random.default_rng(seed)
        k = self.k
        n_reg = self.n_regressors
        n_total = n_draws + n_burnin
        n_beta = n_reg * k

        # Priors (uninformative, following footnote 3)
        beta_prior = np.zeros(n_beta)
        V_prior = 10.0 * np.eye(n_beta)

        nu_prior = float(k + 2)  # Ensure IW is proper
        S_prior = np.eye(k)

        # Initialize
        beta, Sigma_tau, C_vec, w = self._init_params(rng)
        B_tau = beta.reshape(n_reg, k)

        # Storage
        beta_store = np.zeros((n_draws, n_beta))
        Sigma_store = np.zeros((n_draws, k, k))
        C_store = np.zeros((n_draws, k))
        residual_store = np.zeros((n_draws, self.T_eff, k))

        mh_accepts = 0
        mh_total = 0
        kept = 0

        for draw in range(n_total):
            # Step 1: Draw w_t
            w = self._gibbs_step_w(B_tau, Sigma_tau, C_vec, rng)
            w = np.clip(w, 1e-10, 1e10)

            # Step 2: Draw beta_tau
            beta = self._gibbs_step_beta(
                Sigma_tau, C_vec, w, V_prior, beta_prior, rng)
            B_tau_candidate = beta.reshape(n_reg, k)

            if self._check_stationarity(B_tau_candidate):
                B_tau = B_tau_candidate
            else:
                beta = B_tau.ravel()

            # Step 3: Draw Sigma_tau
            Sigma_tau = self._gibbs_step_sigma(
                B_tau, C_vec, w, nu_prior, S_prior, rng)

            # Step 4: MH step for C
            C_vec, accepted = self._mh_step_c(
                B_tau, Sigma_tau, C_vec, w, mh_scale, rng)
            mh_total += 1
            if accepted:
                mh_accepts += 1

            # Store after burn-in
            if draw >= n_burnin:
                idx = draw - n_burnin
                beta_store[idx] = beta
                Sigma_store[idx] = Sigma_tau
                C_store[idx] = C_vec
                residual_store[idx] = self.Y - self.X @ B_tau
                kept += 1

            if verbose and (draw + 1) % max(1, n_total // 10) == 0:
                acc_rate = mh_accepts / mh_total if mh_total > 0 else 0
                print(f"  Draw {draw+1}/{n_total}, "
                      f"MH acceptance rate: {acc_rate:.3f}")

        acc_rate = mh_accepts / mh_total if mh_total > 0 else 0
        if verbose:
            print(f"  Final MH acceptance rate for C: {acc_rate:.3f}")
            if acc_rate < 0.15:
                print("  Warning: MH acceptance rate low. "
                      "Consider reducing mh_scale.")
            elif acc_rate > 0.55:
                print("  Warning: MH acceptance rate high. "
                      "Consider increasing mh_scale.")

        self.beta_draws = beta_store[:kept]
        self.Sigma_draws = Sigma_store[:kept]
        self.C_draws = C_store[:kept]
        self.residual_draws = residual_store[:kept]

        return {
            "beta_draws": self.beta_draws,
            "Sigma_draws": self.Sigma_draws,
            "C_draws": self.C_draws,
            "residual_draws": self.residual_draws,
            "mh_acceptance_rate": acc_rate,
            "n_draws": kept,
            "tau": self.tau.copy(),
            "lags": self.lags,
            "k": self.k,
            "n_regressors": self.n_regressors,
            "var_names": self.var_names,
            "T_eff": self.T_eff,
            "Y": self.Y,
            "X": self.X,
        }

    def get_posterior_median_coefficients(self) -> np.ndarray:
        """Return posterior median of B_tau as (n_reg, k) matrix."""
        if self.beta_draws is None:
            raise RuntimeError("Must call estimate() first.")
        median_beta = np.median(self.beta_draws, axis=0)
        return median_beta.reshape(self.n_regressors, self.k)

    def get_companion_matrix(self, B_tau: np.ndarray) -> np.ndarray:
        """Build companion matrix. B_tau is (n_reg, k)."""
        k = self.k
        p = self.lags
        B_lag = B_tau[1:, :].T  # (k, k*p)
        companion = np.zeros((k * p, k * p))
        companion[:k, :] = B_lag
        if p > 1:
            companion[k:, :k * (p - 1)] = np.eye(k * (p - 1))
        return companion

    def get_residuals_for_draw(self, draw_idx: int) -> np.ndarray:
        """Return residuals for a specific posterior draw."""
        if self.residual_draws is None:
            raise RuntimeError("Must call estimate() first.")
        return self.residual_draws[draw_idx]
