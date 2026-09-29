# style bible: naquuuu essays

Version 1.0. Authored by `naquuuu-curator` on 2026-09-28.

This file is the voice contract for every essay published on
`naquuuu.github.io`. It is the prompt contract for the drafting agents
(`naquuuu-curator` drafts the prose, `naquuuu-builder` assembles the files,
`naquuuu-verifier` runs the gates). It is law, not inspiration. Where this
file and an agent's instinct disagree, this file wins.

It sits beside `TASTE_PROFILE.md` rather than inside the blog repo on
purpose. `blog/scripts/verify_blog_qa.py` must never scan this file, because
this file quotes banned punctuation in order to ban it. Only the sanitization
linter applies here.

Source of truth: `internal-docs/TASTE_PROFILE.md`, `blog/blog/index.html`,
`blog/blog/smart-tailoring-as-kinetic-infrastructure/index.html`,
`blog/blog/the-geometry-of-shibuya-kei/index.html`,
`blog/drafts/gemini-final-audit.md`, `blog/scripts/verify_blog_qa.py`.

NOTE ON PUNCTUATION IN THIS DOCUMENT. This file describes a ban on the
em dash and the en dash. It never reproduces those two characters, not even
inside a quoted example, because the QA gate scans every file it can reach
and a specimen that models a violation is worse than no specimen. We name
them as U+2014 and U+2013 instead. Never type the characters themselves.

NOTE ON CASE IN THIS DOCUMENT. Prose in this file uses normal sentence case
so that a human can read it quickly. Every essay, every sample, every string
an agent emits is lowercase. Section 1.1 governs the output, not the spec.

---

## 1. voice contract

These are instructions to the writer. Obey all of them.

### 1.1 lowercase, absolutely

Write every visible string in lowercase. No exceptions except a closed
proper-noun allowlist, which is the only way this rule stays checkable.

Everything lowercased, always:
- the h1 title
- every h2 and h3
- every body paragraph
- every list item, including the bold lead-in label
- the byline
- the thesis box heading
- the html `<title>` and `<meta name="description">`
- archive card titles and excerpts
- alt text
- text inside inline svg diagrams
- link labels, file names, tag pills, badge labels

Closed proper-noun allowlist (these may keep their natural case):
`jakarta`, `tokyo`, `indonesia`, `indonesian`, `jawa`, `tebet`, `kebayoran`,
`figma`, `spotify`, `instagram`, `github`, `github pages`, `vercel`,
`python`, `javascript`, `typescript`, `sql`, `sqlite`, `api`, `apis`,
`json`, `html`, `css`, `android`, `chrome`, `linux`, `ubuntu`, `cron`,
`cornelius`, `pizzicato five`, `shibuya-kei`, `bossa nova`, `chrisye`,
`guruh gipsy`, `fariz rm`, `vira talisa`, `murphy`, `kafin sulthan`,
`blundstones`, `uat`, `brd`, `prd`, `utc`, `id`, `pm`, `p0`, `p1`.

Note: `shibuya-kei` and `kafin sulthan` are already lowercase on the site.
Do not "correct" them upward.

The list is closed. A proper noun that is not on it gets lowercased like
everything else. If a new one genuinely must be capitalised, add it here
first, in a commit, with a reason. Never decide this silently mid-draft.

### 1.2 thesis first, then numbered sections

The first thing a reader meets after the byline is the claim, in full.
Not a teaser, not a question, not "in this essay i will". The claim itself.

Then number the sections. Two to five h2 sections, always numbered with an
arabic numeral, a period, and a space. The numbering is typed by hand
because nothing in the stylesheet generates it.

Section numbering must be continuous from 1 with no gaps and no sub-letters
at h2 level. If you need sub-sections, use h3 with capital letters, like
"a. converting vectors into svg", and never more than three per essay.

### 1.3 short declarative sentences

Average one to two clauses per sentence. Most sentences under 18 words.
If a sentence needs a semicolon, it wants to be two sentences.

