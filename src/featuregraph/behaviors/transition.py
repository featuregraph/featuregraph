import pandas as pd

from featuregraph.behaviors.base import Behavior, Group, Signals
from featuregraph.operators.events import (
    enter_state,
    event_id,
    event_index,
    exit_state,
)
from featuregraph.operators.states import (
    falling_state,
    rising_state,
    positive_state,
    negative_state,
    inactive_state
)
from featuregraph.preprocessing.smoothing import smooth


class Transition():
    def __init__(
        self,
        signals: Signals,
        group: Group = None,
        diff_lag: int = 10,
        eps: float = 0.0
    ):

        if diff_lag < 1:
            raise ValueError('diff_lag must be at least 1')
        if eps < 0: 
            raise ValueError('eps cannot be negative')

        self.diff_lag = diff_lag
        self.eps = eps

    def classify_direction(self, df, direction, op):
        for signal in self.signals:
            # signal is positive, negative, or inactive
            direction_col = f'{signal}_{direction}'
            df[direction_col] = op(difference, self.eps)

    def add_start_and_end():
        pass
    
    def add_features():
        # rate of change
        # total time
        # etc
        pass