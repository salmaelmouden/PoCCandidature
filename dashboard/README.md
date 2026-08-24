# Dashboard

Streamlit UI, en français. **Aucune logique métier dans les pages** — elles
appellent `app.services.*` et rendent le résultat.

## Docker (recommandé)

```bash
make install   # une fois
make up
make status    # ce qui tourne vs ce qui est sorti
# http://localhost:8501
```

| Conteneur | Attendu |
|-----------|---------|
| `gia-postgres` | running (healthy) |
| `gia-migrate` | exited (0) |
| `gia-seed` | exited (0) |
| `gia-dashboard` | running → :8501 |

## Structure

`Home.py` ne rend rien : il déclare la navigation et exécute la page choisie.
Les pages vivent dans `views/` plutôt que dans un dossier `pages/`
auto-découvert, parce que `st.navigation` permet de les regrouper, de les nommer
en français et de leur donner une icône — ce que le nom de fichier ne permet pas.

| Chemin | Rôle |
|--------|------|
| `Home.py` | Routeur `st.navigation` + injection du thème |
| `views/overview.py` | Synthèse — KPI, trafic, santé de l'entonnoir |
| `views/acquisition.py` | Contribution par canal |
| `views/content.py` | Score de valeur, sujets, écarts portée/conversion |
| `views/funnel.py` | Taux de passage, point de fuite, comparaison de périodes |
| `views/orchestrator.py` | Point d'entrée IA (ADR-004) |
| `views/analyst.py` | Agent analyste — rapport FAIT / INTERPRÉTATION |
| `views/experiments.py` | Agent expérimentation |
| `views/catalogue.py` | Catalogue public YouTube (piste réelle) |

## Couche de présentation

Tout ce qui transforme une valeur en pixels est isolé dans des modules purs,
sans runtime Streamlit — importer une page l'exécute, donc rien de testable ne
peut y vivre.

| Module | Rôle | Pur ? |
|--------|------|-------|
| `theme.py` | Tokens light/dark + feuille de style | oui |
| `formatting.py` | Nombres, dates et vocabulaire en français | oui |
| `components.py` | Fragments HTML (badges, cartes, jauges) | oui |
| `charts.py` | Constructeurs Altair (piste synthétique) | oui |
| `catalogue_view.py` | Constructeurs Altair (catalogue public) | oui |
| `ui.py` | Coquille Streamlit — héros, filtres, sections | non |
| `agent_view.py` | Coquille commune aux trois pages d'agents | non |
| `db.py` | Session SQLAlchemy | non |

Les tests correspondants sont sous `tests/dashboard/`.

## Thème

`.streamlit/config.toml` colore ce que Streamlit peint lui-même (boutons,
tableaux, métriques, barre latérale) ; `theme.py` colore ce que l'on dessine
soi-même. Les deux déclarent les modes clair **et** sombre, donc le sélecteur de
thème de Streamlit continue de fonctionner — `ui.active_tokens()` lit
`st.context.theme` et sert le jeu de tokens correspondant.

Deux palettes cohabitent et sont volontairement séparées :

- **Chrome de marque** — vert profond et or. Identifie *le produit*.
- **Palette de données** — ordre catégoriel, rampe ordinale verte, couleurs de
  statut. Identifie *les données*.

Le vert de marque n'encode jamais une valeur, et aucune couleur de série ne sert
au chrome : sinon une teinte voudrait dire deux choses à la fois.

Les palettes ont été vérifiées avec le validateur data-viz contre les surfaces
réelles (`#fcfcfb` en clair, `#141c19` en sombre), pas à l'œil :

| Palette | Clair | Sombre |
|---------|-------|--------|
| Catégoriel (8) | CVD ΔE 9,1 · vision normale ΔE 19,6 | CVD ΔE 8,4 · tout ≥ 3:1 |
| Rampe entonnoir (5) | monotone, ΔL ≥ 0,06, extrémité claire 2,11:1 | idem, 2,67:1 |

En mode clair, l'aqua, le jaune et le magenta passent sous 3:1 : chaque
graphique qui les emploie porte donc des étiquettes directes **et** un tableau
jumeau (`ui.table_twin`). Aucune valeur n'est accessible par la seule couleur.

## Animation

Entrées en fondu-montée décalées, survol soulevé sur les cartes, jauges qui se
remplissent, dégradé de héros en dérive lente. Tout est court (≈ 380 ms) parce
que Streamlit repeint la page à chaque interaction : plus long, un changement de
filtre donnerait l'impression d'un rechargement. Le tout est neutralisé sous
`prefers-reduced-motion`.
