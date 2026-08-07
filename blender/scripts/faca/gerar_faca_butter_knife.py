import bpy
import math
import random
import shutil
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

PROJECT_ROOT = Path(r"C:\Users\pithe\Documents\Projetos\Github\fastcamp-projeto-final-visao-computacional")
MODEL_PATH = PROJECT_ROOT / "blender" / "assets" / "fbx" / "faca" / "butter_knife.glb"
SCRIPT_PATH = PROJECT_ROOT / "blender" / "scripts" / "gerar_faca_butter_knife.py"
BLEND_PATH = PROJECT_ROOT / "blender" / "cenas" / "faca" / "faca_butter_knife_dataset.blend"
IMAGES_DIR = PROJECT_ROOT / "dataset_lotes" / "faca" / "images"
LABELS_DIR = PROJECT_ROOT / "dataset_lotes" / "faca" / "labels"
TEMP_DIR = PROJECT_ROOT / "resultados" / "temporarios" / "faca_butter_knife"
TEMP_IMAGE_PATH = TEMP_DIR / "render_temporario.png"

CLASS_ID = 1
START_INDEX = 601
END_INDEX = 800
IMAGE_SIZE = 640
BASE_SEED = 2026080603
MAX_ATTEMPTS = 120
SAVE_BLEND_EVERY = 25
TARGET_LENGTH = 0.38
TABLE_TOP_Z = 0.36

WOOD_DARK = [
    ((0.065, 0.021, 0.006, 1.0), (0.145, 0.062, 0.018, 1.0)),
    ((0.080, 0.028, 0.007, 1.0), (0.175, 0.078, 0.022, 1.0)),
    ((0.055, 0.017, 0.004, 1.0), (0.125, 0.050, 0.014, 1.0)),
    ((0.095, 0.034, 0.009, 1.0), (0.195, 0.088, 0.026, 1.0)),
]

def ensure_directories():
    SCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

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
    ]:
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)

def create_principled_material(name, color, roughness, metallic):
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")

    if principled is not None:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Roughness"].default_value = roughness
        principled.inputs["Metallic"].default_value = metallic
        if "Specular" in principled.inputs:
            principled.inputs["Specular"].default_value = 0.35

    return material

def create_black_material():
    return create_principled_material(
        "Material_Fundo_Preto",
        (0.003, 0.003, 0.004, 1.0),
        1.0,
        0.0
    )

def create_wood_material():
    material = bpy.data.materials.new(name="Material_Mesa_Caramelo_Escuro")
    material.use_nodes = True
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

    output.location = (650, 0)
    principled.location = (380, 0)
    texcoord.location = (-900, 0)
    mapping.location = (-700, 0)
    noise.location = (-470, 100)
    ramp.location = (-220, 100)
    bump_noise.location = (-450, -190)
    bump.location = (120, -170)

    mapping.inputs["Scale"].default_value = (7.0, 1.35, 2.0)
    noise.inputs["Scale"].default_value = 3.8
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Roughness"].default_value = 0.58
    noise.inputs["Distortion"].default_value = 0.18

    bump_noise.inputs["Scale"].default_value = 55.0
    bump_noise.inputs["Detail"].default_value = 2.0
    bump_noise.inputs["Roughness"].default_value = 0.45

    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.025

    principled.inputs["Roughness"].default_value = 0.68
    principled.inputs["Metallic"].default_value = 0.0
    if "Specular" in principled.inputs:
        principled.inputs["Specular"].default_value = 0.28

    ramp.color_ramp.elements[0].color = WOOD_DARK[0][0]
    ramp.color_ramp.elements[1].color = WOOD_DARK[0][1]
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[1].position = 0.72

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
    dark, light = random.choice(WOOD_DARK)
    ramp.color_ramp.elements[0].color = dark
    ramp.color_ramp.elements[1].color = light
    noise.inputs["Scale"].default_value = random.uniform(3.2, 4.8)
    noise.inputs["Detail"].default_value = random.uniform(2.2, 3.8)
    noise.inputs["Distortion"].default_value = random.uniform(0.08, 0.22)

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
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False

    try:
        scene.view_settings.view_transform = "Filmic"
        scene.view_settings.look = "Medium High Contrast"
    except Exception:
        pass

    scene.view_settings.exposure = -1.05
    scene.view_settings.gamma = 1.0

    try:
        scene.eevee.taa_render_samples = 64
        scene.eevee.use_gtao = True
        scene.eevee.gtao_distance = 0.24
        scene.eevee.gtao_factor = 1.25
        scene.eevee.use_soft_shadows = True
    except Exception:
        pass

    if scene.world is None:
        scene.world = bpy.data.worlds.new("World_ButterKnife")

    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")

    if background is not None:
        background.inputs["Color"].default_value = (0.0015, 0.0015, 0.002, 1.0)
        background.inputs["Strength"].default_value = 0.018

