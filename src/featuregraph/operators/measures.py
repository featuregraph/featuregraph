def group_transform(df, signal, op, group):
    return df.groupby(group)[signal].transform(op)

def group_map(df, signal, op, group, offset=0):
    return df[group].map(df.groupby(group)[signal].agg(op).shift(offset))

def rate_of_change(df, signal):
    return df[signal].diff()

def signal_measure(df, signal, group_op, group, signal_op):
    group_measure = group_transform(df, signal, group_op, group)
    signal_value = getattr(df[signal], signal_op)()
    return group_measure == signal_value