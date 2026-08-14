# BIDMC respiration experiment record

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
| Complete objects | 174 | 170 | 169 | Close aggregate agreement; object matching is pending |
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
agreement. Symmetry does not: the historical values use different contracts,
and the negative SciPy-boundary value cannot have come from the bounded
formula above.

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
before FeatureGraph summarized the objects. It therefore showed agreement
between a SciPy-boundary-plus-FeatureGraph pipeline and an independently
designed raw-data LLM analysis. It did not show that FeatureGraph natively
found the same boundaries. The current notebook removes that SciPy dependency,
but the raw LLM run preserved only aggregates, so object-level LLM comparison
remains unperformed.

## Next self-implemented detector experiment

1. Freeze the FeatureGraph parameters and all measurement contracts before
   evaluation; separate parameter selection records from evaluation subjects.
2. Give the same raw record independently to native FeatureGraph and a blinded
   LLM analysis. Neither path receives the other's boundaries or output.
3. Require both paths to emit one row per object with start, peak, end,
   completeness, peak-to-peak period, full excursion, and the bounded symmetry
   formula.
4. Match objects one-to-one under a declared boundary tolerance and report
   matched objects, extras, misses, start/peak/end error, and property error.
5. Repeat on additional BIDMC subjects and report parameter sensitivity and
   known failure cases.

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
| Reproduce the original LLM object table | Raw LLM analysis | Not yet; only aggregates were saved |

The evidence currently supports deterministic preservation and maintenance of
an explicitly encoded analysis. It does not support autonomous semantic
recognition by FeatureGraph or full object-level equivalence with the LLM.

## Running the final object-level pass

Run `python experiments/bidmc_llm_capture/prepare_blinded_trial.py`. This
creates the raw input and a hidden FeatureGraph object table under `generated/`.
In a new context-isolated LLM chat, attach only
`raw_respiration_subject_01.csv` and `BLINDED_LLM_PROMPT.md`. Do not expose the
FeatureGraph table, this README, the notebook, or prior aggregate results.

Place the returned `llm_objects_subject_01.csv` in `generated/`, then run
`python experiments/bidmc_llm_capture/compare_object_tables.py`. The comparison
writes matched rows, FeatureGraph-only rows, LLM-only rows, and a summary of
boundary and property errors. Those outputs complete the missing object-level
evidence; until the isolated LLM table exists, they must not be described as a
completed blinded comparison.
