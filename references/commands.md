# Executable helpers and job contracts

Paths inside a job are relative to the **asset workspace**, not the skill directory. Use forward slashes in JSON on Windows. `input` and other files must exist. The coordinator creates immutable `runs/<id>/` directories and prints their paths; use the real previous output path in the next job, not a literal invented run ID.

The examples below refer to explicitly named local inputs such as `inputs/accepted.blend`. The agent must first copy/select the actual approved checkpoint under that name or replace the field with the actual relative run path. These are complete job formats, not supplied character assets. Never overwrite a previously accepted input version.

## Windows bootstrap

```powershell
# NEW: paths for a repo-scoped Codex installation; use .claude for the Claude copy.
$Skill = "C:\Projects\CharacterStudio\.agents\skills\character-pipeline"
$Work = "C:\Projects\CharacterStudio\work\character-01"
$Blender = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"

# NEW: initialization is intentionally non-overwriting; omit it for an existing workspace.
node "$Skill\scripts\pipeline.mjs" init --project "$Work"
node "$Skill\scripts\pipeline.mjs" doctor --project "$Work" --blender "$Blender"
node --test "$Skill\tests\core.test.mjs"
py -3 -B -m unittest discover -s "$Skill\tests" -p "test_*.py" -v

# NEW: the Blender integration selftest must pass on the actual installed build.
Copy-Item "$Skill\assets\selftest.job.json" "$Work\jobs\selftest.json"
node "$Skill\scripts\pipeline.mjs" blender --project "$Work" --blender "$Blender" --job "jobs/selftest.json" --timeout 15
node "$Skill\scripts\pipeline.mjs" status --project "$Work"
```

Locate the user's actual Blender installation; the path above is a common example, not an installation guarantee. A newer Blender folder must pass the same selftest. The selftest performs synthetic normal/coverage baking, basic auto-binding, a small action and GLB rig/animation roundtrip; it does not validate real character quality.

## Running jobs

```powershell
# NEW: execute a complete JSON job already created in the asset workspace.
node "$Skill\scripts\pipeline.mjs" blender --project "$Work" --blender "$Blender" --job "jobs/inspect.json" --timeout 30
```

The exact subprocess shape is:

```text
blender --background --factory-startup --disable-autoexec --python-exit-code 23 --python <absolute-skill-path>/scripts/blender_pipeline.py -- --job <absolute-workspace-path>/runs/<actual-run-id>/request.json
```

Use the coordinator rather than fabricating this request. It adds `_workspace`, `_run_dir` and `_signature`. Input jobs must not supply their own execution roots. The script checks output confinement; the coordinator owns the run folder. When diagnosing a failure, read the run's `blender.log` and `result.json`. `COMPLETED` is a helper result, not asset release acceptance.

## Task matrix

| Task | Required inputs | Main result |
|---|---|---|
| `inspect` | input | audit.json, no scene mutation |
| `prepare` | input, geometry approval; optional high source | normalized scene.blend and before/after report |
| `uv` | input; approval for rebuilding | scene.blend and basic UV report |
| `retopo` | input, one selected object, retopology approval | candidate scene.blend; downstream data invalidated |
| `bake` | input, explicit low/high object pairs | normal/AO/coverage textures, report and scene.blend |
| `materials` | input, named material map/settings | scene.blend and channel mapping report |
| `handoff` | unrigged input with UVs | intermediate handoff.glb for an authorized service upload |
| `rig` | input, fitted skeleton, matching approval | basic deform-rig scene.blend |
| `face_rig` | input head mesh; optional landmarks/expression | face_rigged.blend with Duchenne shape keys & 60-frame animation |
| `animate` | rigged input, explicit motion JSON | active-action scene.blend |
| `retarget` | target input, source motion, mapping, approval | candidate active-action scene.blend |
| `preview` | input | PNGs and calibrated cameras.json |
| `studio_render` | input, calibrated 3-point area lighting, AgX | unbleached rendered PNG frames and studio_render.json |
| `qa` | exact candidate input | qa.json; no scene output |
| `export_candidate` | input and matching mechanical QA | candidate GLB/master/optional FBX and GLB roundtrip report |
| `export` | input, matching QA, release approval | release-reviewed files and repeated roundtrip |
| `selftest` | none | synthetic fixture files and local integration report |

### Facial Rigging and Studio Render Jobs

```json
{
  "task": "face_rig",
  "input": "inputs/hunyuan/head.glb",
  "animate_expression": true,
  "landmarks": {
    "mouth_corner_x": 0.065,
    "mouth_y": -0.285,
    "mouth_z": 0.420,
    "cheek_z": 0.465,
    "eye_z": 0.505
  }
}
```

