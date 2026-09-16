# Modddif: controlled appearance improvement

Use the existing authorized `https://app.modddif.com/` tab. The live account, entitlements and export panel must be inspected. This runbook is an original checkpoint strategy around the documented tools, not a guarantee that a given account presents identical controls.

## Verified interface facts to discover in the live UI

The documented texture workflow uses one actively selected reference per generation, camera-dependent layers, and separate region-generation and patch-application operations. `K` selects the inpainting region; `I` is the patch tool. Patch edits need a UV-mapped paint layer rather than a projected layer. Albedo and color-matching options are documented. [M2]

Import may simplify oversized meshes; the documentation distinguishes object limits and UV-dependent import limits. Check current limits in the actual account rather than trusting the tutorial. [M1] Project reference images and image-variation inputs are distinct from texturing conditioning. [M3] Temporary part masks and segmentation affect which surfaces are accessible; neither is a replacement for a saved topology decision. [M4–M5]

## A. Establish a safe project

Read current privacy and publication settings before creating a project. Prefer an existing approved private project. If only public creation is available, stop for consent rather than exposing a customer's model. Preserve the source image rights and account-specific terms in provenance; free access is not itself permission for confidential use. [M10]

Upload the approved low-poly checkpoint, not a randomly chosen source or rigged export. Capture any simplification/unwrap warning. Save an immediate exported roundtrip when the UI permits it. Inspect triangle counts, object structure, bounding box, geometric/UV fingerprints and material slots in Blender. Equal counts alone are insufficient; UVs can change without a count change.

If correspondence changes, choose one explicit branch: reject the modified import and lower the original mesh under the observed limit; or adopt the service-modified mesh as a new candidate, revalidate UVs, and rebake high-to-low. Never paste the old tangent normal onto an unrelated UV layout. Existing normal maps and generated normal tools have separate roles. [M8]

### Critical Diagnostic: WebGL Decimation Seam Collapse & 'Black Spots/Holes' on Skin

When models exceeding 100k–150k triangles are uploaded into Modddif's web interface, the platform executes automatic client-side WebGL decimation to bring the mesh under its viewport performance threshold (~150k triangles).

**Observed Failure Mode**:
- Downsampling collapses border vertices along UV seams.
- Texture sampling interpolates past the UV boundary margin into the black background or dark hair texture pixels.
- The rendered character exhibits dark speckles, "holes", or black tears along the nostrils, lower eyelids, philtrum, and lips.

**Resolution Protocol**:
1. **Source Texture Inspection**: Check the raw AI reconstruction (e.g. `hunyuan_model.glb`). High-tier AI generators produce pristine 4096×4096 (4K) Albedo, Normal, and Roughness maps with verified, intact primary `UVMap` layers.
2. **Do Not Patch Inpaint Bleed Defects**: Attempting to use Modddif's inpaint brush (`K` / `I`) over collapsed UV borders will continually resample dark boundary pixels, burning generation credits fruitlessly.
3. **Pristine UV Preservation Strategy**: If Modddif's decimation introduces UV tears or dark speckles on the skin, bypass the corrupted WebGL export and preserve the pristine 4K PBR texture maps from the raw Hunyuan GLB. Connect these maps directly in Blender with calibrated dielectric skin shading.


## B. Plan reference use and camera coverage

Create a local camera/region plan before generating. Suggested region order: face → neck/ears → torso front → each side → back → hands and feet → underarms/inner legs → accessory transitions. This prioritizes identity and avoids spending the budget on a body whose face is unacceptable.

Use a face close-up for identity work and a view-matched body reference for the relevant region. Keep the current choice explicit in the evidence. A pile of reference thumbnails is not proof that they jointly condition the next result. The chosen image should be inspected immediately before every submit.

The camera should see the surface close to face-on, with enough surrounding accepted texture to evaluate continuity. Excessively oblique projection stretches fine details. For ears, inner limbs and undersides, make additional views rather than increasing the influence of a distant view until it bleeds through other surfaces. Keep camera orientation, framing, screenshot size and selected region together in the patch log.

## C. Establish the face

Keep a pristine imported layer/checkpoint. Frame the head with ears, chin and hairline visible. Do not crop so tightly that eye position is ambiguous. Use the reference expression intended for the rest model: a neutral closed-mouth reference should not become a broad painted smile.

