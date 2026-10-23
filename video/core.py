import math
from pathlib import Path

import numpy as np
import skia

W, H = 1280, 720
HERE = Path(__file__).parent

INK = (43, 30, 18)
NIGHT = (24, 17, 10)
PAPER = (233, 220, 192)
VELLUM = (246, 238, 216)
GOLD = (176, 132, 52)
GOLD_HI = (226, 186, 104)
GOLD_LO = (122, 88, 30)
SEA = (47, 106, 115)
SEA_HI = (96, 150, 152)
RUST = (138, 74, 44)


def col(c, a=1.0):
    return skia.Color(int(c[0]), int(c[1]), int(c[2]), int(max(0, min(1, a)) * 255))


def stroke(c, w=2.0, a=1.0):
    return skia.Paint(Color=col(c, a), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=w, StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)


def fill(c, a=1.0):
    return skia.Paint(Color=col(c, a), AntiAlias=True, Style=skia.Paint.kFill_Style)


_FACES = {}


def font(name, size):
    files = {"fell": "IMFeENsc28P.ttf", "sans": "AtkinsonHyperlegible-Regular.ttf", "bold": "AtkinsonHyperlegible-Bold.ttf"}
    if name not in _FACES:
        _FACES[name] = skia.Typeface.MakeFromFile(str(HERE / "fonts" / files[name]))
    f = skia.Font(_FACES[name], size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def text(c, s, x, y, fnt, paint, align="left"):
    w = fnt.measureText(s)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    c.drawString(s, x, y, fnt, paint)
    return w


def clamp01(x):
    return max(0.0, min(1.0, x))


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def spring(t, w=14.0, z=0.55):
    if t <= 0:
        return 0.0
    wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * t) * (math.cos(wd * t) + z * w / wd * math.sin(wd * t))


def rng_for(*keys):
    h = 2166136261
    for k in keys:
        for ch in str(k):
            h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return np.random.default_rng(h)


def trimmed(path, frac):
    if frac >= 1:
        return path
    if frac <= 0:
        return skia.Path()
    lengths = []
    m = skia.PathMeasure(path, False)
    while True:
        lengths.append(m.getLength())
        if not m.nextContour():
            break
    left = sum(lengths) * frac
    out = skia.Path()
    m = skia.PathMeasure(path, False)
    for L in lengths:
        if left <= 0:
            break
        m.getSegment(0, min(L, left), out, True)
        left -= L
        m.nextContour()
    return out


def hatch(c, clip, angle_deg, spacing, paint):
    c.save()
    c.clipPath(clip, skia.ClipOp.kIntersect, True)
    b = clip.getBounds()
    cx, cy = b.centerX(), b.centerY()
    r = math.hypot(b.width(), b.height()) / 2 + spacing
    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    nx, ny = -dy, dx
    p = skia.Path()
    k = -r
    while k <= r:
        p.moveTo(cx + nx * k - dx * r, cy + ny * k - dy * r)
        p.lineTo(cx + nx * k + dx * r, cy + ny * k + dy * r)
        k += spacing
    c.drawPath(p, paint)
    c.restore()


def crosshatch(c, clip, spacing, paint, levels=2, base=35):
    for i in range(levels):
        hatch(c, clip, base + i * 70, spacing, paint)


def rot_x(a):
    ca, sa = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]])


def rot_y(a):
    ca, sa = math.cos(a), math.sin(a)
    return np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]])


def rot_z(a):
    ca, sa = math.cos(a), math.sin(a)
    return np.array([[ca, -sa, 0], [sa, ca, 0], [0, 0, 1]])


