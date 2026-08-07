import bpy
import math
import random
import shutil
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

PROJECT_ROOT = Path(r"C:\Users\pithe\Documents\Projetos\Github\fastcamp-projeto-final-visao-computacional")
MODEL_PATH = PROJECT_ROOT / "blender" / "assets" / "fbx" / "faca" / "butter_knife.glb"
SCRIPT_PATH = PROJECT_ROOT / "blender" / "scripts" / "gerar_faca_butter_knife_0601_0800_v4_escuro.py"
BLEND_PATH = PROJECT_ROOT / "blender" / "cenas" / "faca" / "faca_butter_knife_0601_0800_v4_escuro.blend"
IMAGES_DIR = PROJECT_ROOT / "dataset_lotes" / "faca" / "images"
LABELS_DIR = PROJECT_ROOT / "dataset_lotes" / "faca" / "labels"

CLASS_ID = 1
START_INDEX = 601
END_INDEX = 800
IMAGE_SIZE = 640
BASE_SEED = 2026080620
MAX_ATTEMPTS = 40
SAVE_BLEND_EVERY = 25
TARGET_LENGTH = 0.40
TABLE_TOP_Z = 0.36

WOOD_COLORS = [
    ((0.025, 0.007, 0.0015, 1.0), (0.070, 0.025, 0.006, 1.0)),
    ((0.032, 0.010, 0.0020, 1.0), (0.082, 0.031, 0.008, 1.0)),
    ((0.020, 0.005, 0.0010, 1.0), (0.060, 0.020, 0.004, 1.0)),
    ((0.040, 0.013, 0.0025, 1.0), (0.095, 0.037, 0.010, 1.0)),
]

def ensure_directories():
    SCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_DIR.mkdir(parents=True, exist_ok=True)

def save_current_script():
    source_text = None
    space_data = getattr(bpy.context, "space_data", None)

    if space_data is not None and getattr(space_data, "type", "") == "TEXT_EDITOR":
        source_text = getattr(space_data, "text", None)

    if source_text is None:
        source_text = bpy.data.texts.get("Text")

    if source_text is None and len(bpy.data.texts) > 0:
        source_text = max(bpy.data.texts, key=lambda text: len(text.as_string()))

    if source_text is not None:
        SCRIPT_PATH.write_text(source_text.as_string(), encoding="utf-8")
        return

    if "__file__" in globals():
        source_path = Path(__file__)
        if source_path.exists() and source_path.resolve() != SCRIPT_PATH.resolve():
            shutil.copy2(str(source_path), str(SCRIPT_PATH))

def remove_invalid_previous_pairs():
    for index in (601, 602):
        image = IMAGES_DIR / "faca_butter_knife_{:04d}.png".format(index)
        label = LABELS_DIR / "faca_butter_knife_{:04d}.txt".format(index)

        if image.exists():
            image.unlink()

        if label.exists():
            label.unlink()

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for collection in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.lights,
        bpy.data.cameras,
    ):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)

def create_material(name):
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    return material

def create_background_material():
    material = create_material("Material_Fundo")
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.010, 0.012, 0.016, 1.0)
    principled.inputs["Roughness"].default_value = 1.0
    principled.inputs["Metallic"].default_value = 0.0
    return material

def create_wood_material():
    material = create_material("Material_Mesa")
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    for node in list(nodes):
        nodes.remove(node)

    output = nodes.new(type="ShaderNodeOutputMaterial")
    principled = nodes.new(type="ShaderNodeBsdfPrincipled")
    texcoord = nodes.new(type="ShaderNodeTexCoord")
    mapping = nodes.new(type="ShaderNodeMapping")
    noise = nodes.new(type="ShaderNodeTexNoise")
    ramp = nodes.new(type="ShaderNodeValToRGB")
    bump_noise = nodes.new(type="ShaderNodeTexNoise")
    bump = nodes.new(type="ShaderNodeBump")

    output.location = (700, 0)
    principled.location = (420, 0)
    texcoord.location = (-900, 0)
    mapping.location = (-700, 0)
    noise.location = (-470, 130)
    ramp.location = (-220, 130)
    bump_noise.location = (-470, -170)
    bump.location = (120, -170)

    mapping.inputs["Scale"].default_value = (7.5, 1.45, 2.2)
    noise.inputs["Scale"].default_value = 4.0
    noise.inputs["Detail"].default_value = 3.2
    noise.inputs["Roughness"].default_value = 0.52
    noise.inputs["Distortion"].default_value = 0.12

    bump_noise.inputs["Scale"].default_value = 60.0
    bump_noise.inputs["Detail"].default_value = 2.0
    bump_noise.inputs["Roughness"].default_value = 0.42

    bump.inputs["Strength"].default_value = 0.055
    bump.inputs["Distance"].default_value = 0.018

    principled.inputs["Roughness"].default_value = 0.68
    principled.inputs["Metallic"].default_value = 0.0

    if "Specular" in principled.inputs:
        principled.inputs["Specular"].default_value = 0.28

    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[0].color = WOOD_COLORS[0][0]
    ramp.color_ramp.elements[1].color = WOOD_COLORS[0][1]

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(mapping.outputs["Vector"], bump_noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], principled.inputs["Base Color"])
    links.new(bump_noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], principled.inputs["Normal"])
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    return material, ramp, noise

