# Templates & agent-repo conventions (verified 2026-08-10)

## THE HEADLINE FINDING

**No mainstream game template has a single test.** `grep -rc '#\[test\]' src/` returns **0**
for `bevy_new_2d`, `bevy_new_minimal`, `bevy_github_ci_template`, and
`NiklasEi/bevy_game_template` (1137★). None of them has AGENTS.md, CLAUDE.md, or
`.cursor/rules` either.

Meanwhile **Bevy already ships production-grade rendering verification for its own CI** and
no template uses it:
- `bevy_render/src/view/window/screenshot.rs` → `Screenshot`, `ScreenshotCaptured`, `save_to_disk`
- `bevy_dev_tools/src/ci_testing/` → purpose-built CI harness; `trigger_screenshots` spawns
  `Screenshot::primary_window()` on a schedule, driven by `CI_TESTING_CONFIG`
- `.github/workflows/example-run.yml` → runs every example headless, captures `screenshot-*.png`
- `.github/workflows/send-screenshots-to-pixeleagle.yml` → uploads to **Pixel Eagle**
  (https://pixel-eagle.com), Bevy's visual-regression service, SHA-256 hashed for fast equality

And Anthropic's own top-billed best practice is literally *"Give Claude a way to verify its
work: tests, a build, **a screenshot to compare**."*

=> **The gap is real and it is exactly the thing we're building.**

## Prior art occupying adjacent space

| Project | ★ | What it does | Where it stops short |
|---|---|---|---|
| [htdt/godogen](https://github.com/htdt/godogen) | 5321 | Multi-engine (Godot/Bevy/Babylon) agent game *generator*. "Proof over claims — the agent judges results from the running game, not from a clean compile." | Verification = watching a live run or 15–20s clip. No deterministic pixel-diff CI gate, no `just verify`, no MCP. |
| [PlayableIntelligence/game-creator](https://github.com/PlayableIntelligence/game-creator) | 309 | Claude Code plugin, Phaser/Three.js. **QA subagent runs 5 phases per step**: build → headless-Chromium runtime → gameplay verification → architecture validation → **visual review via Playwright MCP screenshots**, autofix-and-retry ×3 gating progress. | Browser canvas only; VLM screenshot *review*, not deterministic baseline diff. **Closest working instance of our exact pattern.** |
| [leigest519/OpenGame](https://github.com/leigest519/OpenGame) + [arXiv:2604.18394](https://arxiv.org/html/2604.18394v1) | 2799 | "Open Agentic Coding for Games". **OpenGame-Bench** = build → serve → headless-browser automated play → ≥1 non-empty screenshot → score "Visual Usability" via pixel heuristic (frame entropy + motion detection) **plus VLM judge**, plus "Intent Alignment" vs structured spec. | Research benchmark, not a clonable template. **Directly informs our eval design.** |
| `bevy_mod_screenshot_test` v0.2.0 (2026-07-15, **61 downloads**) | — | Bevy screenshot testing on top of `rendiff` | Brand new, unproven |
| [`rendiff`](https://github.com/kpreid/rendiff) v0.2.2 | — | The image-diff crate underneath it (28.5k downloads) | — |

Four independent sub-90★ projects converging on this idea within the last ~2 months
(`godot-mcp-enhanced` frame-verify, `godot-visual-regression`, `bevy_mod_screenshot_test`,
`godot-2d-agent-template`) — strongest signal that it's an open opportunity.

Image diff engines: [`odiff`](https://github.com/dmtrKovalenko/odiff) (3150★, SIMD),
`dify` (Rust), `image-compare`.

Engine MCP servers: Unity 13.3k★, Godot 5.1k★, Unreal 2.1k★ — **Bevy MCP is unclaimed**
(every hit has 0 stars). But `bevy_brp_mcp` 0.19.0 exists via the **Bevy Remote Protocol**
(BRP) — JSON-RPC over WebSocket to query/mutate a live ECS world. That's a first-party
agent-inspection channel no other engine has.

## bevy_new_2d — what to steal, what to avoid

Repo: https://github.com/TheBevyFlock/bevy_new_2d (475★, MIT/Apache/CC0, updated to Bevy
0.19 on 2026-08-06). `cargo-generate` template, not a GitHub template repo.

**Steal:**
- Two orthogonal state machines: `Screen {Splash,Title,Loading,Gameplay}` + separate `Menu`
  state + `Pause(bool)`. Teardown via `DespawnOnExit(Screen::X)`.
- Global `AppSystems` SystemSet chain: `TickTimers → RecordInput → Update`, plus a
  `PausableSystems` set gated on `in_state(Pause(false))`. **This is the determinism-relevant
  ordering discipline.**
- Convention: *one plugin per file*; plugins are plain `pub(super) fn plugin(app: &mut App)`
  functions, not structs. Entity templates are `fn foo(..) -> impl Bundle` composed with
  `children![]`.
- Profiles:
  ```toml
  [profile.dev] opt-level = 1
  [profile.dev.package."*"] opt-level = 3
  [profile.ci] inherits="dev", opt-level=0, debug="line-tables-only", codegen-units=4
  [profile.release] codegen-units=1, lto="thin"
  ```
- Three-layer lint config: `[lints.clippy]` in Cargo.toml + `clippy.toml`
  (`standard-macro-braces` for `children![]`) + `bevy_lint` registration via
  `#![cfg_attr(bevy_lint, feature(register_tool), register_tool(bevy))]`.

**Avoid:**
- `bevy_cli` as a hard dependency — **alpha, NOT on crates.io** (the crates.io `bevy_cli` is
  an unrelated 2021 squat), last CLI release `cli-v0.1.0-alpha.2` on **2025-09-24**, ~11
  months stale. README says "Here be dragons 🐉".
  **But `bevy_lint` is healthy** (`lint-v0.6.0`, 2026-02-01) — consume it via the
  `TheBevyFlock/bevy_cli/bevy_lint@main` GitHub Action, not via the CLI.
- Its CI as a model — 6 jobs but the `tests` job runs an empty test set.

Note: `bevy_new_3d` **does not exist**. De-facto 3D counterpart is
[olekspickle/bevy_new_3d_rpg](https://github.com/olekspickle/bevy_new_3d_rpg) (92★) — the only
mainstream Bevy template shipping a `justfile`.

Also: `.cargo/config_fast_builds.toml` now says **"On macOS, the default linker yields higher
performance than LLD"** — do not blindly add mold/lld on macOS.

## Best Rust-native verification-harness prior art

**`bevyengine/bevy/tools/ci`** — a Rust binary run as `cargo run -p ci`, using `argh` +
`xshell`. Subcommands: `format clippy lints test test_check doc doc_check doc_test compile
compile_check compile_fail bench_check example_check integration_test ...`.
Global `--keep-going` **accumulates failures and panics with a bulleted list at the end** —
precisely the legible aggregate error output agents need. Repo root also carries `deny.toml`,
`typos.toml`, `clippy.toml`, `rustfmt.toml`.

**`godot-rust/gdext/check.sh`** — `DEFAULT_COMMANDS=("fmt" "clippy" "test" "itest")` where
`itest/` runs integration tests **inside a live Godot process**. Closest thing to engine-level
E2E in the Rust ecosystem.

## Task runner: `just` wins

| Tool | Version (2026-08-10) | ★ | Machine-readable task list |
|---|---|---|---|
| **just** | 1.58.0 (2026-08-03) | 35222 | ✅ `just --dump --dump-format json` — recipes, params, deps, doc comments |
| mise | v2026.8.3 | 32226 | ✅ `mise tasks ls -J` (also does toolchain pinning + env) |
| go-task | v3.52.0 | 15948 | ✅ `task --list --json` |
| GNU make | 4.4.1 (2023) | — | ❌ none — agents resort to `make -qp` (noisy) or regex |
| cargo-make | 0.37.24 (**2025-01-18**) | 2943 | ❌ none; **stale**, 19mo no release |

=> **`just`**, optionally `mise` for toolchain pinning. `just --dump --dump-format json` is
the machine-readable verification manifest — **no such field exists in the AGENTS.md spec**;
the convention that won is "name one shell command in prose, structure lives in the runner."
[`toolprint/just-mcp`](https://github.com/toolprint/just-mcp) exposes each recipe as an MCP tool.

Real prior art: `dinglebear-ai/soma` tags justfile docs `audience: ["contributors","agents"]`,
`just verify` = `fmt-check + lint + check + test`, and uses `cargo xtask symlink-docs` to keep
AGENTS.md/CLAUDE.md/GEMINI.md as symlinks to one source.

## AGENTS.md vs CLAUDE.md — settled

[agents.md](https://agents.md/) is stewarded by the **Agentic AI Foundation (Linux Foundation)**,
60,000+ repos, adopted by ~20 tools. Plain Markdown, no frontmatter, nested files take local
precedence.

Claude Code docs state directly:
> *"Claude Code reads `CLAUDE.md`, not `AGENTS.md`. If your repository already uses `AGENTS.md`
> for other coding agents, create a `CLAUDE.md` that imports it."*

=> **AGENTS.md is source of truth; CLAUDE.md is a thin `@AGENTS.md` import + Claude-specific
extras.** This is Anthropic's documented advice, not a workaround.

[GitHub's study of 2500+ AGENTS.md files](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/)
found six consistently covered areas — commands, testing, project structure, code style, git
workflow, boundaries — with a three-tier convention: ✅ always / ⚠️ ask first / 🚫 never.

## Anthropic's own guidance (fetched from code.claude.com/docs)

Framing: *"Most best practices are based on one constraint: Claude's context window fills up
fast, and performance degrades as it fills."*

Headline section — **"Give Claude a way to verify its work"**:
> *"Give Claude a check it can run: tests, a build, a screenshot to compare. It's the difference
> between a session you watch and one you walk away from... Claude stops when the work looks
> done. Without a check it can run, 'looks done' is the only signal available, and you become
> the verification loop."*

Escalating enforcement: in-prompt → `/goal` re-checked each turn → **Stop hook that blocks
turn-end until a script passes** (overridden after 8 consecutive blocks) → **verification
subagent with clean context**.

CLAUDE.md authoring rules — include: commands Claude can't guess, style rules that differ from
defaults, testing instructions, repo etiquette, project-specific architecture decisions, env
quirks, non-obvious gotchas. Exclude: anything derivable from reading code, standard conventions,
detailed API docs, frequently-changing info, long tutorials, file-by-file descriptions,
self-evident advice.
> *"For each line ask: 'Would removing this cause Claude to make mistakes?' If not, cut it.
> Bloated CLAUDE.md files cause Claude to ignore your actual instructions!"*

**Target under 200 lines.** New **`.claude/rules/`** dir splits instructions into topic files
with YAML frontmatter `paths:` globs so a rule loads only when Claude touches matching files.
Root CLAUDE.md survives `/compact`; nested files don't.

Five named failure patterns: kitchen-sink session · correcting over and over · the
over-specified CLAUDE.md · the trust-then-verify gap · the infinite exploration.

## Other empirical findings on agent success

- **OpenAI "Harness Engineering" (Feb 2026)**: *harness* = *"the full environment of
  scaffolding, constraints, and feedback loops that surrounds an AI agent — repository
  structure, CI configuration, formatting rules, package managers, frameworks, project
  instructions, external tool integration, and linters."* Case study: 3-person team, empty repo,
  Aug 2025–Jan 2026, **zero human-written lines → 1M LOC, 1500 merged PRs.**
- **[Cognition](https://cognition.com/blog/multi-agents-working)**: *"multi-agent systems work
  best today when writes stay single-threaded and the additional agents contribute intelligence
  rather than actions."* A **reviewer agent with clean separate context catches ~2 bugs per PR,
  58% severe.** Parallel writers still fail.
- **[Ronacher](https://lucumr.pocoo.org/2025/6/12/agentic-coding/)**: *"Tools need to be fast.
  The quicker they respond (and the less useless output they produce) the better."* **Always log
  to a file** so the agent can self-diagnose. Tools must be *"protected against an LLM chaos
  monkey using them completely wrong."* Prefer simple test invocation — *"Agents struggle with
  Python's magic (eg: Pytest's fixture injection)."* Prefer long descriptive function names over
  deep hierarchies.
- **[Huntley, "Ralph Wiggum"](https://ghuntley.com/ralph/)**: `while :; do cat PROMPT.md |
  claude-code; done`. Scaffold: `PROMPT.md`, `fix_plan.md` (agent-maintained backlog), `specs/`,
  `AGENT.md`, `src/`, `examples/`, tight tests. **One thing per loop**; parallel subagents for
  search but **serialized build/test validation**; explicitly instruct "search codebase before
  assuming not implemented".
- **Hamel Husain**: three-layer contract — *docs tell the agent what to do, telemetry tells it
  whether it worked, evals tell it whether the output is good.*
- **Git hooks vs instructions**: instruction files get ~90–95% compliance; hooks make violation
  impossible. Hook error messages **must be written for the agent** (exact rule, file/line,
  replacement example) or it can't self-correct. **Adversarial failure mode: agents run
  `git commit --no-verify`** → counter with a harness-level PreToolUse hook that refuses it.
  Use **lefthook** (Go, parallel, ~10x faster than husky) — latency caps iterations/session.

## Rust hygiene stack — 2026 verdicts

- test runner: **cargo-nextest 0.9.143**
- coverage: **cargo-llvm-cov 0.8.7** (won over tarpaulin, which is alive but Linux-only ptrace)
- snapshot: **insta 1.48** · fixtures: **rstest 0.26.1** · property: **proptest 1.11**
- mutation: **cargo-mutants v27.1.0** (integrates with nextest as runner; `--shard i/N`, or
  `--file`/`--re` for PR-diff-incremental)
- bench: **criterion 0.8.2** or **divan 0.1.21** (both alive) + **codspeed** (free unlimited for
  OSS; `codspeed-divan-compat` / `codspeed-criterion-compat` drop-ins) or **iai-callgrind 0.16.1**
  for instruction-count noise-free CI
- deps: **cargo-deny 0.20.2**, cargo-audit, **cargo-semver-checks 0.50.0**,
  **cargo-machete 0.9.2** (fast, pre-commit) + **cargo-shear 1.13.3** (rust-analyzer parser,
  auto-fixes, handles workspace-level deps)
- **edition 2024 is the `cargo new` default** ⇒ resolver 3 ⇒ MSRV-aware resolution; set
  `workspace.rust-version` explicitly
- `-Zthreads` parallel frontend **still not stabilized** (2026 Project Goal)
- linker: **wild 0.10.0** is real now (3829★, Rust Foundation Innovation Lab) but **Linux-only**;
  on **macOS the default linker beats LLD** — don't add one
- 2025 State of Rust Survey: **78% of Rust devs now use AI coding assistants**
