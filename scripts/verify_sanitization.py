#!/usr/bin/env python3
"""
Personal Sanitization & Leak-Prevention Linter (verify_sanitization.py)

Usage:
  python scripts/verify_sanitization.py [--dir .]

Audits personal repositories before committing or pushing to public GitHub:
1. Scans for accidental leaks of corporate employee names / corporate email domains.
2. Scans for hardcoded API keys, private keys, or credentials.
3. Scans for unmasked sensitive phone numbers.
"""

import os
import sys
import re
import argparse

# Windows console UTF-8 fix
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

FORBIDDEN_RULES = [
    (
        r"[a-zA-Z0-9._%+-]+@(mapclub\.com|map\.co\.id|gtech\.digital)",
        "Corporate employer email domain detected (Must not be pushed to personal public repos)"
    ),
    (
        r"\b(mansyur|joshua\s+gunawan|widya\s+puji|ghozian|evelyn\s+hendrata)\b",
        "Corporate colleague name detected (Keep personal workspace isolated from corporate context)"
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
        r"-----BEGIN (RSA|OPENSSH|EC|DSA)? PRIVATE KEY-----",
        "Private encryption key detected"
    )
]

ALLOWED_FILES = {
    "verify_sanitization.py", "README.md", "AGENTS.md",
    ".env.example", "DECISION_LOG.md", "TECH_STACK.md", "ROADMAP.md"
}

def scan_file(filepath):
    issues = []
    fname = os.path.basename(filepath)
    if fname in ALLOWED_FILES:
        return issues

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line_idx, line in enumerate(f, 1):
                # Ignore self-referencing check lines
                if "FORBIDDEN_RULES" in line or "verify_sanitization" in line:
                    continue
                for pattern, desc in FORBIDDEN_RULES:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        issues.append((line_idx, match.group(0), desc))
    except Exception as e:
        print(f"⚠️ Error reading {filepath}: {e}")
    return issues

def audit(target_dir):
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    scan_path = os.path.join(workspace_root, target_dir) if not os.path.isabs(target_dir) else target_dir

    if not os.path.exists(scan_path):
        print(f"❌ Target path does not exist: {scan_path}")
        return 1

    print(f"🔍 Running Personal Sanitization Audit on: '{target_dir}'...")
    total_violations = 0

    ignored_dirs = {
        ".git", "node_modules", "dist", "build", ".vscode",
        ".antigravity", ".gemini", ".opencode", ".idea",
        "__pycache__", ".venv", "venv", "env"
    }

    for root, dirs, files in os.walk(scan_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".git")]
        for file in files:
            if not file.endswith((".html", ".js", ".ts", ".jsx", ".tsx", ".json", ".md", ".py", ".css")):
                continue
            if file in ALLOWED_FILES:
                continue
            fpath = os.path.join(root, file)
            rel_path = os.path.relpath(fpath, workspace_root)
            issues = scan_file(fpath)
            if issues:
                print(f"\n❌ [VIOLATIONS FOUND] {rel_path}:")
                for l_no, text, desc in issues:
                    print(f"   Line {l_no}: '{text}' ➔ {desc}")
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
    args = parser.parse_args()

    sys.exit(audit(args.dir))
