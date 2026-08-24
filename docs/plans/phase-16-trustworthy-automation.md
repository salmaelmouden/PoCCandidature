# Plan: Phase 16 — Automatisation fiable + mémo éditorial

**Status:** W1 + W2 implemented · W3 + W4 pending
**Branch:** `phase-16-trustworthy-automation`
**Scope:** Corriger l'artefact d'arrondi qui vide l'étage Premium, poser une validation
déterministe entre les skills et les agents, produire un mémo éditorial hebdomadaire fondé
sur le catalogue réel, et rendre la couche d'automatisation observable.
**Out of scope:** Moteur de contenu multi-plateformes (chantier suivant), SEO, CRM, paid,
nouvel agent.
**Effets de bord assumés:** migration `004` (`automation_runs`), un nouvel endpoint API,
deux nouvelles skills, ADR-009. Détaillés en §Effets de bord.

## Why

Deux zones de l'offre sont à moitié couvertes — l'automatisation et les recommandations
data-driven en réunion éditoriale. En les instrumentant, on découvre que le problème n'est
pas leur périmètre mais leur **socle** : les deux reposent aujourd'hui sur un chiffre faux.

### Le constat, mesuré

`generate_synthetic_dataset(seed=42, days=60, as_of=2026-08-20)` :

| Étage | Volume 60 j |
|---|---|
| views | 743 733 |
| visits | 156 412 |
| signups | 10 739 |
| activated | 5 017 |
| **premium** | **11** |

11 conversions Premium pour 5 017 activations, soit **0,22 %** — là où le générateur vise
`premium_rate = 0.12 × _TOPIC_CONV[topic]`, c'est-à-dire ~12 %. Sur la fenêtre hebdomadaire
du dernier rapport (2026-08-14 → 08-20) : **0 premium sur 566 activations**. Seules
**11 lignes sur 2 160 (0,5 %)** portent un premium non nul.

### La cause

[`app/db/synthetic.py:329`](../../app/db/synthetic.py) applique `int()` au grain
`jour × canal × sujet` :

```python
premium = max(0, int(activated * premium_rate * rng.uniform(0.9, 1.05)))
```

À ce grain, `activated` vaut 1 à 5 (médiane 3 — 914 lignes sur 2 160 sont à 1). Avec un taux
de 0,12–0,18, `int(3 × 0.13) = int(0.39) = 0`. La troncature n'arrondit pas : elle **plancher**
systématiquement. L'espérance est détruite, pas bruitée. Les mêmes lignes plus haut dans le
funnel survivent parce que leurs opérandes sont d'un ou deux ordres de grandeur au-dessus du
seuil de troncature — l'erreur est invisible partout sauf au dernier étage.

### Ce que ça produit en aval

1. `sum_funnel` agrège des zéros → `premium_users = 0`.
2. `calculate_funnel` en déduit un goulot `activated_users → premium_users` à **100 % de
   dropoff** — un artefact présenté comme le résultat principal.
3. Le strategist s'y accroche et émet **`[P0] Fix Premium leak on weakest channel`**, avec un
   plan d'action détaillé (audit paywall, timing, CTA) sur un phénomène qui n'existe pas.
4. n8n l'expédie chaque lundi.

C'est le scénario que l'offre appelle *tool-first thinking without judgment*, produit par la
chaîne elle-même : une recommandation P0 confiante née d'un arrondi.

### Pourquoi la suite d'éval ne l'a pas vu

`seed_premium_drop_fixture` épingle des premium à 4 / 25 / 18 / 22 — un étage terminal **sain**.
Les agents n'ont jamais été évalués sur une entrée dégénérée. `make eval` était vert pendant
que la chaîne expédiait un P0 fantôme. Corriger le bug sans réparer ce filet laisserait la
classe de défaut entière non couverte : c'est l'objet de W2 autant que le correctif lui-même.

À établir avant de toucher au générateur :
`tests/test_synthetic_generator.py::test_youtube_premium_declines_in_recent_window` affirme
`previous > 0`. Avec 11 premium sur 60 jours tous canaux confondus, ce test passe au mieux par
chance de seed. Savoir s'il est cassé ou complaisant **avant** de corriger, sinon on ne sait
pas ce qu'on répare.

## Flow

```text
générateur (arrondi correct)
     → skills déterministes (facts)
     → metric_validation           ← NOUVEAU, appelé par le service applicatif
     → warnings dans le schéma d'entrée de l'agent
     → agent (propose)
     → post-condition déterministe ← NOUVEAU : dégrade toute reco visant un étage marqué
     → mémo éditorial FR / rapport hebdo
     → n8n planifié → automation_runs → livraison datée
```

## Décisions

### Générateur

- **Arrondi stochastique, pas `round()`.** `round()` déplace le biais sans le supprimer
  (0,39 → 0). On tire `floor(x) + (rng.random() < frac(x))`, ce qui préserve l'espérance au
  grain fin tout en gardant des entiers. Déterminisme conservé : même seed, même suite de
  tirages. Appliqué à **tous** les étages, la cause étant la magnitude et non l'étage.

