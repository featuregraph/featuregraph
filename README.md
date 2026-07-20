# FeatureGraph

FeatureGraph is a Python framework for constructing **behavioral
objects** from observation sequences.

Project status: FeatureGraph is an early-stage research prototype. Its API, object definitions, and output schemas may change before the first stable release.

Rather than treating a time series as a sequence of independent
measurements, FeatureGraph transforms observations into explicit
behavioral objects with well-defined identities, temporal boundaries,
intrinsic measurements, and relationships. These behavioral objects
provide a structured representation of how a physical system evolves
over time.

The first release includes two behavioral object types:

-   **Oscillations**, which represent cyclic behavior.
-   **Accumulations**, which represent the accumulation of a quantity
    over the lifetime of another behavioral object.

## Behavioral Object Construction

FeatureGraph represents an observation sequence through a common
construction process.

``` text
Observation sequence
        ↓
Represented signal
        ↓
Behavioral primitives
        ↓
Behavioral object identities
        ↓
Object-relative measurements
        ↓
Behavioral object summary
```

Every behavioral object follows the same construction lifecycle while
defining its own primitives, measurements, and object schema.

## Installation

Clone the repository and install the package in editable mode.

``` bash
git clone https://github.com/featuregraph/featuregraph.git
cd featuregraph
python -m pip install -e .
```

Install development dependencies:

``` bash
python -m pip install -e ".[dev]"
```

Install notebook dependencies:

``` bash
python -m pip install -e ".[notebooks]"
```

## Quick Start

### Oscillation objects

``` python
import featuregraph as fg

oscillation = fg.oscillation.Oscillation(
    signals="reactor_temperature",
    group=["fault_number", "simulation_run"],
    smooth_signal=True,
    smooth_window=20,
)

features = oscillation.fit_transform(data)

objects = oscillation.summarize(
    features,
    signal="reactor_temperature",
)
```

The feature table contains row-level behavioral information. The summary
table contains one row per oscillation.

### Accumulation objects

Accumulation objects are constructed from previously identified
behavioral objects.

``` python
accumulation = fg.accumulation.Accumulation(
    signals="reactor_temperature",
    group=["fault_number", "simulation_run"],
    threshold="min",
)

features = accumulation.fit_transform(features)

objects = accumulation.summarize(
    features,
    signal="reactor_temperature",
)
```

Both object types share the same construction interface.

``` python
behavior.fit_transform(...)
behavior.summarize(...)
```

## Behavioral Objects

Every behavioral object implements the same construction lifecycle.

  **Signal**        -                Select or derive the represented
                                    signal

  **Primitives**     -               Construct the primitive states,
                                    events, or quantities

  **Identity**        -              Assign a unique identifier to each
                                    behavioral object

  **Measurements**     -             Compute object-relative properties

  **Summary**           -            Produce one row per behavioral object


This lifecycle is implemented by the `Behavior` base class and shared by
every behavioral object in FeatureGraph.

## Oscillation Objects

Oscillations are constructed directly from an observed signal.

Primitive states:

-   Rising
-   Falling

Event operators:

-   Enter state
-   Exit state

The resulting oscillation objects provide measurements including:

-   start
-   peak
-   end
-   rise duration
-   fall duration
-   duration
-   period
-   amplitude
-   temporal symmetry

## Accumulation Objects

Accumulations are derived from previously constructed behavioral
objects.

Rather than operating directly on the observed signal, an accumulation
first derives an accumulation signal over the parent behavioral object
and then applies the same behavioral construction framework.

Current measurements include:

-   total accumulation
-   accumulation rate
-   accumulation centroid
-   half accumulation time
-   normalized accumulation

## Package Structure

``` text
featuregraph/
├── oscillation/
├── accumulation/
├── behaviors/
├── operators/
├── preprocessing/
├── plotting/
└── utils/
```

Most users should interact only with the public APIs.

``` python
import featuregraph as fg

osc = fg.oscillation.Oscillation(...)
acc = fg.accumulation.Accumulation(...)
```

## Development

Run the test suite.

``` bash
pytest
```

Run the linter.

``` bash
ruff check .
```

Run static type checking.

``` bash
mypy src
```

Build the package.

``` bash
python -m build
```

## Research

FeatureGraph is an active research project investigating the
construction of domain-independent behavioral objects from observation
sequences.

The current implementation has been validated on:

-   physiological respiration signals (BIDMC)
-   industrial reactor temperature and pressure signals (Tennessee
    Eastman)

The long-term objective is to develop a common mathematical framework
for representing physical systems as collections of explicit behavioral
objects rather than isolated observations.

## License

FeatureGraph is released under the MIT License. See the `LICENSE` file
for details.
