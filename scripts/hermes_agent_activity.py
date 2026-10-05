"""Privacy-limited OpenCode activity summary for the Hermes dashboard."""
from pathlib import Path
from datetime import datetime, timezone
try:
    import render_agent_viz as viz
except ModuleNotFoundError:
    from scripts import render_agent_viz as viz

ROLES = {
    'naquuuubot': ('orchestrator', 'Coordinates engineering work.'),
    'naquuuu-curator': ('curator', 'Shapes creative direction.'),
    'naquuuu-builder': ('builder', 'Builds and fixes code.'),
    'naquuuu-scribe': ('scribe', 'Writes and maintains docs.'),
    'naquuuu-librarian': ('librarian', 'Finds supporting knowledge.'),
    'naquuuu-skeptic': ('reviewer', 'Challenges assumptions.'),
    'naquuuu-verifier': ('verifier', 'Checks the result.'),
}

def summary(root: Path) -> dict:
    """Allowlist fields; never return paths, IDs, prompts, or commands."""
    try:
        source = viz.resolve_session_file(root, None)
        state = viz.build_state(root, source)
    except (FileNotFoundError, OSError, ValueError):
        return {'available': False, 'agents': [], 'tasks': {}, 'fresh': False}
    age = max(0, datetime.now(timezone.utc).timestamp() - source.stat().st_mtime)
    fresh = age < 300
    agents = []
    for a in state.agents:
        if a.name not in ROLES:
            continue
        label, description = ROLES[a.name]
        agents.append({'name': label, 'description': description,
                       'status': a.status if fresh else 'idle',
                       'tasks': a.tasks, 'tools': a.tools, 'files': a.files,
                       'errors': a.errors})
    counts = {key: sum(t.get('status') == key for t in state.tasks)
              for key in ('pending', 'in_progress', 'completed')}
    return {'available': True, 'fresh': fresh, 'age_seconds': round(age),
            'agents': agents, 'tasks': counts, 'handoffs': len(state.edges)}
