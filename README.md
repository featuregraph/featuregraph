# FeatureGraph

FeatureGraph is a Python framework for transforming observation sequences into explicit behavioral objects.

Instead of treating a time series only as a sequence of individual measurements, FeatureGraph constructs higher-level objects—such as oscillations—with defined temporal boundaries, intrinsic measurements, and relationships to other objects.

The initial release focuses on oscillation construction.

```python
import featuregraph as fg

oscillation_table = fg.oscillate(X)
```

The result is a table containing one row per oscillation and a standardized set of measurements such as start, peak, end, rise duration, fall duration, total duration, period, amplitude, and temporal symmetry.

## Why FeatureGraph?

Oscillatory information is present in a signal but is usually implicit. A downstream analysis must repeatedly identify wave boundaries, locate peaks and troughs, and derive measurements before it can reason about individual oscillations.

FeatureGraph performs that construction once and exposes the result through a consistent object representation:

```text
observations
    ↓
primitive states
    ↓
transition events
    ↓
object identifiers
    ↓
behavioral objects
    ↓
object measurements
```

The same construction procedure is intended to operate across unrelated physical domains. Domain-specific differences appear in the values of the resulting measurements rather than in the definition of the object itself.

## Installation

Clone the repository and install it in editable mode:

```bash
git clone https://github.com/featuregraph/featuregraph.git
cd featuregraph
python -m pip install -e .
```

Install development dependencies with:

```bash
python -m pip install -e ".[dev]"
```

For notebook and plotting dependencies:

```bash
python -m pip install -e ".[notebooks]"
```

## Quick start

### Construct oscillations from a pandas Series

```python
import featuregraph as fg

oscillation_table = fg.oscillate(df["respiration"])
```

### Construct oscillations from a DataFrame

```python
oscillation_table = fg.oscillate(
    df,
    signal="reactor_pressure",
    group=["fault_number", "simulation_run"],
    smooth=True,
)
```

The output schema is designed to remain stable across signals and domains:

```text
oscillation_id
start_index
peak_index
end_index
rise_duration
fall_duration
duration
period
amplitude
temporal_symmetry
```

## Transformer interface

FeatureGraph also provides a configurable transformer-style interface for reusable workflows:

```python
from featuregraph.oscillation import OscillationTransformer

transformer = OscillationTransformer(
    smooth=True,
    include_incomplete=False,
)

oscillation_table = transformer.transform(
    df,
    signal="reactor_pressure",
    group=["fault_number", "simulation_run"],
)
```

The functional and transformer interfaces use the same underlying construction algorithm.

## Package structure

```text
featuregraph/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── featuregraph/
│       ├── __init__.py
│       ├── oscillation/
│       │   ├── __init__.py
│       │   ├── _functional.py
│       │   ├── _transformer.py
│       │   └── _validation.py
│       ├── accumulation/
│       ├── operators/
│       │   ├── states.py
│       │   ├── events.py
│       │   └── measures.py
│       └── plotting/
├── tests/
└── examples/
```

Implementation modules prefixed with an underscore are private. Users should import from the public package namespaces:

```python
import featuregraph as fg
from featuregraph.oscillation import OscillationTransformer
```

## Development

Run the test suite:

```bash
pytest
```

Run the linter:

```bash
ruff check .
```

Run static type checking:

```bash
mypy src
```

Build the package:

```bash
python -m build
```

## Current research status

The first FeatureGraph research milestone is the construction of domain-independent oscillation objects. The current implementation is being validated using:

- BIDMC physiological respiration signals
- Tennessee Eastman industrial reactor-pressure signals

The same state, event, segmentation, and measurement operators are used in both domains. Future work will extend the framework to accumulation objects, multi-signal interactions, and relationships among behavioral objects.

## License

FeatureGraph is released under the MIT License. See [LICENSE](LICENSE) for details.
