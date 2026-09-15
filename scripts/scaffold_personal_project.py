#!/usr/bin/env python3
"""
Personal Project Scaffolder (scaffold_personal_project.py)

Usage:
  python scripts/scaffold_personal_project.py --name <slug> [--desc "<description>"] [--template <web|cli|python>]

Bootstraps a new independent repository inside projects/<slug>:
1. Initializes Git repo.
2. Creates isolated .gitignore (.env, .vscode, node_modules).
3. Creates README.md and .env.example.
4. Pre-configures Antigravity / OpenCode GCP integration.
"""

import os
import sys
import subprocess
import argparse

# Windows console UTF-8 fix
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GITIGNORE_TEMPLATE = """# Dependencies & Builds
node_modules/
dist/
build/
__pycache__/
*.py[cod]
.venv/
venv/

# Environment & Secrets (Inherits from parent hub if desired)
.env
.env.local
.env.*.local
*.pem
*.key

# IDE & Caches
.vscode/
.idea/
.antigravity/
.gemini/
.opencode/
Thumbs.db
.DS_Store
"""

ENV_EXAMPLE_TEMPLATE = """# Project Environment Configuration
# Inherits settings from C:\\personal\\naquuuu\\.env
GOOGLE_CLOUD_PROJECT=your-personal-gcp-project-id
GOOGLE_CLOUD_REGION=asia-southeast1
GEMINI_API_KEY=AIzaSy_YOUR_PERSONAL_KEY
"""

README_TEMPLATE = """# {name}

{desc}

---

## Architecture
- Managed as an independent repository under the `naquuuu` personal hub.
- Shared AI tooling powered by Google Cloud & Gemini API.

---

## Setup & Run
```bash
# Copy environment configuration
cp .env.example .env
```
"""

def scaffold(name, desc, template):
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    projects_dir = os.path.join(workspace_root, "projects")
    target_dir = os.path.join(projects_dir, name)

    if os.path.exists(target_dir):
        print(f"❌ Project directory already exists: {target_dir}")
        return 1

    print(f"🚀 Scaffolding new personal project: '{name}' in projects/...")
    os.makedirs(target_dir, exist_ok=True)

    # 1. git init
    try:
        subprocess.run(["git", "init", target_dir], check=True, capture_output=True)
        print(f"   ✅ Git repository initialized.")
    except Exception as e:
        print(f"   ⚠️ Could not initialize git: {e}")

    # 2. .gitignore
    with open(os.path.join(target_dir, ".gitignore"), "w", encoding="utf-8") as f:
        f.write(GITIGNORE_TEMPLATE)
    print(f"   ✅ .gitignore created.")

    # 3. .env.example
    with open(os.path.join(target_dir, ".env.example"), "w", encoding="utf-8") as f:
        f.write(ENV_EXAMPLE_TEMPLATE)
    print(f"   ✅ .env.example created.")

    # 4. README.md
    with open(os.path.join(target_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(README_TEMPLATE.format(name=name, desc=desc or "Personal project managed in naquuuu engineering hub."))
    print(f"   ✅ README.md created.")

    print("\n🎉 Scaffolding complete!")
    print(f"📁 Location: {target_dir}")
    print(f"👉 Next steps: Open directory, connect your GitHub remote origin with:")
    print(f"   git -C projects/{name} remote add origin https://github.com/naquuuu/{name}.git")
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scaffold a new independent repository in the personal hub")
    parser.add_argument("--name", required=True, help="Slug/name for the project directory")
    parser.add_argument("--desc", default="", help="Short project description")
    parser.add_argument("--template", default="web", choices=["web", "cli", "python"], help="Project template type")
    args = parser.parse_args()

    sys.exit(scaffold(args.name, args.desc, args.template))
