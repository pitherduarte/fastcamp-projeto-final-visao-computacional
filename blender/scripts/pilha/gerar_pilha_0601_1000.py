import bpy
import os
import random
import math
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

BASE_DIR = r"C:\Users\pithe\Documents\Projetos\Github\fastcamp-projeto-final-visao-computacional"
IMAGES_DIR = os.path.join(BASE_DIR, "dataset_lotes", "pilha", "images")
LABELS_DIR = os.path.join(BASE_DIR, "dataset_lotes", "pilha", "labels")
BLEND_SAVE_DIR = os.path.join(BASE_DIR, "blender", "cenas")
BLEND_FILEPATH = os.path.join(
    BLEND_SAVE_DIR,
    "pilha_dataset_0601_1000.blend"
)

PREFIX = "pilha"
CLASS_ID = 2

START_INDEX = 601
END_INDEX = 1000
SEED_BASE = 6100

SKIP_EXISTING = True

RESOLUTION = 640
TABLE_Z = 0.0

BATTERY_LENGTH = 0.062
BATTERY_RADIUS = 0.009
COPPER_FRACTION = 0.34
MAX_BATTERIES = 6


def ensure_directories():
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(LABELS_DIR, exist_ok=True)
    os.makedirs(BLEND_SAVE_DIR, exist_ok=True)


def save_blend_file():
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_FILEPATH)
    print(f"BLEND SALVO: {BLEND_FILEPATH}")


def reset_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    for collection_name in ["Setup", "Template", "Instances"]:
        collection = bpy.data.collections.get(collection_name)

        if collection is not None:
            for parent in list(bpy.data.collections):
                if collection.name in parent.children:
                    parent.children.unlink(collection)

            if collection.name in bpy.context.scene.collection.children:
                bpy.context.scene.collection.children.unlink(collection)

            bpy.data.collections.remove(collection)

    for datablocks in [
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.cameras,
        bpy.data.lights
    ]:
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def create_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(obj, collection):
    for current_collection in list(obj.users_collection):
        current_collection.objects.unlink(obj)

    if collection.objects.get(obj.name) is None:
        collection.objects.link(obj)


def remove_material(name):
    material = bpy.data.materials.get(name)

    if material is not None:
        bpy.data.materials.remove(material, do_unlink=True)


def create_simple_material(
    name,
    color,
    metallic,
    roughness,
    specular
):
    remove_material(name)

    material = bpy.data.materials.new(name)
    material.use_nodes = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")

    principled.inputs["Base Color"].default_value = color
    principled.inputs["Metallic"].default_value = metallic
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Specular"].default_value = specular

    links.new(
        principled.outputs["BSDF"],
        output.inputs["Surface"]
    )

    return material


def create_wood_material():
    remove_material("WoodMaterial")

    material = bpy.data.materials.new("WoodMaterial")
    material.use_nodes = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    texture_coordinate = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    noise = nodes.new("ShaderNodeTexNoise")
    wave = nodes.new("ShaderNodeTexWave")
    mix = nodes.new("ShaderNodeMixRGB")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")

    mapping.vector_type = 'POINT'
    mapping.inputs["Scale"].default_value = (
        1.3,
        5.0,
        1.0
    )

    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Distortion"].default_value = 0.18

    if noise.inputs.get("Roughness") is not None:
        noise.inputs["Roughness"].default_value = 0.52

    wave.wave_type = 'BANDS'
    wave.bands_direction = 'X'
    wave.inputs["Scale"].default_value = 4.2
    wave.inputs["Distortion"].default_value = 2.6

    if wave.inputs.get("Detail") is not None:
        wave.inputs["Detail"].default_value = 2.0

    if wave.inputs.get("Detail Scale") is not None:
        wave.inputs["Detail Scale"].default_value = 1.4

    mix.blend_type = 'MULTIPLY'
    mix.inputs["Fac"].default_value = 0.24

    ramp.color_ramp.elements[0].position = 0.20
    ramp.color_ramp.elements[0].color = (
        0.018,
        0.004,
        0.001,
        1.0
    )

    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = (
        0.115,
        0.025,
        0.004,
        1.0
    )

    principled.inputs["Roughness"].default_value = 0.60
    principled.inputs["Specular"].default_value = 0.26

    bump.inputs["Strength"].default_value = 0.045
    bump.inputs["Distance"].default_value = 0.020

    links.new(
        texture_coordinate.outputs["Generated"],
        mapping.inputs["Vector"]
    )

    links.new(
        mapping.outputs["Vector"],
        noise.inputs["Vector"]
    )

    links.new(
        mapping.outputs["Vector"],
        wave.inputs["Vector"]
    )

    links.new(
        noise.outputs["Fac"],
        mix.inputs["Color1"]
    )

    links.new(
        wave.outputs["Fac"],
        mix.inputs["Color2"]
    )

    links.new(
        mix.outputs["Color"],
        ramp.inputs["Fac"]
    )

    links.new(
        ramp.outputs["Color"],
        principled.inputs["Base Color"]
    )

    links.new(
        noise.outputs["Fac"],
        bump.inputs["Height"]
    )

    links.new(
        bump.outputs["Normal"],
        principled.inputs["Normal"]
    )

    links.new(
        principled.outputs["BSDF"],
        output.inputs["Surface"]
    )

    return material


