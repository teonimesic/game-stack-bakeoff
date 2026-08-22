#!/usr/bin/env bash
# Wait for run 1 to finish, archive it as the byte-identical-prompt baseline,
# then re-run all four stacks with the stack-native prompts.
set -u
cd "$(dirname "$0")"
until ! pgrep -f run-bakeoff.sh >/dev/null; do sleep 20; done
mkdir -p runs/archive-run1-byte-identical-prompts
for d in runs/bakeoff-*2026-08-11*/; do mv "$d" runs/archive-run1-byte-identical-prompts/ 2>/dev/null; done
cp runs/bakeoff.log runs/archive-run1-byte-identical-prompts/bakeoff.log 2>/dev/null
cat > runs/archive-run1-byte-identical-prompts/README.md <<'MD'
# Run 1 — byte-identical prompts (SUPERSEDED, kept for comparison)

Every stack received the SAME prompt text, which read "a public Bevy resource
`RallyLength(pub u32)` defined in `crates/sim`". That gave Rust a prompt in its
own vocabulary and made TypeScript, Unity and Godot translate Bevy nouns, Rust
paths and a Rust integer type into their own languages.

It also caused a real failure: `u32` has no C# equivalent, one Unity agent chose
`int`, and the held-out test asserted `0u` — NUnit reported the type mismatch as
"Expected: 0, But was: 0". That measured the prompt's ambiguity, not Unity.

Results here are still informative for cost/turns/wall-clock, and for the
self-verify-red pattern. Do not read the pass rates as a stack comparison.
MD
echo "═══ archived run 1; starting run 2 with stack-native prompts $(date +%T) ═══"
> runs/bakeoff.log
./run-bakeoff.sh >> runs/bakeoff.log 2>&1