### Validation (critic #1, #2, #3)

- **La validation est une skill déterministe, pas une consigne de prompt.** Un agent à qui on
  demande gentiment de « ne pas sur-interpréter » sur-interprétera. Cohérent avec ADR-002.
- **Nom : `metric_validation`** (`<domaine>_<capacité>`, conforme à `docs/skills/taxonomy.md`).
  L'ancien `plausibility_gate` nommait un mécanisme, pas une capacité. Inscription au tableau
  de la taxonomie + contrat `docs/templates/skill-contract.md` + README, comme toute skill.
- **Appelée par le service applicatif**, pas par l'agent. Raison : les warnings doivent
  apparaître même quand aucun agent ne tourne — `build_weekly_report(include_orchestrator=False)`
  doit les afficher aussi. Les warnings descendent ensuite dans le **schéma d'entrée** de
  l'agent.
- **Double verrou.** Les warnings sont donnés à l'agent en entrée (contexte), *et* une
  post-condition déterministe dégrade toute recommandation P0/P1 visant un étage marqué. La
  correction ne dépend donc jamais de l'obéissance du LLM — elle est testable sans lui.

### Mémo éditorial (critic #1, #6)

- **Les recommandations ne sortent pas d'une skill.** La décision de la Phase 13 tient : la
  skill émet des faits, choisir quelle contradiction compte est du jugement growth. Le mémo
  reprend donc le motif **déjà en place** dans `build_weekly_report`, qui va chercher
  `orch.strategy_report.recommendations` et les étiquette. Pas d'amendement à la Phase 13,
  pas de nouvel agent (`03-agents.mdc` : la liste des quatre agents est fermée).
- **Le strategist reçoit un nouvel outil** exposant `PublicSignalReport` en lecture. Son
  contrat interdit explicitement tout pont vers signups/conversion — c'est un *hard stop*
  d'`AGENTS.md`, il devient une contrainte écrite du contrat d'agent et un cas de test.
- **Skill séparée, nommée `memo_generation`** — parallèle à `report_generation`
  (`<artefact>_<capacité>`). Justification de la nouvelle abstraction, exigée par
  `02-architecture.mdc` : le schéma d'entrée (`PublicSignalReport`) et la langue de sortie
  n'ont rien de commun avec ceux de `report_generation` (analytics de funnel, anglais).
  Les fusionner produirait une skill bimodale portant deux contrats sans intersection —
  strictement plus complexe que deux skills à contrat unique.
- **Le mémo est en français.** Il est destiné à une réunion éditoriale ; le dashboard est FR
  depuis la Phase 15. Le rapport hebdo anglais reste pour l'API.
- **Les deux pistes restent séparées.** Catalogue réel (`youtube_api`) et funnel synthétique
  (`synthetic_v1`) ne sont jamais additionnés ni mis dans le même tableau.
- **Pas d'historique inventé.** Si le catalogue n'a qu'un instantané, le mémo écrit « premier
  point de mesure, pas encore de comparaison possible ».

### ADR-009 (critic, non bloquant)

Recadré. Ne porte pas sur « le droit de l'agent à qualifier une donnée » — c'est la skill qui
qualifie. Porte sur : **ce qu'un agent doit émettre à la place d'une recommandation lorsqu'un
warning bloquant couvre l'étage visé**, et pourquoi la post-condition est déterministe.

## Effets de bord (critic #5)

| Effet | Décision |
|---|---|
| **Schéma** | Migration `004` — table `automation_runs` (`job_name`, `started_at`, `finished_at`, `ok`, `error`, `output_ref`). `ingest_runs` **n'est pas** généralisée : ses colonnes (`videos_upserted`, `classified`, `channel_id`) sont propres au rafraîchissement du catalogue ; y loger des runs de rapport la déformerait. Seule modification de schéma de la phase. |
| **API** | Ajout `POST /api/memo/editorial`. Test de contrat sous `tests/` (couche API, `docs/conventions/testing.md`). |
| **Skills** | `metric_validation`, `memo_generation` — taxonomie + contrat + README pour les deux. |
| **Agent** | `growth_strategist_agent` : nouvel outil public-signal, entrée enrichie des warnings, contrat mis à jour. Pas de nouvel agent. |
| **Éval** | Nouveau cas + nouvelle fixture (voir W2). |

## Lots

### W1 — Corriger la troncature (bloquant)