def configure_render():
    scene = bpy.context.scene

    scene.render.engine = 'BLENDER_EEVEE'

    scene.eevee.taa_render_samples = 24
    scene.eevee.taa_samples = 8

    scene.eevee.use_gtao = True
    scene.eevee.gtao_distance = 1.4
    scene.eevee.gtao_factor = 1.10
    scene.eevee.use_soft_shadows = True

    if hasattr(scene.eevee, "use_bloom"):
        scene.eevee.use_bloom = False

    if hasattr(scene.eevee, "use_ssr"):
        scene.eevee.use_ssr = False

    if hasattr(scene.eevee, "use_motion_blur"):
        scene.eevee.use_motion_blur = False

    if hasattr(scene.eevee, "shadow_cube_size"):
        scene.eevee.shadow_cube_size = '512'

    if hasattr(scene.eevee, "shadow_cascade_size"):
        scene.eevee.shadow_cascade_size = '512'

    if hasattr(scene.eevee, "use_high_quality_normals"):
        scene.eevee.use_high_quality_normals = False

    scene.render.resolution_x = RESOLUTION
    scene.render.resolution_y = RESOLUTION
    scene.render.resolution_percentage = 100

    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 5

    scene.render.film_transparent = False

    if hasattr(scene.render, "use_persistent_data"):
        scene.render.use_persistent_data = True

    scene.display_settings.display_device = 'sRGB'
    scene.view_settings.view_transform = 'Filmic'

    try:
        scene.view_settings.look = 'Medium High Contrast'
    except:
        try:
            scene.view_settings.look = 'Medium Contrast'
        except:
            pass

    scene.view_settings.exposure = -1.45
    scene.view_settings.gamma = 0.98

    world = bpy.data.worlds.get("World")

    if world is None:
        world = bpy.data.worlds.new("World")
        scene.world = world

    world.use_nodes = True

    background = world.node_tree.nodes.get("Background")

    if background is not None:
        background.inputs["Color"].default_value = (
            0.012,
            0.007,
            0.004,
            1.0
        )

        background.inputs["Strength"].default_value = 0.045


def create_table(collection, material):
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(
            0.0,
            0.0,
            TABLE_Z - 0.035
        )
    )

    table = bpy.context.active_object
    table.name = "WoodTable"

    table.dimensions = (
        2.4,
        1.8,
        0.07
    )

    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True
    )

    move_to_collection(table, collection)

    table.data.materials.clear()
    table.data.materials.append(material)

    bevel = table.modifiers.new(
        "TableBevel",
        type='BEVEL'
    )

    bevel.width = 0.008
    bevel.segments = 2

    bpy.ops.object.select_all(action='DESELECT')
    table.select_set(True)
    bpy.context.view_layer.objects.active = table

    bpy.ops.object.modifier_apply(
        modifier=bevel.name
    )

    table.select_set(False)

    return table


def create_empty(name, location, collection):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = 'PLAIN_AXES'
    obj.location = location

    collection.objects.link(obj)

    return obj


def create_camera(collection):
    camera_data = bpy.data.cameras.new(
        "DatasetCameraData"
    )

    camera_data.lens = 56.0
    camera_data.sensor_width = 36.0

    camera = bpy.data.objects.new(
        "DatasetCamera",
        camera_data
    )

    collection.objects.link(camera)

    target = create_empty(
        "CameraTarget",
        (
            0.0,
            0.0,
            0.02
        ),
        collection
    )

    constraint = camera.constraints.new(
        type='TRACK_TO'
    )

    constraint.target = target
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'

    bpy.context.scene.camera = camera

    return camera, target


