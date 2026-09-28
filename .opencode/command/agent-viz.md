---
description: Render the agent session map for the current session and report who was active.
agent: naquuuubot
---

Render the agent and subagent session map for the hub.

1. Run from the workspace root: `python scripts/render_agent_viz.py $ARGUMENTS --out internal-docs/agent-viz/session-map.html`
   `$ARGUMENTS` is an optional session id filter. Leave it empty to use the most recent session.
2. Add `--serve --open` instead when the owner wants to watch it live. Live mode without `--out` writes nothing into the repository, so it leaves the working tree clean.
3. Report back in plain text, four lines or fewer: the output path, which agents were active, the current in-progress task, and whether the self checks read zero dashes and zero inline width styles.
