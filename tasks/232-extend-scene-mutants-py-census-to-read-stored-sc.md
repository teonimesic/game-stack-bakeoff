---
id: 232
title: Extend scene_mutants.py --census to read stored scene gradings when --runs-root is passed
status: done
priority: 3
refs: eval/judge/scene_mutants.py,eval/judge/scene_probe.py,eval/SCENES.md,eval/RUNS.md,tasks/162
done_when: scene_mutants.py --census --runs-root <main checkout>/eval/runs reports, beside the fixture tables, a per-criterion count over every stored scene grading it can read (1 today), naming each file and refusing unreadable records fail-closed; the fixture/stored populations stay visually separate in the output; a mutant or variant proving the extension can go red is added alongside, per the mutant-and-variant rule.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/111
established_by: 'PR #111 squash-merged as 22e7b9a; CI green at head a672527 (gates 3m28s, controls 20m42s incl. all scene_mutants suites, CodeRabbit round clean after round-3 doc fixes; 7 review threads across 3 rounds all acted-on and resolved). On merged main: --census-selftest 30/30 expectations met; --census --runs-root eval/runs reads the real corpus - 1 stored s1_parallax grading (wg-scene-s1ts-2026-08-25 t0, 5/6 scored 0.833), 0 refusals, fixture and stored populations under separate banners.'
---

The tool asks for this itself: pass 54 ran `scene_mutants.py --census --runs-root eval/runs` (2026-09-02) and it found the 1 stored scene grading at eval/runs/wg-scene-s1ts-2026-08-25/artifacts/s1_parallax__ts__t0/eval/playbot.json and printed 'Extend this census to read them rather than reporting the fixture population as if it were the corpus.' Today the census answers whether a criterion CAN take both values on fixtures, and says so - which is correct - but every new scene submission widens the gap between what the fixtures show and what the corpus shows, and nothing mechanised reads the stored gradings the way tier1_census.py and tier2_census.py read the game corpus. The instrument's own docstring says scene results are read against 'scene_mutants.py --census' until thresholds stop being fixture-chosen (eval/SCENES.md); that sentence needs a census that can see submissions. The playbot.json schema to read: tier=scene_probe, criteria[] with id/passed/scored, unscored{} with reasons, score, usable. Reuse the refusal discipline of audio_regrade_census.py --triggered: refuse a record that does not carry exactly the expected shape rather than guessing.
