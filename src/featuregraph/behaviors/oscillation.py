import pandas as pd

from featuregraph.behaviors.base import Behavior, Group, Signals
from featuregraph.operators.events import (
    enter_state,
    event_id,
    event_index,
    exit_state,
)
from featuregraph.operators.states import (
    negative_state,
    positive_state,
)
from featuregraph.preprocessing.smoothing import smooth


class Oscillation(Behavior):
    """Construct oscillation objects from observed signals."""

    def __init__(
        self,
        signals: Signals,
        group: Group = None,
        smooth_signal: bool = False,
        smooth_window: int = 20,
        diff_lag: int = 10,
        eps: float = 0.0,
    ) -> None:
        super().__init__(
            signals=signals,
            group=group,
        )

        if smooth_window < 1:
            raise ValueError(
                "smooth_window must be at least 1."
            )

        if diff_lag < 1:
            raise ValueError(
                "diff_lag must be at least 1."
            )

        if eps < 0:
            raise ValueError(
                "eps cannot be negative."
            )

        self.smooth_signal = smooth_signal
        self.smooth_window = smooth_window
        self.diff_lag = diff_lag
        self.eps = eps

    def working_signal(self, signal: str) -> str:
        """Return the column used for numerical calculations."""
        if self.smooth_signal:
            return f"{signal}_smooth"

        return signal

    def add_signal(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Optionally add a smoothed working signal."""
        if not self.smooth_signal:
            return df

        for signal in self.signals:
            df[self.working_signal(signal)] = smooth(
                df,
                signal,
                self.group,
                self.smooth_window,
            )

        return df

    def add_primitives(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Add directional states, boundary events, and local rates."""
        for signal in self.signals:
            source = self.working_signal(signal)

            # Derived columns retain the logical signal name.
            rising_col = f"{signal}_rising"
            falling_col = f"{signal}_falling"
            enter_rising_col = f"enter_{rising_col}"
            exit_rising_col = f"exit_{rising_col}"
            rate_col = f"{signal}_rate"

            if self.group_columns:
                difference = (
                    df.groupby(
                        self.group_columns,
                        sort=False,
                    )[source]
                    .diff(self.diff_lag)
                )
                event_group = [
                    df[column]
                    for column in self.group_columns
                ]
            else:
                difference = df[source].diff(
                    self.diff_lag
                )
                event_group = None

            df[rising_col] = positive_state(
                difference,
                self.eps,
            )

            df[falling_col] = negative_state(
                difference,
                self.eps,
            )

            df[enter_rising_col] = enter_state(
                df[rising_col],
                event_group,
            )

            df[exit_rising_col] = exit_state(
                df[rising_col],
                event_group,
            )

            df[f"{signal}_peak_index"] = event_index(
                df,
                exit_rising_col,
                self.group,
            )

            df[f"{signal}_trough_index"] = event_index(
                df,
                enter_rising_col,
                self.group,
            )

            # Approximate change per sample over diff_lag samples.
            # Grouped differences prevent rates from crossing
            # independent sequence boundaries.
            df[rate_col] = difference / self.diff_lag

        return df

    def add_ids(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Assign one identifier to each oscillation."""
        for signal in self.signals:
            df[f"{signal}_wave_id"] = event_id(
                df,
                f"enter_{signal}_rising",
                self.group,
            )

        return df

    def add_features(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Add row-aligned oscillation measurements."""
        for signal in self.signals:
            source = self.working_signal(signal)

            object_group = self.object_group(
                signal,
                "wave_id",
            )

            rising_col = f"{signal}_rising"
            falling_col = f"{signal}_falling"
            rate_col = f"{signal}_rate"

            grouped = df.groupby(
                object_group,
                sort=False,
            )

            rising_time = (
                grouped[rising_col]
                .transform("sum")
            )

            falling_time = (
                grouped[falling_col]
                .transform("sum")
            )

            maximum = (
                grouped[source]
                .transform("max")
            )

            minimum = (
                grouped[source]
                .transform("min")
            )

            net_change = maximum - minimum

            df[f"{signal}_rising_time"] = rising_time
            df[f"{signal}_falling_time"] = falling_time

            df[f"{signal}_amplitude"] = (
                net_change / 2
            )

            df[f"{signal}_duration"] = (
                rising_time + falling_time
            )

            # Mean transition rates describe the average speed
            # from trough to peak and from peak to trough.
            df[f"{signal}_rising_mean_rate"] = (
                net_change / rising_time
            ).where(rising_time > 0)

            df[f"{signal}_falling_mean_rate"] = (
                net_change / falling_time
            ).where(falling_time > 0)

            # Peak rise rate is the largest positive local rate.
            df[f"{signal}_peak_rise_rate"] = (
                grouped[rate_col]
                .transform("max")
                .clip(lower=0)
            )

            # Peak fall rate is represented as a positive magnitude.
            df[f"{signal}_peak_fall_rate"] = (
                -grouped[rate_col]
                .transform("min")
            ).clip(lower=0)

        return df

    def summarize(
        self,
        df: pd.DataFrame,
        signal: str,
        include_partial: bool = False,
    ) -> pd.DataFrame:
        """Return one row per oscillation object."""
        if signal not in self.signals:
            raise ValueError(
                f"Signal {signal!r} was not configured for "
                "this Oscillation constructor."
            )

        source = self.working_signal(signal)
        self.validate_signal(df, source)

        object_group = self.object_group(
            signal,
            "wave_id",
        )

        summarydf = (
            df.groupby(
                object_group,
                sort=False,
            )
            .agg(
                peak_index=(
                    f"{signal}_peak_index",
                    "max",
                ),
                rise_duration=(
                    f"{signal}_rising",
                    "sum",
                ),
                fall_duration=(
                    f"{signal}_falling",
                    "sum",
                ),
                maximum=(
                    source,
                    "max",
                ),
                minimum=(
                    source,
                    "min",
                ),
                peak_rise_rate=(
                    f"{signal}_peak_rise_rate",
                    "max",
                ),
                peak_fall_rate=(
                    f"{signal}_peak_fall_rate",
                    "max",
                ),
                has_start=(
                    f"enter_{signal}_rising",
                    "max",
                ),
            )
            .reset_index()
            .rename(
                columns={
                    f"{signal}_wave_id":
                        "oscillation_id",
                }
            )
        )

        if self.group_columns:
            has_next_boundary = (
                summarydf.groupby(
                    self.group_columns,
                    sort=False,
                )["oscillation_id"]
                .shift(-1)
                .notna()
            )
        else:
            has_next_boundary = (
                summarydf["oscillation_id"]
                .shift(-1)
                .notna()
            )

        summarydf["is_complete"] = (
            summarydf["has_start"].astype(bool)
            & summarydf["peak_index"].notna()
            & summarydf["rise_duration"].gt(0)
            & summarydf["fall_duration"].gt(0)
            & has_next_boundary
        )

        if not include_partial:
            summarydf = (
                summarydf.loc[
                    summarydf["is_complete"]
                ]
                .copy()
                .reset_index(drop=True)
            )

        summarydf["start_index"] = (
            summarydf["peak_index"]
            - summarydf["rise_duration"]
        )

        summarydf["end_index"] = (
            summarydf["peak_index"]
            + summarydf["fall_duration"]
        )

        summarydf["duration"] = (
            summarydf["rise_duration"]
            + summarydf["fall_duration"]
        )

        if self.group_columns:
            summarydf["period"] = (
                summarydf.groupby(
                    self.group_columns,
                    sort=False,
                )["peak_index"]
                .diff()
            )
        else:
            summarydf["period"] = (
                summarydf["peak_index"].diff()
            )

        net_change = (
            summarydf["maximum"]
            - summarydf["minimum"]
        )

        summarydf["amplitude"] = net_change / 2

        summarydf["rising_mean_rate"] = (
            net_change
            / summarydf["rise_duration"]
        ).where(
            summarydf["rise_duration"] > 0
        )

        summarydf["falling_mean_rate"] = (
            net_change
            / summarydf["fall_duration"]
        ).where(
            summarydf["fall_duration"] > 0
        )

        duration = summarydf["duration"]

        summarydf["temporal_symmetry"] = (
            1
            - (
                summarydf["rise_duration"]
                - summarydf["fall_duration"]
            ).abs()
            / duration
        ).where(duration > 0)

        return summarydf[
            [
                *self.group_columns,
                "oscillation_id",
                "is_complete",
                "start_index",
                "peak_index",
                "end_index",
                "rise_duration",
                "fall_duration",
                "duration",
                "period",
                "amplitude",
                "rising_mean_rate",
                "falling_mean_rate",
                "peak_rise_rate",
                "peak_fall_rate",
                "temporal_symmetry",
            ]
        ]
