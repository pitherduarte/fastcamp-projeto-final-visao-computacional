import bpy
import os
import math
import random
import time
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

PROJECT_ROOT = r"C:\Users\pithe\Documents\Projetos\Github\fastcamp-projeto-final-visao-computacional"
IMAGE_DIR = os.path.join(PROJECT_ROOT, "dataset_lotes", "tomada", "images")
LABEL_DIR = os.path.join(PROJECT_ROOT, "dataset_lotes", "tomada", "labels")
SCENE_DIR = os.path.join(PROJECT_ROOT, "blender", "cenas")
BLEND_PATH = os.path.join(SCENE_DIR, "tomada_americana_distancia_media_0718_1100.blend")

PREFIX = "tomada_americana_distante"
START_INDEX = 718
END_INDEX = 1100
COUNT = END_INDEX - START_INDEX + 1
CLASS_ID = 3
SEED_BASE = 52000

for directory in [IMAGE_DIR, LABEL_DIR, SCENE_DIR]:
    os.makedirs(directory, exist_ok=True)

def extract_index(filename):
    stem = os.path.splitext(filename)[0]
    expected_prefix = PREFIX + "_"

    if not stem.startswith(expected_prefix):
        return None

    suffix = stem[len(expected_prefix):]

    if not suffix.isdigit():
        return None

    return int(suffix)

def remove_previous_batch():
    removed_images = 0
    removed_labels = 0

    for filename in os.listdir(IMAGE_DIR):
        index = extract_index(filename)

        if (
            index is not None
            and START_INDEX <= index <= END_INDEX
            and filename.lower().endswith(".png")
        ):
            path = os.path.join(IMAGE_DIR, filename)

            if os.path.isfile(path):
                os.remove(path)
                removed_images += 1

    for filename in os.listdir(LABEL_DIR):
        index = extract_index(filename)

        if (
            index is not None
            and START_INDEX <= index <= END_INDEX
            and filename.lower().endswith(".txt")
        ):
            path = os.path.join(LABEL_DIR, filename)

            if os.path.isfile(path):
                os.remove(path)
                removed_labels += 1

    print("Imagens removidas do intervalo 0718-1100:", removed_images)
    print("Labels removidos do intervalo 0718-1100:", removed_labels)

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    collections = [
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.lights,
        bpy.data.cameras
    ]

    for collection in collections:
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)

def configure_render():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.compression = 10
    scene.render.film_transparent = False

    scene.eevee.taa_render_samples = 32
    scene.eevee.taa_samples = 32
    scene.eevee.use_gtao = True
    scene.eevee.gtao_distance = 2.0
    scene.eevee.gtao_factor = 1.30
    scene.eevee.use_bloom = False
    scene.eevee.use_ssr = True
    scene.eevee.shadow_cube_size = "1024"
    scene.eevee.shadow_cascade_size = "1024"

    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = -0.08
    scene.view_settings.gamma = 1.0

    scene.world.use_nodes = True

    background = scene.world.node_tree.nodes.get("Background")
    background.inputs[0].default_value = (0.065, 0.062, 0.058, 1.0)
    background.inputs[1].default_value = 0.08

def create_material(
    name,
    color,
    roughness=0.5,
    metallic=0.0,
    specular=0.5
):
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True

    shader = material.node_tree.nodes.get("Principled BSDF")

    shader.inputs["Base Color"].default_value = (
        color[0],
        color[1],
        color[2],
        1.0
    )

    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Specular"].default_value = specular

    return material

def create_wall_material():
    material = bpy.data.materials.new(name="MaterialParede")
    material.use_nodes = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links

    shader = nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (
        0.42,
        0.41,
        0.40,
        1.0
    )
    shader.inputs["Roughness"].default_value = 0.95
    shader.inputs["Specular"].default_value = 0.10

    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 55.0
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Roughness"].default_value = 0.55

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.04
    bump.inputs["Distance"].default_value = 0.02

    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])

    return material

def assign_material(obj, material):
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)

def create_cube(name, location, scale, material=None):
    bpy.ops.mesh.primitive_cube_add(location=location)

    obj = bpy.context.object
    obj.name = name
    obj.scale = scale

    if material is not None:
        assign_material(obj, material)

    return obj

def create_uv_sphere(name, location, scale, material=None):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=16,
        location=location
    )

    obj = bpy.context.object
    obj.name = name
    obj.scale = scale

    if material is not None:
        assign_material(obj, material)

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()
    obj.select_set(False)

    return obj

