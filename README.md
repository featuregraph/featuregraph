# FeatureGraph

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21535661.svg)](https://doi.org/10.5281/zenodo.21535661)

FeatureGraph turns ordered observations into explicit behavioral objects that software can inspect and query.

A time series contains values, but behaviors such as oscillations and accumulations remain implicit until their states, boundaries, identities, and properties are constructed. FeatureGraph performs that construction deterministically and returns inspectable object tables.

```text
observations
    → states and events
    → object identities and boundaries
    → behavioral object tables
    → computational queries
```

> **Development status:** The `main` branch contains an unreleased architectural redesign and is not API-compatible with FeatureGraph `v0.1.0a1`. To use or reproduce the public alpha, work from [`alpha/v0.1.x`](https://github.com/featuregraph/featuregraph/tree/alpha/v0.1.x) or the immutable [`v0.1.0a1` release](https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0a1). Migration guidance will be published when the replacement API stabilizes.

## Released alpha

FeatureGraph `v0.1.0a1` provides:

- explicit oscillation objects;
- wave-derived accumulation objects;
- retained sample-level construction evidence;
- one-row-per-object summary tables;
- a deterministic query interface;
- BIDMC and Tennessee Eastman dataset loaders;
- reproducibility scripts, tests, and archived artifacts.

The release constructs observations into states and events, assigns object identities, distinguishes complete from boundary-truncated objects, calculates intrinsic properties, and exposes the resulting tables to downstream queries.

## Quick start

Install the released alpha:

```bash
python -m pip install   "featuregraph @ git+https://github.com/featuregraph/featuregraph.git@v0.1.0a1"
```

Or clone the maintained alpha line:

```bash
git clone --branch alpha/v0.1.x   https://github.com/featuregraph/featuregraph.git
cd featuregraph
python -m pip install -e ".[dev]"
python -m pytest
```

The alpha API constructs oscillations from grouped observations:

```python
import featuregraph as fg

bidmc = fg.datasets.bidmc(subject=1)

oscillation = fg.oscillation.Oscillation(
    signals="respiration",
    group="subject",
    smooth_signal=False,
)

features = oscillation.fit_transform(bidmc)
objects = oscillation.summarize(features, signal="respiration")
```

The result retains both representations:

```python
objects.table         # one row per oscillation
objects.features      # observations, states, events, and identities
objects.construction  # construction parameters
```

Once objects are explicit, downstream code can query them without detecting boundaries again:

```python
long_oscillations = (
    objects.query()
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

Pandas can filter a table. FeatureGraph constructs the behavioral table that makes the filtering meaningful.

See the [alpha demo notebook](https://github.com/featuregraph/featuregraph/blob/v0.1.0a1/notebooks/demo_notebook.ipynb) for oscillation, accumulation, query, BIDMC, and Tennessee Eastman examples.

## Reproducibility and evaluation

The alpha research record is tied to `v0.1.0a1`, not to the changing `main` branch.

```bash
git clone --branch v0.1.0a1 --depth 1   https://github.com/featuregraph/featuregraph.git
cd featuregraph
python -m pip install -e ".[dev]"
python scripts/reproduce.py
```

The release reconstructs the fixed BIDMC and Tennessee Eastman examples and records environment, timing, and checksum metadata. The synthetic evaluation materials were also produced against the alpha API and should not be silently regenerated with the development architecture.

See the [alpha reproducibility guide](https://github.com/featuregraph/featuregraph/blob/v0.1.0a1/docs/reproducibility.md), [evaluation notebook](notebooks/evaluation_notebook.ipynb), and [evaluation artifacts](artifacts/paper/evaluation/).

FeatureGraph `v0.1.0a1` is archived under the [version DOI 10.5281/zenodo.21535662](https://doi.org/10.5281/zenodo.21535662). Use the [concept DOI 10.5281/zenodo.21535661](https://doi.org/10.5281/zenodo.21535661) to refer to FeatureGraph across versions.

## Development line

The next architecture is being developed on `main`. It centers transition summaries and revises how higher-order behaviors consume them. Its API, notebooks, and documentation may change without notice and should not be used to reproduce alpha results.

Current development documentation is labeled explicitly:

- [development architecture](docs/behavior-architecture.md);
- [unreleased changes](CHANGELOG.md);
- [current source](https://github.com/featuregraph/featuregraph/tree/main).

The governing version policy is:

| Reference | Purpose |
| --- | --- |
| `v0.1.0a1` | Immutable released and citable alpha |
| `alpha/v0.1.x` | Usable maintenance line for the alpha API |
| `main` | Breaking, unreleased successor architecture |

FeatureGraph supports Python 3.10 through 3.13 and is released under the MIT License.