def create_scene():
    refs = {}

    bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, TABLE_TOP_Z - 0.04))
    table = bpy.context.active_object
    table.name = "Mesa"
    table.scale = (0.68, 0.46, 0.04)
    wood_material, wood_ramp, wood_noise = create_wood_material()
    table.data.materials.append(wood_material)

    bpy.ops.mesh.primitive_plane_add(
        location=(0.0, 0.58, 0.88),
        rotation=(math.radians(90), 0.0, 0.0)
    )
    backdrop = bpy.context.active_object
    backdrop.name = "Fundo_Preto"
    backdrop.scale = (1.9, 1.45, 1.0)
    backdrop.data.materials.append(create_black_material())

    bpy.ops.object.light_add(type="AREA", location=(0.46, -0.42, 0.98))
    key = bpy.context.active_object
    key.name = "Luz_Principal"
    key.data.energy = 115
    key.data.size = 0.84

    bpy.ops.object.light_add(type="AREA", location=(-0.43, -0.10, 0.78))
    fill = bpy.context.active_object
    fill.name = "Luz_Preenchimento"
    fill.data.energy = 30
    fill.data.size = 1.00

    bpy.ops.object.light_add(type="POINT", location=(0.0, 0.24, 0.90))
    rim = bpy.context.active_object
    rim.name = "Luz_Contorno"
    rim.data.energy = 10

    bpy.ops.object.camera_add(location=(0.0, -0.82, 0.89))
    camera = bpy.context.active_object
    camera.name = "Camera"
    camera.data.lens = 63
    look_at(camera, Vector((0.0, 0.0, TABLE_TOP_Z + 0.014)))
    bpy.context.scene.camera = camera

    refs["wood_ramp"] = wood_ramp
    refs["wood_noise"] = wood_noise
    refs["key"] = key
    refs["fill"] = fill
    refs["rim"] = rim
    refs["camera"] = camera

    return refs

