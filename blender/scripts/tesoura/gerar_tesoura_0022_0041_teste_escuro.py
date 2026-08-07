import bpy
import os
import math
import random
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

PROJECT_ROOT = r"C:\Users\pithe\Documents\Projetos\Github\fastcamp-projeto-final-visao-computacional"
MODEL_PATH = r"C:\Users\pithe\Documents\Projetos\Github\fastcamp-projeto-final-visao-computacional\blender\assets\fbx\tesoura\Scissor_2.obj"

CLASS_NAME = "tesoura"
FILE_PREFIX = "tesoura"
YOLO_CLASS_ID = 0

OUTPUT_IMAGES = os.path.join(PROJECT_ROOT, "dataset_lotes", CLASS_NAME, "images")
OUTPUT_LABELS = os.path.join(PROJECT_ROOT, "dataset_lotes", CLASS_NAME, "labels")
BLEND_OUTPUT = os.path.join(PROJECT_ROOT, "blender", "tesoura", "tesoura_scissor_2_teste_escuro.blend")

START_INDEX = 22
END_INDEX = 41

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 640

SEED = 82
MAX_RANDOM_ATTEMPTS = 80

MIN_LONG_SIDE = 0.48
MIN_SHORT_SIDE = 0.12
MIN_BBOX_AREA = 0.070
MAX_LONG_SIDE = 0.88
FRAME_MARGIN = 0.045


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    for block in list(bpy.data.meshes):
        if block.users == 0:
            bpy.data.meshes.remove(block)

    for block in list(bpy.data.materials):
        if block.users == 0:
            bpy.data.materials.remove(block)

    for block in list(bpy.data.images):
        if block.users == 0:
            bpy.data.images.remove(block)

    for block in list(bpy.data.lights):
        if block.users == 0:
            bpy.data.lights.remove(block)

    for block in list(bpy.data.cameras):
        if block.users == 0:
            bpy.data.cameras.remove(block)


def set_render_settings():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = IMAGE_WIDTH
    scene.render.resolution_y = IMAGE_HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False

    scene.eevee.taa_render_samples = 48
    scene.eevee.taa_samples = 24
    scene.eevee.use_gtao = True
    scene.eevee.gtao_factor = 0.85
    scene.eevee.gtao_distance = 2.0
    scene.eevee.use_bloom = False
    scene.eevee.use_ssr = False
    scene.eevee.shadow_cube_size = '1024'
    scene.eevee.shadow_cascade_size = '1024'

    scene.view_settings.view_transform = 'Filmic'
    try:
        scene.view_settings.look = 'Medium Contrast'
    except Exception:
        pass
    scene.view_settings.exposure = -1.65
    scene.view_settings.gamma = 1.0

    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        scene.world = world

    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background:
        background.inputs[0].default_value = (0.40, 0.41, 0.43, 1.0)
        background.inputs[1].default_value = 0.10


def point_camera_to(camera, target):
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


def create_material(name, color, metallic, roughness, specular):
    material = bpy.data.materials.get(name)

    if material is None:
        material = bpy.data.materials.new(name=name)

    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")

    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Specular"].default_value = specular

    return material


def create_base():
    bpy.ops.mesh.primitive_plane_add(size=3.2, location=(0.0, 0.0, 0.0))
    base = bpy.context.active_object
    base.name = "Base"

    material = create_material(
        "Base_GrayWhite",
        (0.42, 0.43, 0.45, 1.0),
        0.0,
        0.82,
        0.22
    )

    base.data.materials.clear()
    base.data.materials.append(material)

    return base


def create_camera():
    bpy.ops.object.camera_add(location=(0.0, -1.48, 0.92))
    camera = bpy.context.active_object
    camera.name = "Camera"
    camera.data.lens = 58
    camera.data.sensor_width = 36
    point_camera_to(camera, Vector((0.0, 0.0, 0.035)))
    bpy.context.scene.camera = camera

    return camera


def create_lights():
    lights = {}

    bpy.ops.object.light_add(type='AREA', location=(0.62, -0.72, 1.18))
    key = bpy.context.active_object
    key.name = "KeyLight"
    key.data.energy = 430
    key.data.shape = 'RECTANGLE'
    key.data.size = 1.35
    key.data.size_y = 1.10
    point_camera_to(key, Vector((0.0, 0.0, 0.0)))
    lights["key"] = key

    bpy.ops.object.light_add(type='AREA', location=(-0.72, -0.40, 0.82))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 125
    fill.data.shape = 'RECTANGLE'
    fill.data.size = 1.60
    fill.data.size_y = 1.30
    point_camera_to(fill, Vector((0.0, 0.0, 0.0)))
    lights["fill"] = fill

    bpy.ops.object.light_add(type='AREA', location=(0.05, 0.34, 1.28))
    top = bpy.context.active_object
    top.name = "TopLight"
    top.data.energy = 85
    top.data.shape = 'SQUARE'
    top.data.size = 1.55
    point_camera_to(top, Vector((0.0, 0.0, 0.0)))
    lights["top"] = top

    return lights


