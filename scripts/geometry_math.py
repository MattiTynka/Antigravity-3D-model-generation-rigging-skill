# NEW: pure deterministic geometry and skeleton validation, no Blender dependency.
from __future__ import annotations
import hashlib
import json
import math
from typing import Iterable


def normalized_weights(weights: Iterable[tuple[str, float]], limit: int = 4) -> list[tuple[str, float]]:
    if not isinstance(limit, int) or limit < 1:
        raise ValueError('Influence limit must be a positive integer')
    totals: dict[str, float] = {}
    for name, weight in weights:
        if not math.isfinite(weight) or weight < 0:
            raise ValueError('Non-finite or negative skinning weight')
        if weight > 0:
            totals[name] = totals.get(name, 0.0) + weight
    best = sorted(totals.items(), key=lambda item: (-item[1], item[0]))[:limit]
    total = sum(weight for _, weight in best)
    return [(name, weight / total) for name, weight in best] if total > 0 else []


def validate_bones(bones: list[dict]) -> list[dict]:
    if not bones:
        raise ValueError('No approved skeleton landmarks supplied')
    by_name: dict[str, dict] = {}
    for bone in bones:
        name = bone.get('name')
        if not isinstance(name, str) or not name or name in by_name:
            raise ValueError('Bone names must be unique nonempty strings')
        for key in ('head', 'tail'):
            point = bone.get(key)
            if not isinstance(point, list) or len(point) != 3 or not all(isinstance(n, (int, float)) and math.isfinite(n) for n in point):
                raise ValueError(f'{name}: invalid {key}')
        if math.dist(bone['head'], bone['tail']) < 1e-7:
            raise ValueError(f'{name}: zero length bone')
        if not math.isfinite(bone.get('roll', 0)):
            raise ValueError('Invalid bone roll')
        by_name[name] = bone
    output: list[dict] = []
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(name: str) -> None:
        if name in visiting:
            raise ValueError('Cyclic bone hierarchy')
        if name in visited:
            return
        if name not in by_name:
            raise ValueError(f'Unknown parent bone: {name}')
        visiting.add(name)
        parent = by_name[name].get('parent')
        if parent is not None:
            visit(parent)
        visiting.remove(name)
        visited.add(name)
        output.append(by_name[name])
    for name in by_name:
        visit(name)
    return output


def triangle_uv_area(points: list[tuple[float, float]]) -> float:
    a, b, c = points
    return abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])) / 2


def surface_fingerprint(triangles: Iterable[Iterable[Iterable[float]]], precision: int = 6) -> str:
    canonical = []
    for triangle in triangles:
        corners = [tuple(round(float(x), precision) for x in corner) for corner in triangle]
        if len(corners) != 3 or not all(math.isfinite(x) for corner in corners for x in corner):
            raise ValueError('Invalid surface triangle')
        rotations = [tuple(corners[n:] + corners[:n]) for n in range(3)]
        canonical.append(min(rotations))
    return hashlib.sha256(json.dumps(sorted(canonical), separators=(',', ':')).encode()).hexdigest()


def gaussian_falloff(distance: float, sigma: float) -> float:
    """Calculates smooth C-infinity Gaussian falloff for anatomical organic skin deformation."""
    if not math.isfinite(distance) or not math.isfinite(sigma) or sigma <= 0:
        raise ValueError('Invalid distance or sigma for gaussian falloff')
    return math.exp(- (distance * distance) / (2.0 * sigma * sigma))


def parabolic_arc_weight(x: float, corner_x: float, power: float = 1.8) -> float:
    """Calculates continuous parabolic curvature factor for natural human smile arcs without center dips."""
    if not math.isfinite(x) or not math.isfinite(corner_x) or abs(corner_x) < 1e-7:
        raise ValueError('Invalid coordinates for parabolic smile arc')
    norm_x = min(1.0, abs(x) / abs(corner_x))
    return norm_x ** power