def randomize_scene(refs):
    set_wood_style(refs["wood_ramp"], refs["wood_noise"])

    refs["key"].data.energy = random.uniform(95, 135)
    refs["key"].location = Vector((
        random.uniform(0.34, 0.58),
        random.uniform(-0.56, -0.32),
        random.uniform(0.88, 1.04)
    ))

    refs["fill"].data.energy = random.uniform(20, 38)
    refs["fill"].location = Vector((
        random.uniform(-0.56, -0.32),
        random.uniform(-0.22, 0.01),
        random.uniform(0.69, 0.87)
    ))

    refs["rim"].data.energy = random.uniform(5, 14)
    refs["rim"].location = Vector((
        random.uniform(-0.10, 0.10),
        random.uniform(0.18, 0.32),
        random.uniform(0.80, 0.95)
    ))

    camera = refs["camera"]
    camera.location = Vector((
        random.uniform(-0.055, 0.055),
        random.uniform(-0.88, -0.77),
        random.uniform(0.83, 0.93)
    ))
    camera.data.lens = random.uniform(59, 68)

    look_at(
        camera,
        Vector((
            random.uniform(-0.028, 0.028),
            random.uniform(-0.018, 0.018),
            TABLE_TOP_Z + random.uniform(0.006, 0.020)
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
    neutralize_materials(root)
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
                score = (sx / max(sz, 1e-6)) + (sx / max(sy, 1e-6)) - (sz * 8.0)

                if best_score is None or score > best_score:
                    best_score = score
                    best_rotation = (rx, ry, rz)

    if best_rotation is None:
        raise RuntimeError("Não foi possível determinar a orientação da faca.")

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
        raise RuntimeError("O modelo possui dimensões inválidas.")

    factor = target_length / longest
    root.scale = (
        root.scale.x * factor,
        root.scale.y * factor,
        root.scale.z * factor
    )
    bpy.context.view_layer.update()

def neutralize_materials(root):
    fallback = create_principled_material(
        "Material_Faca_Neutro",
        (0.18, 0.20, 0.22, 1.0),
        0.38,
        0.72
    )

    for mesh in get_meshes(root):
        if len(mesh.data.materials) == 0:
            mesh.data.materials.append(fallback)
            continue

        for material in mesh.data.materials:
            if material is None:
                continue

            if not material.use_nodes:
                material.use_nodes = True

            principled = material.node_tree.nodes.get("Principled BSDF")

            if principled is None:
                continue

            name = material.name.lower().replace(" ", "_").replace("-", "_")
            is_handle = any(token in name for token in ["handle", "grip", "cabo", "wood", "plastic", "black"])

            base_input = principled.inputs.get("Base Color")
            roughness_input = principled.inputs.get("Roughness")
            metallic_input = principled.inputs.get("Metallic")

            if is_handle and base_input is not None and not base_input.is_linked:
                base_input.default_value = (0.012, 0.012, 0.014, 1.0)

            if roughness_input is not None and not roughness_input.is_linked:
                roughness_input.default_value = 0.68 if is_handle else 0.38

            if metallic_input is not None and not metallic_input.is_linked and not is_handle:
                metallic_input.default_value = max(metallic_input.default_value, 0.55)

            if "Specular" in principled.inputs:
                principled.inputs["Specular"].default_value = 0.38

def place_model(model):
    root = model["root"]
    root.rotation_euler = model["base_rotation"].copy()
    root.scale = model["base_scale"].copy()
    root.location = Vector((
        random.uniform(-0.10, 0.10),
        random.uniform(-0.068, 0.068),
        0.0
    ))

    root.rotation_euler.x += math.radians(random.uniform(-1.0, 1.0))
    root.rotation_euler.y += math.radians(random.uniform(-1.0, 1.0))
    root.rotation_euler.z += math.radians(random.choice([
        random.uniform(-48, -18),
        random.uniform(-10, 10),
        random.uniform(18, 48),
        random.uniform(132, 160),
        random.uniform(200, 228),
        random.uniform(312, 340)
    ]))

    scale_factor = random.uniform(0.94, 1.10)
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

    margin = 0.045
    longest = max(bbox["width"], bbox["height"])
    shortest = min(bbox["width"], bbox["height"])

    if bbox["min_x"] < margin or bbox["max_x"] > 1.0 - margin:
        return False

    if bbox["min_y"] < margin or bbox["max_y"] > 1.0 - margin:
        return False

    if longest < 0.20 or longest > 0.72:
        return False

    if shortest < 0.006:
        return False

    return True

def image_path(index):
    return IMAGES_DIR / "faca_butter_knife_{:04d}.png".format(index)

def label_path(index):
    return LABELS_DIR / "faca_butter_knife_{:04d}.txt".format(index)

def pair_exists(index):
    return image_path(index).exists() and label_path(index).exists()

def render_temp():
    bpy.context.scene.render.filepath = str(TEMP_IMAGE_PATH)
    bpy.ops.render.render(write_still=True)

    if not TEMP_IMAGE_PATH.exists():
        raise RuntimeError("A imagem temporária não foi criada.")

def sample_luminance(image, x0, y0, x1, y1, samples_x, samples_y):
    width = int(image.size[0])
    height = int(image.size[1])
    pixels = image.pixels

    x0 = max(0, min(width - 1, int(x0)))
    x1 = max(0, min(width, int(x1)))
    y0 = max(0, min(height - 1, int(y0)))
    y1 = max(0, min(height, int(y1)))

    if x1 <= x0 or y1 <= y0:
        return 0.0, 0.0

    total_luminance = 0.0
    white_count = 0
    total = 0

    for iy in range(samples_y):
        py = y0 + int((y1 - y0 - 1) * iy / max(samples_y - 1, 1))

        for ix in range(samples_x):
            px = x0 + int((x1 - x0 - 1) * ix / max(samples_x - 1, 1))
            offset = (py * width + px) * 4
            r = pixels[offset]
            g = pixels[offset + 1]
            b = pixels[offset + 2]
            luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
            total_luminance += luminance
            total += 1

            if luminance > 0.92:
                white_count += 1

    if total == 0:
        return 0.0, 0.0

    return total_luminance / total, white_count / total

def lighting_is_valid(bbox):
    image = bpy.data.images.load(str(TEMP_IMAGE_PATH), check_existing=False)

    try:
        width = int(image.size[0])
        height = int(image.size[1])

        full_mean, full_white = sample_luminance(
            image,
            0,
            0,
            width,
            height,
            32,
            32
        )

        if full_mean > 0.62:
            return False

        if full_white > 0.18:
            return False

        return True

    finally:
        bpy.data.images.remove(image)

def save_final_image(final_path):
    if final_path.exists():
        final_path.unlink()

    shutil.move(str(TEMP_IMAGE_PATH), str(final_path))

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
    rejected_light = 0

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

        render_temp()

        if not lighting_is_valid(bbox):
            rejected_light += 1
            continue

        save_final_image(image_path(index))
        write_label(label_path(index), bbox)

        print("OK — {:04d} | tentativa {}".format(index, attempt))
        return True

    print(
        "REJEIÇÕES — posição: {} | bbox: {} | iluminação: {}".format(
            rejected_position,
            rejected_bbox,
            rejected_light
        )
    )
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