Prefer:
- the active voice, always ("the extractor reads the apk", not "the apk
  is read by the extractor")
- a concrete subject doing a concrete verb
- a period where you feel the urge to use a dash

Do not open three consecutive sentences with the same word. Do not open
a section with "additionally", "furthermore", "moreover", or "in addition".

### 1.4 concrete nouns over abstractions

Name the thing. If you can point at it, photograph it, or measure it, use
its name.

Bad: the system handles unexpected conditions gracefully.
Good: the retry path gives up after three attempts and tells you which id
failed.

Bad: this creates a more cohesive experience.
Good: everything in the palette is the same value of grey, so nothing fights.

Before you ship a paragraph, count its abstract nouns (ease, robustness,
scalability, flexibility, elegance, simplicity, power, capability). If a
paragraph has more than one, rewrite it with an object in it.

### 1.5 teach through one physical analogy per section

Each h2 section carries at least one image borrowed from a physical,
tactile, or musical domain: cloth, tailoring, painting, cooking, freight,
radio, weather, vinyl, a soldering iron, a receipt.

The analogy must do work. It must explain a mechanism, not decorate a
sentence. Bad analogy: "a system is like a kitchen". Good analogy: "read a
lease to find the real door", "paint wet, then walk away".

Draw the analogy from matter, not from software. A machine explaining
itself with another machine is the failure mode this site exists to avoid.

One analogy per section, not three. A section with three analogies has none.

### 1.6 bilingual as texture, never as translation

Indonesian may appear as a phrase, a name, or a piece of local colour.
It is never glossed. You do not explain what it means, and you do not
follow it with an english paraphrase.

Allowed: `yang bisa gagal 'kan gagal juga pada akhirnya`
Allowed: `reka peluang`
Allowed: `satu REQUIREMOTE, satu axis`
Banned: "which means", "in other words", "translated", "loosely",
"roughly speaking".

Rule of thumb: if the indonesian would stop a reader who does not speak it,
it is too central. Texture, not load-bearing structure.

Wrap any indonesian passage longer than about ten words in
`<span lang="id">...</span>`. Short phrases need no attribute.

### 1.7 no synthetic claims

Every number in an essay must be one of exactly three things:
1. a physical constant of the material world (32 degrees, 45 minutes)
2. a documented fact about a tool the owner actually uses
3. explicitly attributed to the owner in the first person
   ("the playlist i keep for long sessions runs about fifty minutes")

Never write a percentage, a latency figure, a frame rate, a user count, a
multiplier, or a growth number that nobody measured. Never write
"significantly faster", "dramatically reduced", "up to". If you cannot
source a number, delete the sentence containing it.

This is not a style preference. It is a correctness rule from `AGENTS.md`
section 5, and generated prose that invents a metric is worse than prose
that says nothing.

### 1.8 the first person is allowed and preferred over "one" or "we"

Write "i" when you mean yourself. Write "we" only when the reader is
genuinely included in the work.

The owner writes alone a lot. Do not manufacture a team. Do not invent
colleagues, managers, stakeholders, clients, or reviewers.

Second person "you" is permitted at roughly one per section. It is never
used for hype: never "you'll love this", never "you've got to try".

### 1.9 punctuation you may use

The bullet separator, the left arrow, the up-right arrow, the check mark,
the cross mark, the four-pointed star, the section sign.

- U+2022 bullet, used as the meta row separator
- U+2190 left arrow, used in "return to home"
- U+2197 up-right arrow, used on outbound links
- U+2713 check, only inside a comparison diagram
- U+2715 cross, only inside a comparison diagram
- U+2726 four-pointed star, decorative only
- U+00A7 section sign, legal and document references

Plus: the apostrophe, the colon, the period, the comma, the semicolon, the
question mark, the exclamation mark (rarely, at most once per essay), the
parenthesis, the slash, the ampersand (always written as `&amp;` in html).

Everything else is out. That includes the em dash (U+2014), the en dash
(U+2013), the minus sign, the figure dash, the horizontal bar, the
asterism, the interpunct used as a dash substitute, and the pipe.

---

## 2. structure template

Exact skeleton. Copy it. Do not improvise class names, and do not invent
classes that do not already exist in `blog/assets/css/style.css`.

`blog/scripts/new_essay.py` renders this skeleton. Run it rather than
hand-writing the shell; it guarantees the asset version query string, the
lens attribute, and the theme colour are correct.

### 2.1 the skeleton

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="color-scheme" content="dark">
  <meta name="theme-color" content="#1B1214">
  <title>essay title here: lowercase subtitle | naquuuu (krishna)</title>
  <meta name="description" content="lowercase one or two sentence summary, under 160 characters.">
  <link rel="canonical" href="https://naquuuu.github.io/blog/SLUG/">
  <link rel="stylesheet" href="../../assets/css/style.css?v=ASSET_VERSION">
  <link rel="icon" type="image/svg+xml" href="../../assets/favicon.svg?v=FAVICON_VERSION">
  <link rel="alternate icon" href="../../favicon.ico?v=FAVICON_VERSION">
</head>
<body data-mode="culture">

  <header class="site-header">
    <div class="wrap nav-container">
      <div class="nav-brand-group">
        <a class="nav-brand" href="../../">
          <span class="nav-telemetry-dot" aria-hidden="true"></span>naquuuu
        </a>
      </div>
      <nav class="nav-links">
        <a href="https://naquuuu.github.io/" class="nav-back-link">[ left-arrow naquuuu.github.io ]</a>
      </nav>
    </div>
  </header>

  <main class="wrap essay-article">

    <header class="essay-header">
      <div class="essay-meta-row">
        <time datetime="YYYY-MM-DD">month year</time>
        <span>bullet</span>
        <span>6 min read</span>
        <span>bullet</span>
        <span class="essay-tag-pill">style essay</span>
        <span class="essay-tag-pill">everyday design</span>
      </div>
      <h1 class="essay-header-title">essay title here: lowercase subtitle</h1>
      <p style="color: var(--text-muted); font-size: 0.95rem; font-style: italic; margin-top: 0.5rem; font-family: var(--font-sans);">
        by ramadhana bhanuharya krishnamurti (krishna / naquuuu) bullet notes on style
      </p>
    </header>

    <article class="essay-content">

      <div class="concept-box" style="border-left: 4px solid var(--accent-crimson);">
        <h3 style="font-size: 1.08rem; color: var(--text-primary); margin-bottom: 0.5rem;">the style thesis</h3>
        <p style="margin: 0; font-size: 0.92rem; color: var(--text-secondary); line-height: 1.7;">
          the whole claim, 35 to 60 words, stated plainly, no hedging.
        </p>
      </div>

      <h2>1. lowercase section heading</h2>
      <p>
        two to four sentences. one physical analogy. concrete nouns.
      </p>
      <ul>
        <li><strong>bold lead-in label:</strong> a clause of real detail after the colon.</li>
        <li><strong>bold lead-in label:</strong> a clause of real detail after the colon.</li>
      </ul>

      <h2>2. lowercase section heading</h2>
      <p>
        two to four sentences.
      </p>

      <div style="margin: 2.5rem 0; padding: 1.5rem; background: var(--bg-surface); border: 1px solid var(--border-active); border-radius: var(--radius-md);">
        <div style="font-family: var(--font-sans); font-size: 0.78rem; color: var(--accent-crimson); font-weight: 700; margin-bottom: 0.4rem;">
          [ outbound link label ]
        </div>
        <p style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6; margin-bottom: 1rem;">
          one sentence on what is behind the link.
        </p>
        <a href="https://example.com/" target="_blank" rel="noopener noreferrer" class="hero-cta-btn hero-cta-primary">
          <span>[ view the thing up-right-arrow ]</span>
        </a>
      </div>

      <div class="concept-box" style="margin: 1.5rem 0; border-color: var(--accent-crimson);">
        <p style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary); line-height: 1.6; margin-bottom: 0.5rem;">
          the takeaway, stated as a rule you could follow tomorrow.
        </p>
        <p style="color: var(--text-secondary); font-size: 0.94rem; line-height: 1.65; margin: 0;">
          one or two sentences closing the argument.
        </p>
      </div>

    </article>

  </main>

  <footer class="site-footer" style="margin-top: 4rem;">
    <div class="footer-wordmark" aria-hidden="true">naquuuu</div>
    <div class="wrap footer-content">
      <div class="footer-channels">
        <a href="https://naquuuu.github.io/">home</a>
        <a href="https://github.com/naquuuu" target="_blank" rel="noopener noreferrer">github</a>
        <a href="mailto:rbkrishnamurti@gmail.com">email</a>
      </div>
      <div class="footer-live-stamp">
        <span>naquuuu.github.io bullet built with matter and code.</span>
      </div>
    </div>
  </footer>

