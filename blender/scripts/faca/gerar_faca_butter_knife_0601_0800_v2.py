import bpy
import math
import random
import shutil
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

PROJECT_ROOT = Path(r"C:\Users\pithe\Documents\Projetos\Github\fastcamp-projeto-final-visao-computacional")
MODEL_PATH = PROJECT_ROOT / "blender" / "assets" / "fbx" / "faca" / "butter_knife.glb"
SCRIPT_PATH = PROJECT_ROOT / "blender" / "scripts" / "gerar_faca_butter_knife_0601_0800_v2.py"
BLEND_PATH = PROJECT_ROOT / "blender" / "cenas" / "faca" / "faca_butter_knife_0601_0800_v2.blend"
IMAGES_DIR = PROJECT_ROOT / "dataset_lotes" / "faca" / "images"
LABELS_DIR = PROJECT_ROOT / "dataset_lotes" / "faca" / "labels"

CLASS_ID = 1
START_INDEX = 601
END_INDEX = 800
IMAGE_SIZE = 640
BASE_SEED = 2026080615
MAX_ATTEMPTS = 120
SAVE_BLEND_EVERY = 25
TABLE_TOP_Z = 0.355
TARGET_LENGTH = 0.46

WOOD_BASES = [
    ((0.11, 0.050, 0.018, 1.0), (0.22, 0.10, 0.04, 1.0)),
    ((0.09, 0.040, 0.015, 1.0), (0.20, 0.09, 0.035, 1.0)),
    ((0.10, 0.045, 0.016, 1.0), (0.24, 0.11, 0.045, 1.0)),
    ((0.08, 0.035, 0.012, 1.0), (0.18, 0.08, 0.030, 1.0)),
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

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for collection in [
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.lights,
        bpy.data.cameras,
        bpy.data.images,
    ]:
        for block in list(collection):
            if getattr(block, "users", 0) == 0:
                collection.remove(block)

def create_material(name):
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    return material

def create_background_material():
    material = create_material("Material_Fundo_Charcoal")
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    for node in list(nodes):
        nodes.remove(node)

    output = nodes.new(type="ShaderNodeOutputMaterial")
    principled = nodes.new(type="ShaderNodeBsdfPrincipled")

    output.location = (280, 0)
    principled.location = (0, 0)
    principled.inputs["Base Color"].default_value = (0.025, 0.028, 0.035, 1.0)
    principled.inputs["Roughness"].default_value = 1.0
    principled.inputs["Metallic"].default_value = 0.0

    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    return material

def create_wood_material():
    material = create_material("Material_Mesa_Madeira")
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

    mapping.inputs["Scale"].default_value = (8.0, 1.5, 2.4)
    noise.inputs["Scale"].default_value = 4.2
    noise.inputs["Detail"].default_value = 3.5
    noise.inputs["Roughness"].default_value = 0.55
    noise.inputs["Distortion"].default_value = 0.14

    bump_noise.inputs["Scale"].default_value = 70.0
    bump_noise.inputs["Detail"].default_value = 2.0
    bump_noise.inputs["Roughness"].default_value = 0.40

    bump.inputs["Strength"].default_value = 0.06
    bump.inputs["Distance"].default_value = 0.02

    principled.inputs["Roughness"].default_value = 0.70
    principled.inputs["Metallic"].default_value = 0.0
    if "Specular" in principled.inputs:
        principled.inputs["Specular"].default_value = 0.28

    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[0].color = WOOD_BASES[0][0]
    ramp.color_ramp.elements[1].color = WOOD_BASES[0][1]

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
    dark, light = random.choice(WOOD_BASES)
    ramp.color_ramp.elements[0].color = dark
    ramp.color_ramp.elements[1].color = light
    noise.inputs["Scale"].default_value = random.uniform(3.6, 4.8)
    noise.inputs["Detail"].default_value = random.uniform(2.8, 4.0)
    noise.inputs["Distortion"].default_value = random.uniform(0.08, 0.18)

def create_steel_material():
    material = create_material("Material_ButterKnife_Steel")
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

    principled.inputs["Base Color"].default_value = (0.62, 0.64, 0.67, 1.0)
    principled.inputs["Metallic"].default_value = 0.88
    principled.inputs["Roughness"].default_value = 0.26
    if "Specular" in principled.inputs:
        principled.inputs["Specular"].default_value = 0.46

    noise.inputs["Scale"].default_value = 180.0
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Roughness"].default_value = 0.35

    bump.inputs["Strength"].default_value = 0.010
    bump.inputs["Distance"].default_value = 0.04

    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], principled.inputs["Normal"])
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    return material

