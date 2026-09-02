# Public study assistant

The conversational study builder, served to more than one person at a time.

`scripts/run_conversational_study_demo.py` runs the same conversation locally
for one person. This is the deployable form, and it differs in three ways that
only matter once the page is public:

- **Sessions are per visitor**, keyed by an opaque `HttpOnly` cookie and swept
  on a timer. The local demo keeps one session in a class attribute, which on a
  public page would let two people type into the same conversation and let
  either approve the other's study.
- **Model calls are budgeted**, per session and per process, and charged before
  the call is made. The counters are reported in `/api/state` so the page can
  show what is left. The global ceiling refills daily rather than being a
  lifetime cap: a limit that never refills takes the demonstration down for
  good the first time it is popular, which is the wrong way for it to fail.
- **The approving authority is the session, not a person.** A visitor clicking
  "Approve and run" is not a researcher approving a study, and the approval
  record in the contract says so. Set `FEATUREGRAPH_ASSISTANT_AUTHORITY` for a
  private deployment where a named person really is approving.

Nothing here executes researcher-supplied code or data. The study that runs is
the maintained PhysioNet wearable protocol fixture.

## Run it locally

    COHERE_API_KEY=... FEATUREGRAPH_INSECURE_COOKIE=1 python apps/assistant/server.py

Without a key it serves the offline frozen example, so the execution boundary
stays demonstrable with no model access at all. `FEATUREGRAPH_INSECURE_COOKIE`
drops the `Secure` flag, which a browser would otherwise refuse to store over
plain HTTP — leave it unset in the deployment.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `PORT` | `8080` | Port to bind. |
| `HOST` | `0.0.0.0` | Interface to bind. |
| `COHERE_API_KEY` | unset | Absent means the offline assistant. |
| `FEATUREGRAPH_ASSISTANT_MODEL` | `command-a-plus-05-2026` | Proposer model. |
| `FEATUREGRAPH_ASSISTANT_AUTHORITY` | `public demonstration session {session}` | Approval authority; `{session}` is substituted. |
| `FEATUREGRAPH_SESSION_CALL_LIMIT` | `10` | Model calls one visitor may spend. |
| `FEATUREGRAPH_GLOBAL_CALL_LIMIT` | `1000` | Model calls this process may spend per window. |
| `FEATUREGRAPH_GLOBAL_WINDOW_SECONDS` | `86400` | How often the global ceiling refills. |
| `FEATUREGRAPH_SESSION_TTL` | `3600` | Seconds before an idle session is swept. |
| `FEATUREGRAPH_MAX_SESSIONS` | `200` | Concurrent sessions before the oldest is evicted. |
| `FEATUREGRAPH_SESSION_DIR` | system temp | Where per-session artifacts are written. |
| `FEATUREGRAPH_INSECURE_COOKIE` | unset | Any value drops the `Secure` cookie flag. |

## Deploying

See the header of `fly.toml`. Run every command from the repository root: the
Dockerfile copies `src/`, `scripts/` and `artifacts/`, so the build context is
the root even though the Dockerfile lives here. Paths inside `fly.toml` — the
`[build] dockerfile` key included — resolve against `fly.toml`'s own directory
instead, which is why that key is a bare filename.

Build on Fly's builder with `--remote-only` unless a local Docker daemon is
available; a Codespace generally has none.

Run `fly scale count 1` after the first deploy. `fly launch` creates two
machines by default and `min_machines_running` will not reduce them -- it sets
a floor, not a ceiling, and there is no fly.toml key for the count.

This app must run on exactly one machine until its state moves out of the
process. The session registry and the call budget are both in memory: with two
machines behind Fly's load balancer a visitor's next request can land on the
one that has never heard of them, and the global call ceiling is enforced twice
over instead of once. Sharing state -- Redis for the counter, sticky sessions or
a session store for the conversations -- is what a second machine needs first.
