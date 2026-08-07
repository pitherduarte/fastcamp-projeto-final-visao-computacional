import bpy
import math
import random
import shutil
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

PROJECT_ROOT = Path(r"C:\Users\pithe\Documents\Projetos\Github\fastcamp-projeto-final-visao-computacional")
MODEL_PATH = PROJECT_ROOT / "blender" / "assets" / "fbx" / "faca" / "KitchenKnife.fbx"
SCRIPT_PATH = PROJECT_ROOT / "blender" / "scripts" / "gerar_faca_kitchenknife_0801_1000_mesmo_codigo.py"
BLEND_PATH = PROJECT_ROOT / "blender" / "cenas" / "faca" / "faca_kitchenknife_0801_1000_mesmo_codigo.blend"
IMAGES_DIR = PROJECT_ROOT / "dataset_lotes" / "faca" / "images"
LABELS_DIR = PROJECT_ROOT / "dataset_lotes" / "faca" / "labels"

CLASS_ID = 1
START_INDEX = 801
END_INDEX = 1000
IMAGE_SIZE = 640
BASE_SEED = 20260807
MAX_ATTEMPTS = 70
SAVE_BLEND_EVERY = 25
TARGET_LENGTH = 0.34
TABLE_TOP_Z = 0.36

WOOD_COLORS = [
    (0.075, 0.028, 0.008),
    (0.090, 0.035, 0.010),
    (0.105, 0.040, 0.012),
    (0.120, 0.046, 0.014),
    (0.085, 0.032, 0.009),
]

BLADE_COLORS = [
    (0.18, 0.20, 0.22),
    (0.22, 0.24, 0.27),
    (0.26, 0.28, 0.31),
    (0.16, 0.18, 0.20),
]

HANDLE_COLORS = [
    (0.010, 0.010, 0.011),
    (0.015, 0.015, 0.017),
    (0.022, 0.018, 0.016),
    (0.028, 0.020, 0.016),
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

def create_material(name, color, roughness, metallic, specular=0.40):
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")

    if principled is not None:
        principled.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
        principled.inputs["Roughness"].default_value = roughness
        principled.inputs["Metallic"].default_value = metallic
        if "Specular" in principled.inputs:
            principled.inputs["Specular"].default_value = specular

    return material

def create_background_material():
    material = bpy.data.materials.new(name="Material_Fundo_Escuro")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    for node in list(nodes):
        nodes.remove(node)

    output = nodes.new(type="ShaderNodeOutputMaterial")
    emission = nodes.new(type="ShaderNodeEmission")
    emission.inputs["Color"].default_value = (0.002, 0.002, 0.0025, 1.0)
    emission.inputs["Strength"].default_value = 0.05

    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material

def set_material_color(material, color):
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)

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

    scene.view_settings.exposure = -0.90
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
        scene.world = bpy.data.worlds.new("World_KitchenKnife")

    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")

    if background is not None:
        background.inputs["Color"].default_value = (0.001, 0.001, 0.0015, 1.0)
        background.inputs["Strength"].default_value = 0.015

def create_scene():
    refs = {}

    bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, TABLE_TOP_Z - 0.04))
    table = bpy.context.active_object
    table.name = "Mesa"
    table.scale = (0.68, 0.46, 0.04)
    table_material = create_material("Material_Mesa", WOOD_COLORS[0], 0.66, 0.0, 0.30)
    table.data.materials.append(table_material)

    bpy.ops.mesh.primitive_plane_add(
        location=(0.0, 0.58, 0.88),
        rotation=(math.radians(90), 0.0, 0.0)
    )
    backdrop = bpy.context.active_object
    backdrop.name = "Fundo"
    backdrop.scale = (1.9, 1.45, 1.0)
    backdrop.data.materials.append(create_background_material())

    bpy.ops.object.light_add(type="AREA", location=(0.46, -0.42, 0.98))
    key = bpy.context.active_object
    key.name = "Luz_Principal"
    key.data.energy = 150
    key.data.size = 0.78

    bpy.ops.object.light_add(type="AREA", location=(-0.42, -0.12, 0.78))
    fill = bpy.context.active_object
    fill.name = "Luz_Preenchimento"
    fill.data.energy = 42
    fill.data.size = 0.96

    bpy.ops.object.light_add(type="POINT", location=(0.0, 0.24, 0.90))
    rim = bpy.context.active_object
    rim.name = "Luz_Contorno"
    rim.data.energy = 16

    bpy.ops.object.camera_add(location=(0.0, -0.80, 0.88))
    camera = bpy.context.active_object
    camera.name = "Camera"
    camera.data.lens = 64
    look_at(camera, Vector((0.0, 0.0, TABLE_TOP_Z + 0.016)))
    bpy.context.scene.camera = camera

    refs["table_material"] = table_material
    refs["key"] = key
    refs["fill"] = fill
    refs["rim"] = rim
    refs["camera"] = camera

    return refs

