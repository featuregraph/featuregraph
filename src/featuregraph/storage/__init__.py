"""Persistence backends for FeatureGraph object data.

This package is deliberately separate from the construction layer
(:mod:`featuregraph.behaviors`, :mod:`featuregraph.contracts`). Constructing
objects is deterministic and requires no external service; persisting them is
an explicit, optional step a study takes when it wants object data to outlive
one process. Importing this package does not require a database driver —
only importing a specific backend (for example
:mod:`featuregraph.storage.postgres`) does.
"""
