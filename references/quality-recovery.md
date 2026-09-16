# Acceptance, recovery, privacy and truthful completion

## Quality policy

Defaults are starting engineering limits for a modest real-time character, not published industry requirements. Read the target's real limits and revise the project policy deliberately. The helper's configuration values are per job; it does not automatically merge every value from `project.json` into Blender jobs. Copy the approved relevant settings into each job.

| Check | Default decision | Implementation |
|---|---|---|
| Non-finite geometry/weights | Fail | Mechanical checks |
| Degenerate faces or invalid basic single-tile UVs | Fail | Mechanical checks |
| Non-boundary non-manifold edges | Fail unless redesigned/explicitly reviewed | Mechanical checks; no automatic repair |
| Open surface boundaries | Review, not automatic failure | Clothing and cards may be intentionally open |
| Triangle budget | 80,000 default | Per-job configurable, not a service quota |
| Deform weights | No unweighted vertices; sum near one; maximum four influences | Helper default tolerance 0.0001 |
| Bake missing sampled texels | Fail above 0.005 interior fraction | Does not detect wrong-surface hits or every tiny island |
| Deformation stretch | Gross edge stretch above 5 is flagged | Coarse sampled heuristic, not proof of good deformation |
| UV overlap/stretch and custom normals | Explicit review | Not fully checked by helper |
| Identity, anatomy, seams, deformation | Render-based review | Required before acceptance |
| Foot contacts and loop continuity | Clip-specific numerical and visual review | Not supplied by the generic QA task |
| Export | Reimport plus target-specific playback | Helper tests GLB structure; target/FBX checks are additional |

Visual pass evidence must name the image/video, frame/view, compared reference and observed result. A review cannot be reduced to “looks good” without opening the artifacts. Keep beauty renders separate from diagnostic lighting. For the final target-compatibility item, distinguish actual engine playback from Blender-only preview.

## Approval records and their limits

Approval files contain status, reviewer, reason, scopes and the exact input SHA-256. Skeleton approvals additionally hash the skeleton JSON; retarget approvals hash the mapping and source motion. Release approvals include visual check names and must match the mechanical QA input. These are audit records, not tamper-proof human authentication. This is not an OS sandbox or a cryptographic human-approval system. A coding agent can technically edit JSON; the skill therefore explicitly forbids inventing permission or approving its own edits outside a user-delegated scope.

Use one scope per decision when practical: `geometry`, `uv_rebuild`, `retopology`, `materials_replace`, `skeleton`, `retarget`, `release`. A prior mesh approval does not grant permission to publish it. A previously approved budget does not permit purchasing additional credits. A release review becomes stale when the source asset changes.

Never turn a failed check into a pass by deleting the report, loosening thresholds without justification, renaming a candidate “final,” or claiming a human approved an unseen render. The helper will refuse several stale records, but the broader workflow relies on the agent following these rules.

## Retry rules

| Failure | Safe response |
|---|---|
| No attached target tab | Inspect authorized browser connection; report a specific access gap |
| Login, CAPTCHA, approval dialog | Pause the affected operation for the user; no bypass or credential extraction |
| Generation cost unknown or exceeds remaining budget | Do not submit; retain current project and request a bounded decision |
| Generation timed out/disconnected | Check the same recorded job/history first; no automatic resubmission |
| New quota/privacy/terms notice | Stop the relevant action and re-establish authorization |
| Download is temporary, HTML or incomplete | Wait/reauthenticate as appropriate; never import it as a valid model |
| Import changed topology or UVs | Reject change or adopt a new version and invalidate downstream bakes |
| Bake missing/wrong hits | Inspect coverage, cage, pairs and thin surfaces; retry only after a changed cause |
| Automatic weights fail | Diagnose geometry/proxy/rigid attachments; never attach unweighted regions randomly |
| Foot slide or joint twist | Recalibrate, apply targeted contact/roll corrections and revalidate |
| Blender operator mismatch | Record build/version and unsupported property; inspect official current API and adapt a tested branch |
| Crashed local run | Keep run files/logs; mark failed/abandoned and start a new immutable run |
| Export loses actions/textures | Inspect graph/action selection, clean scene, re-export and repeat reimport |

As a default, allow at most two substantive attempts per isolated repair before rethinking the approach. This is independent of the paid generation cap. A failed generation reservation remains reserved until the user/account evidence justifies a manual adjustment; do not assume automatic refunds. Never submit concurrent browser jobs from multiple agents into the same project.

## Idempotency and resumption

The Node coordinator locks a workspace for local state changes, hashes declared file dependencies and helper/runtime identity, and writes unique run directories. A completed run is reused only while recorded outputs still hash-match. This is not full reproducible-build isolation: undeclared external resources, mutable add-ons, hardware and filesystem changes still matter. Use packed `.blend` inputs and declare extra dependencies explicitly.

The helper rejects symlink/traversal paths. It runs Blender without shell interpolation or automatic script execution. Run one workspace writer at a time. Before removing a stale lock, inspect its PID, check whether Blender or a generation is still running and preserve the lock contents in recovery evidence. Do not delete the lock while a valid process owns it. A killed parent process may require checking for remaining child processes on the local OS.

After a partial crash, inspect `state.json`, the latest request, log and report. A residual `RUNNING` record after a hard process kill is not proof of an active job; compare process state and mark it abandoned with an evidence event. Do not modify an old output file to repair a failed run. Use a new job/input version.

Write `NEXT_ACTION.md` after every accepted stage and before a context handoff. Include character/target, current stage, latest accepted input path/hash, important browser project/job IDs, last completed local run, unresolved defect, remaining budget, pending approval and the next exact safe action. Exclude tokens, cookies and credentials. The next agent verifies these records instead of restarting the pipeline and charging for duplicate generations.

## Privacy and provenance

Collect only task assets. Do not scan unrelated Chrome tabs, emails, folders or account history. Screenshots should avoid unrelated personal information; crop/sanitize evidence as needed. Never log session storage or attach full browser profiles to the asset archive.

Record source image/mesh/motion rights and consent for recognizable people. An AI-generated derivative is not automatically free of source rights. Check service terms for the actual plan/date, private versus public handling, training use, commercial use, and redistribution. Hunyuan's web-service terms are not interchangeable with an open-source model license. Mixamo incorporation rights are not a blanket standalone motion-redistribution license. This is a rights-verification workflow, not legal advice. [H2, R1, M10]

The authored helper code is licensed separately from any generated asset. No third-party files are bundled. Avoid reference sets built from protected characters, artists' work or real-person photos without an appropriate basis. When provenance is unresolved, deliver the technical candidate with a conspicuous rights limitation rather than claiming commercial clearance.

## Outcome labels

`VERIFIED_FOR_TARGET`: all requested stages, exact-file mechanical QA, visual reviews, license/provenance checks and actual target playback completed with evidence.

`CANDIDATE`: usable intermediate/export with precisely listed unverified target or quality items. A Blender-only GLB roundtrip normally remains a candidate for an untested engine.

`BLOCKED`: a specific missing capability, input, permission or prerequisite prevents the next stage. Include completed safe work and the smallest next action.

`INCOMPLETE`: one or more requested outputs remain unproduced or unverified. List them without implying background work will finish later.

A helper's `COMPLETED` means only that its bounded subprocess reported success. It never substitutes for these asset outcome labels.
