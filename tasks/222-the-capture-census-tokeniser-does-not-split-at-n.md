---
id: 222
title: The capture census tokeniser does not split at newlines, and its docstring says it does
status: todo
priority: 4
refs: eval/judge/prompt_capture_census.py,tasks/218
done_when: 'The main tokeniser path treats newline as a segment separator exactly as the fallback path already does (one-line change in _tokenise or _segments - not a second mechanism), the demonstrated command and its semicolon control are pinned as selftest rows with both answers stated as literals, python3 eval/judge/prompt_capture_census.py --selftest exits 0, the live census over eval/runs still reproduces the pre-registered figures (468 calls, 31 refused, 337 no-path, 179 operands, 0 un-carried on both halves), and the docstring''s split claim matches the code either way. Do NOT conclude anything stored was misclassified: 0 population commands fire the shape, so no published number moves.'
---

eval/judge/prompt_capture_census.py's Bash-half extractor bash_operand_paths documents: split into simple commands at ;, |, &&, || AND NEWLINES. The ValueError fallback path implements the newline split (it replaces newlines with semicolons before splitting); the main shlex path does not - shlex emits no token for a newline (whitespace), so newline-joined commands arrive at _segments as ONE segment. Demonstrated in-process: bash_operand_paths of cat A/audio.json NEWLINE sed 's/x/y/' B/audio.json returns A/audio.json, s/x/y/, B/audio.json - the sed SCRIPT extracted as a path operand, which named_bucket classifies as other, i.e. a PHANTOM UN-CARRIED LEAK; the semicolon control returns A/audio.json, B/audio.json. The failure direction is the one named_bucket's own docstring forbids: a false positive shaped like a finding, moving the 2026-08-28 pre-registration's 0. The file has repaired this family twice already (the <( process substitution and the find expression value, both adjudicated corpus false positives, both pinned as selftest rows) - this is the third member, found before it fired. MEASURED 2026-08-30: within the census's population (57 non-code rounds, 437 usable Bash calls) 3 commands hold newlines and 0 collapse to the defective shape - every published figure stands today, including the pre-registered 0. Corpus-wide including code-seeing rounds outside the population: 1,833 usable Bash calls, 27 hold newlines, 3 collapse to one segment with a pattern-first verb present (all three in idiomatic rounds, all extracting nothing because their scripts sit in non-extractable positions). The trigger shape is data the project holds; the population just has not drawn it yet.

## Reproduction (2026-08-30, in-process, no stored data touched)

```python
import sys; sys.path.insert(0, "eval/judge")
from prompt_capture_census import bash_operand_paths, _tokenise, _segments

cmd = "cat A/audio.json\nsed 's/x/y/' B/audio.json"
_tokenise(cmd)   # ['cat', 'A/audio.json', 'sed', 's/x/y/', 'B/audio.json'] - ONE token stream, no separator
_segments(_tokenise(cmd))  # 1 segment; the same command with ';' yields 2
bash_operand_paths(cmd)    # ['A/audio.json', 's/x/y/', 'B/audio.json']  <- phantom
bash_operand_paths(cmd.replace("\n", ";"))  # ['A/audio.json', 'B/audio.json']  <- control
```

`s/x/y/` classifies through `named_bucket` as `other` and would be itemised as an
un-carried read attributed to the round that stored the command. The phantom is visible
in the itemisation, not silent — but the pre-registration's headline figure is the count
itself, and a phantom moves it. This is why it is a defect rather than a cosmetic note:
`named_bucket`'s docstring states the standard the census must not fail in — "a false
positive shaped like a finding, which is the direction a latent-null census must not
fail in" — and the two corpus false positives already repaired here (`wc -l < <(ls
A/frames)`, `find . -iname "brief.md"`) were fixed and pinned under exactly that
standard.

## Why the main path misses it

`shlex.shlex(punctuation_chars=True)` treats `\n` as whitespace, and
`whitespace_split` never emits a whitespace-only token — so a newline between two
commands leaves no separator token for `_segments` to split at. The `ValueError`
fallback path (unbalanced quotes) replaces `\n` with `;` before splitting, so the two
tokeniser paths DISAGREE about the same command: the fallback classifies it correctly,
the common (balanced-quote) path does not.

## Scope notes

- `_segment_reads` is not the defect — given a correct segment split it already
  honours the pattern slot. The repair belongs at the separator, not the segment walk.
- The census's own population cannot fire the shape today (measured above); the
  repair is about the channel and the docstring/code disagreement, not about any
  stored round.
- If the repair is made in `_tokenise` by translating `\n` to `;` before lexing,
  check the quoted-newline case first: a newline inside quotes is DATA, not a
  separator, and the fallback's blind replace would corrupt it. The right shape is
  whichever preserves quoted newlines while splitting unquoted ones — pin both.