</body>
</html>
```

### 2.2 class name canon

Use these exact names. They are the ones that exist in `style.css`.

Layout and column:
- `.wrap` shared width wrapper
- `.essay-article` page column, 72ch
- `.essay-content` body column, 72ch, min-width 0
- `.essay-header` header block with bottom rule

Header:
- `.site-header` sticky site header
- `.nav-container` flex row inside the header
- `.nav-brand-group` brand cluster
- `.nav-brand` the word naquuuu
- `.nav-telemetry-dot` the small animated dot, aria-hidden
- `.nav-links` right side nav
- `.nav-back-link` the bracketed return link

Essay header:
- `.essay-meta-row` THE article meta row. flex, mono, 0.74rem
- `.essay-tag-pill` the two tag pills
- `.essay-header-title` the h1, 2rem

Do not use `.essay-meta` on an essay page. That class belongs to the
archive cards in `blog/blog/index.html`. The two systems essays use it
incorrectly; do not copy them.

Do not use `.dossier-badge` or `.hero-badge` on an essay page. Those are
homepage classes that the culture essays borrowed. `.essay-tag-pill` is the
correct, essay-scoped pill and it is already defined.

Body:
- `.concept-box` the thesis box and the closing box
- `.flowchart-whiteboard-box` the diagram frame
- `.flowchart-board-toolbar` the diagram top bar
- `.flowchart-toolbar-left` left half of the toolbar
- `.flowchart-toolbar-right` right half of the toolbar
- `.flowchart-board-canvas` the scrolling diagram stage
- `.scroll-x` overflow-x auto, the horizontal scroller

Footer:
- `.site-footer`
- `.footer-wordmark` the big hidden naquuuu
- `.footer-content`
- `.footer-channels`
- `.footer-live-stamp` the "built with matter and code" line

Links:
- `.hero-cta-btn` the bracketed call to action button
- `.hero-cta-primary` its primary variant

### 2.3 lens switch

The body tag carries the lens:
- culture essay: `<body data-mode="culture">`
- systems essay: `<body>` with no data-mode attribute. White is the default.
  There is no `data-mode="systems"` selector in the stylesheet.

theme-color meta follows the lens:
- culture: `#1B1214`
- systems: `#120305`

### 2.4 the byline

Fixed opening, never varies:
`by ramadhana bhanuharya krishnamurti (krishna / naquuuu)`

Then a bullet and one descriptor from this closed set:
- `notes on music` culture lens
- `notes on style` culture lens
- `notes on culture` culture lens
- `notes on systems` systems lens
- `notes on tools` systems lens
- `technical product owner` systems lens, optional

Nothing else. No job titles from an employer, no companies, no clients.

### 2.5 publishing side effects

