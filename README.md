# FeatureGraph

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21984186.svg)](https://doi.org/10.5281/zenodo.21984186)

FeatureGraph is an open framework for deterministic, inspectable, and
reproducible scientific data analysis. A researcher declares what the data
contains and what should be grouped, measured, compared, and checked;
FeatureGraph executes those declared steps and retains the evidence behind each
result. Scientific interpretation remains with researchers and domain experts.

Maintained by Nazia Habib ([@habibdraft](https://github.com/habibdraft)).
FeatureGraph grew out of a decade of work on representing dynamics in
observational data — see
[Origins](https://github.com/featuregraph/featuregraph-research#origins).

FeatureGraph welcomes open-source contributions. To learn how to use
FeatureGraph, follow the [tutorial learning path](notebooks/tutorials/README.md).

## Follow the research sequence

The current research record is organized as five linked studies:

| Study | Question | Evidence |
| --- | --- | --- |
| [BIDMC respiratory objects](artifacts/studies/bidmc_object_workflow_study.md) | Can a researcher-authored contract be expanded into a complete, auditable object workflow? | Compiler-backed directional states and boundaries, 53 records, object-level comparator matching, annotation comparisons, and frozen regression checks |
| [TEP reactor-pressure transfer](artifacts/studies/tep_pressure_transfer_study.md) | Does a frozen construction transfer beyond its development run and distinguish abnormal from normal operation? | Held-out Fault 2 runs, normal-operation windows, and contrasting fault classes |
| [CLaP interoperability](artifacts/studies/clap_state_object_study.md) | Can FeatureGraph preserve states detected by an external method as queryable objects without taking over detection? | Exact label reconstruction, bounded occurrence objects, temporal relations, and declared validation checks |
| [PhysioNet wearable protocols](artifacts/studies/physionet_wearable_protocol_study.md) | Can published protocol states, source boundaries, self-reports, and native-rate wearable measurements be preserved without adding undeclared meaning? | 33 eligible participants, 248 exact protocol occurrences, lossless self-report joins, and one schema across two protocol versions |
| [Output agreement and traceability](artifacts/studies/replica_mechanism_fidelity_study.md) | Can identical outputs hide different levels of scientific traceability? | Exact sample, object, relation, and measurement agreement with deterministic provenance queries |

[Open the complete study guide](artifacts/studies/README.md).


[Visit the FeatureGraph website](https://featuregraph.ai/?utm_source=github&utm_medium=referral&utm_campaign=featuregraph_core_repository). Each record links
the researcher input, generated study, implementation evidence, and limitations.
The sequence moves from a complete in-domain workflow, through frozen transfer
and external-detector interoperability, to a focused test of scientific
traceability.

FeatureGraph turns observation-level states and events into explicit behavioral
objects. External scientific methods may perform detection; FeatureGraph adds
bounded identity, measurements, completeness, provenance, composition, and
relations without taking over the detector's scientific role.

```text
observations
    → states and events
    → object identities and boundaries
    → behavioral object tables
    → computational queries
```

> **Development status:** The `main` branch contains an unreleased architectural redesign and is not API-compatible with FeatureGraph `v0.1.0b1`. To use or reproduce the public beta, work from the immutable [`v0.1.0b1` release](https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0b1) or its compatible maintenance branch, [`beta/v0.1.x`](https://github.com/featuregraph/featuregraph/tree/beta/v0.1.x). Migration guidance will be published when the replacement API stabilizes.

## Current research studies

### 1. BIDMC: complete object workflow

The BIDMC study establishes the paired researcher-input/generated-study
workflow on 53 respiratory records. It preserves observations, directional
states, transition events, plateau-aware boundaries, complete and incomplete
objects, comparator matches, annotation comparisons, and validation evidence.
Its first compiler-backed vertical slice executes the researcher-authored
`state-contract-v1` mapping for directional states and enter/exit boundaries;
preprocessing, plateau projection, object assembly, comparison, and
interpretation remain explicit generated-study logic.

- [Study record](artifacts/studies/bidmc_object_workflow_study.md)
- [Researcher input](notebooks/researcher_input/bidmc_researcher_input.ipynb)
- [Generated study](notebooks/generated_study/bidmc_generated_study.ipynb)
- [State-contract compiler](docs/concepts/state-contracts.md)

### 2. Tennessee Eastman: frozen transfer

The TEP study freezes the reactor-pressure construction selected on Fault 2 run
10 and applies it unchanged to nine held-out Fault 2 runs, ten normal-operation
windows, and matched runs from 20 contrasting fault classes. It finds a
repeatable Fault 2-associated pressure response while showing that reactor
pressure alone is not specific to Fault 2.

- [Study record](artifacts/studies/tep_pressure_transfer_study.md)
- [Researcher input](notebooks/researcher_input/tep_researcher_input.ipynb)
- [Generated study](notebooks/generated_study/tep_generated_study.ipynb)

### 3. CLaP: external-detector interoperability

The CLaP study uses the maintained ClaSPy implementation on the Crop benchmark.
CLaP supplies the state labels; FeatureGraph preserves them as nine bounded
occurrence objects and eight adjacency relations, reconstructing all 20,700
labels exactly. FeatureGraph does not claim to detect or improve the CLaP
states.

- [Study record](artifacts/studies/clap_state_object_study.md)
- [Researcher input](notebooks/researcher_input/clap_researcher_input.ipynb)
- [Generated study](notebooks/generated_study/clap_generated_study.ipynb)
- [Construction figure](artifacts/studies/clap_crop_object_construction.png)
- [State-sequence adapter](src/featuregraph/behaviors/state_occurrence.py)

### 4. PhysioNet: published-protocol preservation

The PhysioNet wearable study follows the stress-protocol states, physical
button marks, exclusions, and self-reports published with an existing dataset.
It preserves 248 declared protocol occurrences across 33 eligible participants
and measures native-rate heart rate, electrodermal activity, and temperature
inside each occurrence. Undeclared gaps remain `unassigned`; FeatureGraph does
not claim to detect stress or validate a biomarker.

- [Study record](artifacts/studies/physionet_wearable_protocol_study.md)
- [Executable study](scripts/run_physionet_wearable_protocol_study.py)
- [Focused tests](tests/test_physionet_wearable_protocol_study.py)
- [Source dataset](https://physionet.org/content/wearable-device-dataset/1.0.1/)

### 5. Output agreement and scientific traceability

The Replica-inspired mechanism-fidelity study holds every sample label, object
boundary, relation, and signal measurement constant while varying whether the
dataset, detector, software version, and study contract are declared. It shows
that exact output agreement is compatible with materially different
traceability records; declared provenance remains evidence, not proof that a
mechanism was executed.

- [Study record](artifacts/studies/replica_mechanism_fidelity_study.md)
- [Executable study](scripts/run_replica_mechanism_fidelity_study.py)

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

## Source data, caching, and air-gapped environments

`fg.datasets.bidmc()` and `fg.datasets.eastman()` download on first use and
cache the result. Two environment variables control where that cache lives and
whether downloading is permitted at all.

| Variable | Effect |
| --- | --- |
| `FEATUREGRAPH_CACHE_DIR` | Where cached source files live. Unset, `~/.cache/featuregraph`. |
| `FEATUREGRAPH_OFFLINE` | When set, a loader that would download raises `SourceUnavailableError` instead. |

Together these make the package usable where a home directory is not writable
and outbound network access does not exist. Seed a directory from a machine
that can reach the source, mount it, and point the variable at it:

```bash
# On a machine with network access:
FEATUREGRAPH_CACHE_DIR=/data/featuregraph python -c "import featuregraph as fg; fg.datasets.bidmc(subject=1)"

# Wherever the work actually runs, with no egress:
export FEATUREGRAPH_CACHE_DIR=/data/featuregraph
export FEATUREGRAPH_OFFLINE=1
```

`FEATUREGRAPH_OFFLINE` is not only a safeguard. Behind a route that drops
packets rather than refusing them, an HTTP request does not fail — it hangs
until the timeout, once per file. Declaring the environment offline turns that
stall into an immediate error naming the file, the directory it belongs in, and
the URL it came from.

Seeding a cache is a way to avoid a download, never a way to avoid
verification. A pre-seeded file is checked against
`datasets/bidmc_manifest.json` exactly as a freshly downloaded one is, and one
that does not match is refused.

## Beta research record

The immutable beta software, evaluation artifacts, and reproduction tooling are
frozen in [`v0.1.0b1`](https://github.com/featuregraph/featuregraph/tree/v0.1.0b1).
The compatible beta research line continues on
[`beta/v0.1.x`](https://github.com/featuregraph/featuregraph/tree/beta/v0.1.x),
while the current [BIDMC study record](artifacts/studies/bidmc_object_workflow_study.md)
documents the maintained workflow on `main`.
The historical `alpha/v0.1.x` branch remains unchanged for existing links. The
immutable beta tag and its
[Zenodo archive](https://doi.org/10.5281/zenodo.21984186) remain the authority
for the released result.

## Development line

The next architecture is being developed on `main`. It centers transition summaries and revises how higher-order behaviors consume them. Its API, notebooks, and documentation may change without notice and should not be used to reproduce beta results.

Current development documentation is labeled explicitly:

- [current framework paper draft](artifacts/paper/master/featuregraph_master_draft.md);
- [development architecture](docs/behavior-architecture.md);
- [state-contract compiler](docs/concepts/state-contracts.md);
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