def look_at(obj, target):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

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

    scene.view_settings.exposure = -0.65
    scene.view_settings.gamma = 1.0

    try:
        scene.eevee.taa_render_samples = 64
        scene.eevee.use_gtao = True
        scene.eevee.gtao_distance = 0.24
        scene.eevee.gtao_factor = 1.20
        scene.eevee.use_soft_shadows = True
        scene.eevee.shadow_cube_size = "1024"
        scene.eevee.shadow_cascade_size = "1024"
    except Exception:
        pass

    if scene.world is None:
        scene.world = bpy.data.worlds.new("World_ButterKnife_V2")

    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Color"].default_value = (0.020, 0.023, 0.028, 1.0)
        background.inputs["Strength"].default_value = 0.030

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

    bpy.ops.object.light_add(type="AREA", location=(0.52, -0.42, 1.06))
    key = bpy.context.active_object
    key.name = "Luz_Principal"
    key.data.energy = 210
    key.data.size = 0.95

    bpy.ops.object.light_add(type="AREA", location=(-0.52, -0.08, 0.88))
    fill = bpy.context.active_object
    fill.name = "Luz_Preenchimento"
    fill.data.energy = 85
    fill.data.size = 1.10

    bpy.ops.object.light_add(type="POINT", location=(0.0, 0.26, 0.95))
    rim = bpy.context.active_object
    rim.name = "Luz_Contorno"
    rim.data.energy = 25

    bpy.ops.object.light_add(type="AREA", location=(0.0, -0.05, 1.30))
    top = bpy.context.active_object
    top.name = "Luz_Superior"
    top.data.energy = 130
    top.data.size = 1.60

    bpy.ops.object.camera_add(location=(0.0, -0.72, 0.80))
    camera = bpy.context.active_object
    camera.name = "Camera"
    camera.data.lens = 58
    look_at(camera, Vector((0.0, 0.0, TABLE_TOP_Z + 0.012)))
    bpy.context.scene.camera = camera

    refs["wood_ramp"] = wood_ramp
    refs["wood_noise"] = wood_noise
    refs["key"] = key
    refs["fill"] = fill
    refs["rim"] = rim
    refs["top"] = top
    refs["camera"] = camera

    return refs

def randomize_scene(refs):
    set_wood_style(refs["wood_ramp"], refs["wood_noise"])

    refs["key"].data.energy = random.uniform(180, 240)
    refs["key"].location = Vector((
        random.uniform(0.38, 0.60),
        random.uniform(-0.52, -0.30),
        random.uniform(0.96, 1.14)
    ))

    refs["fill"].data.energy = random.uniform(65, 100)
    refs["fill"].location = Vector((
        random.uniform(-0.60, -0.34),
        random.uniform(-0.18, 0.02),
        random.uniform(0.78, 0.95)
    ))

    refs["rim"].data.energy = random.uniform(18, 32)
    refs["rim"].location = Vector((
        random.uniform(-0.08, 0.08),
        random.uniform(0.18, 0.32),
        random.uniform(0.84, 0.98)
    ))

    refs["top"].data.energy = random.uniform(105, 150)
    refs["top"].location = Vector((
        random.uniform(-0.10, 0.10),
        random.uniform(-0.10, 0.10),
        random.uniform(1.22, 1.36)
    ))

    camera = refs["camera"]
    camera.location = Vector((
        random.uniform(-0.045, 0.045),
        random.uniform(-0.76, -0.67),
        random.uniform(0.76, 0.86)
    ))
    camera.data.lens = random.uniform(56, 62)

    look_at(
        camera,
        Vector((
            random.uniform(-0.025, 0.025),
            random.uniform(-0.015, 0.015),
            TABLE_TOP_Z + random.uniform(0.004, 0.018)
        ))
    )