A new essay is not finished when its page is written. Also:
1. add a card to `blog/blog/index.html`, newest first, inside `.essay-grid`,
   as `<article class="essay-card" data-theme="culture">` or
   `data-theme="systems"`, wrapping `<a href="./SLUG/" class="essay-card-link">`
   containing `.essay-meta` (with `.essay-theme-pill.theme-culture` or
   `.theme-systems`, plus the dot, plus `.meta-dot` separators),
   `h2.essay-title`, and `p.essay-excerpt`
2. update the three `.filter-count` numbers in `.essay-filter-bar`:
   all notes, systems, culture
3. the excerpt is 15 to 25 words, lowercase, no dashes
4. the archive card h1 stays "essays &amp; notes"

Steps 1 and 2 are performed by `blog/scripts/new_essay.py`. Do not hand-edit
the counts; they are the most common silent breakage on this site.

### 2.6 word and length budgets

| Element | Budget |
| :--- | :--- |
| html `<title>` | 8 to 13 words |
| meta description | under 160 characters |
| essay h1 | 8 to 13 words, colon before the subtitle |
| byline | fixed |
| thesis box heading | lowercase, at most 5 words |
| thesis box body | 35 to 60 words |
| h2 sections | 2 to 5, continuous numbering from 1 |
| culture body total | 350 to 600 words |
| systems body total | 900 to 1500 words |
| archive excerpt | 15 to 25 words |
| tag pills | exactly 2 |
| outbound link block | 0 or 1 per essay |
| inline svg diagrams | 0 to 1 per essay |

Read time is declared, never computed. Say 4 to 6 min for culture, 7 to
9 min for systems. The existing essays declare times that do not match
their real length; that is known drift, and a new essay should not copy the
error into a new number.

### 2.7 images

Zero raster images in an essay body. The site uses inline svg diagrams and
css. There is no `<img>` in any of the four published essays.

If a future essay genuinely needs one, it must carry a descriptive
lowercase alt attribute, and the alt must say what the thing is, not that
it is a picture.

### 2.8 inline svg diagrams: architectural blueprint on warm paper

Inline SVG diagrams must match the blog's warm paper aesthetic rather than
generic dark-mode SaaS or terminal screens.
- Framing: `.flowchart-whiteboard-box` with `var(--bg-surface)` background and subtle hairline border `var(--border-subtle)` / `var(--border-active)`.
- Cards: clean elevated paper (`#ffffff` / `#fffdf6`) with 1px hairline stroke and `rx="5"`.
- Muted analog washes: terracotta wash for audits, slate wash for API contracts, crimson mist for verification gates, sage wash for approved deliverables.
- Lowercase canon: all text nodes, badges, sublabels, and legend labels inside SVG must be strictly lowercase per Section 1.1.
- Involve `naquuuu-curator` or consult `TASTE_PROFILE.md` for visual vetting.

---

## 3. tone spectrum

The two lenses must survive a blind read test with the titles stripped.
A reader who cannot tell them apart means the essay failed.

### 3.1 systems & matter

Sounds like: an engineer who has been burned once, explaining calmly what
broke and what to do instead.

Opens with: a failure mode, a drift, a contradiction, or a cost. Never a
definition. Never "in this essay i will discuss".

Noun diet:
- systems nouns, dominant: state, token, schema, contract, boundary,
  timeout, retry, cache, drift, queue, buffer, failure, recovery, version,
  diff, run, edge
- material nouns, sparse: one or two, used as the analogy, never as the
  subject

Verb diet:
extract, compile, enforce, scope, verify, revert, measure, isolate,
instrument, cap, queue, log, diff, read

Shape:
- a numbered procedure appears at least once, as a real ordered list that a
  reader could follow tomorrow
- concrete examples, ideally with real object names: a file, a column, a
  status, a command, a garment, a machine
- hedges are unwelcome here. commit to a recommendation.

Closes with: a rule. A statement of the form "do x before y, because z".
The closing box must be actionable. If a reader could not act on it tomorrow
morning, it is not a systems closing.

Forbidden in this lens: feelings as the main subject, scenic writing,
anything that sounds like a mood piece.

### 3.2 culture & taste

Sounds like: someone who has worn the thing for two years, telling you why
it still works.

Opens with: a sensation, a scene, or a specific physical situation. A street
at four in the afternoon, a record going quiet, wet paint.

Noun diet:
- material and sensory nouns, dominant: cloth, weave, grain, lining, sole,
  brass, tempo, chord, hiss, humidity, fibre, weight, drape, edge, surface
- systems nouns, rare: one at most, and only to draw the analogy

Verb diet:
cut, press, wear, stack, drop, spin, fold, listen, hang, break in, wear out

Shape:
- lists of named things are welcome: fabrics, records, shoes, brushes. Name
  them. specificity is the whole charm.
- procedure is not required, and a numbered how-to list kills this lens.
- first person and direct address are both more available here.

Closes with: a choice. Something the reader might do differently, or a
preference stated as a preference. Not a rule. An invitation or a verdict.

Forbidden in this lens: architecture diagrams, roadmaps, tier numbering,
anything resembling a requirements document.

### 3.3 the blind read test

