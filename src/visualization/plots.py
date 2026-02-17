"""
Visualization module for bank–NBFI systemic risk analysis.

Generates publication-quality figures for:
  1. Network structure (bipartite bank-NBFI graphs)
  2. Systemic risk measures over time and across sectors
  3. VaR-amplification simulation results
  4. Global financial cycle factor and transmission
  5. Connectedness indices and heatmaps
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
import networkx as nx
from pathlib import Path
from typing import Optional

from src.utils.config import FIGURES_DIR, SECTOR_LABELS

# ── Style defaults ─────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.figsize": (10, 6),
    "figure.dpi": 150,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 12,
})

SECTOR_COLORS = {
    "bank": "#2c3e50",
    "investment_fund": "#2980b9",
    "hedge_fund": "#e74c3c",
    "pension_fund": "#27ae60",
    "insurance": "#8e44ad",
    "mmf": "#f39c12",
    "direct_credit": "#1abc9c",
    "broker_dealer": "#d35400",
}


def _save(fig, name: str, output_dir: Path = FIGURES_DIR):
    """Save figure to the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / f"{name}.png", bbox_inches="tight", dpi=150)
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Network Visualizations
# ═══════════════════════════════════════════════════════════════════════════

def plot_exposure_network(
    G: nx.DiGraph,
    institutions: pd.DataFrame,
    title: str = "Bank–NBFI Exposure Network",
    save_name: Optional[str] = "network_exposure",
) -> plt.Figure:
    """
    Visualize the bipartite bank-NBFI network.

    Nodes colored by sector, sized by total strength (exposure).
    Edge width proportional to exposure amount.
    """
    ticker_to_sector = dict(zip(institutions["ticker"], institutions["sector"]))

    fig, ax = plt.subplots(figsize=(14, 10))

    # Layout: banks on left, NBFIs on right
    pos = {}
    banks = [n for n in G.nodes() if ticker_to_sector.get(n) == "bank"]
    nbfis = [n for n in G.nodes() if ticker_to_sector.get(n) != "bank"]

    for i, node in enumerate(banks):
        pos[node] = (0, i / max(len(banks) - 1, 1))
    for i, node in enumerate(nbfis):
        pos[node] = (1, i / max(len(nbfis) - 1, 1))

    # Node colors and sizes
    colors = []
    sizes = []
    for node in G.nodes():
        sector = ticker_to_sector.get(node, "bank")
        colors.append(SECTOR_COLORS.get(sector, "#95a5a6"))
        strength = G.degree(node, weight="weight")
        sizes.append(50 + strength * 0.01)

    # Edge widths
    weights = [d.get("weight", 1) for _, _, d in G.edges(data=True)]
    max_w = max(weights) if weights else 1
    edge_widths = [0.5 + 3 * w / max_w for w in weights]

    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.2, width=edge_widths,
                           edge_color="#bdc3c7", arrows=True, arrowsize=8)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=colors,
                           node_size=sizes, alpha=0.8, edgecolors="white",
                           linewidths=0.5)

    ax.set_title(title, fontweight="bold")
    ax.set_xlim(-0.3, 1.3)
    ax.text(0, -0.08, "Banks", ha="center", fontsize=12, fontweight="bold",
            transform=ax.transAxes)
    ax.text(1, -0.08, "NBFIs", ha="center", fontsize=12, fontweight="bold",
            transform=ax.transAxes)
    ax.axis("off")

    # Legend
    for sector, color in SECTOR_COLORS.items():
        ax.scatter([], [], c=color, s=60,
                   label=SECTOR_LABELS.get(sector, sector))
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)

    if save_name:
        _save(fig, save_name)
    return fig


def plot_network_statistics_over_time(
    net_stats: pd.DataFrame,
    save_name: Optional[str] = "network_stats_time",
) -> plt.Figure:
    """Plot evolution of network density, total exposure, and HHI."""
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    axes[0].plot(net_stats.index, net_stats["density"], color="#2c3e50", lw=1.5)
    axes[0].set_ylabel("Network Density")
    axes[0].set_title("Evolution of Bank–NBFI Network Structure", fontweight="bold")

    axes[1].plot(net_stats.index, net_stats["total_exposure"] / 1e6,
                 color="#2980b9", lw=1.5)
    axes[1].set_ylabel("Total Exposure\n(USD trillions)")

    axes[2].plot(net_stats.index, net_stats["hhi_exposure"],
                 color="#e74c3c", lw=1.5)
    axes[2].set_ylabel("Exposure HHI\n(concentration)")
    axes[2].set_xlabel("Date")

    for ax in axes:
        ax.grid(alpha=0.3)

    fig.tight_layout()
    if save_name:
        _save(fig, save_name)
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# 2. Systemic Risk Visualizations
# ═══════════════════════════════════════════════════════════════════════════

