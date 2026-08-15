# BIDMC respiration experiment record

The frozen multi-subject result is recorded in `MULTI_SUBJECT_RESULTS.md`.
The scale-adaptive subject 5 hysteresis test is recorded in
`HYSTERESIS_RESULTS.md` and reproduced by `hysteresis_ablation.py`.
The completed absolute-versus-MAD study and its interpretation are incorporated
into `artifacts/paper/bidmc_llm_preservation_study/manuscript.md`. Exact paired
cohort statistics are reproduced by `compare_scaling_runs.py`.

Study governance is recorded separately:

- [`AI_USE_DISCLOSURE.md`](AI_USE_DISCLOSURE.md) distinguishes the lost
  exploratory LLM conversation, the context-isolated proposal, and the
  deterministic frozen method.
- [`DEVELOPMENT_TRANSFER_PROTOCOL.md`](DEVELOPMENT_TRANSFER_PROTOCOL.md)
  defines which records were used for development, frozen transfer, and post
  hoc diagnosis, and specifies the protocol required for the transition-only
  successor study.

## Question

If LLM access disappeared, how much of an LLM-proposed time-series analysis
could a researcher continue to run, inspect, and maintain? This experiment
tests a deterministic handoff: an LLM proposes a raw-signal analysis, a
researcher encodes an explicit behavioral representation in FeatureGraph, and
the encoded path can subsequently run without an LLM.

FeatureGraph does not recognize respiration, infer that a waveform is
oscillatory, or know which peaks matter. The researcher supplies the meaning
and parameters. FeatureGraph applies those rules deterministically, exposes
the resulting boundaries, handles incomplete endpoint objects, and computes
documented object properties.

## Subject 1 record

The current native construction uses the BIDMC subject 1 respiration channel
at 125 Hz with no smoothing, `diff_lag=45`, `eps=0.15`, and
`max_state_gap=7`. The last parameter closes only short False runs bounded by
rising states; it removes one spurious split at the start of the inspected
window. All parameters are preserved in `BehaviorObjects.construction`.

| Measure | Native FeatureGraph | Prior SciPy-boundary FeatureGraph | Raw-data LLM run | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Coverage | 476.8 s | 479.1 s | 480.0 s | Different coverage definitions |
| Complete objects | 174 | 170 | 169 | Close aggregate agreement; resolved below at object level |
| Objects/minute | 21.9 | 21.3 | 21.1 | Close aggregate agreement |
| Mean period | 2.740 s | 2.82 s | 2.818 s | Close aggregate agreement |
| Mean radius amplitude | 0.443 | 0.452 | — | LLM did not report this convention |
| Mean full excursion | 0.886 | 0.904 | 0.906 | Comparable after converting radius to full excursion |
| Mean temporal symmetry | 0.584 | -0.550 | 0.857 | Prior and LLM definitions are not comparable |

The native run detects 175 candidate peaks and returns 176 objects: 174
complete trough–peak–trough objects and two endpoint fragments. Against each
of the two BIDMC annotation columns, one-to-one matching within 0.5 seconds
(63 samples) matches all 170 annotations, leaves five native detections
unmatched, and misses none. Median absolute boundary error is 8 samples for
annotator 1 and 7 for annotator 2; the maxima are 39 and 26 samples,
respectively. This annotation
check evaluates the native boundary rule, not agreement with the LLM.

## Blinded object-level comparison

A context-isolated LLM received only the frozen raw waveform and measurement
contract. It independently selected a fourth-order 0.8 Hz Butterworth filter,
then SciPy `find_peaks` with 188-sample minimum distance and 0.08 prominence on
the filtered signal and its negation. It returned 169 complete objects and one
trailing partial object. No FeatureGraph boundaries, parameters, counts, or
prior results were available to that run.

Complete objects were matched once each, in temporal order, when peak indices
were within 63 samples (0.5 seconds).

| Object-level measure | FeatureGraph | Blinded LLM | Comparison |
| --- | ---: | ---: | --- |
| Complete objects | 174 | 169 | Five FeatureGraph-only; zero LLM-only |
| Matched objects | 169 (97.1%) | 169 (100%) | Every LLM object matched |
| Mean period, matched objects | 2.802 s | 2.821 s | Median absolute error 0.040 s |
| Mean full excursion, matched objects | 0.896 | 0.903 | Median absolute error 0.00489 |
| Mean temporal symmetry, matched objects | 0.596 | 0.844 | Median absolute error 0.250 |

Peak alignment is strong: the median absolute peak error is 10 samples
(0.080 seconds), and the maximum is 29 samples (0.232 seconds). All 169 LLM
objects therefore match well inside the declared tolerance. The five unmatched
FeatureGraph peaks are 7443, 7797, 8296, 8531, and 14354. Both annotation
series also leave five native candidates unmatched in the same event
neighborhoods, supporting a localized over-segmentation diagnosis rather than
cancellation hidden by aggregate means. Exact peak identity inside those
neighborhoods depends on the one-to-one matching objective when multiple
native candidates fall within tolerance; the multi-subject record corrects
the earlier stronger claim that both annotators exclude the exact same five
indices.

