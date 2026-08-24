# Deploy to Railway

Target: a public URL for the Streamlit dashboard, with the catalogue kept current
by a background refresher.

One repository, one image, several services that differ only by start command:

| Railway service | What it is | Config file | Public |
|---|---|---|---|
| **Postgres** | managed database plugin | — | no |
| **dashboard** | the Streamlit app (default `CMD`) | `railway.json` | **yes — this is the link you share** |
| **refresher** | cron, `*/10` — one `refresh_catalogue.py` cycle per run. Without it the catalogue stays empty | `railway.refresher.json` | no |
| **api** | FastAPI for n8n, optional | `railway.api.json` | only if n8n needs to reach it |

Cost is roughly $5/month on the Hobby plan. The refresher is a cron job, so it is
billed only for the seconds it runs rather than for sitting idle.

## Every service must bind `$PORT`

The one rule that matters for anything serving HTTP. Railway picks the target port
for a generated domain by detection, and routes the public URL there; if the
process is listening somewhere else, the edge returns **"Application failed to
respond"** while the container is healthy and the deploy is green. The logs look
perfect, because your request never reached them.

So: set `PORT` explicitly as a variable on every service that has a domain, and
never hardcode a port in a start command. The start commands in `railway.json` and
`railway.api.json` all read `${PORT:-…}`, and the `Dockerfile` deliberately has no
`EXPOSE` line — a stale one is what makes Railway target the wrong port.

## 0. Before you start

- Push the branch to GitHub — Railway deploys from the repo.
- Have your `YOUTUBE_API_KEY` and `ANTHROPIC_API_KEY` to hand. **Never commit them**;
  they go in Railway's variable editor.

> The container image cannot be built on a machine behind a TLS-intercepting
> corporate proxy — `pip install` inside the build fails, which is why local
> development mounts a host-built `.venv` instead. Railway has no such proxy, so
> the build there is unaffected. Do not "fix" the Dockerfile if it fails locally.

## 1. Create the project and the database

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
   → pick this repository and the branch you want.
2. In the project, **New** → **Database** → **Add PostgreSQL**.

> **Railway does not inject `DATABASE_URL` into your other services.** The variable
> exists on the Postgres service only; every service that needs it must reference it
> explicitly (step 2). Skipping this is the most common way this deploy fails, and it
> fails confusingly: without the variable the app falls back to its local-dev default
> and the logs show `connection to server at 127.0.0.1, port 5434 failed` inside a
> healthcheck timeout. The app now refuses to start in that case with an explicit
> message instead.

Whatever the provider hands out, the app rewrites the scheme to the psycopg 3
driver on the way in — managed hosts emit `postgres://`, which SQLAlchemy would
otherwise route to psycopg2 (not installed).

## 2. Configure the dashboard service

The service created from the repo is the web one. Under **Variables**:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
YOUTUBE_API_KEY=<your key>
YOUTUBE_CHANNEL_ID=UCRCCAnVyzDTcqNYh0pDcq7Q
ANTHROPIC_API_KEY=<your key>
APP_ENV=production
```

`${{Postgres.DATABASE_URL}}` is a Railway variable reference, not a literal —
replace `Postgres` with your database service's actual name as shown on its card
in the project canvas. Railway resolves it at deploy time.

Leave `CA_BUNDLE_PATH` unset: it exists only to work around the corporate proxy
locally, and pointing it at a path that does not exist in the image breaks TLS.

Add `PORT=8501` to the variables above, then under **Settings → Networking** click
**Generate Domain** and check the domain's **target port** reads 8501. That URL is
the link you share.

Nothing else to set: `railway.json` supplies the start command (`alembic upgrade
head`, then Streamlit on `$PORT`) and points the health check at `/_stcore/health`.
Leave **Custom Start Command** in the dashboard UI *empty* — an override there is
invisible from the repo, and a hand-typed port in it is the usual way this service
ends up listening somewhere the domain is not pointing.

## 3. Add the refresher service

Without this service the catalogue is never populated, and **Catalogue public**
has nothing to read.

**New** → **GitHub Repo** → the same repository, then under **Settings**:

- **Config-as-code path:** `railway.refresher.json`. That file makes this a **cron
  service** — `cronSchedule` `*/10 * * * *`, one cycle per run. Set it here rather
  than typing a **Custom Start Command**: a UI override is invisible from the repo
  and takes precedence over it, which is how this project spent a deploy running
  the wrong process on the wrong port.
- **Networking:** no domain, and no `PORT` — it has no HTTP server. `PORT` matters
  only for the dashboard and the API.

It declares no healthcheck, on purpose: there is no endpoint to probe, and a
healthcheck against a process that never listens fails the deploy. Its restart
policy is `NEVER`, which is what you want for a scheduled job — a cron run that
exits has finished, not crashed, and restarting it would double the cadence.

Give it the same variables as the dashboard — including its own
`DATABASE_URL=${{Postgres.DATABASE_URL}}` reference, which is not inherited:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
YOUTUBE_API_KEY=<your key>
YOUTUBE_CHANNEL_ID=UCRCCAnVyzDTcqNYh0pDcq7Q
ANTHROPIC_API_KEY=<your key>
APP_ENV=production
```

