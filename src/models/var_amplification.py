"""
VaR-constraint amplification model.

Implements the Adrian & Shin (2010, 2014) framework for procyclical leverage
driven by Value-at-Risk constraints, extended to include non-bank financial
intermediaries alongside banks.

The key mechanism:
  - Intermediaries target a VaR constraint: Pr(Loss > VaR) <= alpha
  - With normally distributed returns: VaR = z_alpha * sigma * Assets
  - Capital constraint: Equity >= VaR => Leverage <= 1 / (z_alpha * sigma)
  - When sigma falls, leverage expands; when sigma rises, forced deleveraging.

This module provides:
  1. Procyclicality regressions (leverage on asset values)
  2. A multi-agent simulation of the leverage-fire-sale spiral
  3. Counterfactual analysis: bank-only vs. bank+NBFI systems
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
import statsmodels.api as sm
from dataclasses import dataclass, field
from typing import Optional

from src.utils.config import VAR_CONFIDENCE, GARCH_P, GARCH_Q


# ═══════════════════════════════════════════════════════════════════════════
# 1. Procyclicality Regressions (Adrian & Shin 2010)
# ═══════════════════════════════════════════════════════════════════════════

def procyclicality_regression(
    leverage: pd.Series,
    asset_growth: pd.Series,
    controls: Optional[pd.DataFrame] = None,
) -> sm.regression.linear_model.RegressionResultsWrapper:
    """
    Estimate the procyclicality of leverage:

        Δlog(Leverage_t) = α + β · Δlog(Assets_t) + γ · X_t + ε_t

    Under passive leverage management (constant debt), β ≈ 0.
    Under active VaR-targeting, β > 0 (leverage moves with asset values).

    Parameters
    ----------
    leverage : Series of leverage ratios (Assets / Equity).
    asset_growth : Series of log-changes in total assets.
    controls : Optional control variables (VIX, rates, etc.).

    Returns
    -------
    statsmodels OLS regression result.
    """
    dlev = np.log(leverage).diff().dropna()
    dasset = asset_growth.reindex(dlev.index)

    common = dlev.dropna().index.intersection(dasset.dropna().index)
    y = dlev.loc[common]
    X = dasset.loc[common].to_frame("asset_growth")

    if controls is not None:
        controls = controls.reindex(common).dropna()
        common = common.intersection(controls.index)
        y = y.loc[common]
        X = X.loc[common]
        X = pd.concat([X, controls.loc[common]], axis=1)

    X = sm.add_constant(X)
    model = sm.OLS(y, X)
    return model.fit(cov_type="HC1")


def sector_procyclicality(
    returns: pd.DataFrame,
    institutions: pd.DataFrame,
    window: int = 60,
) -> pd.DataFrame:
    """
    Estimate procyclicality coefficient β for each sector.

    Uses rolling-window estimated volatility as a proxy for VaR-implied
    leverage: Leverage_proxy = 1 / (z_alpha * sigma_rolling).

    Returns DataFrame with sector-level β estimates and t-statistics.
    """
    z = sp_stats.norm.ppf(VAR_CONFIDENCE)
    ticker_to_sector = dict(zip(institutions["ticker"], institutions["sector"]))

    results = []
    for col in returns.columns:
        if col not in ticker_to_sector:
            continue
        r = returns[col].dropna()
        if len(r) < window + 20:
            continue

        # Rolling volatility → implied leverage
        sigma = r.rolling(window).std()
        leverage_proxy = 1 / (z * sigma)
        leverage_proxy = leverage_proxy.replace([np.inf, -np.inf], np.nan).dropna()

        # Cumulative return as proxy for asset value
        cum_ret = (1 + r).cumprod()
        asset_growth = np.log(cum_ret).diff()

        common = leverage_proxy.index.intersection(asset_growth.dropna().index)
        if len(common) < 30:
            continue

        try:
            reg = procyclicality_regression(
                leverage_proxy.loc[common],
                asset_growth.loc[common],
            )
            results.append({
                "ticker": col,
                "sector": ticker_to_sector[col],
                "beta_procyclicality": reg.params.get("asset_growth", np.nan),
                "t_stat": reg.tvalues.get("asset_growth", np.nan),
                "r_squared": reg.rsquared,
                "n_obs": int(reg.nobs),
            })
        except Exception:
            continue

    return pd.DataFrame(results)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Multi-Agent Fire-Sale Simulation
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Intermediary:
    """A VaR-constrained financial intermediary."""
    name: str
    sector: str
    assets: float                    # total assets
    equity: float                    # equity capital
    var_confidence: float = 0.99     # VaR confidence level
    volatility: float = 0.02        # current estimated volatility
    price_impact: float = 0.0       # share of market (for fire-sale impact)
    max_leverage: float = 50.0      # regulatory or practical ceiling
    is_var_constrained: bool = True  # whether entity follows VaR targeting

    @property
    def leverage(self) -> float:
        return self.assets / self.equity if self.equity > 0 else np.inf

    @property
    def var_limit(self) -> float:
        """Maximum leverage implied by VaR constraint."""
        z = sp_stats.norm.ppf(self.var_confidence)
        return min(1 / (z * self.volatility), self.max_leverage)

    @property
    def excess_leverage(self) -> float:
        """Positive if leverage exceeds VaR-implied limit (must deleverage)."""
        return max(0, self.leverage - self.var_limit)

    def required_asset_sale(self) -> float:
        """
        Amount of assets that must be sold to satisfy VaR constraint.

        If leverage > var_limit, the firm must reduce assets:
            ΔA = A - var_limit * E
        """
        if not self.is_var_constrained or self.excess_leverage <= 0:
            return 0.0
        target_assets = self.var_limit * self.equity
        return max(0, self.assets - target_assets)

    def apply_shock(self, return_shock: float):
        """Apply a return shock to the balance sheet."""
        asset_change = self.assets * return_shock
        self.assets += asset_change
        self.equity += asset_change  # debt is fixed in short run

    def deleverage(self, amount: float):
        """Sell assets and repay debt (equity unchanged)."""
        self.assets -= amount
        # equity unchanged; debt reduced by 'amount'

    def update_volatility(self, new_vol: float):
        """Update estimated volatility (e.g., from EWMA or GARCH)."""
        self.volatility = new_vol


@dataclass
class FireSaleSimulation:
    """
    Simulates the leverage-fire-sale amplification mechanism.

    Multiple VaR-constrained intermediaries hold a common risky asset.
    An initial shock reduces asset values, which:
      1. Raises measured volatility (EWMA update)
      2. Tightens VaR constraints
      3. Forces deleveraging (fire sales)
      4. Fire sales depress prices further (price impact)
      5. Repeat until equilibrium or failure
    """
    intermediaries: list[Intermediary]
    asset_price: float = 100.0
    market_depth: float = 1e6       # price impact = sales / market_depth
    vol_ewma_lambda: float = 0.94   # EWMA decay for volatility updating
    max_rounds: int = 50
    convergence_tol: float = 1e-6

    # History tracking
    history: list[dict] = field(default_factory=list)

    def total_assets(self) -> float:
        return sum(i.assets for i in self.intermediaries)

    def total_equity(self) -> float:
        return sum(i.equity for i in self.intermediaries)

    def aggregate_leverage(self) -> float:
        eq = self.total_equity()
        return self.total_assets() / eq if eq > 0 else np.inf

    def _record_state(self, round_num: int, trigger: str):
        self.history.append({
            "round": round_num,
            "trigger": trigger,
            "asset_price": self.asset_price,
            "total_assets": self.total_assets(),
            "total_equity": self.total_equity(),
            "aggregate_leverage": self.aggregate_leverage(),
            "n_active": sum(1 for i in self.intermediaries if i.equity > 0),
            "total_fire_sales": sum(
                i.required_asset_sale() for i in self.intermediaries
            ),
        })

    def run(self, initial_shock: float = -0.05) -> pd.DataFrame:
        """
        Run the fire-sale simulation.

        Parameters
        ----------
        initial_shock : Initial return shock (e.g., -0.05 = -5%).

        Returns
        -------
        DataFrame of simulation history (one row per round).
        """
        self.history = []
        self._record_state(0, "initial")

        # Round 0: apply initial shock
        price_change = initial_shock
        self.asset_price *= (1 + price_change)

        for agent in self.intermediaries:
            agent.apply_shock(price_change)
            # Update volatility (EWMA)
            new_vol = np.sqrt(
                self.vol_ewma_lambda * agent.volatility ** 2
                + (1 - self.vol_ewma_lambda) * price_change ** 2
            )
            agent.update_volatility(new_vol)

        self._record_state(1, "initial_shock")

        # Iterative fire-sale rounds
        for round_num in range(2, self.max_rounds + 2):
            total_sales = 0
            for agent in self.intermediaries:
                if agent.equity <= 0:
                    continue
                sale = agent.required_asset_sale()
                if sale > 0:
                    agent.deleverage(sale)
                    total_sales += sale

            if total_sales < self.convergence_tol:
                self._record_state(round_num, "converged")
                break

            # Price impact of fire sales
            price_impact = -total_sales / self.market_depth
            self.asset_price *= (1 + price_impact)

            # Apply price impact to remaining portfolios
            for agent in self.intermediaries:
                if agent.equity <= 0:
                    continue
                agent.apply_shock(price_impact)
                new_vol = np.sqrt(
                    self.vol_ewma_lambda * agent.volatility ** 2
                    + (1 - self.vol_ewma_lambda) * price_impact ** 2
                )
                agent.update_volatility(new_vol)

            self._record_state(round_num, "fire_sale_round")

        return pd.DataFrame(self.history)


def build_bank_only_system(
    n_banks: int = 10,
    total_assets: float = 1e6,
    avg_leverage: float = 12,
    seed: int = 42,
) -> list[Intermediary]:
    """Create a system with only banks."""
    rng = np.random.default_rng(seed)
    intermediaries = []
    for i in range(n_banks):
        assets = total_assets / n_banks * rng.uniform(0.7, 1.3)
        equity = assets / avg_leverage * rng.uniform(0.8, 1.2)
        intermediaries.append(Intermediary(
            name=f"Bank_{i}",
            sector="bank",
            assets=assets,
            equity=equity,
            var_confidence=0.99,
            volatility=rng.uniform(0.01, 0.03),
        ))
    return intermediaries


def build_bank_nbfi_system(
    n_banks: int = 10,
    n_hedge_funds: int = 5,
    n_inv_funds: int = 8,
    n_pension: int = 4,
    n_insurance: int = 3,
    total_bank_assets: float = 1e6,
    total_nbfi_assets: float = 8e5,
    seed: int = 42,
) -> list[Intermediary]:
    """Create a mixed system with banks and various NBFI types."""
    rng = np.random.default_rng(seed)
    intermediaries = []

    # Banks
    for i in range(n_banks):
        assets = total_bank_assets / n_banks * rng.uniform(0.7, 1.3)
        intermediaries.append(Intermediary(
            name=f"Bank_{i}",
            sector="bank",
            assets=assets,
            equity=assets / rng.uniform(10, 15),
            var_confidence=0.99,
            volatility=rng.uniform(0.01, 0.025),
        ))

    # NBFI type parameters: (count, label, leverage_range, vol_range, VaR conf)
    nbfi_specs = [
        (n_hedge_funds, "hedge_fund", (5, 25), (0.02, 0.05), 0.99),
        (n_inv_funds, "investment_fund", (1, 3), (0.01, 0.03), 0.95),
        (n_pension, "pension_fund", (1, 2), (0.005, 0.015), 0.995),
        (n_insurance, "insurance", (3, 8), (0.008, 0.02), 0.995),
    ]
    total_nbfi_count = sum(s[0] for s in nbfi_specs)

    for count, sector, lev_range, vol_range, conf in nbfi_specs:
        for i in range(count):
            share = count / total_nbfi_count
            assets = (total_nbfi_assets * share / count
                      * rng.uniform(0.6, 1.4))
            leverage = rng.uniform(*lev_range)
            intermediaries.append(Intermediary(
                name=f"{sector}_{i}",
                sector=sector,
                assets=assets,
                equity=assets / leverage,
                var_confidence=conf,
                volatility=rng.uniform(*vol_range),
            ))

    return intermediaries


def run_counterfactual(
    initial_shock: float = -0.05,
    market_depth: float = 5e5,
    seed: int = 42,
) -> dict[str, pd.DataFrame]:
    """
    Run the core counterfactual experiment:
    Compare amplification in a bank-only system vs. bank+NBFI system.

    Returns dict with 'bank_only' and 'bank_nbfi' simulation histories.
    """
    # Bank-only system (same total assets as banks in mixed system)
    bank_only = build_bank_only_system(
        n_banks=10, total_assets=1e6, seed=seed,
    )
    sim_bank = FireSaleSimulation(
        intermediaries=bank_only,
        market_depth=market_depth,
    )
    hist_bank = sim_bank.run(initial_shock=initial_shock)

    # Bank + NBFI system
    bank_nbfi = build_bank_nbfi_system(seed=seed)
    sim_mixed = FireSaleSimulation(
        intermediaries=bank_nbfi,
        market_depth=market_depth,
    )
    hist_mixed = sim_mixed.run(initial_shock=initial_shock)

    return {
        "bank_only": hist_bank,
        "bank_nbfi": hist_mixed,
    }


def amplification_ratio(histories: dict[str, pd.DataFrame]) -> dict:
    """
    Compute amplification metrics comparing bank-only vs. bank+NBFI systems.

    Returns dict with:
      - price_drop_bank_only: total price decline in bank-only system
      - price_drop_bank_nbfi: total price decline in mixed system
      - amplification_ratio: ratio of mixed to bank-only price decline
      - rounds_bank_only: number of fire-sale rounds
      - rounds_bank_nbfi: number of fire-sale rounds
      - equity_loss_bank_only: fraction of equity destroyed
      - equity_loss_bank_nbfi: fraction of equity destroyed
    """
    h_b = histories["bank_only"]
    h_m = histories["bank_nbfi"]

    p0_b = h_b.iloc[0]["asset_price"]
    p_final_b = h_b.iloc[-1]["asset_price"]
    e0_b = h_b.iloc[0]["total_equity"]
    e_final_b = h_b.iloc[-1]["total_equity"]

    p0_m = h_m.iloc[0]["asset_price"]
    p_final_m = h_m.iloc[-1]["asset_price"]
    e0_m = h_m.iloc[0]["total_equity"]
    e_final_m = h_m.iloc[-1]["total_equity"]

    drop_b = (p_final_b - p0_b) / p0_b
    drop_m = (p_final_m - p0_m) / p0_m

    return {
        "price_drop_bank_only": drop_b,
        "price_drop_bank_nbfi": drop_m,
        "amplification_ratio": drop_m / drop_b if drop_b != 0 else np.inf,
        "rounds_bank_only": len(h_b),
        "rounds_bank_nbfi": len(h_m),
        "equity_loss_bank_only": (e_final_b - e0_b) / e0_b,
        "equity_loss_bank_nbfi": (e_final_m - e0_m) / e0_m,
    }
