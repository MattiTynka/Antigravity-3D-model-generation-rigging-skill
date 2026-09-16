# Source registry and verification boundaries

Checked 15 September 2026. This registry supports the skill. Public documentation was checked independently. Authenticated Hunyuan/Modddif interfaces and account entitlements were not exercised.

The operational choices, quality thresholds, folder design and helper code are authored engineering recommendations. They are not advertised guarantees from the listed services. Interface details and terms must be rechecked when running the skill.

## Agent installation and browser control

| ID | Primary source | What it supports |
|---|---|---|
| C1 | [OpenAI skills documentation](https://developers.openai.com/codex/skills/) and its [current documentation destination](https://learn.chatgpt.com/docs/build-skills) | SKILL.md, progressive disclosure, repo skill discovery and supporting files |
| C2 | [Claude Code skills](https://code.claude.com/docs/en/skills) | Claude skill directories, explicit invocation and reference files |
| C3 | [Claude Code with Chrome](https://code.claude.com/docs/en/chrome) | Authorized browser integration; live tool availability must be verified |
| C4 | [Claude Code: Chrome, Russian](https://code.claude.com/docs/ru/chrome) | Russian browser setup guidance |
| C5 | [Chrome DevTools agent configuration](https://developer.chrome.com/docs/devtools/agents/get-started/configuration) | Existing-session auto-connect and user remote-debugging approval |
| C6 | [Chrome DevTools MCP README](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/README.md) and [configuration](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/configuration.md) | Server configuration and telemetry flags; version-dependent setup |
| C7 | [Chrome DevTools MCP tool reference](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md) | Actual page, pointer, file-upload and screenshot tool contracts |

## Hunyuan

| ID | Primary source | What it supports |
|---|---|---|
| H1 | [Hunyuan3D Studio paper, abstract](https://arxiv.org/abs/2509.12815) | Research description of the asset pipeline; not an account-specific UI guarantee |
| H2 | [Tencent Hunyuan3D-2 repository](https://github.com/Tencent-Hunyuan/Hunyuan3D-2) | Open-source project scope and its separate licensing context |
| H3 | [Tencent cloud 3D product](https://cloud.tencent.cn/product/ai3d) | Commercial service capability context; not interchangeable with every studio tab |

The requested [Hunyuan web studio](https://3d.hunyuan.tencent.com/) could not be inspected as an authenticated session. No fixed daily quota, current button layout, free-tier rigging entitlement or export format is asserted from the tutorial alone.

## Modddif

| ID | Primary source | What it supports |
|---|---|---|
| M1 | [Create/import an object](https://docs.modddif.com/project/create_an_object/) | Import formats and limits; possible automatic simplification |
| M2 | [Texture tools](https://docs.modddif.com/project/texture/) | Active-reference behavior and distinctions among camera generation, masking, patching and layers |
| M3 | [Reference images](https://docs.modddif.com/project/reference_images/) | Reference management versus image variation |
| M4 | [Part masking](https://docs.modddif.com/project/part_masking/) | Reversible region visibility and masking behavior |
| M5 | [Segmentation](https://docs.modddif.com/project/segmentation/) | Semantic part workflows and their separate consequences |
| M6 | [Multi-object texturing](https://docs.modddif.com/project/multi_objects_texturing/) | Working with adjacent objects as context |
| M7 | [Viewport settings](https://docs.modddif.com/project/viewport_settings/) | Flat/PBR/normal and lighting inspection modes |
| M8 | [Normal map tools](https://docs.modddif.com/project/normalmap/) | Imported normals, generated normal detail and deterministic-view behavior |
| M9 | [Official tutorial index](https://docs.modddif.com/videos/) | English workflows by Stefan3D and PixelArtistry, including AI-model texture repair |
| M10 | [Modddif site](https://modddif.com/) and [project creation](https://docs.modddif.com/project/create_a_project/) | Plan/project context; read the actual account terms/privacy before upload |

The requested [Modddif application](https://app.modddif.com/) is an authenticated interactive app, not a stable text API. The agent must observe current prices and project visibility. This bundle does not rely on undocumented “Seal” mode, automatic joint conditioning by all uploaded references, built-in Modddif rigging, or an unobserved PBR export panel.

## Blender and asset formats

| ID | Primary source | What it supports |
|---|---|---|
| B1 | [Blender 4.5 LTS](https://www.blender.org/releases/4-5/) | Intended stable baseline; not a claim that this is the latest Blender branch |
| B2 | [Blender 4.5 command line](https://docs.blender.org/manual/en/4.5/advanced/command_line/index.html) | Background execution and command-line workflow |
| B3 | [Cycles baking manual](https://docs.blender.org/manual/en/5.0/render/cycles/baking.html) | General baking, active image and projection concepts; page version 5.0, so check installed 4.5 RNA/operator behavior |
| B4 | [Blender glTF documentation](https://github.com/KhronosGroup/glTF-Blender-IO/blob/main/docs/blender_docs/scene_gltf2.rst) | Supported material/animation mappings and export conventions |
| B5 | [Khronos glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html) | Metallic/roughness, channel semantics and normal/skin conventions |
| B6 | [Blender 4.5 glTF exporter source](https://github.com/KhronosGroup/glTF-Blender-IO/blob/blender-v4.5-release/addons/io_scene_gltf2/__init__.py) | Version-specific export parameters and animation-mode names |
| B7 | [Russian Cycles baking manual](https://docs.blender.org/manual/ru/3.3/render/cycles/baking.html) | Russian explanation of stable baking concepts; older UI version, not a current button map |

## Rigging and motion

| ID | Primary source | What it supports |
|---|---|---|
| R1 | [Adobe Mixamo FAQ](https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html) | Humanoid auto-rig constraints and incorporated commercial-use FAQ; verify current terms separately |
| R2 | [Rigify basics, Blender 4.5](https://docs.blender.org/manual/en/4.5/addons/rigging/rigify/basics.html) | Metarig/control-rig distinction; public text was also available through the manual's locale mirror |
| R3 | [Rigify bone positioning, Blender 4.5](https://docs.blender.org/manual/en/4.5/addons/rigging/rigify/bone_positioning.html) | Joint, facial and finger fitting principles; inspect current installed add-on |

Commercial add-ons are optional adapters only. They are not included or claimed tested. No assertion of a universally automatic humanoid/creature/facial rig is made.

## Related learning material, English and Russian

The official Modddif tutorial index [M9] lists “AI texturing like a Pro,” “How to Fix AI Generated 3D Models,” “Best Free AI Texture Workflow,” and a 2026 model-to-texture workflow. The index identifies the creators and workflow subjects. The videos were not fully watched or benchmarked here; they are further viewing, not evidence for unverified timing/quality claims.

The Russian operational manual in this bundle is independently authored with the same technical, safety, and quality gates.

## Rights and uncertainty

Record the actual terms and rights applicable to each input and output at execution time. This registry is not a legal clearance or a promise that service output is commercially unrestricted. Reference rights, recognizable-person consent, generated-asset terms, motion redistribution and add-on licenses are separate questions. A paid account is not automatic permission to upload a client's confidential material.

No live browser end-to-end run, real character deformation benchmark, target engine test or Blender integration run was completed during authoring. Consult the bundle's `VERIFICATION.md` for the tests actually executed.
