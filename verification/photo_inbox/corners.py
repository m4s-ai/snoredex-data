"""Suggest card corners in an owner photo, without a trained model (#655, #657).

Long straight edges (Hough lines) are paired into quads of the card's 63 : 88 shape; every side must
lie on edges for most of its length, and of nested quads (the artwork frame and text box are
card-shaped too) the outermost is the card. Measured in #655: within about 1 % of the card width for
one card on a dark backdrop; two cards side by side or a busy background need the owner's choice,
so the inbox offers every candidate and the owner approves or drags the corners.
"""

import itertools

SIZE = 1200          # the long side the search runs at
CARD_RATIO = 63 / 88
RATIO_TOLERANCE = 0.05
LINES = 24           # longest merged lines kept per direction
MIN_SUPPORT = 0.7    # mean share of each side on an edge
MIN_SIDE = 0.4       # the weakest side: the stand may hide part of the bottom edge


def merged(lines, vertical):
    """Collinear segments as one line each, longest first."""
    import cv2
    import numpy as np

    groups = []
    for x1, y1, x2, y2 in lines:
        mid = (x1 + x2) / 2 if vertical else (y1 + y2) / 2
        group = next((g for g in groups if abs(g["mid"] - mid) < 8), None)
        if group is None:
            group = {"mid": mid, "pts": [], "len": 0.0}
            groups.append(group)
        group["pts"] += [(x1, y1), (x2, y2)]
        group["len"] += float(np.hypot(x2 - x1, y2 - y1))
    out = []
    for group in sorted(groups, key=lambda g: -g["len"])[:LINES]:
        vx, vy, x0, y0 = cv2.fitLine(np.array(group["pts"], np.float32), cv2.DIST_L2, 0, 0.01, 0.01).ravel()
        out.append({"p": np.array([x0, y0]), "d": np.array([vx, vy]), "mid": group["mid"]})
    return out


def crossing(a, b):
    import numpy as np

    matrix = np.array([a["d"], -b["d"]]).T
    if abs(np.linalg.det(matrix)) < 1e-6:
        return None
    return a["p"] + np.linalg.solve(matrix, b["p"] - a["p"])[0] * a["d"]


def support(near, quad):
    """Mean share of the four sides on an edge, 0 when one side is weak; corners are skipped (rounded)."""
    import numpy as np

    t = np.linspace(0.1, 0.9, 120)[:, None]
    sides = []
    for a, b in zip(quad, quad[1:] + quad[:1]):
        points = (a + t * (b - a)).round().astype(int)
        if (points < 0).any() or (points[:, 0] >= near.shape[1]).any() or (points[:, 1] >= near.shape[0]).any():
            return 0.0
        sides.append(float(near[points[:, 1], points[:, 0]].mean()))
    return float(np.mean(sides)) if min(sides) >= MIN_SIDE else 0.0


def card_quads(vertical, horizontal, near):
    import numpy as np

    for left, right in itertools.combinations(sorted(vertical, key=lambda g: g["mid"]), 2):
        if right["mid"] - left["mid"] < SIZE * 0.08:
            continue
        for top, bottom in itertools.combinations(sorted(horizontal, key=lambda g: g["mid"]), 2):
            quad = [crossing(left, top), crossing(right, top), crossing(right, bottom), crossing(left, bottom)]
            if any(q is None for q in quad):
                continue
            width = (np.linalg.norm(quad[1] - quad[0]) + np.linalg.norm(quad[2] - quad[3])) / 2
            height = (np.linalg.norm(quad[3] - quad[0]) + np.linalg.norm(quad[2] - quad[1])) / 2
            if height > 0 and abs(width / height - CARD_RATIO) <= RATIO_TOLERANCE and support(near, quad) >= MIN_SUPPORT:
                yield width * height, quad


def outermost(found):
    """Distinct cards: a quad whose centre lies inside a larger one is that card's inner frame."""
    import cv2
    import numpy as np

    kept = []
    for _, quad in sorted(found, key=lambda f: -f[0]):
        centre = tuple(map(float, np.mean(quad, axis=0)))
        if all(cv2.pointPolygonTest(np.array(k, np.float32), centre, False) < 0 for k in kept):
            kept.append(quad)
    return kept


def suggest(image):
    """Card quads in `image` (upright PIL image), largest first, as four [x, y] pairs clockwise from top
    left in its pixels. Empty when nothing card-shaped is found or OpenCV is not installed."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return []
    from PIL import Image

    scale = SIZE / max(image.size)
    rgb = image.convert("RGB").resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    small = cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(small, (3, 3), 0), 40, 120)
    near = cv2.dilate(edges, np.ones((5, 5), np.uint8)) > 0
    segments = cv2.HoughLinesP(edges, 1, np.pi / 360, 60, minLineLength=SIZE * 0.06, maxLineGap=12)
    if segments is None:
        return []
    segments = segments.reshape(-1, 4)
    angles = np.degrees(np.arctan2(segments[:, 3] - segments[:, 1], segments[:, 2] - segments[:, 0])) % 180
    vertical = merged(segments[np.abs(angles - 90) < 12], True)
    horizontal = merged(segments[(angles < 12) | (angles > 168)], False)
    quads = outermost(list(card_quads(vertical, horizontal, near)))
    return [[[round(float(x) / scale), round(float(y) / scale)] for x, y in quad] for quad in quads]