```json
{
  "task": "studio_render",
  "input": "runs/<face_rig_run>/face_rigged.blend",
  "render_frames": [1, 30],
  "samples": 32
}
```


For editing tasks the scene output is normally `scene.blend`. Preserve the exact path returned by the run rather than assuming a stable global filename. The top-level `high` field is a dependency file path; a bake pair's `high` is an array of already imported object names. They are deliberately different.

## Inspection, preparation and previews

```json
{"task":"inspect","input":"inputs/hunyuan/low-v001.glb"}
```

```json
{
  "task":"prepare",
  "input":"inputs/hunyuan/low-v001.glb",
  "high":"inputs/hunyuan/high-v001.glb",
  "approval_file":"approvals/geometry-v001.json",
  "height_m":1.8,
  "rotation_degrees":[0,0,0],
  "merge_distance_fraction":0
}
```

The high import receives `HIGH__` object-name prefixes. Both low and high are transformed identically; inspect the actual resulting names. `merge_distance_fraction` defaults to zero and cannot exceed 0.0001 of height. Changing shape/units after skinning or with unresolved modifiers is refused.

```json
{
  "task":"preview",
  "input":"inputs/accepted.blend",
  "resolution":512,
  "samples":16,
  "sample_frames":[1],
  "angles_degrees":[0,45,90,135,180,225,270,315]
}
```

Preview renders are CPU Cycles for a predictable baseline and are capped at 64 view/frame combinations per job. GPU configuration is not guessed. A local GPU optimization must be explicit and tested.

## UV, provisional retopology and baking

```json
{"task":"uv","input":"inputs/accepted.blend","uv_mode":"preserve"}
```

```json
{
  "task":"uv",
  "input":"inputs/unwrapped-candidate.blend",
  "uv_mode":"smart_project",
  "approval_file":"approvals/uv-rebuild.json",
  "island_margin":0.02
}
```

```json
{
  "task":"retopo",
  "input":"inputs/accepted.blend",
  "objects":["Body"],
  "approval_file":"approvals/retopology.json",
  "target_faces":15000,
  "symmetry":false
}
```

```json
{
  "task":"bake",
  "input":"inputs/low-high-uv-approved.blend",
  "resolution":2048,
  "maps":["NORMAL","AO"],
  "samples":16,
  "margin_pixels":16,
  "max_miss_fraction":0.005,
  "pairs":[{"low":"Body","high":["HIGH__Body"],"ray_distance":0.005}]
}
```

Choose object names from the actual audit. `ray_distance` is in prepared scene units and must be justified by scale. Omit it to use the helper's part-relative default. An optional pair field `cage` names an existing same-topology cage object. Inspect its correspondence. The helper does not auto-create a production cage. Do not append the high source again if the input `.blend` already contains it.

Baked image nodes are targets, not automatically approved shader mappings. Connect an accepted map with `materials`. Save/reuse the exact texture paths from the successful bake run. A failed bake keeps diagnostic files but must not be silently promoted.

## Material mapping and intermediate upload

```json
{
  "task":"materials",
  "input":"inputs/textured-v001.blend",
  "materials":[{
    "material":"Skin",
    "base_color":"inputs/textures/skin-base.png",
    "normal_map":"inputs/textures/skin-normal.png",
    "normal_convention":"+Y",
    "normal_strength":1,
    "roughness_map":"inputs/textures/skin-roughness.png",
    "metallic":0
  }]
}
```

Supported optional material fields include `metallic_map`, `ao_map`, `emission_map`, `roughness`, `ior`, `subsurface_weight`, `subsurface_scale` and `replace_graph`. Full replacement requires `materials_replace` approval. Existing connected scalar inputs cannot be overwritten with a constant by accident. A DirectX normal requires an explicit channel conversion before this job.

```json
{"task":"handoff","input":"inputs/low-uv-materials-approved.blend"}
```

This produces an **intermediate** UV-bearing GLB, not a final release. It refuses to strip an existing armature automatically. The browser agent must still verify upload authorization and reimport correspondence after Modddif. Local creation of `handoff.glb` itself spends no service credits.

## Skeleton and animation jobs

```json
{
  "task":"rig",
  "input":"inputs/textured-approved.blend",
  "skeleton":"inputs/fitted-skeleton.json",
  "approval_file":"approvals/skeleton-fit.json",
  "max_influences":4
}
```

