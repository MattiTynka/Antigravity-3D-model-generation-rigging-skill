# Headless Blender: geometry, UVs, baking and materials

Use the included coordinator and script for the bounded operations listed in `commands.md`. More invasive fixes below are local modeling recipes for the agent to implement against identified objects/regions, not capabilities falsely attributed to the generic helper. For every new operation, start from an immutable checkpoint, add a small test or fixture, save a new result and compare renders before accepting it.

## Inspection before modification

Import with automatic execution disabled. Prefer self-contained GLB and packed local `.blend` files. An OBJ used as a high-poly source should be geometry-only; the helper refuses external `mtllib` references. For third-party `.blend` files, retain the auto-execution restriction, inspect drivers and external dependencies, and never execute embedded text blocks. Disabling scripts is not a substitute for obtaining files from a trusted source.

Run `inspect` and record object names, bounding boxes, transforms, triangle counts, material slots, UV validity, connected components, boundary edges, non-boundary non-manifold edges, degenerate faces, modifiers, shape keys, armatures and actions. The helper's audit covers a subset of these; record the rest through a narrowly scoped Blender inspection script when necessary. It explicitly does not infer semantic topology quality or fully detect UV overlap and self-intersections.

Make neutral front, side, back and oblique renders. Use matching camera matrices and lighting for before/after comparison. Also inspect silhouettes, wireframe overlays, face/hands and a normal-only material. A generic eight-view preview is supplied; close-up framing and wireframe passes are deliberate extensions using the same calibrated scene, not a reason to open and manually operate Blender.

## Normalize once, together

Use an explicit axis convention: Z up, character facing negative Y, character-left positive X when this matches the reviewed model. Resolve exceptions from the actual reference, not filenames. Set a documented real or arbitrary height. For stylized characters preserve proportions; normalization changes overall scale and orientation, not body shape.

Apply one shared affine transform to high and low sources. Ground the soles and center horizontal bounds when appropriate. The `prepare` helper copies mesh data, normalizes both sources together and records the matrix. It refuses existing modifiers, rigs or shape keys rather than silently applying transformations that change deformation behavior. After rigging, change units/orientation only through an explicitly tested whole-character transform workflow.

Do not normalize high and low independently to their own bounds. A stray source detail can otherwise change one mesh's scale and misalign every baking ray. Check correspondence by overlay and cross-sections after normalization.

## Conservative defect repair

The supplied `prepare` task removes isolated vertices, optionally merges extremely close vertices and recalculates face normals. It does **not** automatically delete surface components, dissolve every degenerate face, fill holes, repair all self-intersections or sculpt anatomy.

For additional defects use this decision process:

| Defect | Targeted operation | Required check |
|---|---|---|
| Coincident duplicates | Merge only the reviewed object/region with a scale-relative tolerance | Finger gaps, eyelids, garment borders and UV/sharp seams remain distinct |
| Zero-area or repeated faces | Identify exact face indices; dissolve/remove on a candidate mesh | No new unintended opening; triangulation and material assignment remain valid |
| Inverted faces | Inspect orientation on a locally coherent shell, then recalculate or flip that shell | Internal lining, thin cloth and mirrored transforms are not incorrectly “fixed” |
| Non-manifold junction | Separate overlapping shells or rebuild the affected patch | No crossing internal face; intentionally open boundaries preserved |
| Small floating component | Classify against references before removal | Buttons, teeth, eyes, jewelry, claws, wings and hair strands are never removed by size alone |
| Unwanted hole | Reconstruct the local surface from neighboring flow/reference | Do not cap cuffs, nostrils, eye sockets, mouth openings or garment hems indiscriminately |
| Fused fingers/limbs | Reconstruct separation and local topology, or regenerate the problematic source | New geometry supports the required range of movement |
| Noisy surface | Masked smoothing/sculpt-style correction on the source, with silhouette constraint | Preserve deliberate folds, facial features and stylization |

Use BMesh on copies with explicit vertex/face selections and quantitative changes logged. A generic `remove_doubles` across a entire close-fitting outfit is unsafe. Stop for a topology decision when a repair changes more than the approved region or removes a must-preserve feature. Save source and candidate side by side; do not overwrite the high-poly reference to make a bake look better.

For local smoothing, keep boundary and feature vertices fixed, limit displacement relative to mesh scale, and inspect a signed/distance color overlay. For overlapping garments, separate material surfaces logically; do not union the whole outfit just to make it watertight. Character surfaces need animation suitability, not necessarily 3D-print manifoldness.

## Retopology strategy

