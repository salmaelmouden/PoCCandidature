# Naming Conventions

## Python

| Kind | Convention | Example |
|------|------------|---------|
| Class | PascalCase | `FunnelAnalysisSkill` |
| Function / variable | snake_case | `calculate_dropoffs` |
| Constant | UPPER_SNAKE_CASE | `DEFAULT_FUNNEL_STAGES` |
| Module / file | snake_case | `funnel_analysis` |
| Private | `_leading_underscore` | `_validate_period` |

## Agents

- Identity: `growth_data_analyst_agent`
- Class: `GrowthDataAnalystAgent`
- Package: `app/agents/growth_data_analyst/`

## Skills

- Identity: `funnel_analysis`
- Package: `app/skills/funnel_analysis/`

## Evaluation cases

`eval_<area>_<short_name>` — e.g. `eval_analyst_premium_conversion_drop`

## Commits

Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`

## Channels & topics (domain vocabulary)

**Channels:** YouTube, Organic Search, LinkedIn, Instagram, Paid, Direct  

**Topics:** ETFs, Stocks, Crypto, Personal Finance, Real Estate, Budgeting  

**Funnel:** Views → Visits → Signups → Activated Users → Premium Users
