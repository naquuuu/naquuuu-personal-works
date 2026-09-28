#!/usr/bin/env python3
"""
Multi-Repo Auditor for NAQUUUU Personal Workspace (sync_all_repos.py)

Usage:
  python scripts/sync_all_repos.py [--fetch] [--strict] [--check-freshness]

Audits the hub repo itself and all child repositories under projects/:
1. Detects current active branch.
2. Reports uncommitted changes (clean/dirty).
3. Reports unpushed / unpulled commits against remote tracking branch.

--check-freshness (implied by --strict) additionally reports internal-docs/
digests whose "<!-- verified-against: ADR-nnn -->" stamp trails the newest
"## ADR-nnn:" heading in internal-docs/DECISION_LOG.md.
"""

import os
import re
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

def audit_projects(fetch=False, strict=False):
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    projects_dir = os.path.join(workspace_root, "projects")

    repos = []

    # 0. The hub repo itself. Without this an unpushed hub commit is invisible.
    if os.path.exists(os.path.join(workspace_root, ".git")):
        repos.append(("naquuuu (hub)", workspace_root))
    else:
        print(f"ℹ️ No git repository at the workspace root '{workspace_root}'; auditing child repositories only.")

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
    return 0 if all_clean else (1 if strict else 0)

# --- Digest freshness (--check-freshness, implied by --strict) --------------
# Contract: a digest carries exactly one HTML comment line immediately under
# its H1, "<!-- verified-against: ADR-nnn -->". The newest ADR is the highest
# ADR-nnn heading of the form "## ADR-nnn:" in internal-docs/DECISION_LOG.md.
# Comparison is numeric, so ADR-031 < ADR-100.
FRESHNESS_DIGESTS = ("STATUS.md", "LESSONS.md")
STAMP_RE = re.compile(r"<!--\s*verified-against:\s*ADR-([A-Za-z0-9_-]+)\s*-->")
H1_RE = re.compile(r"^#\s+\S")

def newest_adr(workspace_root):
    """Return (newest_adr_number, problem). problem is None when a number is returned."""
    path = os.path.join(workspace_root, "internal-docs", "DECISION_LOG.md")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        return None, f"UNREADABLE - internal-docs/DECISION_LOG.md cannot be read ({e.__class__.__name__})"
    numbers = [int(n) for n in re.findall(r"^##\s+ADR-(\d+)\s*:", text, re.MULTILINE)]
    if not numbers:
        return None, "UNPARSEABLE - no '## ADR-nnn:' heading in internal-docs/DECISION_LOG.md"
    return max(numbers), None

def read_stamp(path):
    """Return (adr_number, condition). condition is None when a usable stamp was read."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        return None, f"UNREADABLE - cannot be read ({e.__class__.__name__})"

    stamps = list(STAMP_RE.finditer(text))
    if not stamps:
        return None, "MISSING - no '<!-- verified-against: ADR-nnn -->' stamp"
    if len(stamps) > 1:
        return None, f"UNPARSEABLE - {len(stamps)} stamps found, expected exactly 1"

    token = stamps[0].group(1)
    if not token.isdigit():
        if token.lower() == "nnn":
            # The documented placeholder (a file quoting the contract, e.g. INDEX.md)
            # is not a stamp at all.
            return None, "MISSING - only the '<!-- verified-against: ADR-nnn -->' placeholder, no real stamp"
        return None, f"UNPARSEABLE - stamp 'ADR-{token}' is not a number"

    lines = text.splitlines()
    h1_line = next((i for i, line in enumerate(lines) if H1_RE.match(line)), None)
    if h1_line is None:
        return None, "UNPARSEABLE - no H1 heading"
    stamp_line = text[:stamps[0].start()].count("\n")
    if stamp_line != h1_line + 1:
        return None, (f"STAMP_MISPLACED - stamp on line {stamp_line + 1}, "
                      f"expected directly under the H1 (line {h1_line + 1})")
    return int(token), None

def audit_freshness(strict=False):
    """Print the freshness block. Returns True when every expected digest is current."""
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    docs_dir = os.path.join(workspace_root, "internal-docs")

    newest, problem = newest_adr(workspace_root)

    expected = [(name, os.path.join(docs_dir, name)) for name in FRESHNESS_DIGESTS]
    expected_paths = {p for _, p in expected}

    others = []
    try:
        for name in sorted(os.listdir(docs_dir)):
            full = os.path.join(docs_dir, name)
            if name.endswith(".md") and os.path.isfile(full) and full not in expected_paths:
                others.append((name, full))
    except OSError as e:
        others = []
        print(f"❌ UNREADABLE - internal-docs/ cannot be listed ({e.__class__.__name__})")

    print("-" * 75)
    print(f"  FRESHNESS  newest ADR: {'ADR-%03d' % newest if newest else 'unknown'}")

    ok = problem is None
    if problem:
        print(f"  ❌ {problem}")

    skipped = 0
    for name, path in expected + others:
        rel = f"internal-docs/{name}"
        is_expected = path in expected_paths
        if not os.path.exists(path):
            if is_expected:
                print(f"  ❌ {rel}  MISSING_FILE - not found")
                ok = False
            continue
        stamp, condition = read_stamp(path)
        if condition:
            if not is_expected and condition.startswith("MISSING"):
                skipped += 1
                continue
            print(f"  ❌ {rel}  {condition}")
            ok = False
        elif newest is None:
            print(f"  ❌ {rel}  UNPARSEABLE - cannot compare against an unknown newest ADR")
            ok = False
        elif stamp < newest:
            print(f"  ❌ {rel}  STALE - verified against ADR-{stamp:03d}, newest is ADR-{newest:03d}")
            ok = False
        else:
            print(f"  ✅ {rel}  ADR-{stamp:03d} (current)")

    if skipped:
        print(f"  ℹ️ {skipped} other internal-docs/*.md carry no stamp (skipped)")

    if ok:
        print("  🎉 DIGEST FRESHNESS OK")
    elif strict:
        print("  ⚠️ DIGEST FRESHNESS: STALE OR UNSTAMPED DIGESTS NEED RE-VERIFICATION")
    else:
        print("  ⚠️ DIGEST FRESHNESS: STALE OR UNSTAMPED DIGESTS (non-strict: warning only)")
    print("-" * 75)
    return ok

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit status across the hub and all child repositories")
    parser.add_argument("--fetch", action="store_true", help="Fetch remotes before checking status")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any repository is dirty or has unpushed commits, or if a digest is stale")
    parser.add_argument("--check-freshness", action="store_true", help="Report digests that trail the newest ADR (implied by --strict)")
    args = parser.parse_args()

    exit_code = audit_projects(args.fetch, args.strict)
    if args.check_freshness or args.strict:
        if not audit_freshness(strict=args.strict) and args.strict:
            exit_code = 1

    sys.exit(exit_code)
