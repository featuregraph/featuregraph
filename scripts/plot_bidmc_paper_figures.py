"""Generate the BIDMC multiscale paper figures from published artifacts.

Figures are derived artifacts and carry the same provenance as the numbers:
each is regenerated from a committed CSV, and nothing is drawn by hand. This
script reads no network and no cached signal data, so it reproduces anywhere
the repository does.

Figure 1, the construction on one record, is the exception: it draws the raw
subject 13 signals, which are read from ``notebooks/.bidmc_notebook_cache`` when
that cache holds them and skipped, with a message, when it does not. The
computation is the audit's own, imported from
``scripts.analyze_bidmc_subject13_multiscale``.

Figure 5, the lag histogram for subject 13, reads the committed peak table
under ``artifacts/studies/bidmc_peak_measures`` and so needs no signal data.

Usage:
    python -m scripts.plot_bidmc_paper_figures
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analyze_bidmc_subject13_multiscale import (  # noqa: E402
    CACHE,
    END,
    FS,
    START,
    cache_available,
    region_construction,
)

HELDOUT = ROOT / "artifacts" / "studies" / "bidmc_multiscale_heldout"
PEAK_MEASURES = ROOT / "artifacts" / "studies" / "bidmc_peak_measures"
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
            # Fixed salt for SVG element ids; the default salts with object
            # addresses, which differ on every run.
            "svg.hashsalt": "featuregraph",
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
    # No creation date in the file: regenerating a figure from unchanged
    # artifacts then yields byte-identical output, and a clean tree says so.
    metadata = {
        "png": {"Software": None},
        "svg": {"Date": None},
        "pdf": {"CreationDate": None, "ModDate": None, "Producer": None},
    }
    for suffix in ("png", "svg", "pdf"):
        fig.savefig(
            FIGURES / f"{name}.{suffix}",
            dpi=300,
            bbox_inches="tight",
            metadata=metadata[suffix],
        )
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
        x,
        d.shared_phase_resultant,
        s=42,
        color=SHARED,
        marker="o",
        zorder=3,
        label="Shared objects",
        edgecolor=SURFACE,
        linewidth=1.0,
    )
    ax.scatter(
        x,
        d.objects_79_only_phase_resultant,
        s=42,
        color=ONLY_79,
        marker="s",
        zorder=3,
        label="W=79-only objects",
        edgecolor=SURFACE,
        linewidth=1.0,
    )
    negative = int((d.phase_resultant_difference < 0).sum())
    ax.axvline(negative - 0.5, color=INK_MUTED, linewidth=0.8, linestyle=":")
    ax.text(
        (negative - 1) / 2,
        0.95,
        f"{negative} records decrease",
        fontsize=8,
        color=INK_MUTED,
        va="top",
        ha="center",
    )
    ax.text(
        negative + (len(d) - negative) / 2,
        0.95,
        f"{len(d) - negative} records increase",
        fontsize=8,
        color=INK_MUTED,
        va="top",
        ha="center",
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels(d.subject.astype(int), fontsize=7)
    ax.set_xlabel("Held-out record, ordered by difference in concentration")
    ax.set_ylabel("Phase concentration $R$")
    ax.set_ylim(0, 1.02)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2, borderaxespad=0)
    save(fig, "fig2_phase_concentration_paired")


def figure_rate_against_heart_rate() -> None:
    """Local event rate at W=79-only positions against monitor heart rate.

    The plotted quantity is the median, per record, of the local rate of the
    full W=79 construction at the positions where W=79-only objects occur. It
    is not the duration of those objects and not a rate between consecutive
    ones. See Section 9 of the paper.
    """
    d = eligible()
    fig, ax = plt.subplots(figsize=(4.6, 4.4))
    ax.grid(alpha=0.7)
    ax.set_axisbelow(True)
    lo, hi = 15, 130
    ax.fill_between(
        [lo, hi],
        [lo * 0.9, hi * 0.9],
        [lo * 1.1, hi * 1.1],
        color=GRID,
        alpha=0.55,
        linewidth=0,
        zorder=1,
    )
    ax.plot(
        [lo, hi],
        [lo, hi],
        color=INK_MUTED,
        linewidth=1.0,
        linestyle="--",
        zorder=2,
    )
    ax.scatter(
        d.monitor_hr_median,
        d.objects_79_only_rate_median,
        s=48,
        color=ONLY_79,
        marker="s",
        zorder=3,
        edgecolor=SURFACE,
        linewidth=1.0,
    )
    ax.text(
        hi - 22,
        hi - 26,
        "equal rates",
        fontsize=8,
        color=INK_MUTED,
        ha="center",
        va="bottom",
        rotation=45,
        rotation_mode="anchor",
    )
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    ax.set_xlabel("Monitor heart rate (beats/min)")
    ax.set_ylabel("Local event rate at W=79-only objects (per min)")
    ax.set_title(
        "No record's local rate approaches its heart rate",
        fontsize=9,
        loc="left",
    )
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
            g.matched_fraction_reference,
            g.matched_fraction_detected,
            s=38,
            color=colour,
            marker=marker,
            alpha=0.85,
            zorder=3,
            edgecolor=SURFACE,
            linewidth=0.8,
            label=label,
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
        xy=(0.015, 0.014),
        xytext=(0.16, 0.10),
        fontsize=7.5,
        color=INK_MUTED,
        va="center",
        arrowprops={"arrowstyle": "-", "color": INK_MUTED, "linewidth": 0.8},
    )
    ax.set_title(
        "Annotations rarely missed; detections often unmatched",
        fontsize=9,
        loc="left",
    )
    ax.legend(loc="center left", bbox_to_anchor=(0.01, 0.55))
    save(fig, "fig4_annotation_agreement")


def figure_construction(cache: Path = CACHE) -> bool:
    """Figure 1: the construction on subject 13, samples 650 to 1200.

    Two panels sharing the sample axis. Above, the raw respiration with the two
    envelopes and the object peaks each recovers: the one both windows find is
    a shared object, the three only W=79 finds are W=79-only objects, in the
    same colours and marker shapes as every other figure. Below, the filtered
    ECG with its R-peaks, and the interval from each R-peak to the W=79 peak
    that follows it, which is the lag the audit measures. The two annotators'
    breath marks sit as ticks along the top of the upper panel.

    Returns whether the figure was drawn. It is skipped, not failed, when the
    cached signals are absent, so the other figures still regenerate anywhere.
    """
    if not cache_available(cache):
        where = cache.relative_to(ROOT) if cache.is_relative_to(ROOT) else cache
        print(
            "  skipping fig1_subject13_construction: subject 13 signals are not "
            f"cached under {where}"
        )
        return False
    c = region_construction(cache)
    region = np.arange(START, END + 1)
    seconds = (region - START) / FS
    to_s = lambda samples: (np.asarray(samples) - START) / FS  # noqa: E731
    shared_mask = np.isin(c["peaks_79"], c["peaks_100"])

    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(7.2, 4.6), sharex=True, height_ratios=[3, 2]
    )

    top.plot(
        seconds,
        c["raw"].loc[START:END],
        color="0.72",
        linewidth=1.0,
        label="raw respiration",
    )
    top.plot(
        seconds,
        c["smooth_79"].loc[START:END],
        color=ONLY_79,
        linewidth=1.6,
        label="envelope, W = 79",
    )
    top.plot(
        seconds,
        c["smooth_100"].loc[START:END],
        color=SHARED,
        linewidth=1.6,
        label="envelope, W = 100",
    )
    top.scatter(
        to_s(c["peaks_79"][~shared_mask]),
        c["smooth_79"].loc[c["peaks_79"][~shared_mask]],
        s=46,
        color=ONLY_79,
        marker="s",
        zorder=4,
        edgecolor=SURFACE,
        linewidth=1.2,
        label="W = 79-only object peak",
    )
    top.scatter(
        to_s(c["peaks_79"][shared_mask]),
        c["smooth_79"].loc[c["peaks_79"][shared_mask]],
        s=52,
        color=SHARED,
        marker="o",
        zorder=4,
        edgecolor=SURFACE,
        linewidth=1.2,
        label="shared object peak",
    )
    y_top = top.get_ylim()[1]
    for values, style_, name in (
        (c["annotation_1"], "-", "annotator 1 breath mark"),
        (c["annotation_2"], (0, (2, 2)), "annotator 2 breath mark"),
    ):
        for i, value in enumerate(values):
            top.plot(
                [to_s(value)] * 2,
                [y_top * 0.9, y_top],
                color=INK_MUTED,
                linestyle=style_,
                linewidth=1.0,
                label=name if i == 0 else None,
            )
    top.set_ylabel("respiration (a.u.)")
    top.set_title(
        "Subject 13, samples 650 to 1200: one construction at two windows",
        loc="left",
    )
    top.grid(axis="y", alpha=0.5)

    r = c["region_r_peaks"]
    bottom.plot(
        seconds,
        c["ecg_filtered"][START : END + 1],
        color=INK_MUTED,
        linewidth=0.9,
        label="filtered ECG, lead II",
    )
    bottom.scatter(
        to_s(r),
        c["ecg_filtered"][r],
        s=30,
        color=INK,
        marker="^",
        zorder=4,
        label="R-peak",
    )
    for i, (r_peak, peak) in enumerate(
        zip(c["preceding_r"], c["peaks_79"], strict=True)
    ):
        bottom.axvspan(
            to_s(r_peak),
            to_s(peak),
            color=ONLY_79 if not shared_mask[i] else SHARED,
            alpha=0.14,
            linewidth=0,
            label="R-peak to the following object peak" if i == 0 else None,
        )
    bottom.set_ylabel("ECG (filtered)")
    bottom.set_xlabel(f"seconds from sample {START}")
    bottom.grid(axis="y", alpha=0.5)

    # One legend for both panels, below the plot area, so no entry can sit on
    # the data whatever shape the real trace takes.
    handles, labels = [], []
    for axis in (top, bottom):
        axis_handles, axis_labels = axis.get_legend_handles_labels()
        handles += axis_handles
        labels += axis_labels
    fig.tight_layout()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.0),
        ncol=3,
        frameon=False,
    )
    save(fig, "fig1_subject13_construction")
    return True


def figure_lag_histogram(subject: int = 13) -> None:
    """Every W=79 object peak of one record, by its lag after the R-peak.

    One bar per sample. The whole hour is shown, not a region, so that the
    width of the band is the result: the matched peaks, which are breaths,
    and the W=79-only peaks fall in the same few samples. The lag is drawn
    from the committed peak table, so the figure needs no signal data.
    """
    table = pd.read_csv(PEAK_MEASURES / f"bidmc_{subject:02d}_peaks_W79_100.csv")
    lag = table["r_lag"].dropna()
    matched = table["matched"].astype(bool)
    only_79 = lag[~matched.loc[lag.index]].to_numpy()
    shared = lag[matched.loc[lag.index]].to_numpy()
    upper = int(np.ceil(lag.max() / 10) * 10) + 1
    bins = np.arange(0, upper + 1, 1)

    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.grid(axis="y", alpha=0.7)
    ax.set_axisbelow(True)
    ax.hist(
        [shared, only_79],
        bins=bins,
        stacked=True,
        color=[SHARED, ONLY_79],
        label=[
            f"Shared objects (n = {len(shared)})",
            f"W=79-only objects (n = {len(only_79)})",
        ],
        linewidth=0,
    )
    median = float(np.median(lag))
    q1, q3 = np.percentile(lag, [25, 75])
    ax.axvline(median, color=INK, linewidth=0.8, linestyle=":")
    ax.text(
        median + 12,
        ax.get_ylim()[1] * 0.95,
        f"median {median:.0f} samples ({median / FS:.2f} s)\n"
        f"interquartile range {q3 - q1:.0f} samples\n"
        f"n = {len(lag)} peaks over the record",
        fontsize=8,
        color=INK_MUTED,
        va="top",
        ha="left",
    )
    ax.set_xlim(0, upper)
    ax.set_xlabel(
        "Lag from preceding lead-II R-peak to object peak (samples at 125 Hz)"
    )
    ax.set_ylabel("Object peaks")
    seconds = ax.secondary_xaxis("top", functions=(lambda x: x / FS, lambda t: t * FS))
    seconds.set_xlabel("seconds", fontsize=8)
    seconds.tick_params(labelsize=7)
    ax.legend(loc="upper left")
    save(fig, f"fig5_subject{subject}_lag_histogram")


def main() -> None:
    style()
    print("writing figures to", FIGURES.relative_to(ROOT))
    figure_construction()
    figure_phase_concentration()
    figure_rate_against_heart_rate()
    figure_annotation_agreement()
    figure_lag_histogram()


if __name__ == "__main__":
    main()