def randomize_scene(refs):
    set_material_color(refs["table_material"], random.choice(WOOD_COLORS))

    refs["key"].data.energy = random.uniform(130, 180)
    refs["key"].location = Vector((
        random.uniform(0.34, 0.58),
        random.uniform(-0.56, -0.32),
        random.uniform(0.88, 1.04)
    ))

    refs["fill"].data.energy = random.uniform(28, 55)
    refs["fill"].location = Vector((
        random.uniform(-0.56, -0.30),
        random.uniform(-0.22, 0.02),
        random.uniform(0.68, 0.88)
    ))

    refs["rim"].data.energy = random.uniform(8, 20)
    refs["rim"].location = Vector((
        random.uniform(-0.10, 0.10),
        random.uniform(0.18, 0.32),
        random.uniform(0.80, 0.96)
    ))

    camera = refs["camera"]
    camera.location = Vector((
        random.uniform(-0.05, 0.05),
        random.uniform(-0.86, -0.74),
        random.uniform(0.82, 0.92)
    ))
    camera.data.lens = random.uniform(60, 70)

    look_at(
        camera,
        Vector((
            random.uniform(-0.028, 0.028),
            random.uniform(-0.018, 0.018),
            TABLE_TOP_Z + random.uniform(0.006, 0.022)
        ))
    )

def import_and_join_model():
    before = set(obj.name for obj in bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(MODEL_PATH))

    imported_meshes = [
        obj for obj in bpy.data.objects
        if obj.name not in before and obj.type == "MESH"
    ]

    if not imported_meshes:
        raise RuntimeError("Nenhuma malha foi importada do FBX.")

    bpy.ops.object.select_all(action="DESELECT")
    for obj in imported_meshes:
        obj.select_set(True)

    bpy.context.view_layer.objects.active = imported_meshes[0]
    bpy.ops.object.join()

    knife = bpy.context.active_object
    knife.name = "KitchenKnife"

    apply_transform(knife, rotation=True, scale=True)

    dimensions = [knife.dimensions.x, knife.dimensions.y, knife.dimensions.z]
    longest_axis = max(range(3), key=lambda i: dimensions[i])

    if longest_axis == 1:
        knife.rotation_euler.z = math.radians(-90)
        apply_transform(knife, rotation=True, scale=False)
    elif longest_axis == 2:
        knife.rotation_euler.y = math.radians(90)
        apply_transform(knife, rotation=True, scale=False)

    dimensions = [knife.dimensions.x, knife.dimensions.y, knife.dimensions.z]
    smallest_axis = min(range(3), key=lambda i: dimensions[i])

    if smallest_axis == 1:
        knife.rotation_euler.x = math.radians(90)
        apply_transform(knife, rotation=True, scale=False)
    elif smallest_axis == 0:
        knife.rotation_euler.y = math.radians(90)
        apply_transform(knife, rotation=True, scale=False)

    bpy.ops.object.select_all(action="DESELECT")
    knife.select_set(True)
    bpy.context.view_layer.objects.active = knife
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    knife.location = Vector((0.0, 0.0, 0.0))

    longest_dimension = max(knife.dimensions.x, knife.dimensions.y, knife.dimensions.z)
    if longest_dimension <= 0:
        raise RuntimeError("Dimensões inválidas do modelo.")

    factor = TARGET_LENGTH / longest_dimension
    knife.scale = (factor, factor, factor)
    apply_transform(knife, rotation=False, scale=True)

    assign_materials(knife)

    for polygon in knife.data.polygons:
        polygon.use_smooth = True

    bpy.context.view_layer.update()
    bbox = world_bbox(knife)
    knife.location.z = TABLE_TOP_Z + 0.003 - bbox["min"].z
    bpy.context.view_layer.update()

    return {
        "object": knife,
        "base_scale": knife.scale.copy()
    }

