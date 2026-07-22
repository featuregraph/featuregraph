def smooth(df, signal, group, window):
    if group is None:
        return df[signal].rolling(
            window,
            min_periods=window,
        ).mean()

    return (
        df.groupby(group)[signal]
          .transform(lambda s: s.rolling(window, min_periods=window).mean())
    )
