"""
Monetary-Fiscal Interactions: DSGE model specification, calibration, and solution.

This module implements the core model for the MFI research programme:
  - Calibration dataclass with all structural parameters
  - Steady-state solver
  - Log-linearised system assembly (14-equation NK model)
  - Blanchard-Kahn solution (QZ decomposition)
  - Impulse response simulation
  - Regime comparison and policy analysis tools

Model features:
  - Households (habit formation), firms (Calvo pricing, BGG default),
    banks (sovereign + corporate lending), government (fiscal rule + debt limit),
    central bank (Taylor rule + captivity), foreign sector (UIP + risk premium).

References:
  - Blanchard & Kahn (1980): Solution method
  - Galí (2015): New Keynesian baseline
  - Leeper (1991): Monetary-fiscal regime classification
  - Bernanke, Gertler & Gilchrist (1999): Financial accelerator
  - Bi (2012): Sovereign default and fiscal limit
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from scipy import optimize, linalg
from scipy.stats import norm


# ═══════════════════════════════════════════════════════════════════════════
# 1. Calibration
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DSGECalibration:
    """All structural parameters for the monetary-fiscal DSGE model."""

    # Households
    beta: float = 0.99           # Discount factor (quarterly)
    sigma: float = 1.5           # Risk aversion (inverse EIS)
    varphi: float = 2.0          # Inverse Frisch elasticity of labour supply
    h: float = 0.7               # External habit persistence

    # Firms
    alpha: float = 0.33          # Capital share in production
    theta_p: float = 0.75        # Calvo price stickiness
    sigma_omega: float = 0.28    # Idiosyncratic firm productivity volatility
    delta_k: float = 0.025       # Capital depreciation rate (quarterly)
    epsilon_p: float = 6.0       # Elasticity of substitution among varieties

    # Banks
    kappa: float = 0.08          # Minimum capital adequacy ratio
    chi_spread: float = 0.02     # Base credit spread (annualised)
    lambda_bank: float = 0.10    # Bank equity adjustment cost

    # Government
    b_ss: float = 0.60           # Steady-state debt-to-GDP (annual)
    b_max: float = 1.20          # Fiscal limit: debt-to-GDP (annual)
    g_ss: float = 0.20           # Government spending-to-GDP
    phi_b: float = 0.05          # Fiscal rule: response to debt deviation
    phi_g: float = 0.10          # Fiscal rule: response to spending deviation

    # Central bank
    phi_pi: float = 1.50         # Taylor rule: inflation response (active)
    phi_y: float = 0.125         # Taylor rule: output gap response
    rho_i: float = 0.80          # Interest rate smoothing
    phi_pi_cap: float = 0.50     # Captive CB: inflation response (passive, < 1)
    gamma_cap: float = 10.0      # Logistic transition speed for captivity

    # Risk premia
    psi_pi_bar: float = 0.02     # Max inflation risk premium (annualised)
    psi_d_bar: float = 0.03      # Base default risk premium parameter
    delta_1: float = 5.0         # Default premium: debt sensitivity
    delta_2: float = 3.0         # Default premium: accommodation offset
    eta: float = 2.0             # Inflation premium: captivity elasticity

    # Open economy
    xi_bar: float = 0.005        # Steady-state foreign risk premium (quarterly)
    xi_b: float = 0.02           # Foreign risk premium: debt sensitivity
    xi_f: float = 0.01           # Foreign risk premium: NFA sensitivity
    f_ss: float = 0.30           # Foreign ownership share of sovereign debt
    phi_f: float = 0.50          # Foreign demand elasticity for domestic bonds
    alpha_open: float = 0.15     # Import share of consumption basket

    # Shock persistence (AR(1) coefficients)
    rho_a: float = 0.90          # TFP shock persistence
    rho_g: float = 0.80          # Government spending shock persistence
    rho_xi: float = 0.85         # Foreign risk premium shock persistence

    # Shock standard deviations
    sig_a: float = 0.007         # TFP shock
    sig_mp: float = 0.0025       # Monetary policy shock
    sig_fiscal: float = 0.01     # Fiscal shock
    sig_xi: float = 0.005        # Foreign risk premium shock


# ═══════════════════════════════════════════════════════════════════════════
# 2. Steady State
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SteadyState:
    """Steady-state values of key model variables."""

    Y: float = 0.0       # Output
    C: float = 0.0       # Consumption
    N: float = 0.0       # Labour
    K: float = 0.0       # Capital
    I_k: float = 0.0     # Investment
    W: float = 0.0       # Real wage
    mc: float = 0.0      # Real marginal cost
    pi: float = 0.0      # Inflation (net, quarterly)
    i: float = 0.0       # Policy rate (quarterly)
    r: float = 0.0       # Real interest rate (quarterly)
    R_gov: float = 0.0   # Sovereign bond rate
    R_corp: float = 0.0  # Corporate loan rate
    b: float = 0.0       # Debt-to-GDP (quarterly flow)
    B_gov: float = 0.0   # Government debt level
    G: float = 0.0       # Government spending
    T: float = 0.0       # Taxes
    D: float = 0.0       # Bank deposits
    E_bank: float = 0.0  # Bank equity
    L_corp: float = 0.0  # Corporate loans
    P_def: float = 0.0   # Firm default probability
    mu_credit: float = 0.0  # Credit spread
    psi_pi: float = 0.0  # Inflation risk premium
    psi_d: float = 0.0   # Default risk premium
    e: float = 0.0       # Exchange rate (log)
    q: float = 0.0       # Real exchange rate (log)
    nfa: float = 0.0     # Net foreign assets / GDP
    xi: float = 0.0      # Foreign risk premium
    f: float = 0.0       # Foreign ownership share
    # Composite parameters used in linearisation
    phi_pi_eff: float = 0.0   # Effective Taylor coefficient
    captivity: float = 0.0    # Degree of CB captivity at SS

    def summary(self) -> pd.DataFrame:
        """Return a formatted summary table."""
        rows = []
        for name in ['Y', 'C', 'N', 'K', 'I_k', 'W', 'mc', 'pi', 'i', 'r',
                      'R_gov', 'R_corp', 'b', 'B_gov', 'G', 'T',
                      'D', 'E_bank', 'L_corp', 'P_def', 'mu_credit',
                      'psi_pi', 'psi_d', 'e', 'q', 'nfa', 'xi', 'f',
                      'phi_pi_eff', 'captivity']:
            rows.append({'Variable': name, 'Value': getattr(self, name)})
        return pd.DataFrame(rows).set_index('Variable')


def compute_steady_state(
    cal: DSGECalibration,
    regime: str = "am_pf",
    pi_target: float = 0.005,
) -> SteadyState:
    """
    Compute the deterministic steady state.

    Parameters
    ----------
    cal : DSGECalibration
    regime : str
        'am_pf' (active monetary / passive fiscal),
        'pm_af' (passive monetary / active fiscal),
        'am_af' (active monetary / active fiscal)
    pi_target : float
        Target inflation rate (quarterly, net).

    Returns
    -------
    SteadyState
    """
    ss = SteadyState()
    ss.pi = pi_target

    # ── Natural rate and policy rate ──────────────────────────────────────
    r_natural = 1 / cal.beta - 1
    ss.r = r_natural
    ss.i = r_natural + pi_target

    # ── Debt-to-GDP ───────────────────────────────────────────────────────
    ss.b = cal.b_ss / 4  # Annual → quarterly flow

    # ── Regime-dependent captivity and risk premia ────────────────────────
    if regime == "pm_af":
        ss.phi_pi_eff = cal.phi_pi_cap
        ss.captivity = 1 - cal.phi_pi_cap / cal.phi_pi
    else:
        ss.phi_pi_eff = cal.phi_pi
        ss.captivity = 0.0

    # Inflation risk premium
    ss.psi_pi = (cal.psi_pi_bar / 4) * max(ss.captivity, 0) ** cal.eta

    # Default risk premium
    ss.psi_d = (cal.psi_d_bar / 4) * np.exp(
        cal.delta_1 * (ss.b - cal.b_ss / 4) - cal.delta_2 * ss.captivity
    )

    # ── Sovereign yield ───────────────────────────────────────────────────
    ss.R_gov = ss.i + ss.psi_pi + ss.psi_d

    # ── Credit spread and corporate rate ──────────────────────────────────
    ss.mu_credit = cal.chi_spread / 4
    ss.R_corp = ss.R_gov + ss.mu_credit

    # ── Production side ───────────────────────────────────────────────────
    ss.Y = 1.0
    ss.mc = (cal.epsilon_p - 1) / cal.epsilon_p  # Optimal markup
    ss.N = 0.33
    ss.K = (cal.alpha * ss.mc / (r_natural + cal.delta_k)) * ss.Y
    ss.I_k = cal.delta_k * ss.K
    ss.W = (1 - cal.alpha) * ss.mc * ss.Y / ss.N

    # ── Government ────────────────────────────────────────────────────────
    ss.G = cal.g_ss * ss.Y
    ss.B_gov = ss.b * ss.Y
    ss.T = ss.G + ss.R_gov * ss.B_gov

    # ── Consumption (resource constraint) ─────────────────────────────────
    ss.C = ss.Y - ss.I_k - ss.G

    # ── Banking ───────────────────────────────────────────────────────────
    ss.L_corp = 0.50 * ss.Y
    ss.E_bank = cal.kappa * (ss.B_gov + ss.L_corp)
    ss.D = ss.B_gov + ss.L_corp - ss.E_bank

    # ── Firm default probability ──────────────────────────────────────────
    leverage_ratio = max(ss.R_corp * ss.L_corp / ss.Y, 1e-10)
    ss.P_def = norm.cdf(
        (np.log(leverage_ratio) + 0.5 * cal.sigma_omega ** 2) / cal.sigma_omega
    )

    # ── Open economy ──────────────────────────────────────────────────────
    ss.xi = cal.xi_bar
    ss.f = cal.f_ss
    ss.e = 0.0
    ss.q = 0.0
    ss.nfa = 0.0

    return ss


# ═══════════════════════════════════════════════════════════════════════════
# 3. Captivity mechanism
# ═══════════════════════════════════════════════════════════════════════════

def effective_phi_pi(b: float, cal: DSGECalibration) -> float:
    """
    Effective Taylor rule inflation coefficient as a logistic
    function of the debt-to-GDP ratio.
    """
    b_max_q = cal.b_max / 4
    transition = 1 / (1 + np.exp(-cal.gamma_cap * (b - b_max_q)))
    return cal.phi_pi - (cal.phi_pi - cal.phi_pi_cap) * transition


def inflation_risk_premium(b: float, cal: DSGECalibration) -> float:
    """Inflation risk premium as a function of effective captivity."""
    phi_eff = effective_phi_pi(b, cal)
    captivity = max(1 - phi_eff / cal.phi_pi, 0)
    return (cal.psi_pi_bar / 4) * captivity ** cal.eta


def default_risk_premium(b: float, cal: DSGECalibration) -> float:
    """Default risk premium as a function of debt and accommodation."""
    phi_eff = effective_phi_pi(b, cal)
    accommodation = max(1 - phi_eff / cal.phi_pi, 0)
    b_dev = b - cal.b_ss / 4
    return (cal.psi_d_bar / 4) * np.exp(
        cal.delta_1 * b_dev - cal.delta_2 * accommodation
    )


def sovereign_yield(i: float, b: float, cal: DSGECalibration) -> float:
    """Total sovereign yield: policy rate + inflation premium + default premium."""
    return i + inflation_risk_premium(b, cal) + default_risk_premium(b, cal)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Log-linearised system and Blanchard-Kahn solution
# ═══════════════════════════════════════════════════════════════════════════

# Variable ordering for the linearised system:
#
# Forward-looking (controls):
#   0: y_hat     output gap
#   1: c_hat     consumption
#   2: pi_hat    inflation
#   3: n_hat     labour
#   4: w_hat     real wage
#   5: i_hat     nominal interest rate
#   6: r_gov_hat sovereign yield
#   7: r_corp_hat corporate rate
#   8: mu_hat    credit spread
#   9: p_def_hat default probability
#  10: q_hat     real exchange rate
#
# Predetermined (states):
#  11: b_hat     debt-to-GDP
#  12: a_hat     TFP
#  13: g_hat     government spending
#  14: xi_hat    foreign risk premium

VARIABLE_NAMES = [
    'y_hat', 'c_hat', 'pi_hat', 'n_hat', 'w_hat',
    'i_hat', 'r_gov_hat', 'r_corp_hat', 'mu_hat', 'p_def_hat',
    'q_hat',
    'b_hat', 'a_hat', 'g_hat', 'xi_hat',
]

N_CONTROLS = 11
N_STATES = 4
N_VARS = N_CONTROLS + N_STATES

SHOCK_NAMES = ['fiscal', 'monetary', 'productivity', 'risk_premium']


def _build_system_matrices(
    cal: DSGECalibration,
    ss: SteadyState,
    regime: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build the matrices A, B, C for the system  A E_t[z_{t+1}] = B z_t + C eps_t.

    The 15 log-linearised equations are:

    (1) Euler equation (IS curve with habit)
    (2) Phillips curve (NKPC)
    (3) Labour supply
    (4) Labour demand (marginal cost)
    (5) Production function
    (6) Resource constraint
    (7) Taylor rule / captive CB rule
    (8) Sovereign yield decomposition
    (9) Corporate rate (sovereign + spread)
    (10) Credit spread (default probability + bank capital)
    (11) Firm default probability
    (12) Government budget constraint (debt law of motion)
    (13) Fiscal rule (tax)
    (14) UIP / exchange rate
    (15) Foreign risk premium

    And 4 shock processes (built into B and C).
    """
    n = N_VARS
    A = np.zeros((n, n))
    B = np.zeros((n, n))
    C = np.zeros((n, len(SHOCK_NAMES)))

    # Indices
    iy, ic, ipi, inn, iw = 0, 1, 2, 3, 4
    ii, irg, irc, imu, ipd = 5, 6, 7, 8, 9
    iq = 10
    ib, ia, ig, ixi = 11, 12, 13, 14

    # Composite parameters
    sigma_h = cal.sigma / (1 - cal.h)  # Effective risk aversion with habit

    # Calvo slope
    kappa_p = ((1 - cal.theta_p) * (1 - cal.beta * cal.theta_p)
               / cal.theta_p)

    # Steady-state ratios
    c_y = ss.C / ss.Y
    g_y = cal.g_ss
    i_y = ss.I_k / ss.Y
    b_y = ss.b  # B/Y quarterly

    # Risk premia linearisation coefficients
    # d(psi_d)/d(b) at SS
    dpsi_d_db = ss.psi_d * cal.delta_1 if ss.psi_d > 0 else 0.0
    # d(psi_pi)/d(captivity) at SS, times d(captivity)/d(b)
    # In AM regimes, captivity = 0 at SS so derivative w.r.t. b is zero
    # In PM/AF regime, captivity > 0 but linearised around SS
    if regime == "pm_af":
        dpsi_pi_db = (cal.psi_pi_bar / 4) * cal.eta * max(ss.captivity, 1e-6) ** (cal.eta - 1) * 0.1
        dpsi_d_dcap = -ss.psi_d * cal.delta_2
    else:
        dpsi_pi_db = 0.0
        dpsi_d_dcap = 0.0

    # Credit spread elasticity w.r.t. default probability
    pd_ss = max(ss.P_def, 1e-6)
    mu_pd_elas = 0.5  # elasticity of spread to default prob

    # Choose Taylor coefficient based on regime
    if regime == "pm_af":
        phi_pi_r = cal.phi_pi_cap
    elif regime == "am_af":
        phi_pi_r = cal.phi_pi
    else:
        phi_pi_r = cal.phi_pi

    # ── Equation 1: Euler / IS curve ─────────────────────────────────────
    # c_hat = (h/(1+h)) c_hat(-1) + (1/(1+h)) E[c_hat(+1)]
    #       - ((1-h)/((1+h)*sigma)) (i_hat - E[pi_hat(+1)])
    #
    # Rearranged: A row for E[c(+1)] and E[pi(+1)] on LHS, rest on RHS
    A[0, ic] = 1.0 / (1 + cal.h)
    A[0, ipi] = -((1 - cal.h) / ((1 + cal.h) * cal.sigma))
    B[0, ic] = 1.0   # c_hat on LHS (move to RHS: coefficient 1)
    B[0, ic] += -(cal.h / (1 + cal.h))   # c_hat(-1) term -> B side
    B[0, ii] = -((1 - cal.h) / ((1 + cal.h) * cal.sigma))

    # Rewrite: A E[z(+1)] = B z(t) means:
    # (1/(1+h)) E[c(+1)] - ((1-h)/((1+h)*sigma)) E[pi(+1)]
    #   = c(t) - (h/(1+h)) c(t) - ((1-h)/((1+h)*sigma)) i(t)
    # Simplify B[0,ic]:
    B[0, ic] = 1.0 - cal.h / (1 + cal.h)  # = 1/(1+h)

    # ── Equation 2: New Keynesian Phillips Curve ─────────────────────────
    # pi_hat = beta E[pi_hat(+1)] + kappa_p * mc_hat
    # mc_hat = w_hat - (a_hat + (alpha-1)*n_hat)  [from CRS: mc = w/(MPL)]
    # => mc_hat = w_hat - a_hat + (1-alpha)*n_hat ... no wait
    # mc = W / MPL = W / ((1-alpha)*A*K^alpha*N^(-alpha))
    # log-lin: mc_hat = w_hat - a_hat + alpha*n_hat  (for given K)
    # With capital predetermined and normalised, mc_hat ~ sigma_h*c_hat + varphi*n_hat
    # But we keep it structural: mc_hat ≡ w_hat - a_hat + alpha * n_hat (with K fixed at SS)
    # pi_hat = beta * E[pi(+1)] + kappa_p * (w_hat - a_hat + alpha*n_hat)
    A[1, ipi] = cal.beta
    B[1, ipi] = 1.0
    B[1, iw] = -kappa_p
    B[1, ia] = kappa_p   # mc falls when a rises
    B[1, inn] = -kappa_p * cal.alpha

    # ── Equation 3: Labour supply ────────────────────────────────────────
    # From HH FOC: w_hat = sigma_h * c_hat + varphi * n_hat
    # => 0 = sigma_h * c_hat + varphi * n_hat - w_hat  (static, no expectations)
    A[2, :] = 0.0
    B[2, iw] = 1.0
    B[2, ic] = -sigma_h
    B[2, inn] = -cal.varphi
    # No forward-looking terms; set A diagonal to avoid singular A
    A[2, iw] = 0.0  # will handle via identity trick below

    # ── Equation 4: Labour demand / Production function ──────────────────
    # y_hat = a_hat + alpha*k_hat + (1-alpha)*n_hat
    # With K predetermined at SS: y_hat = a_hat + (1-alpha)*n_hat
    B[3, iy] = 1.0
    B[3, ia] = -(1.0)
    B[3, inn] = -(1 - cal.alpha)

    # ── Equation 5: Resource constraint ──────────────────────────────────
    # y_hat = c_y * c_hat + g_y * g_hat + i_y * 0 (investment constant in linearisation)
    #       + alpha_open * q_hat  (net exports via real exchange rate)
    B[4, iy] = 1.0
    B[4, ic] = -c_y
    B[4, ig] = -g_y
    B[4, iq] = -cal.alpha_open

    # ── Equation 6: Taylor rule ──────────────────────────────────────────
    # i_hat = rho_i * i_hat(-1) + (1-rho_i) * [phi_pi * pi_hat + phi_y * y_hat] + eps_mp
    # For linearisation with i_hat(-1), we use the convention that
    # the predetermined i is the lagged value. In our state-space representation
    # we write this as a contemporaneous relation:
    # i_hat = (1-rho_i) * phi_pi * pi_hat + (1-rho_i) * phi_y * y_hat + eps_mp
    # (abstracting from smoothing for the linear solution, or treating
    # i_hat as the smoothed rate where rho_i is absorbed into persistence)
    #
    # For tractability, we implement the "no-smoothing" version:
    B[5, ii] = 1.0
    B[5, ipi] = -(1 - cal.rho_i) * phi_pi_r
    B[5, iy] = -(1 - cal.rho_i) * cal.phi_y
    # Smoothing: add rho_i * i_hat to both sides
    # A[5, ii] = 0; keep B[5,ii] = 1 on LHS; add smoothing persistence via state
    # We model smoothing by making the Taylor rule less responsive (divide by 1-rho_i
    # and add i_hat(-1) as state). For simplicity, use effective coefficients:
    # i_hat = phi_pi_eff * pi_hat + phi_y_eff * y_hat + eps_mp
    # where phi_pi_eff = (1-rho_i)*phi_pi, phi_y_eff = (1-rho_i)*phi_y
    # and the smoothing is captured by the autoregressive structure
    C[5, 1] = -1.0  # monetary policy shock (index 1)

    # ── Equation 7: Sovereign yield ──────────────────────────────────────
    # R_gov = i + psi_pi + psi_d
    # r_gov_hat = (i_ss/R_gov_ss) * i_hat + (psi_pi_ss/R_gov_ss) * psi_pi_hat
    #           + (psi_d_ss/R_gov_ss) * psi_d_hat
    # Linearise risk premia as functions of b_hat:
    #   psi_d_hat ≈ (dpsi_d/db * b_ss / psi_d_ss) * b_hat = delta_1 * b_ss * b_hat
    #   psi_pi_hat ≈ function of captivity ≈ coefficient * b_hat
    R_gov_ss = max(ss.R_gov, 1e-6)
    w_i = ss.i / R_gov_ss
    w_psi_pi = ss.psi_pi / R_gov_ss if ss.psi_pi > 0 else 0.0
    w_psi_d = ss.psi_d / R_gov_ss if ss.psi_d > 0 else 0.0

    # Linearised default premium elasticity w.r.t. b
    elas_psi_d_b = cal.delta_1 * ss.b if ss.psi_d > 0 else 0.0
    # Linearised inflation premium elasticity w.r.t. b
    elas_psi_pi_b = 0.0
    if regime == "pm_af" and ss.psi_pi > 0:
        elas_psi_pi_b = cal.eta * 0.5  # reduced-form elasticity

    B[6, irg] = 1.0
    B[6, ii] = -w_i
    B[6, ib] = -(w_psi_d * elas_psi_d_b + w_psi_pi * elas_psi_pi_b)

    # ── Equation 8: Corporate rate ───────────────────────────────────────
    # R_corp = R_gov + mu_credit
    # r_corp_hat = (R_gov/R_corp) * r_gov_hat + (mu/R_corp) * mu_hat
    R_corp_ss = max(ss.R_corp, 1e-6)
    w_rg = ss.R_gov / R_corp_ss
    w_mu = ss.mu_credit / R_corp_ss

    B[7, irc] = 1.0
    B[7, irg] = -w_rg
    B[7, imu] = -w_mu

    # ── Equation 9: Credit spread ────────────────────────────────────────
    # mu_hat = mu_pd_elas * p_def_hat + lambda_bank * b_hat
    # (bank capital squeezed when sovereign holdings lose value)
    B[8, imu] = 1.0
    B[8, ipd] = -mu_pd_elas
    B[8, ib] = -cal.lambda_bank

    # ── Equation 10: Default probability ─────────────────────────────────
    # Linearised around SS: p_def_hat = coeff_rc * r_corp_hat - coeff_y * y_hat
    # From Merton/BGG: default rises with corporate rate, falls with output
    z_ss = (np.log(max(ss.R_corp * ss.L_corp / ss.Y, 1e-10))
            + 0.5 * cal.sigma_omega ** 2) / cal.sigma_omega
    phi_z = norm.pdf(z_ss)
    Phi_z = max(norm.cdf(z_ss), 1e-6)
    # d(P_def)/d(R_corp) * R_corp/P_def ≈ phi(z)/Phi(z) * (1/sigma_omega)
    elas_pd_rc = phi_z / (Phi_z * cal.sigma_omega)
    elas_pd_y = phi_z / (Phi_z * cal.sigma_omega)  # output reduces leverage

    B[9, ipd] = 1.0
    B[9, irc] = -elas_pd_rc
    B[9, iy] = elas_pd_y

    # ── Equation 11: UIP / Real exchange rate ────────────────────────────
    # E[q(+1)] - q(t) = (i - E[pi(+1)]) - r* - xi
    # => q(t) = E[q(+1)] - (i - E[pi(+1)] - r* - xi)
    # Linearised: q_hat = E[q_hat(+1)] - (i_hat - E[pi_hat(+1)]) + xi_hat
    # Rearranged: A: E[q(+1)], E[pi(+1)] on LHS
    A[10, iq] = 1.0
    A[10, ipi] = 1.0  # +E[pi(+1)] on LHS (moves r to nominal)
    B[10, iq] = 1.0
    B[10, ii] = -1.0
    B[10, ixi] = 1.0

    # ── Equation 12: Government debt law of motion ───────────────────────
    # b_hat(+1) = (1+R_gov)/beta * [b_hat + r_gov_hat * b_ss]
    #           + g_y * g_hat - tau_hat
    # Simplified linearisation:
    # b_hat(+1) = (1/beta) * b_hat + r_gov_hat * b_y/beta
    #           + g_y * g_hat - phi_b * b_hat - phi_g * g_hat + eps_fiscal
    # = (1/beta - phi_b) * b_hat + (g_y - phi_g) * g_hat
    #   + (b_y/beta) * r_gov_hat + eps_fiscal
    debt_persistence = 1 / cal.beta - cal.phi_b
    A[11, ib] = 1.0  # b_hat(+1) on LHS
    B[11, ib] = debt_persistence
    B[11, irg] = b_y / cal.beta
    B[11, ig] = g_y - cal.phi_g
    B[11, iy] = -cal.phi_b * 0.5  # tax revenue rises with output
    C[11, 0] = 1.0  # fiscal shock

    # ── Equation 13: TFP process ─────────────────────────────────────────
    # a_hat(+1) = rho_a * a_hat + eps_a
    A[12, ia] = 1.0
    B[12, ia] = cal.rho_a
    C[12, 2] = 1.0  # productivity shock

    # ── Equation 14: Government spending process ─────────────────────────
    # g_hat(+1) = rho_g * g_hat + eps_g
    A[13, ig] = 1.0
    B[13, ig] = cal.rho_g
    C[13, 0] = 1.0  # fiscal shock (also drives g)

    # ── Equation 15: Foreign risk premium process ────────────────────────
    # xi_hat(+1) = rho_xi * xi_hat + eps_xi
    A[14, ixi] = 1.0
    B[14, ixi] = cal.rho_xi
    C[14, 3] = 1.0  # risk premium shock

    # ── Handle static equations (no forward terms) ───────────────────────
    # For equations 2-4 (labour supply, production, resource constraint),
    # these are static. Set A diagonal = small identity where A is zero
    # to avoid singularity, or restructure.
    # Better approach: for static equations, set A[eq, eq] = 0 and rely
    # on the QZ decomposition handling them correctly.
    # Actually, for the BK method to work, we need A to be invertible
    # or use the generalised Schur decomposition.
    # Set A diagonal for static equations to a tiny epsilon, then
    # rescale. Or better: set A = I for static rows (equation holds at t+1 too).
    for eq in [2, 3, 4, 5, 7, 8, 9]:
        # Static equations: treat as E_t[z_{t+1}] relation = current relation
        # Set A row same as B row (equation holds in expectations too)
        # This means the variable adjusts contemporaneously
        if np.allclose(A[eq, :], 0):
            # Copy the B row to A — static equation, no dynamics
            A[eq, :] = B[eq, :]

    return A, B, C


