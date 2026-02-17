"""
Tests for DCC-GARCH, NBFI subsector models, and real data loaders.
"""

import numpy as np
import pandas as pd
import pytest

from src.data.build_dataset import generate_synthetic_data
from src.models.dcc_garch import (
    fit_univariate_garch,
    fit_all_garch,
    estimate_dcc,
    sector_average_correlation,
)
from src.models.nbfi_subsectors import (
    build_pension_sector, LDIMarginSpiral,
    build_mmf_sector, MMFRunSimulation,
    build_hedge_fund_sector, PrimeBrokerageContagion,
)
from src.data.real_data_loaders import _build_institution_metadata


@pytest.fixture(scope="module")
def synthetic_data():
    return generate_synthetic_data(seed=99)


@pytest.fixture(scope="module")
def weekly_returns(synthetic_data):
    r = synthetic_data["returns"]
    return r.resample("W").apply(lambda x: (1 + x).prod() - 1)


# ── DCC-GARCH tests ───────────────────────────────────────────────────────

class TestDCCGARCH:

    def test_univariate_garch(self, weekly_returns):
        col = weekly_returns.columns[0]
        result = fit_univariate_garch(weekly_returns[col])
        assert len(result["conditional_vol"]) > 0
        assert len(result["std_resid"]) > 0
        assert (result["conditional_vol"] > 0).all()

    def test_fit_all_garch(self, weekly_returns):
        sub = weekly_returns.iloc[:, :4]
        result = fit_all_garch(sub)
        assert len(result["models"]) > 0
        assert result["conditional_vols"].shape[1] > 0
        assert result["std_resids"].shape[1] > 0

    def test_dcc_estimation(self, weekly_returns):
        sub = weekly_returns.iloc[:, :3].dropna()
        garch = fit_all_garch(sub)
        dcc = estimate_dcc(garch["std_resids"])
        assert 0 < dcc["a"] < 1
        assert 0 < dcc["b"] < 1
        assert dcc["persistence"] < 1
        assert len(dcc["dynamic_correlations"]) > 0

    def test_dcc_correlations_bounded(self, weekly_returns):
        sub = weekly_returns.iloc[:, :3].dropna()
        garch = fit_all_garch(sub)
        dcc = estimate_dcc(garch["std_resids"])
        for _, corr in dcc["dynamic_correlations"].items():
            assert corr.min() >= -1.1  # small tolerance
            assert corr.max() <= 1.1


# ── LDI Margin Spiral tests ───────────────────────────────────────────────

class TestLDIMarginSpiral:

    def test_build_pension_sector(self):
        funds = build_pension_sector(n_funds=10)
        assert len(funds) == 10
        assert all(f.assets > 0 for f in funds)

    def test_ldi_simulation_runs(self):
        funds = build_pension_sector(n_funds=10)
        sim = LDIMarginSpiral(pension_funds=funds, market_depth=1e7)
        hist = sim.run(yield_shock_bps=50)
        assert len(hist) > 1
        # Yields should increase during spiral
        assert hist.iloc[-1]["yield_bps"] >= hist.iloc[0]["yield_bps"]

    def test_larger_shock_worse(self):
        funds1 = build_pension_sector(n_funds=10, seed=1)
        funds2 = build_pension_sector(n_funds=10, seed=1)
        sim1 = LDIMarginSpiral(pension_funds=funds1, market_depth=1e7)
        sim2 = LDIMarginSpiral(pension_funds=funds2, market_depth=1e7)
        h1 = sim1.run(yield_shock_bps=30)
        h2 = sim2.run(yield_shock_bps=100)
        assert h2.iloc[-1]["yield_bps"] >= h1.iloc[-1]["yield_bps"]


# ── MMF Run tests ──────────────────────────────────────────────────────────

class TestMMFRun:

    def test_build_mmf_sector(self):
        funds = build_mmf_sector(n_funds=10)
        assert len(funds) == 10
        assert all(f.aum > 0 for f in funds)

    def test_mmf_simulation_runs(self):
        funds = build_mmf_sector(n_funds=10)
        sim = MMFRunSimulation(funds=funds)
        hist = sim.run(initial_credit_loss_pct=0.005)
        assert len(hist) > 0
        # AUM should decline
        assert hist.iloc[-1]["total_aum"] < hist.iloc[0]["total_aum"]

    def test_cp_spreads_widen(self):
        funds = build_mmf_sector(n_funds=10)
        sim = MMFRunSimulation(funds=funds)
        hist = sim.run(initial_credit_loss_pct=0.01)
        assert hist.iloc[-1]["cp_spread_bps"] >= hist.iloc[0]["cp_spread_bps"]


# ── Hedge Fund Deleveraging tests ──────────────────────────────────────────

class TestHedgeFundDeleveraging:

    def test_build_hf_sector(self):
        funds = build_hedge_fund_sector(n_funds=15)
        assert len(funds) == 15
        assert all(f.nav > 0 for f in funds)

    def test_pb_simulation_runs(self):
        funds = build_hedge_fund_sector(n_funds=15)
        sim = PrimeBrokerageContagion(hedge_funds=funds, market_depth=5e5)
        hist = sim.run(initial_shock=-0.04)
        assert len(hist) > 1
        # NAV should decline
        assert hist.iloc[-1]["total_nav"] < hist.iloc[0]["total_nav"]


# ── Real data loader tests ─────────────────────────────────────────────────

class TestRealDataLoaders:

    def test_institution_metadata(self):
        meta = _build_institution_metadata()
        assert len(meta) > 20
        assert "sector" in meta.columns
        assert "bank" in meta["sector"].values
