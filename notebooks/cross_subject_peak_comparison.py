"""
Run the same three-method peak-count comparison (scipy find_peaks on raw signal,
sign-based state-transition detector on the residual, and the W=100 smoothed
construction's implicit 1-per-cycle count) across multiple BIDMC subjects.

This is exactly the logic from bidmc_visual_demo.ipynb, generalized into a
function over subject_id so it can be looped rather than copy-pasted per subject.
"""

import featuregraph as fg
import pandas as pd
from scipy.signal import find_peaks


def analyze_subject(subject_id: int, smooth_window: int = 100, eps: float = 1e-12) -> pd.DataFrame:
    """
    Returns the per-cycle summary table for one subject, with the same
    columns as the original notebook: peak_count (scipy, raw), 
    peak_count_sig_diff (state-transition, on residual), plus subject_id
    stamped on for later concatenation across subjects.
    """
    df = fg.datasets.bidmc(subject=subject_id).copy()

    # scipy find_peaks on the raw, unsmoothed signal.
    peak_indices, _ = find_peaks(df["respiration"].to_numpy())
    df["scipy_peak"] = False
    df.loc[df.index[peak_indices], "scipy_peak"] = True

    # W=100 smoothed envelope.
    df["respiration_smooth"] = (
        df["respiration"]
        .rolling(smooth_window, min_periods=smooth_window, center=True)
        .median()
        .rolling(smooth_window, min_periods=smooth_window, center=True)
        .mean()
    )

    df["respiration_minus_smoothing"] = df["respiration"] - df["respiration_smooth"]
    df["respiration_change"] = df["respiration_smooth"].diff()
    df["respiration_change_unsmoothed"] = df["respiration_minus_smoothing"].diff()

    df["respiration_smooth_valid"] = (
        df["respiration_smooth"].notna() & df["respiration_change"].notna()
    )
    valid = df["respiration_smooth_valid"]

    df["respiration_rising"] = valid & df["respiration_change"].gt(eps)
    df["respiration_rising_unsmoothed"] = valid & df["respiration_change_unsmoothed"].gt(eps)

    df["enter_respiration_rising"] = False
    df["exit_respiration_rising"] = False
    df.loc[valid, "enter_respiration_rising"] = (
        df.loc[valid, "respiration_rising"].astype(int).diff().eq(1)
    )
    df.loc[valid, "exit_respiration_rising"] = (
        df.loc[valid, "respiration_rising"].astype(int).diff().eq(-1)
    )

    df["exit_respiration_rising_id"] = df["exit_respiration_rising"].astype(int).cumsum()
    df["exit_respiration_rising_sig_diff"] = (
        df["respiration_rising_unsmoothed"].astype(int).diff().eq(-1)
    )

    summary = df.groupby("exit_respiration_rising_id").agg(
        start_time=("exit_respiration_rising", "idxmax"),
        end_time=("exit_respiration_rising", "idxmin"),
        duration=("exit_respiration_rising", lambda x: x.index[-1] - x.index[0]),
        peak_count=("scipy_peak", "sum"),
        peak_count_sig_diff=("exit_respiration_rising_sig_diff", "sum"),
    )
    summary["subject_id"] = subject_id
    return summary


def summarize_across_subjects(subject_ids: list) -> pd.DataFrame:
    """
    Runs analyze_subject over each subject_id, returns one row per subject
    with the three-way comparison: mean peaks/cycle under each method, plus
    the correlation between the two independent unsmoothed methods.

    A subject with too few valid cycles for a meaningful correlation
    (e.g. n < 5) is flagged rather than silently included.
    """
    rows = []
    for sid in subject_ids:
        try:
            s = analyze_subject(sid)
        except Exception as e:
            rows.append({"subject_id": sid, "error": str(e)})
            continue

        n_cycles = len(s)
        row = {
            "subject_id": sid,
            "n_cycles": n_cycles,
            "mean_peak_count_scipy": s["peak_count"].mean(),
            "mean_peak_count_sig_diff": s["peak_count_sig_diff"].mean(),
            # W=100 construction defines exactly 1 peak/cycle by construction --
            # included as a literal column so the three-way table is explicit,
            # not left as a comment the reader has to remember.
            "mean_peak_count_smoothed_w100": 1.0,
        }
        if n_cycles >= 5:
            row["corr_scipy_vs_sig_diff"] = s["peak_count"].corr(s["peak_count_sig_diff"])
        else:
            row["corr_scipy_vs_sig_diff"] = None
            row["note"] = f"only {n_cycles} cycles -- correlation not meaningful"
        rows.append(row)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    # Adjust this list to whichever subjects you want in the paper --
    # a handful spanning different signal characters (e.g. include subject 5,
    # which never converged on a stable period in your database-paper notes,
    # as a deliberate edge case worth reporting even if it behaves oddly here).
    subject_ids = [1, 2, 3, 5, 10, 19]
    result = summarize_across_subjects(subject_ids)
    print(result.to_string(index=False))
    result.to_csv("peak_count_cross_subject_summary.csv", index=False)
