# Catalogue insights

Independent reading of the **public** Finary YouTube catalogue (YouTube Data API,
read-only). Not affiliated with Finary.

| Artifact | Role |
|----------|------|
| `catalogue-finary.html` | Static narrative (French) — five readings + charts, for sharing as a file |
| Streamlit **Catalogue public** | The live page — same five readings, every number recomputed from the current DB |

Facts come from `public_signal_analysis`. Which findings matter, and why, is human
INTERPRETATION. Signups and conversion are never estimated.

The Streamlit page holds no hard-coded figures: every number in its narrative is
derived from the report the service returns, so a new ingest updates the prose
along with the charts. The HTML file is a point-in-time snapshot by design and
carries its own collection date.
