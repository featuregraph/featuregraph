## Abstract

Large language models (LLMs) can propose and orchestrate useful data analyses, but an LLM interaction is not itself a durable computational representation of a data analysis. This study asks: if LLM access disappeared, how much of an LLM-assisted time-series analysis could a researcher continue to run, inspect, validate, and maintain? It proposes FeatureGraph, a framework for deterministic preservation and repeatable execution of LLM-driven analysis.

A context-isolated LLM received one raw respiration record from the BIDMC PPG and Respiration Dataset and produced a documented SciPy pipeline and an object table of trough–peak–trough cycles. The human researcher then encoded an independently specified, deterministic transition representation in FeatureGraph, constructing boundaries from a grouped rolling-maximum/rolling-mean envelope and represented exact flat extrema as bounded intervals with midpoint projections.

On the development record, 169 of 169 complete LLM objects matched FeatureGraph objects within 0.5 seconds. Typical period and full-excursion measurements agreed closely, while temporal symmetry remained sensitive to different trough semantics.
