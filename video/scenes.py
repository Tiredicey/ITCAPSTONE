import math

import numpy as np
import skia

import timeline as T
from core import (W, H, INK, NIGHT, PAPER, VELLUM, GOLD, GOLD_HI, GOLD_LO, SEA, SEA_HI, RUST,
                  col, stroke, fill, font, text, clamp01, ease_out, ease_in_out, spring, rng_for,
                  trimmed, hatch, crosshatch, rot_x, rot_y, rot_z, Camera, draw_segments, poly_path,
                  circle3d, polyline_segments)

KICKS = np.array([tt for _, tt in T.kick_times()])
SAMPLE_PCT = 62


def pulse(t, decay=9.0):
    tl = t + T.LEAD
    past = KICKS[KICKS <= tl]
    return math.exp(-(tl - past[-1]) * decay) if len(past) else 0.0


def beats_since(t, t0):
    return max(0.0, (t + T.LEAD - t0) / T.BEAT)


def shot(u):
    return int((u + T.LEAD) / T.BAR)


def hull(pts):
    pts = sorted(map(tuple, pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def proj_hull(cam, P):
    xy, _ = cam.proj(cam.to_cam(np.asarray(P, float)))
    return poly_path(hull(xy))


def gold_shader(y0, y1):
    return skia.GradientShader.MakeLinear([skia.Point(0, y0), skia.Point(0, y1)],
                                          [col(GOLD_HI), col(GOLD), col(GOLD_LO), col(GOLD_HI)], [0.0, 0.45, 0.7, 1.0])


def caption(c, s, t_in, t, x=72, y=H - 78, size=38, hero=True):
    k = spring(t - t_in, 16, 0.7)
    if k <= 0:
        return
    f = font("fell" if hero else "bold", size)
    w = f.measureText(s)
    box = skia.Rect(x - 20, y - size - 14, x + w + 24, y + 22)
    c.save()
    c.resetMatrix()
    c.clipRect(box)
    c.drawRect(box, fill(NIGHT, 0.86))
    c.drawRect(skia.Rect(x - 20, y - size - 14, x - 14, y + 22), fill(GOLD))
    text(c, s, x, y + (1 - k) * 22, f, fill(VELLUM))
    c.restore()


def sample_tag(c, color=VELLUM, y=44):
    c.save()
    c.resetMatrix()
    text(c, "Sample team data", W - 40, y, font("sans", 20), fill(color, 0.9), "right")
    c.restore()


def magic_circle_paths(cx, cy, R):
    rng = rng_for("circle", 3)
    paths = []
    for r in (R, R * 0.93, R * 0.62, R * 0.56):
        p = skia.Path()
        p.addCircle(cx, cy, r)
        paths.append(p)
    star = skia.Path()
    for i in range(8):
        a = -math.pi / 2 + i * 3 * 2 * math.pi / 7
        x, y = cx + R * 0.9 * math.cos(a), cy + R * 0.9 * math.sin(a)
        star.moveTo(x, y) if i == 0 else star.lineTo(x, y)
    paths.append(star)
    ticks = skia.Path()
    for i in range(56):
        a = i * 2 * math.pi / 56
        l = 0.05 if i % 4 else 0.09
        ticks.moveTo(cx + R * 0.93 * math.cos(a), cy + R * 0.93 * math.sin(a))
        ticks.lineTo(cx + R * (0.93 - l) * math.cos(a), cy + R * (0.93 - l) * math.sin(a))
    paths.append(ticks)
    glyphs = skia.Path()
    for i in range(14):
        a = i * 2 * math.pi / 14 + 0.1
        gx, gy, s = cx + R * 0.775 * math.cos(a), cy + R * 0.775 * math.sin(a), R * 0.045
        kind = int(rng.integers(0, 3))
        if kind == 0:
            glyphs.addCircle(gx, gy, s)
        elif kind == 1:
            glyphs.moveTo(gx - s, gy + s); glyphs.lineTo(gx, gy - s); glyphs.lineTo(gx + s, gy + s); glyphs.close()
        else:
            glyphs.moveTo(gx - s, gy); glyphs.lineTo(gx + s, gy); glyphs.moveTo(gx, gy - s); glyphs.lineTo(gx, gy + s)
    paths.append(glyphs)
    return paths


def scene_circle(c, t, u, dur):
    c.clear(col(PAPER))
    cx, cy, R = W * 0.62, H * 0.47, 255
    paths = magic_circle_paths(cx, cy, R)
    b = beats_since(t, 0)
    for i, p in enumerate(paths):
        prog = ease_out((b - i * 1.4) / 2.2)
        if prog > 0:
            c.drawPath(trimmed(p, prog), stroke(INK, 3.2 if i < 2 else 2.2))
    act = clamp01((b - 8) / 3)
    if act > 0:
        disc = skia.Path()
        disc.addCircle(cx, cy, R * 0.56)
        sh = skia.GradientShader.MakeRadial(skia.Point(cx, cy), R * 0.56, [col(GOLD_HI, act), col(GOLD, act * 0.9), col(GOLD_LO, act)], [0, 0.7, 1])
        c.drawPath(disc, skia.Paint(AntiAlias=True, Shader=sh))
        crosshatch(c, disc, 7, stroke(INK, 1.0, 0.35 * act), 2)
        ring = skia.Path()
        ring.addCircle(cx, cy, R * (0.56 + 0.06 * pulse(t, 7)))
        c.drawPath(ring, stroke(GOLD_LO, 2.5, act))
    if b < 11:
        m = skia.PathMeasure(paths[min(len(paths) - 1, int(b / 1.4))], False)
        if m.getLength() > 0:
            pos, _ = m.getPosTan(m.getLength() * clamp01((b % 1.4) / 1.4))
            c.save()
            c.translate(pos.x(), pos.y())
            c.rotate(-35)
            q = skia.Path()
            q.moveTo(0, 0); q.lineTo(-8, -70); q.lineTo(0, -88); q.lineTo(8, -70); q.close()
            c.drawPath(q, fill(INK))
            c.drawPath(q, stroke(GOLD, 1.5))
            c.restore()
    caption(c, "Every capstone starts with one stroke.", 0.5, t, y=H - 86)


def station_geometry():
    rng = rng_for("station")
    A, B = [], []
    seg = 20
    for k in range(44):
        y, r = -k * 4.0, 6.0
        broken = rng.random() < 0.18
        pts = circle3d(r, seg, rot_x(math.pi / 2), (0, y, 0))
        for i in range(seg):
            if broken and rng.random() < 0.35:
                continue
            A.append(pts[i]); B.append(pts[i + 1])
        pts2 = circle3d(r * 0.86, seg, rot_x(math.pi / 2), (0, y - 0.3, 0))
        for i in range(0, seg, 2):
            A.append(pts2[i]); B.append(pts2[i + 1])
        for i in range(0, seg, 2):
            if rng.random() < 0.12:
                continue
            a = 2 * math.pi * i / seg
            p0 = np.array([r * math.cos(a), y, r * math.sin(a)])
            A.append(p0); B.append(np.array([r * math.cos(a), y - 4, r * math.sin(a)]))
            if i % 4 == 0:
                a2 = 2 * math.pi * (i + 2) / seg
                A.append(p0); B.append(np.array([r * math.cos(a2), y - 4, r * math.sin(a2)]))
    for _ in range(70):
        ctr = np.array([rng.uniform(-4.5, 4.5), -rng.uniform(5, 170), rng.uniform(-4.5, 4.5)])
        s = rng.uniform(0.15, 0.5)
        Rm = rot_y(rng.uniform(0, 6.3)) @ rot_x(rng.uniform(0, 6.3))
        v = np.array([[1, 1, 1], [-1, -1, 1], [-1, 1, -1], [1, -1, -1]]) * s @ Rm.T + ctr
        for i in range(4):
            for j in range(i + 1, 4):
                A.append(v[i]); B.append(v[j])
    return np.array(A), np.array(B)


STATION = station_geometry()


def fall_camera(tl, base_speed=4.0, accel=2.6, roll_rate=0.35, t_global=0.0, shake=0.0, roll0=0.0, f=760):
    y = -(base_speed * tl + accel * tl ** 2)
    r = shake * pulse(t_global, 10)
    pos = (math.sin(tl * 0.9) * 0.8 + r * 0.06, y, math.cos(tl * 0.7) * 0.6)
    tgt = (math.sin(tl * 0.9 + 0.5) * 1.2, y - 10, math.cos(tl * 0.7 + 0.4) * 1.0)
    return Camera.look_at(pos, tgt, up=(0, 0, 1), roll=roll0 + tl * roll_rate + r * 0.02, f=f)


def scene_fall(c, t, u, dur):
    c.clear(col(NIGHT))
    A, B = STATION
    k = shot(u)
    for s in range(2):
        cam = fall_camera(u + s / (T.FPS * 2), t_global=t, shake=1.0, roll0=(1.9, -1.2, 0.6)[k % 3], f=(760, 520, 980)[k % 3])
        draw_segments(c, cam, A, B, GOLD, 2.2, fog=(1.0, 55.0), alpha=0.71)
    caption(c, "Capstone year feels like free-fall.", T.bar_time(3, 2), t)


def scene_array(c, t, u, dur, speed=1.0, label=True, cam_z=-9.0, bg=NIGHT):
    if bg is not None:
        c.clear(col(bg))
    b = beats_since(t, T.bar_time(6))
    k = shot(u) if label else int((t + T.LEAD) / T.BEAT)
    yaw = u * 0.35 * speed + (0.0, 1.3, -0.9, 2.2)[k % 4]
    cam = Camera.look_at((math.sin(yaw) * 2.5, (3.2, 6.5, 1.4, 4.8)[k % 4], cam_z), (0, 0, 0), f=(820, 700, 980, 760)[k % 4])
    tilt = rot_x(math.radians(64))
    p = pulse(t, 8)
    for r, i, d in ((3.2, 0, 1), (2.75, 1, -1), (2.0, 2, 1), (1.3, 3, -1), (0.7, 4, 1)):
        g = spring(b - i * 0.75, 15, 0.5) if label else 1.0
        if g <= 0.01:
            continue
        spin = d * u * (0.5 + 0.2 * i) * speed
        plane = tilt @ rot_z(spin) if i % 2 == 0 else tilt @ rot_y(math.radians(18 * d)) @ rot_z(spin)
        a_, b_ = polyline_segments(circle3d(r * g * (1 + 0.03 * p), 120, plane))
        draw_segments(c, cam, a_, b_, GOLD_HI if i == 0 else GOLD, 2.6 if i == 0 else 1.8)
        n_t = 24 + 8 * i
        ang = np.linspace(0, 2 * np.pi, n_t, endpoint=False)
        ring = lambda rr: np.stack([rr * np.cos(ang), rr * np.sin(ang), np.zeros(n_t)], 1) @ plane.T
        draw_segments(c, cam, ring(r * 0.92 * g), ring(r * g), GOLD, 1.4)
    g = spring(b - 4.5, 12, 0.6) if label else 1.0
    if g > 0.01:
        for off in (0.0, math.pi / 6):
            ang = np.array([off + u * 0.25 * speed + j * 2 * math.pi / 3 for j in range(3)])
            P = np.stack([2.0 * g * np.cos(ang), 2.0 * g * np.sin(ang), np.zeros(3)], 1) @ tilt.T
            draw_segments(c, cam, P, np.roll(P, -1, 0), GOLD_HI, 2.0)
    names = ["Ch. 1", "Ch. 2", "Ch. 3", "Prototype", "Testing", "Defense"]
    lit = int(b / 2) if label else 6
    f = font("bold", 24)
    for j, nm in enumerate(names):
        a = j * 2 * math.pi / 6 - math.pi / 2 + u * 0.12 * speed
        Pc = cam.to_cam(np.array([[3.65 * math.cos(a), 3.65 * math.sin(a), 0.0]]) @ tilt.T)
        if Pc[0, 2] <= cam.near:
            continue
        xy, _ = cam.proj(Pc)
        x, y = float(xy[0, 0]), float(xy[0, 1])
        on = j < lit
        c.drawCircle(x, y, 9 + 4 * (p if on else 0), fill(GOLD_HI if on else NIGHT))
        c.drawCircle(x, y, 9, stroke(GOLD, 2))
        if label:
            text(c, nm, x, y - 18, f, fill(GOLD_HI if on else VELLUM, 1.0 if on else 0.75), "center")
    if label:
        caption(c, "Milestones become a magic array.", T.bar_time(6, 2), t)


def bottle_profile(x):
    if x < -2.2 or x > 2.7:
        return 0.0
    if x < -2.0:
        return math.sqrt(max(0.0, 1 - ((x + 2.0) / 0.2) ** 2))
    if x <= 1.1:
        return 1.0
    if x <= 1.8:
        return 1.0 - 0.62 * ease_in_out((x - 1.1) / 0.7)
    return 0.38


def draw_stand(c, cam):
    V = np.array([[x, y, z] for x in (-1.6, 1.0) for y in (-1.25, -1.05) for z in (-0.8, 0.8)])
    xy, z = cam.proj(cam.to_cam(V))
    faces = [(0, 1, 3, 2), (4, 5, 7, 6), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5)]
    for fc in sorted(faces, key=lambda f_: -np.mean(z[list(f_)])):
        pth = poly_path(xy[list(fc)])
        c.drawPath(pth, fill((96, 64, 38)))
        hatch(c, pth, 30, 6, stroke(INK, 1.0, 0.45))
        c.drawPath(pth, stroke(INK, 2.0))


def draw_ship3d(c, cam, h, u):
    y = h + 0.02 * math.sin(u * 3)
    hp = proj_hull(cam, [(-1.25, y + 0.12, -0.2), (1.0, y + 0.12, -0.2), (1.0, y + 0.12, 0.2), (-1.25, y + 0.12, 0.2), (-1.0, y - 0.14, 0.0), (0.8, y - 0.14, 0.0)])
    c.drawPath(hp, fill((90, 58, 34)))
    hatch(c, hp, -20, 5, stroke(INK, 1.0, 0.5))
    c.drawPath(hp, stroke(INK, 2.2))
    for i, mx in enumerate((-0.75, -0.1, 0.55)):
        top = 0.95 - 0.12 * abs(i - 1)
        a2, _ = cam.proj(cam.to_cam(np.array([[mx, y + 0.12, 0], [mx, y + top, 0]])))
        c.drawLine(float(a2[0, 0]), float(a2[0, 1]), float(a2[1, 0]), float(a2[1, 1]), stroke(INK, 2.2))
        for lo_, hi_, wd in ((0.22, 0.52, 0.28), (0.58, top - 0.08, 0.22)):
            billow = 0.08 * (1 + 0.15 * math.sin(u * 2 + i))
            sp = proj_hull(cam, [[mx - wd, y + lo_, 0], [mx, y + (lo_ + hi_) / 2, -billow], [mx + wd, y + lo_, 0], [mx + wd * 0.85, y + hi_, 0], [mx - wd * 0.85, y + hi_, 0]])
            c.drawPath(sp, fill(GOLD if i == 0 else VELLUM))
            c.drawPath(sp, stroke(INK, 1.6))
    fx, _ = cam.proj(cam.to_cam(np.array([[0.55, y + 1.02, 0], [0.55, y + 0.83, 0], [0.25, y + 0.93 + 0.03 * math.sin(u * 6), 0]])))
    c.drawPath(poly_path(fx), fill(RUST))


def draw_bottle3d(c, cam, level, u):
    xs = np.linspace(-2.2, 2.7, 60)
    rs = np.array([bottle_profile(x) for x in xs])
    draw_stand(c, cam)
    h = -0.92 + 1.75 * level
    sea_pts = []
    for x, r in zip(xs, rs):
        if r <= 0 or x > 1.1:
            continue
        for a in np.linspace(0, 2 * np.pi, 36, endpoint=False):
            if r * math.cos(a) <= h:
                sea_pts.append((x, r * math.cos(a), r * math.sin(a)))
        if abs(h) < r:
            w = math.sqrt(r * r - h * h)
            sea_pts += [(x, h, -w), (x, h, w)]
    if sea_pts:
        sea = proj_hull(cam, sea_pts)
        c.drawPath(sea, fill(SEA))
        crosshatch(c, sea, 7, stroke(INK, 1.0, 0.38), 2, 25)
        if abs(h) < 1:
            w = math.sqrt(1 - h * h) * 0.98
            wave = [(x, h + 0.035 * math.sin(x * 6 + u * 4), -w) for x in np.linspace(-1.95, 1.1, 50)]
            wave += [(x, h + 0.035 * math.sin(x * 6 + u * 4 + 1), w) for x in np.linspace(1.1, -1.95, 50)]
            xy2, _ = cam.proj(cam.to_cam(np.array(wave)))
            c.drawPath(poly_path(xy2), fill(SEA_HI, 0.85))
            c.drawPath(poly_path(xy2), stroke(INK, 1.4, 0.8))
    draw_ship3d(c, cam, h, u)
    for x, r in zip(xs[::5], rs[::5]):
        if r > 0:
            a_, b_ = polyline_segments(circle3d(r, 48, rot_y(math.pi / 2), (x, 0, 0)))
            draw_segments(c, cam, a_, b_, VELLUM, 1.0, alpha=0.35)
    glass = proj_hull(cam, [(x, r * math.cos(a), r * math.sin(a)) for a in np.linspace(0, 2 * np.pi, 48, endpoint=False) for x, r in zip(xs, rs) if r > 0])
    c.drawPath(glass, stroke(INK, 5.0))
    c.drawPath(glass, stroke(VELLUM, 1.6, 0.8))
    ck = proj_hull(cam, [(x, 0.4 * math.cos(a), 0.4 * math.sin(a)) for a in np.linspace(0, 2 * np.pi, 32, endpoint=False) for x in (2.45, 3.05)])
    c.drawPath(ck, fill((150, 104, 60)))
    hatch(c, ck, 80, 5, stroke(INK, 1.0, 0.6))
    c.drawPath(ck, stroke(INK, 2.5))
    xy, _ = cam.proj(cam.to_cam(np.array([(x, 0.78, -0.55) for x in np.linspace(-1.7, 0.6, 30)])))
    c.drawPath(poly_path(xy, False), stroke(VELLUM, 4.0, 0.7))


def scene_bottle(c, t, u, dur):
    c.clear(col((36, 26, 16)))
    k = shot(u)
    yaw = (-0.32, 0.55, -0.95)[k % 3] + u * 0.10
    dist, hgt = (5.6, 4.3, 6.4)[k % 3], (1.3, 0.5, 2.6)[k % 3]
    cam = Camera.look_at((math.sin(yaw) * dist, hgt, -math.cos(yaw) * dist), (0.35, -0.1, 0), f=720, cx=W * 0.6)
    pct = min(SAMPLE_PCT, int(SAMPLE_PCT * clamp01(int(beats_since(t, T.bar_time(9))) / 10)))
    draw_bottle3d(c, cam, 0.05 + 0.9 * pct / 100, u)
    w = text(c, f"{pct}", 70, 240, font("fell", 110), skia.Paint(AntiAlias=True, Shader=gold_shader(150, 250)))
    text(c, "%", 78 + w, 240, font("fell", 54), fill(GOLD))
    text(c, "of tasks done", 74, 290, font("bold", 26), fill(VELLUM))
    sample_tag(c)
    caption(c, "Every finished task raises the sea.", T.bar_time(9, 2), t)


def bubble(c, x, y, w_max, msg, who, mine, k, f, fsmall):
    lines, cur = [], ""
    for wd in msg.split():
        nxt = (cur + " " + wd).strip()
        if f.measureText(nxt) > w_max - 36 and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = nxt
    lines.append(cur)
    bw = max(f.measureText(l) for l in lines) + 36
    bh = 18 + 30 * len(lines)
    bx = x + (w_max - bw if mine else 0)
    a = min(1, k * 1.5)
    s = 0.85 + 0.15 * k
    ax = bx + (bw if mine else 0)
    c.save()
    c.translate(ax, y + bh)
    c.scale(s, s)
    c.translate(-ax, -(y + bh))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(bx, y, bx + bw, y + bh), 20, 20), fill(SEA if mine else (232, 222, 200), a))
    for i, l in enumerate(lines):
        text(c, l, bx + 18, y + 35 + 30 * i, f, fill(VELLUM if mine else INK, a))
    if not mine:
        text(c, who, bx + 6, y - 8, fsmall, fill(INK, 0.75 * a))
    c.restore()
    return bh + (28 if not mine else 14)


