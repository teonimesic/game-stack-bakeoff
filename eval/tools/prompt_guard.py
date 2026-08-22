#!/usr/bin/env python3
"""Assertions on the task prompts. Run before any comparison that uses them.

The prompts are ONE template per game rendered per stack — four `gN_*(stack)` functions,
seven vocabulary dicts, no per-stack copies. Two ways that structure silently breaks, one
per axis:

  STACK axis  an engine name written into a game body instead of a vocabulary dict. The
              prompt stops being stack-neutral and hands one stack its own words. The
              first bake-off did exactly this with byte-identical prompts and cost a run:
              turn counts reversed after the fix (rust 32->49, ts 50->43).

  GAME axis   `_preamble()` is shared by every game. An edit aimed at one game reaches all
              of them -- correctly where aimed, invisibly everywhere else. A mouse-aiming
              clause written for the 3D arena landed in Pong, Tetris and the platformer,
              and would have contaminated the one experiment whose whole design was a
              single variable (FINDINGS #41).

Usage:
    python3 tools/prompt_guard.py                 # both assertions
    python3 tools/prompt_guard.py --snapshot DIR  # record rendered prompts
    python3 tools/prompt_guard.py --diff DIR      # diff rendered against a snapshot

Exit 1 on any violation, so it can gate a run.
"""
from __future__ import annotations

import argparse, difflib, hashlib, json, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "suites"))
import wholegame_prompts as W  # noqa: E402

STACKS = ("rust", "ts", "unity", "godot")
# Engine and library names that belong in a vocabulary dict, never in a game body.
ENGINE_WORDS = ("Bevy", "Godot", "Unity", "three.js", "GDScript", "C#", "AudioStreamPlayer",
                "AudioSource", "AudioPlayer", "Node2D", "Node3D", "cargo", "pnpm")


def _game_bodies() -> dict[str, str]:
    src = open(W.__file__).read()
    out, marks = {}, [(m.group(1), m.start()) for m in re.finditer(r"^def (g\d+_\w+)\(", src, re.M)]
    for i, (name, start) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else src.find("\nTASKS", start)
        out[name] = src[start:end]
    return out


def assert_no_engine_names() -> list[str]:
    """STACK axis: a game body naming an engine is no longer stack-neutral."""
    bad = []
    for name, body in _game_bodies().items():
        for w in ENGINE_WORDS:
            if w in body:
                bad.append(f"{name}: game body names `{w}` — move it to a vocabulary dict")
    return bad


def assert_stack_neutral() -> list[str]:
    """Rendered prompts must differ ONLY in substituted vocabulary."""
    bad = []
    for game in W.TASKS:
        texts = {s: W.TASKS[game](s) for s in STACKS}
        base = texts["rust"].split("\n")
        for s in STACKS[1:]:
            d = [l for l in difflib.unified_diff(base, texts[s].split("\n"), lineterm="", n=0)
                 if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
            # Vocabulary substitution touches a handful of lines. Much more than that means
            # game rules themselves diverge by stack, which is not a fair comparison.
            if len(d) > 14:
                bad.append(f"{game}: rust vs {s} differs on {len(d)} lines — "
                           f"rules, not just vocabulary, vary by stack")
    return bad


def snapshot(path: str) -> int:
    os.makedirs(path, exist_ok=True)
    idx = {}
    for game in W.TASKS:
        for s in STACKS:
            t = W.TASKS[game](s)
            open(os.path.join(path, f"{game}__{s}.txt"), "w").write(t)
            idx[f"{game}__{s}"] = hashlib.sha256(t.encode()).hexdigest()[:16]
    json.dump(idx, open(os.path.join(path, "index.json"), "w"), indent=2, sort_keys=True)
    print(f"snapshot: {len(idx)} rendered prompts -> {path}")
    return 0


def diff(path: str) -> int:
    """GAME axis: what the agents ACTUALLY received vs what renders now.

    Diff the rendered inputs, not the source that renders them. A shared preamble makes
    the source look untouched while every game's prompt has changed.
    """
    idx_p = os.path.join(path, "index.json")
    if not os.path.exists(idx_p):
        print(f"no snapshot at {path} — run --snapshot first"); return 1
    old = json.load(open(idx_p))
    changed = []
    for key, h in sorted(old.items()):
        game, s = key.rsplit("__", 1)
        if game not in W.TASKS:
            changed.append(f"{key}: game no longer exists"); continue
        now = W.TASKS[game](s)
        if hashlib.sha256(now.encode()).hexdigest()[:16] != h:
            before = open(os.path.join(path, f"{key}.txt")).read().split("\n")
            d = [l for l in difflib.unified_diff(before, now.split("\n"), lineterm="", n=0)
                 if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
            changed.append(f"{key}: {len(d)} lines changed\n      " + "\n      ".join(d[:4]))
    if changed:
        print(f"{len(changed)} rendered prompt(s) differ from the snapshot:\n")
        for c in changed: print(f"  {c}")
        print("\nAny run compared against the snapshotted trials is now cross-regime.")
        return 1
    print(f"all {len(old)} rendered prompts match the snapshot")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", metavar="DIR")
    ap.add_argument("--diff", metavar="DIR")
    a = ap.parse_args()
    if a.snapshot: return snapshot(a.snapshot)
    if a.diff: return diff(a.diff)

    problems = assert_no_engine_names() + assert_stack_neutral()
    if problems:
        print(f"{len(problems)} violation(s):\n")
        for p in problems: print(f"  {p}")
        return 1
    print(f"ok: {len(W.TASKS)} games x {len(STACKS)} stacks — "
          f"no engine names in game bodies, rules identical across stacks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
