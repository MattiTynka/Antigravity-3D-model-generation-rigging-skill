# Rigging, animation and motion acceptance

## Rig route selection

Use the least destructive route compatible with the actual character:

| Situation | Preferred route | Important boundary |
|---|---|---|
| Download already includes a plausible skeleton | Inspect/reuse the rig and test poses | Do not add another skeleton merely to match the tutorial |
| Conventional unrigged humanoid and an approved additional service | Test Mixamo auto-rig, then inspect locally | New upload destination needs consent; not a solution for arbitrary creatures |
| Local-only body rig or nonstandard proportions | Fit explicit landmarks and use the included deform-rig helper | Coordinates must come from the actual mesh, not a generic height formula |
| Blender animator needs editable controls | Fit a metarig, then generate a Rigify control rig and bake its deform bones for export | Rigify's generation is not automatic landmark detection |
| Wings, tail, quadruped or unusual anatomy | Custom approved hierarchy and validation poses | Standard humanoid motion will not automatically animate extra anatomy |
| Speech/close-up expressions required | Dedicated facial topology and morph/bone workflow | Body auto-rigging does not supply a usable face rig |

Mixamo's official FAQ describes humanoid constraints and royalty-free use of characters/animations in incorporated projects; it does not justify treating every standalone motion redistribution as permitted. Rigify documentation requires correct metarig placement. Check current service/add-on terms and installed versions. [R1–R3]

## 1. Pre-rig mesh review

Freeze accepted geometry, UVs, materials and unit convention. Check that shoulders, hips, elbows, knees, wrists and ankles have enough deformation topology. Separate fingers if individual movement is required. Identify rigid attachments, deforming clothing, eyes, teeth and hair. Remove nothing merely to simplify binding; use a body proxy when a complex outfit confuses weights.

A body proxy is a simpler, anatomically aligned surface used to compute weights, not a visible replacement. The proxy must match the intended body and remain clear of nearby limbs. Transfer weights by reviewed surface correspondence, then test the visible clothing. A nearest-surface transfer across touching legs or fingers can produce wrong influences and must be corrected.

Do not change topology after morph targets exist without explicitly rebuilding them. Do not apply an armature modifier merely to remove an error message: that can bake one pose and destroy the intended reusable rig.

## 2. Fit joints with calibrated images

Use the headless preview outputs and `cameras.json` to generate front, side and oblique views in known world coordinates. The agent examines the actual images and proposes joint centers: pelvis, spine/chest, neck/head, shoulders, elbows, wrists, hips, knees, ankles, ball/toe and any fingers or appendages required. A 2D outline is not the location of the joint center; check depth in another view.

For an orthographic view with square output, normalized pixel coordinates `u,v` measured from the image's top-left, camera orthographic scale `s` and camera world matrix `C`, the view ray can be written as:

`origin = C × ((u − 0.5)s, (0.5 − v)s, 0, 1)`

`direction = C.rotation × (0, 0, −1)`

Intersect or least-squares-fit rays from two or more calibrated views. The formula must be adapted for non-square aspect ratio and any image crop; never triangulate from screenshots with unknown framing. Reject large ray residuals. Constrain the proposed joint to an anatomically plausible location within the relevant mesh cross-section, not just its surface. Use the rendered camera matrices rather than assuming the model is centered or exactly 1.8 meters tall.

Write explicit joint/bone coordinates in a candidate skeleton JSON. Render a skeleton overlay with bone names against the model from at least front and side. Joint fitting and overlay generation are agent modeling operations, not an automatic pose-estimation model shipped in this bundle. The agent may generate the overlay headlessly with temporary curve/cylinder bones in a separate render scene, never modifying the accepted mesh.

Approve the fit only after checking shoulder depth, elbow/knee bend planes, wrist location, finger knuckles, neck attachment and hip width. Store the exact input mesh hash and skeleton JSON hash in the approval. If the user delegated these reviews, identify the agent reviewer and preserve the evidence rather than falsely saying “user approved.”

## 3. Hierarchy, roll and binding

