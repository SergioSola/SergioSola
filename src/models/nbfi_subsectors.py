"""
NBFI subsector-specific models:

1. LDI / Pension fund margin spiral model
   (inspired by the 2022 UK gilt crisis)
2. Money market fund run dynamics
   (inspired by Reserve Primary Fund 2008, March 2020 dash-for-cash)
3. Hedge fund deleveraging and prime brokerage contagion
   (inspired by Archegos 2021, LTCM 1998)

These models capture the distinct amplification mechanisms in each NBFI
subsector and their feedback to the banking system.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from scipy import stats as sp_stats
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════
# 1. LDI / Pension Fund Margin Spiral
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PensionFund:
    """A pension fund using a Liability-Driven Investment (LDI) strategy."""
    name: str
    assets: float              # total assets (bond portfolio + collateral)
    liabilities: float         # present value of pension obligations
    bond_holdings: float       # long-duration gilt/bond holdings
    derivative_notional: float # interest-rate swap notional
    collateral_posted: float   # cash/gilts posted as margin
    collateral_buffer: float   # additional liquid assets for margin calls
    leverage_ratio: float = 3.0  # effective leverage through derivatives

    @property
    def funding_ratio(self) -> float:
        return self.assets / self.liabilities if self.liabilities > 0 else 0

    @property
    def available_collateral(self) -> float:
        return self.collateral_buffer

    def margin_call(self, yield_change_bps: float) -> float:
        """
        Compute margin call from an interest rate shock.

        When yields rise, the pension fund's swap positions lose value
        (they are receiving fixed, paying floating). The margin call is
        approximately: notional * duration * yield_change.
        """
        duration = 15.0  # typical LDI duration ~15 years
        loss = self.derivative_notional * duration * (yield_change_bps / 10000)
        return max(0, loss)

    def can_meet_margin(self, margin_amount: float) -> bool:
        return self.available_collateral >= margin_amount

    def sell_bonds_for_margin(self, amount: float, bond_price: float) -> float:
        """
        Sell bonds to raise collateral for margin call.
        Returns the quantity of bonds sold.
        """
        bonds_to_sell = amount / bond_price if bond_price > 0 else 0
        actual_sale = min(bonds_to_sell, self.bond_holdings)
        self.bond_holdings -= actual_sale
        self.collateral_buffer += actual_sale * bond_price
        return actual_sale


@dataclass
class LDIMarginSpiral:
    """
    Simulates the LDI margin spiral (2022 UK gilt crisis).

    Mechanism:
    1. Yields rise unexpectedly
    2. Pension funds face margin calls on interest-rate swaps
    3. Funds sell gilts to raise cash for margin
    4. Gilt sales push yields higher (price impact)
    5. Higher yields trigger more margin calls → spiral
    """
    pension_funds: list[PensionFund]
    initial_bond_price: float = 100.0
    bond_duration: float = 15.0
    market_depth: float = 1e7    # bond market depth
    max_rounds: int = 30
    convergence_tol: float = 1e-4
    history: list[dict] = field(default_factory=list)

    def _bond_price(self, yield_level_bps: float) -> float:
        """Approximate bond price from yield level using duration."""
        base_yield = 200  # 2% base yield in bps
        price_change = -self.bond_duration * (yield_level_bps - base_yield) / 10000
        return self.initial_bond_price * (1 + price_change)

    def run(self, yield_shock_bps: float = 50) -> pd.DataFrame:
        """
        Run the LDI margin spiral simulation.

        Parameters
        ----------
        yield_shock_bps : Initial yield increase in basis points.

        Returns
        -------
        DataFrame tracking the spiral dynamics per round.
        """
        self.history = []
        current_yield = 200  # starting at 2%

        # Record initial state
        self.history.append({
            "round": 0,
            "yield_bps": current_yield,
            "bond_price": self._bond_price(current_yield),
            "total_bonds_sold": 0,
            "total_margin_calls": 0,
            "funds_in_distress": 0,
            "funds_solvent": len(self.pension_funds),
        })

        # Apply initial shock
        current_yield += yield_shock_bps

        for round_num in range(1, self.max_rounds + 1):
            bond_price = self._bond_price(current_yield)
            total_sold = 0
            total_margin = 0
            distressed = 0

            for fund in self.pension_funds:
                margin = fund.margin_call(yield_shock_bps if round_num == 1
                                          else current_yield - self.history[-1]["yield_bps"])

                if margin <= 0:
                    continue

                total_margin += margin

                if fund.can_meet_margin(margin):
                    fund.collateral_buffer -= margin
                    fund.collateral_posted += margin
                else:
                    # Must sell bonds
                    shortfall = margin - fund.available_collateral
                    bonds_sold = fund.sell_bonds_for_margin(shortfall, bond_price)
                    total_sold += bonds_sold * bond_price
                    fund.collateral_buffer -= min(margin, fund.collateral_buffer)
                    fund.collateral_posted += margin

                    if fund.bond_holdings <= 0:
                        distressed += 1

            # Price impact of bond sales → yield increase
            if total_sold > 0:
                yield_impact = (total_sold / self.market_depth) * 100  # in bps
                current_yield += yield_impact

            self.history.append({
                "round": round_num,
                "yield_bps": current_yield,
                "bond_price": self._bond_price(current_yield),
                "total_bonds_sold": total_sold,
                "total_margin_calls": total_margin,
                "funds_in_distress": distressed,
                "funds_solvent": len(self.pension_funds) - distressed,
            })

            if total_sold < self.convergence_tol:
                break

        return pd.DataFrame(self.history)


def build_pension_sector(
    n_funds: int = 20,
    total_assets: float = 5e6,
    avg_leverage: float = 3.0,
    seed: int = 42,
) -> list[PensionFund]:
    """Create a synthetic pension fund sector for simulation."""
    rng = np.random.default_rng(seed)
    funds = []
    for i in range(n_funds):
        assets = total_assets / n_funds * rng.uniform(0.5, 1.5)
        leverage = rng.uniform(2, avg_leverage + 2)
        funds.append(PensionFund(
            name=f"Pension_{i}",
            assets=assets,
            liabilities=assets * rng.uniform(0.9, 1.1),
            bond_holdings=assets * 0.6,
            derivative_notional=assets * leverage,
            collateral_posted=assets * 0.1,
            collateral_buffer=assets * rng.uniform(0.05, 0.15),
        ))
    return funds


# ═══════════════════════════════════════════════════════════════════════════
# 2. Money Market Fund Run Model
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MoneyMarketFund:
    """A prime money market fund with liquidity transformation."""
    name: str
    nav: float                  # net asset value
    aum: float                  # assets under management
    liquid_assets_pct: float    # fraction in overnight/weekly liquid assets
    cp_holdings: float          # commercial paper holdings
    repo_holdings: float        # repo and short-term bank paper
    gate_threshold: float = 0.30  # minimum weekly liquid assets before gate
    fee_threshold: float = 0.10   # min weekly liquid assets before redemption fee

    @property
    def liquid_assets(self) -> float:
        return self.aum * self.liquid_assets_pct

    @property
    def illiquid_assets(self) -> float:
        return self.aum * (1 - self.liquid_assets_pct)

    def process_redemption(self, amount: float) -> dict:
        """
        Process a redemption request.

        Returns dict with: amount_paid, used_liquid, fire_sale_amount,
                          gate_imposed, fee_imposed, remaining_aum.
        """
        gate = self.liquid_assets_pct < self.gate_threshold
        fee = self.liquid_assets_pct < self.fee_threshold

        if gate:
            # Gate limits redemptions to 10% of AUM
            amount = min(amount, self.aum * 0.10)

        # First use liquid assets
        from_liquid = min(amount, self.liquid_assets)
        remaining = amount - from_liquid

        # Then fire-sell illiquid assets (with haircut)
        fire_sale_haircut = 0.03  # 3% fire-sale discount on CP
        fire_sale_amount = 0
        if remaining > 0:
            fire_sale_amount = remaining * (1 + fire_sale_haircut)
            fire_sale_amount = min(fire_sale_amount, self.illiquid_assets)

        # Update fund state
        total_paid = from_liquid + max(0, fire_sale_amount - remaining * fire_sale_haircut)
        self.aum -= total_paid
        if self.aum > 0:
            self.liquid_assets_pct = max(0,
                (self.liquid_assets - from_liquid) / self.aum)

        return {
            "amount_requested": amount,
            "amount_paid": total_paid,
            "used_liquid": from_liquid,
            "fire_sale_amount": fire_sale_amount,
            "gate_imposed": gate,
            "fee_imposed": fee,
            "remaining_aum": self.aum,
            "remaining_liquid_pct": self.liquid_assets_pct,
        }


@dataclass
class MMFRunSimulation:
    """
    Simulate a run on money market funds.

    Mechanism (Diamond-Dybvig applied to MMFs):
    1. Credit event triggers losses in CP/bank paper holdings
    2. Investors observe NAV decline and start redeeming
    3. Redemptions force fire sales of illiquid assets
    4. Fire sales → CP spread widening → bank funding cost increase
    5. More investors redeem → strategic complementarity → run
    """
    funds: list[MoneyMarketFund]
    cp_spread_bps: float = 20.0        # initial CP-OIS spread
    spread_sensitivity: float = 0.5     # spread response to fire sales
    redemption_rate_calm: float = 0.01  # baseline daily redemption rate
    redemption_rate_panic: float = 0.10 # panic daily redemption rate
    panic_threshold_nav: float = 0.997  # NAV below which panic starts
    max_days: int = 20
    history: list[dict] = field(default_factory=list)

    def run(self, initial_credit_loss_pct: float = 0.005) -> pd.DataFrame:
        """
        Simulate the MMF run.

        Parameters
        ----------
        initial_credit_loss_pct : Initial mark-to-market loss (e.g., 0.5%).
        """
        self.history = []

        # Apply initial credit loss to all funds
        for fund in self.funds:
            fund.aum *= (1 - initial_credit_loss_pct)
            fund.nav = fund.aum  # simplified: NAV tracks AUM

        total_aum_0 = sum(f.aum for f in self.funds)

        for day in range(self.max_days):
            total_aum = sum(f.aum for f in self.funds)
            avg_nav = total_aum / total_aum_0 if total_aum_0 > 0 else 0
            is_panic = avg_nav < self.panic_threshold_nav

            redemption_rate = (self.redemption_rate_panic if is_panic
                               else self.redemption_rate_calm)

            total_fire_sales = 0
            total_redemptions = 0
            gates = 0

            for fund in self.funds:
                if fund.aum <= 0:
                    continue
                redemption = fund.aum * redemption_rate
                result = fund.process_redemption(redemption)
                total_fire_sales += result["fire_sale_amount"]
                total_redemptions += result["amount_paid"]
                if result["gate_imposed"]:
                    gates += 1

            # Fire sales widen CP spreads
            spread_impact = total_fire_sales * self.spread_sensitivity / 1e6
            self.cp_spread_bps += spread_impact

            self.history.append({
                "day": day,
                "total_aum": sum(f.aum for f in self.funds),
                "avg_nav_ratio": sum(f.aum for f in self.funds) / total_aum_0,
                "total_redemptions": total_redemptions,
                "total_fire_sales": total_fire_sales,
                "cp_spread_bps": self.cp_spread_bps,
                "funds_with_gates": gates,
                "is_panic": is_panic,
            })

            if total_redemptions < 1:
                break

        return pd.DataFrame(self.history)


def build_mmf_sector(
    n_funds: int = 15,
    total_aum: float = 1e7,
    seed: int = 42,
) -> list[MoneyMarketFund]:
    """Create a synthetic MMF sector."""
    rng = np.random.default_rng(seed)
    funds = []
    for i in range(n_funds):
        aum = total_aum / n_funds * rng.uniform(0.5, 1.5)
        liquid_pct = rng.uniform(0.30, 0.50)
        funds.append(MoneyMarketFund(
            name=f"MMF_{i}",
            nav=aum,
            aum=aum,
            liquid_assets_pct=liquid_pct,
            cp_holdings=aum * (1 - liquid_pct) * 0.6,
            repo_holdings=aum * (1 - liquid_pct) * 0.4,
        ))
    return funds


# ═══════════════════════════════════════════════════════════════════════════
# 3. Hedge Fund Deleveraging / Prime Brokerage Contagion
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class HedgeFund:
    """A leveraged hedge fund with prime brokerage relationships."""
    name: str
    nav: float                    # net asset value (equity)
    gross_exposure: float         # total long + short positions
    margin_posted: float          # initial margin at prime broker
    prime_broker: str             # name of the prime broker bank
    strategy: str = "relative_value"  # strategy type
    max_leverage: float = 15.0
    margin_requirement: float = 0.10  # 10% initial margin

    @property
    def leverage(self) -> float:
        return self.gross_exposure / self.nav if self.nav > 0 else np.inf

    @property
    def margin_excess(self) -> float:
        """Excess margin above requirement."""
        required = self.gross_exposure * self.margin_requirement
        return self.margin_posted - required

    def apply_pnl(self, pnl_pct: float):
        """Apply P&L to NAV."""
        pnl = self.gross_exposure * pnl_pct
        self.nav += pnl
        self.margin_posted += pnl

    def margin_call_amount(self) -> float:
        """Amount of additional margin needed."""
        required = self.gross_exposure * self.margin_requirement
        return max(0, required - self.margin_posted)

    def forced_deleveraging(self, amount: float) -> float:
        """
        Reduce gross exposure to meet margin requirements.
        Returns amount of positions closed.
        """
        reduction = min(amount / self.margin_requirement, self.gross_exposure)
        self.gross_exposure -= reduction
        return reduction


@dataclass
class PrimeBrokerageContagion:
    """
    Simulate hedge fund deleveraging and contagion to prime brokers.

    Mechanism:
    1. Market shock → hedge fund losses
    2. Prime broker raises margin requirements (procyclical)
    3. Hedge funds deleverage → fire sales
    4. Fire sales → more losses → more margin calls
    5. Prime broker faces credit losses on defaulting funds
    6. Prime broker pulls credit from other funds → contagion
    """
    hedge_funds: list[HedgeFund]
    market_price: float = 100.0
    market_depth: float = 5e5
    margin_procyclicality: float = 0.5  # margin rises with volatility
    max_rounds: int = 30
    history: list[dict] = field(default_factory=list)

    def run(self, initial_shock: float = -0.03) -> pd.DataFrame:
        """Run the prime brokerage contagion simulation."""
        self.history = []

        # Record initial state
        self.history.append({
            "round": 0,
            "market_price": self.market_price,
            "total_nav": sum(f.nav for f in self.hedge_funds),
            "total_gross_exposure": sum(f.gross_exposure for f in self.hedge_funds),
            "avg_leverage": np.mean([f.leverage for f in self.hedge_funds
                                     if f.nav > 0]),
            "funds_defaulted": 0,
            "total_deleveraging": 0,
            "pb_credit_losses": 0,
        })

        # Apply initial shock
        for fund in self.hedge_funds:
            fund.apply_pnl(initial_shock)

        # Increase margin requirements (procyclical)
        base_margin = self.hedge_funds[0].margin_requirement
        vol_increase = abs(initial_shock) * self.margin_procyclicality

        for round_num in range(1, self.max_rounds + 1):
            # Increase margin requirements
            new_margin = base_margin + vol_increase * (round_num / self.max_rounds)
            for fund in self.hedge_funds:
                fund.margin_requirement = new_margin

            total_delev = 0
            defaults = 0
            pb_losses = 0

            for fund in self.hedge_funds:
                if fund.nav <= 0:
                    defaults += 1
                    continue

                margin_needed = fund.margin_call_amount()
                if margin_needed > 0:
                    if margin_needed > fund.nav * 0.5:
                        # Fund defaults — PB absorbs loss
                        pb_losses += max(0, -fund.nav)
                        fund.nav = 0
                        total_delev += fund.gross_exposure
                        fund.gross_exposure = 0
                        defaults += 1
                    else:
                        # Forced deleveraging
                        closed = fund.forced_deleveraging(margin_needed)
                        total_delev += closed

            # Price impact
            if total_delev > 0:
                impact = -total_delev / self.market_depth
                self.market_price *= (1 + impact)

                # Apply losses to remaining funds
                for fund in self.hedge_funds:
                    if fund.nav > 0:
                        fund.apply_pnl(impact)

            active_funds = [f for f in self.hedge_funds if f.nav > 0]
            self.history.append({
                "round": round_num,
                "market_price": self.market_price,
                "total_nav": sum(f.nav for f in self.hedge_funds),
                "total_gross_exposure": sum(f.gross_exposure for f in self.hedge_funds),
                "avg_leverage": (np.mean([f.leverage for f in active_funds])
                                 if active_funds else 0),
                "funds_defaulted": defaults,
                "total_deleveraging": total_delev,
                "pb_credit_losses": pb_losses,
            })

            if total_delev < 1:
                break

        return pd.DataFrame(self.history)


def build_hedge_fund_sector(
    n_funds: int = 20,
    total_nav: float = 2e6,
    banks: Optional[list[str]] = None,
    seed: int = 42,
) -> list[HedgeFund]:
    """Create a synthetic hedge fund sector with prime brokerage links."""
    rng = np.random.default_rng(seed)
    if banks is None:
        banks = ["GS", "JPM", "MS", "CS", "DB"]

    strategies = ["relative_value", "macro", "equity_long_short",
                  "credit", "quant"]
    funds = []
    for i in range(n_funds):
        nav = total_nav / n_funds * rng.uniform(0.3, 2.0)
        leverage = rng.uniform(3, 15)
        funds.append(HedgeFund(
            name=f"HF_{i}",
            nav=nav,
            gross_exposure=nav * leverage,
            margin_posted=nav * leverage * 0.12,
            prime_broker=rng.choice(banks),
            strategy=rng.choice(strategies),
        ))
    return funds