def create_area_light(
    name,
    collection,
    energy,
    size,
    shadows,
    contact_shadows
):
    light_data = bpy.data.lights.new(
        name + "Data",
        type='AREA'
    )

    light_data.energy = energy
    light_data.shape = 'DISK'
    light_data.size = size

    if hasattr(light_data, "use_shadow"):
        light_data.use_shadow = shadows

    if hasattr(light_data, "use_contact_shadow"):
        light_data.use_contact_shadow = contact_shadows

    light = bpy.data.objects.new(
        name,
        light_data
    )

    collection.objects.link(light)

    return light


def create_lights(collection):
    key = create_area_light(
        "KeyLight",
        collection,
        280.0,
        0.52,
        True,
        True
    )

    fill = create_area_light(
        "FillLight",
        collection,
        58.0,
        0.74,
        False,
        False
    )

    rim = create_area_light(
        "RimLight",
        collection,
        28.0,
        0.46,
        False,
        False
    )

    return key, fill, rim


def configure_lights(
    key,
    fill,
    rim,
    center_x,
    center_y
):
    key.location = (
        center_x + random.uniform(0.20, 0.28),
        center_y + random.uniform(-0.24, -0.16),
        random.uniform(0.46, 0.56)
    )

    fill.location = (
        center_x + random.uniform(-0.30, -0.22),
        center_y + random.uniform(-0.18, -0.10),
        random.uniform(0.28, 0.37)
    )

    rim.location = (
        center_x + random.uniform(-0.05, 0.08),
        center_y + random.uniform(0.24, 0.32),
        random.uniform(0.34, 0.44)
    )

    key.data.energy = random.uniform(
        235.0,
        315.0
    )

    fill.data.energy = random.uniform(
        42.0,
        72.0
    )

    rim.data.energy = random.uniform(
        18.0,
        36.0
    )


def create_cylinder(
    name,
    radius,
    depth,
    location,
    material,
    collection,
    bevel_width
):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=40,
        radius=radius,
        depth=depth,
        location=location
    )

    obj = bpy.context.active_object
    obj.name = name

    move_to_collection(
        obj,
        collection
    )

    obj.data.materials.clear()
    obj.data.materials.append(material)

    bevel = obj.modifiers.new(
        name + "Bevel",
        type='BEVEL'
    )

    bevel.width = bevel_width
    bevel.segments = 2

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.modifier_apply(
        modifier=bevel.name
    )

    try:
        bpy.ops.object.shade_smooth()
    except:
        pass

    obj.select_set(False)

    return obj


def build_battery_template(
    collection,
    black_material,
    copper_material,
    metal_material,
    dark_metal_material
):
    root = create_empty(
        "BatteryTemplate",
        (
            0.0,
            0.0,
            0.0
        ),
        collection
    )

    body = create_cylinder(
        "BatteryBody",
        BATTERY_RADIUS,
        BATTERY_LENGTH,
        (
            0.0,
            0.0,
            0.0
        ),
        black_material,
        collection,
        BATTERY_RADIUS * 0.075
    )

    copper_depth = (
        BATTERY_LENGTH
        * COPPER_FRACTION
    )

    copper_center_z = (
        BATTERY_LENGTH * 0.5
        - copper_depth * 0.5
    )

    copper = create_cylinder(
        "BatteryCopper",
        BATTERY_RADIUS * 1.006,
        copper_depth,
        (
            0.0,
            0.0,
            copper_center_z
        ),
        copper_material,
        collection,
        BATTERY_RADIUS * 0.045
    )

    transition_z = (
        BATTERY_LENGTH * 0.5
        - copper_depth
    )

    transition_ring = create_cylinder(
        "BatteryTransitionRing",
        BATTERY_RADIUS * 1.012,
        BATTERY_LENGTH * 0.012,
        (
            0.0,
            0.0,
            transition_z
        ),
        dark_metal_material,
        collection,
        BATTERY_RADIUS * 0.02
    )

    top_cap_depth = (
        BATTERY_LENGTH
        * 0.025
    )

    top_cap = create_cylinder(
        "BatteryTopCap",
        BATTERY_RADIUS * 0.91,
        top_cap_depth,
        (
            0.0,
            0.0,
            BATTERY_LENGTH * 0.5
            + top_cap_depth * 0.45
        ),
        metal_material,
        collection,
        BATTERY_RADIUS * 0.035
    )

    nub_depth = (
        BATTERY_LENGTH
        * 0.045
    )

    nub = create_cylinder(
        "BatteryNub",
        BATTERY_RADIUS * 0.34,
        nub_depth,
        (
            0.0,
            0.0,
            BATTERY_LENGTH * 0.5
            + top_cap_depth
            + nub_depth * 0.42
        ),
        metal_material,
        collection,
        BATTERY_RADIUS * 0.04
    )

    bottom_depth = (
        BATTERY_LENGTH
        * 0.018
    )

    bottom = create_cylinder(
        "BatteryBottom",
        BATTERY_RADIUS * 0.88,
        bottom_depth,
        (
            0.0,
            0.0,
            -BATTERY_LENGTH * 0.5
            - bottom_depth * 0.35
        ),
        dark_metal_material,
        collection,
        BATTERY_RADIUS * 0.025
    )

    body.parent = root
    copper.parent = root
    transition_ring.parent = root
    top_cap.parent = root
    nub.parent = root
    bottom.parent = root

    set_hierarchy_visibility(
        root,
        False
    )

    return root


