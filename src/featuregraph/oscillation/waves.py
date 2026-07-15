from featuregraph.operators.states import rising_state, falling_state
from featuregraph.operators.events import enter_state, exit_state, event_id, event_index
from featuregraph.operators.measures import group_transform, group_map
from featuregraph.preprocessing.smoothing import smooth

import numpy as np

def add_wave_smoothing(df, signals, group, window=20):
    df = df.copy()
    for signal in signals:
        df[f"{signal}_smooth"] = smooth(df, signal, group, window)
    return df

def add_wave_primitives(df, signals, diff_lag=10, eps=0):
    df = df.copy()

    for signal in signals:
        rising_col = f"{signal}_rising"
        falling_col = f"{signal}_falling"
        enter_rising_col = f"enter_{rising_col}"
        exit_rising_col = f"exit_{rising_col}"
        peak_index = f'{signal}_peak_index'
        trough_index = f'{signal}_trough_index'

        df[rising_col] = rising_state(df[signal], diff_lag, eps)
        df[falling_col] = falling_state(df[signal], diff_lag, eps)
        df[enter_rising_col] = enter_state(df[rising_col])
        df[exit_rising_col] = exit_state(df[rising_col])
        df[peak_index] = event_index(df, exit_rising_col)
        df[trough_index] = event_index(df, enter_rising_col)

    return df

def add_wave_id(df, signals, group):
    df = df.copy()
    for signal in signals:
        df[f"{signal}_wave_id"] = event_id(df, f'enter_{signal}_rising', group)
    return df

def add_wave_features(df, signals, group):
    df = df.copy()
    for signal in signals:
        rising_col = f"{signal}_rising"
        falling_col = f"{signal}_falling"
        rising_time_col = f"{rising_col}_time"
        falling_time_col = f"{falling_col}_time"

        df[rising_time_col] = group_transform(df, rising_col, 'sum', group)
        df[falling_time_col] = group_transform(df, falling_col, 'sum', group)
        df[f'{signal}_amplitude'] = (group_transform(df, signal, 'max', group) -
                                     group_transform(df, signal, 'min', group)) / 2
        df[f'{signal}_duration'] = group_transform(df, rising_time_col, 'max', group) + \
                                    group_transform(df, falling_time_col, 'max', group)

    return df

def add_inter_wave_features(df, signals, group):
    for signal in signals:
        df[f'{signal}_previous_amplitude'] = group_map(df, f'{signal}_amplitude', 'max', group, offset=1)
        df[f'{signal}_period'] = group_map(df, f'{signal}_peak_index', 'max', group, offset=0) - \
                                 group_map(df, f'{signal}_peak_index', 'max', group, offset=1)
        df[f"{signal}_log_decrement"] = np.log(df[f"{signal}_previous_amplitude"] / df[f"{signal}_amplitude"])
        df[f"{signal}_damping_ratio"] = df[f"{signal}_log_decrement"] / np.sqrt((2 * np.pi) ** 2 + df[f'{signal}_log_decrement'] ** 2)
        df[f"{signal}_decay_rate"] = np.log(df[f"{signal}_amplitude"] / df[f"{signal}_previous_amplitude"]) / df[f"{signal}_period"]
        df[f"{signal}_symmetry"] = (1 - (df[f"{signal}_rising_time"] - df[f"{signal}_falling_time"]).abs() / df[f"{signal}_duration"])

    return df

def get_wave_summary(df, signal):
    summarydf = (
        df.groupby(f"{signal}_wave_id")
        .agg(
            peak_index=(f"{signal}_peak_index", "max"),
            rise_duration=(f"{signal}_rising", "sum"),
            fall_duration=(f"{signal}_falling", "sum"),
            maximum=(f"{signal}", "max"),
            minimum=(f"{signal}", "min"),
        )
        .reset_index()
        .rename(columns={f"{signal}_wave_id": "oscillation_id"})
    )
    
    summarydf["start_index"] = (
        summarydf["peak_index"] - summarydf["rise_duration"]
    )
    
    summarydf["end_index"] = (
        summarydf["peak_index"] + summarydf["fall_duration"]
    )
    
    summarydf["duration"] = (
        summarydf["rise_duration"] + summarydf["fall_duration"]
    )
    
    summarydf["period"] = (
        summarydf["peak_index"] - summarydf["peak_index"].shift()
    )
    
    summarydf["amplitude"] = (
        summarydf["maximum"] - summarydf["minimum"]
    ) / 2
    
    summarydf["temporal_symmetry"] = (
        1
        - (
            summarydf["rise_duration"]
            - summarydf["fall_duration"]
        ).abs()
        / summarydf["duration"]
    ).where(summarydf["duration"] > 0)
    
    summarydf = summarydf[
        [
            "oscillation_id",
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
    
    return summarydf
