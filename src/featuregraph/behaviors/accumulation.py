from collections.abc import Mapping
from numbers import Real

import numpy as np
import pandas as pd

from featuregraph.behaviors.base import Behavior, Group, Signals
from featuregraph.behaviors.objects import BehaviorObjects

ThresholdValue = Real | str
Threshold = ThresholdValue | Mapping[str, ThresholdValue]


class Accumulation(Behavior):
    """
    Construct baseline-relative accumulation objects inside waves.

    A threshold can be:
    - a number;
    - a column name;
    - a groupby aggregation such as "min";
    - a mapping from signal names to any of the above.
    """

    def __init__(
        self,
        signals: Signals,
        group: Group = None,
        threshold: Threshold = "min",
        eps: float = 0.0,
    ) -> None:
        super().__init__(
            signals=signals,
            group=group,
        )

        if eps < 0:
            raise ValueError("eps cannot be negative.")

        self.threshold = threshold
        self.eps = eps

    def threshold_for(
        self,
        signal: str,
    ) -> ThresholdValue:
        if isinstance(self.threshold, Mapping):
            if signal not in self.threshold:
                raise ValueError(
                    f"No threshold was supplied for {signal!r}."
                )

            return self.threshold[signal]

        return self.threshold

    def wave_group(self, signal: str) -> list[str]:
        return self.object_group(
            signal,
            "wave_id",
        )

    def validate(self, df: pd.DataFrame) -> None:
        super().validate(df)

        missing_wave_ids = [
            f"{signal}_wave_id"
            for signal in self.signals
            if f"{signal}_wave_id" not in df.columns
        ]

        if missing_wave_ids:
            raise ValueError(
                "Accumulation currently requires existing wave IDs. "
                f"Missing columns: {missing_wave_ids}"
            )

    def add_signal(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        for signal in self.signals:
            threshold = self.threshold_for(signal)
            object_group = self.wave_group(signal)

            threshold_col = (
                f"{signal}_accumulation_threshold"
            )
            contribution_col = (
                f"{signal}_accumulation_contribution"
            )
            accumulation_col = (
                f"{signal}_accumulation"
            )

            if isinstance(threshold, str):
                if threshold in df.columns:
                    df[threshold_col] = df[threshold]
                else:
                    df[threshold_col] = (
                        df.groupby(
                            object_group,
                            sort=False,
                        )[signal]
                        .transform(threshold)
                    )
            elif isinstance(threshold, Real):
                df[threshold_col] = float(threshold)
            else:
                raise TypeError(
                    "threshold must be a number, column name, "
                    "aggregation name, or mapping."
                )

            df[contribution_col] = (
                df[signal] - df[threshold_col]
            )

            df[accumulation_col] = (
                df.groupby(
                    object_group,
                    sort=False,
                )[contribution_col]
                .cumsum()
            )

        return df

    def add_primitives(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        for signal in self.signals:
            contribution_col = (
                f"{signal}_accumulation_contribution"
            )

            df[f"{signal}_is_accumulating"] = (
                df[contribution_col] > self.eps
            )

            df[f"{signal}_is_depleting"] = (
                df[contribution_col] < -self.eps
            )

            df[f"{signal}_accumulation_inactive"] = (
                df[contribution_col].abs() <= self.eps
            )

        return df

    def add_ids(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        for signal in self.signals:
            df[f"{signal}_accumulation_id"] = (
                df[f"{signal}_wave_id"]
            )

        return df

    def add_features(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        for signal in self.signals:
            object_group = self.object_group(
                signal,
                "accumulation_id",
            )

            contribution_col = (
                f"{signal}_accumulation_contribution"
            )
            cumulative_col = f"{signal}_accumulation"
            index_col = f"{signal}_accumulation_index"
            source_index_col = f"{signal}_source_index"
            peak_event_col = f"exit_{signal}_rising"

            before_peak_col = f"{signal}_before_peak"
            after_peak_col = f"{signal}_after_peak"

            before_contribution_col = (
                f"{signal}_accumulation_before_peak"
            )
            after_contribution_col = (
                f"{signal}_accumulation_from_peak"
            )

            total_col = f"{signal}_total_auc"
            half_col = f"{signal}_half_auc"
            reached_half_col = f"{signal}_reached_half_auc"
            half_time_col = (
                f"{signal}_half_accumulation_time"
            )
            weighted_col = (
                f"{signal}_weighted_accumulation"
            )

            if peak_event_col not in df.columns:
                raise ValueError(
                    f"Required peak event column "
                    f"{peak_event_col!r} is missing."
                )

            df[index_col] = (
                df.groupby(object_group, sort=False)
                .cumcount()
            )

            df[source_index_col] = df.index

            peak_count = (
                df.groupby(
                    object_group,
                    sort=False,
                )[peak_event_col]
                .cumsum()
            )

            df[before_peak_col] = peak_count == 0
            df[after_peak_col] = peak_count > 0

            df[before_contribution_col] = np.where(
                df[before_peak_col],
                df[contribution_col],
                0.0,
            )

            df[after_contribution_col] = np.where(
                df[after_peak_col],
                df[contribution_col],
                0.0,
            )

            df[f"{signal}_auc_at_peak"] = np.where(
                df[peak_event_col].astype(bool),
                df[cumulative_col],
                0.0,
            )

            df[weighted_col] = (
                df[index_col] * df[contribution_col]
            )

            df[total_col] = (
                df.groupby(
                    object_group,
                    sort=False,
                )[contribution_col]
                .transform("sum")
            )

            df[half_col] = df[total_col] / 2

            df[reached_half_col] = (
                df[cumulative_col] >= df[half_col]
            )

            first_half_rows = (
                df.loc[df[reached_half_col]]
                .groupby(object_group, sort=False)
                .head(1)
            )

            half_times = first_half_rows.set_index(
                object_group
            )[index_col]

            if len(object_group) == 1:
                keys = df[object_group[0]]
            else:
                keys = pd.MultiIndex.from_frame(
                    df[object_group]
                )

            df[half_time_col] = keys.map(half_times)

        return df

    def summarize(
        self,
        df: pd.DataFrame,
        signal: str,
    ) -> BehaviorObjects:
        self.validate_signal(df, signal)

        object_group = self.object_group(
            signal,
            "accumulation_id",
        )

        summarydf = (
            df.groupby(object_group, sort=False)
            .agg(
                start_index=(
                    f"{signal}_source_index",
                    "first",
                ),
                end_index=(
                    f"{signal}_source_index",
                    "last",
                ),
                duration=(
                    f"{signal}_accumulation_index",
                    "count",
                ),
                baseline=(
                    f"{signal}_accumulation_threshold",
                    "first",
                ),
                total_auc=(
                    f"{signal}_accumulation_contribution",
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
            .rename(
                columns={
                    f"{signal}_accumulation_id":
                        "accumulation_id",
                }
            )
        )

        duration = summarydf["duration"]

        summarydf["accumulation_rate"] = (
            summarydf["total_auc"] / duration
        ).where(duration > 0)

        before = summarydf["accumulation_before_peak"]
        after = summarydf["accumulation_from_peak"]
        denominator = before + after

        summarydf["accumulation_symmetry"] = (
            1 - (before - after).abs() / denominator
        ).where(denominator > 0)

        total_auc = summarydf["total_auc"]

        summarydf["centroid_time"] = (
            summarydf["first_moment"] / total_auc
        ).where(total_auc != 0)

        properties = (
            "accumulation_id",
            # "parent_oscillation_id",
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
        )

        table = summarydf[
            [
                *self.group_columns,
                *properties,
            ]
        ]

        return BehaviorObjects(
            behavior_type="accumulation",
            signal=signal,
            table=table,
            features=df,
            group=tuple(self.group_columns),
            properties=properties,
            construction={
                "threshold": self.threshold,
                "eps": self.eps,
            },
            parent_behavior="oscillation",
            parent_id="parent_oscillation_id",
        )