class Camera:
    def __init__(self, pos, R, f=900.0, cx=W / 2, cy=H / 2, near=0.15):
        self.pos = np.asarray(pos, float)
        self.R = R
        self.f, self.cx, self.cy, self.near = f, cx, cy, near

    @staticmethod
    def look_at(pos, target, up=(0, 1, 0), roll=0.0, **kw):
        pos = np.asarray(pos, float)
        fwd = np.asarray(target, float) - pos
        fwd /= np.linalg.norm(fwd)
        right = np.cross(np.asarray(up, float), fwd)
        right /= np.linalg.norm(right)
        R = np.stack([right, np.cross(fwd, right), fwd])
        if roll:
            R = rot_z(roll) @ R
        return Camera(pos, R, **kw)

    def to_cam(self, P):
        return (np.asarray(P, float) - self.pos) @ self.R.T

    def proj(self, Pc):
        z = np.maximum(Pc[..., 2], 1e-6)
        return np.stack([self.cx + self.f * Pc[..., 0] / z, self.cy - self.f * Pc[..., 1] / z], -1), Pc[..., 2]


def draw_segments(c, cam, A, B, color, width=2.0, fog=None, alpha=1.0, buckets=6):
    Ac, Bc = cam.to_cam(A), cam.to_cam(B)
    n = cam.near
    keep = (Ac[:, 2] > n) | (Bc[:, 2] > n)
    Ac, Bc = Ac[keep].copy(), Bc[keep].copy()
    if len(Ac) == 0:
        return
    for P, Q in ((Ac, Bc), (Bc, Ac)):
        behind = P[:, 2] <= n
        if behind.any():
            t = (n - P[behind, 2]) / (Q[behind, 2] - P[behind, 2])
            P[behind] = P[behind] + (Q[behind] - P[behind]) * t[:, None]
    a2, za = cam.proj(Ac)
    b2, zb = cam.proj(Bc)
    z = (za + zb) / 2
    lv = np.zeros(len(z), int) if fog is None else np.clip(((z - fog[0]) / (fog[1] - fog[0]) * buckets).astype(int), 0, buckets)
    for k in range(buckets + 1):
        sel = np.nonzero(lv == k)[0]
        if len(sel) == 0:
            continue
        fade = 1 - k / (buckets + 1) if fog else 1
        p = skia.Path()
        for i in sel:
            p.moveTo(float(a2[i, 0]), float(a2[i, 1]))
            p.lineTo(float(b2[i, 0]), float(b2[i, 1]))
        c.drawPath(p, stroke(color, width * (0.55 + 0.45 * fade) if fog else width, alpha * fade))


def poly_path(pts2d, close=True):
    p = skia.Path()
    p.moveTo(float(pts2d[0][0]), float(pts2d[0][1]))
    for q in pts2d[1:]:
        p.lineTo(float(q[0]), float(q[1]))
    if close:
        p.close()
    return p


def circle3d(r, n=96, plane=np.eye(3), center=(0, 0, 0)):
    a = np.linspace(0, 2 * np.pi, n + 1)
    pts = np.stack([r * np.cos(a), r * np.sin(a), np.zeros_like(a)], 1)
    return pts @ plane.T + np.asarray(center, float)


def polyline_segments(P):
    return P[:-1], P[1:]


class Post:
    def __init__(self, seed=7):
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
        vign = 1 - 0.28 * np.clip(r - 0.35, 0, None) ** 1.6
        small = rng.random((H // 8 + 2, W // 8 + 2)).astype(np.float32)
        paper = np.kron(small, np.ones((8, 8), np.float32))[:H, :W]
        tex = 0.965 + 0.025 * paper + 0.012 * rng.random((H, W)).astype(np.float32)
        self.mult = (vign * tex)[..., None].astype(np.float32)
        self.grain = [(rng.standard_normal((H, W)).astype(np.float32) * 5.0)[..., None] for _ in range(12)]
        self.tone = np.array([1.04, 0.99, 0.90], np.float32)

    def apply(self, rgba, t, grain=1.0):
        f = rgba[..., :3].astype(np.float32)
        lum = f @ np.array([0.299, 0.587, 0.114], np.float32)
        f = f * 0.82 + lum[..., None] * 0.18 * self.tone
        f *= self.mult
        f += self.grain[int(t * 12) % 12] * grain
        return np.clip(f, 0, 255).astype(np.uint8)
