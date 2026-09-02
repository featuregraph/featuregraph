# FeatureGraph framework

A deterministic compiler for state representations. A researcher declares rules
over ordered observations; the compiler turns them into states, events and
bounded objects. It does not infer, smooth, threshold, or interpret — every one
of those is a declaration the researcher makes and the compiler executes.

## The invariant

**Propose → validate → execute.** A model or a person may propose a contract.
Deterministic checks validate it. A named human approves it, and the approval
records a SHA-256 fingerprint of the payload. Execution refuses anything that
was not approved.

Nothing in this repository should erode that boundary. In particular:

- The compiler never judges whether a result is scientifically sensible. If you
  find yourself adding a heuristic that suppresses "suspicious" occurrences,
  stop — an occurrence far shorter than its neighbours was a real finding in
  `artifacts/paper/master/bidmc_preprint_draft.md`, and a filter would have
  deleted it.
- `approve_study_contract` refuses a candidate carrying `approval`, so a
  proposer cannot grant itself authority. Keep it that way.
- The approving authority is a person's name in a private deployment and the
  session id in the public one. It must never be a site owner's name on a page
  where anonymous visitors can click Approve.

## Two Read the Docs projects, and the short name is not this one

- This repo (`featuregraph`) publishes docs at
  **`featuregraph-framework.readthedocs.io`**.
- `featuregraph-research` publishes at `featuregraph.readthedocs.io`.

The shorter, more obvious URL belongs to the research record rather than to
this framework. That mismatch put a wrong "Documentation" link across the live
marketing site, in the nav, the resource card, and `documentation.html`'s
canonical URL and meta refresh. Nothing 404s when it happens — readers simply
land on the research record — so check where a docs link *goes*, not whether it
resolves.

## The package name collision is resolved

Both repositories once declared `name = "featuregraph"` at the same version
with the same description, so pip treated them as one distribution and
installing either clobbered the other. That is the root of the docs mix-up
above and of a bug report filed against a module that was never imported.

The research package is now importable as `featuregraph_research` and
distributed as `featuregraph-research`. **`featuregraph` belongs to this
repository** — it is what the papers cite, what the install lines name, and
what `import featuregraph` should mean.

Two things in the research repository deliberately keep the old string, so
seeing `featuregraph` there is not necessarily a leftover: it is a
representation label in the RL and TEP experiments, where it names a column in
published results rather than a module, and it is the dataset cache directory
at `~/.cache/featuregraph/`, which the two packages share on purpose.

## Layout

- `src/featuregraph/contracts/` — `state_contract.py` compiles; `study_contract.py`
  fingerprints and approves.
- `src/featuregraph/study_builder/` — `intake.py` is the study contract with
  holes in it; `conversation.py` is the bounded session over it.
- `apps/assistant/` — the deployable public assistant. See its README.
- `artifacts/studies/` — frozen contracts and reports. Treat published
  fingerprints as claims already cited elsewhere; do not rewrite them.

## Things learned the hard way

**A reader that does not look somewhere returns a false answer, not a smaller
one.** `intake_from_study_contract` once read five contract sections and never
opened `sources`, then reported everything it had not looked for as undeclared —
accusing a real archived study of omitting seven things it had written down. If
you extend that reader, extend the test that asserts exactly one field is
outstanding for the PhysioNet contract.

**An empty list is an answer.** `[]` means "the researcher says there are none";
`None` means nobody has said. Payloads marked `schema_version: 1` are read the
old way, where `[]` and `"Not yet specified"` both meant unset.

**Compilable and approvable are separate.** A study can satisfy the compiler and
still be unfit for a person to sign, and vice versa. Do not collapse the tiers.

## Working conventions

- Topical branch per change, PR into `main`. Do not push to `main`.
- `.venv/bin/python -m pytest -q` — all tests pass before a PR.
- `ruff check` and `ruff format --check` on files you touched. Pre-existing
  findings elsewhere in `src/` are out of scope; CI does not run ruff.
- Docs: `python -m sphinx -b html docs <out> -W`. Three intersphinx inventories
  are unreachable from sandboxed networks and fail identically on `main` —
  that is the expected clean result, not a regression.
- Register new doc pages in `docs/index.md`; the build treats warnings as errors.
