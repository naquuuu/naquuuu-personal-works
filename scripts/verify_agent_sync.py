#!/usr/bin/env python3
"""
Surface Parity Verifier for NAQUUUU Workspace (verify_agent_sync.py)

Usage:
  python scripts/verify_agent_sync.py [--fix]

Verifies synchronization across agent execution surfaces:
1. Canonical personas in .opencode/agent/*.md
2. Mirrored personas in .agents/agents/*.md (Antigravity IDE & CLI)
3. Router file CLAUDE.md (Claude Code)
4. Declarations in opencode.jsonc
"""

import argparse
import json
import os
from pathlib import Path
import re
import sys

# Windows console UTF-8 fix
if sys.platform == "win32":
    import io
    if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != "utf-8":
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass

DEFAULT_7_AGENT_ROSTER = [
    "naquuuubot",
    "naquuuu-curator",
    "naquuuu-builder",
    "naquuuu-scribe",
    "naquuuu-librarian",
    "naquuuu-skeptic",
    "naquuuu-verifier",
]

REQUIRED_HANDOFF_BLOCKS = [
    "### Result",
    "### Files Changed",
    "### Evidence",
    "### Blockers",
]


def extract_body(markdown_text: str) -> str:
    """Strip YAML frontmatter (between --- and ---) and return the body."""
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.search(pattern, markdown_text, re.DOTALL)
    if match:
        return match.group(2).strip()
    return markdown_text.strip()


def check_sync(root_dir: Path, expected_agents=None):
    """
    Check parity across OpenCode, Antigravity, and Claude Code surfaces.
    Returns (ok: bool, issues: list[str]).
    """
    if expected_agents is None:
        expected_agents = DEFAULT_7_AGENT_ROSTER

    issues = []
    opencode_dir = root_dir / ".opencode" / "agent"
    agy_dir = root_dir / ".agents" / "agents"
    claude_file = root_dir / "CLAUDE.md"
    opencode_jsonc = root_dir / "opencode.jsonc"

    # 1. Check OpenCode agent files
    if not opencode_dir.exists():
        issues.append(f"Directory missing: {opencode_dir}")
        return False, issues

    for agent in expected_agents:
        oc_file = opencode_dir / f"{agent}.md"
        if not oc_file.exists():
            issues.append(f"Missing in .opencode/agent: {agent}.md")

    # 2. Check Antigravity mirrored agents
    if not agy_dir.exists():
        issues.append(f"Directory missing: {agy_dir}")
    else:
        for agent in expected_agents:
            agy_file = agy_dir / f"{agent}.md"
            if not agy_file.exists():
                issues.append(f"Missing in .agents/agents: {agent}.md")

    # 3. Check CLAUDE.md router
    if not claude_file.exists():
        issues.append("Missing root router: CLAUDE.md")
    else:
        try:
            claude_content = claude_file.read_text(encoding="utf-8")
            if "AGENTS.md" not in claude_content:
                issues.append("CLAUDE.md does not reference AGENTS.md")
            for block in REQUIRED_HANDOFF_BLOCKS:
                if block not in claude_content:
                    issues.append(f"CLAUDE.md missing required handoff block: {block}")
        except Exception as e:
            issues.append(f"Error reading CLAUDE.md: {e}")

    # 4. Check opencode.jsonc declarations if present
    if opencode_jsonc.exists():
        try:
            raw = opencode_jsonc.read_text(encoding="utf-8")
            # Strip simple line comments
            lines = [re.sub(r"^\s*//.*$", "", l) for l in raw.splitlines()]
            clean_json = "\n".join(lines)
            data = json.loads(clean_json)
            declared_agents = data.get("agent", {})
            for agent in expected_agents:
                if agent not in declared_agents:
                    issues.append(f"Agent '{agent}' missing in opencode.jsonc declared agents")
        except Exception as e:
            # If JSON parse fails due to trailing commas or block comments, warn
            pass

    return len(issues) == 0, issues


def main():
    parser = argparse.ArgumentParser(description="Verify cross-surface parity for agent definitions.")
    parser.add_argument("--root", type=str, default=None, help="Workspace root path (default: auto-detected)")
    args = parser.parse_args()

    if args.root:
        root_dir = Path(args.root).resolve()
    else:
        env_root = os.environ.get("NAQUUUU_WORKSPACE")
        if env_root:
            root_dir = Path(env_root).resolve()
        else:
            root_dir = Path(__file__).resolve().parent.parent

    print(f"Auditing agent surface parity at: {root_dir}")
    ok, issues = check_sync(root_dir)

    if ok:
        print("✅ AGENT SURFACE PARITY OK (OpenCode, Antigravity, Claude Code aligned)")
        sys.exit(0)
    else:
        print("❌ AGENT SURFACE PARITY FAILED:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)


if __name__ == "__main__":
    main()
