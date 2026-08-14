"""Run the declared BIDMC hysteresis ablation.

The entry threshold is calibrated once from subject 1. Exit thresholds are
expressed as frozen ratios of that entry threshold; no subject-specific
threshold is selected from the results.
"""

from pathlib import Path

import featuregraph as fg
import pandas as pd


REFERENCE_SUBJECT = 1
EVALUATION_SUBJECT = 5
SAMPLING_RATE = 125
DIFF_LAG = 45
REFERENCE_EPS = 0.15
MAX_STATE_GAP = 7
EXIT_RATIOS = (1.0, 0.75, 0.5, 0.25, 0.0)
MATCH_TOLERANCE = round(0.5 * SAMPLING_RATE)


def difference_mad(signal: pd.Series) -> float:
    difference = signal.diff(DIFF_LAG)
    median = difference.median()
    return (difference - median).abs().median()


def match_nearest(detected, reference, tolerance):
    candidates = sorted(
        (abs(left - right), left, right)
        for left in detected
        for right in reference
        if abs(left - right) <= tolerance
    )
    used_detected = set()
    used_reference = set()
    matches = []

    for distance, left, right in candidates:
        if left not in used_detected and right not in used_reference:
            matches.append((left, right, distance))
            used_detected.add(left)
            used_reference.add(right)

    return matches, used_detected, used_reference


def prepare_subject(subject: int) -> tuple[pd.DataFrame, float]:
    observations = fg.datasets.bidmc(subject=subject)
    scale = difference_mad(observations["respiration"])
    if pd.isna(scale) or scale <= 0:
        raise ValueError(f"Subject {subject} difference MAD must be positive.")

    observations["respiration_scaled"] = (
        observations["respiration"] / scale
    )
    return observations, scale


def construct(observations, entry_eps, exit_eps):
    behavior = fg.oscillation.Oscillation(
        signals="respiration_scaled",
        group="subject",
        smooth_signal=False,
        diff_lag=DIFF_LAG,
        eps=entry_eps,
        exit_eps=exit_eps,
        max_state_gap=MAX_STATE_GAP,
    )
    features = behavior.fit_transform(observations)
    objects = behavior.summarize(
        features,
        signal="respiration_scaled",
        include_partial=True,
    ).table
    return features, objects


def main() -> None:
    reference, reference_scale = prepare_subject(REFERENCE_SUBJECT)
    entry_eps = REFERENCE_EPS / reference_scale

    # An explicitly equal exit threshold must preserve the pre-hysteresis
    # construction exactly on the calibration record.
    original = fg.oscillation.Oscillation(
        signals="respiration_scaled",
        group="subject",
        smooth_signal=False,
        diff_lag=DIFF_LAG,
        eps=entry_eps,
        max_state_gap=MAX_STATE_GAP,
    ).fit_transform(reference)
    equal_threshold, _ = construct(reference, entry_eps, entry_eps)
    pd.testing.assert_frame_equal(original, equal_threshold)

    observations, _ = prepare_subject(EVALUATION_SUBJECT)
    annotations = fg.datasets.bidmc_breaths(EVALUATION_SUBJECT)
    rows = []

    for exit_ratio in EXIT_RATIOS:
        exit_eps = entry_eps * exit_ratio
        features, objects = construct(
            observations,
            entry_eps,
            exit_eps,
        )
        complete = objects.loc[objects["is_complete"]]
        detected = features.index[
            features["respiration_scaled_peak"]
        ].tolist()

        row = {
            "subject": EVALUATION_SUBJECT,
            "entry_eps": entry_eps,
            "exit_ratio": exit_ratio,
            "exit_eps": exit_eps,
            "candidate_peaks": len(detected),
            "complete_objects": len(complete),
            "partial_objects": len(objects) - len(complete),
            "mean_period_seconds": (
                complete["period"].mean() / SAMPLING_RATE
            ),
        }

        for column, label in [
            ("breaths ann1 [signal sample no]", "ann1"),
            ("breaths ann2 [signal sample no]", "ann2"),
        ]:
            reference_peaks = (
                annotations[column].dropna().astype(int).tolist()
            )
            matches, used_detected, used_reference = match_nearest(
                detected,
                reference_peaks,
                MATCH_TOLERANCE,
            )
            distances = pd.Series(
                [match[2] for match in matches],
                dtype=float,
            )
            row[f"{label}_matched"] = len(matches)
            row[f"{label}_extra_detected"] = (
                len(detected) - len(used_detected)
            )
            row[f"{label}_missed_reference"] = (
                len(reference_peaks) - len(used_reference)
            )
            row[f"{label}_median_abs_error_samples"] = distances.median()

        rows.append(row)

    result = pd.DataFrame(rows)
    output = Path(__file__).parent / "generated" / "hysteresis_subject_05.csv"
    output.parent.mkdir(exist_ok=True)
    result.to_csv(output, index=False)
    print(result.to_string(index=False))
    print(f"\nWrote {output}")


if __name__ == "__main__":
    main()
