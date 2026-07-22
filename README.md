# FeatureGraph

FeatureGraph is a Python framework for transforming ordered observation
sequences into explicit behavioral objects.

Instead of treating a time series only as a sequence of individual
measurements, FeatureGraph constructs objects with identities, temporal
boundaries, and intrinsic measurements. The current pandas-backed alpha
release provides two object types:

- **Oscillation**, representing alternating rising and falling behavior.
- **Accumulation**, representing baseline-relative cumulative contribution
  over the lifetime of an existing oscillation.

FeatureGraph is currently an alpha research release. Oscillation and wave-derived accumulation construction are functional and tested, but behavioral definitions, boundary conventions, and output schemas may change before the first stable release. Results should be independently validated before use in production or scientific conclusions.

## Construction model

Every behavior follows the same construction lifecycle:

```text
ordered observations
        â†“
represented signal
        â†“
primitive states and events
        â†“
object identifiers
        â†“
row-aligned measurements
        â†“
one-row-per-object summary
```

`fit_transform()` returns the original observations with inspectable states,
events, identifiers, and measurements added as columns. `summarize()` returns a
DataFrame containing one row per behavioral object.

## Installation

FeatureGraph is currently installed from source:

```bash
git clone https://github.com/featuregraph/featuregraph.git
cd featuregraph
python -m pip install -e .
```

For development:

```bash
python -m pip install -e ".[dev]"
```

For the included notebooks:

```bash
python -m pip install -e ".[notebooks]"
```

## Quick start

The following example is self-contained and does not require downloading a
dataset.

```python
import pandas as pd

import featuregraph as fg


data = pd.DataFrame(
    {
        "signal": [
            0.0, 1.0, 2.0, 1.0, 0.0,
            1.0, 2.0, 1.0, 0.0,
            1.0, 2.0, 1.0, 0.0,
        ]
    }
)

oscillation = fg.oscillation.Oscillation(
    signals="signal",
    diff_lag=1,
)

oscillation_features = oscillation.fit_transform(data)
oscillation_objects = oscillation.summarize(
    oscillation_features,
    signal="signal",
)

print(oscillation_objects)
```

The input DataFrame is not modified. `oscillation_features` contains the
observation-level construction, while `oscillation_objects` contains only
complete oscillations by default.

Accumulation objects can then be constructed over the identified waves:

```python
accumulation = fg.accumulation.Accumulation(
    signals="signal",
    threshold="min",
)

accumulation_features = accumulation.fit_transform(
    oscillation_features
)

accumulation_objects = accumulation.summarize(
    accumulation_features,
    signal="signal",
)

print(accumulation_objects)
```

## Oscillation objects

An oscillation is constructed from rising and falling states. Entering the
rising state establishes a new wave identifier, and exiting the rising state
marks the peak event used by the current implementation.

```python
oscillation = fg.oscillation.Oscillation(
    signals="respiration",
    group="subject",
    smooth_signal=True,
    smooth_window=20,
    diff_lag=10,
    eps=0.0,
)
```

### Parameters

- `signals`: one signal name or a sequence of signal names.
- `group`: an optional column name or sequence of columns identifying
  independent observation sequences.
- `smooth_signal`: whether to construct the object from a rolling mean while
  retaining the observed signal.
- `smooth_window`: rolling window size in observations.
- `diff_lag`: number of observations used for directional differences.
- `eps`: nonnegative tolerance for rising and falling state detection.

### Summary schema

`Oscillation.summarize()` emits:

| Column | Meaning |
|---|---|
| grouping columns | Identity of the independent observation sequence |
| `oscillation_id` | Identifier within the observation group |
| `is_complete` | Whether the oscillation has the required boundaries and phases |
| `start_index` | Constructed start position |
| `peak_index` | Exit-rising event position |
| `end_index` | Constructed end position |
| `rise_duration` | Number of rising observations |
| `fall_duration` | Number of falling observations |
| `duration` | Rise duration plus fall duration |
| `period` | Difference between consecutive peak indices |
| `amplitude` | Half of the within-object maximum-minus-minimum range |
| `rising_mean_rate` | Signal range divided by rise duration |
| `falling_mean_rate` | Signal range divided by fall duration |
| `peak_rise_rate` | Largest positive local rate in the object |
| `peak_fall_rate` | Magnitude of the largest negative local rate in the object |
| `temporal_symmetry` | Similarity of rise and fall durations on a 0â€“1 scale |