Generate one candidate for the planned face view. Compare eye separation, eyebrow shape, lip position, nose outline, skin tone and asymmetry with the reference. If the painted eye or mouth is displaced from the actual mesh structure, do not simply accept the image because it looks attractive from this camera. Decide whether the geometry needs correction or the texture candidate is wrong.

Commit only an accepted result. Record an identity anchor screenshot before covering the rest of the model. Review from the opposite three-quarter view to catch a convincing frontal illusion that breaks as soon as the head rotates. Check both sides of the neck for abrupt skin-tone transitions.

## D. Cover the body without sacrificing identity

For each planned region, verify camera, active object/part, active reference and generation scope. Use a small experiment first when changing mode or references. Do not regenerate a complete accepted face just to repair a boot. Preserve layers/checkpoints that allow rollback.

Inspect costume correspondence: a belt should follow the actual belt surface, sleeve colors should agree on both sides, hair should not paint over a collar, and a front logo should not appear on the back. Treat any newly invented feature as a mismatch unless the user delegated design changes. A generated material edge must agree with the mesh/material segmentation needed for later deformation.

Maintain a table containing region, source reference, view, layer/checkpoint, accepted defects and rejected defects. When the budget is limited, prioritize visible silhouette-adjacent surfaces and continuity over imperceptible microdetail. Do not leave uninspected undersides merely because the default turntable hides them.

## E. Local artifact repair as a bounded loop

Diagnose the defect before changing it. Separate a wrong color, a projection seam, a baked shadow, an occluded unpainted surface and an actual geometric dent. A texture patch can repair only the appearance-related cases.

Capture a before screenshot and a second angle. Select the smallest region that includes the defect plus a modest transition border. Verify the visible selection/mask before submitting; never assume a brush stroke registered because the mouse moved. After the candidate arrives, compare it against the accepted surrounding skin/cloth and the reference. Apply only the useful portion to a reversible correction layer. Recheck from the second angle before accepting.

If nothing changes after patching, check the selected layer type, tool, brush settings, visibility and active object before paying for another generation. If a fix changes unrelated areas, undo and reduce scope. If an apparent seam changes when the model rotates, investigate view projection and material shading rather than repeatedly changing color.

Allow two clearly justified local attempts under the agreed budget. After that, change the causal approach: use another camera, correct geometry, adjust the mask, or perform a controlled local texture edit in Blender. Do not make a third identical stochastic call and label it a new strategy.

## F. Occlusions, parts and layers

Use reversible part visibility to reveal inner legs, armpits or overlapping garments. Confirm which part is hidden, and restore visibility before export. A mask controlling visible mesh parts is different from a screen-space regeneration region or a texture layer's opacity. Record which kind is active. [M4–M5]

For multi-object characters, compare adjacent objects together while editing one when the interface allows it. This helps detect different skin colors across a neck/head split or material inconsistency between boots. [M6] Preserve object and material identities for the local rigging stage.

Inspect appearance under a flat/unlit view and under neutral PBR lighting; rotate the environment separately from the character when available. [M7] A dark patch that stays fixed in the texture after light rotation is not necessarily legitimate material color. Reserve final beauty lighting until this diagnosis is complete.

## G. Normal details and export

Prefer a correctly baked geometry normal for mesh detail. Additional image-derived detail is a separate, optional texture layer, not evidence of real geometry. The documented normal-generation tool can be deterministic for an unchanged view; identical retries are not a reliable improvement mechanism. [M8]

Never RGB-average two tangent-space normal maps. Choose the appropriate map or combine them through a deliberate normal-composition method and rebake against the frozen tangent basis. Avoid reinforcing a painted cloth fold both in color shading and an exaggerated normal until it looks engraved.

Inspect the actual export options. Save GLB and any offered separate maps, preserving resolution and channel names. Do not assume roughness/metal/AO export just because the viewport has sliders. Export to a new filename. Verify download completion, container integrity, Blender import, material assignment and the frozen geometry/UV comparison. Save the project URL and accepted layer/camera evidence for a later correction without publishing it.

## Acceptance

Reject the texture checkpoint when the face differs from the agreed identity, a seam appears in a normal viewing angle, a material region is painted on the wrong surface, a meaningful area remains untextured, or geometry/UV changes are unexplained. Pass it only with front/side/back and detail comparisons. A visually attractive Modddif preview is not the final Blender/engine material test.

Related English learning material is curated in the official tutorial index [M9]: Stefan3D's texturing and repair workflows and PixelArtistry's model-to-texture workflow. For Russian-language guidance, refer to the bundled operational manual in [operations-ru.md](operations-ru.md).
