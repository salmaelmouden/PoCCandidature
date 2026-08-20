"""growth_experiment_analyst_agent — analyze results or propose tests."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.growth_data_analyst_agent.schemas import EvidenceClaim, SemanticLabel, ToolInvocation
from app.agents.growth_experiment_analyst_agent.config import ExperimentAnalystConfig
from app.agents.growth_experiment_analyst_agent.prompts import DEFAULT_EXPERIMENT_QUESTION
from app.agents.growth_experiment_analyst_agent.schemas import (
    ExperimentAnalystQuestion,
    ExperimentAnalystReport,
    ExperimentMode,
)
from app.agents.growth_experiment_analyst_agent.tools import (
    tool_analyze_experiment,
    tool_get_analyst_report,
    tool_list_experiments,
)
from app.skills.experiment_analysis import DecisionHint, propose_experiment_design
from app.skills.experiment_analysis.schemas import ExperimentDesignProposal
from app.observability import observation


def classify_experiment_mode(question: str) -> ExperimentMode:
    q = question.lower()
    if any(
        k in q
        for k in (
            "how should we test",
            "how do we test",
            "design an experiment",
            "propose an experiment",
            "what experiment",
            "a/b test idea",
            "ab test idea",
        )
    ):
        return ExperimentMode.PROPOSE
    return ExperimentMode.ANALYZE


def _extract_experiment_key(question: str, default: str) -> str:
    q = question.lower()
    if "youtube" in q and "cta" in q:
        return "syn_exp_youtube_cta"
    if "syn_exp_" in q:
        # crude capture
        for token in question.replace(",", " ").split():
            if token.startswith("syn_exp_"):
                return token.strip("'\"")
    return default


class GrowthExperimentAnalystAgent:
    """Experiment specialist: analyze stored A/B results or propose a test design."""

    name = "growth_experiment_analyst_agent"

    def __init__(self, config: ExperimentAnalystConfig | None = None) -> None:
        self.config = config or ExperimentAnalystConfig()

    def run(
        self, session: Session, question: ExperimentAnalystQuestion | str | None = None
    ) -> ExperimentAnalystReport:
        payload = self._normalize(question)
        mode = classify_experiment_mode(payload.question)
        with observation(
            self.name,
            input={"question": payload.question},
            metadata={"mode": mode.value, "days": payload.days},
            tags=["experiment", mode.value],
        ) as span:
            if mode == ExperimentMode.PROPOSE:
                report = self._propose(session, payload)
            else:
                report = self._analyze(session, payload)
            span.update(
                output={
                    "mode": report.mode.value,
                    "decision_hint": (
                        report.decision_hint.value if report.decision_hint else None
                    ),
                    "insufficient_evidence": report.insufficient_evidence,
                }
            )
            return report

    def _normalize(
        self, question: ExperimentAnalystQuestion | str | None
    ) -> ExperimentAnalystQuestion:
        if question is None:
            return ExperimentAnalystQuestion(question=DEFAULT_EXPERIMENT_QUESTION)
        if isinstance(question, str):
            return ExperimentAnalystQuestion(question=question)
        return question

    def _safe(
        self, tool_calls: list[ToolInvocation], name: str, fn
    ) -> dict | object | None:
        try:
            detail = fn()
            ok = True
            if isinstance(detail, dict) and detail.get("ok") is False:
                ok = False
            summary = name
            if isinstance(detail, dict):
                summary = detail.get("error") or f"{name} ok={ok}"
            elif hasattr(detail, "primary_driver"):
                summary = f"analyst driver={getattr(detail, 'primary_driver', None)!r}"
            tool_calls.append(
                ToolInvocation(tool=name, ok=ok, summary=str(summary)[:240], detail={})
            )
            # Store serializable detail separately when dict
            if isinstance(detail, dict):
                tool_calls[-1].detail = {
                    k: v for k, v in detail.items() if k != "comparison"
                }
                if "comparison" in detail:
                    tool_calls[-1].detail["decision_hint"] = detail["comparison"].get(
                        "decision_hint"
                    )
            return detail
        except Exception as exc:  # noqa: BLE001
            tool_calls.append(
                ToolInvocation(
                    tool=name, ok=False, summary=str(exc), detail={"error": str(exc)}
                )
            )
            return None

    def _analyze(
        self, session: Session, payload: ExperimentAnalystQuestion
    ) -> ExperimentAnalystReport:
        tool_calls: list[ToolInvocation] = []
        self._safe(tool_calls, "list_experiments", lambda: tool_list_experiments(session))
        key = payload.experiment_key or _extract_experiment_key(
            payload.question, self.config.default_experiment_key
        )
        raw = self._safe(
            tool_calls,
            "analyze_experiment",
            lambda: tool_analyze_experiment(session, experiment_key=key, alpha=payload.alpha),
        )
        if not isinstance(raw, dict) or not raw.get("ok"):
            return ExperimentAnalystReport(
                question=payload.question,
                mode=ExperimentMode.ANALYZE,
                experiment_key=key,
                claims=[
                    EvidenceClaim(
                        label=SemanticLabel.INTERPRETATION,
                        text="Insufficient evidence: could not analyze experiment.",
                        source_tool="analyze_experiment",
                    )
                ],
                tool_calls=tool_calls,
                insufficient_evidence=True,
            )

        cmp_ = raw["comparison"]
        claims = [
            EvidenceClaim(
                label=SemanticLabel.FACT,
                text=(
                    f"{raw['name']} ({key}): control rate={cmp_['control']['conversion_rate']:.4f} "
                    f"(n={cmp_['control']['users']}), treatment rate="
                    f"{cmp_['treatment']['conversion_rate']:.4f} (n={cmp_['treatment']['users']})."
                ),
                source_tool="analyze_experiment",
                numbers={
                    "control_rate": cmp_["control"]["conversion_rate"],
                    "treatment_rate": cmp_["treatment"]["conversion_rate"],
                    "absolute_lift": cmp_["absolute_lift"],
                    "p_value": cmp_["p_value"],
                },
            ),
            EvidenceClaim(
                label=SemanticLabel.FACT,
                text=(
                    f"Absolute lift={cmp_['absolute_lift']:.4f}, "
                    f"CI=[{cmp_['ci_low']:.4f}, {cmp_['ci_high']:.4f}], "
                    f"significant={cmp_['significant']} at α={cmp_['alpha']}."
                ),
                source_tool="analyze_experiment",
                numbers={
                    "ci_low": cmp_["ci_low"],
                    "ci_high": cmp_["ci_high"],
                    "z_score": cmp_["z_score"],
                },
            ),
            EvidenceClaim(
                label=SemanticLabel.INTERPRETATION,
                text=cmp_["notes"],
                source_tool="analyze_experiment",
            ),
            EvidenceClaim(
                label=SemanticLabel.RECOMMENDATION,
                text=f"Decision hint: {cmp_['decision_hint']} — {cmp_['notes']}",
                source_tool="analyze_experiment",
                numbers={"decision_hint": cmp_["decision_hint"]},
            ),
        ]
        return ExperimentAnalystReport(
            question=payload.question,
            mode=ExperimentMode.ANALYZE,
            experiment_key=key,
            decision_hint=DecisionHint(cmp_["decision_hint"]),
            claims=claims,
            tool_calls=tool_calls,
            insufficient_evidence=False,
        )

    def _propose(
        self, session: Session, payload: ExperimentAnalystQuestion
    ) -> ExperimentAnalystReport:
        tool_calls: list[ToolInvocation] = []
        report = payload.analyst_report
        if report is None:
            report = self._safe(
                tool_calls,
                "get_analyst_report",
                lambda: tool_get_analyst_report(
                    session,
                    question=payload.question,
                    days=payload.days,
                    channel=payload.channel,
                    as_of=payload.as_of,
                ),
            )
        else:
            tool_calls.append(
                ToolInvocation(
                    tool="get_analyst_report",
                    ok=True,
                    summary="Used caller-provided AnalystReport",
                    detail={"primary_driver": report.primary_driver},
                )
            )

        if report is None or getattr(report, "insufficient_evidence", True):
            driver = "unclear growth driver"
            grounded = None
            insufficient = True
        else:
            driver = report.primary_driver or "stated growth pressure"
            grounded = report.primary_driver
            insufficient = False
            tool_calls = tool_calls  # already set

        # Ensure tool call recorded if analyst returned object without going through _safe detail
        if report is not None and not any(t.tool == "get_analyst_report" for t in tool_calls):
            tool_calls.append(
                ToolInvocation(
                    tool="get_analyst_report",
                    ok=True,
                    summary=f"driver={driver!r}",
                    detail={},
                )
            )

        channel_or_topic = payload.channel
        if channel_or_topic is None and grounded:
            for token in ("YouTube", "LinkedIn", "Instagram"):
                if token.lower() in grounded.lower():
                    channel_or_topic = token
                    break

        design: ExperimentDesignProposal = propose_experiment_design(
            driver=driver,
            channel_or_topic=channel_or_topic,
        )
        claims = [
            EvidenceClaim(
                label=SemanticLabel.FACT,
                text=f"Proposal grounded on analyst primary_driver={grounded!r}.",
                source_tool="get_analyst_report",
                numbers={"driver": grounded},
            ),
            EvidenceClaim(
                label=SemanticLabel.RECOMMENDATION,
                text=(
                    f"{design.name}: {design.hypothesis} "
                    f"Metric={design.primary_metric}. Success: {design.success_criteria}"
                ),
                source_tool=None,
                numbers={"primary_metric": design.primary_metric},
            ),
            EvidenceClaim(
                label=SemanticLabel.INTERPRETATION,
                text=(
                    f"Control: {design.control_description} "
                    f"Treatment: {design.treatment_description}"
                ),
                source_tool=None,
            ),
        ]
        return ExperimentAnalystReport(
            question=payload.question,
            mode=ExperimentMode.PROPOSE,
            design=design,
            claims=claims,
            tool_calls=tool_calls,
            insufficient_evidence=insufficient and grounded is None,
        )
