#!/usr/bin/env python3
"""Assertions on the task prompts. Run before any comparison that uses them.

Two task classes are covered: the games in `suites/wholegame_prompts.py` and the scenes in
`suites/scene_prompts.py`. Both are ONE template per task rendered per stack -- `gN_*(stack)`
and `sN_*(stack)` functions over vocabulary dicts, no per-stack copies. Three ways that
structure silently breaks:

  STACK axis  an engine name written into a task body instead of a vocabulary dict. The
              prompt stops being stack-neutral and hands one stack its own words. The
              first bake-off did exactly this with byte-identical prompts and cost a run:
              turn counts reversed after the fix (rust 32->49, ts 50->43).

  TASK axis   a preamble is shared by every task in its class. An edit aimed at one task
              reaches all of them -- correctly where aimed, invisibly everywhere else. A
              mouse-aiming clause written for the 3D arena landed in Pong, Tetris and the
              platformer, and would have contaminated the one experiment whose whole design
              was a single variable (FINDINGS #41).

  RUBRIC axis a scene prompt naming a criterion, a threshold or a tolerance from
              `eval/SCENES.md`. That is teaching to the test: the scene criteria exist to
              discriminate submissions, and a prompt that states one converts the
              measurement into an instruction. Checked by grepping the RENDERED text.

Usage:
    python3 tools/prompt_guard.py                 # all three assertions
    python3 tools/prompt_guard.py --identity      # byte-identical share across stacks
    python3 tools/prompt_guard.py --snapshot DIR  # record rendered prompts
    python3 tools/prompt_guard.py --diff DIR      # diff rendered against a snapshot

Exit 1 on any violation, so it can gate a run. `tools/prompt_guard_control.py` pins the
rubric assertion in both directions.
"""
from __future__ import annotations

import argparse, difflib, hashlib, json, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(EVAL, "suites"))
import scene_prompts as SC  # noqa: E402
import wholegame_prompts as W  # noqa: E402

# The stack tuple has ONE owner: `wholegame_prompts.STACKS`. `scene_prompts` imports
# and re-exports that same object, and every other consumer reads it from one of the
# two. This used to be a restated literal -- equal on the day it was written and free
# to drift after, the drift invisible in this tool's own output because the population
# it prints is derived from the copy (task 194). So this is a REFERENCE, pinned by
# IDENTITY rather than equality: a restated tuple is equal and still a different
# object, and the guard below is what turns that into an import failure instead of a
# clean-looking wrong population.
STACKS = W.STACKS
# An `if`/`raise` and not an `assert`: asserts are stripped under `python -O` and
# `PYTHONOPTIMIZE`, and this file MEASURED disarmed that way -- planted literal,
# `python3` exits 1, `python3 -O` exits 0 with "ok" (task 194, review round 1).
if STACKS is not W.STACKS:
    raise AssertionError(
        "prompt_guard STACKS is not W.STACKS: the stack tuple is owned by "
        "eval/suites/wholegame_prompts.py, so assign W.STACKS here and restate nothing")
SCENES_MD = os.path.join(EVAL, "SCENES.md")

# Engine and library names that belong in a vocabulary dict, never in a task body.
ENGINE_WORDS = ("Bevy", "Godot", "Unity", "three.js", "GDScript", "C#", "AudioStreamPlayer",
                "AudioSource", "AudioPlayer", "Node2D", "Node3D", "cargo", "pnpm")

# Every task, both classes, as `name -> render(stack)`.
ALL_TASKS = {**W.TASKS, **SC.SCENES}

