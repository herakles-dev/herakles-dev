"""Laminar — the page system for this README.

The page reads as one flow. The masthead is a free streamline field seeded
from the current commit, so it re-forms each time the README is refreshed.
Each section header is one phenomenon of that flow (Kelvin wake, isobars,
Joukowski lift, convection rolls, Chladni plates, a harmonograph, a Kármán
street, pendulum phase space), matched to what the section is about and drawn
in that section's slice of a single heat-tint gradient that runs the length of
the page: titanium's temper colors, straw -> gold -> bronze -> rose -> plum ->
violet -> blue -> teal. The coda at the foot of the page lets the flow settle
into straight, laminar lines.

Everything is SVG with SMIL motion only, so it survives GitHub's <img>
sandbox. Fonts are embedded per file by fontkit.embed().
"""
import cmath
import math
import os
import random
import subprocess
import textwrap
from html import escape

from fontkit import cap_height, fit_size, text_width

W = 880


def _rev() -> str:
    sha = os.environ.get("GITHUB_SHA", "")
    if not sha:
        try:
            sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True,
                                          cwd=os.path.dirname(os.path.abspath(__file__))).strip()
        except (OSError, subprocess.CalledProcessError):
            sha = "0000000"
    return sha[:7]


REV = _rev()
# Section headers keep a fixed seed so their art doesn't churn the repo on every
# refresh; only the masthead re-forms with each commit.
HEADER_SEED = 0x574E4D7

# title, subtitle, short label, count shown on the header, auto-updated?
SECTIONS = [
    ["Live right now", None, "LIVE", "2 SITES", False],
    ["Merged into the wild", None, "MERGED", "3 MERGES", True],
    ["What I'm building", None, "BUILDING", "9 PROJECTS", False],
    ["Zeus Terminal", "how all of this gets built", "ZEUS", "4 SESSIONS", False],
    ["A few things that don't fit on a résumé", None, "OFF-RÉSUMÉ", "4 ITEMS", False],
    ["Stack", None, "STACK", "12 TOOLS", False],
    ["By the numbers", None, "NUMBERS", "3 CARDS", False],
    ["Latest pushes", None, "PUSHES", "5 REPOS", True],
]


def set_count(i: int, text: str) -> None:
    SECTIONS[i][3] = text


def svg(w, h, body, extra=""):
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
            f"font-family=\"'JetBrains Mono',ui-monospace,monospace\"{extra}>{body}</svg>")


def title_parts(t, title, width, dots, title_align, subtitle, label_y):
    """Card title/subtitle placement, with the width assertions that stop a
    title colliding with the frame glyph or overrunning a narrow card."""
    parts = []
    if title:
        if title_align == "center":
            fs = 12
            tw = len(title) * 0.6 * fs
            half = width / 2 - (68 if dots else 12)
            assert tw / 2 <= half, f"title {title!r} collides on {width}px card"
            parts.append(f'<text x="{width / 2}" y="{label_y}" font-size="{fs}" fill="{t["muted"]}" text-anchor="middle">{title}</text>')
        else:
            fs = 14
            tx = 80 if dots else 20
            assert tx + len(title) * 0.6 * fs <= width - 12, f"title {title!r} overruns"
            parts.append(f'<text x="{tx}" y="{label_y + 2}" font-size="{fs}" font-weight="700" fill="{t["fg"]}">{title}</text>')
    if subtitle:
        parts.append(f'<text x="{width - 20}" y="{label_y}" font-size="11" fill="{t["muted"]}" text-anchor="end">{subtitle}</text>')
    return parts


# First-order temper colors, in oxide-thickness order. Names + approx.
# anodizing voltage feed the Temper Scale interlude.
TEMPER_NAMES = [("STRAW", 5), ("GOLD", 8), ("BRONZE", 12), ("ROSE", 16),
                ("PLUM", 20), ("VIOLET", 23), ("BLUE", 27), ("TEAL", 32)]
TEMPER = {
    "dark": ["#E8CF86", "#DDAA4F", "#D0834F", "#C9637E", "#A85BC2", "#8E74F2", "#5B8CF2", "#45C2B8"],
    "light": ["#9A7A1E", "#A87814", "#A9592A", "#A63E62", "#8433A0", "#6A45DB", "#2F62CF", "#14827A"],
}
# Second order: the film keeps thickening and the cycle repeats, brighter and stranger.
ORDER2_NAMES = [("PALE GOLD", 55), ("ROSE II", 65), ("MAGENTA", 75), ("TEAL II", 85), ("GREEN", 95)]
ORDER2 = {
    "dark": ["#EAD98A", "#EE8FB0", "#D25BC0", "#3FD0C4", "#6FD08C"],
    "light": ["#8C7A10", "#C24F7A", "#A12B90", "#0F8C82", "#2E8B4A"],
}
# Card category colors, retinted from the temper scale while Laminar builds.
CARD_TINT = {"purple": "#8E74F2", "amber": "#D0834F", "teal": "#45C2B8",
             "blue": "#5B8CF2", "gold": "#DDAA4F", "green": "#6FD08C"}


def _mix(a, b, f):
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * f):02X}" for x, y in zip(pa, pb))


def _sample(stops, u):
    u = min(max(u, 0.0), 1.0) * (len(stops) - 1)
    k = min(int(u), len(stops) - 2)
    return _mix(stops[k], stops[k + 1], u - k)


def temper(theme, u):
    """First order — the page-long gradient, u in [0, 1]."""
    return _sample(TEMPER[theme], u)


def spectrum(theme, u):
    """Both orders end to end — reserved for interludes."""
    return _sample(TEMPER[theme] + ORDER2[theme], u)