def import_model(filepath):
    extension = os.path.splitext(filepath)[1].lower()
    before = set(bpy.data.objects)

    if extension == ".fbx":
        bpy.ops.import_scene.fbx(filepath=filepath)
    elif extension == ".obj":
        bpy.ops.import_scene.obj(filepath=filepath)
    elif extension in [".glb", ".gltf"]:
        bpy.ops.import_scene.gltf(filepath=filepath)
    else:
        raise ValueError("Formato não suportado: {}".format(extension))

    after = set(bpy.data.objects)
    imported = list(after - before)
    meshes = [obj for obj in imported if obj.type == 'MESH']

    if not meshes:
        meshes = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']

    if not meshes:
        raise RuntimeError("Nenhum objeto MESH foi importado.")

    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.0, 0.0, 0.0))
    root = bpy.context.active_object
    root.name = "TesouraRoot"

    for obj in meshes:
        obj.parent = root

    return root, meshes


def get_world_bbox(meshes):
    points = []

    for obj in meshes:
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))

    minimum = Vector((
        min(point.x for point in points),
        min(point.y for point in points),
        min(point.z for point in points)
    ))

    maximum = Vector((
        max(point.x for point in points),
        max(point.y for point in points),
        max(point.z for point in points)
    ))

    return minimum, maximum


def center_scale_and_flatten(root, meshes, target_size):
    bpy.context.view_layer.update()

    minimum, maximum = get_world_bbox(meshes)
    dimensions = maximum - minimum
    largest = max(dimensions.x, dimensions.y, dimensions.z)

    if largest <= 0:
        raise RuntimeError("O modelo importado possui dimensões inválidas.")

    factor = target_size / largest
    root.scale = (factor, factor, factor)
    bpy.context.view_layer.update()

    minimum, maximum = get_world_bbox(meshes)
    dimensions = maximum - minimum

    if dimensions.x <= dimensions.y and dimensions.x <= dimensions.z:
        root.rotation_euler.y += math.radians(90)
    elif dimensions.y <= dimensions.x and dimensions.y <= dimensions.z:
        root.rotation_euler.x += math.radians(90)

    bpy.context.view_layer.update()

    minimum, maximum = get_world_bbox(meshes)
    center = (minimum + maximum) * 0.5

    root.location.x -= center.x
    root.location.y -= center.y
    bpy.context.view_layer.update()

    minimum, maximum = get_world_bbox(meshes)
    root.location.z += 0.006 - minimum.z
    bpy.context.view_layer.update()


def polygon_world_center(obj, polygon):
    center = Vector((0.0, 0.0, 0.0))

    for vertex_index in polygon.vertices:
        center += obj.data.vertices[vertex_index].co

    center /= max(1, len(polygon.vertices))

    return obj.matrix_world @ center


