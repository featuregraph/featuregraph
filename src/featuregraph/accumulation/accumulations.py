import numpy as np

def add_accumulation_signal(
    df,
    signals,
    thresholds,
    group=None,
):
    df = df.copy()

    for signal in signals:
        threshold = (
            thresholds.get(signal)
            if isinstance(thresholds, dict)
            else thresholds
        )

        threshold_col = f"{signal}_accumulation_threshold"
        contribution_col = f"{signal}_accumulation_contribution"
        accumulation_col = f"{signal}_accumulation"

        if threshold == "group_min":
            if group is None:
                raise ValueError(
                    "group is required when threshold='group_min'"
                )

            df[threshold_col] = (
                df.groupby(group, sort=False)[signal]
                  .transform("min")
            )

        elif threshold == "group_mean":
            if group is None:
                raise ValueError(
                    "group is required when threshold='group_mean'"
                )

            df[threshold_col] = (
                df.groupby(group, sort=False)[signal]
                  .transform("mean")
            )

        elif isinstance(threshold, str):
            df[threshold_col] = df[threshold]

        else:
            df[threshold_col] = threshold

        df[contribution_col] = (
            df[signal] - df[threshold_col]
        )

        if group is None:
            df[accumulation_col] = (
                df[contribution_col].cumsum()
            )
        else:
            df[accumulation_col] = (
                df.groupby(group, sort=False)[contribution_col]
                  .cumsum()
            )

    return df

def add_accumulation_id(df, signals):
    """
    Treat each detected wave as one bounded accumulation episode.
    """
    df = df.copy()

    for signal in signals:
        df[f"{signal}_accumulation_id"] = df[f"{signal}_wave_id"]

    return df


def add_accumulation_primitives(df, signals):
    """
    Calculate row-level quantities used to describe each accumulation.
    """
    df = df.copy()

    for signal in signals:
        group = f"{signal}_accumulation_id"

        baseline_col = f"{signal}_baseline"
        contribution_col = f"{signal}_above_baseline"
        cumulative_col = f"{signal}_cumulative_accumulation"
        active_col = f"{signal}_is_accumulating"
        index_col = f"{signal}_accumulation_index"

        df[baseline_col] = (
            df.groupby(group)[signal]
            .transform("min")
        )

        df[contribution_col] = (
            df[signal] - df[baseline_col]
        )

        df[cumulative_col] = (
            df.groupby(group)[contribution_col]
            .cumsum()
        )

        df[active_col] = (
            df[contribution_col] > 0
        )

        df[index_col] = (
            df.groupby(group)
            .cumcount()
        )

    return df

def add_accumulation_features(df, signals):
    """
    Calculate peak-relative and distributional accumulation features.
    """
    df = df.copy()

    for signal in signals:
        group = f"{signal}_accumulation_id"

        contribution_col = f"{signal}_above_baseline"
        cumulative_col = f"{signal}_cumulative_accumulation"
        index_col = f"{signal}_accumulation_index"
        peak_event_col = f"exit_{signal}_rising"

        before_peak_col = f"{signal}_before_peak"
        after_peak_col = f"{signal}_after_peak"
        before_contribution_col = f"{signal}_accumulation_before_peak"
        after_contribution_col = f"{signal}_accumulation_from_peak"
        total_col = f"{signal}_total_auc"
        half_col = f"{signal}_half_auc"
        reached_half_col = f"{signal}_reached_half_auc"
        half_time_col = f"{signal}_half_accumulation_time"
        weighted_col = f"{signal}_weighted_accumulation"

        peak_count = (
            df.groupby(group)[peak_event_col]
            .cumsum()
        )

        df[before_peak_col] = peak_count == 0
        df[after_peak_col] = peak_count > 0

        df[before_contribution_col] = np.where(
            df[before_peak_col],
            df[contribution_col],
            0,
        )

        df[after_contribution_col] = np.where(
            df[after_peak_col],
            df[contribution_col],
            0,
        )

        df[f"{signal}_auc_at_peak"] = np.where(
            df[peak_event_col],
            df[cumulative_col],
            0,
        )

        df[weighted_col] = (
            df[index_col] * df[contribution_col]
        )

        df[total_col] = (
            df.groupby(group)[contribution_col]
            .transform("sum")
        )

        df[half_col] = df[total_col] / 2

        df[reached_half_col] = (
            df[cumulative_col] >= df[half_col]
        )

        half_accumulation_time = (
            df.loc[df[reached_half_col]]
            .groupby(group)[index_col]
            .first()
        )

        df[half_time_col] = (
            df[group].map(half_accumulation_time)
        )

    return df

def get_accumulation_summary(df, signal):
    group = f"{signal}_accumulation_id"

    summarydf = (
        df.groupby(group)
        .agg(
            start_index=(
                f"{signal}_accumulation_index",
                "min",
            ),
            end_index=(
                f"{signal}_accumulation_index",
                "max",
            ),
            duration=(
                f"{signal}_accumulation_index",
                "count",
            ),
            baseline=(
                f"{signal}_baseline",
                "first",
            ),
            total_auc=(
                f"{signal}_above_baseline",
                "sum",
            ),
            accumulation_before_peak=(
                f"{signal}_accumulation_before_peak",
                "sum",
            ),
            accumulation_from_peak=(
                f"{signal}_accumulation_from_peak",
                "sum",
            ),
            auc_at_peak=(
                f"{signal}_auc_at_peak",
                "max",
            ),
            first_moment=(
                f"{signal}_weighted_accumulation",
                "sum",
            ),
            half_accumulation_time=(
                f"{signal}_half_accumulation_time",
                "first",
            ),
        )
        .reset_index()
        .rename(columns={group: "accumulation_id"})
    )

    summarydf["accumulation_rate"] = (
        summarydf["total_auc"] / summarydf["duration"]
    )

    denominator = (
        summarydf["accumulation_before_peak"]
        + summarydf["accumulation_from_peak"]
    )

    summarydf["accumulation_symmetry"] = (
        1
        - (
            summarydf["accumulation_before_peak"]
            - summarydf["accumulation_from_peak"]
        ).abs()
        / denominator
    ).where(denominator > 0)

    summarydf["centroid_time"] = (
        summarydf["first_moment"]
        / summarydf["total_auc"]
    ).where(summarydf["total_auc"] > 0)

    return summarydf[
        [
            "accumulation_id",
            "start_index",
            "end_index",
            "duration",
            "baseline",
            "total_auc",
            "auc_at_peak",
            "accumulation_before_peak",
            "accumulation_from_peak",
            "accumulation_rate",
            "accumulation_symmetry",
            "centroid_time",
            "half_accumulation_time",
        ]
    ]