Apply to any draft, before accepting:
1. count the material nouns and the systems nouns. The dominant one names
   the lens. A 50/50 split means the essay is a hybrid and the ratio must be
   argued deliberately in the thesis.
2. is there a numbered procedure the reader could execute? yes means systems.
3. what does the closing box do? a rule means systems. a choice or a verdict
   means culture.
4. strip the title and the meta row. does the first sentence still tell you
   which world you are in? it must.

### 3.4 the hybrid

A hybrid is allowed, and it is the most interesting register, but it is
deliberate: name the join inside the thesis, in one clause. systems idea
first, material image second, or the reverse, but only one join per essay and
never twice in the same sentence.

---

## 4. lexicon

### 4.1 canon vocabulary

Use freely. These are house words and the site already owns them.

`matter + code`, `bits &amp; atoms`, `systems &amp; matter`,
`culture &amp; taste`, `build systems that anticipate failure`,
`taste that anticipates feeling`,
`mapping every possibility, from code to culture`, `expect failure`,
`map the edge cases early`, `reka peluang`, `keep slack`, `recovery`,
`ground truth`, `the running artifact`, `boring, on purpose`, `no ctrl+z`,
`the layer between the body and the city`, `wet layers`,
`ground you already own`.

Proper nouns and names in the allowlist in section 1.1 are also canon.

### 4.2 banned punctuation

Hard banned, zero tolerance, enforced by the QA gate:
- U+2014 em dash
- U+2013 en dash

Also banned by taste, and not caught by the gate, so ban them explicitly:
- U+2012 figure dash
- U+2212 minus sign used as a dash
- U+2500 box drawing horizontal
- the html entities `&mdash;` and `&ndash;`
- the numeric entities for the same two code points
- the interpunct used in place of a dash
- the pipe used as a dash in prose

The entities are the danger. The gate greps for the two characters and
entities slip past it. Ban them anyway, because a dash is a dash.

### 4.3 banned words: corporate filler

Each of these is a real word used as a nothing-word. Zero occurrences.

`leverage`, `synergy`, `synergies`, `robust`, `seamless`, `seamlessly`,
`scalable`, `cutting-edge`, `state-of-the-art`, `best-in-class`,
`world-class`, `holistic`, `end-to-end solution`, `value-add`, `value
proposition`, `actionable insights`, `actionable`, `align`, `alignment`,
`circle back`, `deep dive`, `deep dives`, `low-hanging fruit`, `move the
needle`, `north star` (unless literally celestial), `core competency`,
`digital transformation`, `journey`, `empower`, `empowerment`, `facilitate`,
`foster`, `ideate`, `ideating`, `incentivize`, `utilization`, `granular`,
`operationalize`, `socialize`, `next-level`, `deliverable`, `stakeholder`,
`stakeholders`.

Two notes on this list. "align" and "alignment" are banned in the
metaphorical sense, because they are the single most common way an engineer
hides a feeling they have not examined. If you mean two rectangles, say they
line up. "stakeholder" is banned outright: the owner has no stakeholders,
he has readers.

"enterprise" is not banned but is restricted. Allowed as a plain scale
descriptor ("in large apps", "a big codebase"). Banned as a marketing
modifier ("enterprise-grade", "the enterprise solution").

"ops" is banned as a clipping. Write "operations".

### 4.4 banned words: hype adjectives

`revolutionary`, `groundbreaking`, `game-changing`, `game changer`,
`mind-blowing`, `jaw-dropping`, `breathtaking`, `stunning`, `gorgeous`,
`stunningly`, `incredible`, `amazingly`, `awesome`, `epic`, `insane`,
`insanely`, `literally` (as intensifier), `next-level`, `must-have` (as
hype), `ultimate`, `perfectly`, `truly`, `simply put`, `undoubtedly`,
`fundamentally` (as filler).

"literally" is banned only as an intensifier. "the queue literally blocked
the deploy" is fine, though "actually" is better.

"curated" is allowed but capped at one occurrence per essay, and never as
"carefully curated". It is a real word in this owner's mouth because playlist
curation is a genuine practice, and the cap is what keeps it from turning into
marketing.

### 4.5 banned words: the ai-slop register

These are the tells.

Opener furniture:
`in today's fast-paced world`, `in today's world`, `in an era of`, `in the
modern landscape`, `in the ever-evolving`, `as we navigate`, `in an
increasingly`, `now more than ever`, `in the digital age`, `with the rise of`.

Verbs that mean nothing here:
`delve`, `showcase`, `underscore`, `foster`, `elevate` (as a verb), `embark`,
`unlock`, `unleash`, `harness`, `revolutionize`, `transform` (as a bare verb),
`capitalize on`, `leverage`.

Dead nouns:
`tapestry`, `testament`, `realm`, `landscape` (of), `beacon`, `cornerstone`,
`pillar`, `synergy`, `plethora`, `myriad`, `haven`, `oasis`, `treasure trove`.

The rule of three, as decoration: "fast, reliable, and scalable", "simple,
elegant, and powerful", "clear, concise, and compelling". Adjective triads are
banned. Noun lists in body prose are the house list style and are fine.

The antithesis tic: "it's not just x, it's y", "not only x but also y",
"isn't about x, it's about y" written with a comma. This is the single
loudest machine tell and it is banned outright.