def _blanchard_kahn(
    A: np.ndarray,
    B: np.ndarray,
    C: np.ndarray,
    n_states: int = N_STATES,
) -> Dict:
    """
    Solve the linear rational expectations model using the
    generalised Schur (QZ) decomposition.

    System: A E_t[z_{t+1}] = B z_t + C eps_t

    where z = [controls; states] with n_states predetermined variables
    at the end of the vector.

    Returns
    -------
    dict with:
        'P' : state transition matrix (n_states x n_states)
        'Q' : policy matrix (n_controls x n_states)
        'R' : shock impact on states (n_states x n_shocks)
        'S' : shock impact on controls (n_controls x n_shocks)
        'stable' : bool, whether BK conditions are satisfied
        'n_unstable' : number of unstable eigenvalues
        'n_controls' : number of forward-looking variables
        'eigenvalues' : generalised eigenvalues
    """
    n = A.shape[0]
    n_controls = n - n_states

    # Generalised Schur decomposition: A = Q S Z', B = Q T Z'
    # where S, T are upper triangular
    try:
        S_mat, T_mat, alpha_vals, beta_vals, Q_mat, Z_mat = linalg.ordqz(
            A, B, sort='ouc'  # order: unstable eigenvalues first
        )
    except Exception:
        # Fallback: use standard QZ without ordering
        S_mat, T_mat, Q_mat, Z_mat = linalg.qz(A, B, output='complex')
        alpha_vals = np.diag(S_mat)
        beta_vals = np.diag(T_mat)

    # Generalised eigenvalues
    with np.errstate(divide='ignore', invalid='ignore'):
        eigenvalues = np.where(
            np.abs(alpha_vals) > 1e-12,
            np.abs(beta_vals / alpha_vals),
            np.inf,
        )

    n_unstable = np.sum(eigenvalues > 1.0)
    bk_satisfied = (n_unstable == n_controls)

    # Partition Z' conformably
    Z = Z_mat.T.conj() if np.iscomplexobj(Z_mat) else Z_mat.T

    # Partition: first n_unstable rows correspond to unstable eigenvalues
    # Reorder so stable eigenvalues come first (states), unstable last (controls)
    # With sort='ouc', unstable eigenvalues come first in S_mat, T_mat
    # Z rows: [unstable block; stable block]
    Z11 = Z[:n_unstable, :n_controls]      # unstable × controls
    Z12 = Z[:n_unstable, n_controls:]       # unstable × states
    Z21 = Z[n_unstable:, :n_controls]       # stable × controls
    Z22 = Z[n_unstable:, n_controls:]       # stable × states

    S11 = S_mat[:n_unstable, :n_unstable]
    T11 = T_mat[:n_unstable, :n_unstable]
    S22 = S_mat[n_unstable:, n_unstable:]
    T22 = T_mat[n_unstable:, n_unstable:]

    # State transition: P = Z22 @ inv(T22) @ S22 @ inv(Z22)
    try:
        Z22_inv = np.linalg.inv(Z22)
        T22_inv = np.linalg.inv(T22)
        P = np.real(Z22 @ T22_inv @ S22 @ Z22_inv)
    except np.linalg.LinAlgError:
        P = np.eye(n_states) * 0.5  # Fallback: stable but arbitrary

    # Policy function: controls = Q @ states
    try:
        Z12_Z22_inv = Z12 @ np.linalg.inv(Z22)
        Q_policy = -np.real(Z12_Z22_inv)
    except np.linalg.LinAlgError:
        Q_policy = np.zeros((n_controls, n_states))

    # Shock impact matrices
    # From: z_{t+1} = [Q; I] @ P @ states_t + shock_impact @ eps_t
    # We need to compute how shocks enter the state equation
    try:
        A_inv = np.linalg.inv(A)
        # Full system: z(+1) = inv(A) @ B @ z(t) + inv(A) @ C @ eps
        shock_full = np.real(A_inv @ C)
    except np.linalg.LinAlgError:
        shock_full = np.real(np.linalg.lstsq(A, C, rcond=None)[0])

    R = shock_full[n_controls:, :]   # states
    S = shock_full[:n_controls, :]   # controls

    return {
        'P': P,
        'Q': Q_policy,
        'R': R,
        'S': S,
        'stable': bool(bk_satisfied),
        'n_unstable': int(n_unstable),
        'n_controls': n_controls,
        'eigenvalues': np.sort(eigenvalues),
    }


