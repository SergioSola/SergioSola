"""
Plotting module for the Bayesian QVAR.

Generates publication-quality figures for:
  1. Raw data / endogenous variables
  2. Posterior coefficient trace plots and densities
  3. Structural shocks
  4. Quantile Impulse Response Functions (QIRFs) with credible bands
  5. QIRF comparison across quantiles (Q10, Q50, Q90)
  6. Forecast Error Variance Decomposition
"""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from typing import Optional
from pathlib import Path


# Default style
COLORS = {
    "median": "#1f77b4",
    "q10": "#d62728",
    "q90": "#2ca02c",
    "band": "#a0c4e8",
    "band_dark": "#5a9fd4",
    "data": "#333333",
    "shock": "#7f7f7f",
    "grid": "#e0e0e0",
}


def _setup_style():
    """Apply consistent matplotlib style."""
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.color": COLORS["grid"],
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "figure.titlesize": 14,
        "legend.fontsize": 9,
        "lines.linewidth": 1.5,
    })


# ═══════════════════════════════════════════════════════════════════════════
# 1. Plot raw data / endogenous variables
# ═══════════════════════════════════════════════════════════════════════════

def plot_variables(
    data: np.ndarray,
    var_names: list[str],
    dates: Optional[np.ndarray] = None,
    title: str = "Endogenous Variables",
    save_path: Optional[str] = None,
    figsize: Optional[tuple] = None,
) -> plt.Figure:
    """
    Plot each endogenous variable in a separate panel.

    Parameters
    ----------
    data : (T, k) array of observations.
    var_names : Variable names.
    dates : Optional date array for x-axis.
    title : Figure title.
    save_path : If provided, save figure to this path.
    figsize : Figure size.
    """
    _setup_style()
    T, k = data.shape
    if figsize is None:
        figsize = (12, 3 * k)

    fig, axes = plt.subplots(k, 1, figsize=figsize, sharex=True)
    if k == 1:
        axes = [axes]

    x = dates if dates is not None else np.arange(T)

    for i, ax in enumerate(axes):
        ax.plot(x, data[:, i], color=COLORS["data"], linewidth=1.2)
        ax.set_ylabel(var_names[i])
        ax.axhline(0, color="black", linewidth=0.5, alpha=0.5)

    axes[0].set_title(title)
    axes[-1].set_xlabel("Time")
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# 2. Trace plots and posterior densities
# ═══════════════════════════════════════════════════════════════════════════

def plot_trace_diagnostics(
    beta_draws: np.ndarray,
    var_names: list[str],
    k: int,
    lags: int,
    n_params_to_show: int = 12,
    save_path: Optional[str] = None,
    figsize: Optional[tuple] = None,
) -> plt.Figure:
    """
    Plot trace plots and posterior densities for key parameters.

    Shows a subset of the most important coefficients (intercepts
    and first-lag own-effects).
    """
    _setup_style()
    n_reg = beta_draws.shape[1] // k
    n_show = min(n_params_to_show, beta_draws.shape[1])

    # Select intercepts and first-lag diagonal coefficients
    indices = []
    labels = []
    for i in range(k):
        # Intercept for equation i
        idx = i * n_reg
        indices.append(idx)
        labels.append(f"{var_names[i]}: intercept")
        # First lag own-effect
        idx_own = i * n_reg + 1 + i
        if idx_own < beta_draws.shape[1]:
            indices.append(idx_own)
            labels.append(f"{var_names[i]}: own lag-1")

    indices = indices[:n_show]
    labels = labels[:n_show]

    if figsize is None:
        figsize = (14, 3 * len(indices))

    fig, axes = plt.subplots(len(indices), 2, figsize=figsize)
    if len(indices) == 1:
        axes = axes[np.newaxis, :]

    for row, (idx, label) in enumerate(zip(indices, labels)):
        chain = beta_draws[:, idx]

        # Trace plot
        axes[row, 0].plot(chain, color=COLORS["median"], linewidth=0.3, alpha=0.7)
        axes[row, 0].set_ylabel(label)
        if row == 0:
            axes[row, 0].set_title("Trace Plot")

        # Posterior density
        axes[row, 1].hist(chain, bins=50, density=True,
                          color=COLORS["band"], edgecolor=COLORS["band_dark"],
                          alpha=0.7)
        axes[row, 1].axvline(np.median(chain), color=COLORS["median"],
                             linestyle="--", linewidth=1.5, label="Median")
        axes[row, 1].axvline(np.percentile(chain, 16), color=COLORS["q10"],
                             linestyle=":", linewidth=1, label="68% CI")
        axes[row, 1].axvline(np.percentile(chain, 84), color=COLORS["q10"],
                             linestyle=":", linewidth=1)
        if row == 0:
            axes[row, 1].set_title("Posterior Density")
            axes[row, 1].legend()

    fig.suptitle("MCMC Diagnostics", fontsize=14, y=1.01)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# 3. Structural shocks