def assign_materials(knife):
    blade_material = create_material(
        "Material_Lamina",
        random.choice(BLADE_COLORS),
        random.uniform(0.34, 0.48),
        random.uniform(0.55, 0.72),
        0.42
    )

    handle_material = create_material(
        "Material_Cabo",
        random.choice(HANDLE_COLORS),
        random.uniform(0.70, 0.84),
        0.01,
        0.20
    )

    knife.data.materials.clear()
    knife.data.materials.append(blade_material)
    knife.data.materials.append(handle_material)

    vertices = knife.data.vertices
    xs = [v.co.x for v in vertices]
    min_x = min(xs)
    max_x = max(xs)
    length = max_x - min_x
    band = length * 0.20

    min_vertices = [v.co for v in vertices if v.co.x <= min_x + band]
    max_vertices = [v.co for v in vertices if v.co.x >= max_x - band]

    def end_score(points):
        if not points:
            return 0.0
        y_span = max(p.y for p in points) - min(p.y for p in points)
        z_span = max(p.z for p in points) - min(p.z for p in points)
        return y_span * max(z_span, 1e-6)

    handle_at_min = end_score(min_vertices) >= end_score(max_vertices)
    handle_fraction = 0.34

    for polygon in knife.data.polygons:
        center_x = sum(vertices[index].co.x for index in polygon.vertices) / len(polygon.vertices)

        if handle_at_min:
            is_handle = center_x <= min_x + length * handle_fraction
        else:
            is_handle = center_x >= max_x - length * handle_fraction

        polygon.material_index = 1 if is_handle else 0

def refresh_materials(knife):
    assign_materials(knife)

def world_bbox(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return {
        "min": Vector((
            min(p.x for p in points),
            min(p.y for p in points),
            min(p.z for p in points)
        )),
        "max": Vector((
            max(p.x for p in points),
            max(p.y for p in points),
            max(p.z for p in points)
        )),
    }

def place_knife(model):
    knife = model["object"]
    knife.scale = model["base_scale"].copy()
    knife.location = Vector((
        random.uniform(-0.10, 0.10),
        random.uniform(-0.070, 0.070),
        0.0
    ))

    knife.rotation_euler = (
        math.radians(random.uniform(-0.8, 0.8)),
        math.radians(random.uniform(-0.8, 0.8)),
        math.radians(random.choice([
            random.uniform(-46, -18),
            random.uniform(-9, 9),
            random.uniform(18, 46),
            random.uniform(134, 160),
            random.uniform(200, 226),
            random.uniform(314, 340)
        ]))
    )

    scale_factor = random.uniform(0.96, 1.10)
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

def bbox_is_valid(bbox):
    if bbox is None:
        return False

    margin = 0.045
    longest = max(bbox["width"], bbox["height"])

    if bbox["min_x"] < margin or bbox["max_x"] > 1.0 - margin:
        return False

    if bbox["min_y"] < margin or bbox["max_y"] > 1.0 - margin:
        return False

    if longest < 0.28 or longest > 0.64:
        return False

    if min(bbox["width"], bbox["height"]) < 0.020:
        return False

    return True

def image_path(index):
    return IMAGES_DIR / "faca_kitchenknife_{:04d}.png".format(index)

def label_path(index):
    return LABELS_DIR / "faca_kitchenknife_{:04d}.txt".format(index)

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

    for attempt in range(1, MAX_ATTEMPTS + 1):
        random.seed(BASE_SEED + index * 1000 + attempt)

        randomize_scene(refs)
        refresh_materials(model["object"])
        place_knife(model)
        bpy.context.view_layer.update()

        bbox = calculate_yolo_bbox(
            bpy.context.scene,
            refs["camera"],
            model["object"]
        )

        if not bbox_is_valid(bbox):
            continue

        render_image(image_path(index))
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
    save_current_script()
    clear_scene()
    configure_render()
    refs = create_scene()
    model = import_and_join_model()
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