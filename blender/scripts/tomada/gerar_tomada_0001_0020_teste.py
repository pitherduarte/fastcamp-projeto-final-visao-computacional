import bpy
import os
import math
import random
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

PROJECT_ROOT = r"C:\Users\pithe\Documents\Projetos\Github\fastcamp-projeto-final-visao-computacional"
IMAGE_DIR = os.path.join(PROJECT_ROOT, "dataset_lotes", "tomada_teste", "images")
LABEL_DIR = os.path.join(PROJECT_ROOT, "dataset_lotes", "tomada_teste", "labels")
SCENE_DIR = os.path.join(PROJECT_ROOT, "blender", "cenas")
BLEND_PATH = os.path.join(SCENE_DIR, "tomada_americana_teste.blend")

PREFIX = "tomada_americana_teste"
COUNT = 20
CLASS_ID = 3
SEED_BASE = 7300

for directory in [IMAGE_DIR, LABEL_DIR, SCENE_DIR]:
    os.makedirs(directory, exist_ok=True)

def remove_previous_files():
    for directory in [IMAGE_DIR, LABEL_DIR]:
        for filename in os.listdir(directory):
            if filename.startswith(PREFIX + "_"):
                path = os.path.join(directory, filename)
                if os.path.isfile(path):
                    os.remove(path)

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
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
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 10
    scene.render.film_transparent = False

    scene.eevee.taa_render_samples = 32
    scene.eevee.taa_samples = 32
    scene.eevee.use_gtao = True
    scene.eevee.gtao_distance = 2.0
    scene.eevee.gtao_factor = 1.35
    scene.eevee.use_bloom = False
    scene.eevee.use_ssr = True
    scene.eevee.shadow_cube_size = '1024'
    scene.eevee.shadow_cascade_size = '1024'

    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'Medium High Contrast'
    scene.view_settings.exposure = -0.45
    scene.view_settings.gamma = 1.0

    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs[0].default_value = (0.035, 0.035, 0.035, 1.0)
    background.inputs[1].default_value = 0.035

def create_material(name, color, roughness=0.5, metallic=0.0, specular=0.5):
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
    shader.inputs["Base Color"].default_value = (0.21, 0.20, 0.19, 1.0)
    shader.inputs["Roughness"].default_value = 0.94
    shader.inputs["Specular"].default_value = 0.12

    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 52.0
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Roughness"].default_value = 0.55

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.10
    bump.inputs["Distance"].default_value = 0.035

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

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()
    obj.select_set(False)

    return obj

def create_cylinder(name, location, radius, depth, rotation, material=None, vertices=32):
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
    modifier = obj.modifiers.new(name="Bevel", type='BEVEL')
    modifier.width = width
    modifier.segments = segments
    modifier.profile = 0.65

def parent_object(obj, parent):
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()

def point_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

def create_wall():
    material = create_wall_material()

    wall = create_cube(
        "Parede",
        (0.0, 0.0, 1.1),
        (2.6, 0.025, 2.1),
        material
    )

    return {
        "object": wall,
        "material": material
    }

