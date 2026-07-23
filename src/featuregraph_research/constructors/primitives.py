from dataclasses import dataclass
from typing import Any, Callable
from featuregraph_research.operators.states import rising_state, falling_state
from featuregraph_research.operators.events import enter_state, exit_state, event_index

@dataclass
class TransitionPrimitives:
    state: Any
    enter: Any
    exit: Any
    start_index: Any
    end_index: Any

@dataclass
class OscillationPrimitives:
    rising: TransitionPrimitives
    falling: TransitionPrimitives
    trough_index: Any
    peak_index: Any


def transition_primitives(values, state_op: Callable, diff_lag: int, eps: float):
    state = state_op(values, diff_lag, eps)
    enter = enter_state(state)
    exit = exit_state(state)

    return TransitionPrimitives(
        state=state,
        enter=enter,
        exit=exit,
        start_index=event_index(enter),
        end_index=event_index(exit)
    )


def oscillation_primitives(values, diff_lag=10, eps=0):
    rising = transition_primitives(
        values=values,
        state_op=rising_state,
        diff_lag=diff_lag,
        eps=eps
    )

    falling = transition_primitives(
        values=values,
        state_op=falling_state,
        diff_lag=diff_lag,
        eps=eps
    )

    return OscillationPrimitives(
        rising=rising,
        falling=falling,
        trough_index=rising.start_index,
        peak_index=rising.end_index
    )