# --------------------------------------------------------------------------- #
# The rubric vocabulary
# --------------------------------------------------------------------------- #
# Two closed lists, checked against the RENDERED scene prompts.
#
# WHY SCENES ONLY, AND WHY THAT IS AN ADDRESS RATHER THAN A CONVENIENCE. These are the
# words `eval/SCENES.md` uses to state a scene criterion. A game prompt says `score`
# because a game has a score, and `at least three kinds of enemy` because that is the
# game's rule; measured over the 16 rendered game prompts this list lands on 4 of the 4
# games with no true positive among the hits, and over the 8 rendered scene prompts it
# lands on nothing. The scene criteria are what a scene prompt must not state, so the
# scene prompts are where the question is asked.
#
# WHY A LIST AND NOT A DERIVED PROPERTY. The obvious property -- every content word of
# SCENES.md's criterion columns -- was built and measured first: 85 words, 31 hits across
# the corpus, ZERO of them a real leak, because `water`, `glass`, `layers`, `seed` and
# `tick` are the scene's own subject and its capture contract. An open class of English
# words is an enumeration in disguise (AGENTS.md, the census-trigger rule). What is closed
# here is the MEASUREMENT vocabulary: the terms below name how a thing will be checked,
# not what is to be rendered.
#
# ANTI-INVENTION GUARD: every RUBRIC_TERM must appear in `eval/SCENES.md` itself, asserted
# at run time, so this list cannot drift into words the authority never used.
RUBRIC_TERMS = (
    "criterion", "criteria", "rubric", "threshold", "tolerance", "graded", "grading",
    # `probe` was on this list and came off it: it is the name of a starter recipe
    # (`just probe SEED`) that every prompt must state, so it hit all 8 rendered scene
    # prompts with no true positive. A term that fires on the functional contract is a
    # term that gets the whole assertion switched off.
    "score", "weighted", "judge", "mutant",
    "monotonic", "monotonically", "seamlessly", "outlier", "per-frame difference",
    "distinct rates", "declared depth", "angular velocity", "frame hash",
    "world-horizontal", "mass balance", "distorted version", "flat tint",
    "ground plane", "piece transforms", "frame distance", "occlude",
    # THE TWO CLAIMS THE SCENES EXIST TO WITHHOLD, in the plain English SCENES.md uses to
    # say they are withheld -- "s1 does not say the layers scroll at rates ordered by
    # depth", "s2 does not say the water surface stays level while the glass tilts". The
    # measurement wordings above (`distinct rates`, `declared depth`, `world-horizontal`)
    # are the criterion table's, and MEASURED 2026-08-25 they catch neither restatement:
    # planted into a rendered prompt, both read 0 hits on all 8. These 2 phrases cost 0
    # false positives on the 8 shipped prompts and on the packed scene statements.
    "ordered by depth", "stays level",
)

# A threshold in a prompt is a bound expression over a quantity. English bound expressions
# are a closed class, which is why this is a list of them rather than a hunt for digits --
# a scene prompt is full of legitimate numbers (tick counts, the JSON examples) and none of
# them is a threshold. SCENES.md's own worked example of the failure is `>= N pieces`.
BOUND_TERMS = (
    "at least", "at most", "no more than", "no fewer than", "no less than",
    "more than", "fewer than", "less than", "up to", "exceeds", "exceed",
    ">=", "<=", "≥", "≤",
)

# Allow the usual English inflections so that a leak cannot walk past on an `-s` or `-ed`.
_INFLECTION = r"(?:s|es|d|ed|ing)?"


def _term_pattern(term: str) -> re.Pattern:
    if term[0].isalpha():
        return re.compile(r"(?<![a-z])" + re.escape(term) + _INFLECTION + r"(?![a-z])")
    return re.compile(re.escape(term))


def _normalised_scenes_md() -> str:
    """SCENES.md with markdown emphasis and line wrapping removed.

    A term is checked for presence here, not in the raw file: `a **distorted** version`
    and `stays world-horizontal while` are wrapped and emphasised in the source, and a
    presence check against the raw bytes would silently drop those two terms from the
    anti-invention guard while still reporting it green.
    """
    text = open(SCENES_MD).read().lower()
    text = re.sub(r"[*`_]", "", text)
    return re.sub(r"\s+", " ", text)


# --------------------------------------------------------------------------- #
# The three assertions
# --------------------------------------------------------------------------- #