def share_card(c, cx, y, k):
    cw, chh = 300, 176
    s = 0.85 + 0.15 * k
    c.save()
    c.translate(cx + cw, y + chh)
    c.scale(s, s)
    c.translate(-(cx + cw), -(y + chh))
    rr = skia.RRect.MakeRectXY(skia.Rect(cx, y, cx + cw, y + chh), 18, 18)
    c.drawRRect(rr, fill((232, 222, 200)))
    c.save()
    c.clipRRect(rr, True)
    c.drawRect(skia.Rect(cx, y, cx + cw, y + 120), fill(PAPER))
    bx, by = cx + 22, y + 22
    body = skia.RRect.MakeRectXY(skia.Rect(bx, by, bx + 150, by + 78), 36, 36)
    c.drawRRect(body, fill((214, 216, 196)))
    c.save()
    c.clipRRect(body, True)
    c.drawRect(skia.Rect(bx, by + 78 * (1 - SAMPLE_PCT / 100), bx + 150, by + 78), fill(SEA))
    c.restore()
    c.drawRRect(body, stroke(INK, 3))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(bx + 148, by + 24, bx + 176, by + 54), 6, 6), fill((150, 104, 60)))
    text(c, f"{SAMPLE_PCT}%", cx + cw - 20, y + 72, font("fell", 34), fill(INK), "right")
    c.restore()
    text(c, f"Smart Queue System: {SAMPLE_PCT}%", cx + 14, y + 148, font("bold", 19), fill(INK))
    text(c, "31/50 tasks · live link", cx + 14, y + 170, font("sans", 16), fill(INK, 0.8))
    c.restore()
    return chh + 18


