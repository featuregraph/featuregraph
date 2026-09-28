# FeatureGraph Digital Science Catalyst Grant 2026

**Applicant:** Nazia Habib

## 1. The Problem

An AI agent asked to analyze a physiological or industrial signal makes dozens of choices nobody sees: how much to smooth, what counts as a peak, where an interval starts and ends. Those choices change the answer, and today they are buried in generated code.

The people affected are researchers and institutions who analyze time-series data (wearables, patient monitoring, industrial sensors) and the analysts who must defend the results. Today they write bespoke code for each study, or hand the task to a code-writing model and inspect what comes back. Either way the analysis specification stays invisible. The cost is results that are difficult to reproduce and review time spent reverse-engineering code.

## 2. Your Workflow

FeatureGraph is a deterministic compiler that turns a timeseries signal into explicit events and intervals (breaths, protocol steps, process excursions) from rising, falling, and inactive states. The same configuration on the same data always produces the same objects.

1. Characterize (autonomous, no model): Estimates each recording's own period from autocorrelation, derives its smoothing window from that period, and flags recordings with no stable period.
2. Construct (autonomous, no model): The compiler builds the objects and stores them in a database. Each row carries its construction parameters, a configuration fingerprint, the dataset version, the sampling rate, and the software version.
3. Query (model): A language model chooses among five deterministic tools: aggregate, outlier statistics, filter, characterization lookup, and outlier co-occurrence. Every count, comparison, and outlier judgment is computed in code, over only the recordings that step 1 confirmed.
4. Review (human): A researcher judges which detected events reflect the phenomenon under study. 

## 3. Trust, Audit and Governance

What the agent did: Each stored object carries its configuration fingerprint and construction parameters, so a reviewer can see exactly what was computed and rerun it. 

Provenance: Inputs are public datasets used under their published terms. Each study publishes its construction parameters and results so a third party can rerun it.

Uncertainty: The system declines to guess. Where results were checked against two independent human experts, both the result and the ceiling those experts set for each other are reported together, not just the result on its own.

Accountability: No model sits in the execution path, so every error traces to a versioned construction. The person who reviews the results is accountable for that judgment.

## 4. Team

I am the sole founder. I have a computer science degree and about eight years of experience as a data scientist, most recently at a drilling services and automation company, which I left to build FeatureGraph full time. I wrote *Hands-On Q-Learning with Python* (Packt, 2019).

I chose this problem because I could run essentially the same state and event detection across unrelated studies and get parallel, meaningful results. The core finding is that a small, domain-blind vocabulary of sign tests can start that analysis from a signal's own shape, with all domain knowledge supplied in the construction. The same code has run on respiration waveforms and on a chemical-process simulation, among other domains.

## 5. Where You Are Today

Stage: working prototype with published studies. No paying users yet.

What exists:
- A public, MIT-licensed extract of the construction code that reproduces the smoothing paper's results: https://github.com/featuregraph/featuregraph-smoothing-core. The current compiler, database, and query layer are private while I decide what to release.
- A persistent database with BIDMC and CapnoBase populated and their cross-study comparability validated. Tennessee Eastman process data is in progress.
- A query interface with five tools, built on Cohere models under a grant from Cohere Labs (August 2026).
- Validation against human experts: for 32 BIDMC subjects with two independent annotators, recall across three timing tolerances. https://github.com/featuregraph/featuregraph-smoothing-core/blob/main/artifacts/paper/compiler/smoothing.md

How I have tested the idea: the compiler against human annotation, and its structure across two datasets. The agent-reliability harness is built: eight questions, three conditions (no tools, tools, hardened tools), ten repeats each, with a question counted correct only if all ten repeats are correct. That all-repeats rate is the outcome metric. The harness has been tested only against mock models; runs against live models are the next stage.

## 6. Alternatives and Competitors

Today's default is bespoke code, where the specification stays implicit. Biosignal toolkits such as NeuroKit2 (https://github.com/neuropsychology/NeuroKit) and change-point libraries such as ruptures (https://github.com/deepcharles/ruptures) are mature open-source tools, but parameters are tuned per dataset and nothing checks the specification; ruptures can score a completed segmentation against ground truth, but nothing checks whether the smoothing choice that produced it was justified. Workflow systems such as Galaxy (https://galaxyproject.org) record what ran, not whether the segmentation was structurally sound. Code-writing analysis agents from large AI companies are fast, but the specification lives in generated code and shifts between runs.

FeatureGraph differs in three ways: the compiler's construction guarantees validity rather than checking it afterward, it keeps models out of the execution path, and it reports which subjects it cannot analyze.

## 7. Where This Goes

A researcher or agent proposes an analysis of time-series data and gets deterministic, reproducible events back, from a database that spans studies and domains (respiration, wearables, industrial process). At least one to two tiers of access will stay free for researchers.

I plan to charge organizations for hosted compute, private datasets, and custom validated studies, with healthcare AI validation as the first commercial focus. Pricing is not set.

## 8. Fit with Digital Science

FeatureGraph sits in discovery (data analysis) and research integrity (auditable, reproducible analysis decisions), serving researchers and institutions. I would value introductions to institutions and research-integrity teams who need auditable analysis, and direct feedback from a team that builds research infrastructure.

## 9. Budget

- £15,000: protected development time to harden the validation layer and run the reliability evaluation across open and hosted models
- £4,000: compute and model costs for replication across models

I fund my time independently today, which limits how much evaluation I can run. The grant would produce independent evidence on how reliably models work through FeatureGraph and keep the public database free for researchers.
