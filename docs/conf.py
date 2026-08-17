"""Sphinx configuration for the FeatureGraph documentation."""

from __future__ import annotations

import os

project = "FeatureGraph"
author = "Nazia Habib"
copyright = "2026, Nazia Habib"
release = "0.1.0b1"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx_copybutton",
]

autosummary_generate = True
autodoc_typehints = "description"

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

templates_path: list[str] = []
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "/")
html_static_path: list[str] = []

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
}
