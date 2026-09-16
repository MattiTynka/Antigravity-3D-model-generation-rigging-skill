# End-to-end execution and checkpoints

This is the operational plan to follow after loading the entry skill. Numeric targets below are editable project defaults, not service limits or universal production standards. The stage sequence deliberately freezes deformation geometry before final texturing and skinning, and treats every service output as a candidate.

## S0 — Resolve the brief and initialize

Read the request and existing project first. Record: character identity and must-preserve features; image paths and ownership; stylized versus realistic target; target engine/viewer; body height or explicit arbitrary units; desired animations and root-motion policy; face requirements; triangle/texture limits; permitted upload services; confidentiality/publication policy; generation count/credit caps. Use neutral defaults only for aesthetic or technical choices that are inexpensive to revise. A public-project setting, payment, copyright permission or anatomy is not a safe default.

Initialize a workspace independent of the skill installation. Keep original assets immutable and outside Git by default. `project.json` starts with zero generation budget. With explicit user consent, update the service allowlist and budget; save the authorization evidence. A user may delegate repeated visual reviews within a specified scope. Preserve exactly that scope and distinguish agent decisions from operator decisions.

Create `provenance.json`, `evidence/capabilities.json`, `NEXT_ACTION.md` and `asset-manifest.json`. The local `state.json` is a journal of helper runs/events, not a complete security-enforced workflow engine. It cannot independently authenticate human consent. Stage promotion remains the agent's responsibility.

## S1 — Build a trustworthy reference set

Inventory the supplied images before generating new ones. For a humanoid, prefer neutral expression, full body, unoccluded hands, separated fingers where practical, feet visible, and an A/T pose compatible with the target service. Match proportions, hairstyle, costume layers, accessories and face identity across views. Do not let a back view silently invent a backpack or a side view change the nose.

The preferred local reference set is `front.png`, `left.png`, `right.png` when supplied, `back.png`, and `face.png`, with each view in a separate file. A contact sheet is for review, not automatically one multiview input. Record dimensions and framing; align crown, chin, pelvis and soles across orthographic views. Images that look orthographic are not necessarily metrically consistent. Mark an inferred view as inferred.

If the host has an authorized image-generation tool, generate missing reference candidates and review them before upload. Otherwise continue from usable supplied views, or request the missing view when necessary. Do not invent an image-generation API or treat a browser text model as guaranteed image generation. Avoid embedded perspective, dramatic lighting and background clutter that the reconstruction may mistake for shape.

Write a must-preserve checklist: for example “two wings, rounded torso, long ears, five fingers, left shoulder ornament, three coat tails.” Compare every later silhouette against this checklist. This is especially important for stylized and non-human characters.

**Gate S1:** reference identity and pose approved; images and provenance hashed. No generative reconstruction until the input set is internally coherent enough for the requested fidelity.

## S2 — Generate and select geometry

Follow `hunyuan.md`. Capture current UI capabilities instead of assuming a version, quota or export feature. Generate a small number of budgeted candidates, save the high-resolution source, request a separate lower-resolution topology candidate, and download both. Preserve a pre-texture base when available. Name inputs by candidate and immutable version, not `final.glb`.

Inspect candidates headlessly and render neutral orthographic views. Score identity, silhouette, missing parts, fused surfaces, face profile, hands and rest pose before comparing texture detail. A strong texture can conceal a broken nose or merged fingers. Choose one candidate and record why rejected candidates were rejected. Do not combine unrelated high and low meshes for baking merely because their filenames match.

**Gate S2:** chosen geometry is worth repairing. If silhouette or anatomy is fundamentally wrong, regenerate the geometry or use a better modeling route before paying for detailed textures.

## S3 — Repair geometry locally

Read `blender-geometry.md`; run `inspect` first. Normalize chosen low/high together, conservatively remove invisible isolated vertices, and review normals. Render before and after. Identify defects by object and vertex/face region rather than issuing a global “cleanup everything.” Preserve separate hair, teeth, eyes, clothing layers and accessories.

Branch from a pre-rig checkpoint for topology edits. Use Hunyuan topology when it deforms acceptably; otherwise generate a provisional QuadriFlow candidate, use an already installed trusted retopology tool, or author focused local retopology operations. Do not automatically download commercial add-ons or equate decimation with retopology. Validate edge flow in likely joint bends before approval.

**Gate S3:** silhouette and must-preserve features retained; repair diff understood; no unexplained surface loss; deformation topology accepted for the chosen use. Headless automation still requires the agent to view renders.

## S4 — Freeze UVs, shading basis and bakes

Check UV existence, overlap policy, distortion and density. Preserve good UVs. Rebuilding UVs invalidates existing texture correspondence; explicitly approve it. Decide material slots and tangent-basis/triangulation before final normal baking. Keep an editable source plus a deterministic export/bake topology checkpoint.

Bake isolated high-to-low pairs, starting at modest resolution to diagnose projection. Inspect the coverage pass, normals, UV seams, inner legs, ears, fingers and clothing overlaps. Increase resolution only after the mapping works. Save texture files, cage configuration, input hashes and a neutral shaded preview. The helper detects sampled missing hits but cannot prove rays hit the correct anatomical surface.

