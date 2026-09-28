---
description: Draft a new blog essay end to end. Curator writes the voice, scaffolder builds the shell, builder fills the prose, verifier gates it. Use when the owner wants a new post on naquuuu.github.io, asks for a weekly essay, or names a topic from the pool.
agent: naquuuubot
---

New essay. Topic or slug from the owner: $ARGUMENTS

If `$ARGUMENTS` is empty, stop and ask for a topic. Do not invent one.

The voice contract is `internal-docs/STYLE_BIBLE.md`. Read it before drafting. It is
law, not inspiration. The curator owns taste; you own routing and the report.

Work in this order. Do not reorder, and do not merge the drafting step into the
build step, because the curator is read-only and the two must not share a writer.

## 1. route the topic

Work out the lens and the slug.

- odd-numbered topics in STYLE_BIBLE section 8 are systems and matter, white theme
- even-numbered are culture and taste, red theme
- if the owner named a topic, infer the lens from it and say which rule you applied
- slug is lowercase kebab-case, three to six words, no dates, no numbers

State the slug and lens back to the owner in one line before spending tokens.

## 2. curator drafts

Delegate to `naquuuu-curator` with the slug, the lens, and the topic. Ask for the
prose only: thesis box, two to five numbered h2 sections, optional outbound link
block, closing concept-box. Ask it to return the eight-check rubric result alongside
the prose, per STYLE_BIBLE section 7.

The curator is read-only. It will not write files. That is correct.

## 3. scaffolder builds the shell

From the blog repo root at `blog/`:

```
python scripts/new_essay.py --slug <slug> --lens <culture|systems> --title "<h1>" --description "<meta description>" --tags "<tag one>,<tag two>" --excerpt "<15 to 25 words>"
```

The scaffolder renders the STYLE_BIBLE 2.1 skeleton, writes
`blog/blog/<slug>/index.html`, inserts the archive card as the first child of
`.essay-grid`, and recomputes all three `.filter-count` values by counting real
`data-theme` attributes. It never increments blindly. Do not hand-edit those counts.

It leaves the body as a scaffold with `TODO(naquuuu-curator)` markers. That is the
intended contract, not a bug. Use `--print-skeleton` if you need the exact shape.

## 4. builder fills the prose

Delegate to `naquuuu-builder`. Give it the slug and the curator's draft. It replaces
the scaffold markers with the drafted prose, leaving the head, header, meta row,
byline, and footer exactly as the scaffolder rendered them.

Hard rules for this step, because they are gate failures, not style preferences:

- zero U+2014, U+2013, `&mdash;`, `&ndash;`, `&#8212;`, `&#8211;` anywhere
- zero `style="` attributes containing the substring `width`
- everything lowercase, except the closed proper-noun allowlist in STYLE_BIBLE 1.1
- the byline string and both asset version query strings stay as the scaffolder wrote them
- the essay body contains no `img` elements

## 5. verifier gates

Delegate to `naquuuu-verifier`. It runs, from `blog/`:

```
python scripts/verify_blog_qa.py
python scripts/verify_sanitization.py --dir .
python scripts/new_essay.py --check blog/<slug>/index.html --lens <lens>
```

All three must exit 0. The third is the mechanical subset of the acceptance rubric,
checks 1, 2, 3, 7, and 8b.

If the check fails, send the failing lines back to the curator for one revision pass.
One pass only. If it fails again, stop and hand the owner the failing check name and
the line numbers. An essay that cannot pass in two passes is a topic problem, and
that is the owner's call, not yours.

## 6. report

Give the owner, in this order and nothing else:

- slug, lens, and where the page is
- the eight-check rubric result as eight lines
- both gate exit codes
- the one thing you would change if you were him

Then stop. Do not commit, do not push, do not run the hub autosync scripts.

## standing constraints

- No model calls in CI. This pipeline runs on the owner's machine, or remotely
  through the phone relay. Nothing here runs on a GitHub runner, and no API key is
  involved at any point.
- Never read or echo `.env`, the Hermes state directory, or any credential file.
- The published archive is `blog/blog/index.html` in workspace terms, which is
  `blog/index.html` from inside the blog repo. Both are correct; do not mix them up.
- The blog QA gate excludes `drafts/`, so a draft in that directory is never checked.
  Essays live in `blog/blog/<slug>/` precisely so the gates can see them.
