#!/usr/bin/env python3
"""
Four-Block Handoff Contract Validator for NAQUUUU Workspace (verify_handoff.py)

Usage:
  python scripts/verify_handoff.py --file <path>
  python scripts/verify_handoff.py --text "<markdown>"
  cat output.md | python scripts/verify_handoff.py

Validates the universal Four-Block Handoff:
  ### Result
  ### Files Changed
  ### Evidence
  ### Blockers
"""

import argparse
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

REQUIRED_BLOCKS = [
    "### Result",
    "### Files Changed",
    "### Evidence",
    "### Blockers",
]


def validate_handoff(text: str):
    """
    Validate that text contains all required four blocks and non-empty content.
    Returns (ok: bool, errors: list[str]).
    """
    errors = []
    if not text or not text.strip():
        return False, ["Input text is empty"]

    # Check presence and order
    indices = {}
    for block in REQUIRED_BLOCKS:
        pos = text.find(block)
        if pos == -1:
            errors.append(f"Missing required block: '{block}'")
        else:
            indices[block] = pos

    if errors:
        return False, errors

    # Extract sections
    sorted_blocks = sorted(indices.items(), key=lambda x: x[1])
    for i, (block, start_pos) in enumerate(sorted_blocks):
        content_start = start_pos + len(block)
        if i + 1 < len(sorted_blocks):
            content_end = sorted_blocks[i + 1][1]
        else:
            content_end = len(text)

        section_body = text[content_start:content_end].strip()
        if not section_body:
            errors.append(f"Section '{block}' is empty")

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description="Validate Four-Block Handoff format.")
    parser.add_argument("--file", type=str, default=None, help="Path to markdown file")
    parser.add_argument("--text", type=str, default=None, help="Markdown text string to validate")
    args = parser.parse_args()

    content = ""
    if args.file:
        content = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        content = args.text
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        parser.print_help()
        sys.exit(1)

    ok, errors = validate_handoff(content)
    if ok:
        print("✅ FOUR-BLOCK HANDOFF VALIDATED")
        sys.exit(0)
    else:
        print("❌ FOUR-BLOCK HANDOFF INVALID:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
