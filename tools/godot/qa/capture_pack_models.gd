## Loads every imported model of an asset pack (res://assets/models/<pack>/*.glb), prints what Godot
## made of it and saves two screenshots per model: a front three-quarter and a back three-quarter view.
## Part of the image-to-Godot asset pipeline (.claude/skills/image-to-assets/SKILL.md).
##
## Each model prints one line, `GODOT_MODEL {json}`: the bounding-box size in metres, triangles,
## mesh surfaces, and per surface the material type and which textures it carries. These are
## observations; judging them against the Blender build is up to the reader.
##
## Import first, then capture (needs a display; without a GPU use Xvfb and Mesa's software OpenGL):
##
##   godot --headless --path . --import
##   xvfb-run -a -s "-screen 0 1280x720x24" godot --path . --rendering-driver opengl3 \
##       --resolution 1280x720 --script res://tools/godot/qa/capture_pack_models.gd -- \
##       --pack <pack> [--models <id>,<id>] [--out production/qa/evidence/<pack>]
##
## Screenshots land in <out>/<model>/<model>_godot_front.png and _godot_back.png.
extends SceneTree

const MODELS_ROOT := "res://assets/models"
const EVIDENCE_ROOT := "production/qa/evidence"
const BACKGROUND := Color("#d3d3d3")
## Camera azimuths in degrees around +Y; 0 looks at the model's front (glTF +Z) from in front of it.
const VIEWS := {"front": -30.0, "back": 150.0}
const ELEVATION_DEG := 15.0
const FOV_DEG := 40.0
## Frames to wait after each change so shaders compile and the image settles.
const SETTLE_FRAMES := 8


func _initialize() -> void:
	_capture()


func _capture() -> void:
	var options := _parse_options(OS.get_cmdline_user_args())
	var pack_name: String = options.get("pack", "")
	if pack_name.is_empty():
		push_error("capture_pack_models: pass --pack <pack>")
		quit(1)
		return
	var models_dir := MODELS_ROOT.path_join(pack_name)
	var out_dir: String = options.get("out", EVIDENCE_ROOT.path_join(pack_name))
	var wanted: PackedStringArray = String(options.get("models", "")).split(",", false)

	var stage := _build_stage()
	root.add_child(stage)
	await process_frame  # nodes added during _initialize enter the tree on the next frame
	var camera: Camera3D = stage.get_node("Camera")

	for file_name in DirAccess.get_files_at(models_dir):
		if file_name.get_extension() != "glb":
			continue
		var model_name := file_name.get_basename()
		if not wanted.is_empty() and not wanted.has(model_name):
			continue
		var packed := load(models_dir.path_join(file_name)) as PackedScene
		if packed == null:
			print("GODOT_MODEL %s" % JSON.stringify({"name": model_name, "loaded": false}))
			continue
		var model := packed.instantiate() as Node3D
		stage.add_child(model)
		await process_frame
		var bounds := _bounds(model)
		print("GODOT_MODEL %s" % JSON.stringify(_describe(model_name, model, bounds)))

		var model_dir := out_dir.path_join(model_name)
		DirAccess.make_dir_recursive_absolute(model_dir)
		for view: String in VIEWS:
			_frame(camera, bounds, VIEWS[view])
			await _settle()
			var path := model_dir.path_join("%s_godot_%s.png" % [model_name, view])
			root.get_texture().get_image().save_png(path)
			print("captured %s" % path)
		model.queue_free()
		await _settle()
	quit()


## Grey backdrop, soft ambient light, a warm key light, a cool fill light and a camera.
func _build_stage() -> Node3D:
	var stage := Node3D.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = BACKGROUND
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.85, 0.85, 0.9)
	environment.ambient_light_energy = 0.6
	var world := WorldEnvironment.new()
	world.environment = environment
	stage.add_child(world)

	var key := DirectionalLight3D.new()
	key.light_color = Color(1.0, 0.95, 0.9)
	key.light_energy = 1.2
	key.rotation_degrees = Vector3(-45.0, -35.0, 0.0)
	key.shadow_enabled = true
	stage.add_child(key)
	var fill := DirectionalLight3D.new()
	fill.light_color = Color(0.9, 0.95, 1.0)
	fill.light_energy = 0.5
	fill.rotation_degrees = Vector3(-30.0, 140.0, 0.0)
	stage.add_child(fill)

	var camera := Camera3D.new()
	camera.name = "Camera"
	camera.fov = FOV_DEG
	stage.add_child(camera)
	camera.current = true
	return stage


## Merged world-space AABB of every MeshInstance3D under `model`.
func _bounds(model: Node3D) -> AABB:
	var merged := AABB()
	var first := true
	for mesh_instance: MeshInstance3D in _mesh_instances(model):
		var box := mesh_instance.global_transform * mesh_instance.get_aabb()
		merged = box if first else merged.merge(box)
		first = false
	return merged


func _describe(model_name: String, model: Node3D, bounds: AABB) -> Dictionary:
	var triangles := 0
	var surfaces := []
	for mesh_instance: MeshInstance3D in _mesh_instances(model):
		var mesh := mesh_instance.mesh
		triangles += mesh.get_faces().size() / 3
		for surface in mesh.get_surface_count():
			var material := mesh_instance.get_active_material(surface)
			surfaces.append(_describe_material(material))
	return {
		"name": model_name,
		"loaded": true,
		"size_m": [snappedf(bounds.size.x, 0.001), snappedf(bounds.size.y, 0.001), snappedf(bounds.size.z, 0.001)],
		"triangles": triangles,
		"surfaces": surfaces,
	}


func _describe_material(material: Material) -> Dictionary:
	if material == null:
		return {"material": null}
	var info := {"material": material.resource_name, "type": material.get_class()}
	var standard := material as BaseMaterial3D
	if standard != null:
		info["albedo_color"] = standard.albedo_color.to_html(false)
		info["albedo_texture"] = standard.albedo_texture != null
		info["normal_texture"] = standard.normal_enabled and standard.normal_texture != null
		info["roughness_texture"] = standard.roughness_texture != null
		info["emission"] = standard.emission_enabled
		info["transparent"] = standard.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED
	return info


func _mesh_instances(node: Node) -> Array[MeshInstance3D]:
	var found: Array[MeshInstance3D] = []
	for child in node.find_children("*", "MeshInstance3D", true, false):
		found.append(child as MeshInstance3D)
	var self_mesh := node as MeshInstance3D
	if self_mesh != null:
		found.append(self_mesh)
	return found


## Places the camera on a sphere around `bounds`, far enough that the whole model fits.
func _frame(camera: Camera3D, bounds: AABB, azimuth_deg: float) -> void:
	var center := bounds.get_center()
	var radius := bounds.size.length() / 2.0
	var distance := radius / sin(deg_to_rad(FOV_DEG) / 2.0) * 1.1
	var azimuth := deg_to_rad(azimuth_deg)
	var elevation := deg_to_rad(ELEVATION_DEG)
	var offset := Vector3(sin(azimuth) * cos(elevation), sin(elevation), cos(azimuth) * cos(elevation))
	camera.look_at_from_position(center + offset * distance, center)


func _settle() -> void:
	for _frame_index in SETTLE_FRAMES:
		await process_frame
	await RenderingServer.frame_post_draw


## Parses `--key value` pairs.
func _parse_options(arguments: PackedStringArray) -> Dictionary:
	var options := {}
	var i := 0
	while i < arguments.size() - 1:
		if arguments[i].begins_with("--"):
			options[arguments[i].trim_prefix("--")] = arguments[i + 1]
			i += 2
		else:
			i += 1
	return options
