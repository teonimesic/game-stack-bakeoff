#!/usr/bin/env python3
"""Does `anonymise.neutralise` remove a stack's name, and can it still leave code alone?

THE INPUT THAT PRODUCES THE DEFECT IS A NAME IN A CASE OR A POSITION NOBODY ENUMERATED.
`_STACK_TOKENS` was a list of SPELLINGS -- `\\bbevy\\b`, `\\bBevy\\b` -- so `BEVY_ASSET_ROOT`
and `CARGO_MANIFEST_DIR` walked through it untouched and reached 22 of 68 stored packs
(#83, task 73).  `anonymise.py`'s own comment already recorded the same class from
`UnityCsReference`.  A mutant that deletes a rule cannot manufacture that input; only a
VARIANT -- real stored pack text fed through the real function -- can (rule 15).

So this file runs four things, and the last two are the ones that matter:

  1. MUTANT   -- drop one declared name and the leak it covers must come back.  A rule
                 that cannot fail is worse than absent.
  2. PROBE    -- every declared name, in all three case conventions an identifier
                 segment takes, plus the exact one-line probe from the task 73 ticket.
  3. VARIANT+ -- `fixtures/stack_leak_corpus.txt`: 128 distinct lines harvested from the
                 real stored packs that the OLD rewriter left carrying a stack name.
                 None may survive.
  4. VARIANT- -- `fixtures/stack_safe_corpus.txt`: 400 lines from the same packs where a
                 stack name appears INSIDE an innocent word -- `immunity`, `Vec3.UnitY`,
                 `main.tscn`, `bestScore`, `is_three_dimensional`, `trust`.  Every one
                 must come out byte-identical.  This is the half that stops the repair
                 from being "match the name anywhere, case-insensitively", which would
                 have rewritten 54 occurrences of `immunity` into `immEngine`.

Run:  python3 judge/anonymise_selftest.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import anonymise  # noqa: E402

FAILS: list[str] = []


def expect(name: str, cond: bool, detail: str) -> None:
    if not cond:
        FAILS.append(f"{name}: {detail}")


# ---------------------------------------------------------------------------
# 1. The ticket's probe, verbatim.  Reproducing this by hand is what raised task 73
#    to priority 1: it is the LIVE anonymiser, not a stored artefact.
# ---------------------------------------------------------------------------
PROBE_IN = "CARGO_MANIFEST_DIR=/x/crates/game BEVY_ASSET_ROOT=/y"
out = anonymise.neutralise(PROBE_IN)
for tok in ("CARGO", "crates", "BEVY"):
    expect("ticket-probe", tok not in out,
           f"{tok!r} survived the ticket's own probe: {out!r}")
print(f"1 ticket probe            {PROBE_IN!r}\n                       -> {out!r}")


# ---------------------------------------------------------------------------
# 2. Every declared name, in the three case conventions an identifier segment takes,
#    embedded in an identifier rather than standing alone -- because standing alone is
#    the only shape the old list could match.
# ---------------------------------------------------------------------------
def _forms(name: str) -> list[str]:
    return [f"let x = pre_{name}_root;",
            f"const X = PRE_{name.upper()}_ROOT;",
            f"var x = Pre{name.capitalize()}Root;"]


unmatched: list[str] = []
for nm in sorted(anonymise._STACK_NAMES):
    for form in _forms(nm):
        got = anonymise.neutralise(form)
        if nm in got.lower():
            unmatched.append(f"{nm} in {form!r} -> {got!r}")
expect("every-name-in-every-case", not unmatched,
       f"{len(unmatched)} name/case pair(s) survived, e.g. {unmatched[:4]}")
print(f"2 names x case conventions  {len(anonymise._STACK_NAMES)} names x 3 forms  "
      f"survived={len(unmatched)}")


# ---------------------------------------------------------------------------
# 3. MUTANT.  Remove one name from the vocabulary and the probe it covers must come
#    back.  Run for every name, so no entry is dead weight and every one is pinned.
# ---------------------------------------------------------------------------
dead: list[str] = []
real = anonymise._STACK_NAMES
try:
    for nm in sorted(real):
        anonymise._STACK_NAMES = {k: v for k, v in real.items() if k != nm}
        anonymise._rebuild_matcher()
        if all(nm not in anonymise.neutralise(f).lower() for f in _forms(nm)):
            dead.append(nm)
finally:
    anonymise._STACK_NAMES = real
    anonymise._rebuild_matcher()
expect("mutant-every-name-live", not dead,
       f"removing {dead} changed nothing, so those entries are not what scrubs them")
print(f"3 mutant (drop each name)   {len(real)} mutants  silent={len(dead)}")


# ---------------------------------------------------------------------------
# 4. VARIANT +/-: real stored pack text, not tokens anyone thought of.
# ---------------------------------------------------------------------------
FIX = HERE / "fixtures"


def _corpus(name: str) -> list[str]:
    p = FIX / name
    if not p.is_file():
        FAILS.append(f"corpus-present: {p} is missing -- an absent corpus is "
                     f"UNMEASURABLE, not clean")
        return []
    return [ln for ln in p.read_text().splitlines() if ln.strip()]


leaks = _corpus("stack_leak_corpus.txt")
survivors: list[str] = []
for ln in leaks:
    got = anonymise.neutralise(ln)
    if anonymise.find_stack_names(got):
        survivors.append(f"{anonymise.find_stack_names(got)} in {got.strip()[:90]!r}")
expect("variant-leak-corpus", leaks and not survivors,
       f"{len(survivors)} of {len(leaks)} real leaking lines still name a stack, "
       f"e.g. {survivors[:3]}")
print(f"4 variant+ (real leaks)     {len(leaks)} lines  surviving={len(survivors)}")

safe = _corpus("stack_safe_corpus.txt")
corrupted: list[str] = []
for ln in safe:
    got = anonymise.neutralise(ln)
    if got != ln:
        corrupted.append(f"{ln.strip()[:70]!r} -> {got.strip()[:70]!r}")
expect("variant-safe-corpus", safe and not corrupted,
       f"{len(corrupted)} of {len(safe)} innocent lines were rewritten, "
       f"e.g. {corrupted[:3]}")
print(f"5 variant- (innocent words) {len(safe)} lines  corrupted={len(corrupted)}")


# ---------------------------------------------------------------------------
# 5. Idempotence.  `field.build_pack` neutralises a file that `anonymise.build_pack`
#    already neutralised, so a second pass must be a no-op.  Without this a
#    replacement that is itself a name would rot a pack one judging round at a time.
# ---------------------------------------------------------------------------
once = [anonymise.neutralise(ln) for ln in leaks + safe]
twice = [anonymise.neutralise(ln) for ln in once]
expect("idempotent", once == twice,
       f"{sum(1 for a, b in zip(once, twice) if a != b)} line(s) changed on a second "
       f"pass -- a replacement is being rewritten again")
print(f"6 idempotent                {len(once)} lines  changed on 2nd pass="
      f"{sum(1 for a, b in zip(once, twice) if a != b)}")


# ---------------------------------------------------------------------------
# 6. The pack-wide sweep, when the stored runs are reachable.  Reported three-valued:
#    a real count, or an explicit non-measurement.  `eval/runs/` is gitignored, so an
#    agent worktree legitimately has none -- but "no packs found" must never print as
#    "0 packs leaking" (rule 1).
# ---------------------------------------------------------------------------
runs = HERE.parent / "runs"
packs = sorted(p for p in runs.rglob("judge_pack/code") if p.is_dir()) if runs.is_dir() \
    else []
if not packs:
    print(f"7 stored-pack sweep         UNMEASURABLE -- no judge packs under {runs}")
else:
    bad = []
    for d in packs:
        names: set[str] = set()
        for f in sorted(d.rglob("*")):
            if f.is_file():
                names |= set(anonymise.find_stack_names(
                    anonymise.neutralise(f.read_text(errors="replace"))))
        if names:
            bad.append((str(d.relative_to(runs)), sorted(names)))
    expect("stored-packs-clean", not bad,
           f"{len(bad)} of {len(packs)} stored packs still carry a stack name, "
           f"e.g. {bad[:2]}")
    print(f"7 stored-pack sweep         {len(packs)} packs  leaking={len(bad)}")


print(f"\n{len(FAILS)} unmet expectation(s)")
for f in FAILS:
    print("  FAIL", f)
raise SystemExit(1 if FAILS else 0)