def scene_chat(c, t, u, dur):
    c.clear(col((36, 26, 16)))
    px0, py0, pw, ph = 690, 30, 430, 660
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(px0, py0, px0 + pw, py0 + ph), 38, 38), fill(INK))
    scr = skia.Rect(px0 + 14, py0 + 14, px0 + pw - 14, py0 + ph - 14)
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(scr, 28, 28), True)
    c.drawRect(scr, fill(VELLUM))
    c.drawRect(skia.Rect(scr.left(), scr.top(), scr.right(), scr.top() + 70), fill(PAPER))
    text(c, "BSIT 3A · Capstone G4", scr.left() + 22, scr.top() + 44, font("bold", 24), fill(INK))
    f, fs = font("sans", 21), font("sans", 16)
    msgs = [("Cara", "paqod c acoe", False, 0.5), ("me", "check natin progress", True, 2.5), ("card", "", True, 3.5),
            ("Ben", f"{SAMPLE_PCT}% na pala tayo. Petmalu, lodi!", False, 6.0), ("Dino", "Werpa sa defense!", False, 8.0)]
    y = scr.top() + 92
    b = beats_since(t, T.bar_time(12))
    for who, msg, mine, at in msgs:
        k = spring((b - at) * T.BEAT, 18, 0.6)
        if k <= 0:
            continue
        if who == "card":
            y += share_card(c, scr.right() - 318, y, k)
        else:
            y += bubble(c, scr.left() + 18, y, scr.width() - 36, msg, who, mine, k, f, fs)
    c.restore()
    sample_tag(c, VELLUM, H - 16)
    tf = font("fell", 44)
    text(c, "One link.", 72, 250, tf, fill(GOLD_HI))
    text(c, "The whole group chat,", 72, 310, tf, fill(VELLUM))
    text(c, "always current.", 72, 370, tf, fill(VELLUM))
    c.save()
    c.resetMatrix()
    fm = font("sans", 20)
    text(c, "Slang: lodi, petmalu, werpa (Rappler, 2017-12-20);", 72, H - 70, fm, fill(VELLUM, 0.85))
    text(c, "paqod c acoe (Rappler, same list).", 72, H - 42, fm, fill(VELLUM, 0.85))
    c.restore()


