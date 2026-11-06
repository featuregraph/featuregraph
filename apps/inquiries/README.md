# Inquiry form service

Receives the two inquiry forms on featuregraph.ai ("analysis built for you" and
"build your own"). The marketing site is static, so it cannot keep what a
visitor types; this service does.

A submission is written to SQLite first and emailed second, through Resend. If
Resend is down the row is kept with `emailed = 0` and nothing is lost.

- Standard library only. One process, one machine: the database is a file on a
  Fly volume, and a volume attaches to a single machine.
- `POST /inquiries` takes JSON with `kind` (`pilot` or `build`) and that form's
  fields. Unknown fields are dropped; lengths are capped.
- Only the origins in `ALLOWED_ORIGINS` may post. A hidden `website` field is a
  honeypot: a filled one gets a normal success response and is not stored.
  Each client address is limited to 5 submissions an hour (`INQUIRY_RATE_LIMIT`).
  The limiter is in memory, so it resets when the machine stops.
- The email subject is fixed text per form. Nothing a visitor types goes into a
  header; the visitor's address is only the reply-to.
- Stored data is a name, an email address and what the visitor wrote. It stays
  in the volume, and the site's form says so.

## One-time setup

```bash
fly launch --no-deploy --copy-config --config apps/inquiries/fly.toml
fly volumes create inquiries_data --size 1 --region sjc --config apps/inquiries/fly.toml
fly secrets set RESEND_API_KEY=re_... --config apps/inquiries/fly.toml
fly deploy apps/inquiries --config apps/inquiries/fly.toml --remote-only
fly scale count 1 --config apps/inquiries/fly.toml
fly certs add api.featuregraph.ai --config apps/inquiries/fly.toml
```

Then, at IONOS:

1. `CNAME api` -> `featuregraph-inquiries.fly.dev` (and any record `fly certs
   show` asks for).
2. In Resend, add `featuregraph.ai` as a sending domain and create the SPF and
   DKIM records it lists. Until they verify, mail will not send from
   `inquiries@featuregraph.ai`; the inquiries are still stored.

Change `INQUIRY_TO`, `INQUIRY_FROM` and `ALLOWED_ORIGINS` in `fly.toml`.

## Reading what has been stored

```bash
fly ssh console --config apps/inquiries/fly.toml -C \
  "python -c \"import sqlite3;[print(r) for r in sqlite3.connect('/data/inquiries.db').execute('select id,received_at,kind,emailed,fields from inquiries')]\""
```

Back the volume up with `fly volumes snapshots`; Fly also takes daily snapshots.
