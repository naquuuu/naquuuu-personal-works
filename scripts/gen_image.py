#!/usr/bin/env python3
"""Generate an image from a text prompt with the Gemini API.

Usage:
    python3 scripts/gen_image.py "a red apple on a wooden table"
    python3 scripts/gen_image.py "sunset over Jakarta" /tmp/sunset.png

Reads the API key from GEMINI_IMAGE_KEY (falls back to GOOGLE_API_KEY, then to
~/.hermes/.env). Prints the absolute output path on success. Stdlib only.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.request

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MODELS = ("gemini-3.1-flash-image", "gemini-2.5-flash-image", "gemini-3-pro-image")
KEY_NAMES = ("GEMINI_IMAGE_KEY", "GOOGLE_API_KEY")


def from_env_file(name: str) -> str | None:
    path = os.path.join(os.path.expanduser("~"), ".hermes", ".env")
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.strip()
                if line.startswith(f"{name}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        return None
    return None


def api_key() -> str | None:
    for name in KEY_NAMES:
        value = os.environ.get(name) or from_env_file(name)
        if value:
            return value
    return None


def generate(prompt: str, model: str, key: str, timeout: int = 180) -> bytes | None:
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    request = urllib.request.Request(
        API.format(model=model),
        data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except Exception as exc:  # noqa: BLE001 - report and try the next model
        print(f"{model}: {exc.__class__.__name__}", file=sys.stderr)
        return None

    for candidate in payload.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data") or {}
            data = inline.get("data")
            if data:
                return base64.b64decode(data)
    print(f"{model}: no image in response", file=sys.stderr)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an image with the Gemini API.")
    parser.add_argument("prompt", help="image description")
    parser.add_argument("out", nargs="?", default="/tmp/out.png", help="output file path")
    parser.add_argument("--model", default=MODELS[0], help="preferred image model")
    args = parser.parse_args()

    key = api_key()
    if not key:
        print("missing GEMINI_IMAGE_KEY (and no GOOGLE_API_KEY fallback)", file=sys.stderr)
        return 1

    models = [args.model] + [model for model in MODELS if model != args.model]
    data: bytes | None = None
    for model in models:
        data = generate(args.prompt, model, key)
        if data:
            break
    if not data or len(data) < 1000:
        print("image generation failed", file=sys.stderr)
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
