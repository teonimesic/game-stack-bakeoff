#!/usr/bin/env python3
"""Run the instruction-count experiment, and analyse what it produced.

`eval/instrfollow/DESIGN.md` is the design and this is the apparatus. If the two
disagree the design wins and this file is the bug.

THE MANIPULATION
----------------
One base task, held byte-identical everywhere. The only thing that moves between arms is
how many pool instructions are attached to it:

    k1 k2 k4 k8 k16     k instructions, sampled from the pool of 16
    k1pad               ONE instruction, in a prompt padded with non-normative prose to
                        the token length of a k16 prompt

`k1pad` is the arm that decides what the experiment is about. Instruction count and
prompt LENGTH rise together, and length alone is known to degrade behaviour
(arXiv:2402.14848, Chroma's context-rot measurements). Without `k1pad` a decline from k1
to k16 is a two-variable comparison and rule 8 forbids reading it as a count effect.
The padding is drawn from the project's own always-loaded docs and filtered through
`instruction_census.classify` so that every padded sentence is one the census scores as
NOT normative -- the padding adds tokens and no instructions, which is the whole point.

WHAT IS ASSIGNED, AND HOW
-------------------------
Which instructions a trial gets is drawn WITHOUT replacement, and the arms are built by
cycling a reshuffled pool so that every instruction appears a near-equal number of times
in every arm. At n=12 per arm, leaving that to chance would let an arm miss an
instruction entirely and turn a content difference into a fake count effect. Order
within the block is shuffled independently and recorded, because order is a separate
measured variable (arXiv:2402.08939) and this design balances it rather than testing it.

THE ESTIMAND
------------
Per (trial, instruction) binary compliance. The primary comparison is WITHIN
instruction: the same instruction at k=1 against itself at k=16. Instruction content is
then held constant by construction, which is the only way to stop count and content
moving together -- the ticket's third pre-registered outcome, and the thing that would
otherwise make the result uninterpretable.

    python3 eval/instrfollow/run.py plan --n 12
    python3 eval/instrfollow/run.py pilot --n 1
    python3 eval/instrfollow/run.py build --n 12 --run-dir eval/instrfollow/runs/NAME
    python3 eval/instrfollow/run.py analyse --run-dir eval/instrfollow/runs/NAME
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "eval" / "tools"))

import pool as poolmod                                          # noqa: E402
import instruction_census as census                             # noqa: E402

MODEL = "sonnet"
MAX_TURNS = 40
TIMEOUT_S = 600
ARMS = ["k1", "k2", "k4", "k8", "k16", "k1pad"]
ARM_K = {"k1": 1, "k2": 2, "k4": 4, "k8": 8, "k16": 16, "k1pad": 1}

# TRIALS PER ARM ARE NOT EQUAL, AND MUST NOT BE.
# A trial yields k observations, so equal trials per arm means wildly unequal
# observations per instruction: at n=12 everywhere, k16 gives every instruction 12
# observations and k1 gives four instructions NONE. `plan` caught exactly that and
# exits non-zero on it. These sizes give every instruction at least two observations in
# every arm, which is the minimum for the paired within-instruction comparison to have a
# row for it at all.
ARM_N = {"k1": 32, "k2": 16, "k4": 8, "k8": 8, "k16": 8, "k1pad": 32}


# --------------------------------------------------------------------------- #
# Padding for the length control
# --------------------------------------------------------------------------- #

# A sentence is kept as padding ONLY if it opens with one of these.
#
# The census's own classifier is not sufficient on its own, and this is the measurement
# that says so. The first rendered `k1pad` prompt carried the line "Label unverified
# claims as unverified. An unlabelled guess is indistinguishable from a measured fact",
# which is an INSTRUCTION -- and is the source rule behind pool instruction F2. It got
# through because `classify` decides a bare imperative by an enumeration of verbs, and
# `label` is not on that enumeration.
#
# Adding `label` to the verb list would be re-deriving the enumeration, which is the
# failure `AGENTS.md`'s rule audit names by name. So the padding filter does not
# enumerate what to REJECT. It enumerates what to ACCEPT and drops everything else. The
# two lists fail in opposite directions, and that is the point: a miss here costs
# padding volume, never correctness, where a miss in the census costs the count.
SAFE_OPENERS = {
    "the", "this", "that", "these", "those", "a", "an", "it", "its", "there",
    "here", "both", "each", "every", "everything", "nothing", "no", "none",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "several", "most", "some", "any", "neither", "either", "what", "which",
    "whether", "when", "where", "why", "how", "because", "since", "after",
    "before", "although", "though", "while", "whatever", "whichever", "they",
    "he", "she", "we", "you", "his", "her", "their", "our", "at",
    "in", "on", "by", "for", "from", "with", "without", "under", "over",
}


def padding_sentences() -> list[str]:
    """Declarative sentences from the project's own always-loaded docs.

    Four filters, all of which a sentence must survive:

      1. `instruction_census.classify` scores it non-normative -- the same instrument
         that produced the instruction count, so the control and the census cannot
         disagree about what counts as an instruction;
      2. it opens with a word on `SAFE_OPENERS`, which is an accept-list and therefore
         fails closed;
      3. it carries no `*` emphasis and no backticks. This repository bolds its
         imperatives, so the marker is a reliable signal of one even where the wording
         is not, and a backtick usually means a path or flag the agent might act on;
      4. it ends in a full stop and not a list ordinal, which drops the fragments the
         sentence splitter produces at the edges of numbered rules.

    `padcheck` then asserts the survivors share no six-word run with any pool
    instruction, which is what stops the padding restating a pool instruction in other
    words.
    """
    out: list[str] = []
    for rel in census.ALWAYS_LOADED:
        prose, _ = census.strip_code((ROOT / rel).read_text(encoding="utf-8"))
        body = [ln for ln in prose.splitlines()
                if not census.RE_HEADING.match(ln)
                and not census.RE_TABLE_SEP.match(ln)
                and not census.RE_TABLEROW.match(ln)]
        for sent in census.sentences("\n".join(body)):
            flat = " ".join(sent.split())
            flat = flat.lstrip("-*+> ").lstrip()
            flat = re.sub(r"^\d+\.\s*", "", flat)
            if len(flat) < 60 or len(flat) > 300:
                continue
            if census.classify(flat):
                continue
            if "*" in flat or "`" in flat or ">" in flat:
                continue
            if not flat.endswith("."):
                continue
            if re.search(r"\b\d+\.$", flat):
                continue
            # A colon or semicolon is where an imperative hides from a filter that only
            # inspects the opening word. The rendered prompt carried "The qualifier, and
            # it matters as much as the rule: hold variables constant, EXCEPT a ceiling
            # that may be binding" -- safe opener, no emphasis, and an imperative after
            # the colon. `needs` is the same shape for the soft list, which matches
            # "needs to" and not "needs a".
            if ":" in flat or ";" in flat or re.search(r"\bneeds?\b", flat, re.I):
                continue
            words = flat.split()
            if not words:
                continue
            if re.sub(r"[^a-z]", "", words[0].lower()) not in SAFE_OPENERS:
                continue
            out.append(flat)

    # Filter 5, and it was NOT anticipated: drop anything that restates a pool
    # instruction. The four filters above admitted "The fallback turns an error into a
    # plausible in-range number, which is the most dangerous shape a broken check can
    # take" -- declarative, no emphasis, safe opener, and word-for-word the source rule
    # behind pool instruction B1. Padding a k1 prompt with the text of an instruction
    # the trial was not given is the one thing this arm may not do.
    pool_grams: set = set()
    for ins in poolmod.POOL:
        pool_grams |= _grams(ins.text, 4)
    return [s for s in out if not (_grams(s, 4) & pool_grams)]


def _grams(text: str, n: int = 6) -> set:
    w = re.findall(r"[a-z_]+", text.lower())
    return {tuple(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def padcheck() -> int:
    """The control on the length-control arm: the padding must add tokens and NO
    instructions.

    Directional both ways, because only one direction is obvious. It asserts the filter
    admits nothing normative -- and it asserts the filter still admits ENOUGH prose to
    pad with, because an empty accept-list would satisfy every safety property here and
    silently turn `k1pad` into `k1`, which is the arm the whole experiment leans on.
    """
    ok = True
    sents = padding_sentences()
    # The quantity is CHARACTERS AVAILABLE, not sentences. An earlier version asserted
    # a sentence count, which is a proxy for the thing that matters and would have
    # failed a corpus of 30 long sentences that pads perfectly well. Proxy metrics are
    # #59's failure and they do not stop being one because the proxy is convenient.
    need = pad_budget(1.0, 39) * 4
    have = sum(len(s) + 1 for s in sents)
    print(f"padding pool: {len(sents)} sentences, {have} chars; "
          f"a k1pad prompt needs {need}")
    if have < need * 1.5:
        print("  FAIL  not enough prose to pad a k16-length prompt with headroom")
        ok = False
    else:
        print(f"  PASS  {have/need:.1f}x the required volume")

    bad = [s for s in sents if census.classify(s)]
    print(f"  {'PASS' if not bad else 'FAIL'}  none scores as normative ({len(bad)} do)")
    ok = ok and not bad

    pool_grams: set = set()
    for ins in poolmod.POOL:
        pool_grams |= _grams(ins.text, 5)
    overlap = [s for s in sents if _grams(s, 5) & pool_grams]
    print(f"  {'PASS' if not overlap else 'FAIL'}  no sentence shares a 5-word run "
          f"with a pool instruction ({len(overlap)} do)")
    for s in overlap[:5]:
        print(f"      {s[:110]}")
    ok = ok and not overlap

    # A SECOND MECHANISM, not a second threshold. The n-gram check above can only catch
    # a regression in the n-gram filter -- a control that shares its subject's
    # assumptions is the #37 shape. This one looks for the concrete nouns the pool
    # instructions name, so it can fire on a paraphrase that no shared word-run would
    # reveal.
    tokens = ["os.replace", "source_dir", "files_read", "UNVERIFIED", "SystemExit",
              "summary.json", "probe.py", "cost_usd", "88 characters", "stdout"]
    hits = [(t, s) for t in tokens for s in sents if t in s]
    print(f"  {'PASS' if not hits else 'FAIL'}  no sentence names a pool identifier "
          f"({len(hits)} do)")
    for t, s in hits[:5]:
        print(f"      {t}: {s[:100]}")
    ok = ok and not hits

    print("  negative control -- these must all be rejected:")
    for probe in ("Label unverified claims as unverified.",
                  "Run the gate before you believe the number.",
                  "Never quote a value you did not just read."):
        first = re.sub(r"[^a-z]", "", probe.split()[0].lower())
        rejected = (first not in SAFE_OPENERS) or bool(census.classify(probe))
        print(f"    {'PASS' if rejected else 'FAIL'}  {probe!r}")
        ok = ok and rejected

    print("\npadcheck:", "clean" if ok else "FAILED")
    return 0 if ok else 1


def pad_to(text_tokens: int, seed: int) -> str:
    """Non-normative prose, to approximately `text_tokens` tokens (chars/4)."""
    rng = random.Random(seed)
    sents = padding_sentences()
    rng.shuffle(sents)
    want = text_tokens * 4
    got, chunk = 0, []
    for s in sents:
        if got >= want:
            break
        chunk.append(s)
        got += len(s) + 1
    return (
        "Background on this project, for context. None of the following is a "
        "requirement:\n\n" + "\n".join(chunk) + "\n"
    )


# --------------------------------------------------------------------------- #
# Assignment
# --------------------------------------------------------------------------- #

def assign(scale: float, seed: int) -> list[dict]:
    """Build the whole trial list up front, so the design is inspectable before a
    single dollar is spent and identical for `plan` and `build`."""
    rng = random.Random(seed)
    ids = [i.id for i in poolmod.POOL]
    trials: list[dict] = []

    for arm in ARMS:
        k = ARM_K[arm]
        n_per_arm = max(1, round(ARM_N[arm] * scale))
        # Cycle a reshuffled pool so coverage per instruction is near-uniform in
        # every arm rather than uniform only in expectation.
        bag: list[str] = []
        for t in range(n_per_arm):
            chosen: list[str] = []
            while len(chosen) < k:
                if not bag:
                    bag = ids[:]
                    rng.shuffle(bag)
                nxt = bag.pop()
                if nxt not in chosen:
                    chosen.append(nxt)
            order = chosen[:]
            rng.shuffle(order)
            trials.append({
                "trial_id": f"{arm}__t{t}",
                "arm": arm,
                "k": k,
                "instructions": order,
                "padded": arm == "k1pad",
                "seed": rng.randrange(1 << 30),
            })
    return trials


def prompt_for(trial: dict, pad_tokens: int) -> str:
    block = poolmod.render(trial["instructions"])
    parts = [poolmod.BASE_TASK, ""]
    if trial["padded"]:
        parts += [pad_to(pad_tokens, trial["seed"]), ""]
    parts += [block]
    return "\n".join(parts)


def pad_budget(scale: float, seed: int) -> int:
    """Tokens of padding that make a k1pad prompt as long as a k16 prompt."""
    tr = assign(scale, seed)
    k16 = next(t for t in tr if t["arm"] == "k16")
    k1 = next(t for t in tr if t["arm"] == "k1")
    long_len = len(prompt_for(k16, 0))
    short_len = len(prompt_for({**k1, "padded": False}, 0))
    return max(0, round((long_len - short_len) / 4))


# --------------------------------------------------------------------------- #
# Running one trial
# --------------------------------------------------------------------------- #

def agent_metrics(agent: dict) -> dict:
    """Cost and tokens from `modelUsage`; `usage` is the main loop only."""
    mu = agent.get("modelUsage") or {}
    if mu:
        return {
            "cost_usd": round(sum((m or {}).get("costUSD", 0) or 0
                                  for m in mu.values()), 6),
            "input_tokens": sum((m or {}).get("inputTokens", 0) or 0
                                for m in mu.values()),
            "output_tokens": sum((m or {}).get("outputTokens", 0) or 0
                                 for m in mu.values()),
            "models": sorted(mu),
        }
    u = agent.get("usage") or {}
    return {"cost_usd": agent.get("total_cost_usd") or 0,
            "input_tokens": u.get("input_tokens", 0),
            "output_tokens": u.get("output_tokens", 0), "models": []}


def parse_agent(stdout: str) -> dict:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        data = [json.loads(ln) for ln in stdout.splitlines()
                if ln.strip().startswith("{")] or [{}]
    if isinstance(data, dict):
        data = [data]
    res = [d for d in data if isinstance(d, dict) and d.get("type") == "result"]
    return res[-1] if res else (data[-1] if data else {})


def run_one(trial: dict, prompt: str, work_root: Path) -> dict:
    """One agent, one fresh working directory OUTSIDE the repository.

    Outside deliberately: `--setting-sources project` keeps the operator's global
    CLAUDE.md out, and a directory outside the tree keeps this repository's own
    AGENTS.md out. Its 73-113 instructions would be added to EVERY arm, which would
    swamp a manipulation whose largest arm is 16.
    """
    work = work_root / trial["trial_id"]
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    argv = [
        "claude", "-p", prompt,
        "--output-format", "json",
        "--model", MODEL,
        "--max-turns", str(MAX_TURNS),
        "--setting-sources", "project",
        "--strict-mcp-config",
        "--exclude-dynamic-system-prompt-sections",
        "--permission-mode", "acceptEdits",
        # No Bash: the base task says not to run the script, so a shell would only add
        # a variable. No --max-budget-usd either -- a budget flag is visible to the
        # callee and is therefore an instruction (#33), and this experiment counts
        # instructions.
        "--allowedTools", "Write", "Edit", "Read",
        "--session-id", str(uuid.uuid4()),
    ]
    t0 = time.time()
    try:
        p = subprocess.run(argv, cwd=work, capture_output=True, text=True,
                           timeout=TIMEOUT_S, check=False)
        agent, stderr = parse_agent(p.stdout), p.stderr[-2000:]
    except subprocess.TimeoutExpired:
        agent, stderr = {"is_error": True, "subtype": "harness_timeout"}, "TIMEOUT"

    art = work / poolmod.ARTIFACT
    src = art.read_text(encoding="utf-8", errors="replace") if art.exists() else None
    rec = {
        **trial,
        "elapsed_s": round(time.time() - t0, 1),
        "terminal_reason": agent.get("subtype") or (
            "error" if agent.get("is_error") else "completed"),
        "num_turns": agent.get("num_turns"),
        # Rule 11: the subject's own account of its work is stored, because subjects
        # here have twice diagnosed a harness defect in a paragraph nothing read.
        "agent_final_text": (agent.get("result") or "")[:4000],
        "stderr_tail": stderr[-600:],
        "prompt_chars": len(prompt),
        "artifact_written": src is not None,
        "artifact_src": src,
        **agent_metrics(agent),
    }
    if src is None:
        rec["evaluation"] = {
            "usable": False, "parse_error": "no artifact written", "rc": None,
            "checks": {i: {"passed": False, "evidence": "no artifact written",
                           "cls": poolmod.BY_ID[i].cls,
                           "runs_artifact": poolmod.BY_ID[i].runs_artifact}
                       for i in trial["instructions"]},
        }
    else:
        rec["evaluation"] = poolmod.evaluate(src, trial["instructions"])
    return rec


# --------------------------------------------------------------------------- #
# Statistics, in pure Python -- neither numpy nor scipy is installed here
# --------------------------------------------------------------------------- #

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def binom_sf(k: int, n: int, p: float = 0.5) -> float:
    """P(X >= k). Exact, small n."""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def sign_test(diffs: list[float]) -> tuple[int, int, float]:
    """Two-sided exact sign test over paired differences, ties dropped."""
    pos = sum(1 for d in diffs if d > 0)
    neg = sum(1 for d in diffs if d < 0)
    n = pos + neg
    if n == 0:
        return pos, neg, 1.0
    k = max(pos, neg)
    return pos, neg, min(1.0, 2 * binom_sf(k, n))


def statcheck() -> int:
    """Pin the three statistics against values computed independently.

    Neither numpy nor scipy is installed on this machine, so `wilson`, `binom_sf` and
    `sign_test` are hand-rolled -- and a hand-rolled interval that is quietly wrong
    produces a plausible in-range number, which is the most dangerous shape a broken
    check can take. Every expected value below is a closed-form result, not a value read
    back out of this code.
    """
    ok = True

    def chk(name, got, want, tol=5e-4):
        nonlocal ok
        good = abs(got - want) <= tol
        print(f"  {'PASS' if good else 'FAIL'}  {name}: got {got:.6f} want {want:.6f}")
        ok = ok and good

    # Wilson, z=1.96. 10/10 -> [0.72247, 1.0]; 5/10 -> [0.23659, 0.76341].
    chk("wilson(10,10) lo", wilson(10, 10)[0], 0.722468)
    chk("wilson(10,10) hi", wilson(10, 10)[1], 1.0)
    chk("wilson(5,10) lo", wilson(5, 10)[0], 0.236593)
    chk("wilson(5,10) hi", wilson(5, 10)[1], 0.763407)
    lo, hi = wilson(0, 0)
    chk("wilson(0,0) is uninformative", hi - lo, 1.0)

    # Binomial survival. P(X>=10 | n=10, p=.5) = 2^-10.
    chk("binom_sf(10,10)", binom_sf(10, 10), 1 / 1024)
    chk("binom_sf(0,10)", binom_sf(0, 10), 1.0)
    # P(X>=8 | n=10) = (45+10+1)/1024
    chk("binom_sf(8,10)", binom_sf(8, 10), 56 / 1024)

    # Sign test. Ten improvements and no regressions is p = 2 * 2^-10.
    pos, neg, p = sign_test([0.1] * 10)
    chk("sign_test 10 up p", p, 2 / 1024)
    print(f"  {'PASS' if (pos, neg) == (10, 0) else 'FAIL'}  sign_test counts "
          f"{pos} up / {neg} down")
    ok = ok and (pos, neg) == (10, 0)
    # All ties must not be reported as significant, and must not divide by zero.
    pos, neg, p = sign_test([0.0] * 8)
    chk("sign_test all ties p", p, 1.0)
    # A perfectly balanced split is p = 1.
    chk("sign_test balanced p", sign_test([0.1, -0.1])[2], 1.0)

    # The bootstrap on a constant sample must collapse to that constant.
    lo, hi = boot_ci([0.25] * 12, reps=500)
    chk("boot_ci constant lo", lo, 0.25)
    chk("boot_ci constant hi", hi, 0.25)
    # And it must be wide on a split sample rather than silently degenerate.
    lo, hi = boot_ci([0.0, 1.0] * 6, reps=4000)
    wide = (hi - lo) > 0.3
    print(f"  {'PASS' if wide else 'FAIL'}  boot_ci on a split sample is wide: "
          f"[{lo:.3f}, {hi:.3f}]")
    ok = ok and wide

    print("\nstatcheck:", "clean" if ok else "FAILED")
    return 0 if ok else 1


def boot_ci(vals: list[float], seed: int = 7, reps: int = 20000) -> tuple[float, float]:
    if not vals:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    means = []
    n = len(vals)
    for _ in range(reps):
        means.append(sum(rng.choice(vals) for _ in range(n)) / n)
    means.sort()
    return (means[int(0.025 * reps)], means[int(0.975 * reps) - 1])


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

def cmd_plan(a) -> int:
    trials = assign(a.scale, a.seed)
    padtok = pad_budget(a.scale, a.seed)
    sizes = ", ".join(f"{arm}={sum(1 for t in trials if t['arm'] == arm)}"
                      for arm in ARMS)
    print(f"trials: {len(trials)}  ({sizes})")
    print(f"model: {MODEL}   max-turns: {MAX_TURNS}   no budget cap (a cap is an "
          f"instruction, #33)")
    print(f"padding for k1pad: ~{padtok} tokens of non-normative project prose\n")

    cover = defaultdict(lambda: defaultdict(int))
    for t in trials:
        for iid in t["instructions"]:
            cover[t["arm"]][iid] += 1
    hdr = "arm".ljust(7) + "".join(i.id.rjust(5) for i in poolmod.POOL) + "   obs"
    print(hdr)
    for arm in ARMS:
        row = arm.ljust(7) + "".join(str(cover[arm][i.id]).rjust(5)
                                     for i in poolmod.POOL)
        print(row + str(sum(cover[arm].values())).rjust(6))
    print("\nEvery instruction must appear in every arm. A zero above is a content "
          "confound waiting to be read as a count effect.")
    zeros = [(arm, i.id) for arm in ARMS for i in poolmod.POOL
             if cover[arm][i.id] == 0]
    if zeros:
        print(f"ZEROS PRESENT: {zeros[:10]}  -- raise --n")
    print(f"\nprompt chars: k1={len(prompt_for(trials[0], padtok))}, "
          f"k16={len(prompt_for(next(t for t in trials if t['arm'] == 'k16'), padtok))}, "
          f"k1pad={len(prompt_for(next(t for t in trials if t['arm'] == 'k1pad'), padtok))}")
    if a.show:
        t = next(t for t in trials if t["arm"] == a.show)
        print("\n" + "=" * 70 + f"\nPROMPT, arm {a.show}\n" + "=" * 70)
        print(prompt_for(t, padtok))
    return 0 if not zeros else 1


def cmd_build(a) -> int:
    trials = assign(a.scale, a.seed)
    if a.only:
        keep = set(a.only.split(","))
        trials = [t for t in trials if t["arm"] in keep]
    if a.limit:
        trials = trials[:a.limit]
    padtok = pad_budget(a.scale, a.seed)

    run_dir = Path(a.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    tdir = run_dir / "trials"
    tdir.mkdir(exist_ok=True)

    # Append-only configuration record. A second launch adds a record, it never
    # replaces one (eval/AGENTS.md).
    manifest = run_dir / "manifest.json"
    stamp = time.strftime("%Y%m%dT%H%M%S")
    if manifest.exists():
        manifest = run_dir / f"manifest-{stamp}.json"
    manifest.write_text(json.dumps({
        "started_at": stamp, "model": MODEL, "max_turns": MAX_TURNS,
        "scale": a.scale, "arm_n": ARM_N, "seed": a.seed, "arms": ARMS,
        "pad_tokens": padtok, "n_trials": len(trials),
        "pool_ids": [i.id for i in poolmod.POOL],
        "base_task_sha": __import__("hashlib").sha256(
            poolmod.BASE_TASK.encode()).hexdigest()[:16],
    }, indent=2))

    work_root = Path(tempfile.mkdtemp(prefix="instrfollow-work-"))
    print(f"work root (outside the repo, deliberately): {work_root}")
    spend = 0.0
    try:
        for n, t in enumerate(trials, 1):
            dest = tdir / f"{t['trial_id']}.json"
            if dest.exists() and not a.force:
                print(f"[{n}/{len(trials)}] {t['trial_id']} exists, skipping")
                continue
            rec = run_one(t, prompt_for(t, padtok), work_root)
            tmp = dest.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(rec, indent=2))
            os.replace(tmp, dest)
            spend += rec["cost_usd"]
            ev = rec["evaluation"]
            got = sum(c["passed"] for c in ev["checks"].values())
            print(f"[{n}/{len(trials)}] {t['trial_id']:<12} k={t['k']:<2} "
                  f"{got}/{len(t['instructions'])} pass  "
                  f"turns={rec['num_turns']} ${rec['cost_usd']:.4f} "
                  f"{rec['terminal_reason']}  spend=${spend:.2f}")
    finally:
        shutil.rmtree(work_root, ignore_errors=True)
    print(f"\ntotal measured spend: ${spend:.2f} over {len(trials)} trials")
    return 0


def load_trials(run_dir: Path) -> list[dict]:
    return [json.loads(p.read_text())
            for p in sorted((run_dir / "trials").glob("*.json"))]


def cmd_regrade(a) -> int:
    """Re-run every checker over the STORED artifacts, spending nothing.

    `eval/AGENTS.md` prefers offline re-grading to any re-run, and this is what makes
    that possible here: the artifact source is stored in every trial record, so a repair
    to a checker can be applied to trials already paid for. It is also the only honest
    way to use the pilot, whose trials were graded before the fixture split.
    """
    run_dir = Path(a.run_dir)
    changed = 0
    for p in sorted((run_dir / "trials").glob("*.json")):
        rec = json.loads(p.read_text())
        if rec.get("artifact_src") is None:
            continue
        before = rec["evaluation"]
        after = poolmod.evaluate(rec["artifact_src"], rec["instructions"])
        moved = [i for i in after["checks"]
                 if before["checks"].get(i, {}).get("passed")
                 != after["checks"][i]["passed"]]
        if moved or before["usable"] != after["usable"]:
            changed += 1
            print(f"{rec['trial_id']:<12} usable {before['usable']}->{after['usable']}"
                  f"  moved={moved}")
        rec["evaluation"] = after
        # EVERY checker, including the ones this trial was never given. Two things
        # depend on it and neither was anticipated when the pool was written:
        #
        #   * the ACCIDENTAL-COMPLIANCE FLOOR. If an instruction is satisfied most of
        #     the time by an agent that was never given it, then "compliance" with it
        #     is mostly not compliance, and a rate near 1.0 in the given condition says
        #     nothing about whether the instruction was read. Without this the whole
        #     experiment could report high compliance that the instructions did not
        #     cause.
        #   * a LEAKAGE control on the isolation. If this repository's own AGENTS.md
        #     were reaching the agent despite the temp work root and
        #     `--setting-sources project`, agents would spontaneously obey rules they
        #     were not given -- dated docstrings, UNVERIFIED lines, atomic writes. An
        #     elevated not-given rate on exactly the project-flavoured instructions is
        #     what that would look like.
        rec["evaluation_all"] = poolmod.evaluate(rec["artifact_src"])
        rec["regraded_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rec, indent=2))
        os.replace(tmp, p)
    print(f"\nregraded {run_dir}: {changed} trial(s) moved")
    return 0


def cmd_analyse(a) -> int:
    trials = load_trials(Path(a.run_dir))
    if not trials:
        print("no trials")
        return 2

    # Rule 4: partition by terminal status before computing anything.
    by_reason = defaultdict(list)
    for t in trials:
        by_reason[t["terminal_reason"]].append(t)
    print("TERMINAL STATUS")
    for r, ts in sorted(by_reason.items()):
        print(f"  {r:<20} n={len(ts)}")
    nowrite = [t for t in trials if not t["artifact_written"]]
    unusable = [t for t in trials if t["artifact_written"]
                and not t["evaluation"]["usable"]]
    print(f"  no artifact written  n={len(nowrite)}")
    print(f"  artifact unusable    n={len(unusable)}")

    obs = []   # (arm, k, instruction, passed)
    for t in trials:
        for iid, c in t["evaluation"]["checks"].items():
            obs.append((t["arm"], t["k"], iid, bool(c["passed"]), t["trial_id"]))

    print(f"\nOBSERVATIONS: {len(obs)} instruction-instances "
          f"over {len(trials)} trials")

    print("\nPER-ARM COMPLIANCE (pooled over instructions; Wilson 95%)")
    print(f"  {'arm':<7}{'k':>3}{'obs':>7}{'pass':>7}{'rate':>8}   95% CI")
    arm_rate = {}
    for arm in ARMS:
        rows = [o for o in obs if o[0] == arm]
        if not rows:
            continue
        k = sum(1 for o in rows if o[3])
        lo, hi = wilson(k, len(rows))
        arm_rate[arm] = k / len(rows)
        print(f"  {arm:<7}{ARM_K[arm]:>3}{len(rows):>7}{k:>7}{k/len(rows):>8.3f}"
              f"   [{lo:.3f}, {hi:.3f}]")

    # The primary comparison: WITHIN instruction, k=1 against k=16.
    print("\nPAIRED WITHIN-INSTRUCTION, k1 vs k16")
    print("  content is held constant by construction: each row is one instruction")
    print(f"  {'id':<5}{'cls':<4}{'k1':>10}{'k16':>10}{'diff':>9}")
    diffs, rows_pr = [], []
    for ins in poolmod.POOL:
        a1 = [o for o in obs if o[0] == "k1" and o[2] == ins.id]
        a16 = [o for o in obs if o[0] == "k16" and o[2] == ins.id]
        if not a1 or not a16:
            print(f"  {ins.id:<5}{ins.cls:<4}{'--':>10}{'--':>10}   no pair")
            continue
        p1 = sum(o[3] for o in a1) / len(a1)
        p16 = sum(o[3] for o in a16) / len(a16)
        diffs.append(p16 - p1)
        rows_pr.append((ins.id, ins.cls, p1, p16, len(a1), len(a16)))
        print(f"  {ins.id:<5}{ins.cls:<4}{p1:>7.2f}({len(a1):>2}){p16:>7.2f}"
              f"({len(a16):>2}){p16 - p1:>9.2f}")

    if diffs:
        pos, neg, p = sign_test(diffs)
        lo, hi = boot_ci(diffs)
        md = statistics.fmean(diffs)
        print(f"\n  mean paired difference (k16 - k1): {md:+.3f}")
        print(f"  bootstrap 95% CI over instructions: [{lo:+.3f}, {hi:+.3f}]")
        print(f"  sign test: {pos} up, {neg} down, {len(diffs)-pos-neg} tied, "
              f"two-sided p={p:.4f}")

    # The length control.
    print("\nLENGTH CONTROL: k1 vs k1pad (same ONE instruction, k16-length prompt)")
    for arm in ("k1", "k1pad"):
        rows = [o for o in obs if o[0] == arm]
        if rows:
            k = sum(1 for o in rows if o[3])
            lo, hi = wilson(k, len(rows))
            print(f"  {arm:<7} {k}/{len(rows)} = {k/len(rows):.3f}  [{lo:.3f}, {hi:.3f}]")
    if "k1" in arm_rate and "k1pad" in arm_rate:
        print(f"  difference attributable to LENGTH alone: "
              f"{arm_rate['k1pad'] - arm_rate['k1']:+.3f}")
        if "k16" in arm_rate:
            print(f"  difference k16 - k1 (length AND count): "
                  f"{arm_rate['k16'] - arm_rate['k1']:+.3f}")

    # Rule 4 again: never pool a heterogeneous population without showing the parts.
    print("\nBY CLASS (format vs behavioural), per arm")
    print(f"  {'arm':<7}{'F rate':>10}{'B rate':>10}")
    for arm in ARMS:
        rows = [o for o in obs if o[0] == arm]
        if not rows:
            continue
        f = [o for o in rows if poolmod.BY_ID[o[2]].cls == "F"]
        b = [o for o in rows if poolmod.BY_ID[o[2]].cls == "B"]
        fs = f"{sum(o[3] for o in f)/len(f):.3f}" if f else "--"
        bs = f"{sum(o[3] for o in b)/len(b):.3f}" if b else "--"
        print(f"  {arm:<7}{fs:>10}{bs:>10}")

    # Rule 9: uniformity is the signature of a shared cause.
    print("\nPER-INSTRUCTION OVERALL RATE (a saturated row cannot show degradation)")
    sat = []
    for ins in poolmod.POOL:
        rows = [o for o in obs if o[2] == ins.id]
        if not rows:
            continue
        r = sum(o[3] for o in rows) / len(rows)
        flag = ""
        if r == 1.0:
            flag = "  SATURATED: never failed, cannot show a count effect"
            sat.append(ins.id)
        elif r == 0.0:
            flag = "  FLOORED: never passed, cannot show a count effect"
            sat.append(ins.id)
        print(f"  {ins.id:<5}{ins.cls:<3}{r:>7.3f}  n={len(rows):<4}{flag}")
    if sat:
        print(f"\n  {len(sat)} of {len(poolmod.POOL)} instructions carry no variance: "
              f"{sat}")
        print("  An inert term is a question about the QUANTITY, not the parameter "
              "(rule 16).")

    # COST IS REPORTED PER ARM, NEVER POOLED.
    # The arms differ in prompt length and in how much the agent has to write, so a
    # per-trial mean across them is arithmetically correct and describes nothing
    # (rule 4). The pilot measured $0.054 at k1 and $0.322 at k16 -- a 6x spread that a
    # single mean would hide, and anyone pricing a follow-up from that mean would
    # misprice every arm.
    # ACCIDENTAL COMPLIANCE, and the leakage control. Needs `regrade` to have stored
    # `evaluation_all`; it is silent rather than wrong when that is absent.
    have_all = [t for t in trials if t.get("evaluation_all")]
    if have_all:
        print(f"\nGIVEN vs NOT GIVEN  (n={len(have_all)} trials re-checked against all "
              f"16)")
        print("  an instruction satisfied without being given was not COMPLIED with;")
        print("  a high not-given rate on project-flavoured rules would mean leakage.")
        print(f"  {'id':<5}{'cls':<4}{'given':>14}{'not given':>14}{'effect':>9}")
        eff = []
        for ins in poolmod.POOL:
            g = [t for t in have_all if ins.id in t["instructions"]]
            ng = [t for t in have_all if ins.id not in t["instructions"]]
            if not g or not ng:
                continue
            pg = sum(t["evaluation_all"]["checks"][ins.id]["passed"] for t in g) / len(g)
            pn = sum(t["evaluation_all"]["checks"][ins.id]["passed"]
                     for t in ng) / len(ng)
            eff.append((ins.id, pg - pn))
            print(f"  {ins.id:<5}{ins.cls:<4}{pg:>9.3f}({len(g):>3}){pn:>9.3f}"
                  f"({len(ng):>3}){pg - pn:>9.3f}")
        inert = [i for i, d in eff if d <= 0.05]
        if inert:
            print(f"\n  {len(inert)} instruction(s) with effect <= 0.05: {inert}")
            print("  Those are satisfied by default. Their 'compliance' is not evidence "
                  "the instruction was read, and a count effect cannot show up in them.")

    spend = sum(t["cost_usd"] for t in trials)
    print(f"\nCOST: ${spend:.2f} over {len(trials)} trials, per arm:")
    for arm in ARMS:
        ts = [t for t in trials if t["arm"] == arm]
        if not ts:
            continue
        cs = [t["cost_usd"] for t in ts]
        print(f"  {arm:<7} n={len(ts):<4} ${sum(cs):>7.2f}   "
              f"${statistics.fmean(cs):.4f} each "
              f"(min ${min(cs):.4f}, max ${max(cs):.4f})")
    turns = [t["num_turns"] for t in trials if t["num_turns"]]
    if turns:
        print(f"TURNS: median {statistics.median(turns)}, max {max(turns)} "
              f"of a {MAX_TURNS} ceiling"
              + ("   CEILING MAY HAVE BOUND" if max(turns) >= MAX_TURNS else ""))

    if a.json:
        Path(a.json).write_text(json.dumps({
            "arm_rate": arm_rate,
            "paired": [{"id": i, "cls": c, "k1": p1, "k16": p16,
                        "n1": n1, "n16": n16}
                       for i, c, p1, p16, n1, n16 in rows_pr],
            "n_trials": len(trials), "n_obs": len(obs), "spend_usd": spend,
        }, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="show the design, spend nothing")
    p.add_argument("--scale", type=float, default=1.0,
                   help="multiplies ARM_N; 0.25 is a pilot, 1.0 the full design")
    p.add_argument("--seed", type=int, default=39)
    p.add_argument("--show", choices=ARMS, help="print one arm's full prompt")
    p.set_defaults(fn=cmd_plan)

    p = sub.add_parser("build", help="run trials")
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=39)
    p.add_argument("--run-dir", required=True)
    p.add_argument("--only", help="comma-separated arms")
    p.add_argument("--limit", type=int)
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_build)

    p = sub.add_parser("statcheck", help="pin the hand-rolled statistics")
    p.set_defaults(fn=lambda a: statcheck())

    p = sub.add_parser("regrade", help="re-check stored artifacts offline, spend nothing")
    p.add_argument("--run-dir", required=True)
    p.set_defaults(fn=cmd_regrade)

    p = sub.add_parser("padcheck", help="control on the length-control arm")
    p.set_defaults(fn=lambda a: padcheck())

    p = sub.add_parser("analyse", help="read stored trials, spend nothing")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--json", help="write the summary here")
    p.set_defaults(fn=cmd_analyse)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
