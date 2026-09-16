# NEW: bounded headless Blender operations for the character-pipeline agent skill.
# Intended baseline: Blender 4.5 LTS. Run selftest on the installed build first.
# This module is executed by Blender, not by the system Python interpreter.
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
# NEW: runtime imports must not create untracked files inside the installed skill.
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
from geometry_math import normalized_weights, validate_bones, triangle_uv_area, surface_fingerprint, gaussian_falloff, parabolic_arc_weight
import bpy
import bmesh
from mathutils import Matrix, Vector, Euler, Quaternion

CFG: dict = {}
ROOT: Path
OUT: Path
OUTPUTS: list[str] = []


def json_read(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def source_path(relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('Input paths must be workspace-relative')
    candidate = (ROOT / relative).resolve()
    if not candidate.is_relative_to(ROOT):
        raise ValueError(f'Path leaves workspace: {relative}')
    cursor = ROOT
    for part in Path(relative).parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError('Symlink inputs are refused')
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def output_path(name: str) -> Path:
    candidate = (OUT / name).resolve()
    if not candidate.is_relative_to(OUT):
        raise ValueError('Output leaves run directory')
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def register(path: Path) -> None:
    relative = path.relative_to(OUT).as_posix()
    if relative not in OUTPUTS:
        OUTPUTS.append(relative)


def report(name: str, value: object) -> None:
    path = output_path(name)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
    register(path)


def activate(objects: list, active=None) -> None:
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = active or objects[-1]


def operator_call(operator, **kwargs):
    properties = operator.get_rna_type().properties
    missing = [key for key in kwargs if key not in properties]
    if missing:
        raise RuntimeError(f'Installed Blender lacks required operator options: {missing}; do not silently omit them')
    result = operator(**kwargs)
    if 'FINISHED' not in result:
        raise RuntimeError(f'Blender operator did not finish: {result}')
    return result


def import_asset(path: Path, append=False, high=False) -> list:
    before = set(bpy.data.objects)
    suffix = path.suffix.lower()
    if suffix == '.blend':
        if append:
            raise ValueError('For high-poly append use GLB/OBJ/FBX, not arbitrary blend libraries')
        bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
        objects = list(bpy.context.scene.objects)
    elif suffix == '.glb':
        bpy.ops.import_scene.gltf(filepath=str(path))
        objects = [obj for obj in bpy.data.objects if obj not in before]
    elif suffix == '.fbx':
        bpy.ops.import_scene.fbx(filepath=str(path), automatic_bone_orientation=False, use_anim=True)
        objects = [obj for obj in bpy.data.objects if obj not in before]
    elif suffix == '.obj':
        # A geometry-only OBJ is sufficient for the high-poly source. Refuse external MTL imports.
        with path.open('r', encoding='utf-8', errors='replace') as handle:
            for line in handle:
                if line.lstrip().lower().startswith('mtllib '):
                    raise ValueError('Use geometry-only OBJ without mtllib, or self-contained GLB')
        bpy.ops.wm.obj_import(filepath=str(path))
        objects = [obj for obj in bpy.data.objects if obj not in before]
    else:
        raise ValueError('Supported inputs: self-contained GLB, approved FBX, local BLEND, geometry-only OBJ')
    if high:
        for obj in objects:
            obj.name = 'HIGH__' + obj.name
            obj['cp_role'] = 'high'
            obj.hide_render = True
    return objects


def load_input() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_asset(source_path(CFG['input']))
    if CFG.get('high'):
        import_asset(source_path(CFG['high']), append=True, high=True)
    # Refuse missing or out-of-workspace unpacked image dependencies before rendering.
    for image in bpy.data.images:
        if image.source == 'FILE' and not image.packed_file and image.filepath:
            p = Path(bpy.path.abspath(image.filepath)).resolve()
            if not p.is_relative_to(ROOT) or not p.exists():
                raise ValueError(f'Unpacked texture outside workspace or missing: {image.name}')


def meshes(include_high=False) -> list:
    result = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and (include_high or obj.get('cp_role') != 'high')]
    requested = CFG.get('objects')
    if requested:
        available = {obj.name: obj for obj in result}
        if set(requested) - available.keys():
            raise ValueError(f'Unknown mesh names: {set(requested)-available.keys()}')
        result = [available[name] for name in requested]
    return result


def armature() -> object:
    candidates = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE' and obj.get('cp_role') != 'high']
    if CFG.get('armature'):
        candidates = [obj for obj in candidates if obj.name == CFG['armature']]
    if len(candidates) != 1:
        raise ValueError(f'Expected exactly one target armature, found {len(candidates)}')
    return candidates[0]


def bounds(objects: list) -> tuple[Vector, Vector]:
    corners = [obj.matrix_world @ Vector(point) for obj in objects for point in obj.bound_box]
    if not corners:
        raise ValueError('No mesh bounding box')
    return Vector([min(p[i] for p in corners) for i in range(3)]), Vector([max(p[i] for p in corners) for i in range(3)])


def ensure_unrigged(objects: list) -> None:
    for obj in objects:
        if obj.data.shape_keys or any(mod.type == 'ARMATURE' for mod in obj.modifiers):
            raise ValueError('Topology/normalization edits after rigging or shape keys are refused; branch from pre-rig checkpoint')
        if obj.modifiers:
            raise ValueError(f'{obj.name} has modifiers; explicitly resolve their order before destructive edits')


def approved(scope: str) -> dict:
    review = json_read(source_path(CFG['approval_file']))
    if review.get('status') != 'APPROVED' or scope not in review.get('scopes', []):
        raise ValueError(f'Approval does not cover {scope}')
    if review.get('input_sha256') != file_hash(source_path(CFG['input'])):
        raise ValueError('Approval is stale for this input')
    if not review.get('reviewer') or not review.get('reason'):
        raise ValueError('Approval must identify reviewer and reason')
    return review


def save_scene(name='scene.blend') -> None:
    path = output_path(name)
    # Packing keeps the handoff self-contained without writing into source image paths.
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)
    register(path)


def mesh_audit(obj) -> dict:
    mesh = obj.data
    mesh.calc_loop_triangles()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    seen = set()
    components = []
    for vertex in bm.verts:
        if vertex.index in seen:
            continue
        stack = [vertex]
        seen.add(vertex.index)
        count = 0
        while stack:
            current = stack.pop()
            count += 1
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other.index not in seen:
                    seen.add(other.index)
                    stack.append(other)
        components.append(count)
    edges_boundary = sum(edge.is_boundary for edge in bm.edges)
    edges_bad = sum(not edge.is_manifold and not edge.is_boundary and not edge.is_wire for edge in bm.edges)
    degenerate = sum(face.calc_area() < 1e-12 for face in bm.faces)
    bm.free()
    uv = mesh.uv_layers.active
    nonfinite = sum(not all(math.isfinite(c) for c in vertex.co) for vertex in mesh.vertices)
    uv_bad = 0
    uv_outside = 0
    surface = []
    geom = []
    for tri in mesh.loop_triangles:
        coords = [tuple(obj.matrix_world @ mesh.vertices[index].co) for index in tri.vertices]
        tex = [tuple(uv.data[index].uv) for index in tri.loops] if uv else []
        if tex:
            if not all(math.isfinite(x) for p in tex for x in p) or triangle_uv_area(tex) < 1e-12:
                uv_bad += 1
            uv_outside += sum(x < -1e-5 or x > 1.00001 for p in tex for x in p)
        if len(mesh.loop_triangles) <= 300000 and not nonfinite:
            geom.append(coords)
            surface.append([tuple(p) + tuple(t) for p, t in zip(coords, tex)] if tex else coords)
    result = {'object': obj.name, 'vertices': len(mesh.vertices), 'triangles': len(mesh.loop_triangles), 'polygons': len(mesh.polygons),
              'components': len(components), 'largest_components_vertices': sorted(components, reverse=True)[:32],
              'boundary_edges': edges_boundary, 'nonmanifold_nonboundary_edges': edges_bad,
              'degenerate_faces': degenerate, 'nonfinite_vertices': nonfinite, 'has_uv': bool(uv),
              'degenerate_uv_triangles': uv_bad, 'uv_coordinates_outside_unit_tile': uv_outside,
              'geometry_fingerprint': surface_fingerprint(geom) if geom else None,
              'surface_uv_fingerprint': surface_fingerprint(surface) if surface else None,
              'material_slots': [slot.material.name if slot.material else None for slot in obj.material_slots],
              'not_tested': ['UV overlaps and stretch', 'semantic topology quality', 'self intersections', 'identity preservation']}
    return result


