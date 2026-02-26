"""
QVAR Wrapper — Main interface for the Bayesian Quantile VAR framework.

This is the user-facing entry point. It allows you to:
  1. Load data (CSV, Excel, or pass a DataFrame directly)
  2. Select variables and sample period
  3. Choose identification scheme (Cholesky or sign restrictions)
  4. Run estimation
  5. Compute QIRFs at multiple quantiles
  6. Run diagnostics
  7. Generate all plots
  8. Save results to disk

Usage example
-------------
>>> from src.econometrics.qvar_wrapper import QVARModel
>>>
>>> model = QVARModel()
>>> model.load_data("data/my_data.csv", date_col="date")
>>> model.select_variables(["EBP", "GDP_growth", "CPI_inflation", "interest_rate"])
>>> model.set_sample("1980Q1", "2018Q4")
>>> model.configure(lags=2, identification="cholesky")
>>>
>>> # Estimate at multiple quantiles and compute QIRFs
>>> model.estimate_and_analyze(
...     quantiles=[0.1, 0.5, 0.9],
...     shock_idx=0,
...     horizon=20,
...     n_draws=10000,
...     n_burnin=5000,
... )
>>>
>>> # Generate all plots
>>> model.plot_all(output_dir="output/qvar_results")
>>>
>>> # Save results
>>> model.save(output_dir="output/qvar_results")

References
----------
- Beutel, Emter, Metiu, Prieto & Schüler (2025). "The global financial cycle
  and macroeconomic tail risks." JIMF 156, 103342.
- Schüler (2020). "The impact of uncertainty and certainty shocks."
  Bundesbank Discussion Paper 2020/14.
- Arias, Rubio-Ramírez & Waggoner (2018). "Inference based on SVARs
  identified with sign and zero restrictions." Econometrica 86(2), 685-720.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional
from pathlib import Path

from .bayesian_qvar import BayesianQVAR
from .identification import (
    cholesky_identification,
    compute_shock_vector,
    identify_shocks,
)
from .qvar_irf import (
    compute_qirf,
    compute_bayesian_qirfs_cholesky,
    compute_bayesian_qirfs_sign_restrictions,
    compute_bayesian_qirfs_zero_sign,
    compute_qvar_fevd,
)
from .qvar_diagnostics import run_diagnostics, save_results
from .qvar_plots import (
    plot_variables,
    plot_trace_diagnostics,
    plot_structural_shocks,
    plot_qirfs,
    plot_qirf_quantile_comparison,
    plot_qirf_all_variables_by_quantile,
    plot_sign_restriction_irfs,
    plot_fevd,
)


class QVARModel:
    """
    High-level wrapper for Bayesian Quantile VAR estimation and analysis.

    Workflow:
        1. load_data() or set_data()
        2. select_variables()
        3. set_sample() [optional]
        4. configure()
        5. estimate_and_analyze()
        6. plot_all() and/or save()
    """

    def __init__(self):
        self.raw_data: Optional[pd.DataFrame] = None
        self.data: Optional[pd.DataFrame] = None
        self.var_names: list[str] = []
        self.date_col: Optional[str] = None
        self.dates: Optional[np.ndarray] = None

        # Configuration
        self.lags: int = 2
        self.identification: str = "cholesky"
        self.sign_restrictions: Optional[dict] = None
        self.configured: bool = False

        # Results storage
        self.estimations: dict = {}  # quantile -> BayesianQVAR + results
        self.irf_results: dict = {}  # quantile -> IRF results
        self.diagnostics_results: dict = {}  # quantile -> diagnostics
        self.fevd_results: dict = {}  # quantile -> FEVD

    # ═══════════════════════════════════════════════════════════════════
    # Step 1: Data loading
    # ═══════════════════════════════════════════════════════════════════

    def load_data(
        self,
        filepath: str,
        date_col: Optional[str] = None,
        sheet_name: Optional[str] = None,
    ) -> "QVARModel":
        """
        Load data from CSV or Excel file.

        Parameters
        ----------
        filepath : Path to data file (.csv or .xlsx).
        date_col : Name of the date column (will be set as index).
        sheet_name : For Excel files, the sheet to read.

        Returns
        -------
        self (for method chaining).
        """
        path = Path(filepath)
        if path.suffix == ".csv":
            self.raw_data = pd.read_csv(filepath)
        elif path.suffix in (".xlsx", ".xls"):
            self.raw_data = pd.read_excel(filepath, sheet_name=sheet_name)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        if date_col and date_col in self.raw_data.columns:
            self.date_col = date_col
            self.raw_data[date_col] = pd.to_datetime(self.raw_data[date_col])
            self.raw_data = self.raw_data.set_index(date_col)

        print(f"Data loaded: {self.raw_data.shape[0]} observations, "
              f"{self.raw_data.shape[1]} variables")
        print(f"Columns: {list(self.raw_data.columns)}")

        return self

    def set_data(self, data: pd.DataFrame) -> "QVARModel":
        """
        Set data directly from a DataFrame.

        Parameters
        ----------
        data : DataFrame with variables as columns.
               Index should be dates if available.

        Returns
        -------
        self (for method chaining).
        """
        self.raw_data = data.copy()
        print(f"Data set: {self.raw_data.shape[0]} observations, "
              f"{self.raw_data.shape[1]} variables")
        return self

    # ═══════════════════════════════════════════════════════════════════
    # Step 2: Variable selection
    # ═══════════════════════════════════════════════════════════════════

    def select_variables(self, variables: list[str]) -> "QVARModel":
        """
        Select which variables to include in the QVAR.

        The ORDER matters for Cholesky identification:
        variables ordered first can affect all others contemporaneously.

        Parameters
        ----------
        variables : List of column names in the order for the VAR.

        Returns
        -------
        self (for method chaining).
        """
        if self.raw_data is None:
            raise RuntimeError("Load data first with load_data() or set_data().")

        missing = [v for v in variables if v not in self.raw_data.columns]
        if missing:
            raise ValueError(f"Variables not found in data: {missing}")

        self.var_names = variables
        self.data = self.raw_data[variables].copy()

        # Drop rows with NaN
        n_before = len(self.data)
        self.data = self.data.dropna()
        n_after = len(self.data)
        if n_before != n_after:
            print(f"Dropped {n_before - n_after} rows with missing values. "
                  f"Remaining: {n_after} observations.")

        if hasattr(self.data.index, 'to_numpy'):
            self.dates = self.data.index.to_numpy()

        print(f"Selected {len(variables)} variables: {variables}")
        return self

    # ═══════════════════════════════════════════════════════════════════
    # Step 3: Sample selection
    # ═══════════════════════════════════════════════════════════════════

    def set_sample(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> "QVARModel":
        """
        Restrict the sample period.

        Parameters
        ----------
        start : Start date (e.g., "1980-01-01" or "1980Q1").
        end : End date.

        Returns
        -------
        self (for method chaining).
        """
        if self.data is None:
            raise RuntimeError("Select variables first.")

        if start:
            self.data = self.data[self.data.index >= pd.Timestamp(start)]
        if end:
            self.data = self.data[self.data.index <= pd.Timestamp(end)]

        if hasattr(self.data.index, 'to_numpy'):
            self.dates = self.data.index.to_numpy()

        print(f"Sample: {self.data.index[0]} to {self.data.index[-1]} "
              f"({len(self.data)} observations)")
        return self

    # ═══════════════════════════════════════════════════════════════════
    # Step 4: Configuration
    # ═══════════════════════════════════════════════════════════════════

    def configure(
        self,
        lags: int = 2,
        identification: str = "cholesky",
        sign_restrictions: Optional[dict] = None,
        zero_restrictions: Optional[dict] = None,
    ) -> "QVARModel":
        """
        Configure the QVAR model.

        Parameters
        ----------
        lags : Lag order.
        identification : "cholesky", "sign_restrictions", or
            "zero_sign_restrictions".
        sign_restrictions : For sign or zero+sign identification.
            Dict with keys (shock_idx, response_var_idx, horizon)
            and values +1 or -1.
        zero_restrictions : For zero+sign identification.
            Dict with keys (shock_idx, response_var_idx, horizon)
            and values 0.

        Returns
        -------
        self (for method chaining).
        """
        self.lags = lags
        self.identification = identification
        self.sign_restrictions = sign_restrictions
        self.zero_restrictions = zero_restrictions
        self.configured = True

        print(f"Configuration: lags={lags}, identification={identification}")
        if sign_restrictions:
            print(f"  Sign restrictions: {len(sign_restrictions)} constraints")
        if zero_restrictions:
            print(f"  Zero restrictions: {len(zero_restrictions)} constraints")
        return self

    # ═══════════════════════════════════════════════════════════════════
    # Step 5: Estimation and analysis
    # ═══════════════════════════════════════════════════════════════════

    def estimate_and_analyze(
        self,
        quantiles: list[float] = [0.1, 0.5, 0.9],
        shock_idx: int = 0,
        shock_size: float = 1.0,
        horizon: int = 20,
        n_draws: int = 10000,
        n_burnin: int = 5000,
        mh_scale: float = 0.1,
        seed: int = 42,
        credible_levels: tuple = (0.16, 0.84),
        n_rotations: int = 5000,
        max_horizon_check: int = 0,
        verbose: bool = True,
    ) -> "QVARModel":
        """
        Run the full estimation and analysis pipeline.

        For each quantile in `quantiles`:
        1. Set tau vector: response variable at the specified quantile,
           all others at 0.5 (following the paper's parameterization)
        2. Estimate Bayesian QVAR
        3. Run diagnostics
        4. Compute QIRFs with credible bands

        Parameters
        ----------
        quantiles : List of quantile levels to estimate (e.g., [0.1, 0.5, 0.9]).
        shock_idx : Index of the structural shock of interest.
        shock_size : Shock size (default 1.0 for unit shock).
        horizon : IRF horizon in quarters.
        n_draws : Number of posterior draws (after burn-in).
        n_burnin : Number of burn-in draws.
        mh_scale : Scale for MH random walk (for C parameter).
        seed : Random seed.
        credible_levels : Quantiles for credible bands (default: 68%).
        n_rotations : Number of rotation draws for sign restrictions.
        max_horizon_check : Max horizon for sign restriction checks.
        verbose : Print progress.

        Returns
        -------
        self (for method chaining).
        """
        if self.data is None:
            raise RuntimeError("Select variables first.")
        if not self.configured:
            raise RuntimeError("Configure the model first with configure().")

        data_arr = self.data.values
        k = len(self.var_names)

        for q_idx, q_level in enumerate(quantiles):
            print(f"\n{'='*60}")
            print(f"Estimating QVAR at quantile {q_level}")
            print(f"{'='*60}")

            # Build tau vector: GDP (or target) at q_level, others at 0.5
            # The user controls which variable is the "target" via the
            # variable ordering: typically the response variable of interest
            # Following the paper: tau_i=j = q_level, tau_i!=j = 0.5
            # Here we set ALL variables to q_level for generality,
            # but you can customize per the paper's approach
            tau_vec = np.full(k, 0.5)
            # In the paper, only the GDP variable gets the tail quantile.
            # But we provide it for all for maximum flexibility.
            # You can modify this per your needs.
            tau_vec[:] = q_level  # Simple approach: same quantile for all

            # Create estimator
            qvar = BayesianQVAR(
                data=data_arr,
                lags=self.lags,
                tau=tau_vec,
                var_names=self.var_names,
            )

            # Estimate
            est_result = qvar.estimate(
                n_draws=n_draws,
                n_burnin=n_burnin,
                mh_scale=mh_scale,
                seed=seed + q_idx,
                verbose=verbose,
            )

            # Diagnostics
            if verbose:
                print(f"\nRunning diagnostics...")
            diag = run_diagnostics(est_result)
            if verbose:
                print(f"  ESS (min/median/max): "
                      f"{diag['ess']['min']:.0f} / "
                      f"{diag['ess']['median']:.0f} / "
                      f"{diag['ess']['max']:.0f}")
                print(f"  Stationarity rate: {diag['stationarity_rate']:.3f}")
                print(f"  Geweke pass rate: {diag['geweke_pass_rate']:.3f}")

            # QIRFs
            if verbose:
                print(f"Computing QIRFs...")

            if self.identification == "cholesky":
                irf_result = compute_bayesian_qirfs_cholesky(
                    est_result,
                    shock_idx=shock_idx,
                    shock_size=shock_size,
                    horizon=horizon,
                    credible_levels=credible_levels,
                )
                if verbose:
                    print(f"  Valid IRF draws: {irf_result['n_valid']}/{irf_result['n_total']}")

            elif self.identification == "sign_restrictions":
                if self.sign_restrictions is None:
                    raise ValueError("Sign restrictions not specified.")
                irf_result = compute_bayesian_qirfs_sign_restrictions(
                    est_result,
                    sign_restrictions=self.sign_restrictions,
                    horizon=horizon,
                    n_rotations_per_draw=n_rotations,
                    max_horizon_check=max_horizon_check,
                    credible_levels=credible_levels,
                    seed=seed + q_idx + 100,
                )
                if verbose:
                    print(f"  Accepted rotation draws: "
                          f"{irf_result['n_accepted']}")

            elif self.identification == "zero_sign_restrictions":
                if self.zero_restrictions is None:
                    raise ValueError("Zero restrictions not specified.")
                irf_result = compute_bayesian_qirfs_zero_sign(
                    est_result,
                    zero_restrictions=self.zero_restrictions,
                    sign_restrictions=self.sign_restrictions or {},
                    horizon=horizon,
                    n_rotations_per_draw=n_rotations,
                    max_horizon_check=max_horizon_check,
                    credible_levels=credible_levels,
                    seed=seed + q_idx + 100,
                )
                if verbose:
                    print(f"  Accepted rotation draws: "
                          f"{irf_result['n_accepted']}")
            else:
                raise ValueError(f"Unknown identification: {self.identification}")

            # Store
            self.estimations[q_level] = {
                "model": qvar,
                "result": est_result,
            }
            self.irf_results[q_level] = irf_result
            self.diagnostics_results[q_level] = diag

        print(f"\n{'='*60}")
        print(f"Estimation complete for quantiles: {quantiles}")
        print(f"{'='*60}")

        return self

    def estimate_single(
        self,
        tau: float | np.ndarray = 0.5,
        n_draws: int = 10000,
        n_burnin: int = 5000,
        mh_scale: float = 0.1,
        seed: int = 42,
        verbose: bool = True,
    ) -> dict:
        """
        Estimate QVAR at a single quantile (or custom tau vector).

        Returns the raw estimation result without computing IRFs.
        Use this for custom analyses.
        """
        if self.data is None:
            raise RuntimeError("Select variables first.")

        qvar = BayesianQVAR(
            data=self.data.values,
            lags=self.lags,
            tau=tau,
            var_names=self.var_names,
        )
        return qvar.estimate(
            n_draws=n_draws,
            n_burnin=n_burnin,
            mh_scale=mh_scale,
            seed=seed,
            verbose=verbose,
        )

    # ═══════════════════════════════════════════════════════════════════
    # Step 6: Plotting
    # ═══════════════════════════════════════════════════════════════════

    def plot_all(
        self,
        output_dir: str = "output/qvar_results",
        shock_name: Optional[str] = None,
        show: bool = True,
    ) -> dict:
        """
        Generate all plots and optionally save to disk.

        Parameters
        ----------
        output_dir : Directory for saved figures.
        shock_name : Name of the shock for titles.
        show : Whether to display plots.

        Returns
        -------
        Dictionary of figure objects.
        """
        import matplotlib
        if not show:
            matplotlib.use("Agg")

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        figures = {}

        # 1. Raw data
        if self.data is not None:
            fig = plot_variables(
                self.data.values, self.var_names,
                dates=self.dates,
                save_path=f"{output_dir}/01_variables.png",
            )
            figures["variables"] = fig

        # 2. Trace diagnostics (for median quantile if available)
        median_q = None
        for q in [0.5, 0.1, 0.9]:
            if q in self.estimations:
                median_q = q
                break

        if median_q is not None:
            est = self.estimations[median_q]["result"]
            fig = plot_trace_diagnostics(
                est["beta_draws"], self.var_names,
                est["k"], est["lags"],
                save_path=f"{output_dir}/02_trace_diagnostics_q{int(median_q*100)}.png",
            )
            figures["trace"] = fig

        # 3. Structural shocks (from median posterior, Cholesky)
        if median_q is not None and self.identification == "cholesky":
            est = self.estimations[median_q]
            B_median = est["model"].get_posterior_median_coefficients()
            residuals_median = np.median(est["result"]["residual_draws"], axis=0)

            try:
                id_result = cholesky_identification(
                    residuals_median, est["result"]["tau"])
                fig = plot_structural_shocks(
                    id_result["structural_shocks"],
                    self.var_names,
                    dates=self.dates[self.lags:] if self.dates is not None else None,
                    save_path=f"{output_dir}/03_structural_shocks_q{int(median_q*100)}.png",
                )
                figures["shocks"] = fig
            except Exception as e:
                print(f"Warning: Could not plot structural shocks: {e}")

        # 4. QIRFs for each quantile
        for q_level, irf_result in self.irf_results.items():
            q_tag = int(q_level * 100)

            if self.identification == "cholesky":
                fig = plot_qirfs(
                    irf_result,
                    shock_name=shock_name,
                    title=f"QIRF at Q{q_tag}%: Response to "
                          f"{shock_name or 'Shock'}",
                    save_path=f"{output_dir}/04_qirf_q{q_tag}.png",
                )
                figures[f"qirf_q{q_tag}"] = fig
            elif self.identification in ("sign_restrictions",
                                          "zero_sign_restrictions"):
                for shock_idx in irf_result.get("shocks", {}).keys():
                    fig = plot_sign_restriction_irfs(
                        irf_result,
                        shock_idx=shock_idx,
                        var_names=self.var_names,
                        shock_name=shock_name,
                        save_path=f"{output_dir}/04_qirf_sign_q{q_tag}_shock{shock_idx}.png",
                    )
                    figures[f"qirf_sign_q{q_tag}_s{shock_idx}"] = fig

        # 5. Comparison across quantiles (the key figure)
        if (self.identification == "cholesky"
                and len(self.irf_results) > 1):

            # For each response variable
            k = len(self.var_names)
            for var_idx in range(k):
                fig = plot_qirf_quantile_comparison(
                    self.irf_results,
                    response_var_idx=var_idx,
                    var_names=self.var_names,
                    shock_name=shock_name,
                    save_path=f"{output_dir}/05_qirf_comparison_{self.var_names[var_idx]}.png",
                )
                figures[f"comparison_{self.var_names[var_idx]}"] = fig

            # All variables in one figure
            fig = plot_qirf_all_variables_by_quantile(
                self.irf_results,
                self.var_names,
                shock_name=shock_name,
                save_path=f"{output_dir}/05_qirf_comparison_all.png",
            )
            figures["comparison_all"] = fig

        if not show:
            import matplotlib.pyplot as plt
            plt.close("all")

        print(f"Generated {len(figures)} figures in {output_dir}/")
        return figures

    # ═══════════════════════════════════════════════════════════════════
    # Step 7: Save results
    # ═══════════════════════════════════════════════════════════════════

    def save(self, output_dir: str = "output/qvar_results") -> dict:
        """
        Save all estimation results, diagnostics, and IRFs to disk.

        Returns
        -------
        Dictionary with paths to saved files for each quantile.
        """
        all_saved = {}
        for q_level in self.estimations:
            q_tag = int(q_level * 100)
            saved = save_results(
                self.estimations[q_level]["result"],
                self.diagnostics_results.get(q_level, {}),
                self.irf_results.get(q_level, {}),
                output_dir=output_dir,
                prefix=f"qvar_q{q_tag}",
            )
            all_saved[q_level] = saved

        print(f"Results saved to {output_dir}/")
        return all_saved

    # ═══════════════════════════════════════════════════════════════════
    # Convenience methods
    # ═══════════════════════════════════════════════════════════════════

    def get_estimation(self, quantile: float = 0.5) -> dict:
        """Get the estimation result for a specific quantile."""
        if quantile not in self.estimations:
            raise KeyError(f"No estimation for quantile {quantile}. "
                           f"Available: {list(self.estimations.keys())}")
        return self.estimations[quantile]["result"]

    def get_irfs(self, quantile: float = 0.5) -> dict:
        """Get IRF results for a specific quantile."""
        if quantile not in self.irf_results:
            raise KeyError(f"No IRFs for quantile {quantile}. "
                           f"Available: {list(self.irf_results.keys())}")
        return self.irf_results[quantile]

    def get_diagnostics(self, quantile: float = 0.5) -> dict:
        """Get diagnostics for a specific quantile."""
        if quantile not in self.diagnostics_results:
            raise KeyError(f"No diagnostics for quantile {quantile}.")
        return self.diagnostics_results[quantile]

    def summary(self) -> str:
        """Print a summary of the model and results."""
        lines = ["QVAR Model Summary", "=" * 50]

        if self.data is not None:
            lines.append(f"Variables: {self.var_names}")
            lines.append(f"Observations: {len(self.data)}")
            lines.append(f"Sample: {self.data.index[0]} to {self.data.index[-1]}")

        lines.append(f"Lags: {self.lags}")
        lines.append(f"Identification: {self.identification}")

        if self.estimations:
            lines.append(f"\nEstimated quantiles: {sorted(self.estimations.keys())}")
            for q in sorted(self.estimations.keys()):
                est = self.estimations[q]["result"]
                diag = self.diagnostics_results.get(q, {})
                lines.append(f"\n  Q{int(q*100)}%:")
                lines.append(f"    Posterior draws: {est['n_draws']}")
                lines.append(f"    MH acceptance: {est['mh_acceptance_rate']:.3f}")
                if diag:
                    lines.append(f"    ESS (median): {diag['ess']['median']:.0f}")
                    lines.append(f"    Stationarity: {diag['stationarity_rate']:.3f}")

        return "\n".join(lines)
