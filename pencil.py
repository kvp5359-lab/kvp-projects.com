"""Pencil ink shapes as SVG paths, after Dictum's PencilPaths (transcribe-app/Sources/Dictum/Overlay/Styles/Pencil): a hand-drawn centre line (slight bow), the ink width
swelling slowly, filled (never stroked)."""
import math, random, sys, json

def ring(center, normals, width, rnd, closed=True):
    n = len(center)
    p1, p2 = rnd.uniform(0, 6.28), rnd.uniform(0, 6.28)
    slow = rnd.choice([2, 3]); fast = rnd.choice([7, 9, 11])
    left, right = [], []
    for i, ((x, y), (nx, ny)) in enumerate(zip(center, normals)):
        t = i / n * 2 * math.pi
        w = width * (1 + 0.19 * math.sin(t * slow + p1) + 0.06 * math.sin(t * fast + p2))
        if not closed:  # round-ish tapered ends
            edge = min(i, n - 1 - i) / max(n * 0.06, 1)
            w *= min(1, 0.45 + 0.55 * edge)
        left.append((x + nx * w / 2, y + ny * w / 2)); right.append((x - nx * w / 2, y - ny * w / 2))
    f = lambda pts: "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts) + " Z"
    return f(left) + " " + f(list(reversed(right))) if closed else f(left + list(reversed(right)))

def wobble(points, normals, amount, rnd, closed=True):
    n = len(points); a, b = rnd.uniform(0, 6.28), rnd.uniform(0, 6.28); k = rnd.choice([2, 3])
    out = []
    for i, ((x, y), (nx, ny)) in enumerate(zip(points, normals)):
        t = i / n * 2 * math.pi
        d = amount * math.sin(t * k + a) + amount * 0.35 * math.sin(t * 5 + b)
        out.append((x + nx * d, y + ny * d))
    return out

def rounded_rect(w, h, r, width, seed, pad=None):
    rnd = random.Random(seed); pad = pad if pad is not None else width
    x0, y0, x1, y1 = pad, pad, w - pad, h - pad
    pts, nrm = [], []
    def arc(cx, cy, a0):
        for j in range(5):
            a = a0 + j / 5 * math.pi / 2
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r)); nrm.append((math.cos(a), math.sin(a)))
    def line(ax, ay, bx, by, nx, ny):
        L = math.hypot(bx - ax, by - ay); s = max(int(L / 9), 2)
        for j in range(s):
            pts.append((ax + (bx - ax) * j / s, ay + (by - ay) * j / s)); nrm.append((nx, ny))
    line(x0 + r, y0, x1 - r, y0, 0, -1); arc(x1 - r, y0 + r, -math.pi / 2)
    line(x1, y0 + r, x1, y1 - r, 1, 0); arc(x1 - r, y1 - r, 0)
    line(x1 - r, y1, x0 + r, y1, 0, 1); arc(x0 + r, y1 - r, math.pi / 2)
    line(x0, y1 - r, x0, y0 + r, -1, 0); arc(x0 + r, y0 + r, math.pi)
    pts = wobble(pts, nrm, min(w, h) * 0.006 + 0.6, rnd)
    return ring(pts, nrm, width, rnd)

def underline(w, width, seed, h=14):
    rnd = random.Random(seed); n = 80
    pts = [(width + (w - 2 * width) * i / (n - 1), h / 2 + math.sin(i / n * math.pi * 1.3 + rnd.uniform(0, .5)) * h * 0.18) for i in range(n)]
    return ring(pts, [(0, 1)] * n, width, rnd, closed=False)

def sprite():
    """The site's ink shapes as one SVG sprite (assets/ink.svg): cards, the button, the bullet, the underline.
    Fixed seeds: the same hand on every build."""
    shapes = {
        "card1": ((500, 168), rounded_rect(500, 168, 22, 2.4, 11)),
        "card2": ((500, 168), rounded_rect(500, 168, 22, 2.4, 23)),
        "btn": ((230, 52), rounded_rect(230, 52, 24, 2.2, 5)),
        "dot": ((86, 30), rounded_rect(86, 30, 13, 1.5, 8)),
        "under": ((320, 14), underline(320, 4, 3)),
    }
    body = "".join(f'<symbol id="{k}" viewBox="0 0 {w} {h}" preserveAspectRatio="none"><path d="{d}" fill-rule="evenodd"/></symbol>'
                   for k, ((w, h), d) in shapes.items())
    return f'<svg xmlns="http://www.w3.org/2000/svg">{body}</svg>'
