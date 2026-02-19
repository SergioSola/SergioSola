"""
Monetary-Fiscal Interactions: DSGE model specification, calibration, and solution.

This module implements the core model for the MFI research programme:
  - Calibration dataclass with all structural parameters
  - Steady-state solver
  - Log-linearised system assembly
  - Perturbation-based solution (first-order)
  - Impulse response simulation
  - Regime comparison tools

Model features:
  - Households (habit formation), firms (Calvo pricing, BGG default),
    banks (sovereign + corporate lending), government (fiscal rule + debt limit),
    central bank (Taylor rule + captivity), foreign sector (UIP + risk premium).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from scipy import optimize, linalg


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

    # Banks
    kappa: float = 0.08          # Minimum capital adequacy ratio
    chi_spread: float = 0.02     # Base credit spread (annualised)

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
    I: float = 0.0       # Investment
    W: float = 0.0       # Real wage
    pi: float = 0.0      # Inflation (net, quarterly)
    i: float = 0.0       # Policy rate (quarterly)
    R_gov: float = 0.0   # Sovereign bond rate
    R_corp: float = 0.0  # Corporate loan rate
    b: float = 0.0       # Debt-to-GDP
    G: float = 0.0       # Government spending
    T: float = 0.0       # Taxes
    D: float = 0.0       # Bank deposits
    E_bank: float = 0.0  # Bank equity
    L_corp: float = 0.0  # Corporate loans
    B_gov: float = 0.0   # Bank sovereign bond holdings
    P_def: float = 0.0   # Firm default probability
    psi_pi: float = 0.0  # Inflation risk premium
    psi_d: float = 0.0   # Default risk premium
    e: float = 0.0       # Exchange rate (log)
    nfa: float = 0.0     # Net foreign assets / GDP
    xi: float = 0.0      # Foreign risk premium
    f: float = 0.0       # Foreign ownership share


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

    # Policy rate
    r_natural = 1 / cal.beta - 1  # Natural rate (quarterly)
    ss.i = r_natural + pi_target

    # Debt-to-GDP
    ss.b = cal.b_ss / 4  # Convert annual to quarterly

    # Risk premia at steady state (depend on regime)
    if regime == "pm_af":
        # Under fiscal dominance, CB is partially captive at SS
        captivity_degree = 1 - cal.phi_pi_cap / cal.phi_pi
        ss.psi_pi = cal.psi_pi_bar * captivity_degree ** cal.eta / 4
        accommodation = captivity_degree
    else:
        # Active monetary policy: no captivity at SS
        ss.psi_pi = 0.0
        accommodation = 0.0

    ss.psi_d = (cal.psi_d_bar / 4) * np.exp(
        cal.delta_1 * (ss.b - cal.b_ss / 4) - cal.delta_2 * accommodation
    )

    # Sovereign yield
    ss.R_gov = ss.i + ss.psi_pi + ss.psi_d

    # Corporate rate
    ss.R_corp = ss.R_gov + cal.chi_spread / 4

    # Output normalised to 1
    ss.Y = 1.0
    ss.G = cal.g_ss * ss.Y

    # Government budget in SS: T = G + R_gov * B (where B = b * Y)
    ss.B_gov = ss.b * ss.Y
    ss.T = ss.G + ss.R_gov * ss.B_gov

    # Production side
    ss.N = 0.33  # Target: ~1/3 of time working
    ss.K = (cal.alpha / (r_natural + cal.delta_k)) * ss.Y
    ss.I = cal.delta_k * ss.K
    ss.W = (1 - cal.alpha) * ss.Y / ss.N

    # Consumption
    ss.C = ss.Y - ss.I - ss.G

    # Banking
    ss.L_corp = 0.5 * ss.Y  # Corporate loans ~ 50% of GDP
    ss.E_bank = cal.kappa * (ss.B_gov + ss.L_corp)
    ss.D = ss.B_gov + ss.L_corp - ss.E_bank

    # Firm default probability (steady state)
    from scipy.stats import norm
    leverage_ratio = ss.R_corp * ss.L_corp / ss.Y
    ss.P_def = norm.cdf(
        (np.log(leverage_ratio) + 0.5 * cal.sigma_omega**2) / cal.sigma_omega
    )

    # Open economy
    ss.xi = cal.xi_bar
    ss.f = cal.f_ss
    ss.e = 0.0  # Log exchange rate normalised
    ss.nfa = 0.0  # NFA at zero in SS

    return ss


# ═══════════════════════════════════════════════════════════════════════════
# 3. Captivity mechanism
# ═══════════════════════════════════════════════════════════════════════════

def effective_phi_pi(
    b: float,
    cal: DSGECalibration,
) -> float:
    """
    Compute the effective Taylor rule inflation coefficient
    as a logistic function of the debt-to-GDP ratio.

    When b is far below b_max: returns phi_pi (active).
    When b approaches b_max: smoothly transitions to phi_pi_cap (captive).
    """
    b_max_q = cal.b_max / 4  # Quarterly
    transition = 1 / (1 + np.exp(-cal.gamma_cap * (b - b_max_q)))
    return cal.phi_pi - (cal.phi_pi - cal.phi_pi_cap) * transition


def inflation_risk_premium(
    b: float,
    cal: DSGECalibration,
) -> float:
    """Inflation risk premium as a function of effective captivity."""
    phi_eff = effective_phi_pi(b, cal)
    captivity = 1 - phi_eff / cal.phi_pi
    return (cal.psi_pi_bar / 4) * max(captivity, 0) ** cal.eta


def default_risk_premium(
    b: float,
    cal: DSGECalibration,
) -> float:
    """Default risk premium as a function of debt and accommodation."""
    phi_eff = effective_phi_pi(b, cal)
    accommodation = max(1 - phi_eff / cal.phi_pi, 0)
    b_dev = b - cal.b_ss / 4
    return (cal.psi_d_bar / 4) * np.exp(cal.delta_1 * b_dev - cal.delta_2 * accommodation)


def sovereign_yield(
    i: float,
    b: float,
    cal: DSGECalibration,
) -> float:
    """Total sovereign bond yield: policy rate + inflation premium + default premium."""
    return i + inflation_risk_premium(b, cal) + default_risk_premium(b, cal)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Linear system (placeholder for log-linearised equations)
# ═══════════════════════════════════════════════════════════════════════════

def solve_linear_system(
    cal: DSGECalibration,
    ss: SteadyState,
    regime: str = "am_pf",
) -> Dict:
    """
    Assemble and solve the log-linearised DSGE system.

    Uses the method of undetermined coefficients (Blanchard-Kahn)
    or the QZ decomposition for the state-space representation:

        A E_t[x_{t+1}] = B x_t + C e_t

    Parameters
    ----------
    cal : DSGECalibration
    ss : SteadyState
    regime : str

    Returns
    -------
    dict with keys:
        'policy_matrix' : np.ndarray (policy function coefficients)
        'transition_matrix' : np.ndarray (state transition)
        'variable_names' : list of variable names
        'n_states' : int
        'n_controls' : int
    """
    # TODO: Implement full log-linearisation
    # This is a placeholder that returns the structure
    variables = [
        'y_hat', 'c_hat', 'n_hat', 'pi_hat', 'i_hat',
        'r_gov_hat', 'r_corp_hat', 'b_hat', 'e_hat',
        'psi_pi_hat', 'psi_d_hat', 'p_def_hat',
        'a_hat', 'g_hat', 'xi_hat', 'eps_mp',
    ]
    n_vars = len(variables)
    n_states = 4   # a, g, xi, b (predetermined)
    n_controls = n_vars - n_states

    return {
        'policy_matrix': np.zeros((n_controls, n_states)),
        'transition_matrix': np.zeros((n_states, n_states)),
        'variable_names': variables,
        'n_states': n_states,
        'n_controls': n_controls,
        'regime': regime,
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
    Simulate impulse response functions for specified shocks.

    Parameters
    ----------
    cal : DSGECalibration
    ss : SteadyState
    solution : dict from solve_linear_system()
    shocks : list of shock names ('fiscal', 'monetary', 'productivity', 'risk_premium')
    T : int, number of periods

    Returns
    -------
    dict mapping shock name → DataFrame of IRFs (rows = periods, cols = variables)
    """
    if shocks is None:
        shocks = ['fiscal', 'monetary', 'productivity', 'risk_premium']

    shock_sizes = {
        'fiscal': cal.sig_fiscal,
        'monetary': cal.sig_mp,
        'productivity': cal.sig_a,
        'risk_premium': cal.sig_xi,
    }

    irfs = {}
    for shock_name in shocks:
        size = shock_sizes.get(shock_name, 0.01)
        # Placeholder: generate zero IRFs until model is solved
        irf_data = np.zeros((T, len(solution['variable_names'])))
        irfs[shock_name] = pd.DataFrame(
            irf_data,
            columns=solution['variable_names'],
            index=range(T),
        )
        irfs[shock_name].index.name = 'quarter'

    return irfs


# ═══════════════════════════════════════════════════════════════════════════
# 6. Regime comparison
# ═══════════════════════════════════════════════════════════════════════════

REGIME_LABELS = {
    'am_pf': 'Active Monetary / Passive Fiscal',
    'pm_af': 'Passive Monetary / Active Fiscal',
    'am_af': 'Active Monetary / Active Fiscal',
}


def compare_regimes(
    cal: DSGECalibration,
    regimes: Optional[List[str]] = None,
    shocks: Optional[List[str]] = None,
    T: int = 40,
) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Run IRF analysis across multiple policy regimes.

    Returns
    -------
    Nested dict: regime → shock → DataFrame of IRFs
    """
    if regimes is None:
        regimes = ['am_pf', 'pm_af', 'am_af']

    results = {}
    for regime in regimes:
        ss = compute_steady_state(cal, regime=regime)
        sol = solve_linear_system(cal, ss, regime=regime)
        results[regime] = simulate_irfs(cal, ss, sol, shocks=shocks, T=T)

    return results