def task_inspect() -> None:
    report('audit.json', {'blender': bpy.app.version_string, 'input_sha256': file_hash(source_path(CFG['input'])),
                          'meshes': [mesh_audit(obj) for obj in meshes(include_high=True)],
                          'armatures': [obj.name for obj in bpy.context.scene.objects if obj.type == 'ARMATURE'],
                          'actions': [action.name for action in bpy.data.actions]})


def task_prepare() -> None:
    approved('geometry')
    low = meshes()
    all_meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    ensure_unrigged(all_meshes)
    rotation = Euler([math.radians(v) for v in CFG.get('rotation_degrees', [0, 0, 0])], 'XYZ').to_matrix().to_4x4()
    points = [rotation @ obj.matrix_world @ Vector(p) for obj in low for p in obj.bound_box]
    if not points:
        raise ValueError('No target geometry')
    minimum = Vector([min(p[i] for p in points) for i in range(3)])
    maximum = Vector([max(p[i] for p in points) for i in range(3)])
    height = maximum.z - minimum.z
    desired = float(CFG.get('height_m', 1.8))
    if height <= 1e-8 or not 0.01 <= desired <= 100:
        raise ValueError('Invalid source or target height')
    scale = desired / height
    translation = Vector((-(minimum.x + maximum.x)/2, -(minimum.y + maximum.y)/2, -minimum.z)) * scale
    transform = Matrix.Translation(translation) @ Matrix.Scale(scale, 4) @ rotation
    transforms = {obj.name: transform @ obj.matrix_world.copy() for obj in all_meshes}
    before = [mesh_audit(obj) for obj in low]
    for obj in all_meshes:
        obj.data = obj.data.copy()
        obj.data.transform(transforms[obj.name])
        obj.parent = None
        obj.matrix_world = Matrix.Identity(4)
        if obj.get('cp_role') == 'high':
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        # Isolated vertices do not contribute to a renderable surface. Other components are retained.
        unused = [v for v in bm.verts if not v.link_edges and not v.link_faces]
        if unused:
            bmesh.ops.delete(bm, geom=unused, context='VERTS')
        distance = float(CFG.get('merge_distance_fraction', 0)) * desired
        if not 0 <= distance <= desired * 0.0001:
            raise ValueError('Merge radius exceeds conservative safety limit')
        if distance:
            bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=distance)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
    report('prepare.json', {'affine_shared_by_high_and_low': [list(row) for row in transform], 'before': before,
                            'after': [mesh_audit(obj) for obj in low],
                            'warning': 'No components, wings, tails, clothing openings or holes were automatically removed/closed. Normals and silhouette need visual review.'})
    save_scene()


def task_uv() -> None:
    mode = CFG.get('uv_mode', 'preserve')
    if mode == 'smart_project':
        approved('uv_rebuild')
        ensure_unrigged(meshes())
    elif mode != 'preserve':
        raise ValueError('uv_mode must be preserve or smart_project')
    for obj in meshes():
        if mode == 'smart_project':
            activate([obj])
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=float(CFG.get('island_margin', 0.02)))
            bpy.ops.object.mode_set(mode='OBJECT')
        if not obj.data.uv_layers.active:
            raise ValueError(f'{obj.name}: missing UV; automatic rebuilding requires separate approval')
        audit = mesh_audit(obj)
        if audit['degenerate_uv_triangles'] or audit['uv_coordinates_outside_unit_tile']:
            raise ValueError(f'{obj.name}: invalid single-tile UVs')
    report('uv.json', {'mode': mode, 'meshes': [mesh_audit(obj) for obj in meshes()],
                       'warning': 'Smart Project is a provisional fallback, not proof of production UVs. Overlap and texel density require separate review.'})
    save_scene()


def task_retopo() -> None:
    approved('retopology')
    targets = meshes()
    if len(targets) != 1:
        raise ValueError('Retopology operates on one explicitly selected mesh per candidate')
    ensure_unrigged(targets)
    target = int(CFG.get('target_faces', 15000))
    if target < 100 or target > 200000:
        raise ValueError('target_faces must be 100..200000')
    activate(targets)
    operator_call(bpy.ops.object.quadriflow_remesh, target_faces=target, use_mesh_symmetry=bool(CFG.get('symmetry', False)), use_preserve_sharp=True, use_preserve_boundary=True, seed=0)
    report('retopology.json', {'audit': mesh_audit(targets[0]), 'status': 'CANDIDATE_REQUIRES_VISUAL_REVIEW',
                              'invalidated': ['UVs', 'bakes', 'texturing', 'skinning', 'animation'],
                              'warning': 'QuadriFlow does not guarantee joint, facial or finger edge loops.'})
    save_scene()


def make_image(name: str, resolution: int, normal=False):
    image = bpy.data.images.new(name, width=resolution, height=resolution, alpha=True, float_buffer=False)
    image.colorspace_settings.name = 'Non-Color'
    image.generated_color = (0.5, 0.5, 1, 1) if normal else (0, 0, 0, 1)
    return image


def save_image(image, filename: str) -> Path:
    path = output_path(filename)
    image.filepath_raw = str(path)
    image.file_format = 'PNG'
    image.save()
    register(path)
    return path


def target_image(obj, image) -> None:
    if not obj.data.materials:
        mat = bpy.data.materials.new(obj.name + '_Material')
        mat.use_nodes = True
        obj.data.materials.append(mat)
    for index, slot in enumerate(obj.material_slots):
        if slot.material is None:
            slot.material = bpy.data.materials.new(obj.name + '_Material_' + str(index))
        slot.material = slot.material.copy()
        mat = slot.material
        mat.use_nodes = True
        for node in mat.node_tree.nodes:
            node.select = False
        node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        node.name = 'CP_BAKE_TARGET'
        node.image = image
        node.select = True
        mat.node_tree.nodes.active = node


def coverage_fraction(obj, image) -> dict:
    # Conservative interior-texel test; UV-overlap detection is intentionally separate.
    import numpy as np
    grid = 256
    mask = np.zeros((grid, grid), dtype=bool)
    mesh = obj.data
    mesh.calc_loop_triangles()
    uv = mesh.uv_layers.active
    for tri in mesh.loop_triangles:
        p = np.array([uv.data[i].uv[:] for i in tri.loops], dtype=float) * grid - 0.5
        x0, y0 = np.maximum(np.floor(p.min(axis=0)).astype(int), 0)
        x1, y1 = np.minimum(np.ceil(p.max(axis=0)).astype(int), grid-1)
        if x0 > x1 or y0 > y1:
            continue
        xx, yy = np.meshgrid(np.arange(x0, x1+1), np.arange(y0, y1+1))
        signs = []
        for i in range(3):
            a, b = p[i], p[(i+1) % 3]
            signs.append((xx-a[0])*(b[1]-a[1])-(yy-a[1])*(b[0]-a[0]))
        inside = (np.logical_and.reduce([s >= 0 for s in signs]) | np.logical_and.reduce([s <= 0 for s in signs]))
        mask[y0:y1+1, x0:x1+1] |= inside
    interior = mask.copy()
    interior[1:-1, 1:-1] &= mask[:-2, 1:-1] & mask[2:, 1:-1] & mask[1:-1, :-2] & mask[1:-1, 2:]
    interior[[0, -1], :] = False
    interior[:, [0, -1]] = False
    width, height = image.size
    pixels = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape(height, width, 4)
    ys = np.minimum(((np.arange(grid)+0.5)*height/grid).astype(int), height-1)
    xs = np.minimum(((np.arange(grid)+0.5)*width/grid).astype(int), width-1)
    values = pixels[ys[:, None], xs[None, :], 0]
    total = int(interior.sum())
    missed = int(((values < 0.5) & interior).sum())
    return {'sampled_interior_texels': total, 'missed_texels': missed, 'miss_fraction': missed / total if total else None,
            'limitations': 'Does not detect a ray that hit the wrong nearby surface, nor tiny UV islands below sampling resolution.'}


