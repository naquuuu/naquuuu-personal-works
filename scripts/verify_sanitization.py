#!/usr/bin/env python3
"""
Personal Sanitization & Leak-Prevention Linter (verify_sanitization.py)

Usage:
  python scripts/verify_sanitization.py [--dir .] [--all | --staged]

Audits personal repositories before committing or pushing to public GitHub:
1. Scans for accidental leaks of corporate employee names / corporate email domains.
2. Scans for hardcoded API keys, private keys, or credentials.
3. Scans for unmasked sensitive phone numbers.

Scope (mutually exclusive, pick one):
  default   git-tracked files only, because a manual pre-commit gate audits what
            is already tracked. Untracked/ignored artifacts (e.g. scraped raw
            dumps) are out of scope.
  --all     the raw working tree, including untracked and ignored output.
  --staged  the git index: exactly the snapshot the next commit would contain.
            Auto-sync stages first and then gates, so the tracked-only default
            would skip a brand-new file that was never tracked. --staged closes
            that hole: it reads each staged path's blob out of the index, not the
            working tree, and is the only scope that sees a file created in the
            same run. Deletions are excluded (no content to audit).

Fail-closed: if --staged cannot enumerate the index (not a git repository, git
fails), it reports a named condition and exits non-zero. Never a silent pass.
"""

import os
import sys
import re
import subprocess
import argparse

# Windows console UTF-8 fix
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

FORBIDDEN_RULES = [
    (
        r"[a-zA-Z0-9._%+-]{1,64}@(mapclub\.com|map\.co\.id|gtech\.digital)",
        "Corporate employer email domain detected (Must not be pushed to personal public repos)"
    ),
    (
        r"\b(mansyur|joshua\s+gunawan|widya\s+puji|ghozian|evelyn\s+hendrata)\b",
        "Corporate colleague name detected (Keep personal workspace isolated from corporate context)"
    ),
    (
        r"mapclub[-_]po",
        "Corporate workspace identifier detected (keep the personal hub isolated)"
    ),
    (
        r"(['\"]?api[_-]?key['\"]?\s*[:=]\s*['\"][a-zA-Z0-9_\-]{20,}['\"])",
        "Potential hardcoded API key or private credential detected"
    ),
    (
        r"(AIzaSy[a-zA-Z0-9_\-]{33})",
        "Google Gemini API Key pattern detected in plaintext"
    ),
    (
        r"(dop_v1_[a-zA-Z0-9_\-]{16,})",
        "Unmasked DigitalOcean access token detected (must be redacted or removed)"
    ),
    (
        r"(actions\.do-ai\.run/mcp/session/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
        "Live Action Gateway session URL detected (store only the redacted form https://actions.do-ai.run/mcp/session/<id>)"
    ),
    (
        r"-----BEGIN (RSA|OPENSSH|EC|DSA)? PRIVATE KEY-----",
        "Private encryption key detected"
    ),
    (
        r"(?<!\d)(\+62|62|0)8\d{7,12}(?!\d)",
        "Unmasked Indonesian phone number detected (must be redacted or removed)"
    )
]

ALLOWED_FILES = {
    "verify_sanitization.py", "README.md", "AGENTS.md",
    "DECISION_LOG.md", "TECH_STACK.md", "ROADMAP.md"
}

# Public contact numbers the owner intentionally publishes (e.g. the blog
# inquiry button). Canonical form: digits only, country code 62, no plus.
ALLOWED_PHONE_NUMBERS = {
    "6282112255009",
}

# .sh / .ps1 / .jsonc / .yml / .yaml are in scope because the fail-closed gate
# itself lives inside node_autosync.sh and hub_autosync.ps1: without these a
# credential in the very scripts that guard the remote is undetectable.
SCAN_EXTENSIONS = (
    ".html", ".js", ".ts", ".jsx", ".tsx", ".json", ".jsonc", ".md", ".py",
    ".css", ".txt", ".sh", ".ps1", ".yml", ".yaml"
)

# Tracked files that carry no scannable extension but must still be audited.
# Matched against BOTH the basename and the repo-relative path, so the two
# extensionless gate hooks (.githooks/pre-commit, .githooks/pre-push) are
# covered in every scope: they have no suffix, but they are the commit and push
# gate itself. The bare basenames are listed too so --all, which walks the tree
# without a repo-relative path, still audits the hooks.
SCAN_FILENAMES = {
    ".env.example",
    ".githooks/pre-commit",
    ".githooks/pre-push",
    "pre-commit",
    "pre-push",
}

