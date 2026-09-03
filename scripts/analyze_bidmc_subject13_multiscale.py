"""Audit cardiac and annotation relationships in one scale-dependent BIDMC region."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import butter, find_peaks, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "notebooks" / ".bidmc_notebook_cache"
OUTPUT = ROOT / "artifacts" / "studies" / "bidmc_subject13_multiscale"
FS = 125
START = 650
END = 1200


def envelope(raw: pd.Series, window: int) -> pd.Series:
    return (
        raw.rolling(window, min_periods=window)
        .max()
        .rolling(window, min_periods=window)
        .mean()
        .shift(-window)
    )


def cache_available(cache: Path = CACHE) -> bool:
    """Whether the two subject 13 source files this audit needs are present."""
    return all(
        (cache / f"bidmc_13_{kind}.csv").exists() for kind in ("Signals", "Breaths")
    )


def region_construction(cache: Path = CACHE) -> dict:
    """Everything the audit and the paper's Figure 1 draw, from the cached files.

    The object peaks are the ones the frozen construction recovered in this
    region and are stated, not re-detected, so the figure shows the published
    objects rather than a fresh detection.
    """
    signals = pd.read_csv(cache / "bidmc_13_Signals.csv")
    signals.columns = signals.columns.str.strip()
    breaths = pd.read_csv(cache / "bidmc_13_Breaths.csv")
    breaths.columns = breaths.columns.str.strip()

    raw = signals["RESP"].astype(float)
    smooth_79 = envelope(raw, 79)
    smooth_100 = envelope(raw, 100)

    ecg = signals["II"].astype(float).to_numpy()
    ecg_filter = butter(4, [5, 20], btype="bandpass", fs=FS, output="sos")
    ecg_filtered = sosfiltfilt(ecg_filter, ecg)
    r_peaks, _ = find_peaks(
        ecg_filtered,
        distance=63,
        prominence=0.5 * np.std(ecg_filtered),
    )
    region_r_peaks = r_peaks[(r_peaks >= START) & (r_peaks <= END)]

    # Exact object peaks recovered by the frozen construction in this region.
    peaks_79 = np.array([731, 848, 951, 1069])
    peaks_100 = np.array([848])
    preceding_r = np.array(
        [region_r_peaks[region_r_peaks <= peak][-1] for peak in peaks_79]
    )
    cardiac_lag_samples = peaks_79 - preceding_r

    annotation_1 = (
        breaths["breaths ann1 [signal sample no]"].dropna().astype(int).to_numpy()
    )
    annotation_2 = (
        breaths["breaths ann2 [signal sample no]"].dropna().astype(int).to_numpy()
    )
    annotation_1 = annotation_1[(annotation_1 >= START) & (annotation_1 <= END)]
    annotation_2 = annotation_2[(annotation_2 >= START) & (annotation_2 <= END)]
    return {
        "raw": raw,
        "smooth_79": smooth_79,
        "smooth_100": smooth_100,
        "ecg_filtered": ecg_filtered,
        "region_r_peaks": region_r_peaks,
        "peaks_79": peaks_79,
        "peaks_100": peaks_100,
        "preceding_r": preceding_r,
        "cardiac_lag_samples": cardiac_lag_samples,
        "annotation_1": annotation_1,
        "annotation_2": annotation_2,
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    c = region_construction()
    raw, smooth_79, smooth_100 = c["raw"], c["smooth_79"], c["smooth_100"]
    ecg_filtered, region_r_peaks = c["ecg_filtered"], c["region_r_peaks"]
    peaks_79, peaks_100, preceding_r = c["peaks_79"], c["peaks_100"], c["preceding_r"]
    cardiac_lag_samples = c["cardiac_lag_samples"]
    annotation_1, annotation_2 = c["annotation_1"], c["annotation_2"]

    peak_table = pd.DataFrame(
        {
            "featuregraph_peak_79": peaks_79,
            "preceding_ecg_r_peak": preceding_r,
            "lag_samples": cardiac_lag_samples,
            "lag_seconds": cardiac_lag_samples / FS,
            "also_peak_at_window_100": np.isin(peaks_79, peaks_100),
        }
    )
    peak_table.to_csv(OUTPUT / "peak_ecg_relationship.csv", index=False)

    region = np.arange(START, END + 1)
    fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=True)
    axes[0].plot(
        region, raw.loc[START:END], color="0.55", linewidth=1.2, label="raw RESP"
    )
    axes[0].plot(region, smooth_79.loc[START:END], linewidth=2, label="envelope W=79")
    axes[0].plot(region, smooth_100.loc[START:END], linewidth=2, label="envelope W=100")
    axes[0].scatter(
        peaks_79, smooth_79.loc[peaks_79], marker="o", s=55, label="W=79 peaks"
    )
    axes[0].scatter(
        peaks_100, smooth_100.loc[peaks_100], marker="X", s=85, label="W=100 peak"
    )
    for index, value in enumerate(annotation_1):
        axes[0].axvline(
            value,
            color="tab:green",
            linestyle="--",
            alpha=0.8,
            label="annotator 1" if index == 0 else None,
        )
    for index, value in enumerate(annotation_2):
        axes[0].axvline(
            value,
            color="tab:purple",
            linestyle=":",
            alpha=0.9,
            label="annotator 2" if index == 0 else None,
        )
    axes[0].set_ylabel("RESP")
    axes[0].set_title("Subject 13: scale-dependent respiratory-object construction")
    axes[0].legend(ncol=4, fontsize=9)

    axes[1].plot(region, ecg_filtered[START : END + 1], color="tab:red", linewidth=1)
    axes[1].scatter(
        region_r_peaks,
        ecg_filtered[region_r_peaks],
        color="black",
        marker="^",
        s=45,
        label="detected ECG R-peaks",
    )
    for respiratory_peak, r_peak in zip(peaks_79, preceding_r, strict=True):
        axes[1].axvspan(r_peak, respiratory_peak, color="tab:orange", alpha=0.16)
    axes[1].set_ylabel("filtered ECG II")
    axes[1].legend()

    rr = np.diff(region_r_peaks) / FS
    axes[2].plot(region_r_peaks[1:], 60 / rr, "o-", label="ECG-derived heart rate")
    respiratory_rate = 60 / (np.diff(peaks_79) / FS)
    axes[2].plot(peaks_79[1:], respiratory_rate, "s-", label="W=79 interpeak rate")
    axes[2].set_ylabel("events/min")
    axes[2].set_xlabel("sample index")
    axes[2].legend()
    axes[2].grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT / "subject13_samples650_1200_multiscale.png", dpi=180)
    plt.close(fig)

    heart_rate = float(np.median(60 / rr))
    mean_lag = cardiac_lag_samples.mean()
    sd_lag = cardiac_lag_samples.std(ddof=1)
    report = f"""# Subject 13 multiscale audit: samples {START}-{END}

- Sampling rate: {FS} Hz
- W=79 peaks: {peaks_79.tolist()}
- W=100 peaks: {peaks_100.tolist()}
- ECG R-peaks: {region_r_peaks.tolist()}
- W=79 peak lags after preceding ECG R-peaks: {cardiac_lag_samples.tolist()} samples
- Mean lag: {mean_lag:.1f} samples ({mean_lag / FS:.3f} s)
- Lag standard deviation: {sd_lag:.1f} samples ({sd_lag / FS:.3f} s)
- Median ECG-derived heart rate: {heart_rate:.1f} beats/min
- W=79 interpeak rates: {np.round(respiratory_rate, 1).tolist()} events/min
- Annotator 1 events: {annotation_1.tolist()}
- Annotator 2 events: {annotation_2.tolist()}

The W=79 peaks are phase-consistent with the ECG in this interval and recur at a
heart-rate-like frequency. This supports a cardiogenic-component hypothesis but does
not establish it causally. The two breath annotation series disagree in this region,
so annotation proximity alone does not resolve the physiological identity of every
smaller oscillation.
"""
    (OUTPUT / "report.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
