"""
Unit tests for the Monetary-Fiscal Interactions (MFI) analysis modules.

Validates calibration, steady-state computation, risk premia functions,
and data loaders using synthetic data.
"""

import numpy as np
import pandas as pd
import pytest

from src.analysis.monetary_fiscal import (
    DSGECalibration,
    SteadyState,
    compute_steady_state,
    effective_phi_pi,
    inflation_risk_premium,
    default_risk_premium,
    sovereign_yield,
    solve_linear_system,
    simulate_irfs,
    compare_regimes,
)
from src.data.mfi_data_loaders import (
    load_imf_weo_data,
    load_sovereign_yields,
    build_calibration_targets,
)


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def calibration():
    return DSGECalibration()


@pytest.fixture(scope="module")
def steady_state_am_pf(calibration):
    return compute_steady_state(calibration, regime="am_pf")


@pytest.fixture(scope="module")
def steady_state_pm_af(calibration):
    return compute_steady_state(calibration, regime="pm_af")


# ── Calibration tests ────────────────────────────────────────────────────

class TestCalibration:

    def test_default_values(self, calibration):
        assert calibration.beta == 0.99
        assert calibration.phi_pi == 1.50
        assert calibration.phi_pi_cap == 0.50
        assert calibration.b_max > calibration.b_ss

    def test_taylor_principle(self, calibration):
        """Active monetary policy satisfies the Taylor principle."""
        assert calibration.phi_pi > 1.0

    def test_captive_below_taylor(self, calibration):
        """Captive CB violates the Taylor principle."""
        assert calibration.phi_pi_cap < 1.0

    def test_positive_parameters(self, calibration):
        assert calibration.beta > 0
        assert calibration.sigma > 0
        assert calibration.alpha > 0
        assert calibration.alpha < 1
        assert calibration.kappa > 0


# ── Steady state tests ──────────────────────────────────────────────────

class TestSteadyState:

    def test_output_normalised(self, steady_state_am_pf):
        assert steady_state_am_pf.Y == 1.0

    def test_positive_consumption(self, steady_state_am_pf):
        assert steady_state_am_pf.C > 0

    def test_resource_constraint(self, steady_state_am_pf):
        """Y = C + I + G in steady state."""
        ss = steady_state_am_pf
        np.testing.assert_allclose(
            ss.Y, ss.C + ss.I + ss.G, atol=1e-10,
        )

    def test_sovereign_rate_above_policy(self, steady_state_am_pf):
        """Sovereign yield >= policy rate (risk premia are non-negative)."""
        ss = steady_state_am_pf
        assert ss.R_gov >= ss.i - 1e-10

    def test_corporate_above_sovereign(self, steady_state_am_pf):
        """Corporate rate > sovereign rate."""
        ss = steady_state_am_pf
        assert ss.R_corp > ss.R_gov

    def test_bank_balance_sheet(self, steady_state_am_pf):
        """Assets = Liabilities + Equity."""
        ss = steady_state_am_pf
        assets = ss.B_gov + ss.L_corp
        liabilities_equity = ss.D + ss.E_bank
        np.testing.assert_allclose(assets, liabilities_equity, atol=1e-10)

    def test_default_probability_bounded(self, steady_state_am_pf):
        """Default probability is between 0 and 1."""
        assert 0 <= steady_state_am_pf.P_def <= 1

    def test_fiscal_dominance_higher_inflation_premium(
        self, steady_state_am_pf, steady_state_pm_af,
    ):
        """Inflation risk premium is higher under fiscal dominance."""
        assert steady_state_pm_af.psi_pi > steady_state_am_pf.psi_pi

    def test_government_budget(self, steady_state_am_pf, calibration):
        """Taxes cover spending + interest in SS."""
        ss = steady_state_am_pf
        required_taxes = ss.G + ss.R_gov * ss.B_gov
        np.testing.assert_allclose(ss.T, required_taxes, atol=1e-10)