def apply_scissor_materials(meshes):
    metal = create_material(
        "Tesoura_Metal",
        (0.28, 0.30, 0.33, 1.0),
        0.88,
        0.36,
        0.38
    )

    dark = create_material(
        "Tesoura_Cabo_Escuro",
        (0.025, 0.028, 0.034, 1.0),
        0.0,
        0.66,
        0.24
    )

    red = create_material(
        "Tesoura_Cabo_Vermelho",
        (0.30, 0.012, 0.018, 1.0),
        0.0,
        0.58,
        0.28
    )

    centers = []

    for obj in meshes:
        for polygon in obj.data.polygons:
            centers.append(polygon_world_center(obj, polygon))

    if not centers:
        return

    ranges = {
        "x": max(point.x for point in centers) - min(point.x for point in centers),
        "y": max(point.y for point in centers) - min(point.y for point in centers)
    }

    main_axis = "x" if ranges["x"] >= ranges["y"] else "y"
    cross_axis = "y" if main_axis == "x" else "x"

    main_values = [getattr(point, main_axis) for point in centers]
    cross_values = [getattr(point, cross_axis) for point in centers]

    main_min = min(main_values)
    main_max = max(main_values)
    main_range = max(main_max - main_min, 0.000001)

    cross_min = min(cross_values)
    cross_max = max(cross_values)
    cross_mid = (cross_min + cross_max) * 0.5
    cross_range = max(cross_max - cross_min, 0.000001)

    low_count = sum(
        1 for value in main_values
        if (value - main_min) / main_range <= 0.32
    )

    high_count = sum(
        1 for value in main_values
        if (value - main_min) / main_range >= 0.68
    )

    handle_is_low = low_count >= high_count

    for obj in meshes:
        obj.data.materials.clear()
        obj.data.materials.append(metal)
        obj.data.materials.append(dark)
        obj.data.materials.append(red)

        for polygon in obj.data.polygons:
            center = polygon_world_center(obj, polygon)
            main_value = getattr(center, main_axis)
            cross_value = getattr(center, cross_axis)
            normalized = (main_value - main_min) / main_range

            if handle_is_low:
                is_handle = normalized <= 0.42
            else:
                is_handle = normalized >= 0.58

            if not is_handle:
                polygon.material_index = 0
            else:
                cross_distance = abs(cross_value - cross_mid) / cross_range

                if cross_distance >= 0.20:
                    polygon.material_index = 2
                else:
                    polygon.material_index = 1


def randomize_base(base):
    material = base.data.materials[0]
    bsdf = material.node_tree.nodes.get("Principled BSDF")

    if bsdf:
        value = random.uniform(0.38, 0.48)
        bsdf.inputs["Base Color"].default_value = (
            value,
            min(value + 0.01, 0.50),
            min(value + 0.025, 0.52),
            1.0
        )
        bsdf.inputs["Roughness"].default_value = random.uniform(0.78, 0.88)


def randomize_world():
    world = bpy.context.scene.world
    background = world.node_tree.nodes.get("Background")

    if background:
        value = random.uniform(0.34, 0.44)
        background.inputs[0].default_value = (
            value,
            min(value + 0.01, 0.50),
            min(value + 0.025, 0.52),
            1.0
        )
        background.inputs[1].default_value = random.uniform(0.06, 0.12)


def randomize_lights(lights):
    lights["key"].location = (
        random.uniform(0.48, 0.76),
        random.uniform(-0.84, -0.60),
        random.uniform(1.05, 1.27)
    )
    lights["key"].data.energy = random.uniform(330, 500)
    point_camera_to(lights["key"], Vector((0.0, 0.0, 0.0)))

    lights["fill"].location = (
        random.uniform(-0.84, -0.56),
        random.uniform(-0.55, -0.28),
        random.uniform(0.72, 0.94)
    )
    lights["fill"].data.energy = random.uniform(80, 145)
    point_camera_to(lights["fill"], Vector((0.0, 0.0, 0.0)))

    lights["top"].location = (
        random.uniform(-0.18, 0.18),
        random.uniform(0.18, 0.48),
        random.uniform(1.14, 1.38)
    )
    lights["top"].data.energy = random.uniform(45, 90)
    point_camera_to(lights["top"], Vector((0.0, 0.0, 0.0)))


def randomize_camera(camera):
    camera.location = Vector((
        random.uniform(-0.08, 0.08),
        random.uniform(-1.55, -1.38),
        random.uniform(0.86, 0.98)
    ))

    camera.data.lens = random.uniform(54, 63)

    target = Vector((
        random.uniform(-0.025, 0.025),
        random.uniform(-0.025, 0.025),
        random.uniform(0.02, 0.045)
    ))

    point_camera_to(camera, target)


def randomize_pose(root, meshes, base_rotation):
    root.rotation_euler = (
        base_rotation.x + math.radians(random.uniform(-4.5, 4.5)),
        base_rotation.y + math.radians(random.uniform(-4.5, 4.5)),
        base_rotation.z + math.radians(random.uniform(-38, 38))
    )

    root.location = Vector((
        random.uniform(-0.085, 0.085),
        random.uniform(-0.065, 0.065),
        0.0
    ))

    bpy.context.view_layer.update()

    minimum, maximum = get_world_bbox(meshes)
    root.location.z += 0.006 - minimum.z
    bpy.context.view_layer.update()


