## A captured frame: tightly packed RGBA8, `width * height * 4` bytes.
##
## Deliberately a plain byte buffer rather than an [Image]: the assertions below
## are the contract the rendering tests are written against, and keeping them off
## [Image] means they cannot accidentally depend on an image format conversion.
class_name Frame
extends RefCounted

var width: int = 0
var height: int = 0
var rgba: PackedByteArray = PackedByteArray()


## Result of [method ink_centroid]. GDScript has no `Option`, and an untyped
## `null` return would be a [Variant] the strict-typing warnings reject.
class Centroid:
	extends RefCounted
	var found: bool = false
	var x: float = 0.0
	var y: float = 0.0


func _init(p_width: int, p_height: int, p_rgba: PackedByteArray) -> void:
	width = p_width
	height = p_height
	rgba = p_rgba


## Wrap a viewport capture. Returns null when the [Image] is null, which is what
## a display-less run produces — see `tests/render_test.gd`.
static func from_image(image: Image) -> Frame:
	if image == null:
		return null
	if image.get_format() != Image.FORMAT_RGBA8:
		image.convert(Image.FORMAT_RGBA8)
	return Frame.new(image.get_width(), image.get_height(), image.get_data())


## RGBA of one pixel, 0..255 per channel.
func pixel(x: int, y: int) -> PackedByteArray:
	var index: int = (y * width + x) * 4
	return rgba.slice(index, index + 4)


func _differs(index: int, background: PackedByteArray, tolerance: int) -> bool:
	return (
		absi(rgba[index] - background[0]) > tolerance
		or absi(rgba[index + 1] - background[1]) > tolerance
		or absi(rgba[index + 2] - background[2]) > tolerance
	)


## Fraction of pixels that are not the background colour. A cheap, robust "did
## anything actually render?" signal that does not depend on a golden file and
## does not break when colours are tweaked.
func ink_coverage(background: PackedByteArray, tolerance: int) -> float:
	var lit: int = 0
	for index: int in range(0, rgba.size(), 4):
		if _differs(index, background, tolerance):
			lit += 1
	return float(lit) / float(width * height)


## Centre of mass of non-background pixels, in pixel coordinates, restricted to
## [param region] (pass `Rect2i(0, 0, width, height)` for the whole frame).
##
## This is how you assert "it moved to the right" without a golden image and
## without caring about exact pixel values.
func ink_centroid(background: PackedByteArray, tolerance: int, region: Rect2i) -> Centroid:
	var sum_x: float = 0.0
	var sum_y: float = 0.0
	var count: int = 0
	for y: int in range(region.position.y, region.end.y):
		var row: int = y * width * 4
		for x: int in range(region.position.x, region.end.x):
			if _differs(row + x * 4, background, tolerance):
				sum_x += float(x)
				sum_y += float(y)
				count += 1
	var result := Centroid.new()
	if count > 0:
		result.found = true
		result.x = sum_x / float(count)
		result.y = sum_y / float(count)
	return result


## Where one specific colour appears inside [param region]: one byte per pixel,
## row-major, 1 for a match and 0 for anything else.
##
## The counterpart to [method ink_coverage], and the tool for asserting on an
## OVERLAY. "Not the background" cannot tell a HUD from a sprite that drifted
## into the same corner; "within tolerance of the HUD colour" can. `count(1)` is
## how much of it reached the framebuffer, and comparing two masks is how a test
## says the overlay CHANGED rather than merely being present.
func color_mask(color: PackedByteArray, tolerance: int, region: Rect2i) -> PackedByteArray:
	var mask := PackedByteArray()
	mask.resize(region.size.x * region.size.y)
	var at: int = 0
	for y: int in range(region.position.y, region.end.y):
		var row: int = y * width * 4
		for x: int in range(region.position.x, region.end.x):
			var index: int = row + x * 4
			var hit: bool = (
				absi(rgba[index] - color[0]) <= tolerance
				and absi(rgba[index + 1] - color[1]) <= tolerance
				and absi(rgba[index + 2] - color[2]) <= tolerance
			)
			mask[at] = 1 if hit else 0
			at += 1
	return mask


