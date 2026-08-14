# BIDMC LLM analysis capture experiment

Status: protocol development; preliminary single-record results  
Dataset: BIDMC PPG and Respiration Dataset, subject 1  
Sampling rate: 125 Hz  
FeatureGraph line: alpha `v0.1.x`

## Research question

How much of an analysis proposed and executed by an LLM can a researcher transfer into deterministic, inspectable FeatureGraph objects that remain executable and maintainable without continued LLM access?

This experiment does not test whether FeatureGraph autonomously recognizes respiration or oscillation. FeatureGraph has no semantic knowledge of either. The researcher supplies the transition, boundary, object, inclusion, and measurement contracts.

## Capture workflow

1. An LLM independently analyzes the raw respiration record.
2. The researcher inspects the proposed objects and measurements.
3. Accepted analytical structure is encoded as explicit FeatureGraph states, boundaries, objects, and properties.
4. FeatureGraph executes the saved construction deterministically.
5. FeatureGraph and LLM results are compared at boundary, object, and summary levels.
6. The saved construction is tested on held-out BIDMC records without record-specific retuning.

## Preliminary results

| Measure | Self-implemented detector | SciPy-boundary FeatureGraph | Raw-data LLM | Current interpretation |
| --- | ---: | ---: | ---: | --- |
| Duration | 479.1 s | 479.1 s | 480.0 s | Different coverage conventions |
| Complete candidate cycles | 176 | 170 | 169 | Native detector still has extra candidates |
| Rate | 22.0/min | 21.3/min | 21.1/min | Corrected SciPy and LLM runs strongly agree |
| Mean period | 2.72 s | 2.82 s | 2.818 s | Corrected SciPy and LLM runs strongly agree |
| Mean amplitude | 0.441 | 0.452 | 0.906 | FeatureGraph appears to report half-range; contract not yet finalized |
| Temporal symmetry | -0.626 | -0.550 | 0.857 | Definitions are not comparable |

The earlier 553-object result was a segmentation error and is not evidence against the representation. With corrected SciPy boundaries, FeatureGraph and the independent raw-data LLM run converged on essentially the same cycle count, rate, and period.

For amplitude, `2 * 0.452 = 0.904`, nearly matching the raw-data LLM's peak-to-trough value of `0.906`. This is treated as a likely definition mismatch until the FeatureGraph amplitude formula is documented formally.

Symmetry is excluded from agreement claims until both analyses use the same bounded formula and the same rise/fall boundaries.

## Current deterministic boundary contract

```python
rising = respiration.diff(45) > 0.15
peak_candidate = rising.shift(1, fill_value=False) & ~rising
wave_id = peak_candidate.cumsum()
```

This rule reduced the earlier fragmentation from 553 objects to 176 complete candidate objects. The parameters are a researcher-specified definition of relevant signal change; FeatureGraph does not infer them or decide which candidates are physiologically meaningful.

## Representation

The experiment exercises a transferable construction rather than a respiration-specific semantic primitive:

```text
observations
-> change states
-> accumulation objects
-> peak boundaries
-> complete/incomplete cycle objects
-> intrinsic properties and population summaries
```

Cycle objects preserve period, amplitude, phase timing, and completeness. Accumulation objects preserve bounded intervals of sustained positive or negative impedance-signal change inside the waveform. Their magnitude and duration describe signal excursions and phase timing, not calibrated inhaled or exhaled air volume.

## Methodological limitation

The corrected baseline used SciPy `find_peaks` with a 1.5-second minimum distance and 0.15 prominence, then supplied those boundaries to FeatureGraph. That run validates FeatureGraph object construction and summarization given external boundaries; it does not establish independent boundary discovery.

The current `diff(45) > 0.15` construction removes the active SciPy detector but remains a preliminary candidate-boundary rule.

## Frozen next evaluation

Before the detector is treated as validated:

- freeze `diff=45` and `eps=0.15`;
- match self-implemented, SciPy-reference, and BIDMC annotated boundaries one-to-one under a declared timing tolerance;
- report matched, missed, and extra boundaries plus timing offsets;
- compare complete/incomplete objects, period, and harmonized amplitude object by object;
- identify whether extra candidates arise from shoulders, small waves, or endpoint conventions;
- test the fixed construction on held-out BIDMC subjects without record-specific retuning;
- retain accumulation subobjects so internal waveform structure remains inspectable;
- keep symmetry outside agreement claims until its contract is harmonized.

## Claim boundary

The supported target claim is:

> An analysis proposed through LLM-assisted exploration can be transferred by a researcher into an explicit, deterministic, domain-independent object representation that preserves useful analytical functionality and remains reusable without continued LLM access.

The experiment does not claim autonomous semantic recognition, automatic selection of meaningful peaks, or clinical validation.