def import_model():
    before_names = set(obj.name for obj in bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(MODEL_PATH))
    imported = [obj for obj in bpy.data.objects if obj.name not in before_names]

    for obj in list(imported):
        if obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)

    imported = [obj for obj in imported if obj.name in bpy.data.objects]
    meshes = [obj for obj in imported if obj.type == "MESH"]

    if not meshes:
        raise RuntimeError("O arquivo GLB não possui malhas utilizáveis.")

    root = bpy.data.objects.new("ROOT_ButterKnife", None)
    bpy.context.scene.collection.objects.link(root)
    imported_set = set(imported)

    for obj in imported:
        if obj.parent not in imported_set:
            obj.parent = root

    bpy.context.view_layer.update()
    orient_group(root)
    center_group(root)
    scale_group(root, TARGET_LENGTH)
    replace_materials(root)
    fix_normals(root)
    center_group(root)

    return {
        "root": root,
        "base_rotation": root.rotation_euler.copy(),
        "base_scale": root.scale.copy(),
    }

def get_descendants(root):
    result = []
    stack = list(root.children)
    while stack:
        obj = stack.pop()
        result.append(obj)
        stack.extend(list(obj.children))
    return result

def get_meshes(root):
    return [obj for obj in get_descendants(root) if obj.type == "MESH"]

