# featuregraph

Instructions for AI agents working in this repository.

## Agent access across the featuregraph organization

Set by Nazia Habib, 2026-11-25. Applies to every AI agent working in any
`featuregraph` repository.

Agents may write (commit, push, open and merge PRs) only to:

- `featuregraph/featuregraph`
- `featuregraph/featuregraph.github.io`
- `featuregraph/featuregraph-runtime` (private)
- `featuregraph/featuregraph-api` (private)
- `featuregraph/featuregraph-streaming`

Agents must **not** write to:

- `featuregraph/state-detection` (private)
- `featuregraph/featuregraph-core`
- `featuregraph/featuregraph-event-dsl`
- `featuregraph/featuregraph-spatial`
- any repository with `demo` in its name (today: `featuregraph-api-demo`,
  `data-science-demos`)
- the forks `featuregraph/cohere-labs-blog` and `featuregraph/mathematics_in_lean`

The rule for new repositories: private repositories are writable except
`state-detection`; anything with `demo` in the name is not. Any other new
public repository is not writable until it is added to the list above.

If a tool or credential happens to allow a write to a repository outside the
writable list, do not use it: stop and ask. Reading public repositories is fine.
