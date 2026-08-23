# Linting documentation that is read by agents

**Task 32. All measurements dated 2026-08-23**, made on this machine against this repository
unless stated otherwise. Versions are named. Claims that were not measured are labelled
**UNVERIFIED** or **ASSERTION**.

## The question, and the answer

This repository's documentation is read almost entirely by models. 99 project markdown files
outside `eval/runs/`, ~1.20 M characters, ~300 k tokens. ~10,900 of those tokens are in the
always-on set (`AGENTS.md` 462 lines / ~7,300 tok, plus `research/`, `eval/` and `eval/judge/`
folder files). Nothing lints any of it. The operator asked what tooling exists for making prose
work better as agent context.

**The answer is that the tooling exists, is mature, is well maintained — and measures the wrong
thing.** Eight general-purpose linters were run against real files here. Together they produced
**over 14,000 alerts and two defects.** Both defects were found by tools that check *structure or
schema*, not prose. Every prose rule that fired was either a house-style preference, a false
positive on this project's own vocabulary, or a readability score.

The recommendation is therefore **not** to adopt a prose linter. It is to spend about an hour on
three deterministic structural checks that have already demonstrated hits, and to leave the prose
alone.

**And there is now a peer-reviewed literature saying the premise itself is shakier than assumed:**
the best-controlled studies find repository context files do not improve agent task success at
all. Section 4.

---

## 1. What was found in this repository

Two things. Both are real, both were found mechanically, and neither is a prose defect.

### 1.1 `AGENTS.md` rules 10–16 are structurally detached from their own rules

Rules 1–9 use one-digit list markers (`1. `), whose continuation indent is 3 spaces — correct.
Rules 10–16 use two-digit markers (`10. `), which under CommonMark require **4**. Every
continuation line in rules 10–16 is indented 3.

Lazy continuation keeps each rule's *first* paragraph attached. Any paragraph after a blank line
is not. Round-tripping `AGENTS.md` through `remark` emits **five paragraphs at top level, outside
the rule they belong to**:

| line | paragraph | belongs to |
|---|---|---|
| 397 | "A run is not a controlled experiment merely because it is one command." | rule 10 |
| 419 | "Its companion: an accepted-but-ignored flag is worse than an unsupported one." | rule 13 |
| 439 | "Worked example: the no-cap Tetris trial…" | rule 15 |
| 455 | "The check is free, it is offline, and it comes out either way…" | rule 16 |
| 459 | "Its companion, learned in the same hour: sweep the OPEN interval." | rule 16 |

A repo-wide scan found **one affected file and five paragraphs**. Only `AGENTS.md`, and only
because its own rule list crossed from one digit to two. `markdownlint` reports it as 22 confusing
`MD029/ol-prefix` alerts ("Expected 4; Actual 9") buried inside 9,697 total.

**What this establishes:** any CommonMark parser — `remark`, `markdownlint`, a retrieval chunker,
a renderer — detaches those paragraphs from their rules.
**What it does not establish:** that a model reading the raw bytes mis-associates them. That is
unmeasured, and nothing in the literature answers it either. The defect is that the document's
structure does not match its intent; whether the intent survives anyway is unknown.

### 1.2 Five of seven project skills have frontmatter no external tool can read

