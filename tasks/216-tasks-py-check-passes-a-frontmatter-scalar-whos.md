---
id: 216
title: tasks.py check passes a frontmatter scalar that parses shorter than the line wrote it - a space-hash in an unquoted scalar silently truncates the parsed value
status: in_testing
priority: 5
refs: eval/tools/tasks.py, tasks/214-drive-appends-audio-triggered-after-a-lock-confli.md
done_when: 'tasks.py check exits nonzero on a fixture whose unquoted title or done_when scalar contains " #" - the lossy-parse property, stated as the raw line versus the parsed value rather than as a character vocabulary - while the four real rows where a hash follows a NON-whitespace character (tasks/174 refs ",#189", tasks/181 title "(#NN)" and done_when "[#NN]", tasks/187 refs ",#188") stay green, and the repaired tasks/214 title (single-quoted, full text, parses whole) stays green.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/95
established_by: 'tasks_control direction 12 pins both ways: check exit 1 on the real 214 blob 1703566 and on a lossy done_when, exit 0 on the four census greens plus the repaired title; 129 measurements, 0 FAILED, 0 NOT CHECKED; lossy_never_checked CAUGHT 2 red of 129, lossy_by_vocabulary CAUGHT 7 red of 129, full suite 37 mutants 0 survived; live census clean; PR 95 gates+controls+review all green at 35d2671, review round 2 returned 0 comments'
---

Measured on tasks/214, today: its title was written as an unquoted YAML scalar ending
"...unusable, so the #25 exclusion does not reach the one criterion added outside
unusable_criteria". In YAML, ` #` (whitespace before the hash) starts a comment in a
plain scalar, so the PARSED title has been "drive() appends audio.triggered after a
lock-conflict unusable, so the" since the ticket was created (commit 1703566) — through
`tasks.py check` reporting all well-formed, through the queue listing, through the
agent's in_review status write. The file always held the full text; only the parsed
value lost it. `tasks.py show` displays the parsed value, so the visible queue said the
shorter title while the on-disk bytes said the longer one — a reader who greps the file
and a reader who trusts the queue disagree, and nothing flags it.

The bite reaches the field that matters most: a `done_when` containing " #" — e.g.
"done when docstat --findings names #214" — would truncate the done CONDITION at
exactly the citation. Both writers to these files can produce the shape: hand-authored
frontmatter (the 214 case) and the agents' status-write path, which rewrote 214's
done_when unquoted (that value happens to contain no space-hash, so it parsed whole).

**Census, 2026-08-29, over all 214 ticket files:** the only lossy scalar is tasks/214's
title. Three other tickets hold hashes in unquoted frontmatter scalars and parse
correctly, because the hash follows a non-whitespace character — tasks/174 refs
",#189", tasks/181 title "(#NN)" and done_when "[#NN]", tasks/187 refs ",#188". Those
four rows are the green controls a fix must not redden.

**Model for the fix:** a check whose trigger is the PROPERTY, not a vocabulary — a
frontmatter scalar whose parsed value is a strict prefix of (or otherwise shorter than)
the raw text the line carries. That is closed-class: re-serialise or substring-test the
parsed scalar against the raw line, and red on loss. Do not attempt to enumerate
YAML's comment-starting contexts; the property is decidable without them. The natural
home is `tasks.py check`, which already owns well-formedness, with the tasks/214
pre-repair line as the red fixture and the four census rows above as greens.

**What NOT to conclude:** nothing in the stored queue was acted on wrongly — 214's tail
was prose naming the finding, and the ticket's body carried the full statement
throughout. The agent's in_review write did not cause this (its truncated-looking line
parses to the same value the original line did); it only made the display visible
enough to chase.

## note 2026-08-29

Two lessons from the run, for the next agent on this file:

- The control suite went green locally while CI's round-trip row went red on THIS ticket. The two runs read different copies of the same file: `tasks_control.py` resolves the queue to the MAIN checkout (which my `review` write had already normalised through `_render`), while CI reads the BRANCH's committed copy, which I had hand-authored with a single-quoted title that `_render` renders plain. A local green never covered the bytes the gate actually reads. Check the round-trip on the copy your branch commits, not on the main checkout's live copy.

- Review found the predicate firing on `refs: ['one'] # note`: a YAML collection loses nothing, but `_parse` stringifies collections through `_scalar`, so the string "['one']" is a strict prefix of the carrier line and the first version read that as loss. The fix reads raw `yaml.safe_load` types and skips list/dict; pinned by a new direction-12 row in `tasks_control.py`.
