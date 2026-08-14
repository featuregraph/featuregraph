"""Reproduce the blinded LLM's documented BIDMC detector without an LLM."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import butter, find_peaks, sosfiltfilt


SAMPLING_RATE = 125


def assemble_objects(
    signal: np.ndarray,
    peaks: np.ndarray,
    troughs: np.ndarray,
    *,
    sampling_rate: int = SAMPLING_RATE,
) -> pd.DataFrame:
    """Build trough–peak–trough objects from documented LLM boundaries."""
    rows: list[dict[str, object]] = []

    for start, end in zip(troughs[:-1], troughs[1:]):
        candidates = peaks[(peaks > start) & (peaks < end)]
        if len(candidates) != 1:
            continue
        peak = int(candidates[0])
        preceding = peaks[peaks < peak]
        rows.append(
            object_row(
                len(rows) + 1,
                signal,
                int(start),
                peak,
                int(end),
                is_complete=True,
                preceding_peak=(int(preceding[-1]) if len(preceding) else None),
                sampling_rate=sampling_rate,
            )
        )

    if len(troughs):
        start = int(troughs[-1])
        trailing_peaks = peaks[peaks > start]
        if len(trailing_peaks):
            peak = int(trailing_peaks[0])
            preceding = peaks[peaks < peak]
            rows.append(
                object_row(
                    len(rows) + 1,
                    signal,
                    start,
                    peak,
                    len(signal) - 1,
                    is_complete=False,
                    preceding_peak=(
                        int(preceding[-1]) if len(preceding) else None
                    ),
                    sampling_rate=sampling_rate,
                )
            )

    return pd.DataFrame.from_records(rows)


def object_row(
    object_id: int,
    signal: np.ndarray,
    start: int,
    peak: int,
    end: int,
    *,
    is_complete: bool,
    preceding_peak: int | None,
    sampling_rate: int,
) -> dict[str, object]:
    """Calculate the frozen output contract for one object."""
    rise_duration = peak - start
    fall_duration = end - peak
    duration = rise_duration + fall_duration
    interval = signal[start:end + 1]
    return {
        "llm_object_id": object_id,
        "start_index": start,
        "peak_index": peak,
        "end_index": end,
        "is_complete": is_complete,
        "period_seconds": (
            (peak - preceding_peak) / sampling_rate
            if preceding_peak is not None
            else np.nan
        ),
        "full_excursion": interval.max() - interval.min(),
        "temporal_symmetry": (
            1 - abs(rise_duration - fall_duration) / duration
        ),
    }


def reproduce(raw: pd.DataFrame) -> pd.DataFrame:
    """Apply the exact method documented by the blinded LLM run."""
    signal = raw["respiration"].to_numpy()
    sos = butter(
        4,
        0.8,
        btype="lowpass",
        fs=SAMPLING_RATE,
        output="sos",
    )
    filtered = sosfiltfilt(sos, signal)
    peaks, _ = find_peaks(
        filtered,
        distance=188,
        prominence=0.08,
    )
    troughs, _ = find_peaks(
        -filtered,
        distance=188,
        prominence=0.08,
    )
    return assemble_objects(signal, peaks, troughs)


if __name__ == "__main__":
    directory = Path(__file__).parent
    raw_table = pd.read_csv(
        directory / "generated" / "raw_respiration_subject_01.csv"
    )
    reproduced = reproduce(raw_table)
    reproduced.to_csv(
        directory / "generated" / "reproduced_llm_objects_subject_01.csv",
        index=False,
    )
    print(f"Reproduced {len(reproduced)} LLM-defined objects.")
