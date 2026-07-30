from collections.abc import Mapping

import numpy as np
import pandas as pd

from featuregraph.behaviors.base import Behavior, Group, Signals
from featuregraph.behaviors.objects import BehaviorObjects
from featuregraph.operators.events import (
    enter_state,
    event_id,
    exit_state,
    preceding_sample_event,
)
from featuregraph.operators.states import (
    inactive_state,
    negative_state,
    positive_state,
)

from featuregraph.operators.measures import (
    rate_of_change
)

class Transition():

    def __init__(self, df, signal, direction, op, group=None, diff_lag=1, eps=0.0):
        state_col = f'{signal}_{direction}'
        enter_state_col = f'enter_{signal}_{direction}' 
        exit_state_col = f'exit_{signal}_{direction}' 
        rate_of_change_col = f'{signal}_{direction}_rate_of_change'
        id_col = f'{signal}_id'

        df[state_col] = op(df[signal], eps=0)
        df[enter_state_col] = enter_state(df[f'{signal}_{direction}'])
        df[exit_state_col] = exit_state(df[f'{signal}_{direction}'])
        df[rate_of_change_col] = rate_of_change(df, signal)

        df[id_col] = event_id(df, enter_state_col, group)


        self.df = df
        self.group = group
        self.signal = signal
        self.id_col = id_col
        self.state_col = state_col
        self.rate_of_change_col = rate_of_change_col

    def summary(self):
        summarydf = self.df.groupby(self.id_col).agg(
            duration=(self.state_col, 'sum'),
            start_value=(self.signal, 'first'),
            end_value=(self.signal, 'last'),
            peak_rate_of_change=(self.rate_of_change_col, 'max')
        )

        summarydf['net_change'] = summarydf['end_value'] - summarydf['start_value']
        summarydf['mean_rate'] = summarydf['net_change'] / summarydf['duration']

        return summarydf

# transition_id
# state
# start_index
# end_index
# start_value
# end_value
# state_duration
# interval_duration
# net_change
# change_magnitude
# mean_rate
# peak_rate
# has_start_boundary
# has_end_boundary