First try the service's low-poly candidate in validation poses. If its edge flow is inadequate, distinguish three tasks: reducing face count, redistributing topology, and rebuilding semantic loops. Decimation addresses the first; automatic quad remeshing may help the second; joints and expressive faces often require the third.

The bundled `retopo` task runs a single-object QuadriFlow candidate with an explicit face target. It invalidates UVs, bakes and skinning; it is not a production facial retopology tool. Symmetry is off by default. Enable symmetry only after the reference and mesh support it; retain asymmetric hair, clothing, scars and accessories as separate intentional features.

A local retopology recipe for a difficult body region is: create a clean low-resolution patch; place loops around the joint; connect it to the accepted surrounding boundary; project/snap the patch to the source with a small controlled offset; inspect shrinkwrap errors; relax tangentially without shrinking the silhouette; test bending before merging the candidate into the accepted mesh. Keep the high source available for projection and bake detail. On fingers, lips and eyelids, inspect every loop termination.

For shoulders, use a flow that allows the upper arm to lift without pulling the entire chest. For elbows and knees, provide space for compression and extension instead of a single edge crease. Keep high-valence poles away from the most strongly bending region where possible. A face intended for speech needs deliberate lip and eyelid loops and an interior mouth, not simply a denser sphere.

An already licensed add-on can be used after version/API inspection and local verification. Do not automatically install Auto-Rig Pro or a commercial remesher. Missing paid tools are not grounds to fabricate successful retopology; provide a verified simpler candidate or identify the remaining modeling operation.

## UV acceptance

Preserve usable UVs unless there is a concrete defect. For the default single-tile workflow, check finite coordinates, nonzero face area, expected tile range, intentional versus accidental overlap, seam placement, island spacing and texel density. Hair cards and mirrored limbs may intentionally overlap, but that must be recorded, especially when asymmetric texturing or baking is requested.

The supplied UV task validates basic coordinates or creates a provisional Smart Project unwrap with approval. It does not prove absence of overlaps, good packing or coherent face UVs. For a production unwrap, define seams in low-visibility areas, unwrap connected semantic shells, match density deliberately, reserve additional face/hands detail when justified, then pack with a pixel-based margin at the final resolution.

Bake margin and island packing margin are different. Account for mipmapping: islands that are separated in a 4K view can bleed at distant mip levels. Test seams at intended texture resolutions and viewing distances. A checker texture reveals stretch; a UV wireframe on the baked image reveals cross-island contamination. UDIMs need a separate approved export strategy; the bundled basic UV gate assumes one tile.

Before final baking, choose a deterministic triangulation and split-normal setup. Keep an editable quad source separately. Tangent-space detail depends on geometry, UVs, vertex/corner normals and triangulation; a matching vertex count is not proof of matching shading basis. The audit's geometry/UV fingerprints are useful rejection signals, not a complete tangent-basis equivalence proof. Recheck custom normals and triangulation after a web roundtrip.

## High-to-low normal/AO baking

The official Blender baking model requires an active target image and an appropriate selected-to-active ray/cage setup. Use Blender's documented behavior for the installed version, not unverified tutorial numeric settings. [B3]

Create explicit object pairs such as `Body ← HIGH__Body`, `Coat ← HIGH__Coat` and `Boot ← HIGH__Boot`. Temporarily isolate unrelated geometry during each bake. A body ray must not pick up a nearby coat or the opposite leg just because they are visible in the scene. When one source contains all regions, use a reviewed segmentation/cage strategy rather than arbitrary name matching.

The helper bakes normal/AO images and an independent white-emission coverage diagnostic on a black target. It uses a scale-relative, finite ray distance; start with its conservative default and inspect. Do not copy a half-meter extrusion from the tutorial onto a 1.8-meter body or a centimeter-scale asset. Bigger distance can hide missing hits by hitting the wrong surface.

For a cage, duplicate the low mesh with identical connectivity and vertex correspondence, then move cage vertices outward locally without altering topology. Check eyelids, ears, fingers, coat seams and opposite limbs for cage intersections. The helper verifies basic cage topology. A small explicit cage can be more reliable than a universal distance when surfaces are tightly packed. Do not combine an unexamined cage with an enormous ray limit.

Normal baking should be tangent-space with the convention expected by the export pipeline. Base-color textures are color data; normal/AO/roughness/metal maps are non-color data. Save target images explicitly after baking. The helper's bake result creates texture files but does not automatically decide which material should use them; connect accepted maps in a subsequent material job.

