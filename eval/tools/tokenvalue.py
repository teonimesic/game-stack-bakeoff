#!/usr/bin/env python3
"""The one name, and the one format, for the quantity every producer here used to call `$`.

    python3 tools/tokenvalue.py --selftest

`agent.cost_usd`, `field_cost_usd`, `charged_to_ceiling_usd`, `measured_cost_usd` and the
judges' `cost_usd` are all the same quantity: **the list price the tokens a call used would
carry at published API rates**. The CLI computes it as `sum(modelUsage[*].costUSD)` from the
token counts, and it computes it that way whatever the billing arrangement. This account is a
subscription, so none of it is an expenditure (#159).

The token counts underneath are real and every comparison built on them stands. What was wrong
was the unit and the noun: a `$` in front of the figure claims money moved, and a decision was
declined on one.

**So the sigil is the defect, not the number.** `$27.68` cannot be read as anything but money;
`27.68 tokval` cannot be read as money at all, and it is the same measurement. Every producer
formats through here so there is one spelling to change if the account ever moves to per-token
billing — at which point the figures become real and `$` becomes correct again.

`--selftest` pins the format in both directions and greps the producers, because a shared
formatter nobody calls is a rename that did not happen.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import string
import sys

#: The unit. Short enough for a table header, and it is not a currency.
UNIT = "tokval"

#: What the unit means, for a producer to print once per report. One sentence, because a
#: legend nobody reads is a legend that does not travel with the number.
DEFINITION = (
    f"{UNIT} = list-price valuation of the tokens a call used "
    f"(sum of modelUsage[*].costUSD, at published API rates). "
    f"The account is a subscription: no {UNIT} figure is an expenditure (FINDINGS #159)."
)

#: The nouns that assert money moved. A producer must not print any of them beside a
#: figure, and `_producer_problems` greps for them. CLOSED CLASS on purpose - `cost` is
#: not in it, because `cost_usd` is a stored field name and renaming stored keys would
#: invalidate every artifact on disk. The FIELD keeps its name; the LABEL changes.
EXPENDITURE_WORDS = ("spend", "spent", "spends", "spending", "charged", "charges",
                     "charging", "bill", "billed", "billing", "expenditure")


def fmt(value: float | int | None, decimals: int = 2, width: int = 0) -> str:
    """The bare number, right-aligned to `width`. No sigil, ever.

    `None` renders as `n/a` rather than `0.00`: a figure that was never measured and a
    figure measured as zero are different, and `|| echo 0` is the shape AGENTS.md rule 3
    forbids by name.
    """
    if value is None:
        return f"{'n/a':>{width}}" if width else "n/a"
    return f"{float(value):>{width}.{decimals}f}" if width else f"{float(value):.{decimals}f}"


def tag(value: float | int | None, decimals: int = 2) -> str:
    """`27.68 tokval` - the figure carrying its unit, for prose and one-off lines."""
    return f"{fmt(value, decimals)} {UNIT}"


def total(value: float | int | None, decimals: int = 2) -> str:
    """`27.68 tokval` with the definition appended - for the last line of a report."""
    return f"{tag(value, decimals)}\n({DEFINITION})"


# --------------------------------------------------------------------------- selftest

#: Every module that prints one of these figures to a person. THE ADDRESS IS AN INPUT TO
#: THE CHECK (AGENTS.md rule 12): a producer missing from this list is a producer nothing
#: asks about, so `_producer_problems` fails when a path does not exist rather than
#: skipping it, and `--selftest` re-derives the list from the tree and reports any module
#: that formats a `*_usd` value and is not named here.
PRODUCERS = (
    "tools/census.py",
    "tools/cost_census.py",
    "tools/runstat.py",
    "judge/judge_ledger.py",
    "judge/field_sweep.py",
    "judge/pairwise_run.py",
    "judge/judge_design.py",
    "wholegame.py",
    "runner.py",
    "instrfollow/run.py",
    "tools/hook_audit_control.py",
)

EVAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: The names this project renders as a token valuation. A module that interpolates one of
#: these into a string is a producer.
_VALUE = re.compile(r"cost_usd|costUSD|_usd\b|\bspent\b")

#: The conversion characters a `%` format can end on, and `MONEY_PERCENT` must accept the
#: same set. `i` is here because `"%i" % n` is valid Python and was in neither; discovery
#: asking about a smaller set than the sigil check is how a module gets found by one and
#: passed by the other.
_CONV = r"[fgdeisu]"

#: This module's own renderers. A module that calls one of them is a producer whether or
#: not it ever names a `*_usd` field.
_RENDERERS = frozenset({"fmt", "tag", "total"})
_PCT = re.compile(rf"%(?:\([^)]*\))?[-+ #0-9.*]*{_CONV}", re.I)

#: `%%` is an escaped percent sign and introduces nothing. It comes out of a literal before
#: anything looks for a conversion or a mapping key, or the template `"%%(cost_usd)s"` -
#: which renders that text and nothing else - reads as a reference to the field it prints.
_ESCAPED_PCT = re.compile(r"%%")

#: The NAME inside a `%(name)s` mapping key. Read out of a format literal AFTER the escaped
#: percents are gone; never the literal as a whole, which would fire on any string that
#: merely mentions one of these fields in prose.
_MAP_KEY = re.compile(r"%\(([^)]+)\)")


#: A `$` immediately in front of an interpolation or a digit, inside an f-string. This is
#: what a money label looks like and what no producer may contain. `$TMPDIR`, `${VAR}` and
#: a shell prompt `$ ` are not matched: the class is `$` followed by `{` + a Python
#: expression, or `$` followed by a digit.
MONEY_SIGIL = re.compile(r"\$\{[a-z_]", re.I)
MONEY_LITERAL = re.compile(r"\$\d")
#: The same sigil in the two non-f-string forms. `"$%.2f" % spent` and `"${:.2f}".format(x)`
#: are money labels that `MONEY_LITERAL` cannot see - `$` there is followed by `%` or `{:`,
#: never by a digit. Discovery and the sigil check have to know the same 3 forms, or a
#: module found by one passes the other.
MONEY_PERCENT = re.compile(rf"\$%[-+ #0-9.*]*{_CONV}"
                           r"|\$\{[^A-Za-z{}\n][^{}\n]{0,10}\}", re.I)

#: A `$` that is NOT a money label: a shell variable a producer legitimately quotes, or a
#: GitHub Actions `${{ ... }}` template.
#:
#: THIS BLANKS A SPAN. IT USED TO SKIP THE LINE, AND THAT WAS FAIL-OPEN IN MY OWN CHECK.
#: The old pattern ended in `|\{`, so `$` followed by `{` matched it — and every line
#: holding `${` was skipped before any money regex ran. Measured: `print(f"${spent:.2f}")`
#: is a money sigil `MONEY_SIGIL` matches, and the guard skipped the line so it was never
#: asked. A guard that excuses a whole line excuses everything else on it, which is rule 7:
#: every reason not to count a failure is a channel a bug can widen.
#: The names a producer legitimately quotes from the shell.
_SHELL_NAMES = r"TMPDIR|CLAUDE_PROJECT_DIR|STARTER_HOOK_LOG|PATH|HOME|schema"

#: THE BRACED AND UNBRACED FORMS ARE SEPARATE ALTERNATIVES, and that is the whole point.
#: One pattern with an optional `{` had to end in `[^}\n]*\}?` to reach the closing brace,
#: and on an UNBRACED variable that trailing class ran to the end of the line — so
#: `log("$TMPDIR then $27.68")` blanked the sigil along with the variable. Same fail-open
#: as the whole-line skip this replaced, one revision later, in the same guard.
_SHELL_VAR = re.compile(
    r"\$\{\{[^\n]*?\}\}"                       # ${{ ... }}, a GitHub Actions template
    rf"|\$\{{(?:{_SHELL_NAMES})[^}}\n]*\}}"      # ${NAME...}, braced: stop at the brace
    rf"|\$(?:{_SHELL_NAMES})\b")                 # $NAME, unbraced: stop at the name


def _blank_shell_vars(line: str) -> str:
    """The line with its shell-variable spans replaced by a space."""
    return _SHELL_VAR.sub(" ", line)


def money_sigil_in(line: str) -> bool:
    """Does this source line carry a money label, in any of the 3 forms?

    THE ONE CODE PATH. `_producer_problems` calls this and the pins call this, so a pin
    that is green is a statement about what the sweep actually does — not about a second
    copy of the rule that happens to agree with it today.
    """
    text = _blank_shell_vars(line)
    return bool(MONEY_SIGIL.search(text) or MONEY_LITERAL.search(text)
                or MONEY_PERCENT.search(text))


def _producer_problems() -> list[str]:
    """Does any producer still format a figure with a money sigil? Reads the sources."""
    problems = []
    for rel in PRODUCERS:
        path = os.path.join(EVAL, rel)
        if not os.path.exists(path):
            problems.append(f"{rel}: named in PRODUCERS and not on disk. The address is "
                            f"an input to the check - fix the list or the path.")
            continue
        for i, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
            if money_sigil_in(line):
                problems.append(f"{rel}:{i}: money sigil in a producer: {line.strip()[:100]}")
    return problems


#: How a module can render one of these figures. THREE FORMS, because the first version
#: knew only f-strings — so `print("$%.2f" % cost_usd)` in an unlisted module was invisible
#: to discovery, never read by `_producer_problems`, and `--selftest` stayed green. That is
#: the variant direction: not "can the check fail?" but "can it still pass on input it
#: mishandles?" Python has exactly these three ways to interpolate into a string, so this is
#: a closed class rather than a list of the shapes anyone happened to write.
def _field_names(literal: str) -> list[str]:
    """Replacement field names in a `str.format` template.

    `string.Formatter` is the parser `str.format` itself uses, so `{{cost_usd}}` comes back
    as literal TEXT rather than as a field - which is what it is. A regex over braces cannot
    make that distinction, and reported `"{{cost_usd}}".format()` as a producer.
    """
    try:
        return [f for _, f, _, _ in string.Formatter().parse(literal) if f]
    except ValueError:
        return []           # an unparseable template renders nothing


def _references(nodes: list) -> str:
    """The unparsed expressions among `nodes`, WITHOUT literal constants.

    A CONSTANT IS DATA, NOT A REFERENCE. `"{value}".format(value="cost_usd")` renders the
    string `cost_usd`; it does not render a token valuation, and unparsing the keyword value
    made it look like one. That is the false-positive direction, and a gate that fires on
    correct input is a gate that gets disabled.
    """
    return " ".join(ast.unparse(nd) for nd in nodes
                    if not isinstance(nd, ast.Constant))


def formats_a_value(text: str) -> bool:
    """Does this source render one of these figures into a string?

    **THIS PARSES, IT DOES NOT MATCH.** Three regex attempts at the same question each
    missed a form that is ordinary Python, and each miss was silent: `fr"..."` and `F"..."`
    were invisible because the prefix was written as a literal `f`; `f"it's {cost_usd}"`
    was invisible because the pattern scanned to the next quote of either kind and the
    apostrophe ended it first. Every one of those is a module that never reaches
    `PRODUCERS`, is never read by `_producer_problems`, and leaves `--selftest` green.

    Then the repairs began missing in the OTHER direction, which is worse: `{{cost_usd}}` is
    an escaped brace, `%%(cost_usd)s` is an escaped percent, and `.format(value="cost_usd")`
    renders a string that happens to spell the field. All three are templates that render no
    valuation at all, and requiring their modules in `PRODUCERS` would turn the gate red on
    correct input.

    So each construct is read by the parser that owns it: `ast` for the expressions, and
    `string.Formatter` - the one `str.format` itself uses - for a `.format` template. The
    value name is looked for in interpolated EXPRESSIONS and in real FIELD NAMES, never in
    literal text and never in a constant.

    Raises `SyntaxError` on source that does not parse. A file this cannot read is a file
    nothing has cleared, and the caller reports it rather than skipping it.
    """
    tree = ast.parse(text)
    for node in ast.walk(tree):
        # THE SANCTIONED FORM COUNTS TOO, and leaving it out made this census weaker than
        # it read. Once a producer is repaired it stops interpolating `cost_usd` and starts
        # calling `tokenvalue.fmt`, so the predicate that found it before no longer does:
        # measured, `tools/runstat.py` and `tools/hook_audit_control.py` are producers that
        # this function did not discover. A discovery rule that only recognises the BROKEN
        # spelling cannot tell a repaired producer from a module that never was one.
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name in _RENDERERS:
                return True
        expr = None
        if isinstance(node, ast.JoinedStr):
            expr = _references([v.value for v in node.values
                                if isinstance(v, ast.FormattedValue)])
        elif (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod)
                and isinstance(node.left, ast.Constant)
                and isinstance(node.left.value, str)):
            # THE NAME IS NOT ALWAYS IN THE OPERAND. `"%(cost_usd).2f" % row` puts it in
            # the FORMAT STRING and unparses to `row`. Escaped percents come out first.
            literal = _ESCAPED_PCT.sub("", node.left.value)
            if not _PCT.search(literal):
                continue
            expr = _references([node.right]) + " " + " ".join(_MAP_KEY.findall(literal))
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "format"):
            # `"{c:.2f}".format(c=cost_usd)` puts it in a KEYWORD and
            # `"{cost_usd:.2f}".format(**row)` in the replacement FIELD. Both are ordinary
            # Python and both were invisible; the field names come from
            # `string.Formatter`, so `{{cost_usd}}` stays the literal text it is.
            parts = [_references(node.args),
                     _references([k.value for k in node.keywords]),
                     " ".join(k.arg for k in node.keywords if k.arg)]
            if (isinstance(node.func.value, ast.Constant)
                    and isinstance(node.func.value.value, str)):
                parts += _field_names(node.func.value.value)
            expr = " ".join(parts)
        if expr and _VALUE.search(expr):
            return True
    return False


def _unlisted_producers() -> list[str]:
    """Modules that format a `*_usd` value and are not in PRODUCERS.

    A list is an enumeration, and an enumeration goes stale silently. This re-derives the
    population from the tree so a new producer shows up as a problem rather than as
    nothing — and it asks about all three ways Python interpolates a value into a string,
    not only the one the first version happened to check.
    """
    # This module defines the format, so its own regex text mentions the field names it
    # is looking for. Excluding it is not an exemption from the sigil rule above - that
    # one reads PRODUCERS, and this one asks whether PRODUCERS is complete.
    listed = {os.path.normpath(p) for p in PRODUCERS} | {"tools/tokenvalue.py"}
    found = []
    for root, dirs, files in os.walk(EVAL):
        dirs[:] = [d for d in dirs if d not in ("runs", "starters", "__pycache__",
                                                "node_modules")]
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            rel = os.path.normpath(os.path.relpath(path, EVAL))
            if rel in listed:
                continue
            text = open(path, encoding="utf-8", errors="replace").read()
            try:
                if formats_a_value(text):
                    found.append(rel)
            except SyntaxError as exc:
                # A file the matcher cannot read is a file nothing has cleared. Reporting
                # it is the fail-closed direction; skipping it would make an unparseable
                # producer invisible, which is the defect this function exists to prevent.
                found.append(f"{rel} (does not parse, so it was never asked: {exc})")
    return found


def _raises_syntax_error(src: str) -> bool:
    """Did `formats_a_value` refuse this source rather than reading it as clean?"""
    try:
        formats_a_value(src)
    except SyntaxError:
        return True
    return False


def selftest() -> int:
    """Both directions. Green alone would pass on a formatter nobody calls."""
    rows: list[tuple[str, bool]] = []

    def check(name: str, ok: bool) -> None:
        rows.append((name, ok))

    # --- the format itself -------------------------------------------------
    check("fmt renders two decimals", fmt(27.6789) == "27.68")
    check("fmt has no sigil", "$" not in fmt(27.68))
    check("fmt(None) is n/a, not 0.00", fmt(None) == "n/a")
    check("fmt pads to width", fmt(1.5, width=8) == "    1.50")
    check("fmt(None) pads to width", fmt(None, width=8) == "     n/a")
    check("tag carries the unit", tag(27.68) == "27.68 tokval")
    check("UNIT is not a currency", UNIT.lower() not in ("usd", "$", "dollars"))
    check("DEFINITION names the finding", "#159" in DEFINITION)
    check("DEFINITION names the source field", "modelUsage" in DEFINITION)
    check("total appends the definition", DEFINITION in total(1.0))

    # --- the VARIANT: could the format still pass on input it mishandles? ---
    # A mutant removing the sigil would be caught by the rows above. Only a variant asks
    # whether a figure can reach a reader carrying money vocabulary anyway.
    check("no expenditure word in the unit", not any(w in UNIT for w in EXPENDITURE_WORDS))
    check("no expenditure word in a formatted figure",
          not any(w in tag(1.0).lower() for w in EXPENDITURE_WORDS))

    # --- the producers -----------------------------------------------------
    problems = _producer_problems()
    check(f"no producer prints a money sigil ({len(PRODUCERS)} checked)", not problems)
    for p in problems[:20]:
        print(f"    {p}")

    unlisted = _unlisted_producers()
    check("every module formatting a *_usd value is in PRODUCERS", not unlisted)
    for u in unlisted[:20]:
        print(f"    unlisted producer: {u}")

    # PROVE THE EXTRACTION ON ROWS WHOSE TRUE VALUE IS KNOWN IN ADVANCE. Every module in
    # PRODUCERS is a producer by construction, so discovery must find all 11 of them. It
    # found 9 until 2026-08-23: the two that had been repaired to call `tokenvalue.fmt`
    # stopped naming `cost_usd` and fell out of the population the row above counts. A
    # census that cannot see its own known-positive rows is reporting the instrument.
    undiscovered = []
    for rel in PRODUCERS:
        path = os.path.join(EVAL, rel)
        if os.path.exists(path) and not formats_a_value(
                open(path, encoding="utf-8", errors="replace").read()):
            undiscovered.append(rel)
    check(f"discovery finds all {len(PRODUCERS)} known producers", not undiscovered)
    for u in undiscovered:
        print(f"    known producer NOT discovered: {u}")
    check("a module calling tokenvalue.fmt is discovered",
          formats_a_value('import tokenvalue\nprint(tokenvalue.fmt(x))\n'))
    check("a module calling a bare fmt() is discovered",
          formats_a_value('from tokenvalue import fmt\nprint(fmt(x))\n'))
    check("an unrelated call is not discovered",
          not formats_a_value('print(format(x))\n'))

    # --- the address is an input to the check ------------------------------
    # A grep that finds nothing and a grep pointed at nothing print the same word.
    total_lines = sum(1 for rel in PRODUCERS
                      for _ in open(os.path.join(EVAL, rel), errors="replace")
                      if os.path.exists(os.path.join(EVAL, rel)))
    check(f"the producers were actually read ({total_lines} lines)", total_lines > 1000)

    # --- the RED direction: the check must be able to fail ------------------
    check("MONEY_LITERAL catches a re-introduced sigil",
          bool(MONEY_LITERAL.search('print(f"total $27.68")')))

    # --- the VARIANT the first version could not ask -----------------------
    # A mutant deletes the mechanism; only a variant asks whether the check still passes on
    # input it mishandles. Discovery knew f-strings alone, so a module rendering the same
    # figure by `%` or `.format()` was invisible: unlisted, unread, and green.
    check("VARIANT: the percent form is discovered",
          formats_a_value('print("$%.2f" % rec["cost_usd"])'))
    check("VARIANT: the .format form is discovered",
          formats_a_value('print("{:.2f}".format(total_cost_usd))'))
    check("the f-string form is still discovered",
          formats_a_value('print(f"{r[\'cost_usd\']:.2f}")'))
    # EVERY f-STRING PREFIX, not the one anybody happened to write. `fr`, `F` and `RF` are
    # the same string to Python and were all invisible to the first version.
    # EVERY VALID f-STRING PREFIX. `bf`/`fb` are deliberately absent: Python rejects them
    # ("'b' and 'f' prefixes are incompatible"), so a pin on them would be a pin on source
    # that cannot exist - which the regex matcher this replaced happily "discovered".
    for pre in ("f", "F", "rf", "fr", "RF", "FR", "Rf", "fR"):
        check(f"an {pre}-string is discovered",
              formats_a_value(f'print({pre}"{{cost_usd:.2f}}")'))
    # AND EVERY CONVERSION `MONEY_PERCENT` ACCEPTS. Discovery asking about a smaller set
    # than the sigil check is how a module is found by one and passed by the other.
    for conv in ("f", "g", "d", "e", "E", "s", "G", "i", "u"):
        check(f"a %{conv} percent form is discovered",
              formats_a_value(f'print("%{conv}" % cost_usd)'))
    # QUOTING IS THE PARSER'S JOB. Every one of these was a false negative under a regex
    # matcher, and every false negative is a producer that never reaches PRODUCERS.
    for src, what in (
            ("""print(f"it's {cost_usd:.2f}")""", "an apostrophe before the interpolation"),
            ("print(f'he said \"{cost_usd}\"')", "a double quote inside a single-quoted f-string"),
            ('print(f"""\n{cost_usd:.2f}\n""")', "a triple-quoted f-string"),
            ('print(f"{a}" f"{cost_usd}")', "implicit concatenation"),
            ('print("%.2f" % (spent,))', "a percent form over a tuple"),
            ('print("{c:.2f}".format(c=cost_usd))', "a .format keyword ARGUMENT"),
            ('print("{cost_usd:.2f}".format(**row))', "a .format replacement FIELD name"),
            ('print("%(cost_usd).2f" % row)', "a percent MAPPING key"),
            ('print("{0[cost_usd]}".format(row))', "an indexed replacement field"),
    ):
        check(f"discovered: {what}", formats_a_value(src))
    check("source that does not parse raises rather than reading as clean",
          _raises_syntax_error("def ("))
    check("a module that renders no such value is not discovered",
          not formats_a_value('print("hello %s" % name)\nx = cost_usd\n'))
    check("a value merely ASSIGNED, never rendered, is not discovered",
          not formats_a_value('total = rec["cost_usd"]\nreturn total\n'))
    # THE LITERAL IS READ FOR FIELD NAMES ONLY. Scanning a format string whole would turn
    # every sentence that mentions one of these fields into a producer.
    check("prose inside a format literal is not a replacement field",
          not formats_a_value('print("the key is cost_usd, not {x}".format(x=1))'))
    check("a percent literal that merely mentions the name is not a mapping key",
          not formats_a_value('print("cost_usd is absent: %d" % n)'))
    # THE FALSE-POSITIVE DIRECTION, and it is the one that gets a gate disabled. None of
    # these renders a valuation: a constant is data, `{{` is an escaped brace, `%%` is an
    # escaped percent. Requiring their modules in PRODUCERS would turn the sweep red on
    # correct input.
    for src, what in (
            ('print("{value}".format(value="cost_usd"))', "a CONSTANT that spells the field"),
            ('print("{{cost_usd}}".format())', "an escaped brace, not a field"),
            ('print("%%(cost_usd)s" % ())', "an escaped percent, not a mapping key"),
            ("""print(f"{'cost_usd'}")""", "a constant inside an f-string"),
            ('print("{a}".format(a=1) + " cost_usd")', "a field named elsewhere in prose"),
    ):
        check(f"not discovered: {what}", not formats_a_value(src))
    # And the sigil check has to see the percent form too, or the variant above finds the
    # module and the row that matters still passes it.
    # --- the sigil check, ON THE PATH `_producer_problems` USES -------------
    # `money_sigil_in` is what the sweep calls, so these rows are about the sweep. The
    # first four were green against the regexes alone while the guard in front of them
    # skipped the line, which is the failure they now cover.
    RED = [
        ('print(f"${spent:.2f}")', "an interpolated sigil"),
        ('print(f"total ${cost_usd:.2f}")', "an interpolated sigil beside a shell-ish name"),
        ('print(f"total $27.68")', "a literal sigil"),
        ('print("$%.2f" % spent)', "the percent form"),
        ('print("$%E" % spent)', "the percent form, uppercase conversion"),
        ('print("${:.2f}".format(spent))', "the .format form"),
    ]
    for line, what in RED:
        check(f"money_sigil_in catches {what}", money_sigil_in(line), )
    GREEN = [
        ('"invoked ${CLAUDE_PROJECT_DIR:-unset}"', "a shell variable"),
        ('">> \"${STARTER_HOOK_LOG:-${TMPDIR:-/tmp}/x.tsv}\""', "nested shell variables"),
        ("f\"MEASURED: $TMPDIR erosion destroyed 80%\"", "a bare $TMPDIR"),
        ('if: ${{ !cancelled() }}', "an Actions template"),
        ('print(f"{pct:.0f}% of the floor")', "a plain percentage"),
        ('print(f"{tokenvalue.fmt(spent)} tokval")', "a correctly formatted figure"),
    ]
    for line, what in GREEN:
        check(f"money_sigil_in passes {what}", not money_sigil_in(line))
    # THE GUARD MUST NOT SWALLOW THE REST OF THE LINE. This is the exact shape the old
    # whole-line skip had, and it is why the guard blanks a span instead.
    check("a BRACED shell variable does not excuse a sigil on the same line",
          money_sigil_in('log("${TMPDIR} then $27.68")'))
    check("an UNBRACED shell variable does not excuse a sigil on the same line",
          money_sigil_in('log("$TMPDIR then $27.68")'))
    check("an unbraced shell variable is still not a sigil on its own",
          not money_sigil_in('note = "$TMPDIR erosion destroyed 80% of six toolchains"'))

    bad = [n for n, ok in rows if not ok]
    for name, ok in rows:
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    print(f"\n{len(rows) - len(bad)}/{len(rows)} pins green")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--definition", action="store_true",
                    help="print the one-line definition and exit")
    a = ap.parse_args()
    if a.definition:
        print(DEFINITION)
        return 0
    if a.selftest:
        return selftest()
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