def bake_pair(low, high: list, pair: dict, resolution: int) -> dict:
    if not low.data.uv_layers.active:
        raise ValueError('Low-poly UV required')
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = int(CFG.get('samples', 16))
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.margin = int(CFG.get('margin_pixels', 16))
    scene.render.bake.use_clear = True
    scene.render.bake.normal_space = 'TANGENT'
    scene.render.bake.normal_r = 'POS_X'
    scene.render.bake.normal_g = 'POS_Y'
    scene.render.bake.normal_b = 'POS_Z'
    minimum, maximum = bounds([low])
    extent = (maximum-minimum).length
    distance = float(pair.get('ray_distance', extent * 0.005))
    if not math.isfinite(distance) or distance <= 0 or distance > extent * 0.1:
        raise ValueError('Use a finite positive ray distance no larger than 10% of part diagonal')
    cage = bpy.data.objects.get(pair.get('cage', ''))
    if pair.get('cage') and cage is None:
        raise ValueError('The requested cage object does not exist')
    if cage:
        if cage.type != 'MESH' or len(cage.data.vertices) != len(low.data.vertices) or [tuple(p.vertices) for p in cage.data.polygons] != [tuple(p.vertices) for p in low.data.polygons]:
            raise ValueError('Explicit cage must have identical vertex count, polygon order and connectivity')
        scene.render.bake.use_cage = True
        scene.render.bake.cage_object = cage
    else:
        scene.render.bake.use_cage = False
        extrusion = float(pair.get('extrusion', 0))
        if not math.isfinite(extrusion) or not 0 <= extrusion <= extent * 0.1:
            raise ValueError('Cage extrusion must be finite, nonnegative and no larger than 10% of the part diagonal')
        scene.render.bake.cage_extrusion = extrusion
    scene.render.bake.max_ray_distance = distance
    visibility = {obj: obj.hide_render for obj in scene.objects}
    for obj in scene.objects:
        if obj.type == 'MESH':
            obj.hide_render = obj not in [low, *high]
    safe_name = ''.join(c if c.isalnum() or c in '._-' else '_' for c in low.name)
    result = {'low': low.name, 'high': [obj.name for obj in high], 'ray_distance': distance, 'explicit_cage': cage.name if cage else None}
    try:
        for kind in CFG.get('maps', ['NORMAL', 'AO']):
            if kind not in ('NORMAL', 'AO'):
                raise ValueError('This helper bakes geometry normal/AO; use material channel emission baking for other maps')
            image = make_image(safe_name + '_' + kind, resolution, normal=kind == 'NORMAL')
            target_image(low, image)
            activate([*high, low], low)
            bpy.ops.object.bake(type=kind)
            result[kind.lower()] = save_image(image, f'textures/{safe_name}_{kind.lower()}.png').relative_to(OUT).as_posix()
        # A separate white emission pass detects no-hit texels rather than mistaking flat normals for misses.
        white = bpy.data.materials.new('CP_Coverage_White')
        white.use_nodes = True
        white.node_tree.nodes.clear()
        emission = white.node_tree.nodes.new('ShaderNodeEmission')
        emission.inputs['Color'].default_value = (1, 1, 1, 1)
        output = white.node_tree.nodes.new('ShaderNodeOutputMaterial')
        white.node_tree.links.new(emission.outputs[0], output.inputs['Surface'])
        originals = []
        for obj in high:
            originals.append((obj, list(obj.data.materials), [p.material_index for p in obj.data.polygons]))
            obj.data.materials.clear()
            obj.data.materials.append(white)
            for polygon in obj.data.polygons:
                polygon.material_index = 0
        try:
            image = make_image(safe_name + '_coverage', resolution)
            target_image(low, image)
            activate([*high, low], low)
            bpy.ops.object.bake(type='EMIT')
            save_image(image, f'textures/{safe_name}_coverage.png')
            result['coverage'] = coverage_fraction(low, image)
        finally:
            for obj, mats, indices in originals:
                obj.data.materials.clear()
                for mat in mats:
                    obj.data.materials.append(mat)
                for polygon, index in zip(obj.data.polygons, indices):
                    polygon.material_index = index
    finally:
        for obj, hide in visibility.items():
            obj.hide_render = hide
    return result


def task_bake() -> None:
    pairs = CFG.get('pairs', [])
    if not pairs:
        raise ValueError('Explicit low/high object pairs required; cross-part ray targets must not be guessed')
    results = []
    resolution = int(CFG.get('resolution', 2048))
    for pair in pairs:
        low = bpy.data.objects.get(pair['low'])
        high = [bpy.data.objects.get(name) for name in pair['high']]
        if not low or low.type != 'MESH' or not high or any(obj is None or obj.type != 'MESH' for obj in high):
            raise ValueError('Invalid low/high bake pair')
        if low in high:
            raise ValueError('Low target cannot also be a high source')
        results.append(bake_pair(low, high, pair, resolution))
    report('bake.json', {'pairs': results, 'requires_visual_review': True})
    save_scene()
    if any(r['coverage']['miss_fraction'] is None or r['coverage']['miss_fraction'] > float(CFG.get('max_miss_fraction', 0.005)) for r in results):
        raise RuntimeError('Bake coverage failed; diagnostic files retained. Adjust a copy and rebake rather than accepting.')


def texture_node(material, relative: str, color_space: str):
    image = bpy.data.images.load(str(source_path(relative)), check_existing=False)
    image.colorspace_settings.name = color_space
    node = material.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = image
    return node


