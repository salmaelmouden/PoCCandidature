# Deploy to Railway

Target: a public URL for the Streamlit dashboard, with the catalogue kept current
by a background refresher.

Three pieces, one repository:

| Railway service | What it is | Public |
|---|---|---|
| **Postgres** | managed database plugin | no |
| **dashboard** | the Streamlit app (default `CMD`) | **yes — this is the link you share** |
| **refresher** | `refresh_catalogue.py --loop`, same image, different start command | no |

Cost is roughly $5/month on the Hobby plan; the refresher is idle most of the time.

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

Under **Settings → Networking**, click **Generate Domain**. That URL is the link
you share.

Nothing else to set: the default `CMD` runs `alembic upgrade head` and then
Streamlit on `$PORT`, and `railway.json` points the health check at
`/_stcore/health`.

## 3. Add the refresher service

**New** → **GitHub Repo** → the same repository, then under **Settings**:

- **Custom Start Command:**
  ```
  python scripts/refresh_catalogue.py --loop --interval-seconds 900
  ```
- **Networking:** no domain — it has no HTTP server.

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
concurrent `alembic upgrade` runs against one database can collide.

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

## Troubleshooting

| Symptom | Cause |
|---|---|
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
