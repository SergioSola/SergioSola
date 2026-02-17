"""
Master script: run the full bank–NBFI systemic risk analysis pipeline.

Steps:
  1. Build / load dataset
  2. Compute network statistics
  3. Compute systemic risk measures (CoVaR, MES, SRISK)
  4. Estimate Diebold-Yilmaz connectedness
  5. Run VaR-amplification procyclicality tests
  6. Run fire-sale counterfactual simulation
  7. Extract global financial cycle factor
  8. Run GFC amplification regressions
  9. Generate all figures and tables
"""

from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from src.data.build_dataset import generate_synthetic_data, load_processed_data
from src.analysis.network import (
    build_exposure_network,
    compute_centrality_measures,
    rolling_network_statistics,
    bipartite_projection,
)
from src.analysis.systemic_risk import (
    compute_covar_panel,
    compute_mes,
    compute_srisk,
    compute_connectedness,
    rolling_connectedness,
    granger_causality_network,
    aggregate_connectedness_by_sector,
)
from src.models.var_amplification import (
    sector_procyclicality,
    run_counterfactual,
    amplification_ratio,
)
from src.analysis.global_financial_cycle import (
    extract_global_factor,
    build_synthetic_gfc_panel,
    panel_gfc_regression,
    connectedness_amplification_test,
)
from src.visualization.plots import (
    plot_exposure_network,
    plot_network_statistics_over_time,
    plot_covar_by_sector,
    plot_mes_srisk_scatter,
    plot_connectedness_heatmap,
    plot_rolling_connectedness,
    plot_fire_sale_comparison,
    plot_procyclicality_by_sector,
    plot_global_factor,
    plot_gfc_amplification,
)
from src.utils.config import PROCESSED_DIR, RESULTS_DIR, TABLES_DIR


