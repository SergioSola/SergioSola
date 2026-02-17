"""
Unit tests for the bank–NBFI systemic risk analysis pipeline.

Runs on synthetic data to validate that all modules produce
correctly shaped outputs and sensible values.
"""

import numpy as np
import pandas as pd
import pytest

from src.data.build_dataset import generate_synthetic_data
from src.analysis.network import (
    build_exposure_network,
    compute_centrality_measures,
    compute_network_statistics,
    rolling_network_statistics,
    bipartite_projection,
    compute_contagion_matrix,
)
from src.analysis.systemic_risk import (
    estimate_covar,
    compute_covar_panel,
    compute_mes,
    compute_srisk,
    compute_connectedness,
    granger_causality_network,
    aggregate_connectedness_by_sector,
)
from src.models.var_amplification import (
    Intermediary,
    FireSaleSimulation,
    build_bank_only_system,
    build_bank_nbfi_system,
    run_counterfactual,
    amplification_ratio,
    sector_procyclicality,
)
from src.analysis.global_financial_cycle import (
    extract_global_factor,
    build_synthetic_gfc_panel,
    panel_gfc_regression,
)


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def synthetic_data():
    return generate_synthetic_data(seed=123)


@pytest.fixture(scope="module")
def institutions(synthetic_data):
    return synthetic_data["institutions"]


@pytest.fixture(scope="module")
def returns(synthetic_data):
    return synthetic_data["returns"]


@pytest.fixture(scope="module")
def exposures(synthetic_data):
    return synthetic_data["exposures"]


@pytest.fixture(scope="module")
def weekly_returns(returns):
    return returns.resample("W").apply(lambda x: (1 + x).prod() - 1)


# ── Network tests ──────────────────────────────────────────────────────────

class TestNetwork:

    def test_build_network(self, exposures):
        G = build_exposure_network(exposures, date=exposures["date"].max())
        assert G.number_of_nodes() > 0
        assert G.number_of_edges() > 0

    def test_centrality_measures(self, exposures):
        G = build_exposure_network(exposures, date=exposures["date"].max())
        cent = compute_centrality_measures(G)
        assert "pagerank" in cent.columns
        assert "betweenness_centrality" in cent.columns
        assert (cent["pagerank"] >= 0).all()

    def test_network_statistics(self, exposures):
        G = build_exposure_network(exposures, date=exposures["date"].max())
        stats = compute_network_statistics(G)
        assert 0 <= stats["density"] <= 1
        assert stats["total_exposure"] > 0

    def test_rolling_network_stats(self, exposures):
        stats = rolling_network_statistics(exposures)
        assert len(stats) > 0
        assert "density" in stats.columns

    def test_bipartite_projection(self, exposures):
        G = bipartite_projection(exposures, date=exposures["date"].max())
        assert G.number_of_nodes() > 0

    def test_contagion_matrix(self, exposures, institutions):
        matrix = compute_contagion_matrix(
            exposures, institutions, date=exposures["date"].max()
        )
        assert matrix.shape[0] == matrix.shape[1]
        assert (matrix.values >= 0).all()


# ── Systemic risk tests ───────────────────────────────────────────────────

