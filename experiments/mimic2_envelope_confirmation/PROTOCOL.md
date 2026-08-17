# MIMIC-II envelope/plateau confirmation protocol

Protocol frozen before examining confirmation outcomes, August 17, 2026.

## Question

Does the frozen FeatureGraph rolling-envelope construction with exact plateau
midpoint projection reproduce its improvement over the leading-edge envelope
construction on untouched MIMIC-II impedance-respiration windows?

This is a comparator-transfer confirmation. It is not clinical validation:
the additional MIMIC-II windows do not include the two manual breath annotation
series distributed with the curated BIDMC dataset.

## Frozen constructions

The experiment uses the FeatureGraph v0.1.0b1 implementation without changing
its construction or comparison parameters:

- sampling rate: 125 Hz;
- window length: 60,001 samples (the BIDMC eight-minute convention);
- envelope: grouped rolling maximum over 100 samples followed by a rolling
  mean over 100 samples and an offline alignment shift of -100 samples;
- leading-edge construction: `envelope`;
- confirmation construction: `envelope_plateau`;
- plateau projection: floor midpoint of each exact-flat extremum interval;
- frozen SciPy comparator: fourth-order 0.8 Hz Butterworth low-pass filter,
  zero-phase filtering, minimum peak distance 188 samples, and prominence
  0.08;
- one-to-one ordered matching tolerance: 63 samples.

The comparison is run on physical RESP values decoded using each WFDB header's
gain and baseline. No amplitude normalization, interpolation, smoothing change,
threshold tuning, or record-specific correction is permitted.

## Deterministic cohort selection

1. Read subject directories from the public MIMIC-II Matched Waveform Database
   index and sort their `sNNNNN` identifiers lexicographically.
2. Exclude every MIMIC-II subject identifier named in the 53 curated BIDMC
   `Fix.txt` files.
3. Consider the remaining subjects in order.
4. Within a subject, consider layout families and segment headers in
   lexicographic order.
5. A segment is eligible when:
   - its sampling rate is exactly 125 Hz;
   - it contains a channel named exactly `RESP`;
   - it contains at least 60,001 samples;
   - all channels use one shared WFDB data file and a uniform supported format
     (`16` or `80`); and
   - the first 60,001-sample RESP window contains no WFDB invalid sentinel.
6. Select the first eligible segment for each subject and stop after the first
   20 eligible subjects.

Network failures abort discovery rather than causing a subject to be skipped.
The selection audit records every considered subject and the reason it was
selected or excluded.

## Outcomes

The following directional criteria are declared before running the cohort:

1. Plateau midpoint projection preserves the number of FeatureGraph detected
   peak events in every selected window.
2. Cohort-wide matched objects do not decrease relative to leading-edge
   projection.
3. Cohort-wide SciPy-only objects do not increase.
4. Median absolute matched-peak error is lower with plateau midpoint
   projection.

The experiment also reports complete-object counts, FeatureGraph-only objects,
SciPy-only objects, matched fractions, period error, full-excursion error,
symmetry error, ambiguous objects, invalidated complete objects, and all
per-subject results. No record is removed based on detector performance.

## Interpretation boundary

Passing the directional criteria confirms that the representation correction
transfers to untouched records from the BIDMC source environment. It does not
establish that either detector identifies clinically valid breaths, and it
does not classify detector-discordant candidate episodes.
