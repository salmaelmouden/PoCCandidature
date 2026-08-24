# Deploy to Railway

Target: a public URL for the Streamlit dashboard, with the catalogue kept current
by a background refresher.

One repository, one image, several services that differ only by start command:

| Railway service | What it is | Config file | Public |
|---|---|---|---|
| **Postgres** | managed database plugin | — | no |
| **dashboard** | the Streamlit app (default `CMD`) | `railway.json` | **yes — this is the link you share** |
| **refresher** | `refresh_catalogue.py --loop` — without it the catalogue stays empty | `railway.refresher.json` | no |
| **api** | FastAPI for n8n, optional | `railway.api.json` | only if n8n needs to reach it |

Cost is roughly $5/month on the Hobby plan; the refresher is idle most of the time.

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

- **Config-as-code path:** `railway.refresher.json`. That file holds the start
  command (`refresh_catalogue.py --loop --interval-seconds 900`). Set it here
  rather than typing a **Custom Start Command** — a UI override is invisible from
  the repo and takes precedence over it, which is how this project spent a
  deploy running the wrong process on the wrong port.
- **Networking:** no domain, and no `PORT` — it has no HTTP server. `PORT` matters
  only for the dashboard and the API.

It declares no healthcheck, on purpose: there is no endpoint to probe, and a
healthcheck against a process that never listens fails the deploy.

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

With no `--loop` the script runs exactly one cycle and exits. That is enough to
make **Catalogue public** render; the service above is what keeps it current.

### Why a loop rather than a cron

Railway cron jobs fire at most once a minute and spin a container each time; a
long-lived loop costs less and keeps the backoff state that stops a broken key
from hammering the API all day. If you prefer cron, use `--interval-seconds`'s
absence — `refresh_catalogue.py` with no `--loop` runs exactly one cycle and exits.

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

| Cadence | YouTube units/day | Share of the free 10,000 |
|---|---|---|
| 15 min (default) | ~3,840 | 38 % |
| 10 min | ~5,760 | 58 % |
| 5 min | ~11,520 | **over quota** |

Do not go below 10 minutes. YouTube's public counters update with a lag anyway, so
a faster cadence buys no freshness and risks exhausting the daily allowance — after
which the refresher backs off and the page goes stale.

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