def plot_covar_by_sector(
    covar_df: pd.DataFrame,
    save_name: Optional[str] = "covar_by_sector",
) -> plt.Figure:
    """Box plot of ΔCoVaR by institution sector."""
    fig, ax = plt.subplots(figsize=(10, 6))

    sector_order = sorted(covar_df["sector"].unique())
    palette = [SECTOR_COLORS.get(s, "#95a5a6") for s in sector_order]

    sns.boxplot(
        data=covar_df, x="sector", y="delta_covar",
        order=sector_order, palette=palette, ax=ax, width=0.6,
    )
    ax.set_xlabel("")
    ax.set_ylabel("ΔCoVaR (systemic risk contribution)")
    ax.set_title("Systemic Risk Contribution by Sector (ΔCoVaR)", fontweight="bold")
    ax.set_xticklabels([SECTOR_LABELS.get(s, s) for s in sector_order],
                       rotation=30, ha="right")
    ax.axhline(0, color="black", lw=0.5, ls="--")
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    if save_name:
        _save(fig, save_name)
    return fig


def plot_mes_srisk_scatter(
    risk_df: pd.DataFrame,
    save_name: Optional[str] = "mes_srisk_scatter",
) -> plt.Figure:
    """Scatter of MES vs. SRISK colored by sector."""
    fig, ax = plt.subplots(figsize=(10, 7))

    for sector in risk_df["sector"].unique():
        mask = risk_df["sector"] == sector
        ax.scatter(
            risk_df.loc[mask, "mes"],
            risk_df.loc[mask, "srisk"],
            c=SECTOR_COLORS.get(sector, "#95a5a6"),
            label=SECTOR_LABELS.get(sector, sector),
            s=60, alpha=0.7, edgecolors="white", linewidth=0.5,
        )

    ax.set_xlabel("MES (Marginal Expected Shortfall)")
    ax.set_ylabel("SRISK (Systemic Risk Index)")
    ax.set_title("MES vs. SRISK by Institution Type", fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    fig.tight_layout()
    if save_name:
        _save(fig, save_name)
    return fig


def plot_connectedness_heatmap(
    sector_theta: pd.DataFrame,
    save_name: Optional[str] = "connectedness_heatmap",
) -> plt.Figure:
    """Heatmap of sector-level connectedness (GFEVD matrix)."""
    labels = [SECTOR_LABELS.get(s, s) for s in sector_theta.index]

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        sector_theta.values * 100,
        xticklabels=labels,
        yticklabels=labels,
        cmap="YlOrRd",
        annot=True,
        fmt=".1f",
        linewidths=0.5,
        ax=ax,
    )
    ax.set_title("Sector-Level Connectedness (% of FEVD)", fontweight="bold")
    ax.set_xlabel("Shock from")
    ax.set_ylabel("Shock to")

    fig.tight_layout()
    if save_name:
        _save(fig, save_name)
    return fig


def plot_rolling_connectedness(
    rolling_conn: pd.DataFrame,
    save_name: Optional[str] = "rolling_connectedness",
) -> plt.Figure:
    """Plot total connectedness index over time."""
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(rolling_conn.index, rolling_conn["total_connectedness"],
            color="#2c3e50", lw=1.5)
    ax.fill_between(rolling_conn.index, rolling_conn["total_connectedness"],
                    alpha=0.1, color="#2c3e50")
    ax.set_ylabel("Total Connectedness Index (%)")
    ax.set_title("Diebold-Yilmaz Total Connectedness Over Time", fontweight="bold")
    ax.grid(alpha=0.3)

    fig.tight_layout()
    if save_name:
        _save(fig, save_name)
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# 3. VaR Amplification Visualizations
# ═══════════════════════════════════════════════════════════════════════════

