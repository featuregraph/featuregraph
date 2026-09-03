# Related work notes for the compiler paper

Working notes, not prose. Every reference here must be verified against the
source before it is cited. "Verified" below means the bibliographic record
was checked; it does not mean the claim attributed to the work was checked
against its text unless that is stated.

## Qualitative reasoning: the lineage to place the partition in

**Kuipers, B. J. (1986). Qualitative simulation. *Artificial Intelligence*,
29(3), 289–338.** Bibliographic record verified (publisher listing and the
author's own page). The paper defines qualitative structure and behaviour
descriptions as abstractions of differential equations and continuously
differentiable functions, and gives the QSIM algorithm.

What to check in the text before citing for it: the qualitative state of a
variable is a pair of a qualitative magnitude and a direction of change, and
the direction-of-change vocabulary is increasing, steady, decreasing. If that
holds, it is the rising, inactive, falling partition thirty-plus years
earlier, and the framing of behaviour as a sequence of such states with
transitions between them is the occurrence sequence.

**Kuipers, B. J. (1993). Qualitative simulation: then and now. *Artificial
Intelligence*, 59(1–2), 133–140.** Record seen on the author's page; verify
volume and pages. Useful as a retrospective on what the qualitative approach
did and did not deliver, which is where the compiler paper's difference
should be argued.

How to position FeatureGraph against it, once verified:

- QSIM reasons *from a model*, a qualitative differential equation, and
  produces the set of behaviours the model permits. FeatureGraph reasons
  *from observations* and produces the one behaviour the record exhibits
  under a declared partition. Same vocabulary, opposite direction.
- QSIM's contribution was completeness of the simulation. FeatureGraph's is
  provenance and refusal: the partition is fingerprinted, approval is
  attributable, and the compiler distinguishes unobserved, contradicted and
  underdetermined rather than guessing.
- The cross-domain claim has a precedent here. Qualitative reasoning argued
  that direction-of-change descriptions carry meaning without a quantitative
  model. The empirical record in this repository is the evidence that they
  carry across domains in practice, which that literature asserted more than
  measured.

Framing to use: FeatureGraph is the executable, provenance-carrying
descendant of the qualitative-state idea, not a new idea. That is a stronger
position than novelty and it will survive a reviewer who knows the field.

## Still to find and verify

- Signal temporal logic monitoring (Maler and Ničković, and the Breach and
  S-TaLiRo tools). Difference: returns satisfaction or robustness of a
  formula, not a partition with identity.
- Complex event processing (Esper, Siddhi, Flink CEP). Difference: pattern
  matching over streams, no exclusivity or exhaustiveness obligation, no
  approval gate.
- Allen's interval algebra (Allen 1983). Difference: relations between
  intervals given; FeatureGraph constructs the intervals.
- Declarative data transformation with tests (dbt, Great Expectations).
  Difference: validation of tables, not construction of objects with
  identity.

## Sources consulted for the Kuipers records

- https://www.cs.utexas.edu/~qr/papers/Kuipers-aij-86.html
- https://web.eecs.umich.edu/~kuipers/research/pubs/Kuipers-aij-86.html
- https://www.cs.utexas.edu/ftp/qsim/papers/Kuipers-aij-93b.pdf
