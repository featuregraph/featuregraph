import pandas as pd

from featuregraph.behaviors.base import Behavior, Group, Signals
from featuregraph.operators.events import (
    enter_state,
    event_id,
    event_index,
    exit_state,
)
from featuregraph.operators.states import (
    falling_state,
    rising_state,
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
        for signal in self.signals:
            source = self.working_signal(signal)

            # Derived columns retain the logical signal name.
            rising_col = f"{signal}_rising"
            falling_col = f"{signal}_falling"
            enter_rising_col = f"enter_{rising_col}"
            exit_rising_col = f"exit_{rising_col}"

            df[rising_col] = rising_state(
                df[source],
                self.diff_lag,
                self.eps,
            )

            df[falling_col] = falling_state(
                df[source],
                self.diff_lag,
                self.eps,
            )

            df[enter_rising_col] = enter_state(
                df[rising_col]
            )

            df[exit_rising_col] = exit_state(
                df[rising_col]
            )

            df[f"{signal}_peak_index"] = event_index(
                df,
                exit_rising_col,
            )

            df[f"{signal}_trough_index"] = event_index(
                df,
                enter_rising_col,
            )

        return df

    def add_ids(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
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
        for signal in self.signals:
            source = self.working_signal(signal)

            object_group = self.object_group(
                signal,
                "wave_id",
            )

            rising_col = f"{signal}_rising"
            falling_col = f"{signal}_falling"

            grouped = df.groupby(
                object_group,
                sort=False,
            )

            df[f"{signal}_rising_time"] = (
                grouped[rising_col]
                .transform("sum")
            )

            df[f"{signal}_falling_time"] = (
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

            df[f"{signal}_amplitude"] = (
                maximum - minimum
            ) / 2

            df[f"{signal}_duration"] = (
                df[f"{signal}_rising_time"]
                + df[f"{signal}_falling_time"]
            )

        return df

    def summarize(
        self,
        df: pd.DataFrame,
        signal: str,
        include_partial: bool = False,
    ) -> pd.DataFrame:
        
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
                summarydf.loc[summarydf["is_complete"]]
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

        summarydf["amplitude"] = (
            summarydf["maximum"]
            - summarydf["minimum"]
        ) / 2

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
                "temporal_symmetry",
            ]
        ]