Use a stable, documented bone map. A typical deform hierarchy is nondeforming `root` → pelvis/hips → spine/chest → neck/head; left/right clavicles and arm chains from the upper torso; leg chains from hips; optional finger chains from each hand. Choose either `.L/.R` or another consistent naming convention. External source names remain in an explicit mapping; name similarity is not proof of correspondence.

Head/tail coordinates use the prepared scene's world convention. In the bundled local rig the armature is created at identity, so these are also armature-space coordinates. `roll` is radians. Connected bones must share a head/tail joint exactly within the helper tolerance. The validation rejects zero-length bones, duplicate names, absent parents and cycles.

Leave a slight anatomically appropriate bend where it helps define knee/elbow directions; do not distort a supplied rest mesh into a different pose without a reviewed transformation. Bone roll determines local twist/bend axes and must be tested. Do not assign the same Euler-axis instruction to every left/right bone and assume both sides will bend correctly.

The `rig` helper creates a basic deform armature and uses automatic weights. It is not a Rigify control rig. Explicit `rigid_objects` mapping gives a named object full influence from a suitable deform bone. For mixed rigid/deforming meshes, separate the intended regions or use reviewed weight assignments; do not bind the entire outfit to the pelvis.

Weights are pruned and normalized to the configured influence limit. The default four influences is a practical target choice, not a universal limit. Unweighted vertices fail rather than being guessed onto the nearest bone. A numeric pass still requires pose checks: wrong-but-normalized weights are common.

## 4. Correct weights locally

Inspect a heat/weight visualization for the affected bone group, plus the posed surface. Separate the cause: incorrectly placed joint, bad topology, wrong weight region, too many layers influencing each other or unsupported rigid attachment. Fix anatomy and topology before repeatedly smoothing weights.

For a bounded weight correction, select the exact vertex region, lock unrelated accepted groups, remove impossible influences, interpolate plausible neighboring weights, normalize/prune, then replay the same failed pose. Preserve a copy of the original weights and a before/after report. For fingers, keep neighboring finger chains isolated except at the palm transition. For shoulders, distribute motion across clavicle/upper arm and nearby torso as appropriate; do not assign the whole shoulder to one rigid upper-arm group.

A useful validation sequence is rest; arm lift to roughly shoulder level and above; elbow bend; forearm twist; wrist flexion; knee bend; squat; ankle flexion; neck turn; fist/open hand; and appendage extremes when present. Angles depend on character design. Avoid imposing extreme human anatomy on a stylized creature. Render front/side/oblique samples and watch for collapses, exploding vertices, chest dragging, leg cross-influences and cloth intersections.

Corrective shapes or twist bones can improve difficult bends, but verify export support. Blender's preserve-volume deformation can look different from the target's linear-blend skinning; review with the target-equivalent setting instead of approving an effect the export cannot reproduce. Keep technical control bones separate from the final deform skeleton.

## 5. Mixamo route with material preservation

Only after upload approval, use the already prepared neutral humanoid export. Follow observed upload/marker instructions. Place markers from actual anatomy, not a generic screen-coordinate template. Preview the auto-rig with several bends before download. Save each accepted rig/clip locally because a service project/history is not a durable asset archive.

Import FBX using the documented units and axes, with automatic bone reorientation disabled by default in the helper. Inspect the new hierarchy/rest pose and compare the mesh to the pre-rig checkpoint. Repair materials by preserving the old material table and matching actual object/slot correspondence. Never blanket-link one material onto every pink object.

Prefer one accepted skeleton reused for its animation downloads. A motion-only file still needs source-rig identity and mapping checks. A file containing a second skinned character must not be accidentally included in the final export. Save source motion files with licensing metadata.

## 6. Rigify and already-installed add-ons

Use Rigify when an animator needs IK/FK controls in Blender. Verify it is installed/available, add the correct metarig, fit it to the reviewed landmarks, inspect roll and face/finger components, then generate controls. Preserve the metarig and generated rig in an editable master. Bake the deform skeleton's evaluated motion into a clean export rig when needed. Do not export a forest of control bones and constraints and assume every engine will reproduce them. [R2–R3]