## Centre of mass of the pixels matching [param color] inside [param region].
##
## The colour-matching counterpart of [method ink_centroid]. As soon as a frame
## holds more than one thing — an arena and a HUD — "the centroid of everything
## that is not the background" has stopped being a statement about either of
## them, and this is what replaces it.
func color_centroid(color: PackedByteArray, tolerance: int, region: Rect2i) -> Centroid:
	var mask: PackedByteArray = color_mask(color, tolerance, region)
	var sum_x: float = 0.0
	var sum_y: float = 0.0
	var count: int = 0
	var at: int = 0
	for y: int in range(region.position.y, region.end.y):
		for x: int in range(region.position.x, region.end.x):
			if mask[at] == 1:
				sum_x += float(x)
				sum_y += float(y)
				count += 1
			at += 1
	var result := Centroid.new()
	if count > 0:
		result.found = true
		result.x = sum_x / float(count)
		result.y = sum_y / float(count)
	return result


## Fraction of pixels whose colour differs from [param other] by more than
## [param tolerance] on any channel.
##
## Tolerance exists because rasterisation is not bit-identical across GPU
## vendors, drivers, or Godot rendering methods — the same scene under Forward+
## on Metal and under the Compatibility renderer on lavapipe can differ in the
## last bit or two of an edge pixel. Tolerance does NOT exist to paper over a
## rectangle being in the wrong place; that shows up as a large fraction, not a
## small one.
func diff_fraction(other: Frame, tolerance: int) -> float:
	assert(width == other.width and height == other.height, "cannot diff frames of different sizes")
	var differing: int = 0
	for index: int in range(0, rgba.size(), 4):
		if (
			absi(rgba[index] - other.rgba[index]) > tolerance
			or absi(rgba[index + 1] - other.rgba[index + 1]) > tolerance
			or absi(rgba[index + 2] - other.rgba[index + 2]) > tolerance
		):
			differing += 1
	return float(differing) / float(width * height)


## A picture of where two frames disagree, for a human or an agent to open.
##
## Matching pixels are dimmed to a quarter brightness; differing pixels are
## magenta. A geometry bug shows up as a magenta silhouette in the shape of the
## thing that moved, which is immediately readable — a percentage is not.
func diff_image(other: Frame, tolerance: int) -> Frame:
	var out := PackedByteArray()
	out.resize(rgba.size())
	for index: int in range(0, rgba.size(), 4):
		var differs: bool = (
			absi(rgba[index] - other.rgba[index]) > tolerance
			or absi(rgba[index + 1] - other.rgba[index + 1]) > tolerance
			or absi(rgba[index + 2] - other.rgba[index + 2]) > tolerance
		)
		if differs:
			out[index] = 255
			out[index + 1] = 0
			out[index + 2] = 255
		else:
			out[index] = rgba[index] / 4
			out[index + 1] = rgba[index + 1] / 4
			out[index + 2] = rgba[index + 2] / 4
		out[index + 3] = 255
	return Frame.new(width, height, out)


## Write a PNG.
##
## [param path] is a `res://` path, but the write goes through
## [method ProjectSettings.globalize_path] and [method Image.save_png] on the OS
## path on purpose: that bypasses Godot's import pipeline entirely, so a golden
## image never turns into a `.import`ed [CompressedTexture2D] behind your back.
func save_png(path: String) -> Error:
	var image := Image.create_from_data(width, height, false, Image.FORMAT_RGBA8, rgba)
	var os_path: String = ProjectSettings.globalize_path(path)
	DirAccess.make_dir_recursive_absolute(os_path.get_base_dir())
	return image.save_png(os_path)


## Read a PNG. Returns null when the file does not exist or is unreadable.
static func load_png(path: String) -> Frame:
	var os_path: String = ProjectSettings.globalize_path(path)
	if not FileAccess.file_exists(os_path):
		return null
	var image: Image = Image.load_from_file(os_path)
	return from_image(image)
