"""Generate the BIDMC multiscale paper figures from published artifacts.

Figures are derived artifacts and carry the same provenance as the numbers:
each is regenerated from a committed CSV, and nothing is drawn by hand. This
script reads no network and no cached signal data, so it reproduces anywhere
the repository does.

The construction figure for subject 13 is not made here. It needs the raw BIDMC
signals and is produced by ``scripts/analyze_bidmc_subject13_multiscale.py``.

Usage:
    python scripts/plot_bidmc_paper_figures.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HELDOUT = ROOT / "artifacts" / "studies" / "bidmc_multiscale_heldout"
WINDOW_85 = ROOT / "artifacts" / "studies" / "bidmc_window_85"
FIGURES = ROOT / "artifacts" / "paper" / "master" / "figures"

# Validated categorical pair: CVD separation dE 24.7, normal-vision 33.6,
# both inside the lightness band and above 3:1 on the chart surface. Marker
# shape repeats the distinction so the figures survive greyscale printing.
SHARED = "#2a78d6"
ONLY_79 = "#eb6834"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_MUTED = "#52514e"
GRID = "#d9d8d4"


def style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.edgecolor": GRID,
            "axes.labelcolor": INK,
            "axes.labelsize": 9,
            "axes.titlesize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "text.color": INK,
            "xtick.color": INK_MUTED,
            "ytick.color": INK_MUTED,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "legend.frameon": False,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "lines.linewidth": 2.0,
            "font.family": "DejaVu Sans",
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def eligible() -> pd.DataFrame:
    """The 20 held-out records with a class-specific concentration estimate."""
    d = pd.read_csv(HELDOUT / "subject_summary.csv")
    d = d[(d.cohort == "held_out") & d.ecg_valid]
    return d.dropna(subset=["phase_resultant_difference"]).copy()


def save(fig: plt.Figure, name: str) -> None:
    """Write PNG, SVG and PDF.

    PDF is the one arXiv wants: pdflatex takes PDF, PNG and JPG but not SVG,
    and a vector figure survives the printer at any scale.
    """
    FIGURES.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "svg", "pdf"):
        fig.savefig(FIGURES / f"{name}.{suffix}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}.png, {name}.svg and {name}.pdf")


def figure_phase_concentration() -> None:
    """Paired concentration per record. Direction is carried by geometry.

    A bar chart of differences would hide that shared objects are themselves
    concentrated at about 0.38 rather than at zero, which is the fact that
    makes the comparison meaningful.
    """
    d = eligible().sort_values("phase_resultant_difference").reset_index(drop=True)
    x = range(len(d))
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.grid(axis="y", alpha=0.7)
    ax.set_axisbelow(True)
    for i, row in d.iterrows():
        ax.plot(
            [i, i],
            [row.shared_phase_resultant, row.objects_79_only_phase_resultant],
            color=GRID,
            linewidth=1.4,
            zorder=1,
            solid_capstyle="round",
        )
    ax.scatter(
        x, d.shared_phase_resultant, s=42, color=SHARED, marker="o",
        zorder=3, label="Shared objects", edgecolor=SURFACE, linewidth=1.0,
    )
    ax.scatter(
        x, d.objects_79_only_phase_resultant, s=42, color=ONLY_79, marker="s",
        zorder=3, label="W=79-only objects", edgecolor=SURFACE, linewidth=1.0,
    )
    negative = int((d.phase_resultant_difference < 0).sum())
    ax.axvline(negative - 0.5, color=INK_MUTED, linewidth=0.8, linestyle=":")
    ax.text(
        (negative - 1) / 2, 0.95, f"{negative} records decrease",
        fontsize=8, color=INK_MUTED, va="top", ha="center",
    )
    ax.text(
        negative + (len(d) - negative) / 2, 0.95,
        f"{len(d) - negative} records increase",
        fontsize=8, color=INK_MUTED, va="top", ha="center",
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels(d.subject.astype(int), fontsize=7)
    ax.set_xlabel("Held-out record, ordered by difference in concentration")
    ax.set_ylabel("Phase concentration $R$")
    ax.set_ylim(0, 1.02)
    ax.legend(
        loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2, borderaxespad=0
    )
    save(fig, "fig2_phase_concentration_paired")


def figure_rate_against_heart_rate() -> None:
    """W=79-only object rate against monitor heart rate, with a +/-10% band."""
    d = eligible()
    fig, ax = plt.subplots(figsize=(4.6, 4.4))
    ax.grid(alpha=0.7)
    ax.set_axisbelow(True)
    lo, hi = 15, 130
    ax.fill_between(
        [lo, hi], [lo * 0.9, hi * 0.9], [lo * 1.1, hi * 1.1],
        color=GRID, alpha=0.55, linewidth=0, zorder=1,
    )
    ax.plot(
        [lo, hi], [lo, hi],
        color=INK_MUTED, linewidth=1.0, linestyle="--", zorder=2,
    )
    ax.scatter(
        d.monitor_hr_median, d.objects_79_only_rate_median,
        s=48, color=ONLY_79, marker="s", zorder=3,
        edgecolor=SURFACE, linewidth=1.0,
    )
    ax.text(
        hi - 22, hi - 26, "equal rates", fontsize=8, color=INK_MUTED,
        ha="center", va="bottom", rotation=45, rotation_mode="anchor",
    )
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    ax.set_xlabel("Monitor heart rate (beats/min)")
    ax.set_ylabel("W=79-only object rate (per min)")
    ax.set_title("No record falls in the equal-rate band", fontsize=9, loc="left")
    save(fig, "fig3_rate_against_heart_rate")


def figure_annotation_agreement() -> None:
    """The two matching directions against each other, one point per pair."""
    a = pd.read_csv(WINDOW_85 / "annotation_summary.csv")
    fig, ax = plt.subplots(figsize=(4.8, 4.4))
    ax.grid(alpha=0.7)
    ax.set_axisbelow(True)
    for name, colour, marker, label in (
        ("ann1", SHARED, "o", "Annotator 1"),
        ("ann2", ONLY_79, "s", "Annotator 2"),
    ):
        g = a[a.annotator == name]
        ax.scatter(
            g.matched_fraction_reference, g.matched_fraction_detected,
            s=38, color=colour, marker=marker, alpha=0.85, zorder=3,
            edgecolor=SURFACE, linewidth=0.8, label=label,
        )
    ax.axhline(0.95, color=INK_MUTED, linewidth=0.8, linestyle=":")
    ax.axvline(0.95, color=INK_MUTED, linewidth=0.8, linestyle=":")
    ax.text(0.02, 0.955, "0.95", fontsize=7, color=INK_MUTED, va="bottom")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("Fraction of annotated events matched")
    ax.set_ylabel("Fraction of detected peaks matched")
    ax.annotate(
        "record 44,\nannotator 1",
        xy=(0.015, 0.014), xytext=(0.16, 0.10),
        fontsize=7.5, color=INK_MUTED, va="center",
        arrowprops={"arrowstyle": "-", "color": INK_MUTED, "linewidth": 0.8},
    )
    ax.set_title(
        "Annotations rarely missed; detections often unmatched",
        fontsize=9, loc="left",
    )
    ax.legend(loc="center left", bbox_to_anchor=(0.01, 0.55))
    save(fig, "fig4_annotation_agreement")


def main() -> None:
    style()
    print("writing figures to", FIGURES.relative_to(ROOT))
    figure_phase_concentration()
    figure_rate_against_heart_rate()
    figure_annotation_agreement()


if __name__ == "__main__":
    main()