def get_camera_bbox(meshes, camera):
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()

    xs = []
    ys = []

    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()

        try:
            matrix = evaluated.matrix_world

            for vertex in mesh.vertices:
                world_coordinate = matrix @ vertex.co
                camera_coordinate = world_to_camera_view(
                    scene,
                    camera,
                    world_coordinate
                )

                if camera_coordinate.z > 0:
                    xs.append(camera_coordinate.x)
                    ys.append(camera_coordinate.y)
        finally:
            evaluated.to_mesh_clear()

    if not xs or not ys:
        return None

    raw_min_x = min(xs)
    raw_max_x = max(xs)
    raw_min_y = min(ys)
    raw_max_y = max(ys)

    if raw_max_x <= 0 or raw_min_x >= 1:
        return None

    if raw_max_y <= 0 or raw_min_y >= 1:
        return None

    min_x = max(0.0, raw_min_x)
    max_x = min(1.0, raw_max_x)
    min_y = max(0.0, raw_min_y)
    max_y = min(1.0, raw_max_y)

    width = max_x - min_x
    height = max_y - min_y
    center_x = min_x + width * 0.5
    center_y = min_y + height * 0.5

    return (
        center_x,
        center_y,
        width,
        height,
        raw_min_x,
        raw_max_x,
        raw_min_y,
        raw_max_y
    )


def bbox_is_valid(bbox):
    if bbox is None:
        return False

    center_x, center_y, width, height, min_x, max_x, min_y, max_y = bbox

    long_side = max(width, height)
    short_side = min(width, height)
    area = width * height

    if long_side < MIN_LONG_SIDE:
        return False

    if short_side < MIN_SHORT_SIDE:
        return False

    if long_side > MAX_LONG_SIDE:
        return False

    if area < MIN_BBOX_AREA:
        return False

    if min_x < FRAME_MARGIN or max_x > 1.0 - FRAME_MARGIN:
        return False

    if min_y < FRAME_MARGIN or max_y > 1.0 - FRAME_MARGIN:
        return False

    return True


def save_label(path, bbox):
    center_x, center_y, width, height, _, _, _, _ = bbox
    center_y = 1.0 - center_y

    with open(path, "w", encoding="utf-8") as label:
        label.write(
            "{} {:.6f} {:.6f} {:.6f} {:.6f}\n".format(
                YOLO_CLASS_ID,
                center_x,
                center_y,
                width,
                height
            )
        )


def main():
    random.seed(SEED)

    if not os.path.isfile(MODEL_PATH):
        raise FileNotFoundError(
            "Modelo não encontrado: {}".format(MODEL_PATH)
        )

    ensure_dir(OUTPUT_IMAGES)
    ensure_dir(OUTPUT_LABELS)
    ensure_dir(os.path.dirname(BLEND_OUTPUT))

    clean_scene()
    set_render_settings()

    base = create_base()
    camera = create_camera()
    lights = create_lights()

    root, meshes = import_model(MODEL_PATH)
    center_scale_and_flatten(root, meshes, 0.66)
    apply_scissor_materials(meshes)

    base_rotation = root.rotation_euler.copy()

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUTPUT)

    scene = bpy.context.scene

    generated = 0
    skipped = 0
    failed = 0

    print("=" * 72)
    print("TESTE DO MODELO SCISSOR_2")
    print("Modelo:", MODEL_PATH)
    print("Intervalo:", START_INDEX, "a", END_INDEX)
    print("Classe YOLO:", YOLO_CLASS_ID)
    print("=" * 72)

    for index in range(START_INDEX, END_INDEX + 1):
        filename = "{}_{:04d}".format(FILE_PREFIX, index)
        image_path = os.path.join(OUTPUT_IMAGES, filename + ".png")
        label_path = os.path.join(OUTPUT_LABELS, filename + ".txt")

        if os.path.exists(image_path) and os.path.exists(label_path):
            print("[PULADO]", filename)
            skipped += 1
            continue

        valid_bbox = None

        for attempt in range(MAX_RANDOM_ATTEMPTS):
            randomize_base(base)
            randomize_world()
            randomize_lights(lights)
            randomize_camera(camera)
            randomize_pose(root, meshes, base_rotation)

            bpy.context.view_layer.update()

            bbox = get_camera_bbox(meshes, camera)

            if bbox_is_valid(bbox):
                valid_bbox = bbox
                break

        if valid_bbox is None:
            print("[FALHA]", filename)
            failed += 1
            continue

        scene.render.filepath = image_path
        bpy.ops.render.render(write_still=True)
        save_label(label_path, valid_bbox)

        generated += 1
        print("[OK]", filename)

    print("=" * 72)
    print("Geradas:", generated)
    print("Puladas:", skipped)
    print("Falhas:", failed)
    print("=" * 72)


if __name__ == "__main__":
    main()