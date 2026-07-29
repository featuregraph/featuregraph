def group_transform(df, signal, op, group):
    return df.groupby(group)[signal].transform(op)

def group_map(df, signal, op, group, offset=0):
    return df[group].map(df.groupby(group)[signal].agg(op).shift(offset))

def rate_of_change(df, signal):
    return df[signal].diff()