Stale throat-clearing: `at its core`, `at the heart of`, `the bottom line`,
`needless to say`, `it is important to note that`, `it is worth noting that`,
`that being said`, `having said that`, `when it comes to`, `in order to` (write
"to"), `the fact that`, `at the end of the day`, `here's the thing`, `spoiler`,
`tl;dr`, `buckle up`, `picture this`, `imagine if`, `let that sink in`.

Fake humility and hedging: `i'm no expert, but`, `only time will tell`,
`who knows`, `take this with a grain of salt`, `that's a personal opinion`.

False binary openers: `whether you're a beginner or an expert`, `it's not about
x. it's about y.`

Comma splice as rhythm: the model is fast. really fast. deployed on friday.
you see the problem. The one-sentence-per-line cadence is a Medium habit, not
a house habit. Lowercase prose here does not mean chopped prose. Write
paragraphs.

### 4.6 banned content, separate from banned words

Zero occurrences, regardless of phrasing:
- the name of any employer, client, or vendor
- internal project codenames and internal skill names
- internal URLs, staging hosts, dashboards, or prototype links
- query-string access tokens of any kind
- any digit run of eight or more digits
- any phone number in any national format
- any email address other than the single canonical one already in the site
  footer
- percentage, latency, frame rate, or growth metrics that nobody measured
- the names of colleagues, managers, or clients, real or invented

The drafting agents must also refuse to invent them. Fabricating a company
name to make an example land is the same violation as leaking a real one.

---

## 5. hard constraints the QA gate enforces

These are checked by `blog/scripts/verify_blog_qa.py`, five gates, any
failure blocks the publish. Do not attempt to reason about whether a case is
"probably fine". The gate has no judgement and neither should you.

### 5.1 gate 1, inline width and copy hygiene

The gate greps every reachable html file for the pattern
`style="[^"]*width` and fails on any hit.

Consequence: never write the substring "width" inside a quoted style
attribute. This bans width, min-width, max-width, and any compound. It does
NOT ban the width attribute on svg or iframe elements; those are fine and
already used in the diagrams.

The reading column is handled by the stylesheet, which already sets
`.essay-article` and `.essay-content` to max-width 72ch, margin 0 auto,
min-width 0. Never set a width inline to achieve layout. Use the existing
utility classes or an unstyled div.

Then the gate strips comments, script blocks, and style blocks, and fails if
U+2014 or U+2013 appears anywhere in what remains. That scope is broader than
body copy. It includes the html title, meta descriptions, alt text, link
labels, and every text node inside an inline svg diagram. Check your diagram
labels too.

### 5.2 gate 2, anchor integrity

Every in-page link of the form `href="#something"` must resolve to an
`id="something"` in the same file, or the gate fails.

This check does not look at cross-page links. A link to
`../../index.html#some-section` is not verified. Be careful with it anyway,
because a broken cross-page anchor is still a broken link, and because the
scaffolder is the one adding those ids.

### 5.3 gate 3, responsive baseline and asset currency

Every html page must contain `name="viewport"`. The house value is
`content="width=device-width, initial-scale=1, viewport-fit=cover"`.

Every reference to `style.css` and to `main.js` must carry the current asset
version query string, which is `?v=20260917h` as of this writing. A stale
version is a hard failure.

The stylesheet itself must keep three things: `overflow-x: clip` on the body
as a horizontal spill safety net, a mobile media query at 768px, and a
`min-width: 0` guard on flex and grid children. Do not remove these while
tidying. The essay pages are expected to stay fluid down to 320px with no
horizontal scrollbar.

If you ever edit `style.css` itself, bump the version constant in
`verify_blog_qa.py` and every reference in the same commit, or the gate will
fail on the whole site. `new_essay.py` reads the constant from the gate rather
than hardcoding it, so it follows automatically.

Favicon references use `?v=20260917i` and are not version-checked. Keep them
consistent anyway.

### 5.4 gate 4, audio and media

Only relevant if you touch media. If you do: no autoplay attribute, no loop
attribute, `preload="metadata"` required, playback must be driven by a real
user gesture, and looping must be handled on the ended event in `main.js`
rather than with the loop attribute. Do not bind playback to mousemove or
scroll.

Essay pages do not carry audio. Leave it that way.

### 5.5 gate 5, typography and accessibility

The stylesheet must retain max-width 72ch, a 44px minimum touch target
height, and a 16px minimum input font size.

Every page must declare utf-8 charset, as `<meta charset="utf-8">`.

Every img element must carry an alt attribute. Since section 2.7 sets img
count to zero in essay bodies, this is a formality, but do not remove it if a
future essay needs one.

All outbound links use `target="_blank"` with `rel="noopener noreferrer"`.

### 5.6 not gated, but binding anyway

`blog/scripts/verify_sanitization.py` scans tracked html, js, css, md, py,
and txt files for corporate email domains, colleague names, corporate
workspace identifiers, api keys, google and digitalocean tokens, private
keys, and unmasked indonesian phone numbers. It exits non-zero on any hit and
it runs before every public push.