# ═══════════════════════════════════════════════════════════════════════════

def plot_structural_shocks(
    structural_shocks: np.ndarray,
    var_names: list[str],
    dates: Optional[np.ndarray] = None,
    title: str = "Identified Structural Shocks",
    save_path: Optional[str] = None,
    figsize: Optional[tuple] = None,
) -> plt.Figure:
    """
    Plot identified structural shocks from Cholesky identification.
    """
    _setup_style()
    T, k = structural_shocks.shape
    if figsize is None:
        figsize = (12, 2.5 * k)

    fig, axes = plt.subplots(k, 1, figsize=figsize, sharex=True)
    if k == 1:
        axes = [axes]

    x = dates if dates is not None else np.arange(T)

    for i, ax in enumerate(axes):
        ax.bar(x, structural_shocks[:, i], color=COLORS["shock"],
               alpha=0.7, width=0.8)
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_ylabel(f"Shock to\n{var_names[i]}")

    axes[0].set_title(title)
    axes[-1].set_xlabel("Time")
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# 4. QIRFs with credible bands (single quantile)
# ═══════════════════════════════════════════════════════════════════════════

def plot_qirfs(
    irf_result: dict,
    shock_name: Optional[str] = None,
    title: Optional[str] = None,
    save_path: Optional[str] = None,
    figsize: Optional[tuple] = None,
) -> plt.Figure:
    """
    Plot QIRFs for a single quantile with Bayesian credible bands.

    Parameters
    ----------
    irf_result : Output from compute_bayesian_qirfs_cholesky.
    shock_name : Name of the shock for the title.
    title : Custom figure title.
    save_path : Save path.
    figsize : Figure size.
    """
    _setup_style()
    median_irfs = irf_result["median"]
    bands = irf_result["bands"]
    var_names = irf_result["var_names"]
    horizon = irf_result["horizon"]
    k = len(var_names)

    if figsize is None:
        figsize = (12, 3 * k)

    fig, axes = plt.subplots(k, 1, figsize=figsize, sharex=True)
    if k == 1:
        axes = [axes]

    x = np.arange(horizon + 1)
    sorted_bands = sorted(bands.keys())

    for i, ax in enumerate(axes):
        # Credible bands
        if len(sorted_bands) >= 2:
            lower = bands[sorted_bands[0]][:, i]
            upper = bands[sorted_bands[-1]][:, i]
            ax.fill_between(x, lower, upper, color=COLORS["band"],
                            alpha=0.4, label=f"{int(sorted_bands[0]*100)}-"
                            f"{int(sorted_bands[-1]*100)}% CI")

        # Median
        ax.plot(x, median_irfs[:, i], color=COLORS["median"],
                linewidth=2, label="Median")
        ax.axhline(0, color="black", linewidth=0.5, alpha=0.5)
        ax.set_ylabel(var_names[i])

        if i == 0:
            ax.legend(loc="upper right")

    shock_label = shock_name or f"Shock {irf_result['shock_idx']}"
    fig_title = title or f"QIRF: Response to {shock_label}"
    axes[0].set_title(fig_title)
    axes[-1].set_xlabel("Quarters")
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# 5. QIRF comparison across quantiles (the key figure from the paper)
# ═══════════════════════════════════════════════════════════════════════════