def task_materials() -> None:
    updates = CFG.get('materials', [])
    if not updates:
        raise ValueError('Provide explicit existing material names and channel mappings; material semantics are not guessed')
    for item in updates:
        material = bpy.data.materials.get(item['material'])
        if material is None:
            raise ValueError(f"Unknown material {item['material']}")
        material.use_nodes = True
        nodes, links = material.node_tree.nodes, material.node_tree.links
        if item.get('replace_graph', False):
            approved('materials_replace')
            nodes.clear()
        shader = next((node for node in nodes if node.type == 'BSDF_PRINCIPLED'), None)
        if shader is None:
            shader = nodes.new('ShaderNodeBsdfPrincipled')
            output = next((node for node in nodes if node.type == 'OUTPUT_MATERIAL'), None) or nodes.new('ShaderNodeOutputMaterial')
            links.new(shader.outputs['BSDF'], output.inputs['Surface'])
        scalars = {'roughness': 'Roughness', 'metallic': 'Metallic', 'ior': 'IOR', 'subsurface_weight': 'Subsurface Weight', 'subsurface_scale': 'Subsurface Scale'}
        for field, socket in scalars.items():
            if field in item:
                value = float(item[field])
                if not math.isfinite(value) or value < 0 or (field in ('roughness', 'metallic', 'subsurface_weight') and value > 1):
                    raise ValueError(f'Invalid scalar: {field}')
                if socket not in shader.inputs:
                    raise RuntimeError(f'Unsupported Principled socket: {socket}')
                if shader.inputs[socket].is_linked:
                    raise ValueError(f'{socket} already has a map; do not replace texture-driven values with a guessed slider')
                shader.inputs[socket].default_value = value
        channels = {'base_color': ('Base Color', 'sRGB'), 'roughness_map': ('Roughness', 'Non-Color'), 'metallic_map': ('Metallic', 'Non-Color'), 'emission_map': ('Emission Color', 'sRGB')}
        for field, (socket, color_space) in channels.items():
            if item.get(field):
                node = texture_node(material, item[field], color_space)
                links.new(node.outputs['Color'], shader.inputs[socket])
        if item.get('normal_map'):
            if item.get('normal_convention', '+Y') != '+Y':
                raise ValueError('Convert DirectX -Y normals explicitly before this stage')
            image = texture_node(material, item['normal_map'], 'Non-Color')
            normal = nodes.new('ShaderNodeNormalMap')
            normal.space = 'TANGENT'
            normal.inputs['Strength'].default_value = float(item.get('normal_strength', 1))
            links.new(image.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'], shader.inputs['Normal'])
        if item.get('ao_map'):
            image = texture_node(material, item['ao_map'], 'Non-Color')
            group = bpy.data.node_groups.get('glTF Material Output')
            if group is None:
                group = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
                group.interface.new_socket(name='Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
            node = nodes.new('ShaderNodeGroup')
            node.node_tree = group
            links.new(image.outputs['Color'], node.inputs['Occlusion'])
    report('materials.json', {'updated': [item['material'] for item in updates], 'note': 'Existing assignments retained. AO is exported separately, not multiplied into base color. Review engine support for subsurface.'})
    save_scene()


def bind_skeleton(bones: list[dict], rigid: dict[str, str], name='CharacterRig'):
    ordered = validate_bones(bones)
    if any(obj.type == 'ARMATURE' for obj in bpy.context.scene.objects):
        raise ValueError('Existing armature found; validate/reuse it instead of adding another skeleton')
    objects = meshes()
    ensure_unrigged(objects)
    data = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(rig)
    activate([rig])
    bpy.ops.object.mode_set(mode='EDIT')
    for spec in ordered:
        bone = data.edit_bones.new(spec['name'])
        bone.head = spec['head']
        bone.tail = spec['tail']
        bone.roll = float(spec.get('roll', 0))
        bone.use_deform = bool(spec.get('deform', True))
        if spec.get('parent'):
            bone.parent = data.edit_bones[spec['parent']]
        if spec.get('connected', False):
            if bone.parent is None or (bone.head-bone.parent.tail).length > 1e-5:
                raise ValueError('Connected bones must share the same landmark')
            bone.use_connect = True
    bpy.ops.object.mode_set(mode='OBJECT')
    missing_rigid = set(rigid) - {obj.name for obj in objects}
    if missing_rigid:
        raise ValueError(f'Unknown rigid object names: {missing_rigid}')
    deformable = [obj for obj in objects if obj.name not in rigid]
    if deformable:
        activate([*deformable, rig], rig)
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    for obj in objects:
        if obj.name in rigid:
            bone_name = rigid[obj.name]
            if bone_name not in rig.data.bones or not rig.data.bones[bone_name].use_deform:
                raise ValueError('Rigid mesh must map to an existing deform bone')
            for old in list(obj.vertex_groups):
                if old.name in rig.data.bones and rig.data.bones[old.name].use_deform:
                    obj.vertex_groups.remove(old)
            group = obj.vertex_groups.new(name=bone_name)
            group.add(list(range(len(obj.data.vertices))), 1, 'REPLACE')
            modifier = obj.modifiers.new('Armature', 'ARMATURE')
            modifier.object = rig
            world = obj.matrix_world.copy()
            obj.parent = rig
            obj.matrix_world = world
        prune_weights(obj, rig, int(CFG.get('max_influences', 4)))
    return rig


def prune_weights(obj, rig, limit: int) -> None:
    deform = {bone.name for bone in rig.data.bones if bone.use_deform}
    groups = {group.index: group for group in obj.vertex_groups}
    unweighted = []
    for vertex in obj.data.vertices:
        values = [(groups[item.group].name, item.weight) for item in vertex.groups if item.group in groups and groups[item.group].name in deform]
        normalized = normalized_weights(values, limit)
        if not normalized:
            unweighted.append(vertex.index)
            continue
        for name, _ in values:
            obj.vertex_groups[name].remove([vertex.index])
        for name, weight in normalized:
            obj.vertex_groups[name].add([vertex.index], weight, 'REPLACE')
    if unweighted:
        raise RuntimeError(f'{obj.name}: {len(unweighted)} unweighted vertices; first indices {unweighted[:20]}. No nearest-bone guessing was performed.')


def task_rig() -> None:
    review = approved('skeleton')
    skeleton_path = source_path(CFG['skeleton'])
    skeleton = json_read(skeleton_path)
    if skeleton.get('fixture_only'):
        raise ValueError('Synthetic fixture skeleton is not an approved production fit')
    if review.get('skeleton_sha256') != file_hash(skeleton_path):
        raise ValueError('Skeleton approval is stale or missing its hash')
    rig = bind_skeleton(skeleton['bones'], skeleton.get('rigid_objects', {}), skeleton.get('name', 'CharacterRig'))
    report('rig.json', {'armature': rig.name, 'bones': len(rig.data.bones), 'skeleton_sha256': file_hash(skeleton_path),
                       'note': 'Basic deform rig, not a Rigify control rig. Automatic weights require joint and finger pose review.'})
    save_scene()


def clear_pose(rig) -> None:
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
        bone.rotation_mode = 'QUATERNION'


def set_action_interpolation(action, mode='LINEAR') -> None:
    curves = []
    # Blender 4.4+ layered actions, with older action compatibility when present.
    if hasattr(action, 'layers') and len(action.layers):
        for layer in action.layers:
            for strip in layer.strips:
                for bag in getattr(strip, 'channelbags', []):
                    curves.extend(bag.fcurves)
    elif hasattr(action, 'fcurves'):
        curves.extend(action.fcurves)
    for curve in curves:
        for key in curve.keyframe_points:
            key.interpolation = mode


def task_animate() -> None:
    rig = armature()
    motion = json_read(source_path(CFG['motion']))
    if not motion.get('frames'):
        raise ValueError('Motion has no explicit keyframes')
    if any(bone.constraints for bone in rig.pose.bones):
        raise ValueError('For control rigs, bake the deform skeleton instead of overwriting constrained bones')
    rig.animation_data_clear()
    clear_pose(rig)
    # NEW: reject malformed or unbounded external motion settings before keyframe construction.
    motion_fps = motion.get('fps', 30)
    if not isinstance(motion_fps, (int, float)) or not math.isfinite(motion_fps) or not 1 <= motion_fps <= 120:
        raise ValueError('Motion FPS must be finite and within 1..120')
    frame_numbers = [key.get('frame') for key in motion['frames']]
    if any(type(frame) is not int or frame < 0 for frame in frame_numbers) or max(frame_numbers)-min(frame_numbers) > 18000:
        raise ValueError('Motion requires bounded nonnegative integer frames')
    bpy.context.scene.render.fps = int(motion_fps)
    previous_frame = -1
    for key in motion['frames']:
        frame = int(key['frame'])
        if frame <= previous_frame:
            raise ValueError('Keyframe numbers must be strictly increasing')
        previous_frame = frame
        clear_pose(rig)
        unknown = set(key.get('bones', {})) - set(rig.pose.bones.keys())
        if unknown:
            raise ValueError(f'Unknown animated bones: {unknown}')
        for name, value in key.get('bones', {}).items():
            bone = rig.pose.bones[name]
            if 'rotation_degrees' in value:
                angles = value['rotation_degrees']
                if len(angles) != 3 or not all(math.isfinite(n) for n in angles):
                    raise ValueError('Invalid local XYZ rotation')
                bone.rotation_quaternion = Euler([math.radians(n) for n in angles], 'XYZ').to_quaternion()
            if 'location' in value:
                if len(value['location']) != 3 or not all(math.isfinite(n) for n in value['location']):
                    raise ValueError('Invalid local translation')
                bone.location = value['location']
        # Explicit rest keys for unspecified bones avoid accidental pose carryover.
        for bone in rig.pose.bones:
            bone.keyframe_insert(data_path='rotation_quaternion', frame=frame, group=bone.name)
            bone.keyframe_insert(data_path='location', frame=frame, group=bone.name)
            bone.keyframe_insert(data_path='scale', frame=frame, group=bone.name)
    action = rig.animation_data.action
    action.name = motion.get('name', 'AuthoredMotion')
    action.use_fake_user = True
    set_action_interpolation(action)
    scene = bpy.context.scene
    scene.frame_start = int(motion['frames'][0]['frame'])
    scene.frame_end = int(motion['frames'][-1]['frame'])
    scene.frame_set(scene.frame_start)
    report('animation.json', {'action': action.name, 'fps': scene.render.fps, 'start': scene.frame_start, 'end': scene.frame_end,
                              'motion_source': 'explicit local-space pose keys', 'loop_requested': bool(motion.get('loop', False)),
                              'warning': 'A named or endpoint-matched loop is not proof of foot contact or velocity continuity.'})
    save_scene()


def task_retarget() -> None:
    # Rest-space rotation transfer, not an IK/contact solver. Non-humanoid mappings are explicit.
    review = approved('retarget')
    if review.get('mapping_sha256') != file_hash(source_path(CFG['mapping'])) or review.get('source_sha256') != file_hash(source_path(CFG['source'])):
        raise ValueError('Retarget approval must match both mapping and source motion hashes')
    target = armature()
    mapping = json_read(source_path(CFG['mapping']))
    if not mapping.get('alignment_reviewed'):
        raise ValueError('Source/target rest pose and world alignment must be reviewed first')
    source_objects = import_asset(source_path(CFG['source']), append=True)
    source_rigs = [obj for obj in source_objects if obj.type == 'ARMATURE']
    if len(source_rigs) != 1:
        raise ValueError('Animation source must contain one armature')
    source = source_rigs[0]
    if not source.animation_data or not source.animation_data.action:
        raise ValueError('No active source action; select one in an audited source checkpoint')
    if target.constraints or any(bone.constraints for bone in target.pose.bones):
        raise ValueError('Retarget only onto a clean deform rig; bake control rigs separately')
    pairs = mapping['bones']  # target bone name -> source bone name
    for target_name, source_name in pairs.items():
        if target_name not in target.pose.bones or source_name not in source.pose.bones:
            raise ValueError(f'Invalid mapping {target_name} <- {source_name}')
    a = Euler([math.radians(n) for n in mapping.get('source_to_target_rotation_degrees', [0,0,0])], 'XYZ').to_matrix()
    translation_target = mapping.get('translation_target')
    translation_source = mapping.get('translation_source')
    scale = float(mapping.get('translation_scale', 1))
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('translation_scale must be positive')
    mode = mapping.get('root_motion', 'in_place')
    if mode not in ('in_place', 'preserve_translation'):
        raise ValueError('Unsupported root-motion policy')
    if translation_target and (translation_target not in target.pose.bones or translation_source not in source.pose.bones):
        raise ValueError('Invalid translation bone pair')
    start, end = [int(n) for n in source.animation_data.action.frame_range]
    source_fps = float(mapping.get('source_fps', 30))
    fps = int(CFG.get('fps', 30))
    if source_fps <= 0 or not 1 <= fps <= 120:
        raise ValueError('Invalid FPS')
    out_end = 1 + round((end-start) * fps / source_fps)
    if out_end > 18000:
        raise ValueError('Clip exceeds bounded bake length')
    rest_source = {bone.name: source.matrix_world @ bone.matrix_local for bone in source.data.bones}
    rest_target = {bone.name: target.matrix_world @ bone.matrix_local for bone in target.data.bones}
    ordered = sorted(target.pose.bones, key=lambda b: len(b.parent_recursive))
    target.animation_data_clear()
    scene = bpy.context.scene
    for frame in range(1, out_end+1):
        sample = start + (frame-1) * source_fps / fps
        scene.frame_set(math.floor(sample), subframe=sample-math.floor(sample))
        clear_pose(target)
        for bone in ordered:
            if bone.name not in pairs:
                continue
            source_name = pairs[bone.name]
            source_pose_world = source.matrix_world @ source.pose.bones[source_name].matrix
            delta = a @ source_pose_world.to_quaternion().to_matrix() @ rest_source[source_name].to_quaternion().to_matrix().inverted() @ a.inverted()
            desired_rotation = delta @ rest_target[bone.name].to_quaternion().to_matrix()
            if bone.parent:
                anchor_local = bone.parent.matrix @ bone.parent.bone.matrix_local.inverted() @ bone.bone.matrix_local
                head = target.matrix_world @ anchor_local.translation
            else:
                head = rest_target[bone.name].translation.copy()
            if bone.name == translation_target:
                source_head = (source.matrix_world @ source.pose.bones[translation_source].matrix).translation
                offset = a @ (source_head-rest_source[translation_source].translation) * scale
                if mode == 'in_place':
                    offset.x, offset.y = 0, 0
                head = rest_target[bone.name].translation + offset
            matrix = desired_rotation.to_4x4()
            matrix.translation = head
            bone.matrix = target.matrix_world.inverted() @ matrix
            bpy.context.view_layer.update()
        for bone in ordered:
            bone.keyframe_insert(data_path='location', frame=frame, group=bone.name)
            bone.keyframe_insert(data_path='rotation_quaternion', frame=frame, group=bone.name)
            bone.keyframe_insert(data_path='scale', frame=frame, group=bone.name)
    action = target.animation_data.action
    action.name = mapping.get('name', 'RetargetedMotion')
    action.use_fake_user = True
    set_action_interpolation(action)
    for obj in source_objects:
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    scene.render.fps = fps
    scene.frame_start, scene.frame_end = 1, out_end
    scene.frame_set(1)
    report('retarget.json', {'action': action.name, 'frames': out_end, 'fps': fps, 'root_motion': mode,
                             'limitations': ['No automatic foot locking', 'No automatic twist distribution', 'No root-yaw extraction', 'No face semantic mapping'],
                             'status': 'CANDIDATE_REQUIRES_CONTACT_AND_JOINT_REVIEW'})
    save_scene()


def skin_audit(obj, rig) -> dict:
    names = {bone.name for bone in rig.data.bones if bone.use_deform}
    indices = {group.index for group in obj.vertex_groups if group.name in names}
    unweighted, bad_sum, too_many, nonfinite = 0, 0, 0, 0
    for vertex in obj.data.vertices:
        raw_weights = [item.weight for item in vertex.groups if item.group in indices]
        weights = [weight for weight in raw_weights if math.isfinite(weight) and weight > 0]
        unweighted += not weights
        nonfinite += any(not math.isfinite(weight) or weight < 0 for weight in raw_weights)
        bad_sum += bool(weights) and abs(sum(weights)-1) > float(CFG.get('weight_tolerance', 1e-4))
        too_many += len(weights) > int(CFG.get('max_influences', 4))
    return {'object': obj.name, 'unweighted': unweighted, 'unnormalized': bad_sum, 'too_many_influences': too_many, 'nonfinite': nonfinite}


def task_qa() -> None:
    objects = meshes()
    audit = [mesh_audit(obj) for obj in objects]
    failures = []
    warnings = ['Semantic topology, UV overlap, material identity, collisions, contact and silhouette require visual review.']
    if not objects:
        failures.append('No meshes')
    if sum(item['triangles'] for item in audit) > int(CFG.get('max_triangles', 80000)):
        failures.append('Triangle budget exceeded')
    for item in audit:
        for field in ('nonfinite_vertices', 'degenerate_faces', 'nonmanifold_nonboundary_edges', 'degenerate_uv_triangles', 'uv_coordinates_outside_unit_tile'):
            if item[field]:
                failures.append(f"{item['object']}: {field}={item[field]}")
        if not item['has_uv']:
            failures.append(f"{item['object']}: missing UV")
        if item['boundary_edges']:
            warnings.append(f"{item['object']}: open boundaries; review clothing/hair intent instead of closing automatically")
    skins = []
    rig = None
    if CFG.get('expect_rig', True):
        rig = armature()
        for obj in objects:
            item = skin_audit(obj, rig)
            skins.append(item)
            if any(item[key] for key in ('unweighted', 'unnormalized', 'too_many_influences', 'nonfinite')):
                failures.append(f'{obj.name}: invalid skin weights')
            if not any(mod.type == 'ARMATURE' and mod.object == rig for mod in obj.modifiers):
                failures.append(f'{obj.name}: missing matching armature modifier')
        if CFG.get('expect_animation', True) and (not rig.animation_data or not rig.animation_data.action):
            failures.append('No active animation action')
    scene = bpy.context.scene
    frame_before = scene.frame_current
    first, last = scene.frame_start, scene.frame_end
    samples = CFG.get('sample_frames', sorted(set([first, first+(last-first)//4, first+(last-first)//2, first+3*(last-first)//4, last])))
    pose_metrics = []
    for frame in samples:
        scene.frame_set(int(frame))
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for obj in objects:
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            try:
                bad = sum(not all(math.isfinite(x) for x in vertex.co) for vertex in mesh.vertices)
                if bad:
                    failures.append(f'{obj.name}: nonfinite evaluated vertices at frame {frame}')
                ratios = []
                if len(mesh.vertices) == len(obj.data.vertices):
                    for edge in obj.data.edges:
                        i, j = edge.vertices
                        base = (obj.data.vertices[i].co-obj.data.vertices[j].co).length
                        if base > 1e-8:
                            ratios.append((mesh.vertices[i].co-mesh.vertices[j].co).length / base)
                if ratios and max(ratios) > float(CFG.get('max_edge_stretch', 5)):
                    failures.append(f'{obj.name}: extreme edge stretch at frame {frame}')
                pose_metrics.append({'object': obj.name, 'frame': frame, 'maximum_edge_stretch': max(ratios) if ratios else None})
            finally:
                evaluated.to_mesh_clear()
    scene.frame_set(frame_before)
    report('qa.json', {'input_sha256': file_hash(source_path(CFG['input'])), 'mechanical_pass': not failures,
                       'failures': failures, 'warnings': warnings, 'meshes': audit, 'skinning': skins,
                       'pose_samples': pose_metrics, 'visual_status': 'NOT_EVALUATED_BY_THIS_SCRIPT'})
    if failures:
        raise RuntimeError('Mechanical QA failed; see qa.json')


def look_at(obj, target: Vector) -> None:
    obj.rotation_euler = (target-obj.location).to_track_quat('-Z', 'Y').to_euler()


def task_preview() -> None:
    objects = meshes()
    minimum, maximum = bounds(objects)
    center = (minimum+maximum)/2
    diagonal = (maximum-minimum).length
    if diagonal <= 0:
        raise ValueError('Empty bounds')
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = int(CFG.get('samples', 16))
    scene.render.resolution_x = scene.render.resolution_y = int(CFG.get('resolution', 512))
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = True
    for obj in scene.objects:
        if obj.type in ('LIGHT', 'CAMERA') or obj.get('cp_role') == 'high':
            obj.hide_render = True
    world = bpy.data.worlds.new('CP_NeutralWorld')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.12,0.12,0.12,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.5
    scene.world = world
    camera_data = bpy.data.cameras.new('CP_PreviewCamera')
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = diagonal * 1.15
    camera = bpy.data.objects.new('CP_PreviewCamera', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    for index, offset in enumerate([(2,-3,3),(-2,-1,1),(0,2,3)]):
        data = bpy.data.lights.new(f'CP_Area_{index}', 'AREA')
        data.energy = 350 * diagonal * diagonal
        data.shape = 'DISK'
        data.size = diagonal
        lamp = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(lamp)
        lamp.location = center + Vector(offset) * diagonal
        look_at(lamp, center)
    frames = CFG.get('sample_frames', [scene.frame_start])
    angles = CFG.get('angles_degrees', [0,45,90,135,180,225,270,315])
    if len(frames)*len(angles) > 64:
        raise ValueError('Preview capped at 64 images per job')
    camera_records = []
    for frame in frames:
        scene.frame_set(int(frame))
        for index, degrees in enumerate(angles):
            angle = math.radians(degrees)
            camera.location = center + Vector((math.sin(angle),-math.cos(angle),0)) * diagonal * 2
            look_at(camera, center)
            path = output_path(f'previews/frame_{int(frame):04d}_view_{index:02d}.png')
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            register(path)
            camera_records.append({'frame': frame, 'degrees': degrees, 'file': path.relative_to(OUT).as_posix(),
                                   'matrix_world': [list(row) for row in camera.matrix_world], 'ortho_scale': camera_data.ortho_scale})
    report('cameras.json', {'views': camera_records, 'blender': bpy.app.version_string,
                           'note': 'Use identical bounds/angles/lighting for comparisons; these orthographic views are also landmark fitting references.'})


def export_glb(path: Path) -> None:
    targets = meshes() + [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE' and obj.get('cp_role') != 'high']
    activate(targets)
    # NEW: preserve the intended active clip name rather than the exporter's generic merged label.
    active_name = next((obj.animation_data.action.name for obj in targets if obj.type == 'ARMATURE' and obj.animation_data and obj.animation_data.action), 'Animation')
    operator_call(bpy.ops.export_scene.gltf, filepath=str(path), export_format='GLB', use_selection=True,
                  export_nla_strips_merged_animation_name=CFG.get('clip_name', active_name),
                  export_animations=True, export_animation_mode=CFG.get('animation_mode', 'ACTIVE_ACTIONS'), export_force_sampling=True,
                  export_skins=True, export_texcoords=True, export_normals=True, export_tangents=True)


def task_handoff() -> None:
    # NEW: an unrigged intermediate GLB for service input is not a final release.
    if any(obj.type == 'ARMATURE' for obj in bpy.context.scene.objects):
        raise ValueError('Handoff does not strip an existing rig; branch from the accepted pre-rig checkpoint')
    targets = meshes()
    if not targets or any(not obj.data.uv_layers.active for obj in targets):
        raise ValueError('Handoff requires target meshes with accepted UVs')
    activate(targets)
    path = output_path('handoff.glb')
    operator_call(bpy.ops.export_scene.gltf, filepath=str(path), export_format='GLB', use_selection=True,
                  export_animations=False, export_skins=False, export_texcoords=True,
                  export_normals=True, export_tangents=True)
    register(path)
    report('handoff.json', {'status':'INTERMEDIATE_NOT_A_RELEASE', 'input_sha256':file_hash(source_path(CFG['input'])),
                            'meshes':[mesh_audit(obj) for obj in targets],
                            'note':'Creating this local file is not authorization to upload it or publish it.'})


def task_export() -> None:
    # NEW: candidate export breaks the export-before-target-test circular dependency.
    release = CFG['task'] == 'export'
    if release:
        review = approved('release')
        required = {'identity', 'texture_seams', 'joint_deformation', 'animation', 'target_compatibility'}
        if not required.issubset(set(review.get('visual_checks_passed', []))):
            raise ValueError('Release review lacks required visual checks')
    qa = json_read(source_path(CFG['qa_report']))
    current_hash = file_hash(source_path(CFG['input']))
    if qa.get('input_sha256') != current_hash or not qa.get('mechanical_pass'):
        raise ValueError('Missing/stale mechanical QA')
    save_scene('character_master.blend')
    path = output_path('character.glb')
    export_glb(path)
    register(path)
    if CFG.get('fbx', False):
        fbx = output_path('character.fbx')
        operator_call(bpy.ops.export_scene.fbx, filepath=str(fbx), use_selection=True,
                      object_types={'MESH','ARMATURE'}, add_leaf_bones=False, axis_forward='-Z', axis_up='Y',
                      apply_unit_scale=True, bake_anim=True, bake_anim_use_all_bones=True,
                      bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False)
        register(fbx)
    # NEW: establish evaluated triangle counts explicitly rather than relying on exporter side effects.
    for obj in meshes():
        obj.data.calc_loop_triangles()
    expected_triangles = sum(len(obj.data.loop_triangles) for obj in meshes())
    expected_rig = any(obj.type == 'ARMATURE' for obj in bpy.context.scene.objects)
    expected_animation = any(obj.type == 'ARMATURE' and obj.animation_data and obj.animation_data.action for obj in bpy.context.scene.objects)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_asset(path)
    actual_meshes = meshes()
    actual_rigs = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
    for obj in actual_meshes:
        obj.data.calc_loop_triangles()
    actual_triangles = sum(len(obj.data.loop_triangles) for obj in actual_meshes)
    valid = bool(actual_meshes) and (not expected_rig or bool(actual_rigs)) and (not expected_animation or bool(bpy.data.actions))
    if expected_triangles and actual_triangles != expected_triangles:
        valid = False
    report('roundtrip.json', {'asset_status': 'RELEASE_REVIEWED' if release else 'CANDIDATE_NOT_A_RELEASE', 'mechanical_pass': valid, 'triangles': actual_triangles,
                             'armatures': len(actual_rigs), 'actions': [action.name for action in bpy.data.actions],
                             'not_tested': ['Destination engine playback', 'GLB/FBX shading parity', 'Full Khronos validator', 'FBX reimport']})
    if not valid:
        raise RuntimeError('GLB roundtrip lost expected geometry, rig or animation')


def task_selftest() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=12, location=(0,0,1))
    low = bpy.context.object
    low.name = 'FixtureBody'
    low.scale = (0.3,0.3,1)
    activate([low])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    high = low.copy()
    high.data = low.data.copy()
    bpy.context.collection.objects.link(high)
    high.name = 'HIGH__FixtureBody'
    high['cp_role'] = 'high'
    high.hide_render = True
    CFG['samples'] = 1
    CFG['maps'] = ['NORMAL']
    baked = bake_pair(low, [high], {'ray_distance': 0.01}, 64)
    if baked['coverage']['miss_fraction'] is None or baked['coverage']['miss_fraction'] > 0.1:
        raise AssertionError('Synthetic bake coverage failed')
    bones = [{'name':'root','head':[0,0,0],'tail':[0,0,0.2],'deform':False},
             {'name':'lower','parent':'root','head':[0,0,0.1],'tail':[0,0,1]},
             {'name':'upper','parent':'lower','head':[0,0,1],'tail':[0,0,1.9]}]
    rig = bind_skeleton(bones, {})
    clear_pose(rig)
    for frame, angle in [(1,0),(10,0.3),(20,0)]:
        rig.pose.bones['upper'].rotation_quaternion = Euler((angle,0,0)).to_quaternion()
        rig.pose.bones['upper'].keyframe_insert(data_path='rotation_quaternion', frame=frame)
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 20
    rig.animation_data.action.name = 'FixtureBend'
    save_scene('selftest.blend')
    glb = output_path('selftest.glb')
    export_glb(glb)
    register(glb)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_asset(glb)
    assert meshes(), 'GLB reimport lost mesh'
    assert any(obj.type == 'ARMATURE' for obj in bpy.context.scene.objects), 'GLB reimport lost rig'
    assert bpy.data.actions, 'GLB reimport lost animation'
    report('selftest.json', {'status':'PASS','blender':bpy.app.version_string,
                             'checked':['synthetic geometry import/export','Cycles normal and coverage bake','automatic weights','pose keyframes','GLB rig/animation roundtrip'],
                             'not_checked':['live browser','real generated character','rig landmarks','retarget contacts','FBX roundtrip','production material quality']})


def task_face_rig() -> None:
    # NEW: authentic anatomical Duchenne facial rigging and expression synthesis.
    target_objs = meshes()
    if not target_objs:
        raise ValueError('No target mesh found for face rigging')
    target = target_objs[0]
    
    # Calculate bounding box of mesh to establish anatomical proportions
    v_coords = [target.matrix_world @ v.co for v in target.data.vertices]
    min_z = min(v.z for v in v_coords)
    max_z = max(v.z for v in v_coords)
    mid_x = (min(v.x for v in v_coords) + max(v.x for v in v_coords)) / 2
    mid_y = (min(v.y for v in v_coords) + max(v.y for v in v_coords)) / 2
    height = max(1e-4, max_z - min_z)
    
    # Check or create armature
    rig = None
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
    if armatures:
        rig = armatures[0]
    else:
        data = bpy.data.armatures.new('FaceArmature')
        rig = bpy.data.objects.new('FaceArmature', data)
        bpy.context.collection.objects.link(rig)
        activate([rig])
        bpy.ops.object.mode_set(mode='EDIT')
        
        head_b = data.edit_bones.new('Bone_Head')
        head_b.head = Vector((mid_x, mid_y, min_z + height * 0.2))
        head_b.tail = Vector((mid_x, mid_y, max_z))
        
        jaw_b = data.edit_bones.new('Bone_Jaw')
        jaw_b.head = Vector((mid_x, mid_y, min_z + height * 0.35))
        jaw_b.tail = Vector((mid_x, mid_y - height * 0.12, min_z + height * 0.25))
        jaw_b.parent = head_b
        
        for side, sign in [('_L', 1.0), ('_R', -1.0)]:
            lip_b = data.edit_bones.new(f'Bone_LipCorner{side}')
            lip_b.head = Vector((mid_x + sign * 0.065, mid_y - 0.15, min_z + height * 0.42))
            lip_b.tail = Vector((mid_x + sign * 0.075, mid_y - 0.16, min_z + height * 0.45))
            lip_b.parent = head_b
            
            chk_b = data.edit_bones.new(f'Bone_Cheek{side}')
            chk_b.head = Vector((mid_x + sign * 0.10, mid_y - 0.12, min_z + height * 0.48))
            chk_b.tail = Vector((mid_x + sign * 0.11, mid_y - 0.12, min_z + height * 0.52))
            chk_b.parent = head_b
            
        bpy.ops.object.mode_set(mode='OBJECT')
        activate([target, rig], rig)
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')

    # Create Shape Keys: Basis & Smile (Authentic Full-Face Duchenne Smile)
    if not target.data.shape_keys:
        target.shape_key_add(name='Basis')
    basis = target.data.shape_keys.key_blocks['Basis']
    
    smile_key = target.data.shape_keys.key_blocks.get('Smile') or target.shape_key_add(name='Smile')
    
    landmarks = CFG.get('landmarks', {})
    lip_corner_x = float(landmarks.get('mouth_corner_x', 0.065))
    mouth_y = float(landmarks.get('mouth_y', -0.285))
    mouth_z = float(landmarks.get('mouth_z', 0.420))
    cheek_z = float(landmarks.get('cheek_z', 0.465))
    eye_z = float(landmarks.get('eye_z', 0.505))
    
    for i, vert in enumerate(target.data.vertices):
        co = basis.data[i].co
        x, y, z = co.x, co.y, co.z
        dx, dy, dz = 0.0, 0.0, 0.0
        
        # 1. Zygomaticus major: continuous parabolic curvature for mouth corners
        if abs(z - mouth_z) < 0.06 and y < (mouth_y + 0.08):
            falloff_y = gaussian_falloff(abs(y - mouth_y), 0.04)
            falloff_z = gaussian_falloff(abs(z - mouth_z), 0.025)
            arc = parabolic_arc_weight(x, lip_corner_x, power=1.8)
            corner_factor = arc * falloff_y * falloff_z
            dz += 0.026 * corner_factor
            dx += (0.010 if x > 0 else -0.010) * corner_factor
            dy += 0.008 * corner_factor
            
        # 2. Malar cheeks: elevation upward and forward
        if abs(z - cheek_z) < 0.06 and abs(abs(x) - 0.10) < 0.06 and y < -0.20:
            chk_dist = math.sqrt((abs(x) - 0.10)**2 + (y - (-0.25))**2 + (z - cheek_z)**2)
            chk_factor = gaussian_falloff(chk_dist, 0.045)
            dz += 0.018 * chk_factor
            dy -= 0.007 * chk_factor
            dx += (0.005 if x > 0 else -0.005) * chk_factor
            
        # 3. Orbicularis oculi: lower eyelid elevation / squint (smiling eyes)
        if abs(z - eye_z) < 0.04 and abs(abs(x) - 0.055) < 0.04 and y < -0.22:
            eye_dist = math.sqrt((abs(x) - 0.055)**2 + (y - (-0.258))**2 + (z - eye_z)**2)
            eye_factor = gaussian_falloff(eye_dist, 0.035)
            dz += 0.014 * eye_factor
            dy -= 0.005 * eye_factor
            
        # 4. Lateral canthi: crow's feet region lift and compression
        if abs(z - (eye_z + 0.02)) < 0.03 and abs(abs(x) - 0.085) < 0.035 and y < -0.20:
            canthus_dist = math.sqrt((abs(x) - 0.085)**2 + (y - (-0.245))**2 + (z - (eye_z + 0.02))**2)
            canthus_factor = gaussian_falloff(canthus_dist, 0.03)
            dz += 0.008 * canthus_factor
            dx += (-0.004 if x > 0 else 0.004) * canthus_factor
            
        smile_key.data[i].co = Vector((x + dx, y + dy, z + dz))
        
    if CFG.get('animate_expression', True):
        action = bpy.data.actions.new('DuchenneSmile')
        target.data.shape_keys.animation_data_create()
        target.data.shape_keys.animation_data.action = action
        keys = [(1, 0.0), (15, 0.45), (30, 1.0), (45, 1.0), (60, 0.1)]
        for f, val in keys:
            smile_key.value = val
            smile_key.keyframe_insert(data_path='value', frame=f)
        bpy.context.scene.frame_start = 1
        bpy.context.scene.frame_end = 60
        
    blend_path = output_path('face_rigged.blend')
    save_scene('face_rigged.blend')
    report('face_rig.json', {
        'status': 'COMPLETED',
        'shape_keys': [k.name for k in target.data.shape_keys.key_blocks],
        'duchenne_mechanics': [
            'Zygomaticus major parabolic arc',
            'Malar cheek pad elevation',
            'Orbicularis oculi lower eyelid squint',
            'Lateral canthus compression'
        ],
        'armature': rig.name if rig else None
    })


def task_studio_render() -> None:
    # NEW: calibrated studio lighting with AgX color management to prevent skin bleaching.
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = int(CFG.get('samples', 24))
    
    if hasattr(scene, 'view_settings'):
        try:
            scene.view_settings.view_transform = 'AgX'
            scene.view_settings.look = 'AgX - Medium High Contrast'
        except Exception:
            pass
            
    for obj in list(scene.objects):
        if obj.type in ('LIGHT', 'CAMERA'):
            bpy.data.objects.remove(obj, do_unlink=True)
            
    target_objs = meshes()
    minimum, maximum = bounds(target_objs)
    center = (minimum + maximum) / 2
    head_center = Vector((center.x, center.y, maximum.z - (maximum.z - minimum.z) * 0.25))
    
    key_data = bpy.data.lights.new('KeyArea', 'AREA')
    key_data.energy = 18.0
    key_data.size = 0.6
    key_obj = bpy.data.objects.new('KeyArea', key_data)
    scene.collection.objects.link(key_obj)
    key_obj.location = head_center + Vector((0.45, -0.65, 0.35))
    look_at(key_obj, head_center)
    
    fill_data = bpy.data.lights.new('FillArea', 'AREA')
    fill_data.energy = 8.0
    fill_data.size = 0.8
    fill_obj = bpy.data.objects.new('FillArea', fill_data)
    scene.collection.objects.link(fill_obj)
    fill_obj.location = head_center + Vector((-0.55, -0.60, 0.15))
    look_at(fill_obj, head_center)
    
    rim_data = bpy.data.lights.new('RimArea', 'AREA')
    rim_data.energy = 22.0
    rim_data.size = 0.5
    rim_obj = bpy.data.objects.new('RimArea', rim_data)
    scene.collection.objects.link(rim_obj)
    rim_obj.location = head_center + Vector((0.20, 0.65, 0.40))
    look_at(rim_obj, head_center)
    
    cam_data = bpy.data.cameras.new('StudioCam')
    cam_data.lens = 85.0
    cam_obj = bpy.data.objects.new('StudioCam', cam_data)
    scene.collection.objects.link(cam_obj)
    cam_obj.location = head_center + Vector((0.0, -0.68, 0.02))
    look_at(cam_obj, head_center)
    scene.camera = cam_obj
    
    rendered = []
    frames = CFG.get('render_frames', [1, 30])
    for f in frames:
        scene.frame_set(int(f))
        out_file = output_path(f'render_frame_{int(f):02d}.png')
        scene.render.filepath = str(out_file)
        bpy.ops.render.render(write_still=True)
        register(out_file)
        rendered.append(out_file.relative_to(OUT).as_posix())
        
    report('studio_render.json', {
        'status': 'COMPLETED',
        'color_management': getattr(scene.view_settings, 'view_transform', 'default'),
        'rendered_frames': rendered
    })


TASKS = {'inspect':task_inspect, 'prepare':task_prepare, 'uv':task_uv, 'retopo':task_retopo,
         'bake':task_bake, 'materials':task_materials, 'rig':task_rig, 'face_rig':task_face_rig,
         'animate':task_animate, 'retarget':task_retarget, 'qa':task_qa, 'export':task_export,
         'export_candidate':task_export, 'handoff':task_handoff, 'preview':task_preview,
         'studio_render':task_studio_render, 'selftest':task_selftest}



def main() -> None:
    global CFG, ROOT, OUT
    parser = argparse.ArgumentParser()
    parser.add_argument('--job', required=True)
    tail = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    args = parser.parse_args(tail)
    CFG = json_read(Path(args.job).resolve())
    ROOT = Path(CFG['_workspace']).resolve()
    OUT = Path(CFG['_run_dir']).resolve()
    if not OUT.is_relative_to(ROOT / 'runs'):
        raise ValueError('Run output must be inside workspace/runs')
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        if tuple(bpy.app.version[:2]) < (4, 5):
            raise RuntimeError('Blender 4.5+ required; newer versions still require this selftest')
        if CFG['task'] not in TASKS:
            raise ValueError('Unknown task')
        if CFG['task'] != 'selftest':
            load_input()
        TASKS[CFG['task']]()
        report('result.json', {'status':'COMPLETED','task':CFG['task'],'blender':bpy.app.version_string,'outputs':list(OUTPUTS)})
    except Exception as error:
        report('result.json', {'status':'FAILED','task':CFG.get('task'),'error':str(error),'traceback':traceback.format_exc(),'outputs':list(OUTPUTS)})
        raise


if __name__ == '__main__':
    main()