def _task_bodies() -> dict[str, str]:
    """Source text of every `gN_*` / `sN_*` function, keyed by name.

    The body ends at the next top-level `def`, constant assignment or `if __name__`,
    whichever comes first -- the two modules end their task functions with different
    sentinels (`TASKS` and `SCENES`), and keying on either one would read the whole tail
    of the other module as part of its last task.
    """
    out: dict[str, str] = {}
    for mod in (W, SC):
        src = open(mod.__file__).read()
        marks = [(m.group(1), m.start()) for m in re.finditer(r"^def ([gs]\d+_\w+)\(", src, re.M)]
        for i, (name, start) in enumerate(marks):
            after = src[start + 1:]
            stop = re.search(r"^(?:def |[A-Za-z_]+ = |if __name__)", after, re.M)
            end = start + 1 + (stop.start() if stop else len(after))
            if i + 1 < len(marks):
                end = min(end, marks[i + 1][1])
            out[name] = src[start:end]
    return out


def assert_no_engine_names() -> list[str]:
    """STACK axis: a task body naming an engine is no longer stack-neutral."""
    bad = []
    for name, body in _task_bodies().items():
        for w in ENGINE_WORDS:
            if w in body:
                bad.append(f"{name}: task body names `{w}` — move it to a vocabulary dict")
    return bad


def assert_stack_neutral() -> list[str]:
    """Rendered prompts must differ ONLY in substituted vocabulary."""
    bad = []
    for task, render in ALL_TASKS.items():
        texts = {s: render(s) for s in STACKS}
        base = texts["rust"].split("\n")
        for s in STACKS[1:]:
            d = [l for l in difflib.unified_diff(base, texts[s].split("\n"), lineterm="", n=0)
                 if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
            # Vocabulary substitution touches a handful of lines. Much more than that means
            # task rules themselves diverge by stack, which is not a fair comparison.
            # Measured on the shipped prompts: games 6-8, scenes 10.
            if len(d) > 14:
                bad.append(f"{task}: rust vs {s} differs on {len(d)} lines — "
                           f"rules, not just vocabulary, vary by stack")
    return bad


def assert_no_rubric_vocabulary(scenes: dict | None = None) -> list[str]:
    """RUBRIC axis: no scene criterion, threshold or tolerance in a rendered scene prompt.

    Greps what the agent would actually receive. Reading the template instead would miss a
    term that arrives through a vocabulary dict, which is the same reason `--diff` reads
    rendered text rather than source.
    """
    md = _normalised_scenes_md()
    invented = [t for t in RUBRIC_TERMS if t not in md]
    bad = [f"RUBRIC_TERMS names `{t}`, which is not in eval/SCENES.md — "
           f"this list is that file's vocabulary, not a new one" for t in invented]

    for name, render in sorted((scenes if scenes is not None else SC.SCENES).items()):
        for stack in STACKS:
            text = render(stack).lower() if callable(render) else render.lower()
            for term in RUBRIC_TERMS + BOUND_TERMS:
                m = _term_pattern(term).search(text)
                if m:
                    line = text[:m.start()].count("\n") + 1
                    kind = "criterion" if term in RUBRIC_TERMS else "threshold"
                    bad.append(f"{name}/{stack} line {line}: {kind} vocabulary `{m.group(0)}` "
                               f"— eval/SCENES.md is for us, not for the prompt")
    return bad


# --------------------------------------------------------------------------- #
# The producer for the byte-identical share
# --------------------------------------------------------------------------- #

def _shared_lines(render) -> tuple[set[int], list[str]]:
    """Indices of the rust rendering's lines that survive unchanged in the other three."""
    texts = {s: render(s).splitlines(keepends=True) for s in STACKS}
    base = texts["rust"]
    common = set(range(len(base)))
    for s in STACKS[1:]:
        eq: set[int] = set()
        for a, _b, n in difflib.SequenceMatcher(None, base, texts[s],
                                                autojunk=False).get_matching_blocks():
            eq.update(range(a, a + n))
        common &= eq
    return common, base


def identity() -> int:
    """How much of each prompt is byte-identical across all four stacks.

    DEFINITION, because a share means nothing without one: the rust rendering is split
    into lines; a line counts as shared when it survives unchanged in the ts, unity AND
    godot renderings (`difflib` matching blocks, intersected). It answers "how much of
    what one agent read did the other three read word for word", and the remainder is
    exactly the vocabulary substitution.

    BOTH UNITS, because they differ by six points and the docs quote one of them. A
    substituted line is a long one -- a whole `RENDER_NOTE` paragraph on one line -- so
    the share by LINES runs well above the share by CHARACTERS. `.agents/skills/add-game/
    SKILL.md`'s figure is the line share; nothing produced it until this flag existed.
    """
    print(f"{'task':16} {'class':6} {'lines':>13} {'share':>7}   "
          f"{'chars':>15} {'share':>7}")
    tl = ts_ = tc = tcs = 0
    for task, render in ALL_TASKS.items():
        klass = "scene" if task in SC.SCENES else "game"
        common, base = _shared_lines(render)
        chars = sum(len(base[i]) for i in common)
        total = sum(len(l) for l in base)
        tl += len(base); ts_ += len(common); tc += total; tcs += chars
        print(f"{task:16} {klass:6} {len(common):6d}/{len(base):<6d} "
              f"{len(common) / len(base):6.1%}   {chars:7d}/{total:<7d} {chars / total:6.1%}")
    print(f"\n{'ALL':16} {'':6} {ts_:6d}/{tl:<6d} {ts_ / tl:6.1%}   "
          f"{tcs:7d}/{tc:<7d} {tcs / tc:6.1%}")
    print(f"population: {len(ALL_TASKS)} tasks x {len(STACKS)} stacks = "
          f"{len(ALL_TASKS) * len(STACKS)} rendered prompts")
    # DEFINED and USED are different numbers and the gap is the interesting one: a dict
    # that appears once in its module's source is defined and referenced by no template.
    for mod, label in ((W, "wholegame_prompts"), (SC, "scene_prompts")):
        src = open(mod.__file__).read()
        dicts = sorted(n for n, v in vars(mod).items()
                       if isinstance(v, dict) and n.isupper() and set(v) == set(STACKS))
        dead = [n for n in dicts if src.count(n) < 2]
        print(f"{label}: {len(dicts)} vocabulary dicts in scope, {len(dicts) - len(dead)} "
              f"referenced by a template ({', '.join(dicts)})"
              + (f" — DEFINED AND UNUSED: {', '.join(dead)}" if dead else ""))
    return 0


# --------------------------------------------------------------------------- #
# Snapshot and diff
# --------------------------------------------------------------------------- #

def _write_atomic(path: str, text: str) -> None:
    """Write through a temporary file in the same directory, then `os.replace`.

    A snapshot is the durable record of what a run was configured to be, and an artifact
    caught mid-write is indistinguishable from one never written (AGENTS.md rule 2). A
    partial `.txt` reads to `--diff` as drift and a truncated `index.json` aborts it
    before it can report any, so neither may exist even for an instant.

    `mkstemp` rather than a name built from the pid: 2 processes get 2 pids, but 2
    overlapping calls inside 1 process get the same name and each would publish over the
    other's temporary file. `mkstemp` creates with `O_EXCL`, so no naming scheme can
    collide. It also creates at 0600, which `os.replace` would then publish - a snapshot
    should be as readable as any other file in the tree, so the mode is set back to what
    a plain `open(..., "w")` here would have produced.
    """
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", suffix=".tmp",
                               dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
        umask = os.umask(0)
        os.umask(umask)
        os.chmod(tmp, 0o666 & ~umask)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _stale_in(path: str, idx: dict) -> list[str]:
    """`.txt` files in a snapshot directory that its index does not name.

    A snapshot written over an older one leaves the `.txt` of any task since removed,
    while `index.json` stops naming it. Nothing reading the index can see that file, and
    a reader opening `<run>/prompts/g5_gone__rust.txt` would believe that prompt was sent.
    """
    wanted = {f"{k}.txt" for k in idx}
    return sorted(n for n in os.listdir(path)
                  if n.endswith(".txt") and n not in wanted)


def snapshot(path: str) -> int:
    os.makedirs(path, exist_ok=True)
    idx = {}
    for task, render in ALL_TASKS.items():
        for s in STACKS:
            t = render(s)
            _write_atomic(os.path.join(path, f"{task}__{s}.txt"), t)
            idx[f"{task}__{s}"] = hashlib.sha256(t.encode()).hexdigest()[:16]
    # index.json LAST, and it is the commit marker: `--diff` refuses a directory without
    # one rather than reporting a snapshot it only partly has.
    _write_atomic(os.path.join(path, "index.json"),
                  json.dumps(idx, indent=2, sort_keys=True))
    print(f"snapshot: {len(idx)} rendered prompts -> {path}")
    # NAMED, NOT DELETED. A run's prompt directory is append-only (#93) and this tool
    # cannot tell a leftover from something a person put there on purpose. Saying so here
    # and turning `--diff` red is what forces the decision instead of making it.
    stale = _stale_in(path, idx)
    if stale:
        print(f"WARNING: {len(stale)} .txt file(s) here are not in the index and were not "
              f"written by this snapshot: {', '.join(stale)}")
        print("  --diff will refuse this directory until they are removed or explained.")
    return 0


def diff(path: str) -> int:
    """TASK axis: what the agents ACTUALLY received vs what renders now.

    Diff the rendered inputs, not the source that renders them. A shared preamble makes
    the source look untouched while every task's prompt has changed.
    """
    idx_p = os.path.join(path, "index.json")
    if not os.path.exists(idx_p):
        print(f"no snapshot at {path} — run --snapshot first"); return 1
    old = json.load(open(idx_p))
    changed = []
    for key, h in sorted(old.items()):
        task, s = key.rsplit("__", 1)
        if task not in ALL_TASKS:
            changed.append(f"{key}: task no longer exists"); continue
        now = ALL_TASKS[task](s)
        if hashlib.sha256(now.encode()).hexdigest()[:16] != h:
            before = open(os.path.join(path, f"{key}.txt")).read().split("\n")
            d = [l for l in difflib.unified_diff(before, now.split("\n"), lineterm="", n=0)
                 if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
            changed.append(f"{key}: {len(d)} lines changed\n      " + "\n      ".join(d[:4]))
    missing = sorted(f"{t}__{s}" for t in ALL_TASKS for s in STACKS
                     if f"{t}__{s}" not in old)
    # A `.txt` the index does not name is invisible to every loop above, and it reads to
    # anyone opening the directory as a prompt that was sent. Refuse the directory.
    stale = _stale_in(path, old)
    if changed or missing or stale:
        if changed:
            print(f"{len(changed)} rendered prompt(s) differ from the snapshot:\n")
            for c in changed: print(f"  {c}")
        if missing:
            print(f"\n{len(missing)} rendered prompt(s) exist now and are not in the "
                  f"snapshot: {', '.join(missing)}")
        if stale:
            print(f"\n{len(stale)} file(s) in the snapshot are named by no index entry, "
                  f"so nothing reading the index can see them, and a reader opening one "
                  f"would take it for a prompt that was sent: {', '.join(stale)}")
        print("\nAny run compared against the snapshotted trials is now cross-regime.")
        print(f"If the change is intended, re-record it in the SAME commit:\n"
              f"  python3 eval/tools/prompt_guard.py --snapshot {path}")
        return 1
    print(f"all {len(old)} rendered prompts match the snapshot")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", metavar="DIR")
    ap.add_argument("--diff", metavar="DIR")
    ap.add_argument("--identity", action="store_true",
                    help="measure the byte-identical share across stacks")
    a = ap.parse_args()
    if a.snapshot: return snapshot(a.snapshot)
    if a.diff: return diff(a.diff)
    if a.identity: return identity()

    problems = (assert_no_engine_names() + assert_stack_neutral()
                + assert_no_rubric_vocabulary())
    if problems:
        print(f"{len(problems)} violation(s):\n")
        for p in problems: print(f"  {p}")
        return 1
    print(f"ok: {len(W.TASKS)} games + {len(SC.SCENES)} scenes x {len(STACKS)} stacks — "
          f"no engine names in task bodies, rules identical across stacks, "
          f"no eval/SCENES.md criterion or threshold vocabulary in a scene prompt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