def normalize_phone(raw):
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("62"):
        return digits
    if digits.startswith("0"):
        return "62" + digits[1:]
    return "62" + digits

class GateError(Exception):
    """Named fail-closed condition: the gate could not establish what to audit.

    Carries the condition name and an actionable remedy so the caller can
    report both. Never used for "the tree is clean" - only for "the audit
    could not run", which must never exit 0.
    """

    def __init__(self, condition, remedy):
        super().__init__(condition)
        self.condition = condition
        self.remedy = remedy

def repo_root_for(scan_path):
    """Return the git repo root containing scan_path, or None when not in a repo."""
    top = subprocess.run(
        ["git", "-C", scan_path, "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, encoding="utf-8"
    )
    if top.returncode != 0:
        return None
    root = top.stdout.strip()
    return root or None

def _rel_to_root(scan_path, repo_root):
    return os.path.relpath(os.path.abspath(scan_path), repo_root).replace("\\", "/")

def _is_scannable(abspath, repo_rel):
    """True when the path is in the audited file set (by extension or name)."""
    if abspath.endswith(SCAN_EXTENSIONS):
        return True
    return os.path.basename(abspath) in SCAN_FILENAMES or repo_rel in SCAN_FILENAMES

def tracked_files(scan_path):
    """Return tracked files under scan_path, or None when not inside a git repo."""
    try:
        repo_root = repo_root_for(scan_path)
        if repo_root is None:
            return None
        rel = _rel_to_root(scan_path, repo_root)
        args = ["git", "-C", repo_root, "ls-files", "-z"]
        if rel != ".":
            args += ["--", rel]
        listing = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
        if listing.returncode != 0:
            return None
        files = []
        for name in listing.stdout.split("\0"):
            if not name:
                continue
            fpath = os.path.join(repo_root, name)
            if os.path.isfile(fpath):
                files.append((fpath, name))
        return files
    except Exception:
        return None

def staged_files(scan_path):
    """Return the staged snapshot: [(abspath, repo_rel, text)].

    Enumerates the git INDEX (what a commit would contain), not the working
    tree, so a file staged in this same run cannot be skipped. Deletions are
    excluded via --diff-filter=ACMR: a deleted path has no content to audit.

    Raises GateError (fail closed) when the target is not inside a git
    repository, when git fails, or when a staged blob cannot be read.
    """
    repo_root = repo_root_for(scan_path)
    if repo_root is None:
        raise GateError(
            f"'{scan_path}' is not inside a git repository (git rev-parse --show-toplevel failed)",
            "run the gate from inside a repository checkout, or drop --staged to audit git-tracked files"
        )

    rel = _rel_to_root(scan_path, repo_root)
    args = ["git", "-C", repo_root, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]
    if rel != ".":
        args += ["--", rel]
    listing = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    if listing.returncode != 0:
        raise GateError(
            f"git could not enumerate the staged snapshot (exit {listing.returncode}: "
            f"{(listing.stderr or '').strip() or 'no stderr'})",
            "check the index with 'git status' and 'git diff --cached --name-only'; "
            "unstage with 'git restore --staged .' if it is corrupt"
        )

    entries = []
    seen = set()
    for name in listing.stdout.split("\0"):
        if not name or name in seen:
            continue
        seen.add(name)
        # Index paths are repo-relative by construction; anything absolute or
        # escaping the root is refused rather than read.
        if os.path.isabs(name) or name.startswith("../") or "/../" in name:
            raise GateError(
                f"staged path '{name}' escapes the repository root",
                "unstage the offending path with 'git restore --staged .' and re-add it correctly"
            )
        abspath = os.path.join(repo_root, name)
        blob = subprocess.run(
            ["git", "-C", repo_root, "show", ":" + name],
            capture_output=True
        )
        if blob.returncode != 0:
            raise GateError(
                f"staged blob for '{name}' could not be read from the index (exit {blob.returncode})",
                "unstage with 'git restore --staged .' and re-add the file, then re-run the gate"
            )
        entries.append((abspath, name, blob.stdout.decode("utf-8", errors="ignore")))
    return entries

def scan_text(text):
    """Apply FORBIDDEN_RULES to already-loaded text. Shared by every scope."""
    issues = []
    for line_idx, line in enumerate(text.splitlines(), 1):
        # Ignore self-referencing check lines
        if "FORBIDDEN_RULES" in line or "verify_sanitization" in line:
            continue
        for pattern, desc in FORBIDDEN_RULES:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                if "phone number" in desc and normalize_phone(match.group(0)) in ALLOWED_PHONE_NUMBERS:
                    continue
                issues.append((line_idx, match.group(0), desc))
    return issues

def scan_file(filepath):
    issues = []
    fname = os.path.basename(filepath)
    if fname in ALLOWED_FILES:
        return issues

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return scan_text(f.read())
    except Exception as e:
        print(f"⚠️ Error reading {filepath}: {e}")
    return issues

def audit(target_dir, scan_all=False, staged=False):
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    scan_path = os.path.join(workspace_root, target_dir) if not os.path.isabs(target_dir) else target_dir

    if not os.path.exists(scan_path):
        print(f"❌ Target path does not exist: {scan_path}")
        return 1

    staged_entries = None
    if staged:
        # Enumerate first: the scope line reports the exact file count, and a
        # GateError must be reported before any "Running ... Audit" banner.
        try:
            staged_entries = staged_files(scan_path)
        except GateError as e:
            print(f"❌ [GATE REFUSED] Sanitization gate cannot audit the staged snapshot: {e.condition}")
            print(f"   Fix: {e.remedy}")
            print("-" * 75)
            print("❌ FAILED: staged snapshot was not audited. Failing closed; nothing is cleared for publish.")
            return 1
        scope = f"staged snapshot ({len(staged_entries)} files)"
    else:
        scope = "raw working tree" if scan_all else "git-tracked files"
    print(f"🔍 Running Personal Sanitization Audit on: '{target_dir}' ({scope})...")
    total_violations = 0

    if staged:
        if not staged_entries:
            print("ℹ️ Nothing is staged; the staged snapshot is empty (0 files) - nothing to audit.")
        for abspath, repo_rel, text in staged_entries:
            if not _is_scannable(abspath, repo_rel):
                continue
            if os.path.basename(abspath) in ALLOWED_FILES:
                continue
            rel_path = os.path.relpath(abspath, workspace_root)
            issues = scan_text(text)
            if issues:
                print(f"\n❌ [VIOLATIONS FOUND] {rel_path}:")
                for l_no, text_hit, desc in issues:
                    print(f"   Line {l_no}: '{text_hit}' ➔ {desc}")
                total_violations += len(issues)
    else:
        candidate_files = None if scan_all else tracked_files(scan_path)
        if candidate_files is None:
            candidate_files = []
            ignored_dirs = {
                ".git", "node_modules", "dist", "build", ".vscode",
                ".antigravity", ".gemini", ".opencode", ".idea",
                "__pycache__", ".venv", "venv", "env"
            }
            for root, dirs, files in os.walk(scan_path):
                dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".git")]
                for file in files:
                    candidate_files.append((os.path.join(root, file), None))

        for fpath, repo_rel in candidate_files:
            if not _is_scannable(fpath, repo_rel):
                continue
            if os.path.basename(fpath) in ALLOWED_FILES:
                continue
            rel_path = os.path.relpath(fpath, workspace_root)
            issues = scan_file(fpath)
            if issues:
                print(f"\n❌ [VIOLATIONS FOUND] {rel_path}:")
                for l_no, text_hit, desc in issues:
                    print(f"   Line {l_no}: '{text_hit}' ➔ {desc}")
                total_violations += len(issues)

    print("-" * 75)
    if total_violations == 0:
        print(f"✅ PASSED: Zero corporate leaks or unmasked credentials detected in '{target_dir}'.")
        return 0
    else:
        print(f"❌ FAILED: {total_violations} sanitization violation(s) detected.")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit personal files for corporate leaks and credentials")
    parser.add_argument("--dir", default=".", help="Directory to scan (default: .)")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--all", action="store_true", help="Scan the raw working tree instead of only git-tracked files")
    scope.add_argument(
        "--staged", action="store_true",
        help="Audit the git index: exactly the snapshot the next commit would contain "
             "(use after 'git add -A', as auto-sync does)"
    )
    args = parser.parse_args()

    if args.all and args.staged:
        # Unreachable via the mutually exclusive group; kept as a guard so a
        # future programmatic caller can never silently pick one scope.
        parser.error("--all and --staged are mutually exclusive: pick one scope")
    sys.exit(audit(args.dir, args.all, args.staged))
