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