class TestSystemicRisk:

    def test_covar_single(self, weekly_returns):
        cols = weekly_returns.columns[:2]
        r = weekly_returns[cols].dropna()
        result = estimate_covar(r, system_col=cols[0], institution_col=cols[1])
        assert "covar" in result
        assert "delta_covar" in result
        assert np.isfinite(result["covar"])

    def test_covar_panel(self, weekly_returns, institutions):
        df = compute_covar_panel(weekly_returns, institutions)
        assert len(df) > 0
        assert "delta_covar" in df.columns
        assert "sector" in df.columns

    def test_mes(self, weekly_returns, institutions):
        df = compute_mes(weekly_returns, institutions)
        assert len(df) > 0
        # MES should be negative (losses on bad days)
        assert df["mes"].mean() < 0

    def test_srisk(self, weekly_returns, institutions):
        df = compute_srisk(weekly_returns, institutions)
        assert len(df) > 0
        assert "srisk" in df.columns
        assert "lrmes" in df.columns

    def test_connectedness(self, weekly_returns):
        # Use small subset for speed
        sub = weekly_returns.iloc[:200, :5].dropna()
        result = compute_connectedness(sub, lags=2, h=5)
        assert 0 <= result["total_connectedness"] <= 100
        assert result["theta"].shape == (5, 5)
        # Rows should sum to ~1
        np.testing.assert_allclose(
            result["theta"].sum(axis=1).values, 1.0, atol=0.01,
        )

    def test_granger_causality(self, weekly_returns):
        sub = weekly_returns.iloc[:200, :4].dropna()
        adj = granger_causality_network(sub, lags=2)
        assert adj.shape == (4, 4)
        # Diagonal should be zero
        np.testing.assert_array_equal(np.diag(adj.values), 0)

    def test_sector_aggregation(self, weekly_returns, institutions):
        sub = weekly_returns.iloc[:200, :8].dropna()
        conn = compute_connectedness(sub, lags=2, h=5)
        sector_theta = aggregate_connectedness_by_sector(
            conn["theta"], institutions
        )
        assert sector_theta.shape[0] > 0
        assert sector_theta.shape[0] == sector_theta.shape[1]


# ── VaR amplification tests ───────────────────────────────────────────────

class TestVaRAmplification:

    def test_intermediary(self):
        agent = Intermediary(
            name="test", sector="bank",
            assets=1000, equity=100, volatility=0.02,
        )
        assert agent.leverage == 10.0
        assert agent.var_limit > 0

    def test_fire_sale_simulation(self):
        agents = build_bank_only_system(n_banks=5, total_assets=5e5)
        sim = FireSaleSimulation(intermediaries=agents, market_depth=1e5)
        hist = sim.run(initial_shock=-0.05)
        assert len(hist) > 1
        # Price should decline
        assert hist.iloc[-1]["asset_price"] < hist.iloc[0]["asset_price"]

    def test_counterfactual(self):
        histories = run_counterfactual(
            initial_shock=-0.03, market_depth=1e6,
        )
        assert "bank_only" in histories
        assert "bank_nbfi" in histories
        amp = amplification_ratio(histories)
        assert np.isfinite(amp["amplification_ratio"])

    def test_nbfi_amplifies(self):
        """The bank+NBFI system should have a larger price drop."""
        histories = run_counterfactual(
            initial_shock=-0.05, market_depth=5e5,
        )
        amp = amplification_ratio(histories)
        # Amplification ratio should be > 1 (mixed system drops more)
        assert amp["amplification_ratio"] >= 1.0

    def test_procyclicality(self, returns, institutions):
        result = sector_procyclicality(returns.iloc[:500], institutions)
        assert len(result) > 0
        assert "beta_procyclicality" in result.columns


# ── Global financial cycle tests ───────────────────────────────────────────

class TestGlobalFinancialCycle:

    def test_extract_factor(self, weekly_returns):
        result = extract_global_factor(weekly_returns, n_components=3)
        assert result["global_factor"].shape[1] == 3
        assert result["explained_variance_ratio"][0] > 0
        # First PC should explain more than second
        assert (result["explained_variance_ratio"][0]
                >= result["explained_variance_ratio"][1])

    def test_synthetic_panel(self):
        panel = build_synthetic_gfc_panel(n_countries=5, n_periods=40)
        assert len(panel) == 5 * 40
        assert "credit_growth" in panel.columns
        assert "gfc_factor" in panel.columns

    def test_panel_regression(self):
        panel = build_synthetic_gfc_panel(
            true_amplification=0.8, n_countries=10, n_periods=60,
        )
        reg = panel_gfc_regression(panel)
        # The interaction term should be positive and significant
        assert reg.params.get("gfc_x_nbfi", 0) > 0
        assert reg.pvalues.get("gfc_x_nbfi", 1) < 0.10