Two consequences. First, do not put a real example regex, a real token, or a
real phone number into a comment or a sample in a generated file; the linter
scans comments too. Second, the linter's identifier list is not exhaustive, so
passing it is necessary but not sufficient. Section 4.6 is the real rule.

---

## 6. calibration samples

These are the highest value content in this file. Copy the rhythm, not the
subject. An agent following the rules above will still drift; an agent
following these samples will not.

### 6.1 systems & matter sample

> most design drift is not a design problem. figma files go stale because
> nobody owns the compiled artifact. so stop treating the design tool as
> the source of truth and read the binary instead, the way you would read a
> lease to find the real door. the running app already holds the hex codes,
> the fonts, and the padding.

Note what it does: opens on a failure, not a definition. names real
artifacts. borrows one image from property law, and uses it to explain why
the design file is not the source of truth. ends on a concrete noun.

### 6.2 culture & taste sample

> shibuya-kei works because it refuses to choose. bossa nova chords, french
> pop, and vinyl hiss share one tempo, so nothing asks for your attention
> back. for long sessions that matters. lyrics become a second task. analog
> grain becomes a floor under your ears. put it on before you open the
> file, and let the record hold the room.

Note what it does: opens on a property of the music, not on a definition of
the genre. three short declaratives in the middle, each carrying one idea.
ends with an instruction, not a rule.

### 6.3 hybrid sample

> a playlist is a state machine with taste. it needs an idle state, a
> working state, and a state for when the room gets loud, plus a way back
> to the start when the mood breaks. curators have always built recovery
> paths by hand. a good one lets you stop mid track without losing the
> thread.

Note what it does: names the join in the first sentence, as required by
section 3.4. uses a systems noun and a culture noun in the same breath
exactly once. the noun triad is the house list style, which is why it is
allowed while adjective triads are not. ends on feeling, not on procedure.

### 6.4 what these samples deliberately do not do

- they do not open with "in this essay"
- they do not use a dash of any kind
- they do not use a capital letter
- they do not contain a number that nobody measured
- they do not explain an indonesian phrase
- they do not name a company
- they do not tell you how the reader will feel

---

## 7. acceptance rubric

Eight checks, applied to every draft before it is accepted for publishing.
**All eight must pass. No averaging, no partial credit, no "close enough on
the dash thing".**

Checks 1, 2, 3, 7 and 8b are mechanical and are re-implemented in
`blog/scripts/new_essay.py --check`, so the machine never disagrees with the
human checklist.

**1. dash check**
Count occurrences of U+2014, U+2013, `&mdash;`, `&ndash;`, U+2012, and the
numeric entities for U+2014 and U+2013, across the entire file including
head, alt text, and svg text nodes. Also grep for the interpunct in dash
position. PASS if the total is 0. FAIL otherwise, naming every line.

**2. inline width check**
Count matches of a quoted `style` attribute whose body contains the substring
`width`, in any form, including compound forms. PASS if 0. This is a direct
port of the gate's own regex, so a pass here cannot disagree with the gate.

**3. lowercase check**
Strip comments, script blocks, and style blocks. Tokenize the remainder into
alphabetic runs. Every run must be all lowercase, or must appear in the
proper-noun allowlist in section 1.1. PASS if 0 non-allowlisted uppercase
runs. Because the allowlist is a closed literal list, this check is fully
mechanical. FAIL lists the offending words and their line numbers.

**4. banned-term check**
Lowercase the copy, then count case-insensitive whole-word matches against
the combined term lists in sections 4.3, 4.4, and 4.5. Separately run four
pattern checks: the comma antithesis construction, the adjective triad
construction, the throat-clearing opener list as sentence-initial bigrams, and
the AI-slop opener list. PASS if 0 term hits. Any hit is a FAIL even if it
reads fine in context, because the list is the point.

**5. thesis-present check**
Assert exactly one `div.concept-box` appears as the first child of
`article.essay-content`. Assert its `h3` text is lowercase and at most 5
words. Assert its `p` text is 35 to 60 words. Assert exactly one additional
`div.concept-box` appears after the last `h2`, and that it contains a `p`
with no `h3`. PASS if all four assertions hold. The closing box is mandatory;
an essay that opens with a thesis and never lands the point is a FAIL here.

**6. skeleton check**
Assert the following exist, each exactly once, in this document order: `main`
with classes `wrap` and `essay-article`; `header.essay-header`; a
`div.essay-meta-row` containing exactly one `time` element with a valid
`datetime` attribute, exactly one read-time span matching the digits plus
"min read", and exactly two `span.essay-tag-pill`; one `h1.essay-header-title`;
one byline `p` whose text starts with the exact fixed string in section 2.4
and ends with a descriptor from the closed set in section 2.4; one
`article.essay-content`. Then assert two to five `h2` elements inside
`article.essay-content`, each matching a leading arabic numeral, a period, and
a space, numbered continuously from 1 with no gaps. Then assert `body` carries
`data-mode="culture"` or carries no `data-mode` attribute at all, and never
any other value. Finally assert `footer.site-footer` contains
`.footer-wordmark`, `.footer-channels`, and `.footer-live-stamp`, and that
`.footer-wordmark` is `aria-hidden="true"`. PASS only if all assertions hold.