def create_cylinder(
    name,
    location,
    radius,
    depth,
    rotation,
    material=None,
    vertices=32
):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation
    )

    obj = bpy.context.object
    obj.name = name

    if material is not None:
        assign_material(obj, material)

    return obj

def add_bevel(obj, width, segments):
    modifier = obj.modifiers.new(
        name="Bevel",
        type="BEVEL"
    )

    modifier.width = width
    modifier.segments = segments
    modifier.profile = 0.65

def parent_object(obj, parent):
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()

def point_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def create_wall():
    material = create_wall_material()

    wall = create_cube(
        "Parede",
        (0.0, 0.0, 1.30),
        (2.5, 0.025, 1.8),
        material
    )

    return {
        "object": wall,
        "material": material
    }

def create_outlet():
    plate_material = create_material(
        "MaterialPlaca",
        (0.80, 0.79, 0.77),
        0.60,
        0.0,
        0.28
    )

    outer_material = create_material(
        "MaterialModuloExterno",
        (0.57, 0.56, 0.54),
        0.72,
        0.0,
        0.16
    )

    inner_material = create_material(
        "MaterialModuloInterno",
        (0.70, 0.69, 0.67),
        0.68,
        0.0,
        0.20
    )

    hole_material = create_material(
        "MaterialFuros",
        (0.020, 0.019, 0.018),
        0.88,
        0.0,
        0.04
    )

    screw_material = create_material(
        "MaterialParafuso",
        (0.40, 0.40, 0.39),
        0.40,
        0.32,
        0.38
    )

    root = bpy.data.objects.new("TomadaRoot", None)
    bpy.context.scene.collection.objects.link(root)

    plate = create_cube(
        "PlacaTomada",
        (0.0, 0.005, 0.0),
        (0.048, 0.0045, 0.071),
        plate_material
    )

    add_bevel(plate, 0.0034, 5)
    parent_object(plate, root)

    socket_positions = [
        0.027,
        -0.027
    ]

    for socket_index, center_z in enumerate(socket_positions):
        outer_socket = create_uv_sphere(
            "ModuloExterno_" + str(socket_index),
            (0.0, 0.0110, center_z),
            (0.0225, 0.0040, 0.0195),
            outer_material
        )

        inner_socket = create_uv_sphere(
            "ModuloInterno_" + str(socket_index),
            (0.0, 0.0142, center_z),
            (0.0195, 0.0026, 0.0165),
            inner_material
        )

        left_slot = create_cube(
            "RanhuraEsquerda_" + str(socket_index),
            (-0.0068, 0.0170, center_z + 0.0025),
            (0.00155, 0.0011, 0.0072),
            hole_material
        )

        right_slot = create_cube(
            "RanhuraDireita_" + str(socket_index),
            (0.0068, 0.0170, center_z + 0.0025),
            (0.00145, 0.0011, 0.0063),
            hole_material
        )

        ground_hole = create_cylinder(
            "Terra_" + str(socket_index),
            (0.0, 0.0172, center_z - 0.0090),
            0.00365,
            0.0023,
            (math.radians(90.0), 0.0, 0.0),
            hole_material,
            32
        )

        parent_object(outer_socket, root)
        parent_object(inner_socket, root)
        parent_object(left_slot, root)
        parent_object(right_slot, root)
        parent_object(ground_hole, root)

    screw = create_cylinder(
        "ParafusoCentral",
        (0.0, 0.0168, 0.0),
        0.00255,
        0.0021,
        (math.radians(90.0), 0.0, 0.0),
        screw_material,
        32
    )

    screw_slot = create_cube(
        "RanhuraParafuso",
        (0.0, 0.0180, 0.0),
        (0.0022, 0.0007, 0.00042),
        hole_material
    )

    parent_object(screw, root)
    parent_object(screw_slot, root)

    return {
        "root": root,
        "plate": plate,
        "plate_material": plate_material,
        "outer_material": outer_material,
        "inner_material": inner_material
    }