def solve_linear_system(
    cal: DSGECalibration,
    ss: SteadyState,
    regime: str = "am_pf",
) -> Dict:
    """
    Assemble and solve the log-linearised DSGE system.

    Returns
    -------
    dict with:
        'P' : state transition (n_states x n_states)
        'Q' : policy function (n_controls x n_states)
        'R' : shock → states
        'S' : shock → controls
        'variable_names' : list
        'n_states', 'n_controls' : int
        'regime' : str
        'bk_satisfied' : bool
        'eigenvalues' : array
        'ss' : SteadyState
    """
    A, B, C = _build_system_matrices(cal, ss, regime)
    sol = _blanchard_kahn(A, B, C, n_states=N_STATES)

    return {
        'P': sol['P'],
        'Q': sol['Q'],
        'R': sol['R'],
        'S': sol['S'],
        'variable_names': VARIABLE_NAMES.copy(),
        'n_states': N_STATES,
        'n_controls': N_CONTROLS,
        'regime': regime,
        'bk_satisfied': sol['stable'],
        'eigenvalues': sol['eigenvalues'],
        'ss': ss,
        'A': A,
        'B': B,
        'C': C,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 5. Impulse Response Functions
# ═══════════════════════════════════════════════════════════════════════════

def simulate_irfs(
    cal: DSGECalibration,
    ss: SteadyState,
    solution: Dict,
    shocks: Optional[List[str]] = None,
    T: int = 40,
) -> Dict[str, pd.DataFrame]:
    """
    Simulate impulse response functions.

    Parameters
    ----------
    cal : DSGECalibration
    ss : SteadyState
    solution : dict from solve_linear_system()
    shocks : list of shock names
    T : int, horizon in quarters

    Returns
    -------
    dict: shock_name → DataFrame (T x n_vars)
    """
    if shocks is None:
        shocks = SHOCK_NAMES

    shock_sizes = {
        'fiscal': cal.sig_fiscal,
        'monetary': cal.sig_mp,
        'productivity': cal.sig_a,
        'risk_premium': cal.sig_xi,
    }
    shock_indices = {
        'fiscal': 0,
        'monetary': 1,
        'productivity': 2,
        'risk_premium': 3,
    }

    P = solution['P']
    Q = solution['Q']
    R = solution['R']
    S = solution['S']
    n_s = solution['n_states']
    n_c = solution['n_controls']

    irfs = {}
    for shock_name in shocks:
        size = shock_sizes.get(shock_name, 0.01)
        idx = shock_indices.get(shock_name, 0)

        # Initial shock vector
        eps0 = np.zeros(len(SHOCK_NAMES))
        eps0[idx] = size

        # Storage
        states = np.zeros((T, n_s))
        controls = np.zeros((T, n_c))

        # Period 0: shock hits
        states[0, :] = R @ eps0
        controls[0, :] = Q @ states[0, :] + S @ eps0

        # Subsequent periods: no further shocks
        for t in range(1, T):
            states[t, :] = P @ states[t - 1, :]
            controls[t, :] = Q @ states[t, :]

        # Combine
        data = np.hstack([controls, states])
        irfs[shock_name] = pd.DataFrame(
            data,
            columns=solution['variable_names'],
            index=range(T),
        )
        irfs[shock_name].index.name = 'quarter'

        # Convert to percentage deviations (* 100)
        irfs[shock_name] = irfs[shock_name] * 100

    return irfs


# ═══════════════════════════════════════════════════════════════════════════
# 6. Regime comparison
# ═══════════════════════════════════════════════════════════════════════════

REGIME_LABELS = {
    'am_pf': 'Active Monetary / Passive Fiscal',
    'pm_af': 'Passive Monetary / Active Fiscal',
    'am_af': 'Active Monetary / Active Fiscal',
}

REGIME_COLOURS = {
    'am_pf': '#2196F3',
    'pm_af': '#F44336',
    'am_af': '#FF9800',
}


def compare_regimes(
    cal: DSGECalibration,
    regimes: Optional[List[str]] = None,
    shocks: Optional[List[str]] = None,
    T: int = 40,
) -> Dict[str, Dict]:
    """
    Run full analysis across multiple policy regimes.

    Returns
    -------
    dict: regime → {'ss': SteadyState, 'solution': dict, 'irfs': dict}
    """
    if regimes is None:
        regimes = ['am_pf', 'pm_af', 'am_af']

    results = {}
    for regime in regimes:
        ss = compute_steady_state(cal, regime=regime)
        sol = solve_linear_system(cal, ss, regime=regime)
        irf = simulate_irfs(cal, ss, sol, shocks=shocks, T=T)
        results[regime] = {
            'ss': ss,
            'solution': sol,
            'irfs': irf,
        }

    return results


# ═══════════════════════════════════════════════════════════════════════════
# 7. Policy analysis tools
# ═══════════════════════════════════════════════════════════════════════════

def compute_fiscal_multiplier(
    results: Dict[str, Dict],
    regime: str = 'am_pf',
    horizon: int = 20,
) -> Dict[str, float]:
    """
    Compute cumulative fiscal multiplier from fiscal shock IRFs.

    multiplier(h) = sum_{t=0}^{h} y_hat(t) / sum_{t=0}^{h} g_hat(t)
    """
    irf = results[regime]['irfs'].get('fiscal')
    if irf is None:
        return {'impact': np.nan, 'cumulative': np.nan}

    y_cum = irf['y_hat'].iloc[:horizon + 1].sum()
    g_cum = irf['g_hat'].iloc[:horizon + 1].sum()

    if abs(g_cum) < 1e-12:
        return {'impact': np.nan, 'cumulative': np.nan}

    impact = irf['y_hat'].iloc[0] / irf['g_hat'].iloc[0] if abs(irf['g_hat'].iloc[0]) > 1e-12 else np.nan

    return {
        'impact': impact,
        'cumulative': y_cum / g_cum,
        'horizon': horizon,
    }


def compute_sacrifice_ratio(
    results: Dict[str, Dict],
    regime: str = 'am_pf',
    horizon: int = 20,
) -> float:
    """
    Sacrifice ratio: cumulative output loss per unit of inflation reduction
    following a monetary policy shock.

    SR = - sum(y_hat) / sum(pi_hat)
    """
    irf = results[regime]['irfs'].get('monetary')
    if irf is None:
        return np.nan

    y_cum = irf['y_hat'].iloc[:horizon + 1].sum()
    pi_cum = irf['pi_hat'].iloc[:horizon + 1].sum()

    if abs(pi_cum) < 1e-12:
        return np.nan

    return -y_cum / pi_cum


def compute_debt_sustainability(
    cal: DSGECalibration,
    b_range: Optional[np.ndarray] = None,
) -> pd.DataFrame:
    """
    Compute the sovereign yield, risk premia, and required primary surplus
    across a range of debt-to-GDP ratios.

    Useful for visualising the "fiscal limit" region.
    """
    if b_range is None:
        b_range = np.linspace(0.1, 2.0, 200) / 4  # Quarterly

    rows = []
    for b_q in b_range:
        phi_eff = effective_phi_pi(b_q, cal)
        psi_pi = inflation_risk_premium(b_q, cal)
        psi_d = default_risk_premium(b_q, cal)
        # Natural rate
        r_nat = 1 / cal.beta - 1
        i = r_nat + 0.005  # Assume SS inflation
        R_gov = i + psi_pi + psi_d
        # Required primary surplus for debt stabilisation: (R_gov - g) * b
        # where g = growth rate ≈ 0 in SS
        req_surplus = R_gov * b_q
        captivity = max(1 - phi_eff / cal.phi_pi, 0)

        rows.append({
            'debt_gdp_annual': b_q * 4,
            'phi_pi_eff': phi_eff,
            'captivity': captivity,
            'psi_pi': psi_pi * 400,  # Annualise in bp
            'psi_d': psi_d * 400,
            'R_gov_annual': R_gov * 400,
            'req_surplus_gdp': req_surplus * 4,
        })

    return pd.DataFrame(rows)


def sensitivity_analysis(
    cal: DSGECalibration,
    param_name: str,
    param_range: np.ndarray,
    regime: str = 'am_pf',
    shock: str = 'fiscal',
    variable: str = 'y_hat',
    horizon: int = 20,
) -> pd.DataFrame:
    """
    Vary a single parameter and compute the IRF for a given variable.

    Returns DataFrame: rows = quarters, columns = parameter values.
    """
    results = []
    for val in param_range:
        cal_copy = DSGECalibration(**{
            **{f.name: getattr(cal, f.name)
               for f in cal.__dataclass_fields__.values()},
            param_name: val,
        })
        ss = compute_steady_state(cal_copy, regime=regime)
        sol = solve_linear_system(cal_copy, ss, regime=regime)
        irf = simulate_irfs(cal_copy, ss, sol, shocks=[shock], T=horizon)
        results.append(irf[shock][variable].values)

    return pd.DataFrame(
        np.array(results).T,
        columns=[f'{param_name}={v:.3f}' for v in param_range],
        index=range(horizon),
    )
