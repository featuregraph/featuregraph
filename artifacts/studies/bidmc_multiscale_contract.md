# Frozen BIDMC multiscale cardiac-phase contract

This contract was fixed after exploratory inspection of subjects 13, 19, 23,
and 33 and before cardiac-phase analysis of the other 49 BIDMC records.

## Cohorts

- Development: subjects 13, 19, 23, and 33.
- Held out: every subject from 1 through 53 not in the development set.

## Respiratory representations

Construct FeatureGraph objects independently with rolling windows 79 and 100.
All other preprocessing, numerical tolerance, state, event, plateau, identity,
and completeness rules remain unchanged. Match complete objects across windows
by peak index with the existing ordered one-to-one objective: maximize matches,
then minimize total absolute error, subject to a 63-sample tolerance.

- Shared: a W=79 object matched to a W=100 object.
- W=79-only: a complete W=79 object not matched to W=100.

## ECG event construction

For ECG leads II, V, and AVR independently:

1. Apply a fourth-order zero-phase Butterworth band-pass filter from 5 to 20 Hz.
2. Take the absolute value of the filtered lead.
3. Detect peaks with SciPy `find_peaks`, minimum distance 63 samples and
   prominence equal to 0.5 times the full-record standard deviation of the
   absolute filtered signal.
4. Use lead II as the primary R-event series. Leads V and AVR are validation
   series only.

The 63-sample refractory distance limits valid analysis to monitor heart rates
below 119 beats/min. A record is ECG-valid only when:

- its monitor heart-rate values are present and remain below 119 beats/min;
- the absolute difference between ECG-derived and monitor median heart rate is
  no greater than 5 beats/min; and
- at least 90% of lead-II events lie within 10 samples of an event in either
  lead V or AVR.

Records failing these gates remain in the coverage table but are excluded from
cardiac-phase inference. No alternative lead or parameter is selected afterward.

## Cardiac phase

For every respiratory-object peak bracketed by consecutive lead-II R events:

`phase = (respiratory_peak - preceding_R) / (following_R - preceding_R)`

Phase concentration is the circular resultant length, from zero (diffuse) to
one (identical cardiac phase). Calculate it separately for shared and W=79-only
objects within each ECG-valid subject. Require at least five eligible objects
for a class-specific concentration estimate.

## Annotation relationship

A W=79-only peak is annotation-supported when either BIDMC annotation series
contains an event within 63 samples. This is a relationship, not a truth label.

## Frozen outcomes

Primary held-out outcome: the subject-level difference
`R(W=79-only) - R(shared)`. Report its distribution and the number of subjects
with a positive difference; do not tune parameters from the held-out result.

Secondary outcomes:

- W=79-only counts and concentration by subject;
- annotation-supported fraction;
- median W=79-only object rate and monitor heart rate;
- ECG-valid coverage and every exclusion reason.

The analysis tests whether objects introduced by the shorter scale are more
cardiac-phase-concentrated. It does not assume that every W=79-only object is
cardiogenic or that every shared object is a validated breath.
