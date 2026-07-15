def smooth(df, signal, group, window):
    return (
        df.groupby(group)[signal]
          .transform(lambda s: s.rolling(window, min_periods=window).mean())
    )