For an already licensed Auto-Rig Pro or another add-on, inspect its current documented headless operations and version; do not invent operator names or set unknown properties. Such integrations are optional adapters, not bundled or tested by this package. A tool failure does not authorize installing unreviewed scripts or bypassing a license.

## 7. Local animation and calibrated retargeting

The bundled `animate` task consumes explicit local-space pose keys, creating a new active action with rest keys for unspecified bones. It is useful for validation and an authored simple idle. It does not turn a two-key bend into a natural walk. It refuses constrained bones; use a control-rig bake path for those.

The bundled `retarget` task transfers rest-space rotation deltas through an explicit target-to-source bone map and reviewed coordinate alignment. It preserves target segment lengths, resamples using the declared source FPS and optionally transfers scaled translation. It is a baseline FK transfer, **not** a universal IK/contact solver. It has no automatic twist distribution, foot locking, root-yaw extraction or facial semantic mapping.

Choose a short representative source interval first. Calibrate T/A pose differences, shoulder orientation, hand axes, knee direction, source/target armature transforms and translation scale. The source FPS must come from the source metadata or intended timing; an FBX import does not always make scene FPS unambiguous. A correct duration is as important as a correct frame count.

For more complex rest poses, fit a source rest-pose correction or use a verified retargeting tool. Do not compensate for a 90-degree axis mismatch by arbitrarily rotating random bones until one frame looks correct. Save the alignment and mapping as hashed inputs and render the calibration pose.

## 8. Contacts, root motion and loop repair

Identify foot-contact intervals from the intended motion and inspect the foot world positions over time. During stance, compare horizontal drift and height relative to the ground. Suggested starting diagnostics are drift below about one percent of body height and small, intentional ground penetration only; adapt to the animation style and target. These contact measurements are **not** included in the generic QA script, so the agent must calculate them explicitly for walk/run acceptance.

To correct contact locally, set a foot target during the stance interval; solve a two-bone leg chain or use a verified IK control; adjust pelvis height to avoid impossible leg extension; blend target influence at contact boundaries; bake the result to deform bones; remove runtime-only constraints from the export candidate; then recheck knees, foot roll and root motion. This is a recipe for a focused tested Blender operation, not a claim the baseline retarget helper already solves it.

Decide whether the exported clip carries translation, is in-place, or supplies a separate root-motion track. Do not encode the same horizontal travel on both root and hips. The bundled in-place option removes horizontal transferred translation; it does not automatically extract root yaw. Preserve turns when they are part of the clip, or create a separate reviewed yaw policy.

For a loop, compare first/last bone rotations using quaternion angle, positions relative to root, foot phase and velocity. Quaternion sign changes do not necessarily indicate different orientations. Matching endpoints alone can still leave a speed discontinuity. Use a controlled blend or periodic motion correction, then evaluate the seam in playback. Store whether the terminal duplicate frame is present; different destination workflows expect different sampling conventions.

## 9. Actions, NLA and clip export

Every clip gets a stable name, source, license, source/target skeleton hashes, FPS, start/end, duration, loop flag and root-motion policy. Keep validation actions separate from deliverable clips. The helpers replace the active action when creating a new candidate; preserve earlier clips in their checkpoint files instead of assuming they will be auto-assembled.

The default exporter uses `ACTIVE_ACTIONS` to avoid broadcasting stale compatible actions. For several deliverable clips, intentionally assemble the approved actions into an inspected master, create separate named NLA tracks/strips or use a documented action selection mode, set `animation_mode` appropriately, and verify the exported animation list against the manifest. Blender 4.5's exporter defines distinct active-action, action and NLA modes. [B6]

If multi-clip assembly is not performed, deliver separate tested GLBs per clip and a clearly labeled master rather than claiming one GLB contains every requested action. The optional FBX route defaults to the active clip and requires its own reimport/playback test. Constraints and drivers should be baked before a game export unless the target explicitly supports them.

