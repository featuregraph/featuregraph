import pandas as pd


def positive_state(quantity, eps=0):
    return quantity.gt(eps)


def negative_state(quantity, eps=0):
    return quantity.lt(-eps)


def inactive_state(quantity, eps=0):
    return quantity.abs().le(eps)


def hysteresis_state(
    quantity,
    enter_eps=0,
    exit_eps=0,
    group=None,
):
    """Return a state with separate entry and exit thresholds.

    The state enters when ``quantity > enter_eps`` and exits when
    ``quantity <= exit_eps``. Values between the thresholds retain the
    preceding state. Each group starts False, including when its first
    observations are missing.
    """
    if exit_eps > enter_eps:
        raise ValueError(
            "exit_eps cannot exceed enter_eps."
        )

    commands = pd.Series(
        pd.NA,
        index=quantity.index,
        dtype="boolean",
        name=quantity.name,
    )
    commands.loc[quantity.gt(enter_eps)] = True
    commands.loc[quantity.le(exit_eps)] = False

    if group is None:
        return commands.ffill().fillna(False).astype(bool)

    return (
        commands.groupby(group, sort=False)
        .ffill()
        .fillna(False)
        .astype(bool)
    )


def rising_state(series, lag=10, eps=0):
    return positive_state(series.diff(lag), eps)


def falling_state(series, lag=10, eps=0):
    return negative_state(series.diff(lag), eps)


def accumulating_state(contribution, eps=0):
    return positive_state(contribution, eps)


def depleting_state(contribution, eps=0):
    return negative_state(contribution, eps)