def ring_pts(r, y, n=28):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([r * np.cos(a), np.full(n, y), r * np.sin(a)], 1)


def apprentice_parts(yaw):
    R = rot_y(yaw)
    head = np.array([[0.30 * math.sin(p) * math.cos(q), 1.88 + 0.30 * math.cos(p), 0.30 * math.sin(p) * math.sin(q)]
                     for p in np.linspace(0, math.pi, 10) for q in np.linspace(0, 2 * np.pi, 20)])
    bag = np.array([[x, y, z] for x in (0.62, 0.86) for y in (0.55, 0.95) for z in (-0.18, 0.18)])
    parts = [
        ("robe", np.vstack([ring_pts(0.26, 1.55), ring_pts(0.78, 0.0)]), SEA),
        ("collar", np.vstack([ring_pts(0.30, 1.58), ring_pts(0.36, 1.45)]), VELLUM),
        ("head", head, (238, 214, 182)),
        ("brim", np.vstack([ring_pts(0.62, 2.08, 40), ring_pts(0.62, 2.12, 40)]), INK),
        ("hat", np.vstack([ring_pts(0.34, 2.12), np.array([[0.55, 2.92, 0.0]])]), INK),
        ("band", np.vstack([ring_pts(0.345, 2.14), ring_pts(0.325, 2.28)]), GOLD),
        ("bag", bag, RUST),
    ]
    return [(n, P @ R.T, cl) for n, P, cl in parts]


