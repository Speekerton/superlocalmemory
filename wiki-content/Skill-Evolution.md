# Skill Evolution

Agent skills (the `SKILL.md` files that tell an assistant how to do a recurring job) go stale. Skill Evolution watches how skills perform, proposes improved versions, and puts every proposal through verification and your approval before it goes live. It is off by default, and it never runs inside a recall or a remember.

## How a skill changes

The pipeline has six steps: a trigger fires, a cheap screen filters it, a model confirms the problem, a mutation is generated, a separate blind verifier checks it, and the result is persisted.

Triggers are three: the end of a session (the Stop hook), a drop in a behavioural assertion about a skill, and a periodic health check. A change is one of three types: `fix` repairs a skill that is failing, `derived` creates a variant, and `captured` records a new skill from observed behaviour.

A verified change does not go live. It is held in quarantine under `quarantine/skills` in the data folder and moves through the states candidate, verified and quarantined, approved, active (or rejected, or rolled back). Only a person approves a change, unless you set `SLM_EVO_AUTO_APPROVE`, which is off by default. Why: an agent that rewrites its own instructions without review can drift, so the engine is built so that it cannot approve its own work. For the same reason the blind verifier must use a different model from the generator.

## Turning it on

The dashboard's **Skill Evolution** pane has an Evolution engine card with an enable switch, a backend choice and a "Run one evolution cycle" button. From the terminal, run `slm config set evolution.enabled true`. The backend is `auto`, `claude`, `ollama`, `anthropic` or `openai`. Auto picks the first available of the `claude` CLI, then Ollama, then an API key, and otherwise leaves you with the dashboard only. At most 3 evolutions run per cycle, and the mutation, verification and confirmation models default to the cheapest capable one.

## What you see

The pane shows a KPI strip, a lineage diagram of each skill's versions, the engine card, and a performance table built from the behavioural assertions recorded for skills. The lineage diagram is the closest thing to a matrix view: it shows each skill and the chain of versions derived from it. The MCP tools `evolve_skill`, `skill_health` and `skill_lineage` (in the `full` and `power` profiles) give an agent the same information, and the HTTP routes under `/api/evolution/` cover status, enable, disable, run, config, lineage, approve and rollback.

## Where it stores things

The evolution log, per-cycle state and state transitions are in `memory.db`. The evolution configuration and LLM cost log are in `learning.db`.

Code: `evolution/skill_evolver.py`, `evolution/triggers.py`, `evolution/types.py`, `evolution/evolution_store.py`, `mcp/tools_evolution.py`, `server/routes/evolution.py`, `core/config.py` (`EvolutionConfig`).
