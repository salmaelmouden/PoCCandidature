"""Presentation helpers for the automation history — pure, no Streamlit runtime.

The page decides nothing: whether a job is healthy is judged in
`app.services.automation`, and this module only turns that verdict into French
words and a table. Kept separate so both can be tested without importing a page,
which would execute it.
"""

from __future__ import annotations

import pandas as pd

from app.services.automation import AutomationHealth, RunSummary
from dashboard.formatting import fmt_pct, humanize_age

#: Status → (French label, badge kind, what it means for the reader).
#: `stale` and `failing` are kept apart deliberately: an erroring job says what
#: went wrong, a job that stopped being invoked says nothing at all, and the
#: second is the one a run table exists to surface.
STATUS_FR: dict[str, tuple[str, str, str]] = {
    "never": (
        "Jamais exécuté",
        "neutral",
        "Aucun run enregistré. La table existe, le job n'a pas encore tourné.",
    ),
    "ok": (
        "À jour",
        "good",
        "Le dernier run a réussi, et il est assez récent pour que le mémo le soit aussi.",
    ),
    "failing": (
        "En échec",
        "critical",
        "Le dernier run a échoué. Le mémo affiché ailleurs est celui du dernier "
        "run réussi, pas de cette semaine.",
    ),
    "stale": (
        "Silencieux",
        "warning",
        "Le dernier run a réussi, mais il date. Un job planifié qui cesse d'être "
        "déclenché n'écrit aucune ligne — c'est ce silence que cette page rend visible.",
    ),
}


def status_label(health: AutomationHealth) -> tuple[str, str, str]:
    """French label, badge kind and explanation for a health verdict."""
    return STATUS_FR.get(health.status, STATUS_FR["never"])


def headline_age(run: RunSummary | None) -> str:
    """How long ago a run finished, in words. `—` when there is none."""
    if run is None:
        return "—"
    from datetime import UTC, datetime

    return humanize_age((datetime.now(UTC) - run.finished_at.astimezone(UTC)).total_seconds())


def success_rate_label(health: AutomationHealth) -> str:
    rate = health.success_rate
    return "—" if rate is None else fmt_pct(rate, 0)


def runs_frame(health: AutomationHealth) -> pd.DataFrame:
    """One row per run, newest first.

    Failures carry their reason in the same column an artefact would occupy.
    Putting the error somewhere else would let a reader scan the table and see
    only blanks where the failures are.
    """
    return pd.DataFrame(
        [
            {
                "État": "OK" if run.ok else "Échec",
                "Terminé": run.finished_at.strftime("%d/%m/%Y %H:%M"),
                "Durée": f"{run.duration_seconds:.1f} s".replace(".", ","),
                "Résultat": run.artifact_path or run.error or "—",
            }
            for run in health.runs
        ]
    )