def set_wood_style(ramp, noise):
    dark, light = random.choice(WOOD_COLORS)
    ramp.color_ramp.elements[0].color = dark
    ramp.color_ramp.elements[1].color = light
    noise.inputs["Scale"].default_value = random.uniform(3.5, 4.7)
    noise.inputs["Detail"].default_value = random.uniform(2.7, 3.8)
    noise.inputs["Distortion"].default_value = random.uniform(0.07, 0.17)

def create_steel_material():
    material = create_material("Material_Aco")
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    for node in list(nodes):
        nodes.remove(node)

    output = nodes.new(type="ShaderNodeOutputMaterial")
    principled = nodes.new(type="ShaderNodeBsdfPrincipled")
    noise = nodes.new(type="ShaderNodeTexNoise")
    bump = nodes.new(type="ShaderNodeBump")

    output.location = (500, 0)
    principled.location = (220, 0)
    noise.location = (-220, -100)
    bump.location = (0, -100)

    principled.inputs["Base Color"].default_value = (0.18, 0.20, 0.23, 1.0)
    principled.inputs["Metallic"].default_value = 0.68
    principled.inputs["Roughness"].default_value = 0.42

    if "Specular" in principled.inputs:
        principled.inputs["Specular"].default_value = 0.30

    noise.inputs["Scale"].default_value = 170.0
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Roughness"].default_value = 0.35

    bump.inputs["Strength"].default_value = 0.008
    bump.inputs["Distance"].default_value = 0.035

    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], principled.inputs["Normal"])
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    return material

def look_at(obj, target):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def apply_transform(obj, rotation=True, scale=True):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=rotation, scale=scale)
    obj.select_set(False)

def configure_render():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = IMAGE_SIZE
    scene.render.resolution_y = IMAGE_SIZE
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False

    try:
        scene.view_settings.view_transform = "Filmic"
        scene.view_settings.look = "Medium High Contrast"
    except Exception:
        pass

    scene.view_settings.exposure = -1.45
    scene.view_settings.gamma = 1.0

    try:
        scene.eevee.taa_render_samples = 64
        scene.eevee.use_gtao = True
        scene.eevee.gtao_distance = 0.24
        scene.eevee.gtao_factor = 1.20
        scene.eevee.use_soft_shadows = True
    except Exception:
        pass

    if scene.world is None:
        scene.world = bpy.data.worlds.new("World_ButterKnife_V3")

    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.006, 0.007, 0.009, 1.0)
    background.inputs["Strength"].default_value = 0.012