def draw_apprentice(c, cam, yaw, alpha=1.0):
    order = {"bag": -1 if math.sin(yaw) > 0 else 6, "robe": 0, "collar": 1, "head": 2, "brim": 3, "hat": 4, "band": 5}
    for name, P, cl in sorted(apprentice_parts(yaw), key=lambda p: order[p[0]]):
        pth = proj_hull(cam, P)
        c.drawPath(pth, fill(cl, alpha))
        if name in ("robe", "hat"):
            crosshatch(c, pth, 6, stroke(INK if name == "robe" else GOLD_LO, 1.0, 0.45 * alpha), 2 if name == "robe" else 1)
        c.drawPath(pth, stroke(INK, 2.0, alpha))
    R = rot_y(yaw)

    def seg(P, paint):
        q, _ = cam.proj(cam.to_cam(np.array(P) @ R.T))
        c.drawLine(float(q[0, 0]), float(q[0, 1]), float(q[1, 0]), float(q[1, 1]), paint)
    seg([[-0.55, 0.9, -0.5], [-0.75, 1.55, -0.55]], stroke(GOLD_HI, 3.0, alpha))
    if math.cos(yaw) > 0.15:
        seg([[0.0, 1.45, -0.32], [0.0, 0.02, -0.80]], stroke(GOLD, 2.0, alpha))
        for P, r, cl in (([0.0, 1.42, -0.37], 6, GOLD_HI), ([-0.11, 1.9, -0.29], 3.2, INK), ([0.11, 1.9, -0.29], 3.2, INK)):
            q, _ = cam.proj(cam.to_cam(np.array([P]) @ R.T))
            c.drawCircle(float(q[0, 0]), float(q[0, 1]), r, fill(cl, alpha))


