# Installation

## Released 0.2 beta

The compiler lineage, with `compile_states`, state contracts and the study
builder:

```bash
python -m pip install \
  "featuregraph @ git+https://github.com/featuregraph/featuregraph.git@v0.2.0b1"
```

## Released alpha

The released alpha is the supported choice for demonstrations, reproduction,
and evaluation:

```bash
python -m pip install \
  "featuregraph @ git+https://github.com/featuregraph/featuregraph.git@v0.1.0a1"
```

FeatureGraph supports Python 3.10 through 3.13.

## Editable alpha checkout

To modify or inspect the released implementation:

```bash
git clone --branch alpha/v0.1.x \
  https://github.com/featuregraph/featuregraph.git
cd featuregraph
python -m pip install -e ".[dev]"
python -m pytest
```

## Development branch

The `main` branch is a breaking, unreleased successor architecture. Install it
only when working on that redesign:

```bash
git clone https://github.com/featuregraph/featuregraph.git
cd featuregraph
python -m pip install -e ".[dev]"
```

APIs on `main` may change without migration guarantees until a replacement
release is frozen.
