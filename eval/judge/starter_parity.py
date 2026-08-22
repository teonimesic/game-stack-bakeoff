#!/usr/bin/env python3
"""Measure how far the four game-agnostic starters have drifted apart.

This is the check the coordinator asked for, and it is not paranoia: the earlier
Pong parity ports across these four stacks drifted, and the drift was invisible
because there was nothing measuring it. In a whole-game bake-off there are no held-out
unit tests to catch it either - if one starter is more helpful than another, that
difference is silently attributed to the stack.

Five comparisons, weakest to strongest:

  1. `just` recipe names           - do all four expose the same commands?
  2. AGENTS.md size and headings   - is one guide materially more helpful?
  3. Test counts                   - does one starter ship more safety net?
  4. Harness files present         - hook, CI, version notes, lint config
  5. THE HASH CHAIN                - drive all four starters through the identical
                                     input tape and compare the per-tick state hashes.

(5) is the one that matters. If four independently written implementations of the same
placebo rules produce the same 64-bit hash at every tick, they are not merely similar,
they are the same simulation to the last float bit. If they diverge, the numbers in the
bake-off are comparing four different games.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from probe import ProbeError, ProbeSession  # noqa: E402

STACKS = ("rust", "ts", "unity", "godot")


def recipes(repo: Path) -> list[str]:
    out = subprocess.run(["just", "--summary"], cwd=repo, capture_output=True,
                         text=True)
    if out.returncode != 0:
        out = subprocess.run(["just", "--list"], cwd=repo, capture_output=True,
                             text=True)
        return sorted({ln.strip().split()[0] for ln in out.stdout.splitlines()[1:]
                       if ln.strip()})
    return sorted(out.stdout.split())


def agents_md(repo: Path) -> dict[str, Any]:
    p = repo / "AGENTS.md"
    if not p.exists():
        return {"words": 0, "headings": []}
    text = p.read_text(encoding="utf-8", errors="replace")
    return {"words": len(text.split()),
            "headings": [h.strip() for h in re.findall(r"^#{2,3}\s+(.+)$", text,
                                                       re.M)]}


def harness_files(repo: Path) -> dict[str, bool]:
    return {
        "stop_hook": (repo / ".claude" / "hooks" / "verify-gate.sh").exists(),
        "claude_settings": (repo / ".claude" / "settings.json").exists(),
        "ci_workflow": (repo / ".github" / "workflows" / "ci.yaml").exists(),
        "version_notes": any((repo / "docs").glob("*notes*")) if (repo / "docs").exists()
                         else False,
        "golden_image": bool(list(repo.rglob("golden/*.png"))),
    }


def test_counts(repo: Path, timeout_s: int = 1200) -> dict[str, Any]:
    import static  # local import: pulls in runner.py's parsers
    c = static.run(repo, "test", ["just", "test"], timeout_s=timeout_s)
    passed, total = static.parse_test_counts(c.tail)
    return {"exit": c.code, "passed": passed, "total": total,
            "seconds": round(c.seconds, 1)}


TAPE: list[dict[str, Any]] = (
    [{}] * 40 + [{"nudge_up": True}] * 40 + [{}] * 40
    + [{"nudge_down": True}] * 40 + [{}] * 240
)


def hash_chain(repo: Path) -> tuple[list[str], str]:
    try:
        with ProbeSession(repo=repo, seed=7) as s:
            for inp in TAPE:
                s.step_raw(inp)
            return [t.hash for t in s.history], ""
    except ProbeError as e:
        return [], str(e)


#: Recipes every stack MUST expose, because a building agent is told to use them and the
#: grading harness calls them by name. Anything beyond this is a stack tuning its own
#: workflow, which is the point of having four templates rather than one.
CORE_RECIPES = {"verify", "test", "lint", "fmt", "probe", "film", "run"}

#: THREE AXES THIS TOOL DID NOT COVER, each found by something breaking that it had no
#: opinion about. It compared recipes and hash chains, which are the axes somebody thought
#: of; the failures came from elsewhere.
#:
#:   launch discipline  - the shared `tools/launch.just`, byte-identical in all four. A
#:                        Unity player appeared on the operator's desktop with sound
#:                        because the guard was written per-recipe instead of per-resource.
#:   capability parity  - can the starter make sound AT ALL? godot and ts can out of the
#:                        box; rust (bevy default-features=false, no audio feature) and
#:                        unity (no com.unity.modules.audio) cannot, and the task asks
#:                        every agent for audio on a SCORED criterion. Reported, not
#:                        failed: it may be a real property of those two stacks rather
#:                        than a defect, and that argument belongs in IMPROVEMENTS.md.
#:   capture geometry   - see tools/frame_parity.py; one submission filmed at 768x576
#:                        while 21 filmed at 640x400 (#59).
SHARED_LAUNCH = "tools/launch.just"


def _audio_capability(root):
    """Can this starter open an audio device without the agent adding a dependency?"""
    import json as _j
    s = root.name
    if s == "unity":
        m = root / "Packages" / "manifest.json"
        try:
            return "com.unity.modules.audio" in _j.loads(m.read_text()).get("dependencies", {})
        except Exception:
            return None
    if s == "rust":
        c = root / "Cargo.toml"
        try:
            txt = c.read_text()
        except OSError:
            return None
        return ("bevy_audio" in txt) or ("default-features = false" not in txt)
    if s == "godot":
        return True          # engine built-in
    if s == "ts":
        return True          # Web Audio API, no dependency
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--starters", type=Path,
                    default=Path(__file__).resolve().parent.parent / "starters")
    ap.add_argument("--stacks", nargs="*", default=list(STACKS))
    ap.add_argument("--skip-tests", action="store_true",
                    help="skip `just test` (slow on Unity)")
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args()

    present = [s for s in a.stacks if (a.starters / s).exists()]
    missing = [s for s in a.stacks if s not in present]
    report: dict[str, Any] = {"present": present, "missing": missing, "stacks": {}}
    problems: list[str] = []
    notes: list[str] = []

    for s in present:
        repo = a.starters / s
        d: dict[str, Any] = {
            "recipes": recipes(repo),
            "agents_md": agents_md(repo),
            "harness": harness_files(repo),
        }
        if not a.skip_tests:
            d["tests"] = test_counts(repo)
        chain, err = hash_chain(repo)
        d["hash_chain_len"] = len(chain)
        d["hash_error"] = err
        d["_chain"] = chain
        report["stacks"][s] = d

    # 1. recipes
    sets = {s: set(report["stacks"][s]["recipes"]) for s in present}
    if sets:
        common = set.intersection(*sets.values())
        # ONLY THE CORE RECIPES ARE REQUIRED EVERYWHERE. The four templates are
        # deliberately tuned per stack, so `analyzers` (unity), `api-notes` (ts) and
        # `quick` (rust) exist on one stack by design. Requiring set equality made this
        # check fire on EVERY stack on EVERY run, which is not a guard - it is noise
        # that guarantees the tool can never go green (FINDINGS #44, #57).
        for s in present:
            missing_core = sorted(CORE_RECIPES - sets[s])
            if missing_core:
                problems.append(f"{s} is missing CORE recipes {missing_core} - every "
                                f"stack must expose the same contract to a building agent")
            notes.append(f"recipes only in {s}: {sorted(sets[s] - common)}")
        if False:
            extra = gone = set()
            if extra or gone:
                problems.append(f"recipes differ in {s}: only-here={sorted(extra)} "
                                f"missing-here={sorted(gone)}")

    # 2. AGENTS.md
    words = {s: report["stacks"][s]["agents_md"]["words"] for s in present}
    if words:
        lo, hi = min(words.values()), max(words.values())
        if lo and hi / lo > 1.35:
            problems.append(f"AGENTS.md sizes span {lo}-{hi} words "
                            f"({hi / lo:.2f}x) - one guide may be materially more "
                            f"helpful than another")

    # 3. harness files
    for key in ("stop_hook", "claude_settings", "ci_workflow", "version_notes",
                "golden_image"):
        vals = {s: report["stacks"][s]["harness"][key] for s in present}
        if len(set(vals.values())) > 1:
            problems.append(f"harness file mismatch on {key}: {vals}")

    # 5. the hash chain - the one that matters
    chains = {s: report["stacks"][s]["_chain"] for s in present
              if report["stacks"][s]["_chain"]}
    failed = [s for s in present if not report["stacks"][s]["_chain"]]
    for s in failed:
        problems.append(f"{s}: probe did not run - "
                        f"{report['stacks'][s]['hash_error'][:180]}")
    if len(chains) > 1:
        ref_stack = sorted(chains)[0]
        ref = chains[ref_stack]
        for s, ch in sorted(chains.items()):
            if s == ref_stack:
                continue
            if len(ch) != len(ref):
                problems.append(f"{s}: chain length {len(ch)} vs {ref_stack} "
                                f"{len(ref)}")
                continue
            div = next((i for i, (x, y) in enumerate(zip(ref, ch)) if x != y), None)
            if div is None:
                report.setdefault("hash_identical_to", {})[s] = ref_stack
            else:
                # CROSS-STACK HASH EQUALITY IS NOT A GOAL, and DECISIONS.md says so:
                # "the requirement is within-stack determinism only - cross-stack hash
                # equality is not achievable and is not a goal. Unity's 1-ULP
                # divergence is a Mono/ARM64 property (FMA contraction) not reachable
                # from source."
                #
                # This check failed on it anyway, so the tool exited 1 on a condition
                # the project had formally decided was acceptable - and a guard that is
                # permanently red is a guard nobody reads. Reported, not failed.
                notes.append(
                    f"{s} diverges from {ref_stack} at tick {div}: "
                    f"{ref[div]} vs {ch[div]}. Cross-stack hash equality is NOT a "
                    f"goal (DECISIONS.md); within-stack determinism is what is "
                    f"enforced, and `determinism.replay` measures it per stack.")

    # -- the shared launch file must be byte-identical everywhere -------------- #
    import hashlib
    hashes = {}
    for s in present:
        f = a.starters / s / SHARED_LAUNCH
        hashes[s] = (hashlib.sha256(f.read_bytes()).hexdigest()[:16]
                     if f.is_file() else "MISSING")
    src = a.starters / "_shared" / "launch.just"
    if src.is_file():
        hashes["_shared"] = hashlib.sha256(src.read_bytes()).hexdigest()[:16]
    distinct = set(hashes.values())
    if len(distinct) != 1:
        problems.append(f"the shared launch file differs between starters: {hashes} - "
                        f"it is ONE source (`starters/_shared/launch.just`) copied into "
                        f"each tree, and four copies that can drift is the thing it "
                        f"exists to prevent")
    else:
        notes.append(f"shared launch discipline identical in all four: {distinct.pop()}")
    report["launch_hashes"] = hashes

    # -- capability parity: reported, never failed ----------------------------- #
    caps = {s: _audio_capability(a.starters / s) for s in present}
    report["audio_capability"] = caps
    if len(set(caps.values())) > 1:
        yes = sorted(k for k, v in caps.items() if v)
        no = sorted(k for k, v in caps.items() if v is False)
        notes.append(f"AUDIO CAPABILITY IS NOT EQUAL: {yes} ship it, {no} need the agent "
                     f"to add a dependency first - and the task asks every agent for "
                     f"sound on a scored criterion. REAL BUT MEASURED SMALL, so do not "
                     f"reach for it to explain a cost gap: measured from the stored "
                     f"diffs, unity's dependency work is +1 line in manifest.json (+6 "
                     f"lock) and rust's is 12-14 lines in Cargo.toml, while ALL FOUR "
                     f"stacks then author a ~300-line WAV synthesiser (ts 320, rust 340, "
                     f"unity 305, godot 46 on top of the engine's built-in). Reported, "
                     f"not failed: see eval/IMPROVEMENTS.md.")

    # -- recipe BEHAVIOUR now differs by stack; say so before it looks like drift --- #
    notes.append(
        "`run` is GATED DURING TRIALS ON RUST ONLY: Bevy 0.19 on macOS keeps the "
        "application frontmost even with the window hidden and minimised (measured three "
        "ways); godot and unity have working no-raise hooks and ts opens no window. The "
        "rust recipe refuses when STARTER_NO_RAISE=1 and explains why. Reported, not "
        "failed - it is a property of that engine on this OS. See "
        "starters/_shared/launch.just.")

    for d in report["stacks"].values():
        d.pop("_chain", None)
    report["problems"] = problems
    report["notes"] = notes

    print(f"starters present: {present}" + (f"  MISSING: {missing}" if missing else ""))
    print(f"\n{'stack':<8} {'recipes':>8} {'AGENTS':>8} {'tests':>12} {'chain':>7} "
          f"{'hook':>5} {'ci':>4}")
    for s in present:
        d = report["stacks"][s]
        t = d.get("tests") or {}
        print(f"{s:<8} {len(d['recipes']):>8} {d['agents_md']['words']:>8} "
              f"{(str(t.get('passed', '?')) + '/' + str(t.get('total', '?'))):>12} "
              f"{d['hash_chain_len']:>7} "
              f"{'yes' if d['harness']['stop_hook'] else 'NO':>5} "
              f"{'yes' if d['harness']['ci_workflow'] else 'NO':>4}")
    if report.get("hash_identical_to"):
        for s, ref in report["hash_identical_to"].items():
            print(f"\n  hash chain over {len(TAPE)} scripted ticks: {s} is "
                  f"BYTE-IDENTICAL to {ref}")
    if notes:
        print(f"\nEXPECTED AND ACCEPTED - {len(notes)} note(s), not failures:")
        for nline in notes:
            print(f"  {nline}")
    if problems:
        print(f"\nDRIFT - {len(problems)} finding(s):")
        for p in problems:
            print(f"  {p}")
    else:
        print("\nNo drift detected on any measured axis.")
    if a.json:
        a.json.write_text(json.dumps(report, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
