"""Draw the compiler's view of one BIDMC region, at any windows, in one command.

For a subject and a sample range, this compiles the published v2 respiration
contract at each requested window against the raw record, then shows, sharing
one sample axis:

- the raw respiration with each window's envelope and the object peaks it
  recovers (the last rising sample of every rising occurrence);
- one state strip per window: rising, falling and inactive as coloured spans,
  so the partition itself is visible, not only its peaks;
- the filtered ECG with its R-peaks, and the annotators' breath marks.

It also prints the occurrences that touch the region for each window, with
their rise/fall asymmetry, so the shape measures sit beside the picture.

With ``--peaks`` it measures every object peak of the finest window over the
whole record, not only the region: whether a peak of the coarsest window lies
within the paper's matching tolerance, the lag from the preceding R-peak, the
cardiac phase, and the breath phase taken from the coarsest window's own
peaks. The table goes to a csv beside the image; the unmatched peaks inside
the region are printed and ringed on the plot. Those are the objects the
paper calls W=79-only, and the table is what a lag-against-breath-phase plot
is drawn from.

Nothing here re-detects anything. The states come from ``compile_states``
under ``artifacts/contracts/bidmc_respiration_states_v2.json`` with only the
window changed, which is the construction the paper reports.

Usage::

    python -m scripts.inspect_bidmc_region --subject 13 --start 650 --end 1200
    python -m scripts.inspect_bidmc_region --subject 4 --start 0 --end 3000 \\
        --window 79 100 120
    python -m scripts.inspect_bidmc_region --subject 13 --start 0 --end 1200 --peaks

Needs the subject's Signals and Breaths files under
``notebooks/.bidmc_notebook_cache``; they are fetched from PhysioNet on first
use. Output goes to ``outputs/inspect/`` unless ``--output`` says otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.request import urlretrieve

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import featuregraph as fg  # noqa: E402
from scripts.run_bidmc_multiscale_heldout import ecg_events  # noqa: E402

CACHE = ROOT / "notebooks" / ".bidmc_notebook_cache"
CONTRACT = ROOT / "artifacts" / "contracts" / "bidmc_respiration_states_v2.json"
OUTPUT = ROOT / "outputs" / "inspect"
BASE = "https://physionet.org/files/bidmc/1.0.0/bidmc_csv"
FS = 125
DOWNLOAD_ATTEMPTS = 4
# A fine-window peak counts as matched when a coarse-window peak lies within
# this many samples of it, the tolerance the multiscale study uses.
MATCH_TOLERANCE = 63

# The paper's palette for the first two windows; further windows take
# neutral tones so the two the paper discusses stay recognisable.
WINDOW_COLOURS = ["#eb6834", "#2a78d6", "#6b6b6b", "#a0a0a0"]
STATE_COLOURS = {"rising": "#f5c6ad", "falling": "#bcd4f2", "inactive": "#dddddd"}
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_MUTED = "#52514e"


def fetch(subject: int, kind: str, cache: Path = CACHE) -> pd.DataFrame:
    """Read one BIDMC csv from the cache, fetching it first if absent."""
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"bidmc_{subject:02d}_{kind}.csv"
    last_error: Exception | None = None
    for attempt in range(DOWNLOAD_ATTEMPTS):
        try:
            if not path.exists():
                urlretrieve(f"{BASE}/{path.name}", path)
            frame = pd.read_csv(path)
            frame.columns = frame.columns.str.strip()
            return frame
        except (OSError, pd.errors.ParserError) as error:
            last_error = error
            path.unlink(missing_ok=True)
            if attempt < DOWNLOAD_ATTEMPTS - 1:
                time.sleep(2**attempt)
    raise RuntimeError(f"Could not fetch {path.name}") from last_error


def compile_window(raw: pd.Series, subject: int, window: int) -> pd.DataFrame:
    """The published construction at one window, from the raw column."""
    contract = json.loads(CONTRACT.read_text())
    contract["parameters"]["smooth_window"] = int(window)
    observations = pd.DataFrame({"subject_id": subject, "respiration": raw.to_numpy()})
    return fg.compile_states(observations, contract).observations


def region_occurrences(compiled: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    """Occurrences overlapping the region, with the asymmetry of each rise."""
    table = fg.shape.occurrences(compiled)
    asymmetry = fg.shape.rise_fall_asymmetry(compiled)
    table = table.merge(
        asymmetry[["rising_occurrence_id", "paired", "asymmetry"]],
        left_on="state_occurrence_id",
        right_on="rising_occurrence_id",
        how="left",
    ).drop(columns="rising_occurrence_id")
    touching = (table["end_position"] >= start) & (table["start_position"] <= end)
    return table.loc[touching].reset_index(drop=True)


def object_peaks(compiled: pd.DataFrame) -> np.ndarray:
    """Sample positions of the exit-rising event, one per rising occurrence."""
    return np.flatnonzero(compiled["exit_respiration_rising"].to_numpy())


def _cycle_phase(positions: np.ndarray, marks: np.ndarray) -> np.ndarray:
    """Position of each sample inside the cycle of marks that brackets it.

    Zero at the preceding mark, approaching one at the next; NaN where no
    mark precedes or none follows. With R-peaks as marks this is the cardiac
    phase the multiscale study reports; with the coarse window's object peaks
    it is a breath phase.
    """
    marks = np.asarray(marks, dtype=int)
    positions = np.asarray(positions, dtype=int)
    phase = np.full(len(positions), np.nan)
    if len(marks) < 2:
        return phase
    after = np.searchsorted(marks, positions, side="right")
    inside = (after >= 1) & (after < len(marks))
    start = marks[after[inside] - 1]
    end = marks[after[inside]]
    phase[inside] = (positions[inside] - start) / (end - start)
    return phase


def peak_measures(
    fine: pd.DataFrame,
    coarse: pd.DataFrame,
    r_peaks: np.ndarray,
    *,
    tolerance: int = MATCH_TOLERANCE,
) -> pd.DataFrame:
    """One row per object peak of the fine window, over the whole record.

    ``matched`` says whether a coarse-window peak lies within ``tolerance``
    samples; the unmatched rows are the fine-window-only objects. ``r_lag``
    is the distance in samples from the preceding R-peak, ``cardiac_phase``
    that lag as a fraction of the RR interval, and ``breath_phase`` the
    position between the bracketing coarse-window peaks.
    """
    fine_peaks = object_peaks(fine)
    coarse_peaks = object_peaks(coarse)
    r_peaks = np.asarray(r_peaks, dtype=int)

    if len(coarse_peaks):
        slot = np.searchsorted(coarse_peaks, fine_peaks)
        before = coarse_peaks[np.clip(slot - 1, 0, len(coarse_peaks) - 1)]
        after = coarse_peaks[np.clip(slot, 0, len(coarse_peaks) - 1)]
        nearest = np.minimum(np.abs(fine_peaks - before), np.abs(fine_peaks - after))
    else:
        nearest = np.full(len(fine_peaks), np.iinfo(int).max)

    preceding = np.searchsorted(r_peaks, fine_peaks, side="right") - 1
    r_lag = np.full(len(fine_peaks), np.nan)
    has_r = preceding >= 0
    r_lag[has_r] = fine_peaks[has_r] - r_peaks[preceding[has_r]]

    return pd.DataFrame(
        {
            "position": fine_peaks,
            "nearest_coarse_peak": nearest,
            "matched": nearest <= tolerance,
            "r_lag": r_lag,
            "cardiac_phase": _cycle_phase(fine_peaks, r_peaks),
            "breath_phase": _cycle_phase(fine_peaks, coarse_peaks),
        }
    )


def phase_resultant(phase: pd.Series | np.ndarray) -> float:
    """Length of the mean phase vector, NaN below five phases as in the study."""
    values = np.asarray(phase, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) < 5:
        return float("nan")
    return float(np.abs(np.mean(np.exp(2j * np.pi * values))))


def draw(
    subject: int,
    start: int,
    end: int,
    windows: list[int],
    *,
    cache: Path = CACHE,
    output: Path = OUTPUT,
    highlight: np.ndarray | None = None,
) -> tuple[Path, dict[int, pd.DataFrame]]:
    """Draw the region; ``highlight`` rings those sample positions on the raw."""
    signals = fetch(subject, "Signals", cache)
    breaths = fetch(subject, "Breaths", cache)
    raw = signals["RESP"].astype(float)
    end = min(end, len(raw) - 1)
    region = np.arange(start, end + 1)

    compiled = {w: compile_window(raw, subject, w) for w in windows}
    tables = {w: region_occurrences(compiled[w], start, end) for w in windows}

    r_peaks = ecg_events(signals["II"].astype(float).to_numpy())
    r_peaks = r_peaks[(r_peaks >= start) & (r_peaks <= end)]
    lead_ii = signals["II"].astype(float).to_numpy()
    marks = {}
    for column, name in (
        ("breaths ann1 [signal sample no]", "annotator 1"),
        ("breaths ann2 [signal sample no]", "annotator 2"),
    ):
        values = breaths[column].dropna().astype(int).to_numpy()
        marks[name] = values[(values >= start) & (values <= end)]

    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.family": "DejaVu Sans",
            "legend.frameon": False,
            "legend.fontsize": 8,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
        }
    )
    rows = 2 + len(windows)
    fig, axes = plt.subplots(
        rows,
        1,
        figsize=(12, 2.6 + 0.9 * len(windows) + 2.4),
        sharex=True,
        height_ratios=[3, *([0.6] * len(windows)), 2],
    )
    top, strips, bottom = axes[0], axes[1:-1], axes[-1]

    top.plot(
        region, raw.loc[start:end], color="0.72", linewidth=1.0, label="raw respiration"
    )
    for i, w in enumerate(windows):
        colour = WINDOW_COLOURS[i % len(WINDOW_COLOURS)]
        smooth = compiled[w]["respiration_smooth"]
        top.plot(
            region,
            smooth.loc[start:end],
            color=colour,
            linewidth=1.5,
            label=f"envelope, W = {w}",
        )
        peaks = object_peaks(compiled[w])
        peaks = peaks[(peaks >= start) & (peaks <= end)]
        top.scatter(
            peaks,
            smooth.loc[peaks],
            s=40,
            color=colour,
            marker="o" if i else "s",
            zorder=4,
            edgecolor=SURFACE,
            linewidth=1.0,
            label=f"object peaks, W = {w}",
        )
    if highlight is not None:
        highlight = np.asarray(highlight, dtype=int)
        highlight = highlight[(highlight >= start) & (highlight <= end)]
        if len(highlight):
            top.scatter(
                highlight,
                raw.loc[highlight],
                s=140,
                facecolor="none",
                edgecolor=INK,
                linewidth=1.2,
                zorder=5,
                label=f"W = {min(windows)} only",
            )
    y_top = top.get_ylim()[1]
    for (name, values), style_ in zip(marks.items(), ("-", (0, (2, 2))), strict=True):
        for j, value in enumerate(values):
            top.plot(
                [value, value],
                [y_top * 0.92, y_top],
                color=INK_MUTED,
                linestyle=style_,
                linewidth=1.3,
                label=f"{name} breath mark" if j == 0 else None,
            )
    top.set_ylabel("respiration")
    top.set_title(
        f"Subject {subject}, samples {start} to {end}", loc="left", fontsize=10
    )
    top.legend(ncol=4, loc="upper left", bbox_to_anchor=(0, -0.02))

    from matplotlib.patches import Patch

    strips[0].legend(
        handles=[Patch(color=c, label=name) for name, c in STATE_COLOURS.items()],
        ncol=3,
        loc="lower left",
        bbox_to_anchor=(0, 1.0),
    )
    for strip, w in zip(strips, windows, strict=True):
        states = compiled[w]["state"]
        for _, row in fg.shape.occurrences(compiled[w]).iterrows():
            s0, s1 = row["start_position"], row["end_position"]
            if s1 < start or s0 > end:
                continue
            strip.axvspan(
                max(s0, start),
                min(s1, end) + 1,
                color=STATE_COLOURS[row["state"]],
                linewidth=0,
            )
        strip.set_yticks([])
        strip.set_ylabel(f"W={w}", rotation=0, ha="right", va="center")
        strip.set_ylim(0, 1)
        del states

    bottom.plot(
        region,
        lead_ii[start : end + 1],
        color=INK_MUTED,
        linewidth=0.8,
        label="ECG lead II",
    )
    bottom.scatter(
        r_peaks,
        lead_ii[r_peaks],
        s=26,
        color=INK,
        marker="^",
        zorder=4,
        label="R-peak",
    )
    bottom.set_ylabel("ECG")
    bottom.set_xlabel("sample index")
    bottom.legend(ncol=2, loc="upper left", bbox_to_anchor=(0, -0.25))

    fig.align_ylabels()
    fig.tight_layout()
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output / f"bidmc_{subject:02d}_{start}_{end}_W{'_'.join(map(str, windows))}.png"
    )
    fig.savefig(path, dpi=160, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)
    return path, tables


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--subject", type=int, required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=3000)
    parser.add_argument("--window", type=int, nargs="+", default=[79, 100])
    parser.add_argument("--cache", type=Path, default=CACHE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--peaks",
        action="store_true",
        help="measure every peak of the finest window against the coarsest, "
        "over the whole record; write the table and ring the unmatched peaks",
    )
    args = parser.parse_args(argv)
    if args.peaks and len(set(args.window)) < 2:
        parser.error("--peaks needs two different windows")

    measures = None
    if args.peaks:
        signals = fetch(args.subject, "Signals", args.cache)
        raw = signals["RESP"].astype(float)
        fine_w, coarse_w = min(args.window), max(args.window)
        measures = peak_measures(
            compile_window(raw, args.subject, fine_w),
            compile_window(raw, args.subject, coarse_w),
            ecg_events(signals["II"].astype(float).to_numpy()),
        )
    unmatched = (
        None
        if measures is None
        else measures.loc[~measures["matched"], "position"].to_numpy()
    )

    path, tables = draw(
        args.subject,
        args.start,
        args.end,
        args.window,
        cache=args.cache,
        output=args.output,
        highlight=unmatched,
    )
    pd.set_option("display.width", 160)
    for w, table in tables.items():
        rising = table[table["state"] == "rising"]
        summary = f"{len(table)} occurrences touch the region, {len(rising)} rising"
        print(f"\nW = {w}: {summary}")
        print(table.to_string(index=False))

    if measures is not None:
        table_path = path.with_name(
            f"bidmc_{args.subject:02d}_peaks_W{fine_w}_{coarse_w}.csv"
        )
        measures.to_csv(table_path, index=False)
        only = measures[~measures["matched"]]
        in_region = only[
            (only["position"] >= args.start) & (only["position"] <= args.end)
        ]
        print(
            f"\nW = {fine_w} peaks over the record: {len(measures)}, "
            f"of which {len(only)} have no W = {coarse_w} peak within "
            f"{MATCH_TOLERANCE} samples"
        )
        matched = measures.loc[measures["matched"], "cardiac_phase"]
        print(
            "cardiac phase resultant: "
            f"unmatched {phase_resultant(only['cardiac_phase']):.3f}, "
            f"matched {phase_resultant(matched):.3f}"
        )
        print(f"unmatched W = {fine_w} peaks in the region: {len(in_region)}")
        if len(in_region):
            print(in_region.to_string(index=False))
        if table_path.is_relative_to(ROOT):
            table_path = table_path.relative_to(ROOT)
        print(f"wrote {table_path}")

    print(f"\nwrote {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