def duplicate_hierarchy_shared(
    source,
    collection,
    parent_copy=None
):
    obj_copy = source.copy()
    collection.objects.link(obj_copy)

    obj_copy.location = source.location.copy()
    obj_copy.rotation_euler = source.rotation_euler.copy()
    obj_copy.scale = source.scale.copy()

    if parent_copy is not None:
        obj_copy.parent = parent_copy
        obj_copy.matrix_parent_inverse = (
            source.matrix_parent_inverse.copy()
        )

    for child in source.children:
        duplicate_hierarchy_shared(
            child,
            collection,
            obj_copy
        )

    return obj_copy


def hierarchy_objects(root):
    result = [root]
    stack = [root]

    while stack:
        current = stack.pop()

        for child in current.children:
            result.append(child)
            stack.append(child)

    return result


def set_hierarchy_visibility(
    root,
    visible
):
    hidden = not visible

    for obj in hierarchy_objects(root):
        obj.hide_viewport = hidden
        obj.hide_render = hidden


def create_battery_pool(
    template,
    instances_collection
):
    pool = []

    for index in range(MAX_BATTERIES):
        root = duplicate_hierarchy_shared(
            template,
            instances_collection
        )

        root.name = (
            f"BatteryPool_{index + 1:02d}"
        )

        set_hierarchy_visibility(
            root,
            False
        )

        pool.append(root)

    return pool


def mesh_descendants(root):
    result = []
    stack = [root]

    while stack:
        current = stack.pop()

        for child in current.children:
            stack.append(child)

            if child.type == 'MESH':
                result.append(child)

    return result


def choose_count(index):
    if 601 <= index <= 650:
        return 1

    if 651 <= index <= 750:
        return 2

    if 751 <= index <= 900:
        return random.choice([3, 4])

    if 901 <= index <= 1000:
        return random.choice([5, 6])

    raise ValueError(
        f"Índice fora do intervalo previsto: {index}"
    )


def choose_orientations(count):
    if count == 1:
        return [
            random.choice([
                "UP",
                "SIDE"
            ])
        ]

    upright_count = random.randint(
        1,
        count - 1
    )

    orientations = (
        ["UP"] * upright_count
        + ["SIDE"] * (
            count - upright_count
        )
    )

    random.shuffle(orientations)

    return orientations


def footprint_radius(orientation):
    if orientation == "UP":
        return 0.025

    return 0.047


def apply_pose(
    root,
    orientation,
    x,
    y
):
    if orientation == "UP":
        root.location = (
            x,
            y,
            TABLE_Z
            + BATTERY_LENGTH * 0.51
        )

        root.rotation_euler = (
            random.uniform(
                -math.radians(2.5),
                math.radians(2.5)
            ),
            random.uniform(
                -math.radians(2.5),
                math.radians(2.5)
            ),
            random.uniform(
                0.0,
                math.tau
            )
        )

    else:
        root.location = (
            x,
            y,
            TABLE_Z
            + BATTERY_RADIUS * 1.05
        )

        root.rotation_euler = (
            0.0,
            math.radians(90.0)
            + random.uniform(
                -math.radians(2.5),
                math.radians(2.5)
            ),
            random.uniform(
                0.0,
                math.tau
            )
        )