def create_camera():
    camera_data = bpy.data.cameras.new("Camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 1.0
    camera_data.clip_start = 0.01
    camera_data.clip_end = 100.0

    camera = bpy.data.objects.new(
        "Camera",
        camera_data
    )

    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera

    return camera

def create_lights():
    key_data = bpy.data.lights.new(
        "LuzDireita",
        type="AREA"
    )

    key = bpy.data.objects.new(
        "LuzDireita",
        key_data
    )

    bpy.context.scene.collection.objects.link(key)

    fill_data = bpy.data.lights.new(
        "LuzPreenchimento",
        type="AREA"
    )

    fill = bpy.data.objects.new(
        "LuzPreenchimento",
        fill_data
    )

    bpy.context.scene.collection.objects.link(fill)

    if hasattr(key.data, "use_contact_shadow"):
        key.data.use_contact_shadow = True
        key.data.contact_shadow_bias = 0.01
        key.data.contact_shadow_distance = 1.0
        key.data.contact_shadow_thickness = 0.04

    if hasattr(fill.data, "use_contact_shadow"):
        fill.data.use_contact_shadow = True
        fill.data.contact_shadow_bias = 0.01
        fill.data.contact_shadow_distance = 1.0
        fill.data.contact_shadow_thickness = 0.04

    return {
        "key": key,
        "fill": fill
    }

def randomize_materials(wall, outlet):
    gray = random.uniform(0.37, 0.50)
    warm = random.uniform(0.006, 0.020)

    wall["material"].node_tree.nodes[
        "Principled BSDF"
    ].inputs["Base Color"].default_value = (
        gray + warm,
        gray,
        gray - warm * 0.55,
        1.0
    )

    plate_value = random.uniform(0.73, 0.84)

    outlet["plate_material"].node_tree.nodes[
        "Principled BSDF"
    ].inputs["Base Color"].default_value = (
        plate_value + 0.010,
        plate_value,
        plate_value - 0.018,
        1.0
    )

    outer_value = plate_value - random.uniform(
        0.16,
        0.22
    )

    outlet["outer_material"].node_tree.nodes[
        "Principled BSDF"
    ].inputs["Base Color"].default_value = (
        outer_value + 0.006,
        outer_value,
        outer_value - 0.010,
        1.0
    )

    inner_value = plate_value - random.uniform(
        0.045,
        0.080
    )

    outlet["inner_material"].node_tree.nodes[
        "Principled BSDF"
    ].inputs["Base Color"].default_value = (
        inner_value + 0.006,
        inner_value,
        inner_value - 0.012,
        1.0
    )

def configure_camera(camera):
    camera_x = random.uniform(-0.025, 0.025)
    camera_z = random.uniform(1.00, 1.15)

    camera.location = (
        camera_x,
        random.uniform(2.40, 3.00),
        camera_z
    )

    camera.data.ortho_scale = random.uniform(
        0.90,
        1.18
    )

    point_at(
        camera,
        Vector((
            camera_x,
            0.0,
            camera_z
        ))
    )

def randomize_outlet(outlet):
    outlet["root"].location = (
        0.0,
        0.029,
        1.0
    )

    outlet["root"].rotation_euler = (
        math.radians(random.uniform(-0.7, 0.7)),
        math.radians(random.uniform(-3.5, 3.5)),
        math.radians(random.uniform(-3.0, 3.0))
    )

def randomize_lights(lights, outlet):
    target = Vector((
        outlet["root"].location.x,
        outlet["root"].location.y,
        outlet["root"].location.z
    ))

    key = lights["key"]

    key.location = (
        random.uniform(0.55, 1.15),
        random.uniform(0.60, 1.10),
        random.uniform(1.20, 1.85)
    )

    key.data.energy = random.uniform(
        32.0,
        55.0
    )

    key.data.shape = "RECTANGLE"
    key.data.size = random.uniform(0.65, 1.10)
    key.data.size_y = random.uniform(0.75, 1.20)

    key.data.color = (
        1.0,
        random.uniform(0.92, 0.98),
        random.uniform(0.86, 0.95)
    )

    point_at(key, target)

    fill = lights["fill"]

    fill.location = (
        random.uniform(-0.90, -0.45),
        random.uniform(0.70, 1.20),
        random.uniform(0.90, 1.50)
    )

    fill.data.energy = random.uniform(
        6.0,
        13.0
    )

    fill.data.shape = "RECTANGLE"
    fill.data.size = random.uniform(0.90, 1.40)
    fill.data.size_y = random.uniform(0.90, 1.40)

    fill.data.color = (
        random.uniform(0.92, 0.98),
        random.uniform(0.94, 1.0),
        1.0
    )

    point_at(fill, target)

    bpy.context.scene.view_settings.exposure = random.uniform(
        -0.15,
        0.04
    )

def compute_yolo_bbox(obj, camera):
    scene = bpy.context.scene
    projected = []

    for corner in obj.bound_box:
        world_corner = obj.matrix_world @ Vector(corner)

        projected.append(
            world_to_camera_view(
                scene,
                camera,
                world_corner
            )
        )

    if not projected:
        return None

    if max(point.z for point in projected) <= 0.0:
        return None

    min_x = max(
        0.0,
        min(point.x for point in projected)
    )

    max_x = min(
        1.0,
        max(point.x for point in projected)
    )

    min_y = max(
        0.0,
        min(point.y for point in projected)
    )

    max_y = min(
        1.0,
        max(point.y for point in projected)
    )

    if max_x <= min_x or max_y <= min_y:
        return None

    width = max_x - min_x
    height = max_y - min_y

    center_x = (
        min_x + max_x
    ) / 2.0

    center_y = 1.0 - (
        (min_y + max_y) / 2.0
    )

    return (
        center_x,
        center_y,
        width,
        height
    )

def move_outlet_to_screen(
    outlet,
    camera,
    desired_x,
    desired_y
):
    root = outlet["root"]

    for iteration in range(6):
        bpy.context.view_layer.update()

        bbox = compute_yolo_bbox(
            outlet["plate"],
            camera
        )

        if bbox is None:
            return None

        error_x = desired_x - bbox[0]
        error_y = desired_y - bbox[1]

        if (
            abs(error_x) < 0.0005
            and abs(error_y) < 0.0005
        ):
            return bbox

        original_x = root.location.x
        original_z = root.location.z
        step = 0.01

        root.location.x = original_x + step
        bpy.context.view_layer.update()

        bbox_x = compute_yolo_bbox(
            outlet["plate"],
            camera
        )

        root.location.x = original_x
        root.location.z = original_z + step
        bpy.context.view_layer.update()

        bbox_z = compute_yolo_bbox(
            outlet["plate"],
            camera
        )

        root.location.x = original_x
        root.location.z = original_z
        bpy.context.view_layer.update()

        if bbox_x is None or bbox_z is None:
            return None

        j11 = (
            bbox_x[0] - bbox[0]
        ) / step

        j21 = (
            bbox_x[1] - bbox[1]
        ) / step

        j12 = (
            bbox_z[0] - bbox[0]
        ) / step

        j22 = (
            bbox_z[1] - bbox[1]
        ) / step

        determinant = (
            j11 * j22
            - j12 * j21
        )

        if abs(determinant) < 0.000001:
            return None

        delta_x = (
            error_x * j22
            - error_y * j12
        ) / determinant

        delta_z = (
            j11 * error_y
            - j21 * error_x
        ) / determinant

        root.location.x += delta_x
        root.location.z += delta_z

    bpy.context.view_layer.update()

    return compute_yolo_bbox(
        outlet["plate"],
        camera
    )

def bbox_is_valid(bbox):
    if bbox is None:
        return False

    center_x, center_y, width, height = bbox

    if center_x < 0.075 or center_x > 0.34:
        return False

    if center_y < 0.54 or center_y > 0.84:
        return False

    if width < 0.065 or width > 0.13:
        return False

    if height < 0.105 or height > 0.19:
        return False

    if center_x - width / 2.0 <= 0.01:
        return False

    if center_x + width / 2.0 >= 0.99:
        return False

    if center_y - height / 2.0 <= 0.01:
        return False

    if center_y + height / 2.0 >= 0.99:
        return False

    return True

def apply_fallback(outlet, camera, lights):
    camera.location = (
        0.0,
        2.70,
        1.08
    )

    camera.data.ortho_scale = 1.02

    point_at(
        camera,
        Vector((
            0.0,
            0.0,
            1.08
        ))
    )

    outlet["root"].location = (
        0.0,
        0.029,
        1.0
    )

    outlet["root"].rotation_euler = (
        0.0,
        0.0,
        0.0
    )

    bbox = move_outlet_to_screen(
        outlet,
        camera,
        0.19,
        0.70
    )

    randomize_lights(
        lights,
        outlet
    )

    return bbox

def write_label(path, bbox):
    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(
            "{} {:.6f} {:.6f} {:.6f} {:.6f}\n".format(
                CLASS_ID,
                bbox[0],
                bbox[1],
                bbox[2],
                bbox[3]
            )
        )

def format_time(seconds):
    seconds = int(max(0, seconds))

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60

    return "{:02d}:{:02d}:{:02d}".format(
        hours,
        minutes,
        remaining_seconds
    )

def count_dataset_files():
    image_count = len([
        filename
        for filename in os.listdir(IMAGE_DIR)
        if filename.lower().endswith(".png")
    ])

    label_count = len([
        filename
        for filename in os.listdir(LABEL_DIR)
        if filename.lower().endswith(".txt")
    ])

    return image_count, label_count

def generate_dataset():
    remove_previous_batch()
    clear_scene()
    configure_render()

    wall = create_wall()
    outlet = create_outlet()
    camera = create_camera()
    lights = create_lights()

    bpy.context.view_layer.update()

    bpy.ops.wm.save_as_mainfile(
        filepath=BLEND_PATH
    )

    print("=" * 78)
    print("TOMADA AMERICANA | CONTINUAÇÃO")
    print("=" * 78)
    print("Somente parede e tomada")
    print("Quantidade:", COUNT)
    print("Índices:", START_INDEX, "até", END_INDEX)
    print("Classe YOLO:", CLASS_ID)
    print("Imagens:", IMAGE_DIR)
    print("Labels:", LABEL_DIR)
    print("=" * 78)

    start_time = time.time()
    generated = 0
    fallback_count = 0

    for file_index in range(
        START_INDEX,
        END_INDEX + 1
    ):
        random.seed(
            SEED_BASE + file_index * 163
        )

        randomize_materials(
            wall,
            outlet
        )

        configure_camera(camera)
        randomize_outlet(outlet)

        desired_x = random.uniform(
            0.13,
            0.29
        )

        desired_y = random.uniform(
            0.61,
            0.78
        )

        bbox = move_outlet_to_screen(
            outlet,
            camera,
            desired_x,
            desired_y
        )

        randomize_lights(
            lights,
            outlet
        )

        bpy.context.view_layer.update()

        bbox = compute_yolo_bbox(
            outlet["plate"],
            camera
        )

        if not bbox_is_valid(bbox):
            fallback_count += 1

            randomize_materials(
                wall,
                outlet
            )

            bbox = apply_fallback(
                outlet,
                camera,
                lights
            )

            bpy.context.view_layer.update()

            bbox = compute_yolo_bbox(
                outlet["plate"],
                camera
            )

        if not bbox_is_valid(bbox):
            raise RuntimeError(
                "Não foi possível gerar uma caixa válida para a imagem {}. Caixa: {}".format(
                    file_index,
                    bbox
                )
            )

        filename = "{}_{:04d}".format(
            PREFIX,
            file_index
        )

        image_path = os.path.join(
            IMAGE_DIR,
            filename + ".png"
        )

        label_path = os.path.join(
            LABEL_DIR,
            filename + ".txt"
        )

        bpy.context.scene.render.filepath = image_path

        bpy.ops.render.render(
            write_still=True
        )

        write_label(
            label_path,
            bbox
        )

        generated += 1

        elapsed = time.time() - start_time
        average_time = elapsed / generated

        remaining_time = average_time * (
            COUNT - generated
        )

        print(
            "[{:03d}/{:03d}] {} | posição {:.3f}, {:.3f} | caixa {:.3f} x {:.3f} | restante {}".format(
                generated,
                COUNT,
                filename,
                bbox[0],
                bbox[1],
                bbox[2],
                bbox[3],
                format_time(remaining_time)
            )
        )

    bpy.ops.wm.save_as_mainfile(
        filepath=BLEND_PATH
    )

    total_time = time.time() - start_time
    total_images, total_labels = count_dataset_files()

    print("=" * 78)
    print("GERAÇÃO CONCLUÍDA")
    print("=" * 78)
    print("Imagens geradas:", generated)
    print("Labels gerados:", generated)
    print("Intervalo:", START_INDEX, "até", END_INDEX)
    print("Fallbacks usados:", fallback_count)
    print("Tempo total:", format_time(total_time))
    print("Total de PNG na pasta:", total_images)
    print("Total de TXT na pasta:", total_labels)
    print("Blend:", BLEND_PATH)
    print("=" * 78)

generate_dataset()