def scene_crew(c, t, u, dur):
    c.clear(col(PAPER))
    grid = skia.Path()
    for x in range(0, W, 40):
        grid.moveTo(x, 0); grid.lineTo(x, H)
    for y in range(0, H, 40):
        grid.moveTo(0, y); grid.lineTo(W, y)
    c.drawPath(grid, stroke(GOLD, 0.8, 0.25))
    text(c, "APPRENTICE · TURNAROUND", 60, 70, font("fell", 40), fill(INK))
    text(c, "Original character, robe and pointed hat", 60, 102, font("sans", 22), fill(INK, 0.8))
    b = beats_since(t, T.bar_time(15))
    spin = max(0.0, b - 7.5) * 0.5
    views = [("FRONT", 0.0), ("3/4", math.radians(45)), ("SIDE", math.radians(90)), ("BACK", math.pi)]
    crew = [("Ana", 8, 10), ("Ben", 6, 9), ("Cara", 7, 7), ("Dino", 5, 8)]
    for i, ((lab, yaw), (nm, dn, tot)) in enumerate(zip(views, crew)):
        k = spring((b - i) * T.BEAT, 14, 0.6)
        if k <= 0:
            continue
        a = min(1, k * 1.4)
        cx = 190 + i * 300
        cam = Camera.look_at((0, 1.6, -6.5), (0, 1.45, 0), f=560 * (0.9 + 0.1 * k), cx=cx, cy=360)
        draw_apprentice(c, cam, yaw + spin, a)
        text(c, lab, cx, 560, font("bold", 22), fill(INK, min(1, k)), "center")
        text(c, nm, cx, 600, font("fell", 32), fill(INK, min(1, k)), "center")
        c.drawRect(skia.Rect(cx - 90, 616, cx + 90, 628), fill(INK, 0.18))
        c.drawRect(skia.Rect(cx - 90, 616, cx - 90 + 180 * dn / tot * ease_out(k), 628), fill(SEA))
        text(c, f"{dn}/{tot} tasks", cx, 656, font("sans", 21), fill(INK, 0.85 * min(1, k)), "center")
    sample_tag(c, INK, 70)