def create_scene():
    refs = {}

    bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, TABLE_TOP_Z - 0.04))
    table = bpy.context.active_object
    table.name = "Mesa"
    table.scale = (0.72, 0.50, 0.04)
    wood_material, wood_ramp, wood_noise = create_wood_material()
    table.data.materials.append(wood_material)

    bpy.ops.mesh.primitive_plane_add(
        location=(0.0, 0.62, 0.92),
        rotation=(math.radians(90), 0.0, 0.0)
    )
    backdrop = bpy.context.active_object
    backdrop.name = "Fundo"
    backdrop.scale = (2.0, 1.55, 1.0)
    backdrop.data.materials.append(create_background_material())

    bpy.ops.object.light_add(type="AREA", location=(0.48, -0.42, 1.05))
    key = bpy.context.active_object
    key.name = "Luz_Principal"
    key.data.energy = 78
    key.data.size = 0.95

    bpy.ops.object.light_add(type="AREA", location=(-0.50, -0.08, 0.88))
    fill = bpy.context.active_object
    fill.name = "Luz_Preenchimento"
    fill.data.energy = 24
    fill.data.size = 1.10

    bpy.ops.object.light_add(type="AREA", location=(0.0, 0.02, 1.30))
    top = bpy.context.active_object
    top.name = "Luz_Superior"
    top.data.energy = 38
    top.data.size = 1.55

    bpy.ops.object.light_add(type="POINT", location=(0.0, 0.25, 0.95))
    rim = bpy.context.active_object
    rim.name = "Luz_Contorno"
    rim.data.energy = 8

    bpy.ops.object.camera_add(location=(0.0, -0.78, 0.88))
    camera = bpy.context.active_object
    camera.name = "Camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.72
    look_at(camera, Vector((0.0, 0.0, TABLE_TOP_Z + 0.012)))
    bpy.context.scene.camera = camera

    refs["wood_ramp"] = wood_ramp
    refs["wood_noise"] = wood_noise
    refs["key"] = key
    refs["fill"] = fill
    refs["top"] = top
    refs["rim"] = rim
    refs["camera"] = camera

    return refs

def randomize_scene(refs):
    set_wood_style(refs["wood_ramp"], refs["wood_noise"])

    refs["key"].data.energy = random.uniform(62, 92)
    refs["key"].location = Vector((
        random.uniform(0.36, 0.58),
        random.uniform(-0.52, -0.30),
        random.uniform(0.96, 1.13)
    ))

    refs["fill"].data.energy = random.uniform(16, 30)
    refs["fill"].location = Vector((
        random.uniform(-0.58, -0.34),
        random.uniform(-0.18, 0.02),
        random.uniform(0.78, 0.95)
    ))

    refs["top"].data.energy = random.uniform(26, 48)
    refs["top"].location = Vector((
        random.uniform(-0.10, 0.10),
        random.uniform(-0.08, 0.08),
        random.uniform(1.22, 1.36)
    ))

    refs["rim"].data.energy = random.uniform(5, 11)
    refs["rim"].location = Vector((
        random.uniform(-0.08, 0.08),
        random.uniform(0.18, 0.32),
        random.uniform(0.84, 0.98)
    ))

    camera = refs["camera"]
    camera.location = Vector((
        random.uniform(-0.035, 0.035),
        random.uniform(-0.81, -0.75),
        random.uniform(0.85, 0.91)
    ))
    camera.data.ortho_scale = random.uniform(0.66, 0.78)
    camera.data.shift_x = random.uniform(-0.10, 0.10)
    camera.data.shift_y = random.uniform(-0.07, 0.07)

    look_at(
        camera,
        Vector((
            random.uniform(-0.018, 0.018),
            random.uniform(-0.012, 0.012),
            TABLE_TOP_Z + random.uniform(0.005, 0.016)
        ))
    )

def import_model():
    before_names = set(obj.name for obj in bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(MODEL_PATH))
    imported = [obj for obj in bpy.data.objects if obj.name not in before_names]
    meshes = [obj for obj in imported if obj.type == "MESH"]

    if len(meshes) != 1:
        raise RuntimeError("Era esperada exatamente uma malha no GLB.")

    knife = meshes[0]
    world_matrix = knife.matrix_world.copy()
    knife.parent = None
    knife.matrix_world = world_matrix

    for obj in list(imported):
        if obj != knife and obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)

    apply_transform(knife, rotation=True, scale=True)
    align_knife(knife)

    bpy.ops.object.select_all(action="DESELECT")
    knife.select_set(True)
    bpy.context.view_layer.objects.active = knife
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    knife.location = Vector((0.0, 0.0, 0.0))

    longest = max(knife.dimensions.x, knife.dimensions.y, knife.dimensions.z)

    if longest <= 0:
        raise RuntimeError("A faca possui dimensões inválidas.")

    factor = TARGET_LENGTH / longest
    knife.scale = (factor, factor, factor)
    apply_transform(knife, rotation=False, scale=True)

    steel = create_steel_material()
    knife.data.materials.clear()
    knife.data.materials.append(steel)

    fix_normals(knife)

    bbox = world_bbox(knife)
    knife.location.z = TABLE_TOP_Z + 0.003 - bbox["min"].z
    bpy.context.view_layer.update()

    return {
        "object": knife,
        "base_scale": knife.scale.copy(),
    }

