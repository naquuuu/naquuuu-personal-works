#!/usr/bin/env python3
"""
Multi-Repo Auditor for NAQUUUU Personal Workspace (sync_all_repos.py)

Usage:
  python scripts/sync_all_repos.py [--fetch]

Audits all child repositories under projects/:
1. Detects current active branch.
2. Reports uncommitted changes (clean/dirty).
3. Reports unpushed / unpulled commits against remote tracking branch.
"""

import os
import sys
import subprocess
import argparse

# Windows console UTF-8 fix
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def run_git(repo_path, args):
    try:
        res = subprocess.run(
            ["git", "-C", repo_path] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        return None

def audit_projects(fetch=False):
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    projects_dir = os.path.join(workspace_root, "projects")

    repos = []

    # 1. Check direct child repositories (e.g., blog/)
    direct_candidates = ["blog"]
    for d in os.listdir(workspace_root):
        candidate = os.path.join(workspace_root, d)
        if d != ".git" and os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, ".git")):
            if (d, candidate) not in repos:
                repos.append((d, candidate))

    # 2. Check projects/ subdirectories
    if os.path.exists(projects_dir):
        for d in os.listdir(projects_dir):
            candidate = os.path.join(projects_dir, d)
            if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, ".git")):
                repos.append((f"projects/{d}", candidate))

    if not repos:
        print(f"ℹ️ No child git repositories found inside '{workspace_root}'.")
        return 0

    print("=" * 75)
    print(f"  NAQUUUU MULTI-REPO AUDITOR ({len(repos)} Repositories Found)")
    print("=" * 75)

    all_clean = True

    for name, path in sorted(repos):
        if fetch:
            print(f"🔄 Fetching {name}...")
            run_git(path, ["fetch", "--quiet"])

        branch = run_git(path, ["branch", "--show-current"]) or "detached"
        status = run_git(path, ["status", "--short"])
        is_dirty = bool(status)

        # Ahead/behind check
        ahead_behind = ""
        tracking = run_git(path, ["rev-parse", "--abbrev-ref", "@{upstream}"])
        if tracking:
            count = run_git(path, ["rev-list", "--left-right", "--count", f"{tracking}...HEAD"])
            if count:
                behind, ahead = count.split()
                flags = []
                if int(ahead) > 0:
                    flags.append(f"↑{ahead} unpushed")
                if int(behind) > 0:
                    flags.append(f"↓{behind} unpulled")
                if flags:
                    ahead_behind = f" ({', '.join(flags)})"
        else:
            ahead_behind = " (no remote tracking)"

        state_icon = "⚠️ DIRTY" if is_dirty else "✅ CLEAN"
        if is_dirty or "unpushed" in ahead_behind:
            all_clean = False

        print(f"\n📦 {name}")
        print(f"   Branch: {branch}{ahead_behind}")
        print(f"   Status: {state_icon}")

        if is_dirty:
            for line in status.splitlines()[:5]:
                print(f"     {line}")
            if len(status.splitlines()) > 5:
                print(f"     ... and {len(status.splitlines()) - 5} more change(s)")

    print("-" * 75)
    if all_clean:
        print("🎉 ALL REPOSITORIES IN SYNC & CLEAN")
    else:
        print("⚠️ SOME REPOSITORIES REQUIRE ATTENTION (UNCOMMITTED CHANGES OR UNPUSHED COMMITS)")
    print("-" * 75)
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit status across all child repositories")
    parser.add_argument("--fetch", action="store_true", help="Fetch remotes before checking status")
    args = parser.parse_args()

    sys.exit(audit_projects(args.fetch))
