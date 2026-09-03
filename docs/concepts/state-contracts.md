# State contracts

A state contract is a small declarative program that turns an ordered observation
table into explicit state occurrences and boundary events. The compiler is
deterministic. The same observations and contract produce the same output.

The first contract version deliberately has a narrow scope:

- reference observation columns and scalar parameters;
- combine comparisons with `abs`, negation, `and`, `or`, and `not`;
- validate that named states are mutually exclusive and exhaustive;
- mark entry at the first observation in an occurrence and exit at the last;
- mark generic label changes for externally supplied categorical states;
- reset boundaries and occurrence identifiers within declared groups; and
- accept an externally produced categorical state column without relabeling it.

It does not infer scientific states from prose, select preprocessing, choose
thresholds, or decide whether a construction supports a scientific claim. Those
decisions remain in the study and are made explicit as contract inputs.

## Example

```python
import pandas as pd

from featuregraph import compile_states

observations = pd.DataFrame({"rate": [-1.0, 0.0, 1.0, 1.0]})
rate = {"column": "rate"}
eps = {"parameter": "eps"}

contract = {
    "version": "state-contract-v1",
    "parameters": {"eps": 0.1},
    "states": {
        "rising": {"op": "gt", "left": rate, "right": eps},
        "falling": {
            "op": "lt",
            "left": rate,
            "right": {"op": "neg", "value": eps},
        },
        "inactive": {
            "op": "le",
            "left": {"op": "abs", "value": rate},
            "right": eps,
        },
    },
    "events": {
        "enter_rising": {"type": "enter_state", "state": "rising"},
        "exit_rising": {"type": "exit_state", "state": "rising"},
    },
    "validation": {"exclusive": True, "exhaustive": True},
}

result = compile_states(observations, contract)
result.observations
result.validation_report
```

For an existing categorical construction, replace `states` with
`"state_column": "the_external_column"`. FeatureGraph preserves those label
values, derives occurrences and requested events, and reports structural checks.
Use `{"type": "enter_label"}` or `{"type": "exit_label"}` for boundaries at
every categorical label change, regardless of the label value.

## Version 2: the derivation inside the contract

`state-contract-v2` accepts everything v1 accepts and adds two things. v1 is
frozen: a v1 contract compiles exactly as before, and a v1 contract that uses
either addition is refused with the code `operator_requires_v2`.

### `derive`

An ordered mapping of new column names to expressions. Each is evaluated in
declaration order, within each declared group, and becomes a column of the
output. A later derivation may reference an earlier one. A derived name may
not shadow an input column or a column the compiler writes.

Beyond the v1 expression forms, a v2 expression may use:

- `rolling_max`, `rolling_mean`, `rolling_min`, with `window` and an optional
  `min_periods` (default: the full window);
- `shift`, with `periods` (negative looks ahead);
- `diff`, with an optional `periods` (default 1);
- `add`, `sub`, `mul`, `div`, with `left` and `right`.

`window` and `periods` are integers, or scalar expressions such as a
`parameter` or its `neg`.

### `missing_policy: "exclude"`

A window or a shift has nothing to say at the edges of a series, so a
derivation leaves missing values there. Under `"error"`, still the default,
those rows are a data failure. Under `"exclude"`, every row on which a column
the states read is missing stays outside the partition: it carries no state,
no occurrence identifier, and no event; `state_valid` is `False` on it; and
the validation report counts the excluded rows as leading, trailing, or
interior. Row count and order are preserved. An interior gap does not split an
occurrence. It is counted so that the choice stays visible, not made silently.

### Example: the BIDMC respiratory envelope

The published BIDMC and TEP studies build a rolling envelope in pandas and
compile only its first difference. That left the scientific content of the
construction outside the fingerprinted contract. Under v2 the whole
construction is one document:

```python
window = {"parameter": "smooth_window"}
contract = {
    "version": "state-contract-v2",
    "group_by": "subject_id",
    "missing_policy": "exclude",
    "parameters": {"smooth_window": 100, "numerical_atol": 1e-12},
    "derive": {
        "respiration_smooth": {
            "op": "shift",
            "value": {
                "op": "rolling_mean",
                "value": {
                    "op": "rolling_max",
                    "value": {"column": "respiration"},
                    "window": window,
                },
                "window": window,
            },
            "periods": {"op": "neg", "value": window},
        },
        "respiration_change": {"op": "diff", "value": {"column": "respiration_smooth"}},
    },
    "states": {...},   # rising / falling / inactive over respiration_change
    "events": {...},
}
```

`artifacts/contracts/` holds this contract and its TEP counterpart.
`scripts/verify_derived_contracts.py` runs each against the source records
alongside the published preprocess-then-compile path and reports, per record,
whether the derived columns, states, occurrences, and events are identical.
