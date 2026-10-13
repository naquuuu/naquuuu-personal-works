# Site-Wide Diagram Redesign Spec (2026-10-05)

- **Subsystem:** `blog` (6 HTML pages under `blog/experience/*`, `blog/blog/*`, and `blog/performance/recovery/*`).
- **Owner Directives (2026-10-05):**
  1. Keep Warm Paper aesthetic (`#F2F2ED` canvas, `#FFFFFF` cards, terracotta/slate/sage/crimson analog washes, lowercase canon, bottom legend per `STYLE_BIBLE.md` 2.8 & `L-22`).
  2. Eliminate the repetitive 3-column vertical swimlane template (`x=32` Input, `x=256` Process, `x=536` Output + vertical dashed dividers at `x=244` and `x=524`) across all 6 pages. Give each page a distinct topology.
  3. **MapClub:** Keep "Product Management" role label. Focus diagram on the AI-assisted BRD workspace (1-to-3 fan-out into `requirements doc`, `process diagram`, `testable prototype` -> `pm review: ready?` diamond with `[no: revise]` loop -> `brd ready: ~1 week -> <=1 day`).
  4. **Traveloka:** Keep `PM 185` in prose; diagram focuses on Refund Policy Completeness with **only one output** (`95.76% refund policy completeness`), showing dual-source convergence (`provider apis` + `airline cat 16 fare rules` via `improved llm-assisted parsing & translation`) and the `anomaly dashboard` feedback loop (`[coordinate provider fix]`).
  5. **BCG:** Keep `geothermal` (PGE clients); remove `top 2-3` from both diagram and prose. Replace process flowchart with a **non-flowchart structural & funnel diagram** (Embedded EPC Client Context + 2-Tier Proposal Conversion Funnel `10+ led` -> `30% final bid stage` + `$400mn+ pipeline` -> `next fy bd roadmap`).
  6. **Blog Gate Hygiene:** Zero em-dashes (`\u2014`) or en-dashes (`\u2013`) in HTML copy, zero `style="...width"`, preserve `flowchart-whiteboard-box` and `principle-strip` classes.

## Topology Matrix

| Page | Topology | ViewBox |
| :--- | :--- | :--- |
| `experience/mapclub/index.html` | 1-to-3 Fan-Out & Convergence Review Loop | `0 0 780 370` |
| `experience/traveloka/index.html` | Dual-Source Convergence + Feedback Loop to Single Output | `0 0 780 370` |
| `experience/bcg/index.html` | 3-Zone Structural Architecture & Proportional Conversion Funnel | `0 0 780 350` |
| `blog/building-an-autonomous-product-operating-system/index.html` | 2-Row Serpentine (Boustrophedon) State Machine | `0 0 780 430` |
| `blog/reverse-engineering-client-binaries/index.html` | Left Source Hub -> Dual Parallel Extraction Lanes -> Right Access Gate | `0 0 780 390` |
| `performance/recovery/index.html` | Horizontal Chronological Timeline Spine + Above/Below Fault Tree | `0 0 780 380` |