class Field:
    """Uniform flow + curl of a sum-of-waves stream function + point vortices,
    with rectangular obstacles that streamlines slide around."""

    def __init__(self, seed, amp=0.9, waves=7, scale=1.0, base=1.0):
        rnd = random.Random(seed)
        self.base = base
        self.waves = []
        for _ in range(waves):
            ang = rnd.uniform(0, 2 * math.pi)
            k = rnd.uniform(0.010, 0.030) / scale
            self.waves.append((k * math.cos(ang), k * math.sin(ang), rnd.uniform(0, 2 * math.pi),
                               amp * rnd.uniform(0.5, 1.0) / k / waves * 0.02))
        self.obstacles = []
        self.vortices = []

    def add_box(self, x0, y0, x1, y1, pad=10):
        self.obstacles.append((x0 - pad, y0 - pad, x1 + pad, y1 + pad))

    def shed(self, x0, y0, x1, y1, n=3, gamma=60, spacing=110, core=16):
        """A von Kármán vortex street behind the last obstacle: alternating
        vortices trailing downstream, each weaker than the one before."""
        cy, half = (y0 + y1) / 2, (y1 - y0) / 2 + 6
        for k in range(n):
            s = 1 if k % 2 == 0 else -1
            self.vortices.append((x1 + 60 + k * spacing, cy - s * half, s * gamma * 0.82 ** k, core))

    def psi(self, x, y):
        """Exact stream function (obstacles excluded): its contours ARE the streamlines."""
        p = self.base * y
        for kx, ky, ph, a in self.waves:
            p += 50 * a * math.sin(kx * x + ky * y + ph)
        for vx, vy, g, core in self.vortices:
            p -= g / 2 * math.log((x - vx) ** 2 + (y - vy) ** 2 + core * core)
        return p

    def _sdf(self, x, y, box):
        x0, y0, x1, y1 = box
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
        r = min(hx, hy, 14)
        qx, qy = abs(x - cx) - hx + r, abs(y - cy) - hy + r
        return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r

    def raw(self, x, y):
        u, v = self.base, 0.0
        for kx, ky, ph, a in self.waves:
            c = math.cos(kx * x + ky * y + ph) * a
            u += c * ky * 50
            v -= c * kx * 50
        for vx, vy, g, core in self.vortices:
            dx, dy = x - vx, y - vy
            r2 = dx * dx + dy * dy + core * core
            u -= g * dy / r2
            v += g * dx / r2
        return u, v

    def vel(self, x, y):
        u, v = self.raw(x, y)
        for box in self.obstacles:
            d = self._sdf(x, y, box)
            R = 34
            if d < R:
                e = 0.8
                nx = (self._sdf(x + e, y, box) - self._sdf(x - e, y, box)) / (2 * e)
                ny = (self._sdf(x, y + e, box) - self._sdf(x, y - e, box)) / (2 * e)
                w = (1 - max(d, 0) / R) ** 2
                dot = u * nx + v * ny
                if dot < 0:
                    u -= nx * dot * w * 1.15
                    v -= ny * dot * w * 1.15
        n = math.hypot(u, v) or 1
        return u / n, v / n

    def inside(self, x, y):
        return any(self._sdf(x, y, b) < 0 for b in self.obstacles)

    def evenly_spaced(self, x0, x1, y0, y1, dsep, rnd, h=4.0, min_len=60):
        """Jobard–Lefer evenly-spaced streamlines: seed anywhere there's room,
        trace both ways, stop a line when it comes within dsep/2 of another.
        Fills wakes behind obstacles instead of leaving them empty."""
        dtest = dsep * 0.5
        cell = dsep
        grid = {}
        lines = []

        def near(x, y, lid, dist):
            cx, cy = int(x // cell), int(y // cell)
            for gx in (cx - 1, cx, cx + 1):
                for gy in (cy - 1, cy, cy + 1):
                    for px, py, pid in grid.get((gx, gy), ()):
                        if pid != lid and (px - x) ** 2 + (py - y) ** 2 < dist * dist:
                            return True
            return False

        def step(x, y, s):
            u1, v1 = self.vel(x, y)
            u2, v2 = self.vel(x + s * u1 * h / 2, y + s * v1 * h / 2)
            return x + s * u2 * h, y + s * v2 * h

        def trace(x, y, lid):
            halves = []
            for s in (-1, 1):
                pts = []
                px, py = x, y
                for _ in range(600):
                    px, py = step(px, py, s)
                    if not (x0 - 20 <= px <= x1 + 20 and y0 <= py <= y1) or self.inside(px, py) or near(px, py, lid, dtest):
                        break
                    # Leave each eddy a clean eye instead of a knot of tiny orbits.
                    if any((px - vx) ** 2 + (py - vy) ** 2 < (core * 0.85) ** 2 for vx, vy, g, core in self.vortices):
                        break
                    # A closed orbit around a vortex core: stop before it retraces itself.
                    if len(pts) > 30 and (px - x) ** 2 + (py - y) ** 2 < dtest * dtest:
                        break
                    pts.append((px, py))
                halves.append(pts)
            return halves[0][::-1] + [(x, y)] + halves[1]

        seeds = [(x, y) for y in frange(y0 + dsep / 2, y1, dsep * 0.7) for x in frange(x0, x1, dsep * 3)]
        rnd.shuffle(seeds)
        for sx, sy in seeds:
            sx += rnd.uniform(-dsep, dsep)
            if self.inside(sx, sy) or near(sx, sy, -1, dsep):
                continue
            lid = len(lines)
            pts = trace(sx, sy, lid)
            xs, ys = [q[0] for q in pts], [q[1] for q in pts]
            if _length(pts) < min_len or math.hypot(max(xs) - min(xs), max(ys) - min(ys)) < 42:
                continue
            for px, py in pts:
                grid.setdefault((int(px // cell), int(py // cell)), []).append((px, py, lid))
            lines.append(pts)
        return lines


class CylinderField(Field):
    """Exact potential flow past a cylinder, plus a trailing Kármán street."""

    def __init__(self, cx, cy, R, seed, a=120.0, n=6, gamma=70.0):
        super().__init__(seed, amp=0.25, waves=4)
        self.cx, self.cy, self.R = cx, cy, R
        h = 0.281 * a  # von Kármán's stability ratio for the street
        for k in range(n):
            s = 1 if k % 2 == 0 else -1
            self.vortices.append((cx + R + 50 + k * a / 2, cy - s * h, s * gamma * 0.9 ** k, 14))

    def raw(self, x, y):
        u, v = super().raw(x, y)
        dx, dy = x - self.cx, y - self.cy
        r2 = dx * dx + dy * dy
        if r2 > 1:
            R2 = self.R ** 2
            u -= R2 * (dx * dx - dy * dy) / (r2 * r2)
            v -= 2 * R2 * dx * dy / (r2 * r2)
        return u, v

    def inside(self, x, y):
        return (x - self.cx) ** 2 + (y - self.cy) ** 2 < (self.R + 3) ** 2 or super().inside(x, y)


def frange(a, b, s):
    while a < b:
        yield a
        a += s


def _path(pts):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def _length(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def marching_squares(grid, x0, y0, step, level):
    """Isoline segments of a scalar grid at one level, joined into polylines."""
    rows, cols = len(grid), len(grid[0])
    segs = []
    for j in range(rows - 1):
        for i in range(cols - 1):
            a, b = grid[j][i], grid[j][i + 1]
            d, c = grid[j + 1][i], grid[j + 1][i + 1]
            if a is None or b is None or c is None or d is None:
                continue
            X, Y = x0 + i * step, y0 + j * step
            pts = []
            for (p, q, P, Q) in ((a, b, (X, Y), (X + step, Y)), (b, c, (X + step, Y), (X + step, Y + step)),
                                 (d, c, (X, Y + step), (X + step, Y + step)), (a, d, (X, Y), (X, Y + step))):
                if (p - level) * (q - level) < 0:
                    f = (level - p) / (q - p)
                    pts.append((P[0] + (Q[0] - P[0]) * f, P[1] + (Q[1] - P[1]) * f))
            if len(pts) == 2:
                segs.append((pts[0], pts[1]))
            elif len(pts) == 4:
                segs.append((pts[0], pts[1]))
                segs.append((pts[2], pts[3]))
    key = lambda p: (round(p[0], 2), round(p[1], 2))
    adj = {}
    for s in segs:
        adj.setdefault(key(s[0]), []).append(s)
        adj.setdefault(key(s[1]), []).append(s)
    used, lines = set(), []
    for s in segs:
        if id(s) in used:
            continue
        used.add(id(s))
        line = [s[0], s[1]]
        for end in (1, 0):
            while True:
                tip = line[-1] if end else line[0]
                nxt = next((t for t in adj.get(key(tip), []) if id(t) not in used), None)
                if not nxt:
                    break
                used.add(id(nxt))
                other = nxt[1] if key(nxt[0]) == key(tip) else nxt[0]
                if end:
                    line.append(other)
                else:
                    line.insert(0, other)
        lines.append(line)
    return lines


def orient(line, velfn):
    """Reverse a contour so it runs with the flow — particles then travel the
    right way round every orbit, and neighbouring rolls counter-rotate."""
    score = 0.0
    for (ax, ay), (bx, by) in zip(line[::4], line[1::4]):
        u, v = velfn(ax, ay)
        score += (bx - ax) * u + (by - ay) * v
    return line if score >= 0 else line[::-1]


def bbox_diag(line):
    xs, ys = [q[0] for q in line], [q[1] for q in line]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys))


class Laminar:
    section = 0

    def __init__(self, themes):
        self.themes = themes

    key, name = "laminar", "Laminar"

    # ── shared rendering ────────────────────────────────────────────────
    def _defs(self, theme, gid, u0, u1, H, fn=temper):
        stops = "".join(f'<stop offset="{k / 8:.3f}" stop-color="{fn(theme, u0 + (u1 - u0) * k / 8)}"/>' for k in range(9))
        bloom = ('<filter id="bloom" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="1.7" result="b"/>'
                 '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
        return (f'<defs>{bloom}<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{W}" y2="0">{stops}</linearGradient>'
                f'<linearGradient id="fg" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                f'<stop offset="0.06" stop-color="#fff"/><stop offset="0.94" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
                f'<linearGradient id="fgy" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                f'<stop offset="0.14" stop-color="#fff"/><stop offset="0.86" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
                f'<mask id="fade" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="url(#fg)"/></mask>'
                f'<mask id="fadey" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="url(#fgy)"/></mask></defs>')

    def _streams(self, field, H, y_lo, y_hi, dsep, rnd, gid, base_op=0.3, pw=2.1, speed=1.0, theme="dark",
                 stroke=None, x_lo=0, x_hi=W):
        """Two groups: hairline streamlines, then particles (bloomed on dark)."""
        paint = stroke or f"url(#{gid})"
        lines_svg, parts_svg = [], []
        lines = field.evenly_spaced(x_lo, x_hi, y_lo, y_hi, dsep, rnd)
        for pts in lines:
            pts = pts[::2] if len(pts) > 4 else pts
            d = _path(pts)
            L = _length(pts)
            op = base_op * min(1.0, 0.45 + L / 500)
            lines_svg.append(f'<path d="{d}" stroke="{paint}" stroke-width="1" opacity="{op:.2f}"/>')
            period = rnd.uniform(40, 80)
            dur = period / rnd.uniform(20, 38) / speed
            o = rnd.uniform(0, period)
            parts_svg.append(f'<path d="{d}" stroke="{paint}" stroke-width="{pw}" stroke-linecap="round" stroke-dasharray="0.1 {period:.1f}">'
                             f'<animate attributeName="stroke-dashoffset" values="{o:.1f};{o - period - 0.1:.1f}" dur="{dur:.2f}s" repeatCount="indefinite"/></path>')
        bloom = ' filter="url(#bloom)"' if theme == "dark" else ""
        return (f'<g mask="url(#fadey)"><g fill="none" mask="url(#fade)">{"".join(lines_svg)}'
                f'<g{bloom}>{"".join(parts_svg)}</g></g></g>'), len(lines)

    def _back(self, seed, obstacles, H, theme, gid, rnd):
        """Depth: a slower, larger-scale flow behind the main one."""
        back = Field(seed, amp=1.0, waves=5, scale=2.4)
        back.obstacles = list(obstacles)
        g, _ = self._streams(back, H, 2, H - 2, 17, rnd, gid, base_op=0.13, pw=1.3, speed=0.5, theme=theme)
        return f'<g opacity="0.8">{g}</g>'

    def _rings(self, field, theme, gid, H, x_hi=W):
        """A dashed ring on each eddy core, turning with its circulation."""
        out = []
        for vx, vy, g, core in field.vortices:
            if not (10 < vx < x_hi - 10 and 4 < vy < H - 4):
                continue
            r = core * 0.9
            spin = 360 if g > 0 else -360
            out.append(f'<g transform="translate({vx:.1f} {vy:.1f})"><circle r="{r:.1f}" fill="none" stroke="url(#{gid})" '
                       f'stroke-width="0.9" stroke-dasharray="1.5 4" opacity="0.55">'
                       f'<animateTransform attributeName="transform" type="rotate" from="0" to="{spin}" dur="{9 + abs(1000 / (g or 1)) % 7:.1f}s" repeatCount="indefinite"/></circle>'
                       f'<circle r="1.4" fill="url(#{gid})" opacity="0.8"/></g>')
        return f'<g mask="url(#fade)">{"".join(out)}</g>'

    # ── page primitives ─────────────────────────────────────────────────
    def masthead(self, theme):
        t = self.themes[theme]
        H = 290
        rnd = random.Random(int(REV, 16))
        field = Field(int(REV, 16), amp=1.8, waves=9)
        l1, l2 = "MICHAEL", "PISCITELLI"
        fs = fit_size("Anybody", 800, l2, 520, 64)
        ch = cap_height("Anybody", 800, fs)
        x0, b1, b2 = 28, 108, 108 + ch + 18
        w1, w2 = text_width("Anybody", 800, l1, fs), text_width("Anybody", 800, l2, fs)
        field.add_box(x0, b1 - ch, x0 + w1, b1, pad=12)
        field.add_box(x0, b2 - ch, x0 + w2, b2, pad=12)
        field.shed(x0, b1 - ch, x0 + max(w1, w2), b2, n=3, gamma=85, spacing=110, core=24)
        dom = "herakles.dev"
        dfs = 22
        db = b2 + 38
        dw = text_width("Anybody", 800, dom, dfs)
        field.add_box(x0, db - cap_height("Anybody", 800, dfs), x0 + dw, db, pad=10)
        tag = "agentic systems · self-hosted · chicago"
        tb = db + 26
        field.add_box(x0, tb - 11, x0 + text_width("JetBrains Mono", 400, tag, 13), tb + 3, pad=8)
        field.add_box(W - 12 - 340, 12, W - 12, 27, pad=4)
        p = [self._defs(theme, "g", 0, 1, H)]
        p.append(self._back(int(REV, 16) ^ 0x5A5A, field.obstacles, H, theme, "g", random.Random(7)))
        streams, _ = self._streams(field, H, 4, H - 4, 9, rnd, "g", base_op=0.28, theme=theme)
        p.append(streams)
        p.append(self._rings(field, theme, "g", H))
        p.append(f'<text x="{x0}" y="{b1}" font-family="Anybody" font-weight="800" font-size="{fs:.1f}" fill="{t["fg"]}">{l1}</text>')
        p.append(f'<text x="{x0}" y="{b2:.1f}" font-family="Anybody" font-weight="800" font-size="{fs:.1f}" fill="{t["fg"]}">{l2}</text>')
        dstops = "".join(f'<stop offset="{k / 6:.3f}" stop-color="{temper(theme, k / 6)}"/>' for k in range(7))
        p.append(f'<defs><linearGradient id="dom" gradientUnits="userSpaceOnUse" x1="{x0}" x2="{x0 + dw:.0f}">{dstops}</linearGradient></defs>')
        p.append(f'<text x="{x0}" y="{db:.1f}" font-family="Anybody" font-weight="800" font-size="{dfs}" fill="url(#dom)">{dom}</text>')
        p.append(f'<line x1="{x0 + dw + 14:.0f}" y1="{db - 7:.1f}" x2="{x0 + dw + 54:.0f}" y2="{db - 7:.1f}" stroke="url(#g)" stroke-width="1.2"/>')
        p.append(f'<text x="{x0}" y="{tb:.1f}" font-size="13" fill="{t["muted"]}">{tag}</text>')
        p.append(f'<text x="{W - 12}" y="24" font-size="10" fill="{t["muted"]}" text-anchor="end">field seed {REV} · re-forms each refresh</text>')
        return svg(W, H, "".join(p))

    # One phenomenon per section, matched to what the section is about.
    SECTION_ART = [
        ("kelvin", "kelvin wake · 19.47°"),             # 01 live right now — underway
        ("isobars", "isobars · contours of ψ"),          # 02 merged — flows joining
        ("joukowski", "joukowski · lift from a circle"), # 03 building — engineering lift
        ("convection", "convection · parallel rolls"),   # 04 zeus — parallel sessions
        ("chladni", "chladni · nodal lines"),            # 05 off-résumé — the acoustic channel
        ("harmonograph", "harmonograph · 2 : 6.003"),    # 06 stack — layered oscillators
        ("karman", "kármán street · h/a = 0.281"),       # 07 numbers — a measured, regular street
        ("phase", "phase space · ω²/2 − cos θ"),         # 08 pushes — orbits that keep coming round
    ]

    def header(self, i, theme):
        t = self.themes[theme]
        title, sub, short, count, auto = SECTIONS[i]
        H = 120
        n = len(SECTIONS)
        lo, hi = max(0.0, i / n - 0.05), min(1.0, (i + 1) / n + 0.05)
        col = lambda u: temper(theme, lo + (hi - lo) * min(max(u, 0), 1))
        T = title.upper()
        subw = text_width("JetBrains Mono", 400, sub, 12) + 18 if sub else 0
        fs = fit_size("Anybody", 800, T, 560 - subw, 28)
        ch = cap_height("Anybody", 800, fs)
        base = 74
        tw = text_width("Anybody", 800, T, fs)
        label = f"{i + 1:02d} / {n:02d} · {count}" + (" · AUTO-UPDATED" if auto else "")
        ly = base - ch - 13
        ax0 = max(tw + subw + 40, 300)
        kind, caption = self.SECTION_ART[i]
        art = getattr(self, f"_art_{kind}")(theme, ax0, W, H, col, seed=HEADER_SEED + 131 * (i + 1))
        stops = (f'<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                 f'<stop offset="{max(ax0 - 70, 0) / W:.3f}" stop-color="#fff" stop-opacity="0"/>'
                 f'<stop offset="{(ax0 + 30) / W:.3f}" stop-color="#fff"/>'
                 f'<stop offset="0.985" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>')
        p = [f'<defs><filter id="bloom" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="1.6" result="b"/>'
             f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
             f'<linearGradient id="am" x1="0" x2="1">{stops}</linearGradient>'
             f'<linearGradient id="amy" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
             f'<stop offset="0.1" stop-color="#fff"/><stop offset="0.9" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
             f'<mask id="artm" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="url(#am)"/></mask>'
             f'<mask id="artmy" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="url(#amy)"/></mask>'
             f'<clipPath id="ac"><rect x="0" y="0" width="{W}" height="{H}"/></clipPath></defs>',
             f'<g clip-path="url(#ac)"><g mask="url(#artmy)"><g mask="url(#artm)">{art}</g></g></g>']
        p.append(f'<text x="0" y="{ly:.0f}" font-size="10" letter-spacing="0.6" fill="{col(0.5)}">{label}</text>')
        p.append(f'<text x="0" y="{base}" font-family="Anybody" font-weight="800" font-size="{fs:.1f}" fill="{t["fg"]}">{escape(T)}</text>')
        if sub:
            p.append(f'<text x="{tw + 18:.0f}" y="{base}" font-size="12" fill="{t["muted"]}">{escape(sub)}</text>')
        p.append(f'<line x1="0" y1="{base + 14}" x2="{min(tw + subw, 520):.0f}" y2="{base + 14}" stroke="{col(0.5)}" stroke-width="1" opacity="0.5"/>')
        cw = len(caption) * 0.6 * 9 + 12
        p.append(f'<rect x="{W - cw:.0f}" y="{H - 17}" width="{cw:.0f}" height="15" rx="4" fill="{t["bg"]}" opacity="0.82"/>')
        p.append(f'<text x="{W - 6}" y="{H - 6}" font-size="9" fill="{t["muted"]}" text-anchor="end">{escape(caption)}</text>')
        return svg(W, H, "".join(p), extra=' xmlns:xlink="http://www.w3.org/1999/xlink"')

    # ── section art: compact interludes drawn into a box, in the section's slice ──
    def _bloom(self, theme):
        return ' filter="url(#bloom)"' if theme == "dark" else ""

    def _art_kelvin(self, theme, ax0, ax1, H, col, seed):
        t = self.themes[theme]
        bx, by = ax1 - 34, H / 2 + 2
        N = 17
        out = []
        for n in range(1, N + 1):
            a = n * 30
            pts = []
            for k in range(121):
                th = -math.pi / 2 + math.pi * k / 120
                pts.append((bx - a * math.cos(th) * (1 + math.sin(th) ** 2), by + a * math.cos(th) ** 2 * math.sin(th)))
            op = 0.75 * math.exp(-n / 14)
            d = _path(pts[::2])
            c = col(n / N)
            out.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="1" opacity="{op:.2f}"/>')
            out.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="1.7" stroke-linecap="round" stroke-dasharray="0.1 8" opacity="{op:.2f}">'
                       f'<animate attributeName="stroke-dashoffset" values="0;-8.1" dur="{1.3 + n * 0.04:.2f}s" repeatCount="indefinite"/></path>')
        rings = "".join(f'<circle cx="{bx + 5}" cy="{by}" r="3" fill="none" stroke="{t["fg"]}" stroke-width="0.8">'
                        f'<animate attributeName="r" values="3;20" dur="3s" begin="{k}s" repeatCount="indefinite"/>'
                        f'<animate attributeName="opacity" values="0.7;0" dur="3s" begin="{k}s" repeatCount="indefinite"/></circle>' for k in (0, 1.5))
        return "".join(out) + f'<g{self._bloom(theme)}>{rings}<ellipse cx="{bx}" cy="{by}" rx="9" ry="2.6" fill="{t["fg"]}"/></g>'

    def _art_isobars(self, theme, ax0, ax1, H, col, seed):
        rnd = random.Random(seed)
        field = Field(seed, amp=1.4, waves=6, base=0.3)
        for _ in range(4):
            field.vortices.append((rnd.uniform(ax0 + 30, ax1 - 30), rnd.uniform(20, H - 20),
                                   rnd.choice((-1, 1)) * rnd.uniform(30, 60), rnd.uniform(14, 24)))
        step = 5
        gx0 = max(ax0 - 80, 0)
        grid = [[field.psi(gx0 + i * step, j * step) for i in range(int((ax1 - gx0) / step) + 2)] for j in range(H // step + 2)]
        flat = sorted(v for row in grid for v in row)
        lo, hi = flat[len(flat) // 40], flat[-len(flat) // 40]
        nlev = 24
        out = []
        for k in range(nlev):
            lev = lo + (hi - lo) * (k + 0.5) / nlev
            ds = [_path(ln[::2] if len(ln) > 6 else ln) for ln in marching_squares(grid, gx0, 0, step, lev)
                  if len(ln) > 3 and bbox_diag(ln) > 24]
            if ds:
                major = k % 4 == 0
                out.append(f'<path d="{" ".join(ds)}" fill="none" stroke="{col(k / (nlev - 1))}" '
                           f'stroke-width="{1.2 if major else 0.7}" opacity="{0.9 if major else 0.5}"/>')
        return "".join(out)

    def _art_joukowski(self, theme, ax0, ax1, H, col, seed):
        t = self.themes[theme]
        mu = complex(-0.09, 0.08)
        R = abs(1 - mu)
        alpha = math.radians(8)
        z_te = 1 - mu
        dw = cmath.exp(-1j * alpha) - R * R * cmath.exp(1j * alpha) / (z_te * z_te)
        gamma = (2 * math.pi * z_te * dw / 1j).real

        def psi(zeta):
            zp = zeta - mu
            return (zp * cmath.exp(-1j * alpha) + R * R * cmath.exp(1j * alpha) / zp
                    - 1j * gamma / (2 * math.pi) * cmath.log(zp)).imag
        S = 64.0
        cxp, cyp = (ax0 + ax1) / 2 + 30, H / 2 + 6
        st = 0.05
        xs = [(ax0 - 90 - cxp) / S + i * st for i in range(int((ax1 - ax0 + 120) / S / st) + 2)]
        ys = [-1.9 + j * st for j in range(int(3.8 / st) + 1)]
        grid = [[None if abs(complex(x, y) - mu) < R else psi(complex(x, y)) for x in xs] for y in ys]
        lines, cols = [], []
        for k in range(-16, 17):
            for ln in marching_squares(grid, 0, 0, 1, k * 0.11):
                pts = []
                for gx, gy in ln:
                    zeta = complex(xs[0] + gx * st, ys[0] + gy * st)
                    z = zeta + 1 / zeta
                    pts.append((cxp + z.real * S, cyp - z.imag * S))
                if len(pts) > 6 and bbox_diag(pts) > 40:
                    if pts[0][0] > pts[-1][0]:
                        pts = pts[::-1]
                    lines.append(pts)
                    cols.append(col((k + 16) / 32))
        foil = []
        for k in range(121):
            z = (mu + R * cmath.exp(2j * math.pi * k / 120))
            z = z + 1 / z
            foil.append((cxp + z.real * S, cyp - z.imag * S))
        return (self._flow_on(lines, cols, random.Random(seed), theme, width=0.8, op=0.5, pw=1.9)
                + f'<path d="{_path(foil)} Z" fill="{t["bg"]}" stroke="{t["fg"]}" stroke-width="1.1"/>')

    def _art_convection(self, theme, ax0, ax1, H, col, seed):
        top, bot = 14, H - 14
        d = bot - top
        lam = 2 * math.sqrt(2) * d
        x_off = ax1 - 2 * lam
        psi = lambda x, y: math.sin(2 * math.pi * (x - x_off) / lam) * math.sin(math.pi * (y - top) / d)
        step = 4
        gx0 = max(ax0 - 80, 0)
        grid = [[psi(gx0 + i * step, j * step) if top <= j * step <= bot else 0.0
                 for i in range(int((ax1 - gx0) / step) + 2)] for j in range(H // step + 2)]
        e = 0.5
        vel = lambda x, y: ((psi(x, y + e) - psi(x, y - e)) / (2 * e), -(psi(x + e, y) - psi(x - e, y)) / (2 * e))
        lines, cols = [], []
        for lev in (-0.85, -0.6, -0.35, -0.12, 0.12, 0.35, 0.6, 0.85):
            for ln in marching_squares(grid, gx0, 0, step, lev):
                if len(ln) > 4 and bbox_diag(ln) > 14:
                    lines.append(orient(ln, vel))
                    cols.append(col(0.15 + 0.3 * abs(lev)) if lev > 0 else col(0.95 - 0.3 * abs(lev)))
        return (f'<line x1="{gx0}" y1="{top}" x2="{ax1}" y2="{top}" stroke="{col(1)}" stroke-width="1.2"/>'
                f'<line x1="{gx0}" y1="{bot}" x2="{ax1}" y2="{bot}" stroke="{col(0)}" stroke-width="1.2"/>'
                + self._flow_on(lines, cols, random.Random(seed), theme, width=0.9, op=0.55, pw=2, speed=0.6))

    def _art_chladni(self, theme, ax0, ax1, H, col, seed):
        t = self.themes[theme]
        size, gap = 78, 12
        count = max(1, min(5, int((ax1 - ax0 + gap) // (size + gap))))
        modes = [(2, 5), (3, 5), (1, 4), (2, 7), (4, 7)][:count]
        x_start = ax1 - count * size - (count - 1) * gap - 2
        y0 = (H - size) / 2 - 6
        ng = 36
        st = size / ng
        out = []
        for k, (n, m) in enumerate(modes):
            px = x_start + k * (size + gap)
            out.append(f'<rect x="{px:.1f}" y="{y0:.1f}" width="{size}" height="{size}" rx="3" fill="{t["bg"]}" stroke="{t["border"]}"/>')
            groups = []
            for sgn, u in ((-1, 0.3), (1, 0.8)):
                f = lambda x, y: (math.cos(n * math.pi * x) * math.cos(m * math.pi * y)
                                  + sgn * math.cos(m * math.pi * x) * math.cos(n * math.pi * y))
                grid = [[f(i / ng, j / ng) for i in range(ng + 1)] for j in range(ng + 1)]
                ds = [_path(ln) for ln in marching_squares(grid, px, y0, st, 0.0) if len(ln) > 1]
                groups.append(f'<path d="{" ".join(ds)}" fill="none" stroke="{col(u)}" stroke-width="1.6" stroke-linecap="round" stroke-dasharray="0.1 2.3"/>')
            beg = f"{k * 1.3:.1f}s"
            out.append(f'<g{self._bloom(theme)}><g>{groups[0]}<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.42;0.5;0.92;1" dur="11s" begin="{beg}" repeatCount="indefinite"/></g>'
                       f'<g opacity="0">{groups[1]}<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.42;0.5;0.92;1" dur="11s" begin="{beg}" repeatCount="indefinite"/></g></g>')
        return "".join(out)

    def _art_harmonograph(self, theme, ax0, ax1, H, col, seed):
        cx, cy = (ax0 + ax1) / 2 + 20, H / 2 - 8
        raw, tt = [], 0.0
        while tt < 200:
            raw.append((math.sin(2 * tt) * math.exp(-0.004 * tt) + 0.5 * math.sin(6.003 * tt) * math.exp(-0.012 * tt),
                        math.sin(3 * tt + math.pi / 2) * math.exp(-0.006 * tt) + 0.3 * math.sin(2 * tt + 1.5) * math.exp(-0.004 * tt)))
            tt += 0.09
        mx, my = max(abs(q[0]) for q in raw), max(abs(q[1]) for q in raw)
        sx = min(190, (ax1 - ax0) / 2 - 10)
        pts = [(cx + x / mx * sx, cy + y / my * 42) for x, y in raw]
        L = _length(pts)
        d = _path(pts)
        stops = "".join(f'<stop offset="{k / 4}" stop-color="{col(k / 4)}"/>' for k in range(5))
        return (f'<defs><linearGradient id="hg" gradientUnits="userSpaceOnUse" x1="{cx - sx}" x2="{cx + sx}">{stops}</linearGradient></defs>'
                f'<path d="{d}" fill="none" stroke="url(#hg)" stroke-width="0.5" opacity="0.2"/>'
                f'<path d="{d}" fill="none" stroke="url(#hg)" stroke-width="0.7" opacity="0.9" stroke-dasharray="{L:.0f}" stroke-dashoffset="{L:.0f}">'
                f'<animate attributeName="stroke-dashoffset" values="{L:.0f};0;0" keyTimes="0;0.82;1" dur="30s" repeatCount="indefinite"/></path>')

    def _art_phase(self, theme, ax0, ax1, H, col, seed):
        t = self.themes[theme]
        step = 4
        sx = 150 / (2 * math.pi)
        xc = ax1 - 150 / 2 - 40
        sy = (H / 2 - 8) / 2.5
        th = lambda x: (x - xc) / sx
        om = lambda y: (H / 2 - y) / sy
        gx0 = max(ax0 - 80, 0)
        grid = [[om(j * step) ** 2 / 2 - math.cos(th(gx0 + i * step)) for i in range(int((ax1 - gx0) / step) + 2)] for j in range(H // step + 2)]
        vel = lambda x, y: (om(y) * sx, math.sin(th(x)) * sy)
        lines, cols = [], []
        for E in (-0.75, -0.4, 0.0, 0.45, 1.3, 1.8, 2.5):
            for ln in marching_squares(grid, gx0, 0, step, E):
                if len(ln) > 4 and bbox_diag(ln) > 16:
                    lines.append(orient(ln, vel))
                    cols.append(col((E + 0.75) / 3.25))
        sep = "".join(f'<path d="{_path(ln[::2])}" fill="none" stroke="{t["fg"]}" stroke-width="1.1" opacity="0.55"/>'
                      for ln in marching_squares(grid, gx0, 0, step, 1.0) if len(ln) > 4)
        return self._flow_on(lines, cols, random.Random(seed), theme, width=0.9, op=0.55, pw=1.9, speed=0.7) + sep

    def _art_karman(self, theme, ax0, ax1, H, col, seed):
        field = CylinderField(ax0 + 40, H / 2, 17, seed, a=96, n=9, gamma=46)
        field.waves = field.waves[:2]
        lines = field.evenly_spaced(max(ax0 - 60, 0), ax1, 3, H - 3, 7, random.Random(seed))
        cols = [col(min(1, max(0, (sum(q[0] for q in ln) / len(ln) - ax0) / (ax1 - ax0)))) for ln in lines]
        lines = [ln if ln[0][0] <= ln[-1][0] else ln[::-1] for ln in lines]
        t = self.themes[theme]
        rings = []
        for vx, vy, g, core in field.vortices:
            if vx < ax1 - 8:
                spin = 360 if g > 0 else -360
                rings.append(f'<g transform="translate({vx:.1f} {vy:.1f})"><circle r="{core * 0.8:.1f}" fill="none" stroke="{col(0.6)}" '
                             f'stroke-width="0.8" stroke-dasharray="1.5 3.5" opacity="0.6">'
                             f'<animateTransform attributeName="transform" type="rotate" from="0" to="{spin}" dur="10s" repeatCount="indefinite"/></circle></g>')
        return (self._flow_on(lines, cols, random.Random(seed), theme, width=0.8, op=0.4, pw=1.9)
                + "".join(rings)
                + f'<circle cx="{ax0 + 40}" cy="{H / 2}" r="17" fill="{t["bg"]}" stroke="{col(0.2)}" stroke-width="1.2"/>')

    def _slice(self, theme):
        n = len(SECTIONS)
        s = max(self.section, 0)
        return temper(theme, s / n), temper(theme, (s + 1) / n)

    def chrome(self, width, height, t, *, dots=False, title=None, title_align="center",
               subtitle=None, divider_y=None, radius=10):
        theme = "light" if t["bg"].lower() == "#ffffff" else "dark"
        c0, c1 = self._slice(theme)
        p = [f'<defs><linearGradient id="edge" x1="0" x2="1"><stop offset="0" stop-color="{c0}" stop-opacity="0"/>'
             f'<stop offset="0.2" stop-color="{c0}"/><stop offset="0.8" stop-color="{c1}"/><stop offset="1" stop-color="{c1}" stop-opacity="0"/></linearGradient>'
             f'<radialGradient id="sheen" cx="0.15" cy="0" r="0.9"><stop offset="0" stop-color="{c0}" stop-opacity="0.10"/>'
             f'<stop offset="1" stop-color="{c0}" stop-opacity="0"/></radialGradient></defs>',
             f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" fill="{t["bg"]}" stroke="{t["border"]}"/>',
             f'<rect x="0.5" y="0.5" width="{width - 1}" height="{min(height - 1, 120)}" rx="8" fill="url(#sheen)"/>',
             f'<rect x="8" y="0" width="{width - 16}" height="1.5" fill="url(#edge)"/>']
        if dots:
            # Three short streamlines in place of window dots; one particle rides the middle one.
            for k, dy in enumerate((-5, 0, 5)):
                d = f"M18,{24 + dy} C30,{24 + dy - 5} 42,{24 + dy + 5} 60,{24 + dy}"
                p.append(f'<path d="{d}" fill="none" stroke="url(#edge)" stroke-width="1.1" opacity="{0.9 if k == 1 else 0.45}"/>')
            p.append(f'<path d="M18,24 C30,19 42,29 60,24" fill="none" stroke="{c1}" stroke-width="2.2" stroke-linecap="round" stroke-dasharray="0.1 46">'
                     f'<animate attributeName="stroke-dashoffset" values="0;-46.1" dur="1.8s" repeatCount="indefinite"/></path>')
        label_y = 28 if dots else 30
        p += title_parts(t, title, width, dots, title_align, subtitle, label_y)
        if divider_y is not None:
            p.append(f'<line x1="0" y1="{divider_y}" x2="{width}" y2="{divider_y}" stroke="{t["border"]}"/>')
        return p

    def tile(self, x, y, w, h, fill, stroke):
        x, y, w, h = float(x), float(y), float(w), float(h)
        gid = f"t{int(x)}_{int(y)}"
        return (f'<defs><linearGradient id="{gid}" x1="0" x2="1"><stop offset="0" stop-color="{stroke}" stop-opacity="0"/>'
                f'<stop offset="0.5" stop-color="{stroke}"/><stop offset="1" stop-color="{stroke}" stop-opacity="0"/></linearGradient>'
                f'<radialGradient id="{gid}s" cx="0.5" cy="0" r="0.8"><stop offset="0" stop-color="{stroke}" stop-opacity="0.12"/>'
                f'<stop offset="1" stop-color="{stroke}" stop-opacity="0"/></radialGradient></defs>'
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-opacity="0.35"/>'
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="url(#{gid}s)"/>'
                f'<rect x="{x + 10}" y="{y}" width="{w - 20}" height="1.5" fill="url(#{gid})"/>')

    def divider(self, theme):
        """Liquid droplets on a thin stream: blur + alpha-threshold (the "goo"
        filter) makes them merge and pinch apart as they pass each other."""
        H = 48
        cy = H / 2
        stops = "".join(f'<stop offset="{k / 8:.3f}" stop-color="{temper(theme, k / 8)}"/>' for k in range(9))
        drops = [  # radius, keyframe x positions, duration
            (7.5, "90;560;90", 13), (5.5, "790;260;790", 11), (9, "300;700;300", 17),
            (4.5, "440;120;600;440", 9), (6, "650;380;820;650", 15),
        ]
        circles = "".join(
            f'<circle cy="{cy}" r="{r}"><animate attributeName="cx" values="{xs}" dur="{d}s" repeatCount="indefinite" '
            f'calcMode="spline" keySplines="{";".join(["0.45 0 0.55 1"] * (xs.count(";")))}"/></circle>'
            for r, xs, d in drops)
        body = (f'<defs><linearGradient id="dg" gradientUnits="userSpaceOnUse" x1="40" x2="{W - 40}">{stops}</linearGradient>'
                f'<filter id="goo" x="-5%" y="-100%" width="110%" height="300%">'
                f'<feGaussianBlur in="SourceGraphic" stdDeviation="3.6" result="b"/>'
                f'<feColorMatrix in="b" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 18 -6.5" result="g"/>'
                f'<feComposite in="SourceGraphic" in2="g" operator="atop"/></filter>'
                f'<linearGradient id="dm" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.12" stop-color="#fff"/>'
                f'<stop offset="0.88" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
                f'<mask id="dmask" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="url(#dm)"/></mask></defs>'
                f'<g mask="url(#dmask)"><g filter="url(#goo)" fill="url(#dg)">'
                f'<rect x="40" y="{cy - 2.6}" width="{W - 80}" height="5.2" rx="2.6"/>{circles}</g></g>')
        return svg(W, H, body)

    # ── interludes ──────────────────────────────────────────────────────









    # ── interludes, second set ──────────────────────────────────────────
    def _flow_on(self, lines, colors, rnd, theme, width=0.8, op=0.45, pw=1.8, speed=1.0, period=(30, 60)):
        """Contour polylines as hairlines plus particles riding them (bloomed on dark)."""
        base, parts = [], []
        for ln, col in zip(lines, colors):
            pts = ln[::3] if len(ln) > 30 else (ln[::2] if len(ln) > 8 else ln)
            d = _path(pts)
            base.append(f'<path d="{d}" stroke="{col}" stroke-width="{width}" opacity="{op}"/>')
            per = rnd.uniform(*period)
            dur = per / rnd.uniform(18, 34) / speed
            o = rnd.uniform(0, per)
            parts.append(f'<path d="{d}" stroke="{col}" stroke-width="{pw}" stroke-linecap="round" stroke-dasharray="0.1 {per:.1f}">'
                         f'<animate attributeName="stroke-dashoffset" values="{o:.1f};{o - per - 0.1:.1f}" dur="{dur:.2f}s" repeatCount="indefinite"/></path>')
        bloom = ' filter="url(#bloom)"' if theme == "dark" else ""
        return f'<g fill="none">{"".join(base)}<g{bloom}>{"".join(parts)}</g></g>'








    # ── the 3×3 project grid, Laminar layout ────────────────────────────

    # ── page furniture: stack strip, coda, neofetch, live-card restyle ──
    def stack_strip(self, theme, tools):
        """The stack as chips, the whole page gradient running across them."""
        t = self.themes[theme]
        cols, gap, ch, width = 6, 10, 34, W
        cw = (width - gap * (cols - 1)) / cols
        rows = (len(tools) + cols - 1) // cols
        height = rows * ch + (rows - 1) * gap + 2
        out = []
        for k, name in enumerate(tools):
            x = (k % cols) * (cw + gap)
            y = 1 + (k // cols) * (ch + gap)
            c = temper(theme, k / max(len(tools) - 1, 1))
            assert len(name) * 0.6 * 12 <= cw - 34, name
            out.append(f'<rect x="{x + 0.5:.1f}" y="{y + 0.5}" width="{cw - 1:.1f}" height="{ch - 1}" rx="8" fill="{t["bg"]}" stroke="{t["border"]}"/>'
                       f'<rect x="{x + 10:.1f}" y="{y}" width="{cw - 20:.1f}" height="1.5" fill="{c}" opacity="0.8"/>'
                       f'<path d="M{x + 12:.1f},{y + ch / 2 + 1} c4,-5 8,5 12,0" fill="none" stroke="{c}" stroke-width="1.6" stroke-linecap="round"/>'
                       f'<text x="{x + 32:.1f}" y="{y + ch / 2 + 5}" font-size="12" fill="{t["fg"]}">{escape(name)}</text>')
        return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
                f"font-family=\"'JetBrains Mono',ui-monospace,monospace\">{''.join(out)}</svg>")

    def coda(self, theme):
        """The page opens turbulent (the masthead) and ends laminar: the same
        streamlines, their disturbance decaying until the flow runs straight."""
        t = self.themes[theme]
        H = 96
        n = 11
        rnd = random.Random(3)
        paths, parts = [], []
        for k in range(n):
            y0 = 14 + k * (H - 28) / (n - 1)
            pts = []
            for i in range(0, W + 1, 6):
                decay = math.exp(-i / 230)
                pts.append((i, y0 + 7 * decay * math.sin(i / 34 + k * 0.9) * (1 - abs(k - n / 2) / n)))
            d = _path(pts)
            paths.append(f'<path d="{d}" stroke="url(#g)" stroke-width="0.9" opacity="0.45"/>')
            per = rnd.uniform(50, 90)
            o = rnd.uniform(0, per)
            parts.append(f'<path d="{d}" stroke="url(#g)" stroke-width="2" stroke-linecap="round" stroke-dasharray="0.1 {per:.1f}">'
                         f'<animate attributeName="stroke-dashoffset" values="{o:.1f};{o - per - 0.1:.1f}" dur="{per / 30:.2f}s" repeatCount="indefinite"/></path>')
        bloom = ' filter="url(#bloom)"' if theme == "dark" else ""
        body = (self._defs(theme, "g", 0, 1, H)
                + f'<g mask="url(#fade)" fill="none">{"".join(paths)}<g{bloom}>{"".join(parts)}</g></g>'
                + f'<rect x="{W - 150}" y="{H - 16}" width="150" height="15" rx="4" fill="{t["bg"]}" opacity="0.82"/>'
                + f'<text x="{W - 6}" y="{H - 5}" font-size="9" fill="{t["muted"]}" text-anchor="end">laminar · Re &lt; 2300</text>')
        return svg(W, H, body)

    # ── the 3×3 project grid ─────────────────────────────────────────────
    def project_cards(self, theme, cards, colors):
        """Centered tiles. Resting state (icon, name, tag) sits centered; when the
        description fades in, icon and name glide up on the same eased clock to
        make room, so both states read as centered."""
        t = self.themes[theme]
        cols, rows = 3, 3
        card_w, card_h, gap, outer = 200, 184, 12, 8
        width = outer * 2 + cols * card_w + (cols - 1) * gap
        height = outer * 2 + rows * card_h + (rows - 1) * gap
        name_fs, tag_fs, desc_fs, lead = 14, 11.5, 11, 15
        lift = 32
        ease = ";".join(["0.42 0 0.58 1"] * 4)
        esc = lambda s_: s_.replace("&", "&amp;").replace("<", "&lt;")
        tiles = []
        for i, (name, icon_fn, tag, desc, color_key) in enumerate(cards):
            col, row = i % cols, i // cols
            x0 = outer + col * (card_w + gap)
            y0 = outer + row * (card_h + gap)
            mx = x0 + card_w / 2
            c = colors[color_key]
            assert len(name) * 0.6 * name_fs <= card_w - 12, name
            assert len(tag) * 0.6 * tag_fs <= card_w - 8, tag
            begin = f"{i * 0.9:.1f}s"
            timing = f'keyTimes="0;0.4;0.5;0.9;1" calcMode="spline" keySplines="{ease}" dur="9s" begin="{begin}" repeatCount="indefinite"'
            parts = [self.tile(x0, y0, card_w, card_h, t["bg"], c)]
            grp = [icon_fn(mx, y0 + 34, c),
                   f'<text x="{mx}" y="{y0 + 68}" font-size="{name_fs}" font-weight="700" fill="{t["fg"]}" text-anchor="middle">{esc(name)}</text>',
                   f'<g><text x="{mx}" y="{y0 + 92}" font-size="{tag_fs}" fill="{t["muted"]}" text-anchor="middle">{esc(tag)}</text>'
                   f'<animate attributeName="opacity" values="1;1;0;0;1" {timing}/></g>']
            parts.append(f'<g transform="translate(0 {lift})">{"".join(grp)}'
                         f'<animateTransform attributeName="transform" type="translate" values="0 {lift};0 {lift};0 0;0 0;0 {lift}" {timing}/></g>')
            lines = textwrap.wrap(desc, width=26)[:5]
            zone_top, zone_bot = y0 + 82, y0 + card_h - 10
            yy = zone_top + ((zone_bot - zone_top) - len(lines) * lead) / 2 + desc_fs
            dl = []
            for ln in lines:
                dl.append(f'<text x="{mx}" y="{yy:.1f}" font-size="{desc_fs}" fill="{t["muted"]}" text-anchor="middle">{esc(ln)}</text>')
                yy += lead
            parts.append(f'<g opacity="0">{"".join(dl)}<animate attributeName="opacity" values="0;0;1;1;0" {timing}/></g>')
            tiles.append("<g>" + "".join(parts) + "</g>")
        return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
                f"font-family=\"'JetBrains Mono',ui-monospace,monospace\">{''.join(tiles)}</svg>")

    def neofetch(self, facts, colors, monogram, height=320):
        """neofetch at the live card's height, so the pair squares up side by side."""
        t = self.themes["dark"]
        width, logo_col, top = 420, 120, 66
        row_h = (height - top - 58) / (len(facts) - 1)
        body = []
        for i, (label, value, ck) in enumerate(facts):
            y = top + i * row_h
            body.append(f'<text x="{logo_col + 18}" y="{y:.1f}" font-size="12.5" font-weight="700" fill="{colors[ck]}">{label}</text>'
                        f'<text x="{width - 20}" y="{y:.1f}" font-size="12.5" fill="{t["fg"]}" text-anchor="end">{value}</text>')
        mid = (top - 12 + height - 34) / 2
        body += monogram(logo_col / 2, mid, 76, colors["purple"])
        body.append(f'<line x1="{logo_col}" y1="{top - 16}" x2="{logo_col}" y2="{height - 34}" stroke="{t["border"]}"/>')
        body.append(f'<line x1="16" y1="{height - 30}" x2="{width - 16}" y2="{height - 30}" stroke="{t["border"]}"/>')
        body.append(f'<text x="20" y="{height - 12}" font-size="9.5" fill="{t["muted"]}">the box everything on this page runs on</text>')
        chrome = self.chrome(width, height, t, dots=True, title="neofetch", divider_y=40)
        return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
                f"font-family=\"'JetBrains Mono',ui-monospace,monospace\">{''.join(chrome)}{''.join(body)}</svg>")
