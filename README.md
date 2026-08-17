# FeatureGraph

FeatureGraph turns ordered observations into explicit behavioral objects that software can inspect and query.


## Start here

**1. Run the worked example:** [BIDMC respiration behavioral-object notebook](notebooks/bidmc_respiration_pipeline.ipynb)

This clean, executable notebook walks from a raw respiration waveform to explicit transition states, oscillation objects, accumulation objects, validation checks, and a deterministic summary. To run it, clone this branch, install the development environment as shown below, and execute the notebook from top to bottom.

**2. Read the study:** [From LLM-Proposed Analysis to Maintainable Behavioral Objects](https://github.com/featuregraph/featuregraph/blob/alpha/v0.1.x/artifacts/paper/bidmc_llm_preservation_study/manuscript.md)

The paper draft asks what remains maintainable when an LLM-assisted analysis is converted into an explicit computational representation. It reports what the BIDMC experiment preserved, where the representation transferred, and where the boundary rule failed.

> Short path: **install the alpha → run the notebook → inspect the paper and stored evidence.**

A raw time series contains values. It may also contain oscillations, transitions, and accumulations, but those behaviors remain implicit until their states, boundaries, identities, and properties are constructed. FeatureGraph performs that construction deterministically and returns one row per behavioral object.

```text
observations
    → states and events
    → object boundaries and identities
    → behavioral object tables
    → computational queries
```

This branch maintains the released FeatureGraph alpha, `v0.1.0a2`. It provides oscillation objects, wave-derived accumulation objects, inspectable construction features, and a small deterministic query interface. Pandas is the reference execution model.

> The `main` branch contains an unreleased successor architecture and is not API-compatible with this alpha.

## Install the alpha

Install the immutable release:

```bash
python -m pip install "featuregraph @ git+https://github.com/featuregraph/featuregraph.git@v0.1.0a2"
```

For development against the alpha maintenance branch:

```bash
git clone --branch alpha/v0.1.x --single-branch \
  https://github.com/featuregraph/featuregraph.git
cd featuregraph
python -m pip install -e ".[dev]"
python -m pytest
```

## Minimal example

```python
import featuregraph as fg

bidmc = fg.datasets.bidmc(subject=1)

builder = fg.oscillation.Oscillation(
    signals="respiration",
    group="subject",
)

features = builder.fit_transform(bidmc)
objects = builder.summarize(features, signal="respiration")

long_oscillations = (
    objects.query()
    .where(duration__ge=100)
    .select("oscillation_id", "duration", "amplitude")
    .collect()
)
```

`fit_transform()` retains sample-level observations, states, events, and identities. `summarize()` produces one row per complete oscillation. Queries operate on that explicit representation instead of detecting behavioral boundaries again.

## Documentation and research record

- [Alpha documentation](https://featuregraph.readthedocs.io/)
- [Quickstart](https://featuregraph.readthedocs.io/en/latest/quickstart.html)
- [Datasets](https://featuregraph.readthedocs.io/en/latest/datasets.html)
- [API reference](https://featuregraph.readthedocs.io/en/latest/api/index.html)
- [Demonstration notebook](https://github.com/featuregraph/featuregraph/blob/v0.1.0a2/notebooks/demo_notebook.ipynb)
- [Alpha manuscript and evidence](artifacts/paper/README.md)
- [Reproducibility guide](docs/reproducibility.md)
- [Release `v0.1.0a2`](https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0a2)
- [Archived research record](https://doi.org/10.5281/zenodo.21939319)
- [Project website](https://featuregraph.ai)

## Reproduce the research artifacts

```bash
python scripts/reproduce.py
```

The command reads the versioned reproduction manifest, downloads the fixed BIDMC and Tennessee Eastman selections, reconstructs object tables, generates annotated figures, and records environment and checksum metadata. See the [reproducibility guide](docs/reproducibility.md) for details.

## Living alpha research line

The alpha is not frozen. It remains an active research line for asking how well the existing oscillation and accumulation workflow transfers to additional datasets and physical domains.

Work on `alpha/v0.1.x` may:

- add stable datasets and cross-domain demonstrations;
- evaluate oscillation and accumulation behavior under new conditions;
- compare object schemas, measurements, robustness, and failure modes;
- strengthen tests, provenance, and reproducibility;
- correct defects without silently changing released semantics;
- extend the alpha manuscript with evidence from this line of research.

Architectural redesign, successor object models, and incompatible API development belong on `main`. The distinction is between extending the alpha's empirical reach and extending its architecture.

## Citation

If you use FeatureGraph in research, cite the archived alpha software record:

> Habib, N. (2026). *FeatureGraph* (v0.1.0a2). Zenodo. https://doi.org/10.5281/zenodo.21939319

Machine-readable citation metadata is available in [CITATION.cff](CITATION.cff).

## License

FeatureGraph is released under the MIT License.