def scene_climax(c, t, u, dur):
    c.clear(col(NIGHT))
    A, B = STATION
    kb = int((t + T.LEAD) / T.BEAT)
    cam = fall_camera(5.14 + u * 1.3, base_speed=5.0, roll_rate=0.7, t_global=t, shake=1.5, roll0=(0.0, 2.1, -1.4, 3.0)[kb % 4], f=(760, 560, 900, 640)[kb % 4])
    draw_segments(c, cam, A, B, GOLD, 2.0, fog=(1.0, 50.0), alpha=0.8)
    scene_array(c, t, u + 6.0, dur, speed=2.4, label=False, cam_z=-9.0 + u * 0.9, bg=None)
    pct = min(100, SAMPLE_PCT + int((100 - SAMPLE_PCT) * clamp01(beats_since(t, T.bar_time(18)) / 9)))
    f = font("fell", 150)
    s = f"{pct}%"
    w = f.measureText(s)
    c.drawRect(skia.Rect(W / 2 - w / 2 - 30, 245, W / 2 + w / 2 + 30, 420), fill(NIGHT, 0.75))
    text(c, s, W / 2, 390, f, skia.Paint(AntiAlias=True, Shader=gold_shader(260, 400)), "center")
    sample_tag(c)
    if pct == 100:
        caption(c, "Full sea: every task done.", T.bar_time(20), t, x=W / 2 - 230, y=500, size=40)


def scene_plunge(c, t, u, dur):
    c.clear(col(PAPER))
    k = ease_in_out(u / dur)
    for p in magic_circle_paths(W / 2, H / 2, 255 * (1 + 5.0 * k)):
        c.drawPath(p, stroke(INK, 3.0 + 10 * k))
    ink = skia.Path()
    ink.addCircle(W / 2, H / 2, max(1.0, 900 * k ** 2.2))
    c.drawPath(ink, fill(NIGHT))


