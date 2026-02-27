
from slider.curve import Curve, Perfect
from slider.position import Position
from slider import Beatmap, Slider
import math

Arc = dict[str, float | tuple[float, float]]
Vector2D = tuple[float, float]

CirclePresets = [
    (0.4993379862754501, [(1.0, 0.0), (1.0, 0.2549893626632736), (0.8778997558480327, 0.47884446188920726)]),
    (1.7579419829169447, [(1.0, 0.0), (1.0, 0.6263026), (0.42931178, 1.0990661), (-0.18605515, 0.9825393)]),
    (3.1385246920140215, [(1.0, 0.0), (1.0, 0.87084764), (0.002304826, 1.5033062), (-0.9973236, 0.8739115), (-0.9999953, 0.0030679568)]),
    (5.69720464620727, [(1.0, 0.0), (1.0, 1.4137783), (-1.4305235, 2.0779421), (-2.3410065, -0.94017583), (0.05132711, -1.7309346), (0.8331702, -0.5530167)]),
    (2 * math.pi, [(1.0, 0.0), (1.0, 1.2447058), (-0.8526471, 2.118367), (-2.6211002, 7.854936e-06), (-0.8526448, -2.118357), (1.0, -1.2447058), (1.0, -2.4492937e-16)]),
]

def process_perfect_curves(content: str) -> str | None:
    beatmap = Beatmap.parse(content)
    hit_objects = list(beatmap.hit_objects(stacking=False))
    updated_indexes: dict[int, str] = {}

    for index, hit_object in enumerate(hit_objects):
        if not isinstance(hit_object, Slider):
            continue

        if not isinstance(hit_object.curve, Perfect):
            continue

        points = [(point.x, point.y) for point in hit_object.curve.points]
        if len(points) != 3:
            continue

        start_point, middle_point, end_point = points
        if start_point == middle_point or middle_point == end_point:
            continue

        arc = calculate_circle_properties(start_point, middle_point, end_point)
        if arc is None:
            continue

        bezier_points = approximate_circle_with_bezier(arc)
        bezier_positions = [
            Position(round(point[0]), round(point[1]))
            for point in bezier_points
        ]

        hit_object.curve = Curve.from_kind_and_points(
            "B",
            bezier_positions,
            hit_object.length,
        )
        updated_indexes[index] = hit_object.pack()

    if not updated_indexes:
        return None

    # TODO: Directly modify the hit objects instead of replacing lines
    return replace_updated_hitobject_lines(content, updated_indexes)

def replace_updated_hitobject_lines(content: str, updated_indexes: dict[int, str]) -> str:
    lines = content.splitlines()
    new_lines: list[str] = []
    in_hitobjects = False
    hitobject_index = 0

    for line in lines:
        stripped = line.strip()

        if stripped == "[HitObjects]":
            in_hitobjects = True
            new_lines.append(line)
            continue

        if not in_hitobjects:
            new_lines.append(line)
            continue

        if not stripped or stripped.startswith("//"):
            new_lines.append(line)
            continue

        new_lines.append(updated_indexes.get(hitobject_index, line))
        hitobject_index += 1

    return "\n".join(new_lines)

def calculate_circle_properties(
    point_a: Vector2D,
    point_b: Vector2D,
    point_c: Vector2D,
) -> Arc | None:
    determinant = 2 * (
        point_a[0] * (point_b[1] - point_c[1])
        + point_b[0] * (point_c[1] - point_a[1])
        + point_c[0] * (point_a[1] - point_b[1])
    )
    if abs(determinant) < 1e-10:
        return None

    a_sq = _vec_len_sq(point_a)
    b_sq = _vec_len_sq(point_b)
    c_sq = _vec_len_sq(point_c)

    center_x = (
        a_sq * (point_b[1] - point_c[1])
        + b_sq * (point_c[1] - point_a[1])
        + c_sq * (point_a[1] - point_b[1])
    ) / determinant
    center_y = (
        a_sq * (point_c[0] - point_b[0])
        + b_sq * (point_a[0] - point_c[0])
        + c_sq * (point_b[0] - point_a[0])
    ) / determinant

    center = (center_x, center_y)
    delta_a = _vec_sub(point_a, center)
    delta_c = _vec_sub(point_c, center)

    radius = _vec_len(delta_a)
    theta_start = math.atan2(delta_a[1], delta_a[0])
    theta_end = math.atan2(delta_c[1], delta_c[0])

    while theta_end < theta_start:
        theta_end += 2 * math.pi

    direction = 1
    theta_range = theta_end - theta_start

    ortho_ac = (point_c[1] - point_a[1], point_a[0] - point_c[0])
    if _vec_dot(ortho_ac, _vec_sub(point_b, point_a)) < 0:
        direction = -1
        theta_range = 2 * math.pi - theta_range

    return {
        'center': center,
        'radius': radius,
        'theta_start': theta_start,
        'theta_range': theta_range,
        'direction': direction,
    }

def approximate_circle_with_bezier(arc: Arc) -> list[Vector2D]:
    preset_arc_length, preset_points = next(
        (preset for preset in CirclePresets if preset[0] >= arc['theta_range']),
        CirclePresets[-1],
    )

    bezier_arc = list(preset_points)
    curve_order = len(bezier_arc) - 1
    interpolation_factor = arc['theta_range'] / preset_arc_length

    for order in range(curve_order):
        for index in range(curve_order, order, -1):
            bezier_arc[index] = _vec_add(
                _vec_scale(bezier_arc[index], interpolation_factor),
                _vec_scale(bezier_arc[index - 1], 1 - interpolation_factor),
            )

    final_points: list[tuple[float, float]] = []
    cos_start = math.cos(arc['theta_start'])
    sin_start = math.sin(arc['theta_start'])

    for point in bezier_arc:
        scaled = _vec_scale(point, arc['radius'])
        if arc['direction'] < 0:
            scaled = (scaled[0], -scaled[1])

        rotated = (
            scaled[0] * cos_start - scaled[1] * sin_start,
            scaled[0] * sin_start + scaled[1] * cos_start,
        )
        final_points.append(_vec_add(rotated, arc['center']))

    return final_points

def _vec_sub(lhs: Vector2D, rhs: Vector2D) -> Vector2D:
    return lhs[0] - rhs[0], lhs[1] - rhs[1]

def _vec_add(lhs: Vector2D, rhs: Vector2D) -> Vector2D:
    return lhs[0] + rhs[0], lhs[1] + rhs[1]

def _vec_scale(vector: Vector2D, scale: float) -> Vector2D:
    return vector[0] * scale, vector[1] * scale

def _vec_len_sq(vector: Vector2D) -> float:
    return vector[0] ** 2 + vector[1] ** 2

def _vec_len(vector: Vector2D) -> float:
    return math.sqrt(_vec_len_sq(vector))

def _vec_dot(lhs: Vector2D, rhs: Vector2D) -> float:
    return lhs[0] * rhs[0] + lhs[1] * rhs[1]