def plot_qirf_quantile_comparison(
    irf_results_by_quantile: dict,
    response_var_idx: int,
    var_names: list[str],
    shock_name: Optional[str] = None,
    quantile_labels: Optional[dict] = None,
    title: Optional[str] = None,
    save_path: Optional[str] = None,
    figsize: tuple = (10, 6),
) -> plt.Figure:
    """
    Compare QIRFs across quantiles for a specific response variable.

    This replicates the key figure from Beutel et al. (2025): response
    of GDP growth at Q10%, Q50%, Q90% to a U.S. financial shock.

    Parameters
    ----------
    irf_results_by_quantile : Dict mapping quantile label (e.g., 0.1) to
        IRF result dictionaries (from compute_bayesian_qirfs_cholesky).
    response_var_idx : Index of the response variable to plot.
    var_names : Variable names.
    shock_name : Name of the shock.
    quantile_labels : Dict mapping quantile -> display label.
    title : Custom title.
    save_path : Save path.
    figsize : Figure size.
    """
    _setup_style()
    fig, ax = plt.subplots(1, 1, figsize=figsize)

    default_colors = {0.1: COLORS["q10"], 0.5: COLORS["median"],
                      0.9: COLORS["q90"]}
    default_labels = {0.1: "Q10%", 0.5: "Median (Q50%)", 0.9: "Q90%"}

    for q_level, irf_result in sorted(irf_results_by_quantile.items()):
        median_irfs = irf_result["median"]
        bands = irf_result["bands"]
        horizon = irf_result["horizon"]
        x = np.arange(horizon + 1)

        color = default_colors.get(q_level, None)
        if color is None:
            # Fallback color cycle
            color = plt.cm.coolwarm(q_level)

        label = (quantile_labels or default_labels).get(
            q_level, f"Q{int(q_level*100)}%")

        # Plot median IRF
        ax.plot(x, median_irfs[:, response_var_idx], color=color,
                linewidth=2, label=label)

        # Shaded band
        sorted_bands = sorted(bands.keys())
        if len(sorted_bands) >= 2:
            lower = bands[sorted_bands[0]][:, response_var_idx]
            upper = bands[sorted_bands[-1]][:, response_var_idx]
            ax.fill_between(x, lower, upper, color=color, alpha=0.15)

    ax.axhline(0, color="black", linewidth=0.5, alpha=0.5)
    ax.legend(loc="lower right")
    ax.set_xlabel("Quarters")
    ax.set_ylabel(var_names[response_var_idx])

    shock_label = shock_name or "Structural Shock"
    fig_title = title or f"QIRF: {var_names[response_var_idx]} response to {shock_label}"
    ax.set_title(fig_title)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_qirf_all_variables_by_quantile(
    irf_results_by_quantile: dict,
    var_names: list[str],
    shock_name: Optional[str] = None,
    title: Optional[str] = None,
    save_path: Optional[str] = None,
    figsize: Optional[tuple] = None,
) -> plt.Figure:
    """
    Plot QIRFs for ALL variables across quantiles in a multi-panel figure.

    Each panel shows one variable's response at Q10%, Q50%, Q90%.
    """
    _setup_style()
    k = len(var_names)
    if figsize is None:
        figsize = (12, 3.5 * k)

    fig, axes = plt.subplots(k, 1, figsize=figsize, sharex=True)
    if k == 1:
        axes = [axes]

    default_colors = {0.1: COLORS["q10"], 0.5: COLORS["median"],
                      0.9: COLORS["q90"]}
    default_labels = {0.1: "Q10%", 0.5: "Q50%", 0.9: "Q90%"}

    for i, ax in enumerate(axes):
        for q_level, irf_result in sorted(irf_results_by_quantile.items()):
            median_irfs = irf_result["median"]
            bands = irf_result["bands"]
            horizon = irf_result["horizon"]
            x = np.arange(horizon + 1)

            color = default_colors.get(q_level, plt.cm.coolwarm(q_level))
            label = default_labels.get(q_level, f"Q{int(q_level*100)}%")

            ax.plot(x, median_irfs[:, i], color=color, linewidth=2, label=label)

            sorted_bands = sorted(bands.keys())
            if len(sorted_bands) >= 2:
                lower = bands[sorted_bands[0]][:, i]
                upper = bands[sorted_bands[-1]][:, i]
                ax.fill_between(x, lower, upper, color=color, alpha=0.12)

        ax.axhline(0, color="black", linewidth=0.5, alpha=0.5)
        ax.set_ylabel(var_names[i])

        if i == 0:
            ax.legend(loc="upper right", ncol=3)

    shock_label = shock_name or "Structural Shock"
    fig_title = title or f"QIRFs: Response to {shock_label}"
    axes[0].set_title(fig_title)
    axes[-1].set_xlabel("Quarters")
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# 6. Sign restriction IRFs
# ═══════════════════════════════════════════════════════════════════════════