def plot_fire_sale_comparison(
    histories: dict[str, pd.DataFrame],
    save_name: Optional[str] = "fire_sale_comparison",
) -> plt.Figure:
    """
    Compare fire-sale dynamics: bank-only vs. bank+NBFI system.
    Shows asset price, aggregate leverage, and equity over rounds.
    """
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    labels = {"bank_only": "Banks Only", "bank_nbfi": "Banks + NBFIs"}
    colors = {"bank_only": "#2c3e50", "bank_nbfi": "#e74c3c"}

    for key, hist in histories.items():
        axes[0].plot(hist["round"], hist["asset_price"],
                     label=labels[key], color=colors[key], lw=2)
        axes[1].plot(hist["round"], hist["aggregate_leverage"],
                     label=labels[key], color=colors[key], lw=2)
        axes[2].plot(hist["round"], hist["total_equity"],
                     label=labels[key], color=colors[key], lw=2)

    axes[0].set_ylabel("Asset Price")
    axes[0].set_title("Asset Price Dynamics")
    axes[1].set_ylabel("Aggregate Leverage")
    axes[1].set_title("Leverage Dynamics")
    axes[2].set_ylabel("Total Equity")
    axes[2].set_title("Equity Dynamics")

    for ax in axes:
        ax.set_xlabel("Fire-Sale Round")
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)

    fig.suptitle("Fire-Sale Amplification: Bank-Only vs. Bank + NBFI System",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    if save_name:
        _save(fig, save_name)
    return fig


def plot_procyclicality_by_sector(
    procyc_df: pd.DataFrame,
    save_name: Optional[str] = "procyclicality_sectors",
) -> plt.Figure:
    """Bar chart of procyclicality coefficient β by sector."""
    fig, ax = plt.subplots(figsize=(10, 6))

    sector_means = (
        procyc_df.groupby("sector")["beta_procyclicality"]
        .agg(["mean", "std"])
        .sort_values("mean", ascending=False)
    )

    colors = [SECTOR_COLORS.get(s, "#95a5a6") for s in sector_means.index]
    bars = ax.bar(
        range(len(sector_means)),
        sector_means["mean"],
        yerr=sector_means["std"],
        color=colors,
        capsize=4,
        alpha=0.85,
        edgecolor="white",
        linewidth=0.5,
    )
    ax.set_xticks(range(len(sector_means)))
    ax.set_xticklabels(
        [SECTOR_LABELS.get(s, s) for s in sector_means.index],
        rotation=30, ha="right",
    )
    ax.set_ylabel("Procyclicality Coefficient (β)")
    ax.set_title("Leverage Procyclicality by Sector (Adrian & Shin 2010)",
                 fontweight="bold")
    ax.axhline(0, color="black", lw=0.5, ls="--")
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    if save_name:
        _save(fig, save_name)
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# 4. Global Financial Cycle Visualizations
# ═══════════════════════════════════════════════════════════════════════════

def plot_global_factor(
    gfc: pd.DataFrame,
    vix: Optional[pd.Series] = None,
    save_name: Optional[str] = "global_factor",
) -> plt.Figure:
    """Plot the extracted global financial cycle factor, optionally with VIX."""
    fig, ax1 = plt.subplots(figsize=(12, 5))

    col = gfc.columns[0] if isinstance(gfc, pd.DataFrame) else gfc.name
    series = gfc[col] if isinstance(gfc, pd.DataFrame) else gfc

    ax1.plot(series.index, series, color="#2c3e50", lw=1.5, label="Global Factor")
    ax1.fill_between(series.index, series, alpha=0.1, color="#2c3e50")
    ax1.set_ylabel("Global Financial Cycle Factor", color="#2c3e50")
    ax1.set_title("Global Financial Cycle (Miranda-Agrippino & Rey 2020)",
                  fontweight="bold")

    if vix is not None:
        ax2 = ax1.twinx()
        ax2.plot(vix.index, vix, color="#e74c3c", lw=1, alpha=0.6, label="VIX")
        ax2.set_ylabel("VIX", color="#e74c3c")
        ax2.invert_yaxis()  # VIX inverted to show co-movement
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="lower left")
    else:
        ax1.legend()

    ax1.grid(alpha=0.3)
    fig.tight_layout()
    if save_name:
        _save(fig, save_name)
    return fig


def plot_gfc_amplification(
    panel: pd.DataFrame,
    y_col: str = "credit_growth",
    gfc_col: str = "gfc_factor",
    nbfi_col: str = "nbfi_assets_pct_gdp",
    save_name: Optional[str] = "gfc_amplification",
) -> plt.Figure:
    """
    Scatter plot showing how the GFC-credit relationship steepens
    with NBFI penetration (high vs. low NBFI countries).
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    median_nbfi = panel[nbfi_col].median()
    low = panel[panel[nbfi_col] <= median_nbfi]
    high = panel[panel[nbfi_col] > median_nbfi]

    for ax, data, label, color in [
        (axes[0], low, "Low NBFI Penetration", "#2980b9"),
        (axes[1], high, "High NBFI Penetration", "#e74c3c"),
    ]:
        ax.scatter(data[gfc_col], data[y_col], alpha=0.3, s=15, color=color)
        # Fit line
        mask = data[[gfc_col, y_col]].dropna().index
        if len(mask) > 10:
            z = np.polyfit(data.loc[mask, gfc_col], data.loc[mask, y_col], 1)
            p = np.poly1d(z)
            x_range = np.linspace(data[gfc_col].min(), data[gfc_col].max(), 100)
            ax.plot(x_range, p(x_range), color="black", lw=2,
                    label=f"slope = {z[0]:.2f}")
        ax.set_xlabel("Global Financial Cycle Factor")
        ax.set_ylabel("Local Credit Growth")
        ax.set_title(label, fontweight="bold")
        ax.legend()
        ax.grid(alpha=0.3)

    fig.suptitle("GFC Transmission: Low vs. High NBFI Countries",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    if save_name:
        _save(fig, save_name)
    return fig
