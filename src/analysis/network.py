"""
Network analysis of bank–NBFI interlinkages.

Constructs weighted bipartite and full networks from bilateral exposure data
and computes centrality measures, community structure, and systemic importance
metrics following the methodology described in:
  - Abad et al. (2022) — euro-area derivatives network
  - Aldasoro, Huang & Kemp (2020) — BIS cross-border bank-NBFI exposures
  - Cont & Schaanning (2017) — fire-sale contagion through overlapping portfolios
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import networkx as nx
from typing import Optional


def build_exposure_network(
    exposures: pd.DataFrame,
    date: Optional[str] = None,
) -> nx.DiGraph:
    """
    Build a directed weighted network from bilateral exposure data.

    Parameters
    ----------
    exposures : DataFrame with columns [date, source, target, exposure_usd_mn]
    date : If provided, filter to a single quarter.

    Returns
    -------
    nx.DiGraph with edge attribute 'weight' = exposure amount.
    """
    if date is not None:
        exposures = exposures[exposures["date"] == date]

    G = nx.DiGraph()
    for _, row in exposures.iterrows():
        G.add_edge(
            row["source"],
            row["target"],
            weight=row["exposure_usd_mn"],
        )
    return G


def compute_centrality_measures(G: nx.DiGraph) -> pd.DataFrame:
    """
    Compute node-level centrality measures for an exposure network.

    Returns DataFrame with columns:
      - in_degree, out_degree, total_degree
      - in_strength, out_strength, total_strength (weighted degree)
      - eigenvector_centrality
      - betweenness_centrality
      - pagerank
    """
    nodes = list(G.nodes())

    in_deg = dict(G.in_degree())
    out_deg = dict(G.out_degree())
    in_str = dict(G.in_degree(weight="weight"))
    out_str = dict(G.out_degree(weight="weight"))

    try:
        eigen = nx.eigenvector_centrality_numpy(G, weight="weight")
    except Exception:
        eigen = {n: np.nan for n in nodes}

    between = nx.betweenness_centrality(G, weight="weight")
    pr = nx.pagerank(G, weight="weight")

    records = []
    for n in nodes:
        records.append({
            "node": n,
            "in_degree": in_deg.get(n, 0),
            "out_degree": out_deg.get(n, 0),
            "total_degree": in_deg.get(n, 0) + out_deg.get(n, 0),
            "in_strength": in_str.get(n, 0),
            "out_strength": out_str.get(n, 0),
            "total_strength": in_str.get(n, 0) + out_str.get(n, 0),
            "eigenvector_centrality": eigen.get(n, np.nan),
            "betweenness_centrality": between.get(n, 0),
            "pagerank": pr.get(n, 0),
        })
    return pd.DataFrame(records).set_index("node")


def compute_network_statistics(G: nx.DiGraph) -> dict:
    """
    Compute aggregate network-level statistics.

    Returns dict with density, reciprocity, clustering, assortativity,
    total exposure, concentration (HHI), and number of components.
    """
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    weights = np.array([d["weight"] for _, _, d in G.edges(data=True)])

    stats = {
        "n_nodes": n_nodes,
        "n_edges": n_edges,
        "density": nx.density(G),
        "reciprocity": nx.reciprocity(G) if n_edges > 0 else 0,
        "total_exposure": weights.sum() if len(weights) > 0 else 0,
        "mean_exposure": weights.mean() if len(weights) > 0 else 0,
        "max_exposure": weights.max() if len(weights) > 0 else 0,
        "hhi_exposure": (
            np.sum((weights / weights.sum()) ** 2) if weights.sum() > 0 else 0
        ),
        "n_weakly_connected": nx.number_weakly_connected_components(G),
    }

    # Assortativity (degree correlation)
    try:
        stats["degree_assortativity"] = nx.degree_assortativity_coefficient(G)
    except Exception:
        stats["degree_assortativity"] = np.nan

    return stats


def rolling_network_statistics(
    exposures: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute network statistics for each quarter in the exposure data.

    Returns a DataFrame indexed by date with network-level metrics.
    """
    dates = sorted(exposures["date"].unique())
    records = []
    for date in dates:
        G = build_exposure_network(exposures, date=date)
        stats = compute_network_statistics(G)
        stats["date"] = date
        records.append(stats)
    return pd.DataFrame(records).set_index("date")


def bipartite_projection(
    exposures: pd.DataFrame,
    date: Optional[str] = None,
    project_on: str = "bank",
) -> nx.Graph:
    """
    Create a one-mode projection of the bipartite bank-NBFI network.

    If project_on='bank', two banks are connected if they share NBFI
    counterparties (weighted by sum of shared exposure). This captures
    indirect contagion through common counterparties.
    """
    if date is not None:
        exposures = exposures[exposures["date"] == date]

    B = nx.Graph()
    sources = exposures["source"].unique()
    targets = exposures["target"].unique()

    B.add_nodes_from(sources, bipartite=0)  # banks
    B.add_nodes_from(targets, bipartite=1)  # NBFIs

    for _, row in exposures.iterrows():
        B.add_edge(row["source"], row["target"], weight=row["exposure_usd_mn"])

    if project_on == "bank":
        nodes = sources
    else:
        nodes = targets

    return nx.bipartite.weighted_projected_graph(B, nodes)


def compute_contagion_matrix(
    exposures: pd.DataFrame,
    institutions: pd.DataFrame,
    date: Optional[str] = None,
    loss_given_default: float = 0.6,
) -> pd.DataFrame:
    """
    Compute a simple direct-contagion loss matrix.

    Entry (i, j) = loss to institution i if institution j defaults,
    calculated as LGD × exposure(i → j).

    This is the first-round loss; iterating gives cascade effects
    (Eisenberg & Noe 2001 style clearing).
    """
    if date is not None:
        exposures = exposures[exposures["date"] == date]

    nodes = sorted(
        set(exposures["source"].tolist() + exposures["target"].tolist())
    )
    n = len(nodes)
    node_idx = {node: i for i, node in enumerate(nodes)}

    matrix = np.zeros((n, n))
    for _, row in exposures.iterrows():
        i = node_idx[row["source"]]
        j = node_idx[row["target"]]
        matrix[i, j] = loss_given_default * row["exposure_usd_mn"]

    return pd.DataFrame(matrix, index=nodes, columns=nodes)