def plot_sign_restriction_irfs(
    sign_result: dict,
    shock_idx: int = 0,
    var_names: Optional[list[str]] = None,
    shock_name: Optional[str] = None,
    credible_levels: tuple = (0.16, 0.84),
    save_path: Optional[str] = None,
    figsize: Optional[tuple] = None,
) -> plt.Figure:
    """
    Plot IRFs from sign-restriction identification.

    Shows the median and credible set from accepted rotation draws.
    """
    _setup_style()
    shock_data = sign_result["shocks"][shock_idx]
    median_irfs = shock_data["median"]
    all_irfs = shock_data["all_irfs"]  # (n_accepted, H+1, k)

    k = median_irfs.shape[1]
    var_names = var_names or sign_result.get("var_names", [f"y{i}" for i in range(k)])
    horizon = median_irfs.shape[0] - 1

    if figsize is None:
        figsize = (12, 3 * k)

    fig, axes = plt.subplots(k, 1, figsize=figsize, sharex=True)
    if k == 1:
        axes = [axes]

    x = np.arange(horizon + 1)

    for i, ax in enumerate(axes):
        # Credible bands
        lower = np.percentile(all_irfs[:, :, i], credible_levels[0] * 100, axis=0)
        upper = np.percentile(all_irfs[:, :, i], credible_levels[1] * 100, axis=0)
        ax.fill_between(x, lower, upper, color=COLORS["band"], alpha=0.4,
                        label=f"{int(credible_levels[0]*100)}-"
                              f"{int(credible_levels[1]*100)}% CI")

        # Median
        ax.plot(x, median_irfs[:, i], color=COLORS["median"], linewidth=2,
                label="Median")
        ax.axhline(0, color="black", linewidth=0.5, alpha=0.5)
        ax.set_ylabel(var_names[i])

        if i == 0:
            ax.legend(loc="upper right")

    shock_label = shock_name or f"Shock {shock_idx}"
    n_acc = sign_result["n_accepted"]
    axes[0].set_title(
        f"QIRF (sign restrictions): Response to {shock_label} "
        f"({n_acc} accepted draws)")
    axes[-1].set_xlabel("Quarters")
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# 7. FEVD
# ═══════════════════════════════════════════════════════════════════════════

def plot_fevd(
    fevd: np.ndarray,
    var_names: list[str],
    title: str = "Forecast Error Variance Decomposition",
    save_path: Optional[str] = None,
    figsize: tuple = (10, 6),
) -> plt.Figure:
    """Plot FEVD as a stacked bar chart."""
    _setup_style()
    k = len(var_names)
    fig, ax = plt.subplots(1, 1, figsize=figsize)

    x = np.arange(k)
    bottom = np.zeros(k)
    cmap = plt.cm.Set3

    for j in range(k):
        color = cmap(j / k)
        ax.bar(x, fevd[:, j], bottom=bottom, color=color,
               label=f"Shock: {var_names[j]}", alpha=0.8)
        bottom += fevd[:, j]

    ax.set_xticks(x)
    ax.set_xticklabels(var_names, rotation=45, ha="right")
    ax.set_ylabel("Share of forecast error variance")
    ax.set_title(title)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig
