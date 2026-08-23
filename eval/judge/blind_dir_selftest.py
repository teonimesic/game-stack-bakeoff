#!/usr/bin/env python3
"""Does `blind_language` blind the DIRECTORY names a pack carries, and only there?

WHAT THIS EXISTS FOR. `blind_extensions` closed the suffix half of the pack leak
(`blind_ext_selftest.py`). The segment half survived it: measured over the 8 stored
`architecture` packs after `neutralise` AND after `blind_extensions`, 1,561 arm-naming
tokens remained. Partitioned by channel, that total says two different things:

    channel        a real path segment    the same word doing something else
    CHANGED.txt                   182                                       0
    code content                  149                                   1,230

`CHANGED.txt` is pure signal because the harness writes it - a whole `git diff --stat`
listing the real authored tree, handed to a judge whose every file was renamed to
`bucket/NN.src`. It is repaired by mapping every row through the pack's own
origin -> label manifest, so no vocabulary is involved and nothing can be missed.

The code half is 89% collision and is deliberately NOT repaired. The census that
declined it is PART 6 below, so the decision has a producer rather than a remembered
table; the reasoning is in `DECISIONS.md` and `tasks/103`.

SIX PARTS, and none is redundant:

  1. POSITIVE   - a blind field's CHANGED.txt names no arm-naming directory segment,
                  and every row it does carry names a file that is on disk in that
                  pack. A row citing a file the judge cannot open is not a repair.
  2. MUTANT     - with the mapping neutered, check 1 must go red (rule 1).
  3. VARIANT    - the same field built with `blind_language=False` must carry a
                  CHANGED.txt byte-identical to the old behaviour, `neutralise` and
                  nothing else. `idiomatic` reads the real tree on purpose. A mutant
                  cannot ask this; only a variant can (rule 15).
  4. SHAPES     - `--stat` rows the mapping has to survive: a rename row spelled
                  `a/{b => c}`, a `Bin 0 -> N bytes` churn column, the summary tail,
                  and a path that is a PREFIX of a manifest origin but not equal to it.
  5. FAIL-CLOSED - a manifest whose origins no longer spell the diff's paths must
                  REFUSE, not write an empty CHANGED.txt that reads as a submission
                  which changed nothing (rule 7, rule 12).
  6. CODE HALF   - the census behind the decision NOT to rewrite code content, and
                  the trigger that would re-open it. `--runs-root` only.

THE DETECTOR IS DERIVED FROM THE FOUR STARTERS, not from the repair. `blind_changed_txt`
uses no directory vocabulary at all, so a starter-derived one shares none of its
assumptions - which is the property a control needs and usually does not have (#37).

Run:  python3 judge/blind_dir_selftest.py
      python3 judge/blind_dir_selftest.py --runs-root <main checkout>/eval/runs
          ... additionally re-sweeps every stored submission that has both a
          `diff.stat` and a manifest, and reports the surviving count PER SEGMENT;
          and runs the code-half census of part 6.
          `eval/runs/**` is gitignored, so a worktree's copy is empty and the sweep
          would confidently report zero.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import anonymise  # noqa: E402
import field  # noqa: E402

FAILS: list[str] = []


def expect(name: str, cond: bool, detail: str) -> None:
    if not cond:
        FAILS.append(f"{name}: {detail}")


#: A worktree forked before the repair is a real state this file will meet, and a bare
#: AttributeError is a poor red. Check 1 still measures the unrepaired state there.
HAS_MAP = hasattr(field, "blind_changed_txt")
if not HAS_MAP:
    FAILS.append("pre-change: `field.blind_changed_txt` does not exist in this "
                 "checkout, so checks 2-5 measured nothing. Check 1 is the "
                 "measurement of the unrepaired state.")


# ---------------------------------------------------------------------------
# THE DETECTOR. Arm-exclusive directory segments, read from the four starters.
# ---------------------------------------------------------------------------
STARTERS = Path(__file__).resolve().parents[1] / "starters"
ARMS = ("godot", "rust", "ts", "unity")
#: A path segment is bounded by `/` or by a character no path segment contains.
_WORD = r"[A-Za-z0-9_.\-]"


def starter_dirs_by_arm() -> dict[str, set[str]]:
    """directory segment -> every arm whose starter tree contains it.

    READ FROM GIT, NOT FROM THE DISK, and the difference is not cosmetic: an `rglob`
    over the same path returns 21 segments in a working checkout and 19 in a fresh
    worktree, because the checkout has run Unity and carries untracked `Logs/`,
    `Generated/` and `Analyzers/`. A detector whose vocabulary depends on whether
    somebody built the product is not a detector - and the failure is not safely
    one-directional either, since an untracked directory appearing under a SECOND arm
    would move a segment from exclusive to shared and quietly stop detecting it.
    The starters are the product; `git ls-files` is what the product is.

    Both vocabularies in this file come from here rather than from two calls, so
    "exclusive" and "shared" cannot be computed against different trees.
    """
    r = subprocess.run(["git", "-C", str(STARTERS), "ls-files", "-z"],
                       capture_output=True, text=True, check=False)
    if r.returncode != 0:
        FAILS.append(f"detector-vocabulary: `git ls-files` under {STARTERS} exited "
                     f"{r.returncode}, so the vocabulary is UNMEASURED, not empty: "
                     f"{r.stderr[-200:]}")
        return {}
    where: dict[str, set[str]] = collections.defaultdict(set)
    for rel in r.stdout.split("\0"):
        if not rel:
            continue
        parts = Path(rel).parts
        if len(parts) < 2 or parts[0] not in ARMS:
            continue
        arm, rest = parts[0], parts[1:-1]        # [-1] is the filename
        if any(p in anonymise.SKIP_DIRS for p in rest):
            continue
        for p in rest:
            where[p].add(arm)
    return where


def arm_exclusive_dirs() -> dict[str, str]:
    """segment -> the one arm whose starter tree contains it."""
    return {d: next(iter(a)) for d, a in starter_dirs_by_arm().items()
            if len(a) == 1}


def seg_re(d: str) -> re.Pattern[str]:
    return re.compile(rf"(?:(?<=/)|(?<!{_WORD})){re.escape(d)}(?:(?=/)|(?!{_WORD}))")


def dir_hits(text: str, vocab: dict[str, str]) -> collections.Counter:
    """Whole-segment, path-adjacent occurrences. Case-SENSITIVE, deliberately.

    `Sim/`, `View/` and `Tests/` are Unity directories and `sim/`, `view/` and
    `tests/` are this pack's OWN bucket labels, which the judge is told to cite. A
    case-insensitive detector reports the pack's labels as a leak and would push the
    next reader into redacting them.
    """
    out: collections.Counter = collections.Counter()
    for d in vocab:
        for m in seg_re(d).finditer(text):
            s, e = m.span()
            if text[max(0, s - 1):s] == "/" or text[e:e + 1] == "/":
                out[d] += 1
    return out


VOCAB = arm_exclusive_dirs() if STARTERS.is_dir() else {}
expect("detector-is-not-vacuous", len(VOCAB) >= 10,
       f"only {len(VOCAB)} arm-exclusive directory segment(s) under {STARTERS} - the "
       f"detector is reading an empty or wrong tree (rule 12), not a clean one")
expect("detector-does-not-claim-the-pack-labels",
       not ({"sim", "view", "tests", "other"} & set(VOCAB)),
       f"the starter-derived detector claims a pack bucket label: "
       f"{sorted({'sim', 'view', 'tests', 'other'} & set(VOCAB))}. Blinding those "
       f"would redact the paths the judge's brief tells it to cite.")
print(f"0 detector               arm_exclusive_dirs={len(VOCAB)} "
      f"eg {sorted(VOCAB)[:6]}")


# ---------------------------------------------------------------------------
# A run in the shape `field.build_pack` reads. Each `diff.stat` carries rows the
# manifest CAN map, rows it cannot, and the summary tail - the real proportions
# from `wg-g4c-2026-08-21T02-26-46`, where 196 of 424 rows mapped.
# ---------------------------------------------------------------------------
ORIGINS = {
    "rust":  ["crates/sim/src/world.rs", "crates/game/src/main.rs"],
    "ts":    ["src/sim/world.ts", "public/render/view.ts"],
    "unity": ["Assets/Sim/Grid.cs", "Assets/View/GameView.cs"],
    "godot": ["sim/world.gd", "scenes/main.gd"],
}
#: Rows naming files that are NOT in the pack. Every one is a real shape from the
#: stored corpus, and Unity's `.meta` sidecars are why the dropped-row COUNT is not
#: reported: it runs 53 against 15 between arms.
UNMAPPED = {
    "rust":  [" Cargo.lock | 12 +", " .config/nextest.toml | 4 +"],
    "ts":    [" public/audio/attack.wav | Bin 0 -> 7982 bytes"],
    "unity": [" Assets/Audio.meta | 8 +", " Packages/manifest.json | 1 +",
              " ProjectSettings/GraphicsSettings.asset | 2 +",
              " Assets/View/{Flat.shader.meta => Glow.shader.meta} | 2 +-"],
    "godot": [" project.godot | 9 +", " res/audio/jump.ogg | Bin 0 -> 1 bytes"],
}
STACK_EXT = {"rust": ".rs", "ts": ".ts", "unity": ".cs", "godot": ".gd"}


def stored_run(root: Path, game: str = "g9_probe", *, break_origins: bool = False) -> Path:
    run = root / "run"
    for stack in ARMS:
        for trial in ("t0", "t1"):
            sub = run / "artifacts" / f"{game}__{stack}__{trial}"
            code = sub / "eval" / "judge_pack" / "code"
            (code / "sim").mkdir(parents=True)
            manifest, rows = [], []
            for i, origin in enumerate(ORIGINS[stack], start=1):
                label = f"sim/{i:02d}{STACK_EXT[stack]}"
                body = f"// module {i}\n"
                (code / label).write_text(body)
                manifest.append({
                    "label": label,
                    # The break is ONE character in the spelling of the origin, which
                    # is exactly how this fails in the wild: the manifest still parses,
                    # still maps, and maps nothing.
                    "origin": ("x/" + origin) if break_origins else origin,
                    "chars": str(len(body))})
                rows.append(f" {origin:<48} | {40 + i} ++--")
            rows += UNMAPPED[stack]
            rows.append(f" {len(rows)} files changed, 512 insertions(+), 7 deletions(-)")
            (sub / "diff.stat").write_text("\n".join(rows) + "\n")
            (sub / "eval" / "report.json").write_text(json.dumps({
                "game": game,
                "pack": {"built": True, "files_in_pack": len(manifest),
                         "files_dropped_for_length": 0, "frames": 0,
                         "manifest": manifest}}))
    return run


def changed_texts(dest: Path) -> dict[str, str]:
    return {str(p.parent.relative_to(dest)): p.read_text()
            for p in sorted(dest.rglob("CHANGED.txt"))}


with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    run = stored_run(root)

    # -----------------------------------------------------------------------
    # NON-VACUITY FIRST. The fixture must carry the defect, or every green below
    # is a reading of an empty set.
    # -----------------------------------------------------------------------
    raw_hits: collections.Counter = collections.Counter()
    for sub in sorted((run / "artifacts").iterdir()):
        raw_hits += dir_hits(
            field.blind_extensions(
                anonymise.neutralise((sub / "diff.stat").read_text())), VOCAB)
    expect("fixture-carries-the-defect", sum(raw_hits.values()) >= 8,
           f"the fixture's diff.stat files carry {sum(raw_hits.values())} arm-naming "
           f"segment(s) after neutralise+blind_extensions; there is nothing to repair "
           f"and check 1 below would pass on an empty set")
    print(f"  fixture (unrepaired)   {sum(raw_hits.values())} segment(s): "
          f"{dict(raw_hits.most_common(6))}")

    # -----------------------------------------------------------------------
    # 1. POSITIVE.
    # -----------------------------------------------------------------------
    dest = root / "blind"
    field.build_pack(run, "g9_probe", dest, order_seed=7,
                     sees="code", blind_language=True)
    blind = changed_texts(dest)
    found: collections.Counter = collections.Counter()
    for t in blind.values():
        found += dir_hits(t, VOCAB)
    expect("blind-changed-txt-has-no-arm-directory", not found,
           f"{sum(found.values())} segment(s) survive: {dict(found)}")
    expect("blind-changed-txt-count", len(blind) == 8,
           f"{len(blind)} CHANGED.txt files, expected 8 - the checks are vacuous "
           f"without them")

    # Every row must name a file the judge can open. A citation to something absent is
    # the failure the judge's brief already complains about (11 of 16 claims in one
    # real field cited a reconstructed name).
    row = re.compile(r"^\s*(\S+)\s*\|")
    bad: list[str] = []
    rows_seen = 0
    for label, text in blind.items():
        on_disk = {str(p.relative_to(dest / label))
                   for p in (dest / label).rglob("*") if p.is_file()}
        for line in text.splitlines():
            m = row.match(line)
            if not m:
                continue
            rows_seen += 1
            if m.group(1) not in on_disk:
                bad.append(f"{label}:{m.group(1)}")
    expect("blind-changed-txt-rows-are-openable", not bad,
           f"{len(bad)} row(s) cite a file that is not in that pack: {bad[:5]}")
    expect("blind-changed-txt-keeps-the-mapped-rows", rows_seen == 16,
           f"{rows_seen} rows survived, expected 16 (2 mappable per submission x 8). "
           f"Fewer means the mapping is dropping rows it can resolve; more means it "
           f"is keeping rows it cannot.")
    print(f"1 blind field            changed_txt={len(blind)} rows={rows_seen} "
          f"leaking_segments={sum(found.values())} unopenable_rows={len(bad)}")

    # -----------------------------------------------------------------------
    # 2. MUTANT. Neuter the mapping; check 1 must go red.
    # -----------------------------------------------------------------------
    mfound: collections.Counter = collections.Counter()
    if HAS_MAP:
        real = field.blind_changed_txt
        field.blind_changed_txt = (                     # type: ignore[assignment]
            lambda text, origins: (text, 1, 0))
        try:
            mdest = root / "mutant"
            field.build_pack(run, "g9_probe", mdest, order_seed=7,
                             sees="code", blind_language=True)
            for t in changed_texts(mdest).values():
                mfound += dir_hits(t, VOCAB)
        finally:
            field.blind_changed_txt = real              # type: ignore[assignment]
        expect("mutant-turns-check-red", bool(mfound),
               "with `blind_changed_txt` neutered the blind CHANGED.txt still read "
               "clean, so check 1 cannot fail and measures nothing")
    print(f"2 mutant (no mapping)    leaking_segments={sum(mfound.values())} "
          f"{dict(mfound.most_common(5))}")

    # -----------------------------------------------------------------------
    # 3. VARIANT. The non-blind path must be what it always was: `neutralise` over
    #    the raw `--stat`, under the old header. Compared against the source text
    #    put through `neutralise` directly, never against a stored golden, so the
    #    assertion cannot drift with the fixture.
    # -----------------------------------------------------------------------
    ndest = root / "plain"
    field.build_pack(run, "g9_probe", ndest, order_seed=7,
                     sees="code", blind_language=False)
    plain = changed_texts(ndest)
    wrong: list[str] = []
    for label, text in plain.items():
        sub_name = json.loads(
            (ndest.parent / "plain.MAPPING.json").read_text())["mapping"][label]
        raw = (run / "artifacts" / sub_name / "diff.stat").read_text()
        want = ("Files this submission's author changed, and by how much.\n"
                "Everything else is template code they inherited.\n\n"
                + anonymise.neutralise(raw))
        if text != want:
            wrong.append(label)
    expect("non-blind-changed-txt-byte-identical", not wrong,
           f"a non-blind CHANGED.txt differs from `neutralise` alone in {wrong} - the "
           f"repair has reached the aspect that must NOT be blinded")
    still: collections.Counter = collections.Counter()
    for t in plain.values():
        still += dir_hits(t, VOCAB)
    expect("non-blind-changed-txt-keeps-directories", sum(still.values()) >= 8,
           f"only {sum(still.values())} directory segment(s) remain in the non-blind "
           f"CHANGED.txt - the repair has reached `idiomatic`")
    print(f"3 non-blind field        changed_txt={len(plain)} "
          f"byte_identical={not wrong} directories_kept={sum(still.values())}")

    # -----------------------------------------------------------------------
    # 5. FAIL-CLOSED. Break one character in every manifest origin. The mapping
    #    still runs, still parses and maps nothing; that must REFUSE.
    # -----------------------------------------------------------------------
    if HAS_MAP:
        broken = stored_run(root / "broken-root", break_origins=True)
        try:
            field.build_pack(broken, "g9_probe", root / "broken-pack", order_seed=7,
                             sees="code", blind_language=True)
            expect("zero-mapped-refuses", False,
                   "a manifest whose origins match no diff row produced a pack "
                   "instead of a refusal - the blind CHANGED.txt would be empty and "
                   "read as a submission that changed nothing")
        except RuntimeError as e:
            expect("zero-mapped-refuses-with-a-usable-reason",
                   "CHANGED.txt mapped 0" in str(e),
                   f"refused, but for another reason: {str(e)[:200]}")
            print(f"5 fail-closed            refused: {str(e)[:74]}...")


# ---------------------------------------------------------------------------
# 4. SHAPES the mapping must handle, asserted on the function directly.
# ---------------------------------------------------------------------------
if HAS_MAP:
    O = {"Assets/Sim/Grid.cs": "sim/01.src", "src/sim/world.ts": "sim/02.src",
         "Assets/View/Glow.shader.meta": "view/01.src"}
    SHAPES = [
        ("plain row", " Assets/Sim/Grid.cs | 42 ++--", 1, 0),
        ("rename row, new name in the manifest",
         " Assets/View/{Flat.shader.meta => Glow.shader.meta} | 2 +-", 1, 0),
        ("binary churn column",
         " public/audio/attack.wav | Bin 0 -> 7982 bytes", 0, 1),
        ("summary tail carries no pipe and is not a row",
         " 37 files changed, 5502 insertions(+), 517 deletions(-)", 0, 0),
        ("a PREFIX of an origin is not that origin",
         " Assets/Sim/Grid.csx | 3 +", 0, 1),
        ("an origin that is a prefix of the row is not a match",
         " Assets/Sim/Grid.cs.orig | 3 +", 0, 1),
        ("blank line", "", 0, 0),
    ]
    for why, text, want_kept, want_dropped in SHAPES:
        body, kept, dropped = field.blind_changed_txt(text, O)
        expect(f"shape/{why}", (kept, dropped) == (want_kept, want_dropped),
               f"kept={kept} dropped={dropped}, expected {want_kept}/{want_dropped}; "
               f"body={body!r}")
    # And the churn column must survive intact - it is the whole point of the file.
    body, _, _ = field.blind_changed_txt(" Assets/Sim/Grid.cs | 42 ++--", O)
    expect("shape/churn-survives", body.strip().endswith("| 42 ++--"),
           f"the churn column did not survive: {body!r}")
    print(f"4 shapes                 {len(SHAPES)} + churn column")


# ---------------------------------------------------------------------------
# 6. RE-SWEEP. Per segment, not one total: the ticket's single figure of 1,561
#    hid that one channel was 100% signal and the other 89% collision.
# ---------------------------------------------------------------------------
ap = argparse.ArgumentParser(add_help=False)
ap.add_argument("--runs-root", type=Path)
args, _ = ap.parse_known_args()
if args.runs_root and HAS_MAP:
    before: collections.Counter = collections.Counter()
    after: collections.Counter = collections.Counter()
    subs = mapped_rows = dropped_rows = 0
    # `*/artifacts/*` misses the runs that nest an arm one level deeper, which is how
    # the extension sweep found 68 of 84 packs. Search at any depth (rule 12).
    for stat in sorted(args.runs_root.glob("**/diff.stat")):
        sub = stat.parent
        origins = field._pack_origins(sub)
        if not origins:
            continue
        subs += 1
        raw = anonymise.neutralise(stat.read_text(errors="ignore"))
        before += dir_hits(field.blind_extensions(raw), VOCAB)
        labels = {o: str(Path(lbl).with_suffix(field.NEUTRAL_EXT))
                  for o, lbl in origins.items()}
        body, kept, dropped = field.blind_changed_txt(raw, labels)
        mapped_rows += kept
        dropped_rows += dropped
        after += dir_hits(field.blind_extensions(body), VOCAB)
    print(f"\nre-sweep of stored CHANGED.txt sources "
          f"({subs} submissions with a diff.stat AND a manifest under {args.runs_root})")
    print(f"  rows mapped to a label   : {mapped_rows}")
    print(f"  rows omitted (not packed): {dropped_rows}")
    print(f"  {'segment':22} {'before':>8} {'after':>8}")
    for seg in sorted(set(before) | set(after), key=lambda s: -before[s]):
        print(f"  {seg:22} {before[seg]:>8} {after[seg]:>8}")
    print(f"  {'TOTAL':22} {sum(before.values()):>8} {sum(after.values()):>8}")
    expect("sweep-is-not-vacuous", subs > 0,
           f"no submission under {args.runs_root} has both a diff.stat and a "
           f"manifest - the sweep measured nothing")
    expect("sweep-has-something-to-repair", sum(before.values()) > 0,
           f"the pre-repair sweep found 0 segments in {subs} submissions, so the "
           f"post-repair figure is a reading of an empty set, not a repair")
    expect("sweep-blind-path-is-clean", not after,
           f"{sum(after.values())} segment(s) survive the blind path: {dict(after)}")

# ---------------------------------------------------------------------------
# 6. THE CODE HALF. Why no rewrite of code content has landed, as a census rather
#    than as a remembered table.
#
# THE STATISTIC IS NOT THE ONE THE DECISION WAS FIRST WRITTEN AGAINST, and that is
# the result. `DECISIONS.md` declined the arm-exclusive vocabulary because its
# "redaction density is stack-correlated by construction - godot 0, rust 43, unity
# 228, ts 265", and set the reversal condition to a rewrite whose per-arm density is
# UNIFORM. Per-arm density is an aggregate; a judge never sees it. What a judge sees
# is eight packs and how redacted each one looks, so the property that matters is
# whether a THRESHOLD ON ONE PACK'S COUNT names an arm - measured per field, and
# strictly, so a tie can never count as a separation.
#
# Measured over the 9 independent stored fields, that reordered the candidates:
# a vocabulary-free rewrite gets per-arm density to 2.1x and leaves no arm at zero,
# satisfying the old trigger outright, and isolates an arm in 9 of 9 fields against
# the declined candidate's 6 of 9. Making the aggregate uniform did not close the
# channel; it moved the leak from one arm's zero to another arm's extreme. Chance is
# 7.1% per arm-field pair and NOTHING MEASURED GETS NEAR IT.
# ---------------------------------------------------------------------------
BUCKETS = {"sim", "view", "tests", "other"}

#: The published per-arm table (`DECISIONS.md`, `tasks/103`), pinned to the corpus.
#: It EXCLUDES `bin`, and the exclusion is a real finding rather than an oversight:
#: `bin` is the only arm-exclusive segment that fires in all four arms, and it does
#: so through `#!/usr/bin/env`, which is a shebang and not the Rust starter's
#: `src/bin/`. Including it turns 536 into 562 and Godot's 0 into 9 - a redaction
#: that removes nothing. The CHANGED.txt detector above keeps `bin`, correctly:
#: a `--stat` row IS a path, so `src/bin/probe.rs` there is a true positive.
PUBLISHED_CODE_HALF = {"godot": 0, "rust": 43, "ts": 265, "unity": 228}

#: A path-shaped token: two or more segments joined by `/`, bounded by characters no
#: path contains. The last segment is the filename and is not a directory.
_PATHISH = re.compile(r"(?<![A-Za-z0-9_./\-])(?:\.{1,2}/)?"
                      r"(?P<body>[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)+)"
                      r"(?![A-Za-z0-9_.\-])")


def path_components(text: str) -> collections.Counter:
    out: collections.Counter = collections.Counter()
    for m in _PATHISH.finditer(text):
        for s in m.group("body").split("/")[:-1]:
            if s not in ("", ".", ".."):
                out[s] += 1
    return out


def all_starter_dirs() -> dict[str, str]:
    """Every starter directory segment, shared ones included, minus bucket labels."""
    return {d: "shared" for d in starter_dirs_by_arm() if d not in BUCKETS}


def isolated_arms(counts: dict[str, list[int]]) -> list[str]:
    """Arms a single STRICT threshold on one pack's count separates from the rest."""
    out = []
    for a in ARMS:
        other = [v for b in ARMS if b != a for v in counts[b]]
        if not counts[a] or not other:
            continue
        if max(counts[a]) < min(other) or min(counts[a]) > max(other):
            out.append(a)
    return out


def code_half_census(runs_root: Path) -> None:
    excl = {k: v for k, v in VOCAB.items() if k != "bin"}
    cands = {
        "C1' arm-exclusive vocabulary (the declined one)":
            lambda t: dir_hits(t, excl),
        "C2  every starter directory, shared included":
            lambda t: dir_hits(t, all_starter_dirs()),
        "C3  vocabulary-free: every path component":
            path_components,
        "C4  C3 minus the four bucket labels":
            lambda t: collections.Counter({k: v for k, v in
                                           path_components(t).items()
                                           if k not in BUCKETS}),
    }

    # Assemble the stored fields. A field is one (run, game): 4 arms x 2 trials.
    fields: dict[tuple[str, str], dict[tuple[str, str], str]] = \
        collections.defaultdict(dict)
    blobs: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    per_arm_text: dict[str, list[str]] = collections.defaultdict(list)
    for code in sorted(runs_root.glob("**/judge_pack/code")):
        sub = code.parents[2]
        parts = sub.name.split("__")
        if len(parts) != 3 or parts[1] not in ARMS:
            continue
        game, arm, trial = parts
        raw = []
        for p in sorted(code.rglob("*")):
            if p.is_file():
                raw.append(p.read_text(errors="ignore"))
                blobs[(str(sub.parent.parent), game)].add(
                    hashlib.sha256(p.read_bytes()).hexdigest())
        text = field.blind_extensions(anonymise.neutralise("\n".join(raw)))
        fields[(str(sub.parent.parent), game)][(arm, trial)] = text
        per_arm_text[arm].append(text)

    complete = {k: v for k, v in fields.items()
                if len(v) == 8 and {a for a, _ in v} == set(ARMS)}

    # RULE 9. Two fields that are re-packs of the same submissions are one subject,
    # and pooling them would report the instrument twice. Decided on SHARED CONTENT,
    # never on a run name: `wg-g4c-capgate/uncapped` shares 176 of 199 pack file
    # blobs with `wg-g4c-2026-08-21T02-26-46` under different labels, so no digest
    # of the pack catches it and no list of names would survive the next re-pack.
    indep: dict[tuple[str, str], dict] = {}
    collapsed: list[tuple[str, str]] = []
    for k in sorted(complete):
        dup = next((j for j in indep
                    if len(blobs[k] & blobs[j]) / max(1, len(blobs[k] | blobs[j]))
                    >= 0.5), None)
        if dup:
            collapsed.append((f"{Path(k[0]).name}/{k[1]}",
                              f"{Path(dup[0]).name}/{dup[1]}"))
        else:
            indep[k] = complete[k]

    n_trees = sum(len(v) for v in per_arm_text.values())
    print(f"\ncode-half census ({n_trees} stored judge_pack/code trees "
          f"under {runs_root})")
    print(f"  complete 8-pack fields: {len(complete)}; independent: {len(indep)}")
    for a, b in collapsed:
        print(f"    collapsed {a} into {b} (>=50% shared pack blobs)")

    expect("code-half-population", len(indep) >= 5,
           f"only {len(indep)} independent 8-pack field(s) under {runs_root}; the "
           f"per-field statistic below is a reading of an almost-empty set, and a "
           f"wrong --runs-root looks exactly like this (rule 12)")

    # The published table, pinned. This is the check that CAN fail, and it did:
    # built with the shipped vocabulary it reads 9/50/265/238, because `bin` is in it.
    got = {a: sum(sum(dir_hits(t, excl).values()) for t in per_arm_text[a])
           for a in ARMS}
    expect("code-half-published-table-reproduces", got == PUBLISHED_CODE_HALF,
           f"the per-arm code-content table is {got}, published as "
           f"{PUBLISHED_CODE_HALF}. One of the two is now wrong; do not quote either "
           f"until you know which (rule 5)")

    # And the `bin` exclusion, pinned to its reason rather than to a name.
    bin_all = sum(sum(dir_hits(t, {"bin": "rust"}).values())
                  for ts in per_arm_text.values() for t in ts)
    bin_shebang = sum(
        sum(1 for m in seg_re("bin").finditer(t)
            if t[max(0, s := t.rfind("\n", 0, m.start()) + 1):s + 2] == "#!")
        for ts in per_arm_text.values() for t in ts)
    bin_arms = sum(1 for a in ARMS
                   if any(dir_hits(t, {"bin": "rust"}) for t in per_arm_text[a]))
    expect("code-half-bin-is-excluded-for-a-measured-reason",
           bin_arms >= 3 and bin_shebang * 2 > bin_all,
           f"`bin` was excluded from the published table because it fires in every "
           f"arm through `#!/usr/bin/env`; it now fires in {bin_arms} arm(s) with "
           f"{bin_shebang} of {bin_all} hits on a shebang line. If that is no longer "
           f"true the exclusion has to be re-argued, not inherited")
    print(f"  `bin`: {bin_all} hits in {bin_arms} arms, {bin_shebang} of them on a "
          f"`#!` line -> excluded from the table above")

    print(f"\n  {'candidate':48}{'godot':>7}{'rust':>7}{'ts':>7}{'unity':>7}"
          f"{'ratio':>8}{'zero-arm':>10}{'isolates':>10}")
    reopen = []
    for name, fn in cands.items():
        tot = {a: sum(sum(fn(t).values()) for t in per_arm_text[a]) for a in ARMS}
        chars = {a: sum(len(t) for t in per_arm_text[a]) for a in ARMS}
        dens = [tot[a] / chars[a] for a in ARMS if chars[a]]
        ratio = (f"{max(dens) / min(dens):.1f}x" if min(dens) else "inf")
        iso_fields = zero_fields = 0
        for packs in indep.values():
            c = {a: [sum(fn(t).values()) for (b, _), t in packs.items() if b == a]
                 for a in ARMS}
            iso_fields += bool(isolated_arms(c))
            zero = [a for a in ARMS if max(c[a]) == 0]
            rest = [v for a in ARMS if a not in zero for v in c[a]]
            zero_fields += bool(zero) and bool(rest) and min(rest) > 0
        print(f"  {name:48}" + "".join(f"{tot[a]:>7}" for a in ARMS)
              + f"{ratio:>8}{f'{zero_fields}/{len(indep)}':>10}"
              + f"{f'{iso_fields}/{len(indep)}':>10}")
        if iso_fields * 3 <= len(indep):
            reopen.append(f"{name} isolates an arm in only {iso_fields} of "
                          f"{len(indep)} fields")
    print(f"  chance an arm is strictly isolated = 2/C(8,2) = {2 / 28:.1%} per "
          f"arm-field pair")

    # A trigger that fires on NEW INFORMATION, never on drift: if some candidate
    # here stops partitioning the field, the decision rests on a number that moved.
    if reopen:
        FAILS.append("code-half-decision-may-be-stale: " + "; ".join(reopen)
                     + ". `DECISIONS.md` declines the code-half rewrite because "
                       "every candidate hands the judge the arm partition. One no "
                       "longer does - re-open the decision rather than silencing "
                       "this")
    print("  REVERSAL TRIGGER: "
          + ("MET - see the failure below" if reopen else
             "not met; every candidate still partitions the field"))


if args.runs_root:
    code_half_census(args.runs_root)

if FAILS:
    print("\nFAIL")
    for f in FAILS:
        print(f"  - {f}")
    raise SystemExit(1)
print("\nOK")