def configure_pool(
    pool,
    count
):
    active = []

    for index, root in enumerate(pool):
        visible = index < count

        set_hierarchy_visibility(
            root,
            visible
        )

        if visible:
            active.append(root)

    return active


def place_batteries(
    roots,
    orientations
):
    placed = []

    for root, orientation in zip(
        roots,
        orientations
    ):
        radius = footprint_radius(
            orientation
        )

        success = False

        for attempt in range(800):
            x = random.uniform(
                -0.17,
                0.17
            )

            y = random.uniform(
                -0.115,
                0.12
            )

            valid = True

            for (
                existing_x,
                existing_y,
                existing_radius
            ) in placed:
                distance = math.sqrt(
                    (x - existing_x) ** 2
                    + (y - existing_y) ** 2
                )

                required_distance = (
                    radius
                    + existing_radius
                    + 0.010
                )

                if distance < required_distance:
                    valid = False
                    break

            if not valid:
                continue

            apply_pose(
                root,
                orientation,
                x,
                y
            )

            placed.append(
                (
                    x,
                    y,
                    radius
                )
            )

            success = True
            break

        if not success:
            return None

    return placed


def configure_camera(
    camera,
    target,
    count,
    positions
):
    center_x = sum(
        position[0]
        for position in positions
    ) / len(positions)

    center_y = sum(
        position[1]
        for position in positions
    ) / len(positions)

    if count == 1:
        distance = 0.27
        height = 0.19

        lens = random.uniform(
            59.0,
            64.0
        )

    elif count == 2:
        distance = 0.32
        height = 0.22

        lens = random.uniform(
            57.0,
            62.0
        )

    elif count <= 4:
        distance = 0.39
        height = 0.27

        lens = random.uniform(
            54.0,
            59.0
        )

    else:
        distance = 0.46
        height = 0.31

        lens = random.uniform(
            51.0,
            56.0
        )

    target.location = (
        center_x,
        center_y,
        0.018
    )

    camera.location = (
        center_x
        + random.uniform(
            -0.025,
            0.025
        ),
        center_y - distance,
        height
        + random.uniform(
            -0.012,
            0.012
        )
    )

    camera.data.lens = lens

    return center_x, center_y


def get_yolo_bbox(
    root,
    camera,
    scene
):
    meshes = mesh_descendants(root)

    if not meshes:
        return None

    projected_points = []

    for obj in meshes:
        for corner in obj.bound_box:
            world_corner = (
                obj.matrix_world
                @ Vector(corner)
            )

            projected = world_to_camera_view(
                scene,
                camera,
                world_corner
            )

            if projected.z <= 0.0:
                return None

            projected_points.append(
                projected
            )

    minimum_x = min(
        point.x
        for point in projected_points
    )

    maximum_x = max(
        point.x
        for point in projected_points
    )

    minimum_y = min(
        point.y
        for point in projected_points
    )

    maximum_y = max(
        point.y
        for point in projected_points
    )

    if minimum_x < 0.015:
        return None

    if maximum_x > 0.985:
        return None

    if minimum_y < 0.015:
        return None

    if maximum_y > 0.985:
        return None

    width = maximum_x - minimum_x
    height = maximum_y - minimum_y

    if width < 0.045:
        return None

    if height < 0.045:
        return None

    center_x = (
        minimum_x
        + maximum_x
    ) * 0.5

    center_y = 1.0 - (
        (
            minimum_y
            + maximum_y
        ) * 0.5
    )

    return (
        center_x,
        center_y,
        width,
        height
    )


def save_labels(path, boxes):
    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:
        for box in boxes:
            file.write(
                f"{CLASS_ID} "
                f"{box[0]:.6f} "
                f"{box[1]:.6f} "
                f"{box[2]:.6f} "
                f"{box[3]:.6f}\n"
            )


def render_image(path):
    scene = bpy.context.scene
    scene.render.filepath = path

    bpy.ops.render.render(
        write_still=True
    )