**7. head and asset check**
Assert `<meta charset="utf-8">` present. Assert a viewport meta present whose
content contains `width=device-width`. Assert the canonical link is absolute,
begins `https://naquuuu.github.io/blog/`, and ends with a trailing slash
matching the folder. Assert the stylesheet href ends exactly in
`style.css?v=<CURRENT_ASSET_VERSION>`. Assert every `href="#..."` in the file
resolves to an `id` in the same file. Assert every `target="_blank"` carries
`rel="noopener noreferrer"`. Assert the theme-color value matches the lens.
Verify the asset version against the `CURRENT_ASSET_VERSION` constant in the
gate rather than hardcoding it at the call site.

**8. hygiene and budget check**
Six sub-assertions, all required:
- **a. content bans.** Zero matches against section 4.6: no employer, client
  or vendor name, no internal codename, no internal or staging URL, no
  access-token query string, no digit run of eight or more digits, no
  phone-shaped number, no email address other than the canonical one in the
  footer, and no colleague name real or invented.
- **b. claim discipline.** Zero matches for a percentage, a millisecond
  figure, a frame rate, a multiplier, or a user count. Every remaining numeral
  must be traceable to a physical constant, a tool specification, or a
  first-person attribution.
- **c. image count.** Zero `img` elements in `article.essay-content`. If a
  non-zero count ever appears, every one carries a lowercase descriptive alt.
- **d. length budgets.** Title 8 to 13 words. Excerpt 15 to 25 words. Culture
  body 350 to 600 words, or systems body 900 to 1500 words. Read-time span
  present and inside the declared band for the lens.
- **e. ampersand hygiene.** No bare `&` anywhere in html text or attributes.
  Every one is written `&amp;`.
- **f. drafting residue.** Zero occurrences of placeholder text, lorem ipsum,
  TODO, FIXME, TBD, bracketed instructions, doubled words, or a heading whose
  text is still the literal placeholder from the template in section 2.1.

PASS only if all six sub-assertions hold.

---

## 8. topic pool

Rotation index 1 to 12. **Odd numbers are systems & matter (white theme).
Even numbers are culture & taste (red theme).** The parity rule means the
rotation alternates lenses automatically, so the site never runs six white
weeks and then six red weeks. No corporate material anywhere in this list.
Nothing here requires employer knowledge.

1. **buffers, not optimism: slack in a pipeline behaves exactly like cash in a pocket** (systems)
2. **the coffee shop buffer: treating an idle hour as infrastructure, not procrastination** (culture)
3. **write the failure state first: designing timeouts, retries, and the boring path home** (systems)
4. **building a short set by ear: cutting forty minutes without a single transition** (culture)
5. **one query, one truth: reading a database schema the way you read a garment label** (systems)
6. **paint wet, then walk away: layering texture without a ctrl+z** (culture)
7. **tuesday deploys: making a weekly release boring enough to survive a bad friday** (systems)
8. **the two-minute morning: cutting a wardrobe down until getting dressed is boring** (culture)
9. **the api as a promise: writing contracts so a future teammate never has to guess** (systems)
10. **the record as reference track: keeping a ground truth you can actually hear** (culture)
11. **state machines you can wear: modeling a repair loop so a jacket actually comes back** (systems)
12. **lugged soles and hot asphalt: what a long walk teaches you about friction** (culture)

Deliberate design notes: 1 and 7 are both about pace but not the same idea,
one is about where capacity sits and one is about when you release. 2 and 11
are both about buffers but from opposite ends of the register, which is
exactly the hybrid test in section 3.4. 4 and 10 are both about music but one
is about editing and one is about reference, so they will not read alike. None
of the twelve overlap the four published essays.

---

## 9. owner decisions required

Two fields in `TASTE_PROFILE.md` are still marked as needing owner input.
Proposals below. Both are flagged as proposed, pending owner confirmation, and
both are safe to override by editing this file.

### 9.1 emoji set

**PROPOSED, PENDING OWNER CONFIRMATION: zero emoji, in all copy,
permanently.**

Rationale: the site uses typographic marks only, and it uses them well. The
seven marks in section 1.9 do the work that an emoji would otherwise do, and
they render identically everywhere, they survive a font swap, and they can be
recoloured by the theme.

If the owner wants a set anyway, the smallest set that would not damage the
brand is exactly these three, and no more: U+2726 decorative emphasis in the
culture lens only, U+2197 outbound link affordance, U+2022 meta row separator.

Override by replacing section 9.1 in full. Do not add emoji incrementally.

### 9.2 words to avoid

**PROPOSED, PENDING OWNER CONFIRMATION: the four lists in section 4.**

That is: banned punctuation (4.2), corporate filler (4.3), hype adjectives
(4.4), and the ai-slop register (4.5), plus the content bans in 4.6.

The list is intentionally long. A short list of "words to avoid" is a
suggestion; a long list of exact strings is a gate. The owner should override
by deleting entries, not by adding, because every added entry becomes
something the drafting agents must enforce forever.

One open question the owner should answer, because taste cannot decide it:
whether "curated" should stay allowed at a cap of one per essay, or be banned
outright. It is currently allowed, on the grounds that playlist curation is a
real practice in this owner's life and not a marketing word in his mouth.