# ── Captivity mechanism tests ────────────────────────────────────────────

class TestCaptivityMechanism:

    def test_no_captivity_at_low_debt(self, calibration):
        """Far below debt limit, phi_pi is close to phi_pi (active)."""
        b_low = 0.01  # Very low debt, well below quarterly limit
        phi = effective_phi_pi(b_low, calibration)
        # Should be much closer to active (1.5) than captive (0.5)
        assert phi > (calibration.phi_pi + calibration.phi_pi_cap) / 2

    def test_captivity_at_high_debt(self, calibration):
        """Well above debt limit, phi_pi approaches phi_pi_cap."""
        b_high = calibration.b_max / 4 + 0.5  # Well above quarterly limit
        phi = effective_phi_pi(b_high, calibration)
        assert abs(phi - calibration.phi_pi_cap) < 0.05

    def test_monotonic_transition(self, calibration):
        """phi_pi decreases monotonically as debt increases."""
        debts = np.linspace(0.05, 0.5, 50)
        phis = [effective_phi_pi(b, calibration) for b in debts]
        # Should be non-increasing
        for i in range(1, len(phis)):
            assert phis[i] <= phis[i - 1] + 1e-10

    def test_inflation_premium_zero_at_low_debt(self, calibration):
        """Inflation risk premium is ~0 when debt is low."""
        b_low = 0.01  # Very low debt
        psi = inflation_risk_premium(b_low, calibration)
        assert psi < 1e-4

    def test_inflation_premium_positive_at_high_debt(self, calibration):
        """Inflation risk premium is positive near debt limit."""
        b_high = calibration.b_max / 4
        psi = inflation_risk_premium(b_high, calibration)
        assert psi > 0

    def test_sovereign_yield_composition(self, calibration):
        """Sovereign yield = policy rate + inflation premium + default premium."""
        i = 0.01
        b = calibration.b_ss / 4
        y = sovereign_yield(i, b, calibration)
        psi_pi = inflation_risk_premium(b, calibration)
        psi_d = default_risk_premium(b, calibration)
        np.testing.assert_allclose(y, i + psi_pi + psi_d, atol=1e-12)


# ── Solution and IRF tests ──────────────────────────────────────────────

class TestSolutionAndIRFs:

    def test_solve_returns_structure(self, calibration, steady_state_am_pf):
        sol = solve_linear_system(calibration, steady_state_am_pf, "am_pf")
        assert "policy_matrix" in sol
        assert "transition_matrix" in sol
        assert "variable_names" in sol
        assert sol["n_states"] > 0
        assert sol["n_controls"] > 0

    def test_irf_shape(self, calibration, steady_state_am_pf):
        sol = solve_linear_system(calibration, steady_state_am_pf, "am_pf")
        irfs = simulate_irfs(calibration, steady_state_am_pf, sol, T=20)
        for shock_name, df in irfs.items():
            assert len(df) == 20
            assert list(df.columns) == sol["variable_names"]

    def test_compare_regimes(self, calibration):
        results = compare_regimes(calibration, T=10)
        assert "am_pf" in results
        assert "pm_af" in results
        assert "am_af" in results


# ── Data loader tests ────────────────────────────────────────────────────

class TestDataLoaders:

    def test_synthetic_weo_data(self):
        df = load_imf_weo_data(countries=["USA", "DEU"])
        assert len(df) > 0
        assert "country" in df.columns
        assert "debt_gdp" in df.columns

    def test_synthetic_yields(self):
        df = load_sovereign_yields()
        assert len(df) > 0
        assert "country" in df.columns
        assert "yield" in df.columns
        assert "maturity" in df.columns

    def test_calibration_targets(self):
        targets = build_calibration_targets(country="USA")
        assert "debt_gdp" in targets
        assert "inflation" in targets
        assert "sovereign_yield_10y" in targets
        assert isinstance(targets["debt_gdp"], float)
