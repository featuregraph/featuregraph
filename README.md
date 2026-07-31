# FeatureGraph

FeatureGraph turns ordered observations into explicit behavioral objects that software can inspect and query.

A raw time series contains values. It may also contain oscillations, transitions, and accumulations, but those behaviors remain implicit until their states, boundaries, identities, and properties are constructed. FeatureGraph performs that construction deterministically and returns one row per behavioral object.

```text
observations
    → states and events
    → object boundaries and identities
    → behavioral object tables
    → computational queries
```

This branch maintains the released FeatureGraph alpha, `v0.1.0a1`. It provides oscillation objects, wave-derived accumulation objects, inspectable construction features, and a small deterministic query interface. Pandas is the reference execution model.

> The `main` branch contains an unreleased successor architecture and is not API-compatible with this alpha.

## Install the alpha

Install the immutable release:

```bash
python -m pip install "featuregraph @ git+https://github.com/featuregraph/featuregraph.git@v0.1.0a1"
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
- [API reference](https://featuregraph.readthedocs.io/en/latest/api/index.html)
- [Demonstration notebook](https://github.com/featuregraph/featuregraph/blob/v0.1.0a1/notebooks/demo_notebook.ipynb)
- [Alpha manuscript and evidence](artifacts/paper/README.md)
- [Reproducibility guide](docs/reproducibility.md)
- [Release `v0.1.0a1`](https://github.com/featuregraph/featuregraph/releases/tag/v0.1.0a1)
- [Archived research record](https://doi.org/10.5281/zenodo.21535661)
- [Project website](https://featuregraph.ai)

## Reproduce the research artifacts

```bash
python scripts/reproduce.py
```

The command reads the versioned reproduction manifest, downloads the fixed BIDMC and Tennessee Eastman selections, reconstructs object tables, generates annotated figures, and records environment and checksum metadata. See the [reproducibility guide](docs/reproducibility.md) for details.

## Alpha maintenance policy

Changes on `alpha/v0.1.x` are limited to:

- correcting defects in released alpha behavior;
- strengthening alpha tests and reproducibility;
- completing and maintaining the alpha paper;
- improving documentation without silently changing released semantics.

New behavioral objects and successor-architecture work belong on `main`. The alpha API may receive corrections, but incompatible development is kept separate.

## Citation

If you use FeatureGraph in research, cite the archived alpha software record:

> Habib, N. (2026). *FeatureGraph* (v0.1.0a1). Zenodo. https://doi.org/10.5281/zenodo.21535661

Machine-readable citation metadata is available in [CITATION.cff](CITATION.cff).

## License

FeatureGraph is released under the MIT License.
