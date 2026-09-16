# naquuuu-personal-works — Personal Engineering Hub

> **Personal, Non-Employed Engineering Workspace**  
> Central hub for independent software projects, research explorations, creative web experiments, and portfolio applications.

---

## 🎯 Purpose & Scope

This workspace is strictly dedicated to personal, non-employed engineering activities:
- **Zero Corporate Entanglement**: Maintained with strict isolation from any corporate or client assets.
- **Single GCP / Vertex AI Economy**: All personal AI exploration, scripts, and automation route through a single personal Google Cloud Project.
- **Multi-Repo Architecture**: Manages standalone projects and repositories without the brittleness of git submodules.

---

## 📂 Workspace Structure

```
naquuuu-personal-works/
├── .env.example                      # Template for personal GCP & Gemini keys
├── AGENTS.md                         # Operating Guide & Definition of Done
├── README.md                         # Hub directory & active project index
├── blog/                             # Personal blog & portfolio (naquuuu.github.io repo)
├── internal-docs/                    # Architectural decisions & roadmaps
│   ├── DECISION_LOG.md
│   ├── ROADMAP.md
│   └── TECH_STACK.md
├── projects/                         # Additional standalone GitHub repositories
└── scripts/                          # Workspace automation & QA gates
    ├── sync_all_repos.py             # Multi-repo status checker
    ├── verify_sanitization.py        # Leak-prevention auditor
    └── scaffold_personal_project.py  # New project generator
```

---

## 🌐 Repositories Overview

| Repository | Local Path | Purpose | GitHub Remote |
| :--- | :--- | :--- | :--- |
| **Personal Works (Hub)** | `.` | Meta-hub, operating guides, QA scripts, workspace orchestration | [naquuuu/naquuuu-personal-works](https://github.com/naquuuu/naquuuu-personal-works) |
| **Blog & Portfolio** | `blog/` | Personal blog & live portfolio (tracked independently) | [naquuuu/naquuuu.github.io](https://github.com/naquuuu/naquuuu.github.io) |
| **Random Stuff (Sandbox)** | `projects/random-stuff/` | Quick experiments, prototypes, fun hacks, and ideation spikes | [naquuuu/random-stuff](https://github.com/naquuuu/random-stuff) |
| **BI Scraper (Study Corpus)** | `projects/bi-scraper/` | PCPM/TPD study corpus from public bi.go.id sources (personal use only) | [naquuuu/bi-scraper](https://github.com/naquuuu/bi-scraper) |
| **Dedicated Projects** | `projects/<slug>/` | Standalone long-term apps & tools with their own git lifecycles | Independent GitHub repositories |

> **Note on `blog/` and `projects/`**: Both are git-ignored by this hub repository. Each sub-project maintains its own standalone `.git` history, branch management, and remote origin to prevent git submodule conflicts.

---

## 🧭 How to Decide: Where Does New Work Go?

```
[New Idea or Code]
       │
       ├─► Is it a quick spike, fun hack, test script, or messy prototype?
       │     └──► `projects/random-stuff/` (fast sandbox, low ceremony)
       │
       ├─► Is it a public article, essay, or interactive portfolio piece?
       │     └──► `blog/` (naquuuu.github.io)
       │
       ├─► Is it becoming a serious, standalone tool/app you will maintain?
       │     └──► `projects/<slug>/` (scaffold a dedicated repo)
       │
       └─► Is it workspace automation, QA gates, or global personal configs?
             └──► `.` (naquuuu-personal-works hub)
```

### 🏷️ AI Agent Prompt Tags
Prefix your prompts so AI coding assistants immediately know where code belongs:
- **`[PROJECT: <slug>]`** → Sets up a serious, isolated project in `projects/<slug>/` with dedicated venv, git, and tests.
- **`[SANDBOX]`** or **`[SPIKE]`** → Places quick experiments directly in `projects/random-stuff/`.
- **`[BLOG]`** → Works on articles or portfolio UI in `blog/`.
- **`[HUB]`** → Modifies workspace orchestration, QA scripts, or global configs.

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