The skeleton schema is supplied in `assets/skeleton.schema.json`. It contains a name, explicit bones with head/tail/parent/roll/deform/connected fields, and a mapping of rigid object names to deform bones. Coordinates must fit the actual mesh. The helper is not an anatomy estimator. `skeleton.fixture.json` is a synthetic test reference and must not be used as a human rig.

```json
{"task":"animate","input":"inputs/rig-approved.blend","motion":"inputs/motion/idle-keys.json"}
```

Motion JSON contains `name`, `fps`, `loop` and strictly increasing `frames`. Each frame contains a `bones` object mapping existing names to local `rotation_degrees` XYZ and/or `location`. Unspecified bones receive explicit rest keys. The included fixture motion is a test bend, not a production walk. Preserve previous actions in their own checkpoints before creating another clip.

```json
{
  "task":"retarget",
  "input":"inputs/rig-approved.blend",
  "source":"inputs/motion/source-walk.fbx",
  "mapping":"inputs/motion/walk-map.json",
  "approval_file":"approvals/retarget-calibration.json",
  "fps":30
}
```

The retarget approval must include `mapping_sha256` and `source_sha256` matching both files, in addition to the target input hash. Mapping contains `alignment_reviewed:true`, `bones` as target-name → source-name, `source_to_target_rotation_degrees`, `source_fps`, `translation_scale`, `root_motion` (`in_place` or `preserve_translation`) and optional `translation_target`/`translation_source`. Set these from real source/target inspection. This helper does not solve contacts, facial motion, twist distribution or root yaw.

## QA, candidate export, target test, final export

```json
{
  "task":"qa",
  "input":"inputs/animated-approved.blend",
  "expect_rig":true,
  "expect_animation":true,
  "max_triangles":80000,
  "max_influences":4,
  "weight_tolerance":0.0001,
  "max_edge_stretch":5,
  "sample_frames":[1,8,16,24,32]
}
```

Use actual clip frames. For a static mesh check set `expect_rig:false` and `expect_animation:false`. The helper does not inherit quality values automatically from `project.json`; supply approved per-job settings.

```json
{
  "task":"export_candidate",
  "input":"inputs/animated-approved.blend",
  "qa_report":"inputs/reports/animated-qa.json",
  "animation_mode":"ACTIVE_ACTIONS",
  "fbx":false
}
```

The referenced QA must be the report for the exact input hash. Candidate export is necessary to test the actual target before granting release approval. It saves a master and reimports the GLB locally, but its status remains a candidate. Test that exported artifact in the target engine/viewer and record evidence. For several clips use a deliberately assembled and tested NLA/action strategy; do not select a broad export mode to recover untracked orphan actions.

```json
{
  "task":"export",
  "input":"inputs/animated-approved.blend",
  "qa_report":"inputs/reports/animated-qa.json",
  "approval_file":"approvals/release.json",
  "animation_mode":"ACTIVE_ACTIONS",
  "fbx":true
}
```

Release approval must match the input and list `identity`, `texture_seams`, `joint_deformation`, `animation`, `target_compatibility` in `visual_checks_passed`. Do not falsely mark target compatibility just because Blender reimport succeeded. Candidate and final exports should be compared; retest if the final output materially differs. FBX reimport and destination playback are not performed by the helper and must be verified separately when requested.

## Hashes, events and generation reservations

```powershell
# NEW: obtain a content hash for a genuine approval record.
(Get-FileHash -Algorithm SHA256 "$Work\inputs\animated-approved.blend").Hash.ToLowerInvariant()

# NEW: validate a downloaded container before Blender inspection.
node "$Skill\scripts\pipeline.mjs" check-glb --project "$Work" --file "inputs/modddif/textured-v001.glb"

# NEW: reserve a cost observed in the current authorized account before submitting the browser job.
node "$Skill\scripts\pipeline.mjs" reserve --project "$Work" --domain "app.modddif.com" --cost 2 --evidence "evidence/observed-cost.png"

# NEW: append a browser/review/checkpoint record with a real evidence file.
node "$Skill\scripts\pipeline.mjs" event --project "$Work" --file "evidence/browser-event.json"
```

The example cost `2` is illustrative, **not a Modddif price**; use the observed value. A zero-cost generation still consumes the configured generation-count budget. Approved domains must first be recorded in `project.json`. The reservation log does not grant account permission or prove a paid call actually occurred; record the subsequent job/result separately.

Event types: `browser_observation`, `generation_submitted`, `generation_result`, `checkpoint`, `blocked`, `visual_review`, `operator_approval`. Each event requires an existing evidence path. Do not include passwords, cookies, tokens or unrelated account data.
