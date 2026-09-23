# Task Briefs (human-run AGY sessions)

Convention for briefs prepared by opencode/Hermes and pasted by the owner into the AGY IDE or the `agy` interactive TUI.

## Naming
`<YYYY-MM-DD>-<slug>.md`

## Format
- **Goal**: one sentence outcome
- **Context**: file paths only, no pastes
- **Done when**: 2-3 verifiable criteria
- **Constraints**: in-scope / out-of-scope
- **Return**: artifact paths plus evidence

## Single-writer lock
While a brief is active, create a `.lock` file next to it containing the brief name and a timestamp. opencode must not write to any path referenced by an active brief until the owner removes the lock or the brief is marked done in its own file. One writer per file path, always.

## Content rules
Tier 2 workspace content only. Never secrets, credentials, phone numbers, or personal identity data.