`claude plugin validate --strict` (Claude Code 2.1.220, Anthropic's own canonical schema check)
against a scratch plugin wrapper containing copies of `.claude/skills/*`:

> `frontmatter: YAML frontmatter failed to parse: YAML Parse error: Unexpected token. At runtime
> this skill loads with empty metadata (all frontmatter fields silently dropped).`

Failing: `add-game`, `audit-docs`, `evaluate-run`, `refine`, `run-matrix`. Clean: `prune`, `tasks`.
The `.agents/skills/` Codex duplicates failed identically, 5 of 6; that tree was **deleted on
2026-08-23** (task 27, #99), so `.claude/skills/` is now the whole population.

**Cause:** an unquoted YAML scalar containing `": "`. `description: Add a game task or a play-bot
criterion to the eval suite: prompt rules that…` is not valid YAML. `prune` and `tasks` pass only
because their descriptions happen to contain no colon.

**Positive control** — required, because a check that only ever fails is not a check: quoting the
values in the scratch copy makes **all seven validate clean**. The fix is one character at each
end of five strings.

Corroborated independently by two other parsers: PyYAML fails on the same five; `vale` 3.18.0
fails and, importantly, **aborts**.

**The qualifier, and it matters.** Claude Code's own project-skill loader tolerates it. Evidence:
this session's available-skills listing shows every description in full, colons included. So the
validator's runtime prediction does **not** hold for `.claude/skills/` on 2.1.220. What *is*
established is narrower and still worth fixing: **every tool outside Claude Code is locked out of
these files**, including Anthropic's own validator, and the tolerance is undocumented behaviour
that could change.

### 1.3 One near-miss worth recording

`agnix` reported, in 8 `.claude/settings.json` files across `template*/` and `eval/starters/*/`:

> `CC-HK-018: Matcher at hooks.Stop[0] is silently ignored for 'Stop' events`

Verified against https://code.claude.com/docs/en/hooks (fetched 2026-08-23): `Stop` is listed
under "no matcher support — always fires on every occurrence". The tool is **correct on the fact**.

It is also **inconsequential**: the matcher is `""`, and since `Stop` always fires, an ignored
empty matcher changes nothing. The `verify-gate.sh` hook runs.

This is worth recording precisely because it is the shape `AGENTS.md` rule 13's companion warns
about — an accepted-but-ignored field — and here the shape is present with no consequence. **A
tool being right is not the same as a finding mattering.** Do not fix it as if it were a bug; the
files are the product and editing them is a regime boundary.

---

## 2. Every tool, measured here

Run 2026-08-23 on this repository. Nothing was installed permanently: `npx --yes`, `uvx`, or a
release binary unpacked into a scratch directory. `vale`'s styles were synced into scratch.

| tool | version | how run | alerts here | true positives |
|---|---|---|---|---|
| `markdownlint-cli2` | 0.23.2 (lib 0.41.1) | `npx` | **9,697** repo-wide | 1 (§1.1, as MD029) |
| `vale` + Microsoft/Google/Readability | 3.18.0 | release binary | **4,234** on 6 core docs | 0 |
| `write-good` | 1.0.8 | `npx` | 137 on `AGENTS.md` | 0 |
| `alex` | 11.0.1 | `npx` | 35 on `AGENTS.md` | 0 |
| `proselint` | 0.16.0 | `uvx proselint check` | 18 on `AGENTS.md` | 0–1 |
| `typos` | latest via uvx | `uvx --from typos typos` | 161 repo-wide | 0 |
| `cspell` | 10.x | `npx` | 17 on `AGENTS.md` | 0 |
| `remark-lint` recommended | preset 7.0.1 | local install | **0** | 0 |
| `textlint` | 15.8.0 | `npx` | refuses to run | — |
| `agnix` | 0.49.0 | `npx` | 279 repo-wide | 2 (§1.2, §1.3) |
| `claude plugin validate --strict` | CC 2.1.220 | built in | 5 errors | **5 (§1.2)** |

Baseline confirmed before running anything: `which` found **none** of vale, markdownlint,
markdownlint-cli2, proselint, write-good, textlint, alex, remark, typos, cspell, harper-ls.
**Correction to the brief that commissioned this:** `ruff 0.16.4` *is* installed, as a `uv` tool
at `~/.local/share/uv/tools/ruff/bin/ruff`. No `pyproject.toml`, `ruff.toml` or `setup.cfg`
configures it for this repository, so it has never been run against this code.

### 2.1 `markdownlint-cli2` — 95.6% of its output is line width

Rule histogram across all `*.md` excluding `eval/runs/`:

```
MD013 line-length        7180     MD029 ol-prefix           22
MD060 table-column-style 2084     MD018 no-missing-space    19
MD040 fenced-code-lang     73     MD024 no-duplicate-head   12
MD022 blanks-around-head   66     MD041 first-line-heading  10
MD004 ul-style             57     ...and 14 more, <10 each
```

`MD013` + `MD060` are 9,264 of 9,697 — line width against an 80-column default the repo does not
use, and table cell padding. Config noise.

Of what remains, adjudicated by reading:

- **`MD018` — 19 of 19 false.** Every one is a finding citation (`#59 measured…`) at line start.
  Not headings in CommonMark; the rule guesses at a *probable* missing space. It fires on the
  project's own citation convention.
- **`MD041` — 8 of 10 false.** Those 8 are the `CLAUDE.md` → `@AGENTS.md` one-line import files.
  That import is the pattern Anthropic documents.
- **`MD024` — 12, by design.** "Hypothesis"/"Falsification" per iteration in `IMPROVEMENTS.md`,
  "The general form" per finding. Nested under distinct parents; unambiguous in context.
- **`MD036` — 2 false.** Quoted task prompts in `eval/BAKEOFF.md`.
- **Real but trivial:** `README.md:15` a second H1, `README.md:81` and `three-api.md:19` skip h2.
- **Real and not trivial:** `MD029`, which is §1.1.

### 2.2 `vale` cannot run over this repository at all

```
$ vale --config=vale.ini <repo-root>
.agents/skills/audit-docs/SKILL.md:1:E201:yaml: line 2: mapping values are not allowed in this context
```

**One line of output, 0.09 s, nothing linted.** It aborts on the first unparseable SKILL.md
frontmatter (§1.2) rather than skipping the file. Anyone adopting Vale here fixes §1.2 first,
whether they meant to or not.

Run per-file on six core docs (`AGENTS.md`, `README.md`, `DECISIONS.md`, `eval/PROTOCOL.md`,
`eval/judge/RUBRIC.md`, `eval/judge/JUDGING.md`) with the Microsoft, Google and Readability
packages: **4,234 alerts**, ~0.9 s for 3 files. Cost: 41 MB binary, 376 KB styles.

```
Contractions 950   Passive 832   Dashes/EmDash 702   Parens 267
SentenceLength 189  Spelling 156  Semicolons 302  Vocab 124  Acronyms 190
```

The 950 `Contractions` alerts want "it's" for "it is", "can't" for "cannot", "don't" for "do not".
`Microsoft.Vocab` fires **50 times with "Prefer 'personal digital assistant' over 'agent'"**. The
`Readability` package emits six whole-document scores per file — `AGENTS.md` scores
Flesch–Kincaid 8.62, Gunning-Fog 10.62, SMOG 11.30, LIX 37.84, and is told to get all of them
lower.

Three rule classes came closest to relevance and all three were adjudicated false here:

- **`Google.Timeless`, 9 hits on "currently".** Read every one. All nine correctly qualify a
  stated snapshot of an instrument ("`bot_mutants.py` currently reports 36 criteria"). The rule's
  *idea* — a claim about "now" needs a date — is a real project rule from `research/AGENTS.md`,
  but this implementation cannot tell a dated snapshot from an undated one.
- **`Google.ExcessiveClaims`, 14 hits on "best"/"fastest".** All are the project quoting its own
  null result: *"there is no best stack"*.
- **`Google.Anthropomorphism`, 18 hits on "sees"/"tells".** The subject of most of them is a
  judge model, which does see things.

**The value in Vale is not its style packages.** It is the custom-rule engine (`existence`,
`substitution`, `conditional`, `capitalization` in YAML). A five-line rule encoding this project's
own "cite `IMPROVEMENTS.md` by path" convention was written and does fire — but so does `grep`,
and the repo already has the right home for such a rule (§5).

### 2.3 `write-good`, `alex`, `proselint` — 190 alerts, no defects

**`write-good`, 137 on `AGENTS.md`.** Passive voice, "it is", weasel words. Markdown-blind: it
flagged the skill name `` `evaluate-run` `` inside a table cell as *"'evaluate' is wordy or
unneeded"*. **Dormant upstream** — npm 1.0.8 published 2021-02-16, last code change over five
years ago. Gotcha for CI: it **exits with the issue count**, not 0/1.

**`alex`, 35 on `AGENTS.md`, all false.** It flags `failure`, `failures`, `failed`, `fire`,
`firing`, `fires`, `dead`, `died`, `dies`, `buried`, `harder` as *"profane in some cases"*, and
`obvious`, `just`, `easy` as *"may be insensitive"*. Those words are this project's core
vocabulary — a rule that *fires*, a check that *failed*, a document that is *dead weight*. On a
corpus about failure analysis, alex has a 100% false-positive rate. **Dormant** — no code commit
in ~2 years, npm 11.0.1 from 2023-08-18.

**`proselint`, 18 on `AGENTS.md`.** Sixteen are `typography.symbols.curly_quotes`, recommending
`""` be replaced with `""`. **Following that advice would make the docs worse**: curly quotes
break exact-match `grep` on quoted strings, which is how this repo's grep-first `tasks/` layout is
navigated. One `redundancy` hit ("these ones") is a fair, trivial catch. **Maintained but slow** —
and it *moved*: the primary repo is now https://codeberg.org/amperser/proselint; GitHub is a
mirror. v0.16.0 released 2025-11-14 introduced **subcommands**, so `proselint FILE` no longer
works; it is `proselint check FILE`.

### 2.4 Spelling — `typos` and `cspell` both zero here

`typos` produced **161 alerts, none real.** `PN` → `ON` comes from tokenising "PNGs"; `mis` →
`miss` from "mis-posed"; `empted` → `emptied` from "pre-empted"; `LOD` → `LOAD` from Unity's
`QualitySettings.asset`. `cspell` produced 17 on `AGENTS.md`, all British spellings
(`generalises`, `authorised`, `defence`, `behaviour`), tool names (`runstat`, `pgrep`, `execve`)
and `Tetris`. Both are actively maintained and genuinely useful tools; this corpus simply has no
typos in it and a dialect their defaults do not carry.

### 2.5 `remark-lint` — a clean score on everything

`remark-preset-lint-recommended` on `AGENTS.md`, `README.md`, `eval/PROTOCOL.md`: **zero issues**.
Verified unpiped — `no issues found`, exit 0.

This is the exact shape the project distrusts. The same file that remark reports clean is the file
whose list structure remark's *own parser* silently rewrites (§1.1). The preset simply has no rule
for it.

`remark` also **cannot be run one-shot**: `npx --package remark-cli --package
remark-preset-lint-recommended` fails with `Cannot find package`, because unified-engine resolves
plugins relative to cwd. It needs `npm i -D` + `.remarkrc` (20 MB `node_modules`). With no config
it is not a linter at all — it prints the reformatted document and says `no issues found`.

### 2.6 `textlint` — zero default behaviour

```
$ npx --yes textlint AGENTS.md
Possible reasons:
* Your textlint config file has no rules.
```

Ships no enabled rules. Its English rule ecosystem is thin wrappers around write-good and alex,
both dormant: `textlint-rule-write-good` last released 2021-06-06,
`textlint-rule-alex` 2024-02-04. Actively maintained framework (v15.8.0, 2026-08-01), strongest
for Japanese. Nothing to adopt here.

### 2.7 `agnix` — the only agent-file linter with traction, and 277 of 279 alerts are noise

https://github.com/agent-sh/agnix, 391 stars, last push 2026-08-22, Rust, LSP + CLI, **448 rules**,
`npx agnix .`. This is the only serious AGENTS.md/CLAUDE.md linter in existence; the other nine
that GitHub search surfaces have 0–2 stars.

279 findings here. Adjudicated:

| rule | n | verdict |
|---|---|---|
| `AS-016` failed to parse SKILL.md | 10 | **TRUE** — §1.2, independent corroboration |
| `CC-HK-018` Stop matcher ignored | 8 | **TRUE on the fact, no consequence** — §1.3 |
| `CDX-AG-005` "references missing file" | ~60 | **FALSE.** Treats every backtick span as a path: `` `Sim.step()` ``, `` `Vector2.clamped(n)` ``, `` `[Writes(...)]` `` |
| `XP-003` hard-coded `.claude/` path | 38 | **FALSE.** `AGENTS.md` deliberately mandates `.claude/skills/<name>/SKILL.md` |
| `AGM-006` nested AGENTS.md detected | 11 | **FALSE.** Folder-scoped `AGENTS.md` is this repo's design |
| `AGM-004` missing project context section | 11 | prescription, unsourced |
| `XP-SK-001`/`CX-SK-001` non-universal fields | 20 | **WAS TRUE for `.agents/` only**, and helped settle task 27 — see below |
| `PE-004` ambiguous term 'often'/'usually' | 11 | prescription, unsourced |
| `PE-001` critical keyword position | 4 | see below |

Two are worth pulling out.

**`XP-SK-001`/`CX-SK-001`**: `when_to_use` and `argument-hint` are Claude Code fields, not part of
the universal Agent Skills spec, and *"not supported by Codex CLI — it will be ignored"*. For
`.claude/skills/` that is a false positive. For the `.agents/skills/` Codex copies it was a real
finding, and it fed **task 27**: those copies existed to serve Codex, and Codex discards the two
fields that decide when a skill is invoked — so the mirror could not have worked as intended even
had a Codex sibling been reading it. **Settled 2026-08-23: `.agents/skills/` is deleted** (#99),
`.claude/skills/<name>/SKILL.md` is the sole authoritative path, and `docstat.py --sweep` fails on
any `SKILL.md` outside it.

**`PE-001` — "Critical keyword 'never' at 47 percent of document (40-60 percent is the…)".** This
is agnix operationalising the lost-in-the-middle result (arXiv:2307.03172) as a lint rule. It is
also the clearest instance in this whole survey of the failure mode the project exists to
distrust: a real published effect, converted into a precise-looking percentage band, with **no
citation on the rule and no measurement that a keyword landing at 47% is followed less often**.
agnix's rule documentation carries no evidence for any individual rule. Reading its output, the
band looks measured. It is not.

---

## 3. Tool landscape and maintenance status

Read from the GitHub / npm / PyPI / crates.io / Homebrew APIs on **2026-08-23**.

| tool | latest | last commit | verdict | catches |
|---|---|---|---|---|
| **vale** | v3.18.0, 2026-08-20 | 2026-08-21 | **very active** — 8 releases since 2026-05-15 | prose style vs a declared guide; markup-aware |
| **markdownlint / -cli2** | 0.41.1 / 0.23.2, 2026-07 | 2026-07-28 | **active**; cli2 has 2 open issues on 903★ | markdown structure only; **53 rules**, IDs to MD060 |
| **rumdl** | 0.2.60, 2026-08-22 | 2026-08-22 | **very active**, 1,444★ | markdownlint-compatible, Rust, 16 ms |
| **mado** | 0.3.1, 2026-07-22 | 2026-08-17 | active, 380★ | markdown structure, Rust |
| **harper** (Automattic) | v2.8.0, 2026-08-13 | 2026-08-22 | **very active**, 14,684★ | real **grammar** + spelling, offline, 818 rules on |
| **cspell** | 10.1.0, 2026-08-22 | 2026-08-22 | **very active**, 6.3 M dl/mo | dictionary spelling |
| **typos** | 1.49.0, 2026-08-03 | 2026-08-20 | active | typo corpus, identifier-aware |
| **codespell** | 2.4.3, 2026-07-15 | 2026-08-18 | active | typo corpus |
| **textlint** | 15.8.0, 2026-08-01 | 2026-08-20 | active framework | nothing by default |
| **proselint** | 0.16.0, 2025-11-14 | 2026-06-22 | **alive, slow** — and moved to Codeberg | English usage/typography |
| **remark-lint** | preset 7.0.1, 2025-01 | 2026-01-05 | maintained, low velocity; **`remark-cli` untouched on npm since 2024-04-30** | markdown structure as mdast plugins |
| **write-good** | 1.0.8, **2021-02-16** | 2025-03-10 (README only) | **dormant** | 8 regex heuristics |
| **alex** | 11.0.1, **2023-08-18** | 2024-11-27 (README only) | **dormant** | inclusive language |
| **agnix** | 0.49.0 | 2026-08-22 | active, 391★ | AGENTS.md / CLAUDE.md / skills / hooks |
| **ltex-ls** | 16.0.0, 2023-03-19 | — | **ARCHIVED** — use `ltex-plus/ltex-ls-plus` (18.7.0, 2026-06-13), but its bundles are **~315 MB** |
| **RedPen** | 1.10.4, 2020-01-05 | 2021-03-14 | **dead** |

Two things worth knowing that are not in any tutorial:

**The Vale org was renamed.** `errata-ai/vale` → `vale-cli/vale`, and the freed `errata-ai` org
name is now held by a different, empty account created 2026-03-17. Vale's package registry
`library.json` still resolves Google/Microsoft/proselint/write-good/alex through
`github.com/errata-ai/<Style>/releases/...`, which works only while GitHub's rename redirect
holds. Pin package versions.

**Vale's own style packages are mostly frozen** even though Vale is not: `write-good` v0.4.1 and
`proselint` v0.3.4 both released 2024-06-09 (and the proselint port has since diverged from
upstream 0.16.0), `alex` v0.2.3 2024-11-02, `Joblint` v0.4.1 2021-04-07, and **`Readability`
v0.1.1 with no commit since 2022-03-17**. The readability scores this survey argues against are
served by the most dormant package in the registry.

**New, 2026-08-05, and relevant:** `vale-cli/agent-tools` — Vale packaged as Claude Code skills
plus an edit-time linting hook that surfaces only error-level alerts. Last commit 2026-08-05, no
release, 0 stars. The MCP server component requires a **paid Vale CMS subscription**. Noted
because it is the only first-party attempt to wire a real linter into an agent loop; too new to
recommend.

---

## 4. Is there an established practice for writing docs as agent context?

**No.** And the negative is now evidenced rather than merely unexamined, which is a stronger
result than it was a year ago.

### 4.1 `AGENTS.md` is a convention with an empty spec

[agents.md](https://agents.md/), stewarded by the Agentic AI Foundation under the Linux
Foundation; repo `agentsmd/agents.md`, 23,801★, created 2025-08-19, last push 2026-03-12. Its FAQ:
*"AGENTS.md is just standard Markdown. Use any headings you like; the agent simply parses the text
you provide."* **No mandatory fields, no schema, no conformance suite.** There is nothing to
validate against, which is why every "AGENTS.md linter" is really somebody's style guide.

Independent adoption denominator (the "60k repos" figure on the site is a code-search count, not
an audit): **arXiv:2605.08435** (2026-05-08) sampled 40,585 actively-maintained repos, classified
36,710 as engineered software, and found **4,738 (12.9%)** contained any agent configuration
artifact.

### 4.2 The best-controlled studies find context files do not help correctness

This is the part that bears on the premise of the whole exercise.

- **arXiv:2602.11988** (2026-02-12, rev 2026-06-23; Gloaguen, Mündler, Müller, Raychev, Vechev —
  ETH). *"Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?"*
  SWE-bench tasks with generated context files, plus a new collection of issues from repos with
  developer-committed files. Abstract, verbatim (fetched 2026-08-23): *"we find that providing
  context files does not generally improve task success rates, while increasing inference cost by
  over 20% on average… while instructions in the context files are well followed by coding agents,
  repository overviews, although popular and recommended by model providers, are not helpful."*
- **arXiv:2607.27250** (2026-07-28). Claude Code + Codex, 17 tasks, 3 repos, **288 evaluated
  runs**, gold-test evaluation, effect bounded to **≤10–15 pp by equivalence testing**. A
  manipulation probe found the real AGENTS.md never converted a near-miss into a pass on either
  agent. Failure triage: agents fail on implementation skill, not missing repository knowledge.
- **arXiv:2601.20404** (2026-01-28). 10 repos, 124 PRs, with/without: **median runtime −28.64%,
  output tokens −16.58%**, comparable completion. Positive — on *efficiency*, not correctness.
- **arXiv:2606.20512** (2026-06-18). SWE-bench Verified, 4 trials: 33.0% vs 28.3% vs 25.5%
  unguided (p<0.001). Mechanism is **coverage, not precision** — +14.5 pp more evaluable patches,
  per-patch precision statistically constant (~59%, p=0.119). Guidance helps the agent reach the
  right file.

**Reconciliation:** context files reliably transmit *instructions* and *novel facts*; they do not
reliably transmit *competence*. The repository-overview section — the most-recommended content
type in every guide — is the one with a measured null.

**What this repo should take from it, and what it should not.** This repository's `AGENTS.md` is
almost entirely instructions and hard-won constraints, which is the category the ETH paper says is
followed. It contains very little repository overview. So the null does not obviously apply here.
**Do not conclude that this project's documentation is useless**; do conclude that nobody has
shown it helps, and that this project — which owns a working agent-evaluation harness — is one of
the few places that could actually measure it.

### 4.3 The nearest thing to a validated checklist, and its limits

**arXiv:2606.15828** (2026-06-14, rev 2026-07-30), *"Configuration Smells in AGENTS.md Files"*,
**SCAM 2026, peer-reviewed**. Six smells with heuristics, measured on 100 popular repos: Lint
Leakage 62%, **Context Bloat (≥200 lines) 42%**, Skill Leakage 35%, **Conflicting Instructions
28%**, Init Fossilization 24%, Blind References 16%.

**It measured prevalence only.** No smell has been shown to degrade agent behaviour, and four of
the six heuristics require an LLM judge. It is a catalogue of things that look wrong, not of
things shown to be wrong — and it is exactly the shape of artefact that gets cited as if it were a
quality standard.

**arXiv:2606.09090** (2026-06-08) is the one genuinely reusable mechanical check: an existing
README/wiki consistency checker run on 356 repos found **stale code-element references in 23.0%**.
*Do the identifiers named in your instruction file still exist in the code?* This project already
has that check — `eval/tools/docstat.py --sweep`, which caught five nonexistent judges named in
`RUBRIC.md` (#38). It reports **`sweep clean: 95 docs checked`** today.

### 4.4 What is measured about document properties and agent behaviour

- **Length:** arXiv:2307.03172 (*Lost in the Middle*, U-shaped by position); arXiv:2402.14848
  (degradation with length holding the task constant); arXiv:2502.05167 (*NoLiMa*).
- **Order:** arXiv:2402.08939 — reordering *logically equivalent* premises alone changes reasoning
  accuracy. The most direct evidence that within-document ordering is a real variable.
- **Instruction count — the most actionable result.** arXiv:2509.21051 (*When Instructions
  Multiply*, 2025-09-25): ManyIFEval and StyleMBPP across 10 LLMs; compliance degrades
  consistently as instruction count rises, and **a logistic regression on instruction count alone
  predicts compliance to ~10% error**. arXiv:2510.14842 identifies the mechanism as **conflict
  between instructions** and contributes a conflict-scoring tool.
- **Chroma "Context Rot"** (2025-07-14, 18 models, public code at `chroma-core/context-rot`):
  consistent degradation with input length even on trivial tasks; distractors compound
  non-uniformly; and — the finding that should temper any confidence here — **shuffled haystacks
  outperformed logically structured ones.** Whatever "well-structured for an agent" means, it is
  not obviously "coherently organised for a reader".

### 4.5 `llms.txt` is not relevant to this repository, and it does not work

[llmstxt.org](https://llmstxt.org/), Jeremy Howard, 2024-09-03. No validator exists (`llms-txt
in:name validate` on GitHub returns 0 repos); the reference implementation is a parser.

Measured: **Ahrefs, 2026-06-15**, server logs across **137,210 domains**, May 2026 — 28% published
a valid `llms.txt`, **97% of those files received zero requests**, and **no AI bot probed for a
missing one**. Search Engine Land, 2026-01-20, 10 sites, 90-day before/after: 8 no change, 1 down
19.7%, 2 up and attributed to other causes. Google's John Mueller: *"None of the AI services have
said they're using llms.txt."* arXiv full-text search for `"llms.txt"` returns two papers, neither
an evaluation.

**But scope it correctly.** `llms.txt` is about web publishing to crawlers. Its failure is a
crawler-adoption failure, not evidence about whether a well-structured document is good context
once a model reads it. Do not transfer the null to `AGENTS.md`.

### 4.6 The specific question the operator asked, answered plainly

**No published study relates human-readability metrics — Flesch–Kincaid, passive voice, weasel
words, reading grade — to LLM instruction-following or retrieval accuracy, in either direction.**
Searched; nothing on point. The correlation this project doubted has, as far as can be
established, never been tested.

That is not "readability doesn't matter". It is: **nobody knows, the tools that measure it were
validated on human comprehension, and any adoption on that basis is a guess wearing a number.**
This is the proxy-metric failure of #59 with prose in place of `ux`.

---

## 5. Claude Code skills and plugins

Read on 2026-08-23. Machine state: Claude Code 2.1.220, `~/.claude/skills/` empty, and of 7
entries in `enabledPlugins` **only `rust-analyzer-lsp` actually loads** — four fail because the
`claude-code-plugins` marketplace name is now reserved by Anthropic for `anthropics`-org sources,
two cache-miss on a relative path. Nothing documentation-related is installed.

`anthropics/claude-plugins-official` (33,834★) carries 286 plugins. Filtered for
doc/writing/prose/lint/context/token/memory: **two are on-topic, neither is tooling.**

**`claude-md-management`, Anthropic-authored.** 745 lines across 5 files. The only executable
content in the entire plugin is one `find . -name "CLAUDE.md"`. Everything else is a prompt — and
what it prompts the model to emit is `**Score: XX/100 (Grade: X)**` with a five-row weighted table
and an "average score" across files, with **no mechanism behind any digit**. By this project's
first sentence — *a number that is wrong is worse than no number, because it gets acted on* — this
ships the number-shaped output without the measurement. **Do not install.** Its six underlying
criteria are a reasonable checklist; take those and drop the scoring.

**`avoid-ai-writing`** (in `wshobson/agents`, 39,031★) is the most substantial doc-quality skill in
the ecosystem: 44 KB of pattern catalogue, word tiers and genre profiles. **No `scripts/`
directory, zero tool invocations — entirely prompt.** To its credit it is the most epistemically
honest artefact in this survey: it warns that AI-text detection has **false-positive rates of
roughly 30–78%** and forbids using it for academic-integrity or hiring calls.

**`documentation-standards`/HADS** states verbatim in its own SKILL.md: `Validator: (planned — not
yet included in this release)`. **`elements-of-style`** (541★) is Strunk 1918 as markdown, honestly
labelled. Every context-compression skill found (`ozempskills` 1★ claiming "40%+",
`context-compressor-skill` 0★ claiming "60–95% fewer tokens") has a percentage with no methodology
and no users.

**The clearest single result of the plugin survey:** a GitHub code search for `vale` in
`**/SKILL.md` returns **`total_count: 0`**. Nobody has wrapped Vale, proselint, write-good,
textlint or markdownlint as a Claude Code skill. Every prose-quality skill in the ecosystem is a
prompt. The deterministic tools all exist and are mature; they have simply not been packaged,
because a skill that shells out to `vale --output=JSON` looks less impressive than a 44 KB rubric.

**Is there an official way to lint a skill or a CLAUDE.md?** For skills, yes, three, all
deterministic: `claude plugin validate <path> [--strict]` (the canonical schema + frontmatter
check — this is what found §1.2); `skills-ref validate` (whose own README says
demonstration-only); and `anthropics/skills`' `skill-creator/scripts/quick_validate.py`, 15
regex/YAML/length checks, no LLM calls. For CLAUDE.md there is **no schema and no validator**, but
`/doctor` (v2.1.206+, so available here) proposes trims — model-generated, a proposal not a
measurement.

Also deterministic and worth knowing: **`claude plugin details`** prints a component inventory and
projected always-on token cost, and the **`InstructionsLoaded` hook** logs which instruction files
loaded, when, and why. The latter is this project's own "capture what the instrument DID" rule
applied to context loading, and it addresses #60's *wrong address* failure directly.

---

## 6. Recommendation

**Adopt no prose linter.** 14,000+ alerts, zero prose defects, and two of the three tools whose
rules came closest to relevance (`write-good`, `alex`) are dormant while the third
(Vale `Readability`) has not been committed to since 2022.

Four things are worth doing. The first two are demonstrated; the third is judgement; the fourth is
an experiment.

**1. Fix the two defects. (~20 minutes, demonstrated.)**
Quote the five SKILL.md `description`/`when_to_use` values (§1.2) and re-indent `AGENTS.md`
rules 10–16 to 4 spaces (§1.1). Both have a positive control: `claude plugin validate --strict`
goes from 5 errors to 0, and the detached-paragraph scan goes from 5 to 0. Filed as **tasks 35 and
36**. Do not bundle them with anything else.

**2. Add two deterministic gates to `eval/tools/docstat.py`, where the mechanical doc checks
already live. (~1 hour, both demonstrated to fire. Task 37.)**
- `claude plugin validate --strict` over `.claude/skills/`, or the same YAML-parse check in ten
  lines of Python. It found a real defect that seven prose linters missed. (`.agents/skills/` was
  in scope when this was written and was deleted on 2026-08-23, #99 — `.claude/skills/` is now the
  whole population. **Enumerate the files with `os.walk`, not `glob`:** `glob` does not descend
  into dot-directories, so a `**/SKILL.md` pattern matches none of them and the gate passes by
  finding nothing. `docstat.py` has an `_all_skill_files()` that walks.)
- The list-continuation-indent check. Twenty lines; it found §1.1 and nothing else, which is the
  right false-positive rate.

Put them in `docstat.py` rather than adding a linter, because `docstat.py` already exists, already
gates on exit 1, and already carries the conservatism this repo needs — see below.

**3. Consider `markdownlint-cli2` with almost everything off, or skip it.** With `MD013` and
`MD060` disabled it drops from 9,697 alerts to ~430, of which the great majority are still false
against this repo's conventions (`MD018` on `#59` citations, `MD041` on the `@AGENTS.md` imports,
`MD024` on per-iteration headings). The honest configuration is `MD029` plus `MD001`, and at that
point it is two rules and a config file to maintain for what §5's twenty-line check already does.
**Weak recommendation: don't.**

**4. The experiment nobody has run.** §4.6 established that the relationship between document
properties and agent instruction-following is untested. This project has a working
agent-evaluation harness, blinded judging, and stored trials. **arXiv:2509.21051's result —
compliance predicted by instruction count alone to ~10% error — is directly testable here**, and
`AGENTS.md` is a 462-line file with 16 numbered rules whose author has already observed that
some of them fail to fire. Filed as **task 39**, priority 5, because it needs a design before it
needs a run.

### What was deliberately not recommended

- **No readability gate.** Trivially gameable, validated on human comprehension, and with nothing
  connecting it to agent behaviour. `AGENTS.md` scores Gunning-Fog 10.62; there is no evidence
  that lowering it changes anything, and the package computing it is dormant since 2022.
- **No path-resolution check, and this one is instructive.** `docstat.py:195-199` records that
  this repo already tried it: *"NO PATH CHECK… Measured: 0 true positives, 2 false."* Independent
  re-measurement today, against the main checkout: **265 distinct backtick-quoted paths, 68
  unresolved, 0 true positives** — vendored Unity `PackageCache` docs, crate sources cited
  deliberately per `research/AGENTS.md`, run-relative artifact names, and the comparison project's
  files. `agnix`'s `CDX-AG-005` implements exactly this check and produces ~60 false positives
  here. Relative markdown links: 82 checked, 0 broken, so `remark-validate-links` would find
  nothing either. **A conservative check that says nothing is a better instrument than a thorough
  one nobody trusts.**
- **No `CLAUDE.md` size gate**, despite `AGENTS.md` being 462 lines against Anthropic's documented
  *"target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce
  adherence"* (https://code.claude.com/docs/en/memory, fetched 2026-08-23). **That adherence claim
  is a vendor ASSERTION published with no measurement.** The mechanism to act on it if it is ever
  believed is `.claude/rules/` with `paths:` frontmatter, which loads a rule only when Claude reads
  matching files — genuinely deterministic and already available. But moving 7,300 tokens of
  hard-won rules out of always-on context on the strength of an unmeasured vendor line would be
  the same error this document is arguing against.

### A methodological note this survey itself paid for

The path-resolution check above was first run **inside an agent worktree**, where `eval/runs/` is
not checked out. It reported a different and confidently wrong picture. That is `AGENTS.md` rule
12 exactly — *the address is an input to the check* — arriving unprompted in the middle of writing
a document about checking things. The number in this brief is the one from the main checkout.

---

## 7. Two defects in this project's own tooling, found while doing this

Filed as **task 38**.

**`tasks.py add` from an agent worktree writes the file, then crashes.** `eval/tools/tasks.py:252`
calls `Path.relative_to(ROOT)` to print the created path, but `TASKS` resolves to the main
checkout while `ROOT` is the worktree. The task file **is created correctly**; the tool then exits
non-zero with a `ValueError` traceback. A successful create that reads as a failure is the
fail-open/fail-closed distinction of rule 7 pointed at the queue.

**`tasks.py check`'s reachability warning has the trigger-as-a-list defect, in code.** It warned
on task 32's `done_when` even though that `done_when` *has* an escape branch — "If no tool is
worth adopting, the file records that as the result… and that closes the task too" — because
`ESCAPE` at `eval/tools/tasks.py:302` is a nine-word keyword list and that phrasing matches none
of them. This is `AGENTS.md`'s own *"a rule whose trigger is a list must be re-derived by every
reader who meets an item not on the list"*, implemented as a list. And it is the companion to
rule 16: *a check that fires where nothing is wrong spends exactly the attention that a check
firing correctly needs.*

---

## Sources

Tools: [vale-cli/vale](https://github.com/vale-cli/vale) ·
[vale-cli/packages](https://github.com/vale-cli/packages) ·
[vale-cli/agent-tools](https://github.com/vale-cli/agent-tools) ·
[DavidAnson/markdownlint](https://github.com/DavidAnson/markdownlint) ·
[markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2) ·
[rvben/rumdl](https://github.com/rvben/rumdl) · [akiomik/mado](https://github.com/akiomik/mado) ·
[Automattic/harper](https://github.com/Automattic/harper) ·
[amperser/proselint (Codeberg)](https://codeberg.org/amperser/proselint) ·
[btford/write-good](https://github.com/btford/write-good) ·
[get-alex/alex](https://github.com/get-alex/alex) ·
[remarkjs/remark-lint](https://github.com/remarkjs/remark-lint) ·
[textlint/textlint](https://github.com/textlint/textlint) ·
[crate-ci/typos](https://github.com/crate-ci/typos) ·
[streetsidesoftware/cspell](https://github.com/streetsidesoftware/cspell) ·
[agent-sh/agnix](https://github.com/agent-sh/agnix) ·
[ltex-plus/ltex-ls-plus](https://github.com/ltex-plus/ltex-ls-plus)

Conventions and docs: [agents.md](https://agents.md/) · [llmstxt.org](https://llmstxt.org/) ·
[Claude Code memory](https://code.claude.com/docs/en/memory) ·
[Claude Code hooks](https://code.claude.com/docs/en/hooks) ·
[Claude Code plugins reference](https://code.claude.com/docs/en/plugins-reference) ·
[Agent Skills spec](https://agentskills.io/specification) ·
[Anthropic: effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) ·
[Anthropic: skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

Measurements by others: [Chroma, Context Rot, 2025-07-14](https://www.trychroma.com/research/context-rot) ·
[Ahrefs, llms.txt across 137k sites, 2026-06-15](https://ahrefs.com/blog/llmstxt-study/) ·
[Search Engine Land, llms.txt before/after, 2026-01-20](https://searchengineland.com/does-llms-txt-matter-467740)

Papers: [2602.11988](https://arxiv.org/abs/2602.11988) ·
[2607.27250](https://arxiv.org/abs/2607.27250) · [2601.20404](https://arxiv.org/abs/2601.20404) ·
[2606.20512](https://arxiv.org/abs/2606.20512) · [2606.15828](https://arxiv.org/abs/2606.15828) ·
[2606.09090](https://arxiv.org/abs/2606.09090) · [2605.08435](https://arxiv.org/abs/2605.08435) ·
[2509.21051](https://arxiv.org/abs/2509.21051) · [2510.14842](https://arxiv.org/abs/2510.14842) ·
[2307.03172](https://arxiv.org/abs/2307.03172) · [2402.14848](https://arxiv.org/abs/2402.14848) ·
[2402.08939](https://arxiv.org/abs/2402.08939) · [2502.05167](https://arxiv.org/abs/2502.05167)

**Not cited as evidence, deliberately:** arXiv:2603.00822 (ContextCov, 88.3% compliance) — its
stated code URL returns 404 as of 2026-08-23 and the result is unreproduced. arXiv:2607.14275 (a
seven-criterion context rubric) — multi-juror LLM scoring, one group, no peer review.
