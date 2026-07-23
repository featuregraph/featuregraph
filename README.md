# FeatureGraph

FeatureGraph turns ordered observations into explicit behavioral objects that software can inspect and query.

A raw time series contains values. It may also contain oscillations, transitions, and accumulations, but those behaviors remain implicit until their states, boundaries, identities, and properties are constructed. FeatureGraph performs that construction deterministically and returns one row per behavioral object.

```text
observations
    â†’ states and events
    â†’ object boundaries and identities
    â†’ behavioral object tables
    â†’ computational queries
```

The current alpha provides oscillation objects, wave-derived accumulation objects, inspectable construction features, and a small deterministic query interface. Pandas is the reference execution model.

## Demo

This example begins with BIDMC respiration observations:

```python
import featuregraph as fg

bidmc = fg.datasets.bidmc(subject=1)
```

### Construct oscillation objects

```python
respiration = fg.oscillation.Oscillation(
    signals="respiration",
    group="subject",
    smooth_signal=False,
)

respiration_features = respiration.fit_transform(bidmc)

respiration_objects = respiration.summarize(
    respiration_features,
    signal="respiration",
)
```

`fit_transform()` constructs the sample-level representation:

- rising and falling states;
- state-entry and state-exit events;
- peak and trough locations;
- oscillation identities;
- object-relative measurements.

`summarize()` produces one row per complete oscillation.

The returned result contains both the object table and the evidence supporting its construction:

```python
respiration_objects.behavior_type
# "oscillation"

respiration_objects.signal
# "respiration"

respiration_objects.count
# 545

respiration_objects.table
# one row per oscillation

respiration_objects.features
# row-level observations, states, events, and identities

respiration_objects.construction
# parameters used during construction
```

### Query the objects

Once oscillations are explicit, downstream code can ask questions about them without detecting their boundaries again:

```python
long_oscillations = (
    respiration_objects
    .query()
    .where(duration__ge=100)
    .select(
        "oscillation_id",
        "start_index",
        "end_index",
        "duration",
        "amplitude",
    )
    .collect()
)
```

```python
long_count = len(long_oscillations)
total_count = respiration_objects.count

{
    "long_oscillations": long_count,
    "total_oscillations": total_count,
    "percentage": 100 * long_count / total_count,
}
```

Result:

```python
{
    "long_oscillations": 175,
    "total_oscillations": 545,
    "percentage": 32.11009174311927,
}
```

Of the 545 complete respiration oscillations FeatureGraph constructed, 175â€”or 32.11%â€”lasted at least 100 samples.

The query itself is deliberately simple. The important step happened earlier: FeatureGraph converted the waveform into identified oscillations with explicit boundaries and measurements. The query operates on that representation rather than rediscovering waves from raw samples.

More structural questions use the same interface:

```python
long_symmetric_oscillations = (
    respiration_objects
    .query()
    .where(
        duration__ge=100,
        temporal_symmetry__ge=0.9,
    )
    .select(
        "oscillation_id",
        "duration",
        "amplitude",
        "temporal_symmetry",
    )
    .order_by(
        "amplitude",
        ascending=False,
    )
    .collect()
)
```

This finds long respiration cycles whose rise and fall durations are nearly equal, then orders them by amplitude.

## Construct related accumulation objects

FeatureGraph can construct a wave-derived accumulation representation from the oscillation-enriched observations:

```python
accumulation = fg.accumulation.Accumulation(
    signals="respiration",
    group="subject",
)

accumulation_features = accumulation.fit_transform(
    respiration_features
)

accumulation_objects = accumulation.summarize(
    accumulation_features,
    signal="respiration",
)
```

Each accumulation object exposes properties such as baseline, total area above baseline, accumulation rate, symmetry, centroid time, half-accumulation time, and parent oscillation identity.

```python
high_accumulations = (
    accumulation_objects
    .query()
    .where(total_auc__gt=50)
    .select(
        "accumulation_id",
        "parent_oscillation_id",
        "total_auc",
        "accumulation_rate",
        "centroid_time",
    )
    .order_by(
        "total_auc",
        ascending=False,
    )
    .collect()
)
```

The current `Accumulation` implementation is wave-derived: each accumulation is constructed within the boundaries of a parent oscillation.

## Apply the same construction in another domain

The oscillation workflow is not specific to respiration:

```python
eastman = fg.datasets.eastman(
    fault_number=1,
    simulation_run=1,
)

temperature = fg.oscillation.Oscillation(
    signals="reactor_temperature",
    group=[
        "fault_number",
        "simulation_run",
    ],
    smooth_signal=True,
    smooth_window=20,
)

temperature_features = temperature.fit_transform(eastman)

temperature_objects = temperature.summarize(
    temperature_features,
    signal="reactor_temperature",
)
```

BIDMC respiration and Tennessee Eastman reactor temperature are unrelated physical signals. FeatureGraph nevertheless applies the same construction workflow and returns the same oscillation schema for both. Only the signal mapping, grouping, and optional preprocessing differ.

## Reproducibility

After the signal, grouping columns, and construction parameters are specified, FeatureGraph automatically:

1. detects primitive states;
2. locates boundary events;
3. assigns object identities;
4. distinguishes complete and boundary-truncated objects;
5. calculates intrinsic properties;
6. returns inspectable features and object tables;
7. exposes those objects to deterministic queries.

No individual peak, trough, oscillation, or accumulation is manually annotated. The same observations and parameters produce the same representation.

FeatureGraph does not assume every waveform can be interpreted without configuration. Noise, missing observations, irregular sampling, nested frequencies, and unsuitable detection parameters may require preprocessing or a revised behavioral definition.

## Why FeatureGraph?

Pandas can filter a table. FeatureGraph constructs the behavioral table that makes the filtering meaningful.

Without an explicit representation, each downstream analysis must identify waves, infer boundaries, and calculate measurements from raw samples. FeatureGraph performs that work once and exposes the result as an inspectable representation:

```text
raw samples
    â†’ explicit oscillations
    â†’ related accumulations
    â†’ ordinary computational queries
```

The resulting objects can support analysis, visualization, validation, inter-object relationships, and downstream models without hiding how they were constructed.

## Installation

```bash
git clone https://github.com/featuregraph/featuregraph.git
cd featuregraph
python -m pip install -e .
```

## Status

FeatureGraph is an alpha research release. Current development priorities include:

- transition objects;
- stronger completeness and boundary validation;
- tests across multiple signals and groups;
- additional relationships between objects;
- a clean interface for defining new behavioral object types.

The API may change while these semantics are finalized.

## License

FeatureGraph is released under the MIT License.
