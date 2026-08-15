# Framework

## Motivation

The research question behind this study is: "If large language model (LLM) access were gone tomorrow, what could researchers maintain from their LLM-assisted analyses? An LLM conversation can produce a useful analysis, but a conversation is not a durable computational representation of the analysis. 

A researcher using an LLM for data analysis can produce useful results, but an LLM interaction is not a persistent computational representation of that analysis. If the researcher needed to run a similar study, they would need to consult the LLM again, or often design their own bespoke analysis that incorporated their own expertise and that might not be reproducible by others.

## Representation

A timeseries signal can be described using this taxonomy:

1. Intrinsic behavior

This consists of: 
- the literal raw values that compose the signal
- the direction and curvature of the visual representation of the signal along its timeseries and value axis
- its transitions and turning points
- measured characteristics such as amplitude, rate of change, symmetry, and accumulation

The FeatureGraph position is: If intrinsic signal behaviors can be defined in a contract that can then be used to identify corresponding characteristics in unrelated signals, this suggests an constructable durability of physical signal definition and encourages generalization about physical signals by exposing their commonalities. 

2. Measurement and representation frame

This consists of:
- the physical units a signal is expressed in
- its sampling interval and temporal granularity
- the duration of each observation
- normalizing and smoothing that have been applied to the signal
- sensor resolution and preprocessing

Representation frame makes up the second layer of timeseries signal taxonomy. It specifies the non-visual context that cannot be removed from the signal while retaining information extraction.

3. Semantic or physical context

This consists of:
- what the signal represents
- which physical mechanism produced it
- what domain it belongs to
- what causal meaning and structure the engineer believes it contains

Semantic context explicitly exists outside the scope of FeatureGraph. It will not be asked to understand what a signal means in the real world to an observer or researcher. Its goal is to deliver a representation of the signal that does not include semantic context.


