# Framework

## Motivation

The research question behind this study is: "If large language model (LLM) access were gone tomorrow, what could researchers maintain from their LLM-assisted analyses?" 

A researcher using an LLM for data analysis can produce useful results, but an LLM interaction is not a persistent computational representation of that analysis. Much of the output of the work exists in prompts, generated code, ad hoc parameter tuning, and both human and LLM interpretation that cannot be easily recreated to perform the analysis again without LLM assistance. 

If the researcher needed to run a similar study, they would need to consult the LLM again, or often design their own bespoke analysis that incorporated their own expertise and that might not be reproducible by others.

## Representation

A timeseries signal can be described using this taxonomy:

1. Observed data

This consists of:
- sampled values and their ordering

2. Construction contract

This consists of: 
- rules that identify states, transitions, boundaries, and objects

The FeatureGraph position is: If observed signal morphology can be described in a contract that can then be used to identify corresponding characteristics in multiple signals, the analytical procedure has become durable, inspectable, and testable for transfer.

3. Representation frame

This consists of:
- the physical units a signal is expressed in
- its sampling interval and temporal resolution
- the duration of each observation
- normalizing and smoothing that have been applied to the signal
- sensor resolution and preprocessing

Representation frame makes up the third layer of timeseries signal taxonomy. It specifies the context that must be recorded to interpret and compare measurements from the signal while retaining information extraction.

4. Measurement contract

This consists of:

- how measured characteristics such as amplitude, rate of change, symmetry, and accumulation are calculated

5. Semantic or physical context

This consists of:
- what the signal represents
- which physical mechanism produced it
- what domain it belongs to
- what causal meaning and structure the engineer believes it contains

Semantic context explicitly exists outside the scope of FeatureGraph. It will not be asked to understand what a signal means in the real world to an observer or researcher. FeatureGraph may retain user-supplied labels and metadata, but object construction does not depend on FeatureGraph inferring their physical or domain meaning.

## Durability, inspectability, and transfer

A representation system can convert analytical decisions that were implicit in an LLM-assisted workflow into an explicit, executable contract. The quality of the representation contract can be measured using the following criteria: 

1. Durability

Can the same declared analysis be executed later without the LLM? The analysis should produce reproducible objects from the constructed contract on frozen inputs.

2. Inspectability

Can a human see and revise how states, boundaries, objects, and measurements were defined? A human should be able to modify and rerun the code, edit its assumptions and contract, and identify structural limitations with the representation. 

3. Transfer

Does the same contract produce useful objects on new data without case-specific modification? We can measure this in:
- whether the contract runs unchanged
- whether it produces structurally valid objects
- whether those objects agree with an independent reference or annotation