Trough boundaries agree less closely. FeatureGraph starts and ends are a
median 53 samples (0.424 seconds) from the filtered local troughs selected by
the LLM, and FeatureGraph boundaries are systematically later. This explains
the remaining symmetry disagreement even though both paths now use the same
bounded formula: temporal symmetry is highly sensitive to boundary semantics.
Typical period and full-excursion measurements agree closely, while their
largest errors occur near the five additional FeatureGraph transitions.

## Measurement contracts

- Complete object: strictly ordered trough, peak, and next trough. Partial
  endpoint objects are retained but excluded from complete-object statistics.
- Coverage: inclusive span from the first returned start to the last returned
  end. Rate is complete objects divided by this coverage.
- Period: distance between consecutive peak indices.
- Amplitude: half of within-object maximum minus minimum. Full excursion is
  twice this value.
- Temporal symmetry:
  `1 - abs(rise_duration - fall_duration) / duration`, bounded in `[0, 1]`.

The cycle count, rate, period, and converted amplitude show genuine aggregate
and object-level agreement. The historical symmetry values used different
contracts. After harmonization, symmetry still does not agree because the two
detectors place trough boundaries differently.

## Accumulation representation

For each complete oscillation, FeatureGraph also constructs an accumulation
object: the discrete area of the waveform above the object's trough-derived
baseline. Its properties include total area, area before and after the peak,
accumulation symmetry, centroid time, and half-accumulation time. These enrich
the transferable representation, but they are waveform-shape measurements;
the normalized BIDMC channel does not justify interpreting them as calibrated
inhaled or exhaled volume.

## Methodological limitation

The earlier corrected comparison used SciPy `find_peaks` to assign boundaries
before FeatureGraph summarized the objects. It therefore did not show that
FeatureGraph natively found the same boundaries. The completed comparison now
uses FeatureGraph's native transition construction on one side and a blinded
LLM-selected SciPy pipeline on the other. SciPy remains a conventional
dependency of the LLM baseline, but it no longer supplies FeatureGraph's
boundaries.

## Frozen multi-subject evaluation

The frozen constructions have now been applied to all 53 BIDMC subjects;
subjects 2–53 are the held-out transfer cohort. FeatureGraph matches 6,031 of
6,999 complete baseline objects, but also produces 2,755 unmatched objects and
misses 968. The median subject-level matched fractions are 78.5% of native
FeatureGraph objects and 99.1% of baseline objects. Annotation checks confirm
that the subject 1 absolute threshold does not transfer uniformly: it
over-segments many records and severely under-detects several others.

See [MULTI_SUBJECT_RESULTS.md](MULTI_SUBJECT_RESULTS.md) for the full transfer
record, boundary and property errors, annotation comparison, limitations, and
reproduction command. The next detector study should define a scale-adaptive
transition contract on a declared development subset and evaluate it once on
a held-out subset without subject-specific tuning.

## Capability ledger

| Capability | Source today | Runs without LLM access? |
| --- | --- | --- |
| Choose respiration as the phenomenon of interest | Researcher/LLM question | Choice must already be recorded |
| Select `diff_lag`, `eps`, and `max_state_gap` | Researcher, after visual inspection | Yes |
| Construct directional states and boundaries | FeatureGraph | Yes |
| Retain and label incomplete objects | FeatureGraph | Yes |
| Compute oscillation and accumulation properties | FeatureGraph | Yes |
| Render the same tables and plots | FeatureGraph/notebook | Yes |
| Judge whether detected peaks are physiologically meaningful | Human or domain-aware analysis | No |
| Preserve the blinded LLM object table and method | Saved experiment results | Yes |
| Reproduce the blinded LLM detector | Recorded SciPy pipeline | Yes; numerically verified |

The evidence supports deterministic preservation, auditability, and
maintenance of an explicitly encoded analysis. Subject 1 supports strong
object-level agreement, but the full cohort shows that the current native
parameterization is not transferable enough to claim general equivalence.
Determinism preserves an explicit rule; it does not make a subject-specific
rule general or give FeatureGraph autonomous semantic recognition.

## Reproducing the object-level pass

Run `python experiments/bidmc_llm_capture/prepare_blinded_trial.py`. This
creates the raw input and a hidden FeatureGraph object table under `generated/`.
In a new context-isolated LLM chat, attach only
`raw_respiration_subject_01.csv` and `BLINDED_LLM_PROMPT.md`. Do not expose the
FeatureGraph table, this README, the notebook, or prior aggregate results.

The frozen outputs and method are retained under `results/`. To repeat the
trial, place a returned `llm_objects_subject_01.csv` in `generated/`, then run
`python experiments/bidmc_llm_capture/compare_object_tables.py`. The comparison
writes matched rows, FeatureGraph-only rows, LLM-only rows, and a summary of
boundary and property errors. Run
`python experiments/bidmc_llm_capture/reproduce_llm_method.py` to reproduce the
LLM's fully documented detector without further LLM access.