def align_knife(knife):
    dimensions = [knife.dimensions.x, knife.dimensions.y, knife.dimensions.z]
    longest_axis = max(range(3), key=lambda index: dimensions[index])

    if longest_axis == 1:
        knife.rotation_euler.z = math.radians(-90)
        apply_transform(knife, rotation=True, scale=False)
    elif longest_axis == 2:
        knife.rotation_euler.y = math.radians(90)
        apply_transform(knife, rotation=True, scale=False)

    dimensions = [knife.dimensions.x, knife.dimensions.y, knife.dimensions.z]
    smallest_axis = min(range(3), key=lambda index: dimensions[index])

    if smallest_axis == 0:
        knife.rotation_euler.y = math.radians(90)
        apply_transform(knife, rotation=True, scale=False)
    elif smallest_axis == 1:
        knife.rotation_euler.x = math.radians(90)
        apply_transform(knife, rotation=True, scale=False)

def fix_normals(knife):
    bpy.ops.object.select_all(action="DESELECT")
    knife.select_set(True)
    bpy.context.view_layer.objects.active = knife
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")

    for polygon in knife.data.polygons:
        polygon.use_smooth = True

    if hasattr(knife.data, "use_auto_smooth"):
        knife.data.use_auto_smooth = True
        knife.data.auto_smooth_angle = math.radians(45)

    knife.select_set(False)

def world_bbox(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]

    return {
        "min": Vector((
            min(point.x for point in points),
            min(point.y for point in points),
            min(point.z for point in points)
        )),
        "max": Vector((
            max(point.x for point in points),
            max(point.y for point in points),
            max(point.z for point in points)
        )),
    }

def place_knife(model):
    knife = model["object"]
    knife.scale = model["base_scale"].copy()
    knife.location = Vector((
        random.uniform(-0.09, 0.09),
        random.uniform(-0.055, 0.055),
        0.0
    ))

    knife.rotation_euler = (
        math.radians(random.uniform(-0.6, 0.6)),
        math.radians(random.uniform(-0.6, 0.6)),
        math.radians(random.choice([
            random.uniform(-42, -18),
            random.uniform(-9, 9),
            random.uniform(18, 42),
            random.uniform(138, 160),
            random.uniform(200, 222),
            random.uniform(318, 340),
        ]))
    )

    scale_factor = random.uniform(0.95, 1.10)
    knife.scale = (
        model["base_scale"].x * scale_factor,
        model["base_scale"].y * scale_factor,
        model["base_scale"].z * scale_factor
    )

    bpy.context.view_layer.update()
    bbox = world_bbox(knife)
    knife.location.z += TABLE_TOP_Z + 0.003 - bbox["min"].z
    bpy.context.view_layer.update()

def calculate_yolo_bbox(scene, camera, knife):
    projected = []

    for corner in knife.bound_box:
        point = world_to_camera_view(
            scene,
            camera,
            knife.matrix_world @ Vector(corner)
        )

        if point.z <= 0:
            return None

        projected.append(point)

    min_x = min(point.x for point in projected)
    max_x = max(point.x for point in projected)
    min_y = min(point.y for point in projected)
    max_y = max(point.y for point in projected)

    width = max_x - min_x
    height = max_y - min_y

    return {
        "x_center": min_x + width / 2.0,
        "y_center": 1.0 - (min_y + height / 2.0),
        "width": width,
        "height": height,
        "min_x": min_x,
        "max_x": max_x,
        "min_y": min_y,
        "max_y": max_y,
    }

def fit_camera_and_get_bbox(scene, camera, knife):
    camera.data.ortho_scale = min(max(camera.data.ortho_scale, 0.58), 0.90)

    for _ in range(24):
        bpy.context.view_layer.update()
        bbox = calculate_yolo_bbox(scene, camera, knife)

        if bbox is None:
            camera.data.ortho_scale *= 1.06
            continue

        outside = (
            bbox["min_x"] < 0.035
            or bbox["max_x"] > 0.965
            or bbox["min_y"] < 0.035
            or bbox["max_y"] > 0.965
        )

        longest = max(bbox["width"], bbox["height"])

        if outside or longest > 0.72:
            camera.data.ortho_scale *= 1.055
            continue

        if longest < 0.38:
            camera.data.ortho_scale *= 0.95
            continue

        return bbox

    return calculate_yolo_bbox(scene, camera, knife)