- Établir d'abord l'état réel de `test_youtube_premium_declines_in_recent_window`.
- Arrondi stochastique dans `_build_acquisitions`, appliqué à tous les étages.
- **Invariant par étage** (critic #8) : pour chaque transition, le taux agrégé sur 60 j est
  comparé au taux attendu **calculé depuis les constantes du module** (`_TOPIC_CONV`,
  multiplicateurs de canal, fenêtre `in_decline`) — pas à une constante recopiée dans le test.
  Seed et fenêtre épinglés. Tolérance dérivée des bornes de `rng.uniform`, pas choisie
  (critic #7).
- Test de forme au grain fin : la part de lignes à premium nul reste plausible.
- Re-seed, regénérer un rapport hebdo, constater la disparition des zéros.

### W2 — `metric_validation` + le filet qui a manqué

- Skill déterministe : `FunnelResult` + volumes → `DataWarning` typés
  (`terminal_stage_empty`, `impossible_dropoff`, `cohort_too_small`), seuils documentés au
  contrat.
- Appel depuis `app/services/` ; warnings dans le schéma d'entrée du strategist ;
  post-condition déterministe sur sa sortie.
- Warnings affichés **en tête** du mémo et du rapport, pas en note de bas de page.
- Tests unitaires skill + agent, dont le cas historique exact (premium 0 / activated 566 →
  warning, **aucun** P0).
- **Cas d'évaluation** `eval_strategist_degenerate_funnel` + fixture
  `seed_degenerate_funnel_fixture` (critic #4) — l'étage terminal vide entre enfin dans la
  suite d'éval, au niveau que `docs/skills/taxonomy.md` désigne pour le contrôle qualité.
- ADR-009.

### W3 — Mémo éditorial hebdomadaire (catalogue réel)

- `memo_generation` : composition FR au-dessus de `public_signal_analysis`. **Faits
  uniquement.**
- Contenu factuel : ce qui a changé depuis la semaine dernière (nouvelles vidéos, portée vs
  cohorte), sujets/hooks sur- et sous-performants par format, section « ce que je ne peux pas
  mesurer ».
- Section recommandations alimentée par `growth_strategist_agent` via son nouvel outil,
  étiquetée RECOMMENDATION, jamais fusionnée avec les faits.
- Diff semaine-à-semaine via `VideoDailyMetric.metric_date` + `ingest_runs` ; dégradation
  explicite si l'historique manque.
- Service + `POST /api/memo/editorial`, markdown daté sous `reports/`.
- Tests : composition FR, dégradation sans historique, aucun chiffre non dérivé du rapport,
  contrat API, et **le strategist ne doit jamais produire d'énoncé liant signal public et
  signups**.

### W4 — Rendre l'automatisation observable

- Migration `004` + repository `AutomationRunRepository`.
- Workflow n8n #2 : mémo éditorial planifié (lundi matin), livraison datée, run enregistré.
- L'échec est un état : un run KO ne doit pas laisser croire à un mémo frais — même
  distinction `last_checked` / `last_changed` qu'en Phase 14.
- Historique des runs visible au dashboard, logique en service (l'UI ne calcule rien).
- README n8n : les deux workflows, ce qu'ils produisent, à quelle heure.

## DoD

- [x] W1 — état établi : le test était **complaisant**, pas cassé. Il passait *grâce* au
      bug (déclin de 100 % au lieu des 42 % configurés), et sur six seeds. Remplacé par
      un ratio épinglé aux facteurs `_PREMIUM_YOUTUBE_*`
- [x] W1 — invariant **par étage** ; a révélé une **seconde** occurrence non anticipée :
      `signups→activated_users` à 46,72 % contre une bande [50,60 %, 57,75 %]
- [x] W1 — arrondi stochastique ; premium 0,22 % → 11,72 %, activation 46,72 % → 54,18 %
- [x] W1 — plus aucun `premium_rate=0.0000` (fenêtre hebdo : `premium=0` → `premium=77`)
- [x] W2 — `metric_validation` : skill + contrat + README + entrée taxonomie
- [x] W2 — appel en service prévu par le schéma, warnings en entrée, post-condition
      déterministe sur la sortie agent (P2 de vérification, jamais P0/P1)
- [x] W2 — cas d'éval `eval_strategist_degenerate_funnel` + fixture
- [x] W2 — ADR-009 rédigé (`docs/decisions/ADR-009-data-quality-gate.md`)
- [x] W2 — câblage complet : `build_weekly_report` appelle `validate_funnel`, propage
      via `OrchestratorQuestion` → `StrategistQuestion`, et le rapport ouvre sur une
      section « ⚠ Data quality ». Testé avec **et sans** orchestrateur
- [ ] W3 — `memo_generation` : skill + contrat + README + entrée taxonomie
- [ ] W3 — mémo FR, faits dérivés du rapport, recos étiquetées et attribuées à l'agent
- [ ] W3 — test : aucun pont signal public → signups
- [ ] W3 — dégradation propre sans historique
- [ ] W4 — migration `004`, workflow planifié, run history au dashboard, README à jour
- [ ] `make test`, `make eval`, `make lint` verts
- [ ] README / phases.md / demo-script / taxonomies synchronisés
- [ ] L'histoire du bug écrite quelque part de lisible — c'est la preuve de jugement
