# AI-use disclosure

This disclosure separates three uses of large language models in the BIDMC
respiration preservation study. They have different provenance and must not be
described as if they were one reproducible interaction.

## 1. Undocumented original exploratory session

An early LLM conversation proposed and interpreted an initial respiration
analysis. That conversation was lost before the experiment record was frozen.
The repository does not contain its transcript, model and model version,
system instructions, sampling settings, tool state, or complete inputs and
outputs.

The session is therefore historical motivation only. Results remembered or
copied from it are not used as independently reproducible evidence. The paper
may describe that an exploratory interaction occurred, but it must not claim
that another researcher can replay the model's original proposal process.

## 2. Context-isolated proposal and reproducible frozen method

A later, context-isolated LLM trial was created to establish an auditable
comparison. The model received:

- the archived subject 1 raw respiration waveform;
- the 125 Hz sampling rate;
- the required object schema and measurement contract; and
- `BLINDED_LLM_PROMPT.md`.

It did not receive FeatureGraph boundaries, parameters, object counts, tables,
or earlier comparison results. The returned object table is stored at
`results/llm_objects_subject_01.csv`, and the written method is stored at
`results/llm_method.md`.

Exact provider-side model/session metadata were not retained. Accordingly,
the LLM's *selection* of a fourth-order 0.8 Hz Butterworth filter and SciPy
peak detector cannot be reproduced as a model interaction. The selected method
itself is fully specified and implemented in `reproduce_llm_method.py`. That
deterministic implementation reproduces the frozen output without an LLM and
is covered by repository tests.

In all study materials:

- **reproducible frozen method** means the archived algorithm, parameters,
  endpoint rules, code, and outputs can be rerun;
- it does **not** mean the original LLM response can be regenerated; and
- the frozen LLM/SciPy path is a comparator, not ground truth.

## 3. Research-engineering and writing assistance

LLM tools also assisted the named researcher with code drafting, debugging,
experiment orchestration, prose revision, and identifying questions for human
review. The researcher:

- selected the research question and study scope;
- approved the object and measurement contracts;
- chose when constructions were frozen;
- executed and inspected analyses and audit tables;
- checked reported values against versioned artifacts;
- determined the interpretation and limitations; and
- accepts responsibility for the repository and manuscript.

LLMs are not authors. Model-generated prose, code, or interpretations are not
treated as evidence without verification against code, saved outputs, or cited
sources.

## Known disclosure limits

The study cannot retrospectively recover missing provider metadata for either
the lost exploratory session or the context-isolated proposal. This gap is
reported as a provenance threat. Future LLM trials should archive, subject to
provider availability and privacy constraints, the model identifier, date,
system and user prompts, tool configuration, input checksums, complete raw
response, and deterministic translation used for evaluation.
