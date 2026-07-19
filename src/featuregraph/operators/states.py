def positive_state(quantity, eps=0):
    return quantity.gt(eps)


def negative_state(quantity, eps=0):
    return quantity.lt(-eps)


def inactive_state(quantity, eps=0):
    return quantity.abs().le(eps)


def rising_state(series, lag=10, eps=0):
    return positive_state(series.diff(lag), eps)


def falling_state(series, lag=10, eps=0):
    return negative_state(series.diff(lag), eps)


def accumulating_state(contribution, eps=0):
    return positive_state(contribution, eps)


def depleting_state(contribution, eps=0):
    return negative_state(contribution, eps)
