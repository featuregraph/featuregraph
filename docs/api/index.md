# Alpha API

The public alpha namespace exposes:

- `featuregraph.oscillation` for oscillation construction;
- `featuregraph.accumulation` for wave-bounded accumulation construction;
- `featuregraph.datasets` for the demonstration datasets;
- `featuregraph.plot` for plotting constructed behaviors.

The authoritative implementation is the immutable
[`v0.1.0b1` source tree](https://github.com/featuregraph/featuregraph/tree/v0.1.0b1).
The [demonstration notebook](https://github.com/featuregraph/featuregraph/blob/v0.1.0b1/notebooks/demo_notebook.ipynb)
shows the complete construction and query workflow.

The alpha dataset namespace includes `bidmc()`, `eastman()`, `cartpole()`, and
`mountaincar()` trajectory loaders. See [Datasets](../datasets.md) for their
schemas and oscillation/accumulation workflows.

```{note}
Transition construction belongs to the unreleased successor architecture on
`main`; it is not part of the `v0.1.0b1` public API.
```