def sample_paths(index):
    image_path = os.path.join(
        IMAGES_DIR,
        f"{PREFIX}_{index:04d}.png"
    )

    label_path = os.path.join(
        LABELS_DIR,
        f"{PREFIX}_{index:04d}.txt"
    )

    return image_path, label_path


def sample_exists(index):
    image_path, label_path = sample_paths(
        index
    )

    return (
        os.path.isfile(image_path)
        and os.path.isfile(label_path)
    )


def generate_sample(
    index,
    scene,
    pool,
    camera,
    target,
    key,
    fill,
    rim
):
    for attempt in range(120):
        count = choose_count(index)

        active_roots = configure_pool(
            pool,
            count
        )

        orientations = choose_orientations(
            count
        )

        positions = place_batteries(
            active_roots,
            orientations
        )

        if positions is None:
            continue

        center_x, center_y = configure_camera(
            camera,
            target,
            count,
            positions
        )

        configure_lights(
            key,
            fill,
            rim,
            center_x,
            center_y
        )

        bpy.context.view_layer.update()

        boxes = []
        valid = True

        for root in active_roots:
            box = get_yolo_bbox(
                root,
                camera,
                scene
            )

            if box is None:
                valid = False
                break

            boxes.append(box)

        if not valid:
            continue

        image_path, label_path = sample_paths(
            index
        )

        render_image(image_path)

        save_labels(
            label_path,
            boxes
        )

        print(
            f"OK {index:04d} | "
            f"pilhas: {count} | "
            f"orientacoes: {orientations}"
        )

        return True

    print(
        f"FALHOU {index:04d}"
    )

    return False


def main():
    ensure_directories()
    reset_scene()
    configure_render()

    setup_collection = create_collection(
        "Setup"
    )

    template_collection = create_collection(
        "Template"
    )

    instances_collection = create_collection(
        "Instances"
    )

    wood_material = create_wood_material()

    black_material = create_simple_material(
        "BatteryBlack",
        (
            0.003,
            0.003,
            0.003,
            1.0
        ),
        0.01,
        0.30,
        0.42
    )

    copper_material = create_simple_material(
        "BatteryCopper",
        (
            0.28,
            0.042,
            0.005,
            1.0
        ),
        0.38,
        0.29,
        0.46
    )

    metal_material = create_simple_material(
        "BatteryMetal",
        (
            0.19,
            0.19,
            0.19,
            1.0
        ),
        0.76,
        0.23,
        0.50
    )

    dark_metal_material = create_simple_material(
        "BatteryDarkMetal",
        (
            0.045,
            0.045,
            0.045,
            1.0
        ),
        0.58,
        0.27,
        0.46
    )

    create_table(
        setup_collection,
        wood_material
    )

    camera, target = create_camera(
        setup_collection
    )

    key, fill, rim = create_lights(
        setup_collection
    )

    template = build_battery_template(
        template_collection,
        black_material,
        copper_material,
        metal_material,
        dark_metal_material
    )

    pool = create_battery_pool(
        template,
        instances_collection
    )

    save_blend_file()

    scene = bpy.context.scene

    print("=" * 72)
    print("PILHA | LOTE COMPLEMENTAR 0601–1000")
    print(f"INTERVALO: {START_INDEX:04d}-{END_INDEX:04d}")
    print(f"IMAGENS: {IMAGES_DIR}")
    print(f"LABELS: {LABELS_DIR}")
    print(f"BLEND: {BLEND_FILEPATH}")
    print("=" * 72)

    generated = 0
    skipped = 0

    for index in range(
        START_INDEX,
        END_INDEX + 1
    ):
        if (
            SKIP_EXISTING
            and sample_exists(index)
        ):
            print(
                f"PULADO {index:04d} | "
                "imagem e label já existem"
            )

            skipped += 1
            continue

        random.seed(
            SEED_BASE + index
        )

        success = generate_sample(
            index,
            scene,
            pool,
            camera,
            target,
            key,
            fill,
            rim
        )

        if not success:
            print(
                f"INTERROMPIDO NO ÍNDICE "
                f"{index:04d}"
            )

            save_blend_file()
            return

        generated += 1

    for root in pool:
        set_hierarchy_visibility(
            root,
            False
        )

    save_blend_file()

    print("=" * 72)
    print("GERAÇÃO CONCLUÍDA")
    print(f"NOVAS IMAGENS: {generated}")
    print(f"ARQUIVOS PULADOS: {skipped}")
    print("=" * 72)


main()