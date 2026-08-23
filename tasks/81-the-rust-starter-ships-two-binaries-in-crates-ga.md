---
id: 81
title: The Rust starter ships two binaries in crates/game with no default-run, so just run is ambiguous on a pristine tree
status: open
priority: 3
refs: 'eval/FINDINGS.md #98, eval/tools/disclosure.py, eval/starters/rust/justfile:152, eval/starters/rust/crates/game/Cargo.toml'
done_when: either cargo run -p game --release has been observed on a pristine copy of eval/starters/rust and the observed behaviour recorded (ambiguous-binary error, or it runs), and if ambiguous the starter repaired with the regime boundary recorded in eval/RUNS.md and verify_blind.py plus starter_parity.py re-run; or the decision to leave it is recorded with the reason
---

Four independent Rust agents across three runs (wg-matrix pong t1, wg-matrix tetris3d t1, wg-matrix arena t1, wg-audio48 tetris3d t1) wrote in their closing messages that just run was broken in the starter baseline because crates/game ships two binaries and cargo run -p game was ambiguous; two of them added default-run themselves. Surfaced by eval/tools/disclosure.py on its first pass over the stored corpus - the reader that tasks/71 built. NOT yet reproduced by running cargo: the manifest has no default-run and the crate has src/main.rs plus src/bin/film.rs, which is the documented cargo condition for the error, but nobody has executed the recipe. just run is not a graded criterion (RUNS.md records it as REFUSED under the harness for this stack), so the cost is turns and money inside a trial, not a score - the same shape as FINDINGS 98, which cost no published number either.