def group_bbox(root):
    points = []
    for obj in get_meshes(root):
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))

    if not points:
        return None

    min_x = min(point.x for point in points)
    max_x = max(point.x for point in points)
    min_y = min(point.y for point in points)
    max_y = max(point.y for point in points)
    min_z = min(point.z for point in points)
    max_z = max(point.z for point in points)

    return {
        "min": Vector((min_x, min_y, min_z)),
        "max": Vector((max_x, max_y, max_z)),
        "center": Vector(((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0)),
        "size": Vector((max_x - min_x, max_y - min_y, max_z - min_z)),
    }

def orient_group(root):
    candidates = [0.0, math.radians(90), math.radians(180), math.radians(270)]
    best_rotation = None
    best_score = None

    for rx in candidates:
        for ry in candidates:
            for rz in candidates:
                root.rotation_euler = (rx, ry, rz)
                bpy.context.view_layer.update()
                bbox = group_bbox(root)

                if bbox is None:
                    continue

                sx = bbox["size"].x
                sy = bbox["size"].y
                sz = bbox["size"].z

                longest_bonus = sx / max(sy, 1e-6)
                flat_bonus = sx / max(sz, 1e-6)
                thickness_penalty = sz * 10.0
                score = longest_bonus + flat_bonus - thickness_penalty

                if best_score is None or score > best_score:
                    best_score = score
                    best_rotation = (rx, ry, rz)

    if best_rotation is None:
        raise RuntimeError("Não foi possível orientar a faca.")

    root.rotation_euler = best_rotation
    bpy.context.view_layer.update()

def center_group(root):
    bbox = group_bbox(root)
    if bbox is None:
        raise RuntimeError("Não foi possível centralizar a faca.")

    root.location.x -= bbox["center"].x
    root.location.y -= bbox["center"].y
    root.location.z -= bbox["min"].z
    bpy.context.view_layer.update()

def scale_group(root, target_length):
    bbox = group_bbox(root)
    if bbox is None:
        raise RuntimeError("Não foi possível medir a faca.")

    longest = max(bbox["size"].x, bbox["size"].y, bbox["size"].z)
    if longest <= 0:
        raise RuntimeError("Dimensões inválidas da faca.")

    factor = target_length / longest
    root.scale = (
        root.scale.x * factor,
        root.scale.y * factor,
        root.scale.z * factor
    )
    bpy.context.view_layer.update()

def replace_materials(root):
    steel = create_steel_material()

    for mesh in get_meshes(root):
        mesh.data.materials.clear()
        mesh.data.materials.append(steel)

def fix_normals(root):
    for mesh in get_meshes(root):
        bpy.context.view_layer.objects.active = mesh
        bpy.ops.object.select_all(action="DESELECT")
        mesh.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        mesh.select_set(False)

        for polygon in mesh.data.polygons:
            polygon.use_smooth = True

        if hasattr(mesh.data, "use_auto_smooth"):
            mesh.data.use_auto_smooth = True
            mesh.data.auto_smooth_angle = math.radians(50)

def place_model(model):
    root = model["root"]
    root.rotation_euler = model["base_rotation"].copy()
    root.scale = model["base_scale"].copy()
    root.location = Vector((
        random.uniform(-0.11, 0.11),
        random.uniform(-0.070, 0.070),
        0.0
    ))

    root.rotation_euler.x += math.radians(random.uniform(-0.8, 0.8))
    root.rotation_euler.y += math.radians(random.uniform(-0.8, 0.8))
    root.rotation_euler.z += math.radians(random.choice([
        random.uniform(-42, -18),
        random.uniform(-10, 10),
        random.uniform(18, 42),
        random.uniform(138, 160),
        random.uniform(200, 222),
        random.uniform(318, 340),
    ]))

    scale_factor = random.uniform(0.96, 1.12)
    root.scale = (
        model["base_scale"].x * scale_factor,
        model["base_scale"].y * scale_factor,
        model["base_scale"].z * scale_factor
    )

    bpy.context.view_layer.update()
    bbox = group_bbox(root)
    if bbox is None:
        return False

    root.location.z += TABLE_TOP_Z + 0.003 - bbox["min"].z
    bpy.context.view_layer.update()
    return True

def calculate_yolo_bbox(scene, camera, root):
    projected = []

    for obj in get_meshes(root):
        for corner in obj.bound_box:
            point = world_to_camera_view(scene, camera, obj.matrix_world @ Vector(corner))
            if point.z <= 0:
                return None
            projected.append(point)

    if not projected:
        return None

    min_x = min(point.x for point in projected)
    max_x = max(point.x for point in projected)
    min_y = min(point.y for point in projected)
    max_y = max(point.y for point in projected)

    width = max_x - min_x
    height = max_y - min_y

    if width <= 0 or height <= 0:
        return None

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

def bbox_is_valid(bbox):
    if bbox is None:
        return False

    if bbox["min_x"] < 0.03 or bbox["max_x"] > 0.97:
        return False

    if bbox["min_y"] < 0.03 or bbox["max_y"] > 0.97:
        return False

    longest = max(bbox["width"], bbox["height"])
    shortest = min(bbox["width"], bbox["height"])
    area = bbox["width"] * bbox["height"]

    if longest < 0.34 or longest > 0.78:
        return False

    if shortest < 0.010:
        return False

    if area < 0.008:
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

    rejected_position = 0
    rejected_bbox = 0

    for attempt in range(1, MAX_ATTEMPTS + 1):
        random.seed(BASE_SEED + index * 1000 + attempt)
        randomize_scene(refs)

        if not place_model(model):
            rejected_position += 1
            continue

        bpy.context.view_layer.update()
        bbox = calculate_yolo_bbox(bpy.context.scene, refs["camera"], model["root"])

        if not bbox_is_valid(bbox):
            rejected_bbox += 1
            continue

        render_image(image_path(index))
        write_label(label_path(index), bbox)

        print("OK — {:04d} | tentativa {}".format(index, attempt))
        return True

    print("REJEIÇÕES — posição: {} | bbox: {}".format(rejected_position, rejected_bbox))
    return False

def main():
    if not PROJECT_ROOT.exists():
        raise FileNotFoundError(PROJECT_ROOT)

    if not MODEL_PATH.exists():
        raise FileNotFoundError(MODEL_PATH)

    ensure_directories()
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
            raise RuntimeError("Não foi possível gerar a imagem {:04d}.".format(index))

        if index % SAVE_BLEND_EVERY == 0 or index == END_INDEX:
            save_blend()

        print("PROGRESSO: {}/{}".format(index - START_INDEX + 1, END_INDEX - START_INDEX + 1))

    save_blend()
    print("Concluído.")

if __name__ == "__main__":
    main()