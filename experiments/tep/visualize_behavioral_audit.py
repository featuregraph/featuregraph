"""Generate review figures for the Tennessee Eastman behavioral audit."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm
import numpy as np
import pandas as pd

FAULTS = (1, 2, 4, 6, 7, 12, 14)
REGIMES = ("pre_injection", "early_response", "post_response")
REGIME_COLORS = {
    "pre_injection": "#8090a0",
    "early_response": "#e17632",
    "post_response": "#3d78b5",
}
PROPERTIES = (
    "rise_duration",
    "fall_duration",
    "duration",
    "period",
    "amplitude",
    "rising_mean_rate",
    "falling_mean_rate",
    "peak_rise_rate",
    "peak_fall_rate",
    "temporal_symmetry",
)


def _save(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    fig.savefig(output_dir / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_amplitude_by_regime(objects: pd.DataFrame, output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(13, 7))
    positions, values, colors = [], [], []
    for fault_index, fault in enumerate(FAULTS):
        for regime_index, regime in enumerate(REGIMES):
            selected = objects.loc[
                objects["fault_number"].eq(fault)
                & objects["regime"].eq(regime),
                "amplitude",
            ].dropna()
            positions.append(fault_index * 4 + regime_index)
            values.append(np.log10(1 + selected.to_numpy()))
            colors.append(REGIME_COLORS[regime])
    boxes = ax.boxplot(
        values,
        positions=positions,
        widths=0.72,
        patch_artist=True,
        showfliers=False,
        whis=(5, 95),
    )
    for patch, color in zip(boxes["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.72)
    centers = [index * 4 + 1 for index in range(len(FAULTS))]
    ax.set_xticks(centers, [f"Fault {fault}" for fault in FAULTS])
    ax.set_ylabel("log10(1 + amplitude)")
    ax.set_title("TEP reactor-pressure oscillation amplitude by regime")
    handles = [
        plt.Line2D([0], [0], color=color, lw=8, label=regime.replace("_", " "))
        for regime, color in REGIME_COLORS.items()
    ]
    ax.legend(handles=handles, ncols=3, loc="upper right")
    ax.grid(axis="y", alpha=0.25)
    fig.text(
        0.5,
        0.01,
        "Complete FeatureGraph objects across five runs.",
        ha="center",
        fontsize=9,
        color="#59636e",
    )
    _save(fig, output_dir, "amplitude_by_regime")


def _matrix(
    frame: pd.DataFrame,
    regime: str,
    value: str,
    *,
    signatures_only: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    matrix = np.full((len(FAULTS), len(PROPERTIES)), np.nan)
    repeatable = np.zeros_like(matrix, dtype=bool)
    selected = frame.loc[frame["regime"].eq(regime)]
    for row in selected.itertuples(index=False):
        if row.fault_number not in FAULTS or row.property not in PROPERTIES:
            continue
        i = FAULTS.index(row.fault_number)
        j = PROPERTIES.index(row.property)
        current = float(getattr(row, value))
        if signatures_only and row.dominant_direction == "decrease":
            current *= -1
        matrix[i, j] = current
        repeatable[i, j] = bool(row.repeatable)
    return matrix, repeatable


def _heatmap_axes(axes: np.ndarray) -> None:
    for ax in axes:
        ax.set_xticks(range(len(PROPERTIES)), [
            name.replace("_", " ") for name in PROPERTIES
        ], rotation=35, ha="right", fontsize=8)
        ax.set_yticks(range(len(FAULTS)), [f"Fault {fault}" for fault in FAULTS])


def plot_cross_run_effect_sizes(
    reproducibility: pd.DataFrame,
    output_dir: Path,
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), constrained_layout=True)
    norm = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
    image = None
    for ax, regime in zip(axes, ("early_response", "post_response")):
        matrix, repeatable = _matrix(
            reproducibility, regime, "median_cliffs_delta"
        )
        image = ax.imshow(matrix, cmap="RdBu_r", norm=norm, aspect="auto")
        for i, j in zip(*np.where(np.isfinite(matrix))):
            ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", fontsize=7)
            if repeatable[i, j]:
                ax.plot(j + 0.38, i - 0.35, "ko", markersize=3)
        ax.set_title(regime.replace("_", " "))
    _heatmap_axes(axes)
    fig.colorbar(image, ax=axes, label="median Cliff's delta")
    fig.suptitle("Cross-run behavioral effect sizes", fontsize=16)
    fig.text(
        0.5,
        0.005,
        "Dots mark repeatable changes: >=80% directional agreement and |delta| >= 0.33.",
        ha="center",
        fontsize=9,
        color="#59636e",
    )
    _save(fig, output_dir, "cross_run_effect_sizes")


def plot_object_boundary_reconstruction(
    objects: pd.DataFrame,
    output_dir: Path,
    *,
    fault_number: int = 1,
    simulation_run: int = 1,
    start: int = 500,
    end: int = 1250,
) -> None:
    selected = objects.loc[
        objects["fault_number"].eq(fault_number)
        & objects["simulation_run"].eq(simulation_run)
        & objects["end_index"].ge(start)
        & objects["start_index"].le(end)
    ].sort_values("start_index")
    fig, ax = plt.subplots(figsize=(14, 6))
    for row in selected.itertuples(index=False):
        ax.plot(
            [row.start_index, row.peak_index, row.end_index],
            [0, np.log10(1 + row.amplitude), 0],
            color=REGIME_COLORS.get(row.regime, "#8090a0"),
            lw=2,
            marker="o",
            markersize=3,
        )
    ax.axvline(600, color="#b3261e", ls="--", label="fault injection (600)")
    ax.axvline(1200, color="#6d4c8d", ls=":", label="early-response end (1200)")
    ax.set_xlim(start, end)
    ax.set_xlabel("sample index")
    ax.set_ylabel("log10(1 + object amplitude)")
    ax.set_title("Fault 1 behavioral-object reconstruction around injection")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.text(
        0.5,
        0.01,
        "Triangles use FeatureGraph start/peak/end indices and amplitude. "
        "This is not the raw reactor-pressure trace.",
        ha="center",
        fontsize=9,
        color="#59636e",
    )
    _save(fig, output_dir, "object_boundary_reconstruction")


def plot_behavioral_signature_heatmap(
    signatures: pd.DataFrame,
    output_dir: Path,
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), constrained_layout=True)
    max_strength = max(1.0, float(signatures["behavioral_strength"].abs().max()))
    norm = TwoSlopeNorm(vmin=-max_strength, vcenter=0, vmax=max_strength)
    image = None
    for ax, regime in zip(axes, ("early_response", "post_response")):
        matrix, _ = _matrix(
            signatures,
            regime,
            "behavioral_strength",
            signatures_only=True,
        )
        masked = np.ma.masked_invalid(matrix)
        image = ax.imshow(masked, cmap="RdBu_r", norm=norm, aspect="auto")
        for i, j in zip(*np.where(np.isfinite(matrix))):
            row = signatures.loc[
                signatures["fault_number"].eq(FAULTS[i])
                & signatures["regime"].eq(regime)
                & signatures["property"].eq(PROPERTIES[j])
            ].iloc[0]
            ax.text(
                j,
                i,
                f"#{int(row.signature_rank)}\n{matrix[i, j]:.2f}",
                ha="center",
                va="center",
                fontsize=7,
            )
        ax.set_title(regime.replace("_", " "))
    _heatmap_axes(axes)
    fig.colorbar(image, ax=axes, label="signed behavioral strength")
    fig.suptitle("Strongest repeatable behavioral signatures", fontsize=16)
    _save(fig, output_dir, "behavioral_signature_heatmap")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--comparison-dir",
        type=Path,
        default=Path("artifacts/tep/fault_comparison"),
    )
    parser.add_argument(
        "--audit-dir",
        type=Path,
        default=Path("artifacts/tep/behavioral_audit"),
    )
    args = parser.parse_args()
    output_dir = args.audit_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)

    objects = pd.read_csv(args.comparison_dir / "objects.csv")
    reproducibility = pd.read_csv(
        args.audit_dir / "cross_run_reproducibility.csv"
    )
    signatures = pd.read_csv(args.audit_dir / "behavioral_signatures.csv")

    plot_amplitude_by_regime(objects, output_dir)
    plot_cross_run_effect_sizes(reproducibility, output_dir)
    plot_object_boundary_reconstruction(objects, output_dir)
    plot_behavioral_signature_heatmap(signatures, output_dir)
    print("Figures written to", output_dir)


if __name__ == "__main__":
    main()