Do not let this service run migrations: the dashboard already does, and two
concurrent `alembic upgrade` runs against one database can collide. That is why
`railway.refresher.json` starts the script directly, with no `alembic upgrade
head` in front of it.

### Seeding it once, right now

If you just want data in the page without waiting for a service, run a single
cycle from the Railway shell on any service that has the variables:

```
python scripts/refresh_catalogue.py
```

The script runs exactly one cycle and exits. That is enough to make **Catalogue
public** render; the cron service above is what keeps it current.

Note the absence of `--respect-backoff` here. A manual seed should never be
silently skipped because an earlier run failed, so the flag is opt-in and the
cron service is the only thing that passes it.

### Why cron rather than a long-lived loop

The script still supports `--loop`, but the deployed service does not use it.

Cron is cheaper. Railway bills by resource-second, and a loop that sleeps 10
minutes between 8-second cycles still holds its memory allocation for all 720
hours in a month. The cron service is billed for the seconds it actually runs —
a few hours a month rather than all of them. An earlier version of this guide
claimed the opposite; it was wrong.

The reason it *was* a loop is that exponential backoff lived in a local variable,
and a fresh container per run resets it to zero. That mattered: with a revoked key
or an exhausted quota, a naive cron would retry at full cadence all day, spending
the daily allowance on calls that cannot succeed.

So the counter moved into the database. `IngestRunRepository.consecutive_failures()`
counts failed runs since the last successful one, and `--respect-backoff` widens
the interval from that count — doubling per failure, capped at 8x — before the run
touches the API at all. The state now outlives the process, which is what made
cron viable. If the check itself cannot reach the database it lets the run
proceed: pacing is an optimisation, and it must never be the reason nothing
refreshes.

## 4. First data load

The refresher populates everything on its first cycle: ~950 videos ingested
(~8 s, ~40 of the 10,000 free daily YouTube units) and then classified.

**The first classification costs roughly $0.65** — every video is new. Subsequent
cycles classify only new uploads, so the ongoing cost is effectively zero.

Watch the refresher's **Deploy Logs** for:

```
refresh_cycle ok=True videos=952 metrics=952 classified=952 failed=0
```

Then open the dashboard URL → **Catalogue public**. The header shows when it last
checked and when the numbers last changed.

### Optional: the synthetic pages

Pages 1–6 read the labelled synthetic funnel dataset and will be empty without it.
To populate them, run once from the Railway shell (or as a one-off service command):

```
python scripts/seed_synthetic_data.py
```

The **Catalogue public** page does not need this — it reads only the real ingested
catalogue.

## 5. Quota and cost guards

One full pass over ~950 videos costs ~40 of the 10,000 free daily YouTube units.

| Cadence | `cronSchedule` | YouTube units/day | Share of the free 10,000 |
|---|---|---|---|
| 15 min | `*/15 * * * *` | ~3,840 | 38 % |
| **10 min (default)** | `*/10 * * * *` | ~5,760 | **58 %** |
| 5 min | `*/5 * * * *` | ~11,520 | **over quota — do not** |

