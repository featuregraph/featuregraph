# BIDMC–CapnoBase Cross-Domain Studies: Status

A short series of study notes comparing BIDMC (impedance-derived respiration)
against CapnoBase (capnography), scoped after both datasets were populated
and validated for cross-study comparability. Separate from, and not tied to,
the smoothing paper.

## Why this series exists

Two ideas sit behind this, one broader and one specific to this pairing.

**The broader idea**: downstream domain-science questions like this one are
deliberately scoped as short 2–3 page study notes, not full papers. A study
note states the question, runs it through infrastructure that already
exists, reports the result plainly, and stops. This is the concrete
expression of the platform-builder contribution — "here is what I built so
someone else doesn't have to build the infrastructure before they can
start" — rather than every downstream finding being forced into one large
paper, or into work only the platform's builder can do.

**The specific idea for BIDMC + CapnoBase**: strengthen the generality
argument by showing the same deterministic construction produces meaningful,
checkable comparisons across two different, physiologically unrelated
signal domains — chest-impedance-derived respiration and capnography —
without being rebuilt for either one. Each of the four studies was chosen
specifically because it avoids the one thing that *doesn't* generalize
between these two signals (amplitude, different physical units) while still
saying something real:

- Study 1 needed real time units (not raw sample counts) to even be
  comparable across two different sampling rates — this is why
  `sampling_rate_hz`/`duration_seconds`/`period_seconds` were added to the
  schema in the first place.
- Study 2 uses a ratio (`temporal_symmetry`) specifically because ratios of
  same-unit quantities sidestep the amplitude problem entirely.
- Study 3 turns something that was otherwise just an incidental
  observation — CapnoBase characterizing more reliably than BIDMC — into a
  formal, citable methodological finding.
- Study 4 is the direct two-domain sequel to the smoothing paper's own
  single-domain (BIDMC-only) generality claim — the same instability shown
  on a second, unrelated signal is meaningfully stronger evidence than one
  domain alone.

This is the same generality logic later extended again to TEP — an
industrial process, not a biosignal at all — making the full evidence chain
BIDMC alone → BIDMC + CapnoBase → BIDMC + CapnoBase + TEP.

## Precondition for all four

Re-run with the flagged BIDMC subjects screened out first — subject 23 at
minimum, ideally 10, 25, 33, and 48 too. Those specific subjects were shown
to distort population-level statistics in earlier analysis. This is a cheap
filter on data that already exists, not new infrastructure.

## Ready to run

1. **Population-level timing comparison** — `period_seconds`,
   `duration_seconds`, `rising_duration_seconds`/`falling_duration_seconds`,
   BIDMC vs. CapnoBase, once flagged subjects are excluded.

2. **Cycle-shape comparison via `temporal_symmetry`** — not yet run. A ratio
   of two same-unit quantities, so it needs no unit conversion and sidesteps
   the amplitude problem entirely. Asks whether a chest-impedance breath is
   *shaped* differently from a CO2-waveform breath.

3. **Signal-reliability as a formal finding** — CapnoBase's confident-
   characterization rate (35/42, ~83%) vs. BIDMC's (37/53, ~70%). A real,
   statable methodological result: direct capnography produces more
   reliably periodic signal than impedance-derived respiration.

4. **Within-dataset window variability, compared across datasets** — both
   populations independently show large per-subject smoothing-window
   variation. Having this on two physiologically unrelated signals would be
   meaningfully stronger generality evidence than BIDMC alone.

## Off the table

- **Any amplitude comparison** — permanently blocked; the two signals are in
  different physical units.
- **Treating CapnoBase's ground truth as equal-strength to BIDMC's** — no
  inter-annotator ceiling exists for CapnoBase to judge it against.
- **Anything using CapnoBase's inspiration-phase labels**
  (`co2_startinsp`/`peak_index`) — never validated.

## Open question before any of these run as public study notes

This series was scoped before the CapnoBase data-usage permission question
came up, and before CapnoBase was removed from the smoothing paper. Studies
1, 2, and 4 all involve publishing CapnoBase-derived numbers — the same
category of thing that permission question concerned. 

Study 3 is a partial exception: it's closer to an aggregate observation
about signal characteristics (a confidence-rate comparison) than a
per-subject derived result, and may sit more comfortably even without
resolved permission — but that's worth a deliberate decision, not an
assumption.

## CapnoBase usage permission — resolved

CapnoBase's own terms (capnobase.org) require citation of the 2010 STA
abstract and the 2013 IEEE TBME paper, and require that redistributed
data carry that citation and the terms of use. The IEEE TBME RR
Benchmark's specific restriction is: the dataset must not be used to
train or tune an algorithm, since doing so would bias its value as a
fixed benchmark for future work.

None of Studies 1–4 train or tune anything against CapnoBase — each
applies FeatureGraph's fixed, deterministic construction and reports
comparative or descriptive results, which is explicitly named as
permitted use in the CapnoBase materials agreement ("comparing data...
with other Materials," "extracting... for use in other projects,
publications, research"). All four are clear to publish as study
notes, provided the required citation accompanies each one.

CapnoBase was removed from the smoothing paper for separate,
already-settled reasons (scope), unrelated to this permission
question.

## References

BIDMC PPG and Respiration Dataset: Pimentel, M. A. F., Johnson, A. E. W.,
Charlton, P. H., Birrenkott, D., Watkinson, P. J., Tarassenko, L., &
Clifton, D. A. (2016). Toward a robust estimation of respiratory rate
from pulse oximeters. *IEEE Transactions on Biomedical Engineering*,
64(8), 1914–1923.

CapnoBase IEEE TBME Respiratory Rate Benchmark: Karlen, W., Raman, S.,
Ansermino, J. M., & Dumont, G. A. (2013). Multiparameter respiratory rate
estimation from the photoplethysmogram. *IEEE Transactions on Biomedical
Engineering*, 60(7), 1946–1953.

