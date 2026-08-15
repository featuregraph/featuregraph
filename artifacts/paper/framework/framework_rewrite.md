# Framework

## Motivation

The research question behind this study is: "If large language model (LLM) access were gone tomorrow, what could researchers maintain from their LLM-assisted analyses?" 

A researcher using an LLM for data analysis can produce useful results, but an LLM interaction is not a persistent computational representation of that analysis. Much of the output of the work exists in prompts, generated code, ad hoc parameter tuning, and both human and LLM interpretation that cannot be easily recreated to perform the analysis again without LLM assistance. 

If the researcher needed to run a similar study, they would need to consult the LLM again, or often design their own bespoke analysis that incorporated their own expertise and that might not be reproducible by others.

## Representation

A timeseries signal can be described using this taxonomy:

1. Intrinsic behavior

This consists of: 
- the literal raw values that compose the sampled signal
- the direction and curvature estimated from changes in the signal along its timeseries and value axis
- its transitions and turning points

The FeatureGraph position is: If observed signal morphology can be described in a contract that can then be used to identify corresponding characteristics in multiple signals, the analytical procedure has become durable, inspectable, and testable for transfer.

2. Measurement and representation frame

This consists of:
- the physical units a signal is expressed in
- its sampling interval and temporal granularity
- the duration of each observation
- normalizing and smoothing that have been applied to the signal
- sensor resolution and preprocessing
- measured characteristics such as amplitude, rate of change, symmetry, and accumulation

Representation frame makes up the second layer of timeseries signal taxonomy. It specifies the context that cannot be removed from the signal while retaining information extraction.

3. Semantic or physical context

This consists of:
- what the signal represents
- which physical mechanism produced it
- what domain it belongs to
- what causal meaning and structure the engineer believes it contains

Semantic context explicitly exists outside the scope of FeatureGraph. It will not be asked to understand what a signal means in the real world to an observer or researcher. Its goal is to deliver a representation of the signal that does not include semantic context.

## Durability, inspectability, and transfer

A representation system can take explicit information from a timeseries signal and make it explicit. The quality of the representation system can be measured using the following criteria: 

Durability

Can the same declared analysis be executed later without the LLM? The analysis should run and produce coherent behavioral objects of the same structure as the original analysis.

Inspectability

Can a human see and revise how states, boundaries, objects, and measurements were defined? A human should be able to modify and rerun the code, edit its assumptions and contract, and identify structural limitatons with the representation. 

Transfer

Does the same contract produce useful objects on new data without case-specific modification? We can measure this in the correctness of the representation when applied to unobserved test data.


