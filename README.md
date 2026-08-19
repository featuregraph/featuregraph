# FeatureGraph

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21984186.svg)](https://doi.org/10.5281/zenodo.21984186)

> ## Start with the public beta
>
> **The released, public-facing project is [`v0.1.0b1`](https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0b1).**
>
> 1. [Open the beta release](https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0b1)
> 2. [Run the BIDMC reconstruction notebook](https://github.com/featuregraph/featuregraph/blob/v0.1.0b1/notebooks/bidmc_respiration_pipeline.ipynb)
> 3. [Read the beta paper draft](https://github.com/featuregraph/featuregraph/blob/beta/v0.1.x/artifacts/paper/bidmc_llm_preservation_study/manuscript.md)
>
> Compatible maintenance continues on
> [`beta/v0.1.x`](https://github.com/featuregraph/featuregraph/tree/beta/v0.1.x).
> The historical `alpha/v0.1.x` branch remains available for old links. The
> `main` branch is an unreleased successor architecture and is not the
> recommended visitor path.

FeatureGraph studies how an LLM-assisted analysis can become a deterministic, inspectable computational record, so the code, method, assumptions, and evidence remain available after the conversation is gone.

```text
observations
    → states and events
    → object identities and boundaries
    → behavioral object tables
    → computational queries
```

> **Development status:** The `main` branch contains an unreleased architectural redesign and is not API-compatible with FeatureGraph `v0.1.0b1`. To use or reproduce the public beta, work from the immutable [`v0.1.0b1` release](https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0b1) or its compatible maintenance branch, [`beta/v0.1.x`](https://github.com/featuregraph/featuregraph/tree/beta/v0.1.x). Migration guidance will be published when the replacement API stabilizes.

## Released beta

FeatureGraph `v0.1.0b1` provides:

- explicit oscillation objects;
- wave-derived accumulation objects;
- retained sample-level construction evidence;
- one-row-per-object summary tables;
- a deterministic query interface;
- BIDMC and Tennessee Eastman dataset loaders;
- reproducibility scripts, tests, and archived artifacts.

The release constructs observations into states and events, assigns object identities, distinguishes complete from boundary-truncated objects, calculates intrinsic properties, and exposes the resulting tables to downstream queries.

## Quick start

Install the released beta:

```bash
python -m pip install   "featuregraph @ git+https://github.com/featuregraph/featuregraph.git@v0.1.0b1"
```

Or clone the compatible maintenance line:

```bash
git clone --branch beta/v0.1.x   https://github.com/featuregraph/featuregraph.git
cd featuregraph
python -m pip install -e ".[dev]"
python -m pytest
```

The beta API constructs oscillations from grouped observations:

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

See the [beta demo notebook](https://github.com/featuregraph/featuregraph/blob/v0.1.0b1/notebooks/demo_notebook.ipynb) for oscillation, accumulation, query, BIDMC, and Tennessee Eastman examples.

## Beta research record

The immutable beta software, evaluation artifacts, and reproduction tooling are
frozen in [`v0.1.0b1`](https://github.com/featuregraph/featuregraph/tree/v0.1.0b1).
The corresponding [beta paper draft](https://github.com/featuregraph/featuregraph/blob/beta/v0.1.x/artifacts/paper/bidmc_llm_preservation_study/manuscript.md)
and compatible research line continue on
[`beta/v0.1.x`](https://github.com/featuregraph/featuregraph/tree/beta/v0.1.x).
The historical `alpha/v0.1.x` branch remains unchanged for existing links. The
immutable beta tag and its
[Zenodo archive](https://doi.org/10.5281/zenodo.21984186) remain the authority
for the released result.

## Development line

The next architecture is being developed on `main`. It centers transition summaries and revises how higher-order behaviors consume them. Its API, notebooks, and documentation may change without notice and should not be used to reproduce beta results.

Current development documentation is labeled explicitly:

- [current framework paper draft](artifacts/paper/master/featuregraph_master_draft.md);
- [development architecture](docs/behavior-architecture.md);
- [unreleased changes](CHANGELOG.md);
- [current source](https://github.com/featuregraph/featuregraph/tree/main).

The governing version policy is:

| Reference | Purpose |
| --- | --- |
| `v0.1.0b1` | Immutable released and citable beta |
| `beta/v0.1.x` | Compatible maintenance line for the beta API |
| `alpha/v0.1.x` | Frozen historical alpha branch |
| `main` | Breaking, unreleased successor architecture |

FeatureGraph supports Python 3.10 through 3.13 and is released under the MIT License.
