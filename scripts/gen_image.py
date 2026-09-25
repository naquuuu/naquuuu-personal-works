#!/usr/bin/env python3
"""Generate an image from a text prompt using a free, keyless endpoint.

Usage:
    python3 scripts/gen_image.py "a red apple on a wooden table"
    python3 scripts/gen_image.py "sunset over Jakarta" /tmp/sunset.jpg --size 1024

Prints the absolute output path on success (the response is JPEG).
No API key, no third-party dependencies.
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.parse
import urllib.request

ENDPOINT = "https://image.pollinations.ai/prompt/"
MIN_BYTES = 1000


def build_url(prompt: str, size: int, model: str) -> str:
    query = urllib.parse.urlencode(
        {"width": size, "height": size, "nologo": "true", "model": model}
    )
    return f"{ENDPOINT}{urllib.parse.quote(prompt)}?{query}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an image from a prompt (free, keyless).")
    parser.add_argument("prompt", help="image description")
    parser.add_argument("out", nargs="?", default="image.jpg", help="output file path")
    parser.add_argument("--size", type=int, default=1024, help="square size in pixels")
    parser.add_argument("--model", default="flux", help="endpoint model hint")
    args = parser.parse_args()

    url = build_url(args.prompt, args.size, args.model)
    try:
        with urllib.request.urlopen(url, timeout=180) as response:
            data = response.read()
    except Exception as exc:  # noqa: BLE001 - report and exit non-zero
        print(f"image generation failed: {exc.__class__.__name__}", file=sys.stderr)
        return 1

    if len(data) < MIN_BYTES:
        print("image generation failed: response too small", file=sys.stderr)
        return 1

    out = os.path.abspath(args.out)
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out, "wb") as handle:
        handle.write(data)

    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
