import pandas as pd

from featuregraph.behaviors.base import Behavior, Group, Signals
from featuregraph.behaviors.objects import BehaviorObjects
from featuregraph.operators.events import (
    enter_state,
    event_id,
    event_index,
    exit_state,
    preceding_sample_event,
)
from featuregraph.operators.states import (
    negative_state,
    positive_state,
)
from featuregraph.preprocessing.smoothing import smooth


class Oscillation(Behavior):
    """Construct oscillation objects from explicitly configured transitions.

    ``diff_lag`` and ``eps`` define the rising and falling states. When
    ``max_state_gap`` is greater than zero, False runs of at most that many
    samples are changed to True only when they are bounded by rising states
    in the same group. This deterministic gap-closing rule can prevent a
    brief interruption from creating an additional candidate peak; it does
    not determine whether a signal is an oscillation or whether a candidate
    peak is meaningful.
    """

    def __init__(
        self,
        signals: Signals,
        group: Group = None,
        smooth_signal: bool = False,
        smooth_window: int = 20,
        diff_lag: int = 10,
        eps: float = 0.0,
        max_state_gap: int = 0,
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

        if isinstance(max_state_gap, bool) or not isinstance(
            max_state_gap,
            int,
        ):
            raise TypeError(
                "max_state_gap must be an integer."
            )

        if max_state_gap < 0:
            raise ValueError(
                "max_state_gap cannot be negative."
            )

        self.smooth_signal = smooth_signal
        self.smooth_window = smooth_window
        self.diff_lag = diff_lag
        self.eps = eps
        self.max_state_gap = max_state_gap

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

    @staticmethod
    def _close_short_false_runs(
        state: pd.Series,
        max_gap: int,
    ) -> pd.Series:
        """Fill short False runs bounded by True states."""
        if max_gap == 0 or state.empty:
            return state.astype(bool)

        run_id = state.ne(state.shift()).cumsum()
        run_value = state.groupby(run_id).first()
        run_size = state.groupby(run_id).size()

        fill_run = (
            ~run_value
            & run_value.shift(fill_value=False)
            & run_value.shift(-1, fill_value=False)
            & run_size.le(max_gap)
        )

        fill_samples = (
            run_id
            .map(fill_run)
            .fillna(False)
            .astype(bool)
        )

        return state.astype(bool) | fill_samples

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
            peak_col = f"{signal}_peak"
            trough_col = f"{signal}_trough"

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

            if self.group_columns:
                df[rising_col] = (
                    df.groupby(
                        self.group_columns,
                        sort=False,
                    )[rising_col]
                    .transform(
                        lambda state:
                            self._close_short_false_runs(
                                state,
                                self.max_state_gap,
                            )
                    )
                )
            else:
                df[rising_col] = (
                    self._close_short_false_runs(
                        df[rising_col],
                        self.max_state_gap,
                    )
                )

            # A filled rising-state interruption is treated as part of
            # the same transition, so directional states remain exclusive.
            df[falling_col] = (
                df[falling_col]
                & ~df[rising_col]
            )

            df[enter_rising_col] = enter_state(
                df[rising_col],
                event_group,
            )

            df[exit_rising_col] = exit_state(
                df[rising_col],
                event_group,
            )

            # Directional states describe the edge ending at the current
            # row. A reversal detected at row i therefore places the
            # corresponding extremum at the preceding sample.
            df[peak_col] = preceding_sample_event(
                df[exit_rising_col],
                event_group,
            )

            df[trough_col] = preceding_sample_event(
                df[enter_rising_col],
                event_group,
            )

            df[f"{signal}_peak_index"] = event_index(
                df,
                peak_col,
                self.group,
            )

            df[f"{signal}_trough_index"] = event_index(
                df,
                trough_col,
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

            wave_id_col = f"{signal}_wave_id"
            start_index = grouped[
                f"{signal}_trough_index"
            ].transform("first")
            peak_index = grouped[
                f"{signal}_peak_index"
            ].transform("max")
            end_index = grouped[
                f"{signal}_trough_index"
            ].transform("max")
            has_start = grouped[
                f"enter_{signal}_rising"
            ].transform("max").astype(bool)

            if self.group_columns:
                last_wave_id = (
                    df.groupby(
                        self.group_columns,
                        sort=False,
                    )[wave_id_col]
                    .transform("max")
                )
            else:
                last_wave_id = df[wave_id_col].max()

            df[f"{signal}_wave_complete"] = (
                has_start
                & start_index.notna()
                & peak_index.notna()
                & end_index.notna()
                & start_index.lt(peak_index)
                & peak_index.lt(end_index)
                & df[wave_id_col].lt(last_wave_id)
            )

        return df

    def summarize(
        self,
        df: pd.DataFrame,
        signal: str,
        include_partial: bool = False,
    ) -> BehaviorObjects:
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
                start_index=(
                    f"{signal}_trough_index",
                    "first",
                ),
                peak_index=(
                    f"{signal}_peak_index",
                    "max",
                ),
                end_index=(
                    f"{signal}_trough_index",
                    "max",
                ),
                rising_samples=(
                    f"{signal}_rising",
                    "sum",
                ),
                falling_samples=(
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
                is_complete=(
                    f"{signal}_wave_complete",
                    "first",
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

        if not include_partial:
            summarydf = (
                summarydf.loc[
                    summarydf["is_complete"]
                ]
                .copy()
                .reset_index(drop=True)
            )

        summarydf["rise_duration"] = (
            summarydf["peak_index"]
            - summarydf["start_index"]
        )

        summarydf["fall_duration"] = (
            summarydf["end_index"]
            - summarydf["peak_index"]
        )

        summarydf["duration"] = (
            summarydf["end_index"]
            - summarydf["start_index"]
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

        properties = (
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
        )
        
        table = summarydf[
            [
                *self.group_columns,
                *properties,
            ]
        ]

        return BehaviorObjects(
            behavior_type="oscillation",
            signal=signal,
            table=table,
            features=df,
            group=tuple(self.group_columns),
            properties=properties,
            construction={
                "smooth_signal": self.smooth_signal,
                "smooth_window": self.smooth_window,
                "diff_lag": self.diff_lag,
                "eps": self.eps,
                "max_state_gap": self.max_state_gap,
                "include_partial": include_partial,
            },
        )