def floral_border(x0, y0, x1, y1):
    rng = rng_for("floral", 9)
    vine, leaves, corners = skia.Path(), skia.Path(), skia.Path()
    first = True
    for ax, ay, bx, by in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        L = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / L, (by - ay) / L
        nx, ny = -uy, ux
        n = int(L / 6)
        for i in range(n + 1):
            s = i / n * L
            off = 9 * math.sin(s / 38 * 2 * math.pi)
            x, y = ax + ux * s + nx * off, ay + uy * s + ny * off
            if first:
                vine.moveTo(x, y)
                first = False
            else:
                vine.lineTo(x, y)
        for j in range(int(L / 38)):
            s = (j + 0.25) * 38
            sd = 1 if j % 2 == 0 else -1
            px, py = ax + ux * s + nx * 9 * sd, ay + uy * s + ny * 9 * sd
            tx, ty = px + nx * 18 * sd + ux * 10, py + ny * 18 * sd + uy * 10
            leaves.moveTo(px, py)
            leaves.quadTo(px + nx * 14 * sd - ux * 4, py + ny * 14 * sd - uy * 4, tx, ty)
            leaves.quadTo(px + ux * 14, py + uy * 14, px, py)
            if rng.random() < 0.3:
                leaves.addCircle(tx + nx * 6 * sd, ty + ny * 6 * sd, 3.5)
    for cx, cy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        for r in (26, 18, 10):
            corners.addCircle(cx, cy, r)
        for k in range(8):
            a = k * math.pi / 4
            corners.moveTo(cx + 26 * math.cos(a), cy + 26 * math.sin(a))
            corners.lineTo(cx + 40 * math.cos(a), cy + 40 * math.sin(a))
    return vine, leaves, corners


def scene_title(c, t, u, dur):
    c.clear(col(NIGHT))
    vine, leaves, corners = floral_border(70, 60, W - 70, H - 60)
    c.drawPath(trimmed(vine, ease_out(u / 2.2)), stroke(GOLD, 2.2))
    lk = ease_out((u - 0.6) / 2.0)
    if lk > 0:
        c.drawPath(leaves, fill(GOLD, lk * 0.9))
        c.drawPath(leaves, stroke(GOLD_LO, 1.0, lk))
        c.drawPath(corners, stroke(GOLD_HI, 1.8, lk))
    c.drawRect(skia.Rect(110, 100, W - 110, H - 100), stroke(GOLD_LO, 1.2, 0.8))
    s = spring(u, 9, 0.75)
    c.save()
    c.translate(W / 2, 330)
    c.scale(0.92 + 0.08 * s, 0.92 + 0.08 * s)
    pa = skia.Paint(AntiAlias=True, Shader=gold_shader(-110, 10))
    pa.setAlphaf(clamp01(s * 1.4))
    f = font("fell", 132)
    text(c, "Bote sa Bote", 0, 0, f, pa, "center")
    text(c, "Bote sa Bote", 0, 0, f, stroke(GOLD_LO, 1.2, clamp01(s)), "center")
    c.restore()
    k2 = spring(u - 0.9, 12, 0.8)
    if k2 > 0:
        text(c, "Capstone progress in a bottle", W / 2, 400 + (1 - k2) * 16, font("fell", 42), fill(VELLUM, clamp01(k2)), "center")
    k3 = spring(u - 1.7, 12, 0.8)
    if k3 > 0:
        text(c, "BSIT 3rd year · STI College Lipa", W / 2, 470, font("bold", 28), fill(GOLD_HI, clamp01(k3)), "center")
        text(c, "github.com/Tiredicey/ITCAPSTONE", W / 2, 520, font("sans", 26), fill(VELLUM, clamp01(k3)), "center")


SCENES = {"circle": scene_circle, "fall": scene_fall, "array": scene_array, "bottle": scene_bottle,
          "chat": scene_chat, "crew": scene_crew, "climax": scene_climax, "plunge": scene_plunge, "title": scene_title}

FRAMING = {
    "circle": [(1.0, W * 0.62, H * 0.47), (1.55, W * 0.66, H * 0.40), (1.12, W * 0.62, H * 0.47)],
    "chat": [(1.0, W / 2, H / 2), (1.38, 905, 330), (1.12, 380, 320)],
    "crew": [(1.0, W / 2, H / 2), (1.5, 340, 470), (1.08, W / 2, H / 2)],
}


def paint(c, t):
    name, u, dur = T.section_at(t)
    c.save()
    if name in FRAMING:
        fr = FRAMING[name]
        z, px, py = fr[min(shot(u), len(fr) - 1)]
        z *= 1 + 0.035 * ((u + T.LEAD) % T.BAR) / T.BAR
    elif name == "title":
        z, px, py = 1 + 0.03 * u / dur, W / 2, H / 2
    else:
        z, px, py = 1.0, 0, 0
    c.translate(px, py)
    c.scale(z, z)
    c.translate(-px, -py)
    SCENES[name](c, t, u, dur)
    c.restore()
    return name