Initial and final boundary-truncated objects are excluded by default. They can
be retained for inspection:

```python
objects = oscillation.summarize(
    oscillation_features,
    signal="respiration",
    include_partial=True,
)
```

## Accumulation objects

The current `Accumulation` implementation is wave-derived. It requires a
`<signal>_wave_id` column produced by oscillation construction and assigns one
accumulation object to each wave.

For a signal value \(x_t\) and threshold \(b_t\), the contribution is:

```text
contribution_t = x_t - b_t
```

The accumulation column is the cumulative sum of this contribution within the
parent wave.

```python
accumulation = fg.accumulation.Accumulation(
    signals="respiration",
    group="subject",
    threshold="min",
    eps=0.0,
)
```

`threshold` can be:

- a numeric constant;
- the name of a threshold column;
- a pandas aggregation name such as `"min"`;
- a mapping from signal names to any of those values.

### Summary schema

`Accumulation.summarize()` emits:

| Column | Meaning |
|---|---|
| grouping columns | Identity of the independent observation sequence |
| `accumulation_id` | Identifier inherited from the parent wave |
| `start_index` | First source index in the object |
| `end_index` | Last source index in the object |
| `duration` | Number of observations in the object |
| `baseline` | Threshold used to calculate contribution |
| `total_auc` | Sum of contribution values over the object |
| `auc_at_peak` | Cumulative contribution at the peak event |
| `accumulation_before_peak` | Contribution assigned before the peak event |
| `accumulation_from_peak` | Contribution assigned from the peak event onward |
| `accumulation_rate` | Total contribution divided by observation count |
| `accumulation_symmetry` | Balance between contribution before and after the peak |
| `centroid_time` | Contribution-weighted position within the object |
| `half_accumulation_time` | First object-relative position reaching half the total |

Despite the current `auc` column names, integration is presently a discrete
sum with an implicit sample interval of one. Physical-time integration for
irregularly sampled observations is not yet implemented.

## Input requirements and current conventions

FeatureGraph currently expects:

- a pandas DataFrame;
- one row per ordered observation;
- numeric signal columns;
- rows already sorted within each group;
- independent sequences identified through `group` when multiple sequences
  are present;
- an index suitable for the current index-based boundary calculations.

Durations and rates are measured in observations and change per observation,
not physical time. If observations have a real timestamp or irregular sampling
interval, preserve that column in the input, but do not interpret the current
duration, period, rate, or accumulation fields as time-aware measurements.

Smoothing creates a new `<signal>_smooth` column and does not replace the
observed signal. The first `smooth_window - 1` values within each group are
missing because a complete rolling window is required.

## Example datasets

FeatureGraph includes convenience loaders used by the project notebooks:

```python
bidmc = fg.datasets.bidmc(subject=1)

eastman = fg.datasets.eastman(
    fault_number=1,
    simulation_run=1,
)
```

The repository currently demonstrates the same oscillation and accumulation
interfaces on:

- [BIDMC physiological respiration signals](https://physionet.org/content/bidmc/1.0.0/);
- [Tennessee Eastman industrial process signals](https://github.com/mv-per/tennessee-eastman-dataset).

These loaders retrieve data from external sources and therefore require network
access. Users should review and follow the source datasets' attribution,
citation, and usage requirements.

## Package structure

```text
src/featuregraph/
â”œâ”€â”€ behaviors/
â”‚   â”œâ”€â”€ base.py
â”‚   â”œâ”€â”€ oscillation.py
â”‚   â””â”€â”€ accumulation.py
â”œâ”€â”€ datasets/
â”œâ”€â”€ operators/
â”œâ”€â”€ preprocessing/
â””â”€â”€ utils/
```

Most users interact with behavior constructors and dataset loaders through the
public package:

```python
import featuregraph as fg

fg.oscillation.Oscillation(...)
fg.accumulation.Accumulation(...)
fg.datasets.bidmc(...)
```

## Development

Run the automated tests:

```bash
pytest
```

Build the distribution artifacts:

```bash
python -m build
```

The test suite runs automatically on pushes and pull requests against Python
3.10, 3.11, 3.12, and 3.13.

## Project status

Current work is focused on:

- making boundary semantics explicit;
- propagating partial-object completeness into accumulation objects;
- supporting physical-time measurements and integration;
- adding transition objects;
- separating behavioral definitions from dataframe-specific execution.

## License

FeatureGraph is released under the MIT License. See [LICENSE.md](LICENSE.md).