## 10. Face and secondary motion: Authentic Duchenne Smile Biomechanics

Facial rigging and expression animation require strict adherence to human facial biomechanics. An isolated mouth corner pull produces a fake, cartoonish, or grimacing expression. A genuine human smile is a **Duchenne smile**, requiring synchronous coordination across multiple facial regions:

### Anatomical Subsystems of the Duchenne Smile

1. **Zygomaticus Major (Mouth Curvature & Elevation)**:
   - **Continuous Parabolic Arc**: In natural smiles, the entire upper and lower lip line flexes upward according to a power-law curvature rather than independent, piecewise linear vertex pulls:
     $$\Delta z(x) = \Delta z_{\text{corner}} \cdot \left(\frac{|x|}{x_{\text{corner}}}\right)^{1.8}$$
     with 3D Gaussian falloffs along $Y$ (depth) and $Z$ (height). This completely prevents the "mustache dip" (where mouth corners lift but the philtrum sags) and eliminates boundary tearing.
   - **Vector Displacements**: Mouth corners elevate upward ($dZ \approx +0.026\text{ m}$ on a 1.8m figure), flare slightly outward ($dX \approx \pm 0.010\text{ m}$), and recess slightly posteriorly into the buccinator space ($dY \approx +0.008\text{ m}$).

2. **Malar Fat Pads (Cheek Bunching)**:
   - Cheeks do not remain stationary during a smile; the malar fat pads elevate upward ($dZ \approx +0.018\text{ m}$), slightly forward ($dY \approx -0.007\text{ m}$), and outward ($dX \approx \pm 0.005\text{ m}$).
   - This creates natural soft tissue bunching beneath the infraorbital margin.

3. **Orbicularis Oculi (Smiling Eyes / Lower Eyelid Squint)**:
   - **Lower Eyelid Elevation**: The infraorbital skin and lower eyelids push upward ($dZ \approx +0.014\text{ m}$) and slightly forward ($dY \approx -0.005\text{ m}$), narrowing the vertical eye aperture.
   - **Lateral Canthi / Crow's Feet**: The outer eye corners elevate ($dZ \approx +0.008\text{ m}$) and compress slightly inward ($dX \approx \mp 0.004\text{ m}$).
   - **Outer Brow Relaxation**: Outer eyebrows relax slightly downward ($dZ \approx -0.004\text{ m}$), releasing tension and communicating warmth.

### Dual Facial Rigging Architecture (Bones + Shape Keys)

- **Armature Hierarchy**:
  - `Bone_Head`: Parent bone for the cranium.
  - `Bone_Jaw`: Connected to `Bone_Head` with pivot near the temporomandibular joint (TMJ).
  - `Bone_LipCorner_L` / `Bone_LipCorner_R`: Deform bones for the modiolus / lip corners.
  - `Bone_Cheek_L` / `Bone_Cheek_R`: Deform bones for the zygomatic / malar fat pads.
- **Morph Targets / Shape Keys**:
  - `Basis`: Neutral resting expression (relaxed mouth, forward gaze).
  - `Smile`: Full Duchenne composite expression applying the mathematical falloff fields.
  - Additional isolated morphs when required: `Smile_Eyes`, `Cheek_Puff`, `Jaw_Open`.
- **60-Frame Expression Schedule (@ 30 fps)**:
  - **Frame 01 (Value 0.00)**: Neutral resting expression.
  - **Frame 15 (Value 0.45)**: Smooth natural smile onset.
  - **Frame 30 (Value 1.00)**: Peak radiant Duchenne smile.
  - **Frame 45 (Value 1.00)**: Warm expressive hold.
  - **Frame 60 (Value 0.10)**: Gentle settling into a subtle, relaxed pleasant resting expression.

For hair, coat tails, wings and other appendages, use explicit bones and authored/retargeted secondary motion or a carefully baked simulation. Do not remove them to make a humanoid pipeline pass. Simulated cloth and hair are not automatically portable through skeletal GLB; bake to a supported representation or provide a clear target limitation.

