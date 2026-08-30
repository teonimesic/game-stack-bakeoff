#!/usr/bin/env python3
"""WHAT THE NON-CODE JUDGE ROUNDS READ, against what their packs carried.

THE PRODUCER for the population figures in `eval/RUNS.md`'s 2026-08-28
pre-registration of the `claude -p` prompt keyed on the pack's `sees`
(`field.JUDGE_PROMPT_SEES`). Until that change the prompt told every judge to
read code in A/ through H/ whatever its pack held. These figures are the
LATENT-NULL measurement: did any stored non-code round actually read the
evidence its prompt named and its pack did not carry? Do not quote them from
memory; run this.

Population: every JSON record under the root carrying `aspect` and `order_seed`
(the same predicate `blurb_selftest.py --stored-rounds` counts), whose pack
carries no code — `provenance.sees` lacking `code`, or for a round stored
before `provenance` existed, the aspect's `sees`.

Per aspect it reports six counts over the Read half; the first four are round
states and sum to the aspect's n, the fifth counts targets, the last counts
reads:

* **capture** — a `files_opened` list of strings is stored. The key did not
  exist before task 09 (2026-08-22), so absence is a THIRD value and not a
  clean bill: what that round read is permanently unaskable (#83's shape).
* **null** — the key is present but null. Only null counts as null.
* **absent** — the key is not in the record.
* **malformed** — the key is present but its value is neither null nor a list
  of strings: a shape the capture code never writes, refused whole. The unit
  is the RECORD — a bad shape poisons the capture, so nothing in it is
  classified.
* **truncated** — a read target of exactly 200 characters inside an
  otherwise-usable list: the length the capture in `field.py` stored at until
  2026-08-28 (task 204, since when it stores the full target), so in every
  round captured before then the stored tail — where the filename lives —
  cannot be vouched for. The unit is the TARGET: refused from classification,
  counted per target, itemised in full, and never counted as carried or as
  un-carried, while the list's good targets still classify. The walk never
  aborts on any of this.
* **un-carried reads** — reads naming anything the pack does not carry. This is
  the column the pre-registration is about; its content would make the wording
  change a re-scoring event rather than a wording change. The pack holds four
  kinds of thing and nothing else, so a read target naming NO known bucket —
  a `.src` path, a `.png` outside `frames/` — is un-carried too, and is
  itemised under its filename rather than folded away: a classifier with a
  residual bucket is a classifier that decides by default what it did not
  expect.

THE BASH HALF (task 218). `files_opened` is filled from Read/NotebookRead
calls only, but `tool_calls` — stored beside it since task 204 (2026-08-28) —
records every tool call with its full target, and the stored corpus holds far
more reading done through Bash than through Grep. A judge that `cat`s or
`grep`s an un-carried path lands in none of the six states above, so the
census also walks `tool_calls` and reports a second table per aspect beside
the first. Its unit and refusal rules, stated to the same precision:

* **population** — the same rounds. The Bash half is read from `tool_calls`,
  whose key states mirror the Read half's: a round with no `tool_calls` key,
  a null one, or a malformed one (not a list, or an element that is not an
  object carrying a string `target` — shapes the capture never writes) is
  **unassessable on the Bash half and is counted, never read as clean**. The
  two halves refuse independently: the unit of a malformed refusal is the
  KEY'S CAPTURE, not the round, so a round whose `files_opened` is malformed
  still contributes its Bash half and conversely.
* **the call is the unit.** A Bash or Grep tool call is one call. A command of
  exactly 200 characters is a stored truncation (the same cap the Read half
  refuses at) and is **refused whole** — its tail may hold more operands, so
  nothing in it is classified; counted per command, itemised in full.
* **no-path is a state, never a drop.** From every other call the extractor
  pulls the path-like operands of the READING VERBS — `cat head tail less grep
  sed awk wc find`, a closed set: the ticket names it, and `ls`, `du`, `cmp`
  and `python3` extract nothing and land their call here. So does a call with
  a reading verb and nothing extractable — options, a `grep`/`sed`/`awk`
  pattern or script operand (the first non-option operand of those three is
  never a path), a shell expansion (`$d`, `*.png`, `` ` ``, `~`), a glob with
  no literal path, or no reading verb at all. Each such call is counted under
  **no-path**; it is a measurement of what the record can classify, not an
  absence of measurement.
* **operands classify through the SAME `named_bucket` as Read targets**,
  against the same layout `<label>/frames/*.png`, `<label>/audio.json`,
  `<label>/telemetry.json`, plus the shapes a Bash operand can be and a Read
  target cannot: the pack root (`.`) and a bare bucket label (`A`) are always
  carried — every pack carries all eight submission buckets — and a path
  naming the frames DIRECTORY (`A/frames`) is the frames bucket. Everything
  else is an **un-carried Bash read** — the leak column this half exists for,
  itemised with the operand and the command that named it.
* **a Grep tool call has no command.** Its stored target is the `path` input
  when one was given and the `pattern` when not, so: a path-like stored target
  classifies as the call's operand; a non-path-like one is a no-path call. A
  path-like PATTERN naming un-carried evidence would read as a leak — the
  same shape-versus-location limit as below, caught by the itemisation.
* **limits, stated because they cannot be engineered away here.** The record
  carries no pack root (the pack tmpdir is deleted after the round), so an
  operand classifies by its shape, not by where it really was — the same
  limit the Read half documents, with the same compensating control: every
  un-carried operand is itemised with its full command. And the extractor
  reads the command as ONE shell level: `bash -c` strings, `$(...)`, heredoc
  bodies and anything else that is a nested interpreter are not re-entered;
  what they read is not extractable, and a call reduced to nothing by that
  limit is counted under no-path rather than silently clean.

One read target is classified by the path it names, against the layout
`build_pack` writes: `<label>/frames/*.png`, `<label>/audio.json`,
`<label>/telemetry.json`; `BRIEF.md`, `SCENE.md` and anything under `/.claude/`
are housekeeping every judge is handed.

The classification is proven on a fixture tree (`--selftest`) whose every
answer is written out as a literal beside it, including the two rows that
discriminate: a code read inside a frames pack (the leak the column exists to
catch) and a `.png` read NOT under `frames/` (which must land in `other`, not
in frames — the exact bug a right-splitting path parse had here once).

Run:  python3 judge/prompt_capture_census.py --runs-root <main checkout>/eval/runs
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import aspects  # noqa: E402

#: `sees` for a round stored before `provenance` existed — the aspect is the
#: only thing those records carry. Same table and same reason as the census in
#: `blurb_selftest.py`: kept beside the code that uses it so a `sees` change
#: surfaces here as a mismatch rather than silently reclassifying rounds.
_SEES_BY_ASPECT = {"idiomatic": "code", "architecture": "code",
                   "fun": "frames+telemetry", "fun_frames": "frames",
                   "audio": "audio", "ux": "frames"}


def named_bucket(target: str) -> str:
    """Which evidence bucket a read target names, or `housekeeping`/`other`.

    The bucket is named by the FILENAME for audio and telemetry and by the
    DIRECTORY for frames, and the housekeeping files by their names — so a
    RELATIVE target (`BRIEF.md`, `frames/f0.png`, `A/audio.json`) classifies
    exactly as an absolute one. Under the earlier `/frames/`-and-slash rules a
    relative read fell into `other` and was counted un-carried: a false
    positive shaped like a finding, which is the direction a latent-null
    census must not fail in.

    THE BASH-HALF SHAPES (task 218), added beside the file shapes and proven
    to move 0 of the 6,317 stored Read targets: a Bash operand can BE the pack
    root (`.`), a bare bucket label (`A` — every pack carries all eight
    submission buckets), the frames DIRECTORY of a bucket (`A/frames`), or the
    `.claude` directory itself. `..` anywhere escapes the pack by shape and is
    `other`, however much the tail resembles the layout.

    THE LIMIT, stated because it cannot be engineered away here: the stored
    record carries no pack root — the pack tmpdir is deleted after the round —
    so a target OUTSIDE the pack that mimics the layout classifies by its
    shape, not by where it really was. The compensating controls are that
    every un-carried read is itemised with its full target path, and any
    target naming no known bucket is itemised by filename rather than folded
    into a bucket.
    """
    t = target.replace("\\", "/")
    name = t.rsplit("/", 1)[-1]
    if name.endswith(".png") and ("/frames/" in t or t.startswith("frames/")):
        return "frames"
    if name == "audio.json":
        return "audio"
    if name == "telemetry.json":
        return "telemetry"
    if (name in ("BRIEF.md", "SCENE.md") or "/.claude/" in t
            or t.startswith(".claude/")):
        return "housekeeping"
    s = t
    while s.startswith("./"):
        s = s[2:]
    if s.endswith("/"):
        s = s.rstrip("/") or "/"
    if s in (".", ""):
        return "pack-root"
    parts = s.split("/")
    if ".." in parts:
        return "other"
    if parts[-1] == "frames":
        return "frames"
    if s == ".claude" or parts[-1] == ".claude":
        return "housekeeping"
    if len(parts) == 1 and len(s) == 1 and s.isalpha() and s.isupper():
        return "bucket"
    return "other"


#: Buckets that are carried whatever the aspect's `sees` says: housekeeping is
#: handed to every judge, the pack root carries only what the pack carries,
#: and a bare bucket label is one of the eight submission directories every
#: pack holds.
_ALWAYS_CARRIED = frozenset({"housekeeping", "pack-root", "bucket"})

#: THE READING VERBS the Bash half extracts operands from. CLOSED: the ticket
#: names them, and the census states the consequence in its docstring - `ls`,
#: `du`, `cmp` and `python3` extract nothing and land their call in `no-path`,
#: a counted state, never a silent drop.
_READ_VERBS = frozenset(
    {"cat", "head", "tail", "less", "grep", "sed", "awk", "wc", "find"})

#: Verbs whose FIRST non-option operand is a pattern, program or script and
#: never a path - `grep pat file`, `sed 's/x/y/' file`, `awk '{print}' file`.
#: A pattern operand can be path-LIKE (`grep -v /frames/`, `sed 's/^/  /'`)
#: and extracting it would read a false un-carried leak.
_PATTERN_FIRST = frozenset({"grep", "sed", "awk"})

#: Pattern-first flags whose NEXT token is the pattern or a pattern file,
#: not a path - honoured for the pattern-first verbs only: `cat -e` shows
#: line ends and `tail -f` follows the file named after it, so there the
#: next token is an operand.
_VALUE_FLAGS = frozenset({"-e", "-f"})

#: A token carrying any of these is a shell EXPANSION, not a literal path:
#: it may name nothing, or anything, and classifying a guess would be a
#: measurement the record cannot support. `$d`, `*.png`, `` `cmd` ``, `~`,
#: `{a,b}` all land here.
_EXPANSION_CHARS = "$`{}*?~"

#: Simple commands are split at these and ONLY these - newline included
#: (task 222): the lexer emits it as a punctuation token, so it splits here
#: exactly like `;`, which is how the ValueError fallback already treats it.
#: `<` and `>` are deliberately absent: they are handled inside the segment,
#: where `< file` is a read and `> file` is a write target - splitting on
#: them would deliver the redirected file as a verb-less segment and lose
#: the read.
_SEGMENT_BREAK = frozenset("();|&\n")

#: The lexer's punctuation set: shlex's default `();<>|&` plus the newline
#: (task 222). With it shlex ends a word at a newline and emits the newline
#: as its own token, alone or inside a punctuation run, while a newline
#: INSIDE quotes is data and never reaches the set. The other half is in
#: `_tokenise`: shlex consults whitespace BEFORE its punctuation machinery
#: and its constructor removes a punctuation char from wordchars only, so a
#: newline left in whitespace is consumed silently and two newline-joined
#: commands arrive as ONE segment - which is how the sed script `s/x/y/`
#: extracted as a path operand: a false positive shaped like a finding, the
#: direction `named_bucket`'s docstring forbids.
_LEX_PUNCT = "();<>|&\n"

#: `FOO=bar cmd ...` — an environment assignment before the verb, never the
#: verb itself nor an operand.
_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _tokenise(command: str) -> list[str]:
    """One shell level of tokens, quotes respected, separators visible.

    `punctuation_chars` keeps runs of `;|&()<>' and newline as whole tokens
    so the segment walker can see them; `whitespace_split` keeps word tokens
    whole. THE NEWLINE IS A SEPARATOR, NOT WHITESPACE (task 222): shlex
    consults whitespace before its punctuation machinery, so the newline is
    dropped from the whitespace set as well as being in `_LEX_PUNCT` - in
    whitespace it was consumed silently, newline-joined commands arrived as
    ONE segment, and a pattern-first verb's script (`sed 's/x/y/'`)
    extracted as a path operand. A newline inside quotes is DATA and stays
    inside its token: the quoted state consults neither set. An untokenisable
    command (unbalanced quote) falls back to splitting on the separators and
    whitespace - stated in the docstring as a limit, and the itemisation
    adjudicates whatever it yields; that path's newline replace is blind
    because the quotes have already failed to lex, so a quoted newline in a
    fallback command does not survive (the main path's does).
    """
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=_LEX_PUNCT)
        lex.whitespace_split = True
        lex.commenters = ""
        lex.whitespace = lex.whitespace.replace("\n", "")
        return list(lex)
    except ValueError:
        for sep in ("&&", "||"):
            command = command.replace(sep, ";")
        for sep in (";", "|", "\n"):
            command = command.replace(sep, ";")
        return [w for seg in command.split(";") for w in seg.split()]


def _segments(toks: list[str]) -> list[list[str]]:
    """Split a token stream at shell separators into simple-command runs."""
    segs: list[list[str]] = []
    cur: list[str] = []
    for t in toks:
        if t and set(t) <= _SEGMENT_BREAK:
            if cur:
                segs.append(cur)
                cur = []
        else:
            cur.append(t)
    if cur:
        segs.append(cur)
    return segs


def _pathlike(tok: str) -> bool:
    """Whether a token is a LITERAL path-like operand.

    Three ways to be one - a slash, a dot, or a bare uppercase letter (a
    bucket label). A shell expansion (`$d`, `*.png`, `` ` ``, `~`, `{a,b}`) is
    never one: it may name nothing or anything, and classifying a guess would
    be a measurement the record cannot support. An option (`-x`, `--all`) is
    never one - which is also what keeps an option's VALUE a non-path when
    the value is a bare word (`-maxdepth 2`, `-type f`).
    """
    if any(c in tok for c in _EXPANSION_CHARS):
        return False
    if tok.startswith("-") and len(tok) > 1:
        return False
    return ("/" in tok or "." in tok
            or (len(tok) == 1 and tok.isalpha() and tok.isupper()))


def _find_path_operands(toks: list[str]) -> list[str]:
    """find's OWN POSIX shape, not the generic operand walk.

    `find [options] path... expression`: every operand BEFORE the first
    expression token is a path, and nothing after it is - the expression is
    primaries (`-type`, `-name`, `-exec`, ...) and their VALUES, and a value
    can be path-like. Measured on the stored corpus: `find . -iname "BRIEF.md"
    -o -iname "brief.md"` had its case-variant search value extracted as an
    operand and read as a false un-carried leak, while `find A B C -type f`
    names three genuine path operands. `-H -L -P` are the options POSIX lets
    precede the paths, so they neither break nor extract.
    """
    out: list[str] = []
    for tok in toks:
        if tok in ("-H", "-L", "-P"):
            continue
        if (tok.startswith("-") and len(tok) > 1) or tok in ("(", ")", "!", ","):
            break  # the expression begins; everything after is not a path
        if _pathlike(tok):
            out.append(tok)
    return out


def _segment_reads(seg: list[str]) -> list[str]:
    """The path-like operands one simple command reads.

    `< file` is a read whatever the verb is; `> file` is written, never read;
    a punctuation token after `<` is a process substitution, not a file, and
    the substitution's command stays inside the one-shell-level limit.
    Options (tokens starting with `-`) are skipped, `--` ends the options,
    the first operand of a pattern-first verb is the pattern, and only
    path-like tokens (see `_pathlike`) survive. `find` follows its own POSIX
    shape: every operand BEFORE the first expression token is a path, and
    nothing after it is - which is what keeps a case-variant search value
    (`-iname "brief.md"`) from reading as a false un-carried leak. What
    survives is extracted verbatim for the classifier.
    """
    reads: list[str] = []
    walk: list[str] = []
    i = 0
    while i < len(seg):
        t = seg[i]
        if t == "<":
            if i + 1 < len(seg):
                nxt = seg[i + 1]
                if _pathlike(nxt):
                    reads.append(nxt)
            i += 2
            continue
        if ">" in t and set(t) <= {">", "&"}:
            # every punctuation-only redirect spelling: >, >>, &>, >& - and
            # the `2` of `2>` arrives as its own word token. Skip the operator
            # AND its write target: a redirect target is written, never read.
            # A quoted > inside a data argument carries other characters and
            # does not match, so `grep "a>b" A/audio.json` still extracts.
            i += 2
            continue
        walk.append(t)
        i += 1
    j = 0
    while j < len(walk) and _ASSIGN_RE.match(walk[j]):
        j += 1
    if j >= len(walk):
        return reads
    verb = walk[j].rsplit("/", 1)[-1]
    if verb not in _READ_VERBS:
        return reads
    if verb == "find":
        return reads + _find_path_operands(walk[j + 1:])
    endopts = False
    pattern_pending = verb in _PATTERN_FIRST
    expect_value = False
    for tok in walk[j + 1:]:
        if expect_value:
            expect_value = False
            continue
        if not endopts and tok == "--":
            endopts = True
            pattern_pending = False
            continue
        if not endopts and tok.startswith("-") and len(tok) > 1:
            if verb in _PATTERN_FIRST and tok in _VALUE_FLAGS:
                # -e/-f take a VALUE only on the pattern-first verbs (grep's
                # -f is a pattern file; sed/awk match). The same spellings on
                # the other verbs are plain options: `cat -e` shows line ends
                # and `tail -f` FOLLOWS the file named after it, so eating the
                # next token there would hide a real read. The value also
                # satisfies the pattern slot, so the next operand is a file.
                expect_value = True
                pattern_pending = False
            elif verb in _PATTERN_FIRST and tok[:2] in _VALUE_FLAGS and len(tok) > 2:
                # the ATTACHED spelling - `-epat`, `-fVALUE`, or the shell-glued
                # `-e's/.../'`, one token either way - carries the pattern
                # INLINE: there is no next token to consume and the pattern slot
                # is satisfied here, so the file after it extracts.
                pattern_pending = False
            continue
        if pattern_pending:
            pattern_pending = False
            continue
        if _pathlike(tok):
            reads.append(tok)
    return reads


def bash_operand_paths(command: str) -> list[str]:
    """Every path-like operand the reading verbs in one Bash command name.

    The command is read as ONE shell level (the docstring states the limit:
    `bash -c` strings, `$(...)` and heredoc bodies are not re-entered), split
    into simple commands at `;`, `|`, `&&`, `||` and newlines, and each
    reading verb's operands are extracted verbatim. Order is command order.
    """
    out: list[str] = []
    for seg in _segments(_tokenise(command)):
        out.extend(_segment_reads(seg))
    return out


def rounds(runs_root: Path) -> list[dict]:
    """Every stored round record the population predicate accepts."""
    out = []
    for p in sorted(runs_root.rglob("*.json")):
        try:
            d = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not (isinstance(d, dict) and "aspect" in d and "order_seed" in d):
            continue
        prov = d.get("provenance") or {}
        aid = d["aspect"]
        sees = prov.get("sees") or _SEES_BY_ASPECT.get(aid)
        if not sees or "code" in sees.split("+"):
            continue
        out.append({"path": p, "aspect": aid, "sees": sees, "record": d})
    return out


def census(runs_root: Path) -> int:
    rs = rounds(runs_root)
    if not rs:
        print(f"no non-code judge rounds under {runs_root} - UNMEASURED, not clean",
              file=sys.stderr)
        return 2

    per: dict[str, dict[str, int]] = {}
    bash: dict[str, dict[str, int]] = {}
    leaks: list[str] = []
    truncs: list[str] = []
    others: dict[str, int] = {}
    bleaks: list[str] = []
    btruncs: list[str] = []
    for r in rs:
        row = per.setdefault(r["aspect"], {"n": 0, "capture": 0, "null": 0,
                                           "absent": 0, "uncarried": 0,
                                           "malformed": 0, "truncated": 0})
        brow = bash.setdefault(r["aspect"], {"tc_capture": 0, "tc_null": 0,
                                             "tc_absent": 0, "tc_malformed": 0,
                                             "calls": 0, "btrunc": 0,
                                             "nopath": 0, "operands": 0,
                                             "bunc": 0})
        row["n"] += 1
        rec = r["record"]
        carried = set(r["sees"].split("+"))
        # ---- THE READ HALF (files_opened). MEMBERSHIP, not `.get`: a key
        # that is absent and a key stored null are two different unassessable
        # states, and `.get` reads both as None - which collapsed the columns
        # in the fixture before it touched the corpus. A third: only None
        # counts as null. Anything else that is not a list of strings is a
        # shape the capture code never writes - named `malformed` and skipped
        # WHOLE, because classifying a dict as null reads a shape error as a
        # recorded state, and classifying the string elements of a bad list
        # would silently keep the readable half. (Review round 2: both shapes
        # used to be worse - the dict read as null, and a list holding a
        # non-string reached the classifier and aborted the whole walk at
        # `target.replace`.)
        if "files_opened" not in rec:
            row["absent"] += 1
        else:
            opened = rec["files_opened"]
            if opened is None:
                row["null"] += 1
            elif (not isinstance(opened, list)
                    or any(not isinstance(t, str) for t in opened)):
                row["malformed"] += 1
            else:
                row["capture"] += 1
                for t in opened:
                    # A stored target of EXACTLY 200 characters may be a
                    # truncation: until 2026-08-28 the capture in field.py
                    # stored str(target)[:200], so anything longer than the
                    # cap was stored at exactly this length with its tail -
                    # the filename - gone, and anything shorter was never
                    # cut. The capture now stores the full target (task 204),
                    # but every round captured before that date remains
                    # 200-capped, so the arm stays for the stored corpus.
                    # Classifying it would be a guess; refused and itemised,
                    # never a carried read and never a leak. Counted per
                    # TARGET under `truncated` - a different unit from
                    # `malformed` above, which is per record: two truncated
                    # targets in one list are two, and the list's good
                    # targets still classify. (Round 4: both used to add to
                    # the same column, which made a count that named no
                    # unit.)
                    if len(t) == 200:
                        row["truncated"] += 1
                        truncs.append(f"{r['path'].name}: {t}")
                        continue
                    b = named_bucket(t)
                    if b in _ALWAYS_CARRIED or b in carried:
                        continue
                    row["uncarried"] += 1
                    others[Path(t).name] = others.get(Path(t).name, 0) + 1
                    leaks.append(f"{r['path'].name}: {t}")
        # ---- THE BASH HALF (tool_calls, task 218). An INDEPENDENT key with
        # its own states: the refusal of one half never silences the other,
        # because each key's capture stands or falls alone and a round whose
        # files_opened is malformed may still carry a perfect tool_calls list
        # (the fixture pins both directions). Unassessable on this half is a
        # counted state, never clean.
        if "tool_calls" not in rec:
            brow["tc_absent"] += 1
        else:
            tcs = rec["tool_calls"]
            if tcs is None:
                brow["tc_null"] += 1
            elif (not isinstance(tcs, list)
                    or any(not isinstance(c, dict)
                           or not isinstance(c.get("target"), str)
                           for c in tcs)):
                brow["tc_malformed"] += 1
            else:
                brow["tc_capture"] += 1
                for c in tcs:
                    if c.get("tool") not in ("Bash", "Grep"):
                        continue
                    brow["calls"] += 1
                    tgt = c["target"]
                    # THE SAME CAP THE READ HALF REFUSES AT. A command of
                    # exactly 200 characters was stored by the pre-204
                    # capture with its tail - where later operands live -
                    # unverifiable, so the whole COMMAND is refused: counted
                    # per command, itemised in full, classified never.
                    if len(tgt) == 200:
                        brow["btrunc"] += 1
                        btruncs.append(f"{r['path'].name}: {tgt}")
                        continue
                    ops = (bash_operand_paths(tgt) if c["tool"] == "Bash"
                           else ([tgt] if _pathlike(tgt) else []))
                    if not ops:
                        # NO-PATH IS A STATE, NEVER A DROP: no reading verb
                        # ran, or nothing in the call extracted to a literal
                        # path (options, a pattern operand, a shell
                        # expansion, a nested shell). Counted per call.
                        brow["nopath"] += 1
                        continue
                    brow["operands"] += len(ops)
                    for op in ops:
                        b = named_bucket(op)
                        if b in _ALWAYS_CARRIED or b in carried:
                            continue
                        brow["bunc"] += 1
                        bleaks.append(f"{r['path'].name}: {op}  "
                                      f"[{c['tool']}: {tgt}]")

    print(f"non-code judge rounds under {runs_root}: {len(rs)}")
    print(f"  {'aspect':12s} {'n':>3s} {'capture':>8s} {'null':>5s} {'absent':>7s} "
          f"{'un-carried reads':>17s} {'malformed':>10s} {'truncated':>10s} "
          f"{'bash-unc':>9s}")
    for aid, row in sorted(per.items()):
        print(f"  {aid:12s} {row['n']:3d} {row['capture']:8d} {row['null']:5d} "
              f"{row['absent']:7d} {row['uncarried']:17d} {row['malformed']:10d} "
              f"{row['truncated']:10d} {bash[aid]['bunc']:9d}")
    n_cap = sum(r["capture"] for r in per.values())
    n_unc = sum(r["uncarried"] for r in per.values())
    n_mal = sum(r["malformed"] for r in per.values())
    n_trc = sum(r["truncated"] for r in per.values())
    n_bunc = sum(r["bunc"] for r in bash.values())
    print(f"  totals: {len(rs)} rounds, {n_cap} carrying a usable files_opened "
          f"capture, {len(rs) - n_cap} unassessable, {n_mal} malformed records, "
          f"{n_trc} truncated targets, {n_unc} reads of un-carried evidence, "
          f"{n_bunc} un-carried Bash/Grep reads")
    n_tcc = sum(r["tc_capture"] for r in bash.values())
    n_tcn = sum(r["tc_null"] for r in bash.values())
    n_tca = sum(r["tc_absent"] for r in bash.values())
    n_tcm = sum(r["tc_malformed"] for r in bash.values())
    n_calls = sum(r["calls"] for r in bash.values())
    n_bt = sum(r["btrunc"] for r in bash.values())
    n_np = sum(r["nopath"] for r in bash.values())
    n_ops = sum(r["operands"] for r in bash.values())
    print(f"  bash/grep half (unit: the tool_call, over the rounds whose "
          f"tool_calls capture is usable):")
    print(f"    {'aspect':12s} {'tc-cap':>7s} {'tc-null':>8s} {'tc-abs':>7s} "
          f"{'tc-mal':>7s} {'calls':>6s} {'trunc':>6s} {'no-path':>8s} "
          f"{'operands':>9s} {'un-carried':>11s}")
    for aid in sorted(bash):
        b = bash[aid]
        print(f"    {aid:12s} {b['tc_capture']:7d} {b['tc_null']:8d} "
              f"{b['tc_absent']:7d} {b['tc_malformed']:7d} {b['calls']:6d} "
              f"{b['btrunc']:6d} {b['nopath']:8d} {b['operands']:9d} "
              f"{b['bunc']:11d}")
    print(f"    totals: {n_tcc} rounds with a usable tool_calls capture, "
          f"{n_calls} Bash/Grep calls, {n_bt} truncated command{s_(n_bt)} "
          f"refused whole, {n_np} call{s_(n_np)} with no extractable path, "
          f"{n_ops} operand{s_(n_ops)} extracted, "
          f"{n_bunc} un-carried Bash/Grep read{s_(n_bunc)} - and "
          f"{n_tca + n_tcn + n_tcm} round{s_(n_tca + n_tcn + n_tcm)} "
          f"(absent {n_tca}, null {n_tcn}, malformed {n_tcm}) unassessable "
          f"on this half, not clean")
    if others:
        print("  un-carried reads by filename (what they named, not folded away):")
        for name, n in sorted(others.items()):
            print(f"    {n:3d}  {name}")
    if leaks:
        print("  UN-CARRIED READS (each makes the prompt wording a scoring event):")
        for ln in leaks:
            print(f"    {ln}")
    if truncs:
        print("  REFUSED-TARGET reads (exactly 200 chars - the length the capture "
              "in field.py stored at until 2026-08-28, so rounds captured before "
              "then may be cut; the tail cannot be vouched for, so the "
              "target is classified as neither carried nor un-carried):")
        for ln in truncs:
            print(f"    {ln}")
    if bleaks:
        print("  UN-CARRIED BASH/GREP READS (each names evidence its pack does "
              "not carry, extracted from the command the record stores):")
        for ln in bleaks:
            print(f"    {ln}")
    if btruncs:
        print("  REFUSED COMMANDS (exactly 200 chars - the same cap the Read "
              "half refuses at; the command tail may hold more operands, so "
              "the whole command is classified as neither carried nor "
              "un-carried):")
        for ln in btruncs:
            print(f"    {ln}")
    return 0


def s_(n: int) -> str:
    """`s` for a plural count, so the totals line stays a sentence."""
    return "" if n == 1 else "s"


def _fixture(root: Path) -> Path:
    """A stored-runs tree whose every census answer is written out beside it."""

    def write(rel: str, rec: dict) -> None:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec))

    def rnd(aid: str, opened, tc=...) -> dict:
        d: dict = {"aspect": aid, "order_seed": 0, "game": "g9_probe"}
        if opened is not ...:
            d["files_opened"] = opened
        if tc is not ...:
            d["tool_calls"] = tc
        return d

    def rd(*targets: str) -> list[dict]:
        """tool_calls holding Read calls only - no Bash half, states intact."""
        return [{"tool": "Read", "target": t} for t in targets]

    P = "/tmp/pack"
    # audio: reads its own bucket plus the housekeeping every judge is handed.
    write("run-a/a.json", rnd("audio", [f"{P}/A/audio.json", f"{P}/A/BRIEF.md",
                                        f"{P}/.claude/skills/sampling-code/SKILL.md"],
                              tc=rd(f"{P}/A/audio.json")))
    # audio again, ALL RELATIVE TARGETS - the shape that classified as `other`
    # and read as a false leak under slash-anchored rules.
    write("run-a/a2.json", rnd("audio", ["A/audio.json", "BRIEF.md",
                                         ".claude/skills/sampling-code/SKILL.md"],
                               tc=rd("A/audio.json")))
    # fun_frames: the discriminating row - one code read inside a frames pack.
    write("run-f/f1.json", rnd("fun_frames", [f"{P}/B/frames/f0.png",
                                              f"{P}/B/frames/f1.png",
                                              f"{P}/B/BRIEF.md",
                                              f"{P}/B/code/sim/01.src"],
                               tc=rd(f"{P}/B/code/sim/01.src")))
    # ux: key present but null. fun: key absent altogether.
    write("run-f/f2.json", rnd("ux", None, tc=None))          # null on BOTH keys
    write("run-f/f3.json", rnd("fun", ...))                   # absent on BOTH keys
    # telemetry read by a frames aspect is carried (fun_frames sees frames only,
    # so this one IS un-carried); fun sees frames+telemetry, so this is not.
    write("run-t/t1.json", rnd("fun", [f"{P}/C/telemetry.json"],
                               tc=rd(f"{P}/C/telemetry.json")))
    write("run-t/t2.json", rnd("fun_frames", [f"{P}/D/telemetry.json"],
                               tc=rd(f"{P}/D/telemetry.json")))
    # A png NOT under frames/ names no known bucket: `other`, never `frames`.
    # o1 carries NO tool_calls: the round whose Bash half is unassessable
    # because the key predates the capture (third value, never clean).
    write("run-o/o1.json", rnd("audio", [f"{P}/E/stills/x.png"]))
    # MALFORMED captures, one per shape no capture ever takes: a dict where
    # the list belongs, and a list holding a non-string. The second mixes a
    # real target with the bad element to pin that a malformed shape is
    # refused WHOLE - the good element must not be classified, and neither
    # shape may abort the walk.
    write("run-m/m1.json", rnd("ux", {}, tc=rd(f"{P}/A/telemetry.json")))
    write("run-m/m2.json", rnd("fun", [f"{P}/C/telemetry.json", None],
                               tc=rd(f"{P}/C/telemetry.json")))
    # THE BASH HALF (task 218). Every call below is one of the shapes the
    # corpus actually stores, and every answer is asserted in selftest() as a
    # literal.
    #
    # b1 (audio): 7 Bash/Grep calls -
    #   find .                -> pack root, always carried
    #   find A/frames -type f -> the frames DIRECTORY of an audio pack:
    #                            UN-CARRIED (the directory branch fires, and
    #                            frames is not in audio's carried set)
    #   cat "$d/telemetry.json" -> a shell expansion: no literal path, so the
    #                            call is a NO-PATH state, classified never
    #   cat A/audio.json      -> carried operand
    #   sed 's/^/  /' A/audio.json -> the sed SCRIPT is skipped (first operand
    #                            of a pattern-first verb), the file classifies
    #   Grep tool "A/audio.json"   -> path-like stored target, carried
    #   Grep tool "spectral"       -> the pattern (no path input), NO-PATH
    write("run-b/b1.json", rnd("audio", [f"{P}/A/audio.json"], tc=[
        {"tool": "Bash", "target": "find . -maxdepth 2 -type d"},
        {"tool": "Bash", "target": "find A/frames -type f"},
        {"tool": "Bash", "target": 'cat "$d/telemetry.json"'},
        {"tool": "Bash", "target": "cat A/audio.json"},
        {"tool": "Bash", "target": "sed 's/^/  /' A/audio.json"},
        {"tool": "Grep", "target": "A/audio.json"},
        {"tool": "Grep", "target": "spectral|centroid"},
    ]))
    # b2 (fun_frames): THE ROW THE TICKET NAMES - a cat of an un-carried path
    # inside a Bash call must land in the new un-carried column (fun_frames
    # carries frames only; code/sim/01.src is not carried). Plus: a carried
    # cat, a 200-char command refused WHOLE under bash-truncated, an echo/ls
    # command with no reading verb (no-path), a Grep tool call carrying a
    # frames operand, and a for-loop over an expansion variable (no-path).
    t200cmd = "find E -type f | sort; echo ---; " + "z" * (200 - 33)
    assert len(t200cmd) == 200
    write("run-b/b2.json", rnd("fun_frames", [], tc=[
        {"tool": "Bash", "target": "cat /tmp/pack/B/code/sim/01.src"},
        {"tool": "Bash", "target": "cat B/frames/f2.png"},
        {"tool": "Bash", "target": t200cmd},
        {"tool": "Bash", "target": "echo hello && ls -la"},
        {"tool": "Grep", "target": "B/frames/f0.png"},
        {"tool": "Bash", "target": 'for d in A B C D E F G H; do find "$d" -type f; done'},
    ]))
    # m3 (fun): tool_calls MALFORMED - an element without a string target is a
    # shape the capture never writes; refused WHOLE (per record), never read
    # as a clean no-Bash round.
    write("run-m/m3.json", rnd("fun", [f"{P}/C/telemetry.json"],
                               tc=[{"tool": "Bash"}]))
    # b4 (fun): a usable files_opened capture and NO tool_calls key - the two
    # keys refuse independently, so this round is captured on the Read half
    # and unassessable on the Bash half.
    write("run-b/b4.json", rnd("fun", [f"{P}/C/telemetry.json"]))
    # TARGETS AT THE CAP LENGTH, TWO IN ONE LIST. field.py's capture stored
    # str(target)[:200] until 2026-08-28 (task 204; it stores the full target
    # since), so a stored target of exactly 200 characters may be a
    # truncation whose tail - the filename - is gone. Stated in advance: each
    # is refused from classification and counted per TARGET under `truncated`,
    # never as a frames read and never as a leak, while the record's good
    # targets still classify - the unit differs from `malformed`, which is per
    # RECORD. Without the rule these targets classify as `other` and read as
    # false un-carried leaks - the direction a latent-null census must not
    # fail in.
    t200 = "/tmp/pack/B/frames/" + "z" * (200 - len("/tmp/pack/B/frames/"))
    t200b = ("/tmp/pack/B/frames/deep/"
             + "y" * (200 - len("/tmp/pack/B/frames/deep/")))
    write("run-l/l1.json", rnd("fun_frames", [t200, t200b,
                                              f"{P}/B/frames/f0.png"],
                               tc=rd(f"{P}/B/frames/f0.png")))
    # Round shapes that must stay out of the population.
    write("run-c/c.json", rnd("architecture", [f"{P}/G/code/sim/01.src"]))  # code
    write("run-x/x.json", {"aspect": "fun"})                                # no seed
    (root / "run-x/notjson.json").write_text("{")
    return root


def selftest() -> int:
    import tempfile
    failures: list[str] = []

    def expect(name: str, cond: bool, detail: str) -> None:
        if not cond:
            failures.append(f"{name}: {detail}")

    # Unit rows first, on the classifier alone - one case per branch, each with
    # its answer stated in advance.
    cases = [
        ("/tmp/p/A/frames/frame_00.png", "frames"),
        ("/tmp/p/A/audio.json", "audio"),
        ("/tmp/p/A/telemetry.json", "telemetry"),
        ("/tmp/p/A/BRIEF.md", "housekeeping"),
        ("/tmp/p/A/SCENE.md", "housekeeping"),
        ("/tmp/p/.claude/skills/sampling-code/SKILL.md", "housekeeping"),
        ("/tmp/p/A/code/sim/01.src", "other"),
        ("/tmp/p/A/stills/x.png", "other"),  # png outside frames/: NOT frames
        # Relative targets classify as their absolute shapes.
        ("BRIEF.md", "housekeeping"),
        ("frames/frame_00.png", "frames"),
        ("A/audio.json", "audio"),
        (".claude/skills/sampling-code/SKILL.md", "housekeeping"),
        # THE DOCUMENTED LIMIT: a target outside the pack that mimics the
        # layout classifies by its shape, because the record carries no pack
        # root. Pinned here as stated, so the limit is a decision rather than
        # an accident.
        ("/elsewhere/pack/B/frames/x.png", "frames"),
        # THE BASH-HALF SHAPES (task 218): operands a Bash command can name
        # and a Read target cannot. The pack root and a bare bucket label are
        # always carried (every pack carries all eight buckets); a path whose
        # last component is the frames DIRECTORY is the frames bucket; the
        # .claude directory itself is housekeeping. A `..` anywhere escapes
        # the pack by shape and is `other`, however much the tail looks like
        # the layout.
        (".", "pack-root"),
        ("./", "pack-root"),
        ("A", "bucket"),
        ("./A", "bucket"),
        ("H", "bucket"),
        ("A/frames", "frames"),
        ("./A/frames", "frames"),
        ("/tmp/pack/B/frames/", "frames"),
        (".claude", "housekeeping"),
        ("/tmp/pack/B/.claude", "housekeeping"),
        ("../A", "other"),
        ("../frames", "other"),
    ]
    for target, want in cases:
        expect(f"named-bucket[{Path(target).name}]", named_bucket(target) == want,
               f"named_bucket({target!r}) returned {named_bucket(target)!r}, "
               f"expected {want!r}")

    # The extractor, on one command shape per branch - every answer a literal.
    # `bash -c` is pinned as the DOCUMENTED LIMIT (one shell level; a nested
    # interpreter is not re-entered), not as an extraction.
    commands = [
        ("cat /tmp/pack/B/code/sim/01.src",
         ["/tmp/pack/B/code/sim/01.src"]),
        ("cat A/audio.json | awk '{print}' | head -3", ["A/audio.json"]),
        ("find . -maxdepth 2 -type d", ["."]),
        ("find A B C -type f", ["A", "B", "C"]),
        ("sed 's/^/  /' A/audio.json", ["A/audio.json"]),
        ("grep -il 'pat' A/audio.json B/audio.json",
         ["A/audio.json", "B/audio.json"]),
        ("grep -e pat A/audio.json", ["A/audio.json"]),
        # PR #98 round 2: the ATTACHED spellings - `-epat`, `-fVALUE`, and the
        # shell-glued `-e's/.../'` - are one token, so the option skip passed
        # them by and the pattern slot ate the FILE after them. The value is
        # the pattern inline: no next-token consumption, the file extracts.
        ("grep -epat A/audio.json", ["A/audio.json"]),
        ("sed -e's/^/  /' A/audio.json", ["A/audio.json"]),
        ("awk -fprog.awk A/audio.json", ["A/audio.json"]),
        # ...while the separate form still consumes its next token as the
        # pattern file, exactly as before.
        ("grep -f pats.txt A/audio.json", ["A/audio.json"]),
        # PR #98 review: -e/-f consume a VALUE only for the pattern-first
        # verbs; for cat/tail/less they are plain options and the file after
        # them is an operand (tail -f of a pack file is a real read shape).
        ("cat -e A/audio.json", ["A/audio.json"]),
        ("tail -f A/audio.json | head -5", ["A/audio.json"]),
        # PR #98 review: an append or combined redirect (>>, 2>>) is a write
        # target exactly like >, and its target is not a read operand.
        ("cat A/audio.json >> log.txt", ["A/audio.json"]),
        ("wc -l A/audio.json 2>> err.txt", ["A/audio.json"]),
        # ...but a quoted > inside a pattern argument is data, not a redirect.
        ('grep "a>b" A/audio.json', ["A/audio.json"]),
        ("cat < A/audio.json", ["A/audio.json"]),
        # BOTH from the stored corpus, where the pre-fix extractor itemised
        # each as an un-carried read - the two false positives that had to be
        # adjudicated before the corpus 0 could stand:
        #   g4_platformer__ux__seed0__rep3 - the punctuation `<(` of a process
        #   substitution read as the redirected file; the substitution's own
        #   operand A/frames IS extracted and classifies carried for ux.
        #   g2_tetris3d__fun_frames__seed0__rep5 - the find expression VALUE
        #   `brief.md` extracted as a path operand.
        ("wc -l < <(ls A/frames)", ["A/frames"]),
        ('find . -iname "BRIEF.md" -o -iname "brief.md"; echo ---; ls -la .',
         ["."]),
        ("find . -name '*.png' | sort", ["."]),
        ("find . -type f | head -100", ["."]),
        ("cd /tmp/pack && cat BRIEF.md", ["BRIEF.md"]),
        ("grep -r secret /etc/passwd", ["/etc/passwd"]),
        # No extractable path - the shapes that land a call in `no-path`:
        ('cat "$d/telemetry.json"', []),          # shell expansion
        ("wc -l */audio.json", []),               # glob, no literal path
        ("grep -v /frames/", []),                 # pattern operand, not a path
        ("echo hello && ls -la", []),             # no reading verb
        ("python3 analyze.py", []),               # not a reading verb
        ('for d in A B C; do find "$d" -type f; done', []),   # expansion in loop
        ("bash -c 'cat /etc/shadow'", []),        # nested shell: THE LIMIT
        # TASK 222: the newline is a segment separator on the MAIN tokeniser
        # path too, exactly as the ValueError fallback already treats it.
        # The demonstrated defect: before the fix shlex consumed a newline
        # between two commands as whitespace, both arrived as ONE segment, and
        # the sed SCRIPT `s/x/y/` extracted as a path operand - which
        # named_bucket classifies as `other`, i.e. a PHANTOM UN-CARRIED LEAK,
        # the false-positive direction named_bucket's own docstring forbids.
        # Pinned beside its semicolon control, both answers literal:
        ("cat A/audio.json\nsed 's/x/y/' B/audio.json",
         ["A/audio.json", "B/audio.json"]),
        ("cat A/audio.json;sed 's/x/y/' B/audio.json",
         ["A/audio.json", "B/audio.json"]),
        # ...and the other half of the same property, which the repair must
        # not break: a newline INSIDE quotes is DATA, not a separator. The
        # ValueError fallback's blind `replace("\n", ";")` would read the
        # first of these back as a DIFFERENT token (`A/new;line.json`);
        # quoted operands keep their newline, and a quoted pattern is still
        # the pattern slot, never a path.
        ("cat 'A/new\nline.json'", ["A/new\nline.json"]),
        ("grep 'foo\nbar' A/audio.json", ["A/audio.json"]),
    ]
    for command, want in commands:
        got = bash_operand_paths(command)
        expect(f"extract[{command[:32]}]", got == want,
               f"bash_operand_paths({command!r}) returned {got!r}, "
               f"expected {want!r}")

    with tempfile.TemporaryDirectory() as td:
        root = _fixture(Path(td))
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = census(root)
        out = buf.getvalue()
        expect("selftest-census-runs", rc == 0, f"census returned {rc}: {out}")
        # Stated in advance: 15 population rounds. THE READ HALF - audio: 4
        # rounds, all capture, 1 un-carried (the png outside frames/ - an
        # audio pack carries no such file, wherever it was read from); the
        # relative-target round is carried throughout. fun: 3 captures
        # (telemetry is carried) + 1 key-absent + 1 malformed RECORD (a list
        # holding a non-string). fun_frames: 4 captures, 2 un-carried (the
        # .src read and the telemetry read - frames-only carries neither) and
        # 2 truncated TARGETS (exactly 200 chars - the length the capture
        # stored at until 2026-08-28, so never classified; the count is per
        # target, and the good frames read in the same list still classifies).
        # ux: 1 key-stored-null + 1 malformed RECORD (a dict where the list
        # belongs). Everything else is housekeeping. THE BASH HALF is the
        # last column: un-carried operands only.
        want_rows = {"audio": (4, 4, 0, 0, 1, 0, 0, 1),
                     "fun": (5, 3, 0, 1, 0, 1, 0, 0),
                     "fun_frames": (4, 4, 0, 0, 2, 0, 2, 1),
                     "ux": (2, 0, 1, 0, 0, 1, 0, 0)}
        for aid, (n, cap, null, absent, unc, mal, trc, bunc) in want_rows.items():
            hit = next((ln for ln in out.splitlines() if ln.split()[:1] == [aid]),
                       "")
            got = tuple(int(v) for v in hit.split()[1:9]) if hit else ()
            expect(f"fixture-row[{aid}]",
                   got == (n, cap, null, absent, unc, mal, trc, bunc),
                   f"the {aid} row reads {got}, expected "
                   f"{(n, cap, null, absent, unc, mal, trc, bunc)}\n{out}")
        expect("fixture-malformed-total",
               "2 malformed records" in out,
               f"the totals line must name the malformed captures it refused "
               f"whole - the unit is the record:\n{out}")
        expect("fixture-truncated-total",
               "2 truncated targets" in out,
               f"the totals line must count truncated targets per target, not "
               f"per record - two in one list are two:\n{out}")
        expect("fixture-truncated-reported",
               "l1.json: /tmp/pack/B/frames/" in out,
               f"the 200-char target must be itemised in full under the round "
               f"that stored it, refused from classification rather than read "
               f"as a frames read or as a leak:\n{out}")
        expect("fixture-un-carried-total",
               "3 reads of un-carried evidence" in out,
               f"the un-carried total line is wrong:\n{out}")
        expect("fixture-other-reported",
               "stills/x.png" in out,
               f"a png outside frames/ must appear in the un-carried itemisation "
               f"under the name it carried, never counted as a frames read:\n{out}")
        # THE BASH HALF, table 2, stated per aspect:
        # (tc-capture, tc-null, tc-absent, tc-malformed,
        #  calls, bash-truncated, no-path, operands, un-carried)
        want_bash = {"audio": (3, 0, 1, 0, 7, 0, 2, 5, 1),
                     "fun": (2, 0, 2, 1, 0, 0, 0, 0, 0),
                     "fun_frames": (4, 0, 0, 0, 6, 1, 2, 3, 1),
                     "ux": (1, 1, 0, 0, 0, 0, 0, 0, 0)}
        for aid, want in want_bash.items():
            hit = next((ln for ln in out.splitlines()
                        if ln.startswith(f"    {aid} ")), "")
            got = tuple(int(v) for v in hit.split()[1:10]) if hit else ()
            expect(f"fixture-bash-row[{aid}]", got == want,
                   f"the {aid} bash row reads {got}, expected {want}\n{out}")
        expect("fixture-bash-ticket-row",
               "b2.json: /tmp/pack/B/code/sim/01.src" in out,
               f"THE ROW THE TICKET NAMES: a cat of an un-carried path inside "
               f"a Bash call must land in the new un-carried column and be "
               f"itemised with the command that named it:\n{out}")
        expect("fixture-bash-frames-dir-row",
               "b1.json: A/frames" in out,
               f"the frames DIRECTORY of an audio pack is un-carried - the "
               f"directory branch must fire and the leak be itemised:\n{out}")
        expect("fixture-bash-truncated-total",
               "1 truncated command" in out,
               f"the bash totals must count truncated COMMANDS per command, "
               f"refused whole:\n{out}")
        expect("fixture-bash-nopath-total",
               "4 calls with no extractable path" in out,
               f"no-path is a STATE, never a silent drop - the totals must "
               f"count it:\n{out}")
        expect("fixture-bash-uncarried-total",
               "2 un-carried Bash/Grep reads" in out,
               f"the bash un-carried total line is wrong:\n{out}")
        expect("fixture-bash-unassessable-named",
               "unassessable" in out and "not clean" in out,
               f"rounds whose tool_calls is absent, null or malformed must be "
               f"named unassessable on the Bash half, never folded into "
               f"clean:\n{out}")

    if failures:
        print(f"PROMPT CAPTURE CENSUS SELFTEST: {len(failures)} unmet\n")
        for f in failures:
            print(f"  FAIL {f}")
        return 1
    print("PROMPT CAPTURE CENSUS SELFTEST: the classifier answers every branch "
          "as stated, and the fixture rows - including the code-read leak and "
          "the png outside frames/ - come back exactly as written.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs-root", type=Path, metavar="RUNS_ROOT",
                    help="the MAIN checkout's eval/runs - a worktree's is "
                         "gitignored and empty, which reads as UNMEASURED.")
    ap.add_argument("--selftest", action="store_true",
                    help="run the fixture tree instead of the corpus")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(selftest())
    if not args.runs_root:
        ap.error("--runs-root is required (or --selftest)")
    raise SystemExit(census(args.runs_root))
