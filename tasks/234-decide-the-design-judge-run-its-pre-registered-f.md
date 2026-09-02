---
id: 234
title: 'Decide the design judge: run its pre-registered falsification or retire it'
status: todo
priority: 3
refs: 'IMPROVEMENTS.md (root, iteration 2), eval/judge/judge_design.py, eval/judge/design_criteria.py, eval/judge/RUBRIC.md, #21, #55, eval/tools/tokenvalue.py'
done_when: 'EITHER the falsification runs: the tuned-vs-detuned fixture pair judged (a handful of calls, tokval-priced, the cheapest model the module already pins), run-to-run spread on identical input measured separately from the tuned-detuned gap per the iteration''s ''Also required'', and the result recorded in root IMPROVEMENTS.md and DECISIONS.md with the falsifier''s verdict stated either way. OR the module is retired, with a DECISIONS.md row that names its ground honestly - supersession by the aspect tier (fun/fun_frames carry the aesthetics question) is a valid ground, but say that is what happened; the iteration''s own falsifier demands the measurement only if the instrument is to SHIP, not if it is withdrawn. Either way the iteration''s status line stops being false.'
---

judge_design.py and design_criteria.py are original equipment (imported with the repo, a3d0fd1), built exactly to root IMPROVEMENTS.md's iteration-2 spec (frames + telemetry, no source, anchored 0-4, no weight until tuned-vs-detuned separation exceeds run-to-run spread), they price their calls through tokenvalue.py's PRODUCERS - and they have NEVER RUN: no stored round, no doc, no decision names them (swept 2026-09-02). The archive iteration still reads 'not yet built', which is now false in the other direction. The instrument is a live question nobody can see.