def main():
    print("=" * 70)
    print("  Bank–NBFI Systemic Risk Analysis Pipeline")
    print("=" * 70)

    # ── 1. Data ────────────────────────────────────────────────────────
    print("\n[1/9] Building dataset...")
    try:
        data = load_processed_data()
        if not data:
            raise FileNotFoundError
        print("  Loaded processed data from disk.")
    except Exception:
        print("  Generating synthetic data...")
        data = generate_synthetic_data()

    institutions = data["institutions"]
    returns = data["returns"]
    exposures = data["exposures"]

    print(f"  Institutions: {len(institutions)} "
          f"({(institutions['sector'] == 'bank').sum()} banks, "
          f"{(institutions['sector'] != 'bank').sum()} NBFIs)")
    print(f"  Returns: {returns.shape[0]} days × {returns.shape[1]} entities")
    print(f"  Exposures: {len(exposures)} bilateral observations")

    # ── 2. Network analysis ────────────────────────────────────────────
    print("\n[2/9] Computing network statistics...")
    net_stats = rolling_network_statistics(exposures)
    print(f"  {len(net_stats)} quarters of network data")

    latest_date = exposures["date"].max()
    G = build_exposure_network(exposures, date=latest_date)
    centrality = compute_centrality_measures(G)
    print(f"  Latest network: {G.number_of_nodes()} nodes, "
          f"{G.number_of_edges()} edges")

    # ── 3. Systemic risk measures ──────────────────────────────────────
    print("\n[3/9] Computing systemic risk measures...")

    # Use weekly returns for tractability
    weekly_returns = returns.resample("W").apply(
        lambda x: (1 + x).prod() - 1
    )

    # CoVaR
    covar_df = compute_covar_panel(weekly_returns, institutions)
    print(f"  CoVaR computed for {len(covar_df)} institutions")

    # MES
    mes_df = compute_mes(weekly_returns, institutions)
    print(f"  MES computed for {len(mes_df)} institutions")

    # SRISK
    srisk_df = compute_srisk(weekly_returns, institutions)
    print(f"  SRISK computed for {len(srisk_df)} institutions")

    # ── 4. Connectedness ───────────────────────────────────────────────
    print("\n[4/9] Estimating Diebold-Yilmaz connectedness...")

    # Use a subset for tractability (top 15 by market activity)
    top_n = 15
    vol_rank = weekly_returns.std().nlargest(top_n).index.tolist()
    sub_returns = weekly_returns[vol_rank].dropna()

    conn = compute_connectedness(sub_returns)
    print(f"  Total connectedness: {conn['total_connectedness']:.1f}%")

    # Sector-level aggregation
    sector_theta = aggregate_connectedness_by_sector(conn["theta"], institutions)

    # Rolling connectedness (monthly step for speed)
    monthly_returns = returns[vol_rank].resample("ME").apply(
        lambda x: (1 + x).prod() - 1
    ).dropna()
    roll_conn = rolling_connectedness(monthly_returns, window=36, step=1)
    print(f"  Rolling connectedness: {len(roll_conn)} observations")

    # ── 5. Procyclicality ──────────────────────────────────────────────
    print("\n[5/9] Testing leverage procyclicality by sector...")
    procyc = sector_procyclicality(returns, institutions, window=60)
    sector_summary = (
        procyc.groupby("sector")["beta_procyclicality"]
        .agg(["mean", "count"])
    )
    print(sector_summary.to_string())

    # ── 6. Fire-sale simulation ────────────────────────────────────────
    print("\n[6/9] Running fire-sale counterfactual simulation...")
    histories = run_counterfactual(initial_shock=-0.05, market_depth=5e5)
    amp = amplification_ratio(histories)
    print(f"  Bank-only price drop:  {amp['price_drop_bank_only']:.4f}")
    print(f"  Bank+NBFI price drop:  {amp['price_drop_bank_nbfi']:.4f}")
    print(f"  Amplification ratio:   {amp['amplification_ratio']:.2f}x")

    # ── 7. Global financial cycle ──────────────────────────────────────
    print("\n[7/9] Extracting global financial cycle factor...")
    gfc_result = extract_global_factor(weekly_returns, n_components=3)
    print(f"  Variance explained by PC1: "
          f"{gfc_result['explained_variance_ratio'][0]:.1%}")
    print(f"  Top 3 PCs explain: "
          f"{gfc_result['explained_variance_ratio'].sum():.1%}")

    # ── 8. GFC amplification regressions ───────────────────────────────
    print("\n[8/9] Running GFC amplification regressions...")
    gfc_panel = build_synthetic_gfc_panel(
        true_amplification=0.5, seed=42,
    )

    reg = panel_gfc_regression(gfc_panel)
    print("  Panel regression results:")
    print(f"    GFC coefficient:     {reg.params.get('gfc_factor', np.nan):.3f} "
          f"(p={reg.pvalues.get('gfc_factor', np.nan):.3f})")
    print(f"    NBFI coefficient:    {reg.params.get('nbfi_assets_pct_gdp', np.nan):.3f} "
          f"(p={reg.pvalues.get('nbfi_assets_pct_gdp', np.nan):.3f})")
    print(f"    GFC × NBFI:          {reg.params.get('gfc_x_nbfi', np.nan):.3f} "
          f"(p={reg.pvalues.get('gfc_x_nbfi', np.nan):.3f})")
    print(f"    R²:                  {reg.rsquared:.3f}")

    # ── 9. Generate outputs ────────────────────────────────────────────
    print("\n[9/9] Generating figures and tables...")

    # Figures
    plot_exposure_network(G, institutions)
    plot_network_statistics_over_time(net_stats)
    plot_covar_by_sector(covar_df)
    if "srisk" in srisk_df.columns and "mes" in srisk_df.columns:
        plot_mes_srisk_scatter(srisk_df)
    plot_connectedness_heatmap(sector_theta)
    if len(roll_conn) > 0:
        plot_rolling_connectedness(roll_conn)
    plot_fire_sale_comparison(histories)
    plot_procyclicality_by_sector(procyc)
    plot_global_factor(gfc_result["global_factor"])
    plot_gfc_amplification(gfc_panel)

    # Save tables
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    covar_df.to_csv(TABLES_DIR / "covar_results.csv", index=False)
    srisk_df.to_csv(TABLES_DIR / "srisk_results.csv", index=False)
    centrality.to_csv(TABLES_DIR / "network_centrality.csv")
    procyc.to_csv(TABLES_DIR / "procyclicality.csv", index=False)

    # Save amplification results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    pd.Series(amp).to_csv(RESULTS_DIR / "amplification_ratio.csv")

    print("\n" + "=" * 70)
    print("  Analysis complete. Outputs saved to output/")
    print("=" * 70)


if __name__ == "__main__":
    main()
