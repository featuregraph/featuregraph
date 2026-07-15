def rising_state(series, lag=10, eps=0):
    return series.diff(lag).gt(eps)


def falling_state(series, lag=10, eps=0):
    return series.diff(lag).lt(-eps)
