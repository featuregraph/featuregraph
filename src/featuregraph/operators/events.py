import numpy as np
import pandas as pd


def _group_keys(df, group):
    if group is None:
        return None
    if isinstance(group, str):
        return df[group]
    return [df[column] for column in group]


def enter_state(state, group=None):
    x = state.astype(int)
    if group is None:
        return x.diff().eq(1)
    return x.groupby(group).diff().eq(1)


def exit_state(state, group=None):
    x = state.astype(int)
    if group is None:
        return x.diff().eq(-1)
    return x.groupby(group).diff().eq(-1)


def enter_label(state, group=None, include_first=True):
    """Mark the first sample of every maximal run of one categorical label.

    Unlike :func:`enter_state`, which detects a False-to-True transition in a
    boolean predicate, this operator detects any categorical label change.
    """
    if group is None:
        entered = state.ne(state.shift(1))
        if len(entered) and not include_first:
            entered.iloc[0] = False
        return entered.astype(bool)

    grouped = state.groupby(group, sort=False)
    entered = state.ne(grouped.shift(1))
    if not include_first:
        first_in_group = grouped.cumcount().eq(0)
        entered = entered & ~first_in_group
    return entered.astype(bool)


def exit_label(state, group=None, include_last=True):
    """Mark the final sample of every maximal run of one categorical label."""
    if group is None:
        exited = state.ne(state.shift(-1))
        if len(exited) and not include_last:
            exited.iloc[-1] = False
        return exited.astype(bool)

    grouped = state.groupby(group, sort=False)
    exited = state.ne(grouped.shift(-1))
    if not include_last:
        last_in_group = grouped.cumcount(ascending=False).eq(0)
        exited = exited & ~last_in_group
    return exited.astype(bool)


def event_id(df, enter_col, group=None):
    if group is None:
        return df[enter_col].cumsum()
    return df.groupby(group)[enter_col].cumsum()


def event_index(df, event_col, group=None):
    indices = pd.Series(
        np.where(df[event_col], df.index, np.nan),
        index=df.index,
    )

    if group is None:
        return indices.ffill()

    return indices.groupby(
        _group_keys(df, group),
        sort=False,
    ).ffill()


def preceding_sample_event(event, group=None):
    """Move a transition event to the preceding sample within each group."""
    event = event.astype(bool)

    if group is None:
        return event.shift(-1, fill_value=False).astype(bool)

    return event.groupby(group, sort=False).shift(-1, fill_value=False).astype(bool)