Read the coverage image and statistics before judging the normal map. A flat blue normal texel is not automatically a miss. Conversely, high coverage does not prove the correct surface was hit. Inspect seams and thin regions from several lit views and compare to the source. Work at 512/1024 while correcting cages, then repeat at approved final resolution. Record resolution, margin, low/high hashes, cage and projection settings.

The supplied sampled coverage gate defaults to a maximum missed interior fraction of 0.005. This is an engineering starting threshold, not an aesthetic quality standard. Tiny islands and narrow defects may escape the sampling grid. An unexplained visible defect fails regardless of the numeric score. On repeated failure, change the projection or topology rather than lowering the threshold simply to pass.

## Material reconstruction

Keep original material assignments and repair missing texture paths or nodes individually. The tutorial's blanket material linking can assign skin to boots or erase different slots. Pink/magenta rendering can indicate missing images, but inspect the image path and graph before deciding the fix.

Use an explicit channel table. Base color and ordinary color emission images generally use sRGB. Tangent normal, roughness, metallic and occlusion data use non-color interpretation. In the glTF metallic-roughness layout, roughness occupies green and metallic blue; occlusion can occupy red in a shared texture when the intended export layout uses it. Preserve alpha separately and document whether it represents transparency or an unrelated mask. [B4, B5]

The provided `materials` task assigns maps and selected scalar settings to named existing materials, retaining the graph unless replacement is explicitly approved. It connects normal maps through a Normal Map node. It places AO in the exporter-recognized occlusion route rather than multiplying it into base color. An existing texture-driven roughness cannot be overwritten by a guessed constant without a deliberate graph edit.

When a destination requests an explicit ORM image, pack equal-size, UV-matched linear channel arrays into R=AO, G=roughness, B=metallic, A=1; missing AO can default to 1 and metallic to 0 only when those meanings are appropriate. Validate channel extraction after saving. This explicit packing operation is not a separate bundled task; Blender's exporter may construct its needed layout from supported graphs. Inspect the resulting GLB material/image references instead of claiming that a file named `orm.png` proves correct packing.

### Look-development defaults, not universal material truths

For nonmetals such as skin and ordinary fabric, start with metallic zero. Treat actual exposed metal as a separate material or mask rather than making the whole character slightly metallic. Vary roughness according to reference appearance; a uniform value of one can flatten all meaningful surface response. A dielectric IOR around the usual renderer default is a starting point, not a diagnosis; do not apply an unverified 1.1 globally to skin, glass, cloth and metal. [B5]

Skin may use restrained subsurface scattering in a physically sized scene. Its scale matters; evaluate ears and nose under backlighting without turning the face waxy. Keep the engine-compatible fallback distinct because glTF/engine support for advanced shading varies. Cloth should not become translucent plastic merely because skin settings were linked. Hair cards need appropriate alpha handling and sorting tests; solid stylized hair can use a simpler opaque material. Cornea/teeth/eyeball appearance requires separate consideration when present.

### Anti-Bleaching Color Management and Studio Lighting Protocol

A frequent failure mode in automated 3D rendering is "skin bleaching", where delicate melanin and facial tones are completely washed out into ghostly pale white.

1. **Color Management Transform**:
   - Never use standard legacy sRGB clipping for Cycles renders of skin.
   - Configure Blender's **AgX Color Management**:
     - `view_transform = 'AgX'`
     - `look = 'AgX - Medium High Contrast'`
   - AgX provides logarithmic highlight rolloff that preserves skin hue and saturation under strong illumination without harsh clipping.

2. **Calibrated Studio Area Lighting**:
   - Point lights placed within 1m of a face concentrate extreme radiant flux into tiny specular hot spots.
   - Use calibrated 3-point **Area Lights** scaled relative to the subject:
     - **Key Area Light**: 15–20W, size 0.5–0.8m, placed at 45° azimuth and +30° elevation.
     - **Fill Area Light**: 8–10W, size 0.6–1.0m, placed on the opposite side to soften shadows without flattening form.
     - **Rim / Accent Area Light**: 20–25W, size 0.4–0.6m, placed behind and above the head to cleanly separate hair and shoulders from the background.

3. **Physically Realistic Skin BSDF Parameters**:
   - Skin is dielectric: set `Metallic = 0.0`.
   - Set `Roughness = 0.50 – 0.55` (a roughness of 0.1–0.2 produces unnatural plastic shine; 1.0 produces chalky deadness).
   - Set `Specular IOR Level = 0.30` (equivalent to standard skin refractive index $n \approx 1.40 - 1.45$).

Never use material adjustments to hide bad geometry. Show neutral before/after views first, then final lighting. For export preview, avoid relying on Blender-only features that are absent in the target shader.