def create_outlet():
    plate_material = create_material(
        "MaterialPlaca",
        (0.72, 0.71, 0.69),
        0.58,
        0.0,
        0.30
    )

    socket_outer_material = create_material(
        "MaterialModuloExterno",
        (0.50, 0.49, 0.47),
        0.70,
        0.0,
        0.18
    )

    socket_inner_material = create_material(
        "MaterialModuloInterno",
        (0.66, 0.65, 0.63),
        0.68,
        0.0,
        0.22
    )

    hole_material = create_material(
        "MaterialFuros",
        (0.018, 0.017, 0.016),
        0.88,
        0.0,
        0.05
    )

    screw_material = create_material(
        "MaterialParafuso",
        (0.36, 0.36, 0.35),
        0.38,
        0.35,
        0.40
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

    socket_positions = [0.027, -0.027]

    for socket_index, center_z in enumerate(socket_positions):
        outer_socket = create_uv_sphere(
            "ModuloExterno_" + str(socket_index),
            (0.0, 0.0110, center_z),
            (0.0225, 0.0040, 0.0195),
            socket_outer_material
        )

        inner_socket = create_uv_sphere(
            "ModuloInterno_" + str(socket_index),
            (0.0, 0.0142, center_z),
            (0.0195, 0.0026, 0.0165),
            socket_inner_material
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
        "socket_outer_material": socket_outer_material,
        "socket_inner_material": socket_inner_material
    }

def create_camera():
    camera_data = bpy.data.cameras.new("Camera")
    camera = bpy.data.objects.new("Camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)

    bpy.context.scene.camera = camera
    camera.data.sensor_width = 36.0
    camera.data.clip_start = 0.01
    camera.data.clip_end = 100.0

    return camera

def create_lights():
    key_data = bpy.data.lights.new("LuzPrincipal", type='AREA')
    key = bpy.data.objects.new("LuzPrincipal", key_data)
    bpy.context.scene.collection.objects.link(key)

    fill_data = bpy.data.lights.new("LuzPreenchimento", type='AREA')
    fill = bpy.data.objects.new("LuzPreenchimento", fill_data)
    bpy.context.scene.collection.objects.link(fill)

    return {
        "key": key,
        "fill": fill
    }

def randomize_materials(wall, outlet):
    gray = random.uniform(0.17, 0.245)
    warm = random.uniform(-0.008, 0.010)

    wall["material"].node_tree.nodes["Principled BSDF"].inputs[
        "Base Color"
    ].default_value = (
        gray + warm,
        gray,
        gray - warm,
        1.0
    )

    plate_value = random.uniform(0.66, 0.77)

    outlet["plate_material"].node_tree.nodes["Principled BSDF"].inputs[
        "Base Color"
    ].default_value = (
        plate_value + 0.012,
        plate_value,
        plate_value - 0.018,
        1.0
    )

    outer_value = plate_value - random.uniform(0.18, 0.23)

    outlet["socket_outer_material"].node_tree.nodes["Principled BSDF"].inputs[
        "Base Color"
    ].default_value = (
        outer_value + 0.006,
        outer_value,
        outer_value - 0.010,
        1.0
    )

    inner_value = plate_value - random.uniform(0.055, 0.090)

    outlet["socket_inner_material"].node_tree.nodes["Principled BSDF"].inputs[
        "Base Color"
    ].default_value = (
        inner_value + 0.006,
        inner_value,
        inner_value - 0.012,
        1.0
    )

def randomize_lights(lights, target):
    key = lights["key"]
    key.location = (
        random.uniform(-0.75, -0.48),
        random.uniform(0.60, 0.85),
        random.uniform(1.15, 1.50)
    )
    key.data.energy = random.uniform(28.0, 46.0)
    key.data.shape = 'RECTANGLE'
    key.data.size = random.uniform(0.80, 1.05)
    key.data.size_y = random.uniform(0.80, 1.05)
    point_at(key, target)

    fill = lights["fill"]
    fill.location = (
        random.uniform(0.50, 0.78),
        random.uniform(0.65, 0.90),
        random.uniform(0.85, 1.20)
    )
    fill.data.energy = random.uniform(7.0, 14.0)
    fill.data.shape = 'RECTANGLE'
    fill.data.size = random.uniform(0.70, 0.95)
    fill.data.size_y = random.uniform(0.70, 0.95)
    point_at(fill, target)

def compute_yolo_bbox(obj, camera):
    scene = bpy.context.scene
    projected = []

    for corner in obj.bound_box:
        world_corner = obj.matrix_world @ Vector(corner)
        projected.append(
            world_to_camera_view(scene, camera, world_corner)
        )

    if not projected:
        return None

    if max(point.z for point in projected) <= 0.0:
        return None

    min_x = max(0.0, min(point.x for point in projected))
    max_x = min(1.0, max(point.x for point in projected))
    min_y = max(0.0, min(point.y for point in projected))
    max_y = min(1.0, max(point.y for point in projected))

    if max_x <= min_x or max_y <= min_y:
        return None

    width = max_x - min_x
    height = max_y - min_y
    center_x = (min_x + max_x) / 2.0
    center_y = 1.0 - ((min_y + max_y) / 2.0)

    return center_x, center_y, width, height

def bbox_is_valid(bbox):
    if bbox is None:
        return False

    center_x, center_y, width, height = bbox

    if center_x < 0.20 or center_x > 0.80:
        return False

    if center_y < 0.20 or center_y > 0.80:
        return False

    if width < 0.13 or width > 0.30:
        return False

    if height < 0.22 or height > 0.43:
        return False

    return True

def randomize_outlet_and_camera(outlet, camera):
    outlet_x = random.uniform(-0.25, 0.25)
    outlet_z = random.uniform(0.78, 1.16)

    outlet["root"].location = (
        outlet_x,
        0.028,
        outlet_z
    )

    outlet["root"].rotation_euler = (
        math.radians(random.uniform(-0.4, 0.4)),
        math.radians(random.uniform(-1.8, 1.8)),
        math.radians(random.uniform(-1.5, 1.5))
    )

    camera.location = (
        outlet_x + random.uniform(-0.10, 0.10),
        random.uniform(0.53, 0.69),
        outlet_z + random.uniform(-0.045, 0.070)
    )

    camera.data.lens = random.uniform(50.0, 61.0)

    target = Vector((
        outlet_x + random.uniform(-0.006, 0.006),
        0.028,
        outlet_z + random.uniform(-0.006, 0.006)
    ))

    point_at(camera, target)

def use_fallback(outlet, camera, lights):
    outlet["root"].location = (0.0, 0.028, 0.96)
    outlet["root"].rotation_euler = (0.0, 0.0, 0.0)

    camera.location = (0.0, 0.61, 0.97)
    camera.data.lens = 55.0

    target = Vector((0.0, 0.028, 0.96))
    point_at(camera, target)
    randomize_lights(lights, target)

def write_label(path, bbox):
    center_x, center_y, width, height = bbox

    with open(path, "w", encoding="utf-8") as file:
        file.write(
            "{} {:.6f} {:.6f} {:.6f} {:.6f}\n".format(
                CLASS_ID,
                center_x,
                center_y,
                width,
                height
            )
        )

def generate_dataset():
    remove_previous_files()
    clear_scene()
    configure_render()

    wall = create_wall()
    outlet = create_outlet()
    camera = create_camera()
    lights = create_lights()

    bpy.context.view_layer.update()

    print("=" * 72)
    print("TESTE CORRIGIDO DE TOMADA AMERICANA")
    print("=" * 72)

    generated = 0

    for index in range(1, COUNT + 1):
        random.seed(SEED_BASE + index * 109)

        valid_bbox = None

        for attempt in range(60):
            randomize_materials(wall, outlet)
            randomize_outlet_and_camera(outlet, camera)

            target = Vector((
                outlet["root"].location.x,
                outlet["root"].location.y,
                outlet["root"].location.z
            ))

            randomize_lights(lights, target)
            bpy.context.view_layer.update()

            bbox = compute_yolo_bbox(outlet["plate"], camera)

            if bbox_is_valid(bbox):
                valid_bbox = bbox
                break

        if valid_bbox is None:
            use_fallback(outlet, camera, lights)
            bpy.context.view_layer.update()
            valid_bbox = compute_yolo_bbox(outlet["plate"], camera)

        if not bbox_is_valid(valid_bbox):
            raise RuntimeError(
                "Falha ao gerar caixa válida para a imagem {}".format(index)
            )

        filename = "{}_{:04d}".format(PREFIX, index)
        image_path = os.path.join(IMAGE_DIR, filename + ".png")
        label_path = os.path.join(LABEL_DIR, filename + ".txt")

        bpy.context.scene.render.filepath = image_path
        bpy.ops.render.render(write_still=True)
        write_label(label_path, valid_bbox)

        generated += 1

        print(
            "[{:02d}/{:02d}] {} | largura={:.3f} altura={:.3f}".format(
                generated,
                COUNT,
                filename,
                valid_bbox[2],
                valid_bbox[3]
            )
        )

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)

    print("=" * 72)
    print("CONCLUÍDO")
    print("Imagens:", generated)
    print("Labels:", generated)
    print("Blend:", BLEND_PATH)
    print("=" * 72)

generate_dataset()