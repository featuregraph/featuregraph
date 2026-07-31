# Alpha quickstart

This example uses the immutable `v0.1.0a1` API.

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

The construction retains both the object table and the sample-level evidence:

```python
objects.table
objects.features
objects.construction
```

Once the oscillations are explicit, query their properties without detecting
their boundaries again:

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

Pandas can filter a table. FeatureGraph constructs the behavioral table that
makes the filtering meaningful.

For the full example, see the
[alpha demonstration notebook](https://github.com/featuregraph/featuregraph/blob/v0.1.0a1/notebooks/demo_notebook.ipynb).