Use `handoff` to create the unrigged intermediate GLB for Modddif; this is not the final release export.

**Gate S4:** chosen low mesh/UV/bake basis approved and versioned. If a later service changes them, re-enter S4 instead of silently reusing the normal map.

## S5 — Improve texture in Modddif

Read `modddif.md`. Prefer an approved private project; do not copy the tutorial's automatic public-project choice. Import the final low mesh and inspect it before generation. If the service changes triangle count, object structure or UVs, decide explicitly whether to reject that import, reduce the mesh locally, or adopt the changed mesh and rebake.

Use the face reference to establish identity, then body front, sides, back and occluded areas. Keep a patch log with camera/view, intended correction, selected reference, result layer and before/after evidence. Evaluate transitions in more than the generation camera. Treat a painted-on strap, eye, finger or fold as texture, not repaired geometry.

Export a self-contained GLB and any separately available maps. Do not promise that an unobserved export panel supports all PBR channels. Reinspect the exported mesh in Blender and compare with the frozen version.

**Gate S5:** coherent identity and coverage, no obvious seam or illumination artifacts; exported geometry/UV relationship documented.

## S6 — Reconstruct and validate materials

Retain material-to-face assignments. Identify base color, normal, roughness, metal, occlusion and emission by actual file and channel semantics. Assign correct color spaces. Avoid baking AO twice, treating a beauty image as physical albedo, or making skin metallic to improve highlights. Look at separate skin, cloth, hair and metal in neutral lighting before a final beauty scene.

Use the existing valid normal map only when its tangent basis remains compatible. Distinguish geometric detail from painted shading; neither a normal map nor subsurface scattering fixes a wrong silhouette. Verify target support for translucency, subsurface and alpha. Save an engine-compatible material checkpoint separately from any Cycles-only look-development scene.

**Gate S6:** shader mappings, texture paths and target feature limitations recorded; neutral comparison accepted.

## S7 — Fit and bind a rig

Read `rigging-animation.md`. Reuse a good downloaded rig when possible; do not add a second armature automatically. For an unrigged model, choose between an approved external humanoid auto-rigger and a local landmark-fitted deform rig. A Rigify control rig is an optional layer after the metarig is correctly fitted, not a substitute for anatomical fitting.

Generate calibrated front/side views; infer candidate joint centers from multiple views; compare a skeleton overlay; request or perform a delegated visual approval. Store the fitted skeleton in JSON tied to the exact mesh hash. Bind and inspect weights. If automatic weighting fails, fix the responsible geometry, separate rigid attachments, or transfer weights from an approved body proxy. Never “solve” by attaching every unweighted vertex to the nearest bone without anatomical review.

**Gate S7:** complete hierarchy, no unweighted deform vertices, bounded normalized influences, stable joint poses, no lost appendages. Facial rigging is a separate acceptance item when requested.

## S8 — Animate, retarget and correct

For a minimal verified result, create an explicitly authored idle/test action on the approved rig. For walking or expressive movement, import licensed motion or author a proper clip. Calibrate rest poses, bone correspondence, character scale and axes before transfer. Run a short contact test before baking a long sequence.

Check knee/elbow direction, twist, head alignment, foot height, sliding, hand collisions and ground plane. Separate root-motion policy from hip motion. Make loops continuous in transforms and velocity; remove a duplicated terminal sample in the exported cycle when the destination requires it. Preserve each accepted clip and its source license. Assemble multiple clips through intentional action/NLA handling, not “export all actions” on an unclean scene.

**Gate S8:** named clips, explicit FPS/duration/root policy, deformations and contact behavior accepted. A plausible first frame does not validate an animation.

## S9 — Mechanical and visual acceptance

Run `qa` on the exact candidate `.blend`, then render reference-matched stills and sampled animation views. Record checklist outcomes and evidence. The mechanical report does not cover UV intersections, all self-collisions, facial identity, foot locking or engine parity. Do those separately. For a changed input hash, every dependent QA/approval must be refreshed.

A failed gate yields a candidate plus the cause and next safe operation, not a final asset disguised by a beauty render. Use a new version for fixes. Any topology change requires reconsidering UVs, bakes, skinning and downstream animations.

## S10 — Export, reimport and deliver

First run `export_candidate` after mechanical QA to obtain the exact artifact needed for target playback. Grant release approval only after the candidate's actual target test. Then run `export` for the release-reviewed GLB and optional FBX; compare the final output and repeat target checks if it changed materially. The helper saves a packed `.blend`, exports selected mesh/armature objects, and reimports GLB in a clean scene. It does not test FBX reimport or the destination engine; add those tests when FBX or a specific engine is requested. Perform full Khronos validation when an approved validator is available. Reopen the scene without the original input directory mounted to verify self-contained dependencies.

Test the exported asset in the actual target. If unavailable, label it `CANDIDATE` or “Blender roundtrip verified; target playback untested,” not `VERIFIED_FOR_TARGET`. Copy only accepted deliverables into `delivery/`, preserving the run artifacts. Include master scene, models, maps, clips manifest, previews, provenance, QA, licenses/limitations and hashes. Write a concise completion summary with actual file paths.
