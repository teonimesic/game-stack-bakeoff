## A ~100-line test runner, deliberately not GUT or gdUnit4.
##
## `just verify` needs exactly two things from a test framework: a per-test
## PASS/FAIL line, and a NON-ZERO EXIT CODE when anything failed. An addon adds a
## version to pin, an import step, and its own opinions about scene setup, in
## exchange for features this template does not use. Keep it this small.
##
## Output contract (parse it, do not eyeball it):
##   PASS <name>
##   SKIP <name> — <reason>          (a FAIL instead when --strict is passed)
##   FAIL <name>
##       <assertion message>
##   TESTS total=N passed=N failed=N skipped=N
class_name TestRunner
extends RefCounted

var total: int = 0
var passed: int = 0
var failed: int = 0
var skipped: int = 0

## When true, a skip is a FAILURE. `just ci` sets it (via `-- --strict`).
##
## A skip means a test did not run. Locally that is a kindness — a developer with
## no display should not see red they cannot fix — but in CI it is the exact
## false-confidence failure this template exists to prevent: five render tests
## reporting SKIP and the pipeline reporting green over ZERO render coverage.
## CI must never be able to do that.
var strict: bool = false

var _current: String = ""
var _failures: PackedStringArray = PackedStringArray()
var _skip_reason: String = ""
var _skips: PackedStringArray = PackedStringArray()
var _skip_reasons: PackedStringArray = PackedStringArray()


## Run a synchronous test. For a test that must `await`, call [method begin] and
## [method end] around the body instead.
func run(name: String, body: Callable) -> void:
	begin(name)
	body.call(self)
	end()


func begin(name: String) -> void:
	_current = name
	_failures = PackedStringArray()
	_skip_reason = ""


func end() -> void:
	total += 1
	if not _skip_reason.is_empty():
		skipped += 1
		_skips.append(_current)
		_skip_reasons.append(_skip_reason)
		if strict:
			failed += 1
			print("FAIL %s" % _current)
			print("      SKIPPED, and --strict is on: a skipped test is zero coverage.")
			print("      %s" % _skip_reason)
		else:
			passed += 1
			print("SKIP %s — %s" % [_current, _skip_reason])
	elif _failures.is_empty():
		passed += 1
		print("PASS %s" % _current)
	else:
		failed += 1
		print("FAIL %s" % _current)
		for failure: String in _failures:
			print("      %s" % failure)
	_current = ""


## Mark the current test as skipped rather than failed. Use ONLY for a missing
## capability of the machine (no display, no golden image), never to get past a
## red assertion.
func skip(reason: String) -> void:
	_skip_reason = reason


func check(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)


# `==` on two Variants yields a Variant, and the strict-typing warnings in
# project.godot reject passing that where a `bool` is declared. This generic
# comparator is the one place in the repo where the dynamism is the point, so it
# gets a NARROW, NAMED suppression rather than the warnings being turned down
# project-wide. Do not copy this annotation into game code.
func eq(actual: Variant, expected: Variant, message: String) -> void:
	@warning_ignore("unsafe_call_argument")
	check(actual == expected, "%s (got %s, expected %s)" % [message, actual, expected])


func ne(actual: Variant, unexpected: Variant, message: String) -> void:
	@warning_ignore("unsafe_call_argument")
	check(actual != unexpected, "%s (both were %s)" % [message, actual])


func gt(actual: float, bound: float, message: String) -> void:
	check(actual > bound, "%s (got %s, expected > %s)" % [message, actual, bound])


func ge(actual: float, bound: float, message: String) -> void:
	check(actual >= bound, "%s (got %s, expected >= %s)" % [message, actual, bound])


func lt(actual: float, bound: float, message: String) -> void:
	check(actual < bound, "%s (got %s, expected < %s)" % [message, actual, bound])


func le(actual: float, bound: float, message: String) -> void:
	check(actual <= bound, "%s (got %s, expected <= %s)" % [message, actual, bound])


## Print the machine-readable summary and return the process exit code.
func summary() -> int:
	print("TESTS total=%d passed=%d failed=%d skipped=%d" % [total, passed, failed, skipped])

	# A skip is silent by nature — it reads like a pass in a wall of PASS lines.
	# Say it loudly, in the summary, where it cannot be scrolled past.
	if skipped > 0:
		print("=========================================================================")
		print("⚠️  %d TEST(S) SKIPPED — that coverage DID NOT RUN." % skipped)
		print("   Green here does NOT mean the behaviour was verified.")
		# Grouped by reason: five render tests skipping for the same missing display
		# is one problem, and printing it five times buries the summary.
		var seen := PackedStringArray()
		for reason: String in _skip_reasons:
			if seen.has(reason):
				continue
			seen.append(reason)
			var names := PackedStringArray()
			for index: int in range(_skip_reasons.size()):
				if _skip_reasons[index] == reason:
					names.append(_skips[index])
			print("   • %s" % reason)
			print("     affects: %s" % ", ".join(names))
		if not strict:
			print("   `just ci` runs with --strict, where each of these is a FAILURE.")
		print("=========================================================================")

	if failed > 0:
		printerr("%d test(s) failed" % failed)
		return 1
	if total == 0:
		printerr("no tests ran — the runner found nothing to execute")
		return 1
	return 0
