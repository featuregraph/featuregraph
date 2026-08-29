# Cohere conversational study demo

This local browser demonstration turns a researcher conversation into an
explicitly approved FeatureGraph study and linked Markdown artifacts. Cohere
proposes the language and structured decisions; it cannot approve or execute a
study. FeatureGraph validates and runs the approved contract deterministically.

The first bounded demonstration uses the protected, network-free PhysioNet
wearable fixture. It proves the interaction and execution path without exposing
source participant data or presenting fixture values as physiological results.

## Run it

Install the study-builder dependencies from the repository root:

```bash
python -m pip install -e ".[dev,study-builder]"
export COHERE_API_KEY="your-key"
python -m scripts.run_conversational_study_demo --open
```

Without a key, or for a completely network-free run:

```bash
python -m scripts.run_conversational_study_demo --offline --open
```

The console prints the local URL and output directory. The browser links every
conversation checkpoint, candidate specification, approved contract, results
summary, and comparison produced during the session.

## Three-minute demonstration

1. Enter: `How can the two protocol versions share one inspectable representation?`
2. Answer the clarification: `Yes, exactly. Preserve those boundaries.`
3. Open `specification_candidate_v1.md`, then select **Approve and run**.
4. Open `results_v1.md`.
5. Enter: `For the next version, keep only sample counts and medians.`
6. Review and approve version 2.
7. Open `comparison_v1_to_v2.md`.

Version 2 changes the reported measurements without changing the 248 declared
protocol occurrences. This makes the conversational revision visible while
preserving researcher authority and deterministic execution.

## Deliberate limits

- One maintained study template
- One local researcher session
- No arbitrary uploads or generated Python
- No autonomous scientific interpretation
- No production identity, security, or collaboration layer
