from collections.abc import Mapping

import numpy as np
import pandas as pd

from featuregraph.behaviors.base import Behavior, Group, Signals
from featuregraph.behaviors.objects import BehaviorObjects
from featuregraph.operators.events import (
    enter_state,
    event_id,
    exit_state,
    preceding_sample_event,
)
from featuregraph.operators.states import (
    inactive_state,
    negative_state,
    positive_state,
)


class Transition(Behavior):
    """Construct contiguous directional transitions from observed signals."""

    directions = ("rising", "falling", "inactive")

    def __init__(
        self,
        signals: Signals,
        group: Group = None,
        diff_lag: int = 10,
        eps: float = 0.0,
        source_signals: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(signals=signals, group=group)

        if diff_lag < 1:
            raise ValueError("diff_lag must be at least 1.")

        if eps < 0:
            raise ValueError("eps cannot be negative.")

        self.diff_lag = diff_lag
        self.eps = eps
        self.source_signals = dict(source_signals or {})

    def source_for(self, signal: str) -> str:
        """Return the numerical source used to construct a transition."""
        return self.source_signals.get(signal, signal)

    def validate(self, df: pd.DataFrame) -> None:
        super().validate(df)

        missing = [
            self.source_for(signal)
            for signal in self.signals
            if self.source_for(signal) not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Transition source columns are missing: {missing}"
            )

    def add_primitives(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Add direction states and their entry and exit events."""
        for signal in self.signals:
            source = self.source_for(signal)
            difference_col = f"{signal}_difference"
            rate_col = f"{signal}_rate"

            if self.group_columns:
                difference = (
                    df.groupby(self.group_columns, sort=False)[source]
                    .diff(self.diff_lag)
                )
                event_group = [
                    df[column]
                    for column in self.group_columns
                ]
            else:
                difference = df[source].diff(self.diff_lag)
                event_group = None

            df[difference_col] = difference
            df[rate_col] = difference / self.diff_lag

            state_operators = {
                "rising": positive_state,
                "falling": negative_state,
                "inactive": inactive_state,
            }

            for direction, operator in state_operators.items():
                state_col = f"{signal}_{direction}"
                df[state_col] = operator(difference, self.eps)
                df[f"enter_{state_col}"] = enter_state(
                    df[state_col],
                    event_group,
                )
                df[f"exit_{state_col}"] = exit_state(
                    df[state_col],
                    event_group,
                )

            df[f"{signal}_transition_direction"] = np.select(
                [
                    df[f"{signal}_rising"],
                    df[f"{signal}_falling"],
                    df[f"{signal}_inactive"],
                ],
                list(self.directions),
                default=None,
            )

            enter_columns = [
                f"enter_{signal}_{direction}"
                for direction in self.directions
            ]
            exit_columns = [
                f"exit_{signal}_{direction}"
                for direction in self.directions
            ]

            df[f"enter_{signal}_transition"] = (
                df[enter_columns].any(axis=1)
            )
            df[f"exit_{signal}_transition"] = (
                df[exit_columns].any(axis=1)
            )

            df[f"{signal}_transition_start"] = (
                preceding_sample_event(
                    df[f"enter_{signal}_transition"],
                    event_group,
                )
            )
            df[f"{signal}_transition_end"] = (
                preceding_sample_event(
                    df[f"exit_{signal}_transition"],
                    event_group,
                )
            )

            source_index = pd.Series(
                df.index,
                index=df.index,
            )

            if self.group_columns:
                previous_index = source_index.groupby(
                    event_group,
                    sort=False,
                ).shift(1)
                previous_value = df[source].groupby(
                    event_group,
                    sort=False,
                ).shift(1)
            else:
                previous_index = source_index.shift(1)
                previous_value = df[source].shift(1)

            start_index = previous_index.where(
                df[f"enter_{signal}_transition"]
            )
            start_value = previous_value.where(
                df[f"enter_{signal}_transition"]
            )

            if self.group_columns:
                start_index = start_index.groupby(
                    event_group,
                    sort=False,
                ).ffill()
                start_value = start_value.groupby(
                    event_group,
                    sort=False,
                ).ffill()
            else:
                start_index = start_index.ffill()
                start_value = start_value.ffill()

            df[f"{signal}_transition_start_index"] = start_index
            df[f"{signal}_transition_start_value"] = start_value
            df[f"{signal}_transition_end_index"] = np.where(
                df[f"{signal}_transition_end"],
                df.index,
                np.nan,
            )

        return df

    def add_ids(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Assign one identifier to each contiguous direction state."""
        for signal in self.signals:
            transition_id_col = f"{signal}_transition_id"
            df[transition_id_col] = event_id(
                df,
                f"enter_{signal}_transition",
                self.group,
            )

            for direction in self.directions:
                df[f"{signal}_{direction}_transition_id"] = (
                    df[transition_id_col].where(
                        df[f"{signal}_{direction}"]
                    )
                )

        return df

    def add_features(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Add row-aligned transition measurements."""
        for signal in self.signals:
            source = self.source_for(signal)
            object_group = self.object_group(
                signal,
                "transition_id",
            )
            grouped = df.groupby(object_group, sort=False)

            start_index = grouped[
                f"{signal}_transition_start_index"
            ].transform("first")
            detected_end = grouped[
                f"{signal}_transition_end_index"
            ].transform("max")

            if self.group_columns:
                sequence_end = (
                    df.groupby(self.group_columns, sort=False)[source]
                    .transform(lambda values: values.index[-1])
                )
            else:
                sequence_end = pd.Series(
                    df.index[-1],
                    index=df.index,
                )

            end_index = detected_end.fillna(sequence_end)
            start_value = grouped[
                f"{signal}_transition_start_value"
            ].transform("first")
            end_value = grouped[source].transform("last")
            duration = end_index - start_index

            df[f"{signal}_transition_start_index"] = start_index
            df[f"{signal}_transition_end_index"] = end_index
            df[f"{signal}_transition_duration"] = duration
            df[f"{signal}_transition_start_value"] = start_value
            df[f"{signal}_transition_end_value"] = end_value
            df[f"{signal}_transition_net_change"] = (
                end_value - start_value
            )
            df[f"{signal}_transition_mean_rate"] = (
                (end_value - start_value) / duration
            ).where(duration > 0)
            df[f"{signal}_transition_peak_rate"] = (
                grouped[f"{signal}_rate"]
                .transform(lambda values: values.abs().max())
            )
            df[f"{signal}_transition_complete"] = (
                grouped[f"{signal}_transition_end"]
                .transform("max")
                .astype(bool)
            )

        return df

    def summarize(
        self,
        df: pd.DataFrame,
        signal: str,
        include_partial: bool = False,
    ) -> BehaviorObjects:
        """Return one row per directional transition."""
        if signal not in self.signals:
            raise ValueError(
                f"Signal {signal!r} was not configured for "
                "this Transition constructor."
            )

        source = self.source_for(signal)
        self.validate_signal(df, source)
        object_group = self.object_group(
            signal,
            "transition_id",
        )

        summarydf = (
            df.loc[
                df[f"{signal}_transition_direction"].notna()
            ]
            .groupby(object_group, sort=False)
            .agg(
                direction=(
                    f"{signal}_transition_direction",
                    "first",
                ),
                is_complete=(
                    f"{signal}_transition_complete",
                    "first",
                ),
                start_index=(
                    f"{signal}_transition_start_index",
                    "first",
                ),
                end_index=(
                    f"{signal}_transition_end_index",
                    "first",
                ),
                duration=(
                    f"{signal}_transition_duration",
                    "first",
                ),
                start_value=(
                    f"{signal}_transition_start_value",
                    "first",
                ),
                end_value=(
                    f"{signal}_transition_end_value",
                    "first",
                ),
                net_change=(
                    f"{signal}_transition_net_change",
                    "first",
                ),
                mean_rate=(
                    f"{signal}_transition_mean_rate",
                    "first",
                ),
                peak_rate=(
                    f"{signal}_transition_peak_rate",
                    "first",
                ),
            )
            .reset_index()
            .rename(
                columns={
                    f"{signal}_transition_id": "transition_id",
                }
            )
        )

        if not include_partial:
            summarydf = (
                summarydf.loc[summarydf["is_complete"]]
                .copy()
                .reset_index(drop=True)
            )

        properties = (
            "transition_id",
            "direction",
            "is_complete",
            "start_index",
            "end_index",
            "duration",
            "start_value",
            "end_value",
            "net_change",
            "mean_rate",
            "peak_rate",
        )

        return BehaviorObjects(
            behavior_type="transition",
            signal=signal,
            table=summarydf[
                [*self.group_columns, *properties]
            ],
            features=df,
            group=tuple(self.group_columns),
            properties=properties,
            construction={
                "diff_lag": self.diff_lag,
                "eps": self.eps,
                "include_partial": include_partial,
            },
        )
