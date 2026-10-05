"""Mounted by Hermes under its existing authenticated plugin API."""
import asyncio
import os
import sys
from pathlib import Path
from fastapi import APIRouter

# Helper code is versioned separately from private Hermes state.
sys.path.insert(0, str(Path.home() / '.local/share/naquuuu/relay-guards'))
from hermes_agent_activity import summary

router = APIRouter()

@router.get('/activity')
async def activity():
    root = os.environ.get('NAQUUUU_WORKSPACE')
    if not root:
        return {'available': False, 'agents': [], 'tasks': {}, 'fresh': False}
    return await asyncio.to_thread(summary, Path(root))
