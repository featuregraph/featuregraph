import pandas as pd

from featuregraph.behaviors.base import Behavior, Group, Signals, Time
from featuregraph.behaviors.objects import BehaviorObjects
from featuregraph.behaviors.transition import Transition
from featuregraph.operators.events import (
    event_id,
    event_index,
    event_value,
    preceding_sample_event,
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
        time: Time = None,
    ) -> None:
        super().__init__(
            signals=signals,
            group=group,
            time=time,
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
        """Compose extrema primitives from directional transitions."""
        transitions = Transition(
            signals=self.signals,
            group=self.group,
            diff_lag=self.diff_lag,
            eps=self.eps,
            source_signals={
                signal: self.working_signal(signal)
                for signal in self.signals
            },
            time=self.time,
        )
        df = transitions.fit_transform(df)

        for signal in self.signals:
            enter_rising_col = f"enter_{signal}_rising"
            exit_rising_col = f"exit_{signal}_rising"
            peak_col = f"{signal}_peak"
            trough_col = f"{signal}_trough"

            if self.group_columns:
                event_group = [
                    df[column]
                    for column in self.group_columns
                ]
            else:
                event_group = None

            positions = self.positions(df)
            numeric_time = self.numeric_time(df)

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
            df[f"{signal}_peak_position"] = event_value(
                df,
                peak_col,
                positions,
                self.group,
            )
            df[f"{signal}_trough_position"] = event_value(
                df,
                trough_col,
                positions,
                self.group,
            )
            if numeric_time is None:
                df[f"{signal}_peak_time"] = pd.NA
                df[f"{signal}_trough_time"] = pd.NA
            else:
                df[f"{signal}_peak_time"] = event_value(
                    df,
                    peak_col,
                    numeric_time,
                    self.group,
                )
                df[f"{signal}_trough_time"] = event_value(
                    df,
                    trough_col,
                    numeric_time,
                    self.group,
                )

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

            direction_col = f"{signal}_transition_direction"
            rate_col = f"{signal}_rate"

            grouped = df.groupby(
                object_group,
                sort=False,
            )

            rising_time = grouped[
                direction_col
            ].transform(
                lambda direction: direction.eq("rising").sum()
            )

            falling_time = grouped[
                direction_col
            ].transform(
                lambda direction: direction.eq("falling").sum()
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
            ].transform("last")
            end_index = grouped[
                f"{signal}_trough_index"
            ].transform("last")
            start_position = grouped[
                f"{signal}_trough_position"
            ].transform("first")
            peak_position = grouped[
                f"{signal}_peak_position"
            ].transform("max")
            end_position = grouped[
                f"{signal}_trough_position"
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
                & start_position.lt(peak_position)
                & peak_position.lt(end_position)
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
                start_position=(
                    f"{signal}_trough_position",
                    "first",
                ),
                peak_position=(
                    f"{signal}_peak_position",
                    "max",
                ),
                end_position=(
                    f"{signal}_trough_position",
                    "max",
                ),
                start_time=(
                    f"{signal}_trough_time",
                    "first",
                ),
                peak_time=(
                    f"{signal}_peak_time",
                    "max",
                ),
                end_time=(
                    f"{signal}_trough_time",
                    "max",
                ),
                rising_samples=(
                    f"{signal}_transition_direction",
                    lambda direction:
                        direction.eq("rising").sum(),
                ),
                falling_samples=(
                    f"{signal}_transition_direction",
                    lambda direction:
                        direction.eq("falling").sum(),
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

        summarydf["rise_duration_samples"] = (
            summarydf["peak_position"]
            - summarydf["start_position"]
        )

        summarydf["fall_duration_samples"] = (
            summarydf["end_position"]
            - summarydf["peak_position"]
        )

        summarydf["duration_samples"] = (
            summarydf["end_position"]
            - summarydf["start_position"]
        )

        if self.group_columns:
            summarydf["period_samples"] = (
                summarydf.groupby(
                    self.group_columns,
                    sort=False,
                )["peak_position"]
                .diff()
            )
        else:
            summarydf["period_samples"] = (
                summarydf["peak_position"].diff()
            )

        if self.time is None:
            summarydf["rise_duration"] = summarydf[
                "rise_duration_samples"
            ]
            summarydf["fall_duration"] = summarydf[
                "fall_duration_samples"
            ]
            summarydf["duration"] = summarydf["duration_samples"]
            summarydf["period"] = summarydf["period_samples"]
        else:
            summarydf["rise_duration"] = (
                summarydf["peak_time"] - summarydf["start_time"]
            )
            summarydf["fall_duration"] = (
                summarydf["end_time"] - summarydf["peak_time"]
            )
            summarydf["duration"] = (
                summarydf["end_time"] - summarydf["start_time"]
            )
            if self.group_columns:
                summarydf["period"] = (
                    summarydf.groupby(
                        self.group_columns,
                        sort=False,
                    )["peak_time"].diff()
                )
            else:
                summarydf["period"] = summarydf["peak_time"].diff()

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
                "start_time",
                "peak_time",
                "end_time",
                "rise_duration_samples",
                "fall_duration_samples",
                "duration_samples",
                "period_samples",
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
                "time": self.time,
                "include_partial": include_partial,
            },
        )