def bbox_is_valid(bbox):
    if bbox is None:
        return False

    if bbox["min_x"] < 0.025 or bbox["max_x"] > 0.975:
        return False

    if bbox["min_y"] < 0.025 or bbox["max_y"] > 0.975:
        return False

    longest = max(bbox["width"], bbox["height"])

    if longest < 0.34 or longest > 0.76:
        return False

    if min(bbox["width"], bbox["height"]) < 0.008:
        return False

    return True

def image_path(index):
    return IMAGES_DIR / "faca_butter_knife_{:04d}.png".format(index)

def label_path(index):
    return LABELS_DIR / "faca_butter_knife_{:04d}.txt".format(index)

def pair_exists(index):
    return image_path(index).exists() and label_path(index).exists()

def render_image(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)

    if not path.exists():
        raise RuntimeError("A imagem não foi criada.")

def image_is_acceptable(path):
    image = bpy.data.images.load(str(path), check_existing=False)

    try:
        width = int(image.size[0])
        height = int(image.size[1])
        pixels = image.pixels

        total = 0
        luminance_sum = 0.0
        white_pixels = 0
        dark_pixels = 0

        for y in range(0, height, 20):
            for x in range(0, width, 20):
                offset = (y * width + x) * 4
                r = pixels[offset]
                g = pixels[offset + 1]
                b = pixels[offset + 2]
                luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b

                luminance_sum += luminance
                total += 1

                if luminance > 0.82:
                    white_pixels += 1

                if luminance < 0.015:
                    dark_pixels += 1

        if total == 0:
            return False

        mean_luminance = luminance_sum / total
        white_ratio = white_pixels / total
        dark_ratio = dark_pixels / total

        if mean_luminance > 0.30:
            return False

        if white_ratio > 0.015:
            return False

        if mean_luminance < 0.025:
            return False

        if dark_ratio > 0.80:
            return False

        return True

    finally:
        bpy.data.images.remove(image)

def write_label(path, bbox):
    path.write_text(
        "{} {:.6f} {:.6f} {:.6f} {:.6f}\n".format(
            CLASS_ID,
            bbox["x_center"],
            bbox["y_center"],
            bbox["width"],
            bbox["height"]
        ),
        encoding="utf-8"
    )

def save_blend():
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

def generate_one(index, refs, model):
    if pair_exists(index):
        return True

    scene = bpy.context.scene
    camera = refs["camera"]

    for attempt in range(1, MAX_ATTEMPTS + 1):
        random.seed(BASE_SEED + index * 1000 + attempt)
        randomize_scene(refs)
        place_knife(model)

        bbox = fit_camera_and_get_bbox(
            scene,
            camera,
            model["object"]
        )

        if not bbox_is_valid(bbox):
            continue

        final_image = image_path(index)
        render_image(final_image)

        if not image_is_acceptable(final_image):
            if final_image.exists():
                final_image.unlink()
            continue

        write_label(label_path(index), bbox)

        print("OK — {:04d} | tentativa {}".format(index, attempt))
        return True

    return False

def main():
    if not PROJECT_ROOT.exists():
        raise FileNotFoundError(PROJECT_ROOT)

    if not MODEL_PATH.exists():
        raise FileNotFoundError(MODEL_PATH)

    ensure_directories()
    remove_invalid_previous_pairs()
    save_current_script()
    clear_scene()
    configure_render()
    refs = create_scene()
    model = import_model()
    save_blend()

    print("Modelo:", MODEL_PATH)
    print("Imagens:", IMAGES_DIR)
    print("Labels:", LABELS_DIR)
    print("Índices: {}–{}".format(START_INDEX, END_INDEX))

    for index in range(START_INDEX, END_INDEX + 1):
        if not generate_one(index, refs, model):
            raise RuntimeError(
                "Não foi possível gerar a imagem {:04d} após {} tentativas.".format(
                    index,
                    MAX_ATTEMPTS
                )
            )

        if index % SAVE_BLEND_EVERY == 0 or index == END_INDEX:
            save_blend()

        print(
            "PROGRESSO: {}/{}".format(
                index - START_INDEX + 1,
                END_INDEX - START_INDEX + 1
            )
        )

    save_blend()
    print("Concluído.")

if __name__ == "__main__":
    main()