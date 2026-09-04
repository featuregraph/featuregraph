# Every W=79 peak against the W=100 peaks and the ECG, all 53 BIDMC subjects

This directory holds one table per subject written by
`scripts/inspect_bidmc_region.py --peaks` at framework commit `c6376ea`
(the merge of PR #82), and a one-row-per-subject summary derived from them by
`scripts/summarize_bidmc_peak_measures.py`. The tables were produced outside
continuous integration, because PhysioNet is not reachable from it, and
committed directly (commit `84131c8`).

It is an audit of the frozen multiscale study, not a replacement for it. The
study's numbers in `bidmc_multiscale_heldout/subject_summary.csv` are the
published ones. What this adds is the quantity the study does not report: the
lag, in samples, from each object peak to the R-peak before it, for every
peak at W=79, matched or not, over the whole hour of every record.

## What each row measures

For every exit-rising event at W=79 under the published v2 contract:

- `nearest_coarse_peak`, `matched`: distance to the nearest W=100 exit-rising
  event, and whether it is within the study's 63-sample tolerance. Unmatched
  rows are the objects the paper calls W=79-only.
- `r_lag`: samples from the preceding lead-II R-peak, using the study's
  detector.
- `cardiac_phase`: that lag as a fraction of the RR interval, the study's
  phase definition. NaN where the peak is not bracketed by two R-peaks.
- `breath_phase`: position between the bracketing W=100 peaks, zero at a
  W=100 peak.

## How this differs from the frozen study

The two constructions count and place peaks differently, so their numbers
agree in pattern and not to the unit.

| | Frozen study | These tables |
| --- | --- | --- |
| Object | trough to trough, complete objects only | every exit-rising event |
| Peak position | midpoint of the envelope's flat run | the exit sample |
| Matching | one-to-one optimal assignment within 63 samples | any W=100 peak within 63 samples |
| Peaks at W=79, all subjects | 8,780 | 8,900 |
| W=79-only, all subjects | 862 | 912 |

The extra peaks here are the incomplete and plateau-ambiguous objects the
study excludes. Counts agree exactly in 16 subjects and differ by one to
nineteen in the rest; subject 27 differs most, with 19 more peaks here.

## Result

**The same subjects are locked.** Among the 45 ECG-valid subjects, 24 have at
least five unmatched peaks with a phase. Nine of them have an unmatched
resultant of 0.9 or more: subjects 6, 9, 13, 19, 23, 30, 31, 32 and 50. The
frozen study reports the same eight subjects that reach five objects under its
stricter count; subject 30 has six unmatched peaks here and four objects
there. No subject is locked in one construction and not the other.

**Subject 13 is the only record where the matched peaks are locked too.** Its
matched resultant is 0.937 here and 0.946 in the study. No other ECG-valid
subject has a matched resultant above 0.75. In subject 13 every peak the
compiler finds at either window sits 39 samples, 0.31 s, after an R-peak,
with an interquartile range of 3 samples across 421 peaks and one hour. The
next tightest records are subjects 19 (4.5 samples) and 45 (8 samples). The
cohort median is 30.

**The lag does not drift.** In subject 13 the first and second half-hours give
median lags of 38 and 39 samples, and a straight line fitted to lag against
time has a slope under one sample per hour. The nine peaks with lags outside
30 to 60 samples are all matched peaks: breaths whose envelope exit fell
between two bumps.

**Where the W=79-only peaks sit differs between locked subjects.** In subject
13, 163 of 197 unmatched peaks are one RR interval from a W=100 peak and the
remaining 26 are two, at breath phases from 0.23 to 0.76 and never nearer a
W=100 peak than that. They are the first and second cardiac bumps after a
breath peak, on the falling limb; the bump before the next breath peak is
never kept, because the rising limb absorbs it. In subject 9, by contrast,
none of the 74 unmatched peaks is one RR interval from a W=100 peak, and all
sit at breath phases between 0.42 and 0.55, mid-breath. Both are locked to
the ECG at 0.95 or better. Phase locking says where a peak sits in the
cardiac cycle; it does not say where it sits in the breath, and the two
records answer that second question differently.

## What this does and does not change

The paper's held-out result is untouched: it was computed by the frozen study
from a frozen contract, and the counts and resultants here reproduce its
pattern in every subject. Two statements can be added with this evidence:

- In subject 13 the lag from R-peak to object peak is constant to within a
  few samples over the whole record, for matched and unmatched objects alike,
  so the whole construction is locked there, not only the W=79-only class.
- The W=79-only objects in subject 13 are a breath-position-biased sample of
  a continuous cardiac-rate train: falling-limb bumps only. That is a property
  of the look-ahead maximum, which absorbs any bump followed by a larger value
  within the window, and it is measured here rather than inferred.

Neither statement transfers to the held-out population as a whole. Subject 13
is a development record and the only one where the shared objects are locked.

## Reproduction

```bash
for s in $(seq 1 53); do
  python -m scripts.inspect_bidmc_region --subject $s --end 3000 --peaks
done
cp outputs/inspect/bidmc_*_peaks_W79_100.csv artifacts/studies/bidmc_peak_measures/
python -m scripts.summarize_bidmc_peak_measures
```

The first step needs the BIDMC Signals files under
`notebooks/.bidmc_notebook_cache`; they are fetched from PhysioNet on first
use. The summary step is pure and runs anywhere.
