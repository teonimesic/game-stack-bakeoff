extends Node
## Keeps a LAUNCHED game from stealing the operator's keyboard. HARNESS SCAFFOLDING,
## NOT GAME BEHAVIOUR.
##
## Gated on STARTER_NO_RAISE, which is UNSET BY DEFAULT. A human running `just run` gets
## the game exactly as its author wrote it: the window raises and takes focus, which is
## what a player wants. Only the evaluation harness sets the variable.
##
## That gate is what makes this scaffolding rather than a change to the shipped product —
## the same line that made Unity's `AudioListener.volume = 0` acceptable and project-level
## "Disable Unity Audio" not. A guard that alters the artifact when nobody asked is a
## different thing from one that alters a launch the harness owns.
##
## WHY A RUNTIME HOOK AT ALL. Godot has no `--no-focus` flag; the
## `display/window/size/no_focus` project setting has no effect on macOS 4.7 (measured,
## both via `override.cfg` and written directly into `project.godot`); and
## `open -g -j -a Godot.app` is overridden because the engine activates itself. The
## launch-time hint that works for Unity does not generalise.


func _ready() -> void:
	if OS.get_environment("STARTER_NO_RAISE") != "1":
		return
	# CHEAPEST FIRST: ask the window not to take focus.
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	await get_tree().process_frame
	if not DisplayServer.window_is_focused():
		print("[no_raise] flag sufficient: window did not take focus")
		return
	# LAST RESORT, and it is a DIFFERENT RESULT: the engine could not be PREVENTED from
	# raising, only corrected afterwards. Minimising hands the keyboard back.
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_MINIMIZED)
	print("[no_raise] flag INSUFFICIENT - window raised anyway; minimised to return focus")