**10 minutes is the floor.** At 5 the daily allowance is gone by mid-afternoon,
the refresher backs off, and the page ends up *staler* than it would have been on
a slower cadence. YouTube's public counters update with hours of lag regardless,
so polling faster buys no real freshness — only quota risk.

If you change the cadence, change it in **two places**: `cronSchedule` and the
`--interval-seconds` in the same file. The first decides when runs fire; the
second is what the backoff multiplies when they fail. Leaving them inconsistent
does not break anything, but the backoff will pace itself against the wrong
baseline.

## 6. Optional: the API service

Only needed if n8n (or anything else) must call `POST /api/reports/weekly` over
HTTP. The dashboard does not depend on it — skip this section otherwise.

**New** → **GitHub Repo** → the same repository, then under **Settings**:

- **Config-as-code path:** `railway.api.json` — this is what makes the service run
  uvicorn instead of Streamlit. Set it here rather than typing a **Custom Start
  Command**, so the deployed command lives in the repo and survives the next person
  to touch the dashboard.
- **Variables:** the same block as the dashboard, plus `PORT=8000`.
- **Networking:** generate a domain only if n8n runs outside this project;
  otherwise use the internal hostname and keep it private. Either way, confirm the
  domain's target port matches `PORT`.

`railway.api.json` runs uvicorn **without** `alembic upgrade head`, on purpose: the
dashboard already migrates, and two concurrent `alembic upgrade` runs against one
database can collide. If this service's logs show alembic running, it is using an
overridden start command rather than the config file.

Once it is up, `GET /` returns the service name, version, and where the docs are;
`/docs` is the OpenAPI UI and `/health` is what the health check probes.

## Troubleshooting

| Symptom | Cause |
|---|---|
| **"Application failed to respond"**, but the logs show a clean startup and a `200 OK` on the health path from `100.64.0.2` | The container is fine and Railway's proxy can reach it — your request cannot. The domain's **target port** does not match the port the process bound. Set `PORT` on the service, make sure the start command reads `$PORT`, and check the target port on the domain |
| The public URL 404s with `{"detail":"Not Found"}` | You reached the **api** service, not the dashboard. That is a live app answering correctly — try `/docs` |
| Logs show uvicorn where you expected Streamlit (or vice versa) | A **Custom Start Command** in the UI is overriding the repo config. Clear it and set the config-as-code path instead |
| The app works but renders unstyled — stock Streamlit colours, no brand sidebar | `.streamlit/config.toml` did not reach the image. The `Dockerfile` copies named paths, so the directory needs its own `COPY`, and `.dockerignore` must exclude only `.streamlit/secrets.toml` — not the whole directory. Nothing fails at build time when it is missing |
| `ImportError: no pq wrapper available` / `No module named 'psycopg_binary'` | The `psycopg[binary]` wheel did not install, so psycopg fell back to pure Python and found no libpq. The `Dockerfile` installs `libpq5` to cover this — if you see it again, that step was removed. Do **not** "fix" it with `build-essential` + `libpq-dev`: that costs ~110 MB and the runtime library alone is enough |
| Healthcheck fails; logs show `connection to server at 127.0.0.1, port 5434 failed` | `DATABASE_URL` is missing on **that** service — add the `${{Postgres.DATABASE_URL}}` reference. It is per-service, never inherited |
| `DATABASE_URL is not set and APP_ENV is production` | Same cause, caught early — follow the message |
| `ModuleNotFoundError: psycopg2` | `DATABASE_URL` reached SQLAlchemy unrewritten — check `app/config/settings.py` is on the deployed revision |
| Health check fails, logs show Streamlit started | The app is not bound to `$PORT` — check the start command was not overridden |
| `YOUTUBE_API_KEY is required — nothing to refresh` | The variable is missing on the **refresher** service specifically |
| Refresher logs `refresh_backoff` repeatedly | Expired key, or the daily quota is exhausted; the page keeps serving the last good numbers |
| Page says "Aucun cycle de rafraîchissement enregistré" | The refresher service is not running |

## What is public

The dashboard URL is public and unauthenticated once a domain is generated. It
serves an independent analysis of publicly available YouTube data, and the page
states that on every load. It contains no credentials and no private data — but it
is a public page, so treat the link accordingly.
