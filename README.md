# naquuuu — Personal Engineering Hub

Central hub for personal projects, engineering portfolio, and web explorations. Powered by a single Google Cloud Project and Gemini API configuration with multi-repo orchestration.

---

## Workspace Structure

```
naquuuu/
├── .env.example                      # Template for personal GCP & Gemini keys
├── AGENTS.md                         # Operating Guide & Definition of Done
├── README.md                         # Workspace directory
├── internal-docs/                    # Architectural decisions & roadmaps
│   ├── DECISION_LOG.md
│   ├── ROADMAP.md
│   └── TECH_STACK.md
├── projects/                         # Standalone GitHub repositories
│   └── naquuuu.github.io/            # Blog & portfolio site
└── scripts/                          # Workspace automation & QA gates
    ├── sync_all_repos.py             # Multi-repo status checker
    ├── verify_sanitization.py        # Leak-prevention auditor
    └── scaffold_personal_project.py  # New project generator
```

---

## Active Repositories

| Repository | Path | Purpose | Remote |
| :--- | :--- | :--- | :--- |
| **naquuuu.github.io** | `projects/naquuuu.github.io` | Personal blog & showcase portfolio | [github.com/naquuuu/naquuuu.github.io](https://github.com/naquuuu/naquuuu.github.io) |

---

## Quickstart

### 1. Configure Environment
Copy `.env.example` to `.env` and fill in your personal GCP Project ID and Gemini API key:
```bash
cp .env.example .env
```

### 2. Check Status Across All Projects
Run the multi-repo auditor:
```bash
python scripts/sync_all_repos.py
```

### 3. Verify Sanitization Before Pushing
Ensure no corporate data or unmasked credentials exist in your changes:
```bash
python scripts/verify_sanitization.py
```

### 4. Scaffold a New Project
```bash
python scripts/scaffold_personal_project.py --name "my-new-app"
```
