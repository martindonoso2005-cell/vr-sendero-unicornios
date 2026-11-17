"""Genera 4 panoramas equirectangulares (2:1, 360x180) de un sendero con unicornios.
Uso: python generar_panoramas.py [ancho]   (por defecto 4096 -> 4096x2048)
"""
import math, os, sys, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

OUT = os.path.dirname(os.path.abspath(__file__))
W = int(sys.argv[1]) if len(sys.argv) > 1 else 4096
H = W // 2
CAM_H = 1.6

# ---------------------------------------------------------------- ruido
def _hash(ix, iy, seed):
    n = (ix * 374761393 + iy * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    n = n ^ (n >> 16)
    return (n & 0xFFFF).astype(np.float32) / 65535.0

def vnoise(x, y, seed=0):
    ix = np.floor(x).astype(np.int64); iy = np.floor(y).astype(np.int64)
    fx = (x - ix).astype(np.float32); fy = (y - iy).astype(np.float32)
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a = _hash(ix, iy, seed); b = _hash(ix + 1, iy, seed)
    c = _hash(ix, iy + 1, seed); d = _hash(ix + 1, iy + 1, seed)
    return (a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy

def fbm(x, y, octaves=5, seed=0):
    x, y = np.broadcast_arrays(x, y); s = np.zeros(x.shape, np.float32); amp, tot = 0.5, 0.0
    for o in range(octaves):
        s += amp * vnoise(x, y, seed + o * 17); tot += amp
        x = x * 2.03 + 11.3; y = y * 2.03 - 7.1; amp *= 0.5
    return s / tot

def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

def mix(a, b, t):
    t = np.asarray(t)[..., None] if np.ndim(t) else t
    return np.asarray(a, np.float32) * (1 - t) + np.asarray(b, np.float32) * t

def hsv(h, s=1.0, v=1.0):
    import colorsys
    return np.array(colorsys.hsv_to_rgb(h % 1.0, s, v), np.float32)

def hsv_np(h, s, v):
    h = (h % 1.0) * 6; i = np.floor(h).astype(int) % 6; f = h - np.floor(h)
    p = v * (1 - s); q = v * (1 - s * f); t = v * (1 - s * (1 - f))
    v = np.broadcast_to(v, h.shape); p = np.broadcast_to(p, h.shape)
    r = np.choose(i, [v, q, p, p, t, v]); g = np.choose(i, [t, v, v, q, p, p]); b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], -1).astype(np.float32)

def C(hexs):
    hexs = hexs.lstrip('#'); return np.array([int(hexs[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)

# ---------------------------------------------------------------- sendero
def path_center(z):
    return 2.4 * np.sin(z / 9.0) + 1.1 * np.sin(z / 4.1 + 0.0) * np.tanh(np.abs(z) / 6)

PATH_W = 1.0

# ---------------------------------------------------------------- temas
THEMES = {
    "1_dia_arcoiris": dict(
        zenith=C('2f6fd6'), horizon=C('bfe3ff'), sun_dir=(0.6, 0.32, -0.6), sun_col=C('fff6d8'),
        sun_size=0.03, sun_glow=0.35, clouds=C('ffffff'), cloud_amt=0.55, rainbow=0.45,
        mtn_far=C('8fa9d6'), mtn_near=C('5f8f6a'), grass1=C('5fae3e'), grass2=C('8cc94a'),
        path1=C('c9a26b'), path2=C('a57f4f'), path_mode='dirt', fog=C('cfe6ff'), fog_d=75,
        flowers=[C('ffffff'), C('ffd84d'), C('ff7fb8'), C('b98cff')], flower_amt=0.06,
        trees='mixed', tree_cols=[C('2f7d3a'), C('3e9a45'), C('25683a')], trunk=C('6b4a2e'),
        unicorns=[('ffffff', ['ff6b8b', 'ffb04d', 'ffe34d', '6be38b', '6bb8ff', 'b07bff'], 'f5c542'),
                  ('fff0f7', ['ff8ad8', 'c78bff', '8bd3ff'], 'ffd166'),
                  ('f4f0ff', ['7bdcff', 'a0ffcf', 'fff07b'], 'ffcf4d'),
                  ('fffaf0', ['ff9a9a', 'ffd38a', 'ff7ad1'], 'f7c948')],
        stars=0, glow=False, aurora=False, sparkles=40),
    "2_atardecer_magico": dict(
        zenith=C('3b2a7a'), horizon=C('ffb07a'), sun_dir=(-0.8, 0.06, 0.6), sun_col=C('fff0b0'),
        sun_size=0.045, sun_glow=0.9, clouds=C('ff9ac2'), cloud_amt=0.5, rainbow=0.0,
        mtn_far=C('9c6bb8'), mtn_near=C('5a3d7a'), grass1=C('4e7d4a'), grass2=C('8a8a4a'),
        path1=C('e3b08c'), path2=C('b9806a'), path_mode='dirt', fog=C('f5a98f'), fog_d=60,
        flowers=[C('ffd1e8'), C('ffea80'), C('ff8ab0')], flower_amt=0.05,
        trees='round', tree_cols=[C('6a4c6e'), C('7e5a6b'), C('4f4566')], trunk=C('4a3040'),
        unicorns=[('fff2e6', ['ff6fa8', 'ffb36b', 'ffe07a'], 'ffd166'),
                  ('f6e6ff', ['b07bff', 'ff7bd5', '7bc4ff'], 'f5c542'),
                  ('ffffff', ['ff6b8b', 'ffb04d', 'ffe34d', '6be38b', '6bb8ff', 'b07bff'], 'f5c542'),
                  ('ffe8f0', ['ff8f8f', 'ffc6e0'], 'ffcf4d')],
        stars=0, glow=False, aurora=False, sparkles=80),
    "3_noche_estrellada": dict(
        zenith=C('060a24'), horizon=C('243a73'), sun_dir=(0.3, 0.45, 0.85), sun_col=C('f4f6ff'),
        sun_size=0.025, sun_glow=0.12, clouds=C('3a4a8a'), cloud_amt=0.25, rainbow=0.0,
        mtn_far=C('1d2a5a'), mtn_near=C('121a3a'), grass1=C('16322e'), grass2=C('1f4038'),
        path1=C('5a6ea8'), path2=C('3b4a7a'), path_mode='glow', fog=C('1c2a5a'), fog_d=55,
        flowers=[C('9ff7ff'), C('d3a6ff'), C('ff9ff0')], flower_amt=0.04,
        trees='pine', tree_cols=[C('0f2a2a'), C('12302f'), C('0c2224')], trunk=C('1a1a22'),
        unicorns=[('eef4ff', ['7bdcff', 'b07bff', 'ff7bd5'], 'fff1a8'),
                  ('ffffff', ['8bffcf', '7bc4ff', 'c39bff'], 'ffe680'),
                  ('f4ecff', ['ff8ad8', 'ffd38a', '8bd3ff'], 'fff1a8'),
                  ('eafcff', ['a0ffcf', 'fff07b', 'ff9ad5'], 'ffe680')],
        stars=2500, glow=True, aurora=True, sparkles=130),
    "4_bosque_algodon_pastel": dict(
        zenith=C('9fc2ff'), horizon=C('ffd9ee'), sun_dir=(-0.2, 0.7, -0.7), sun_col=C('fffbe8'),
        sun_size=0.035, sun_glow=0.4, clouds=C('fff2fa'), cloud_amt=0.6, rainbow=0.35,
        mtn_far=C('c8b6ff'), mtn_near=C('9fe0c8'), grass1=C('9fe6b4'), grass2=C('c6f2a6'),
        path1=None, path2=None, path_mode='rainbow', fog=C('fde6f3'), fog_d=70,
        flowers=[C('ffffff'), C('ffb3d9'), C('fff07b'), C('b3e0ff'), C('d9b3ff')], flower_amt=0.09,
        trees='lollipop', tree_cols=[C('ffb3d9'), C('b3e0ff'), C('d9b3ff'), C('fff0a0'), C('b3ffd9')],
        trunk=C('f0d0e0'),
        unicorns=[('ffffff', ['ff6b8b', 'ffb04d', 'ffe34d', '6be38b', '6bb8ff', 'b07bff'], 'f5c542'),
                  ('fff0fa', ['ff8ad8', 'c78bff', '8bd3ff'], 'ffd166'),
                  ('f0fbff', ['8bd3ff', 'a0ffcf', 'fff07b'], 'f5c542'),
                  ('fffaf0', ['ffb3d9', 'd9b3ff', 'b3e0ff'], 'ffcf4d')],
        stars=0, glow=False, aurora=False, sparkles=120),
}

# ---------------------------------------------------------------- fondo
def mountain_profile(seed, base, amp):
    rng = np.random.default_rng(seed)
    lon = (np.arange(W) + 0.5) / W * 2 * np.pi - np.pi
    h = np.full(W, base, np.float32)
    for k in range(1, 40):
        h += amp * rng.normal() / k ** 1.1 * np.sin(k * lon + rng.uniform(0, 6.28))
    return np.maximum(h, 0.002)

def render_background(T, seed):
    img = np.zeros((H, W, 3), np.float32)
    mtn_far = mountain_profile(seed + 1, 0.06, 0.09)
    mtn_near = mountain_profile(seed + 2, 0.025, 0.05)
    sd = np.array(T['sun_dir'], np.float32); sd /= np.linalg.norm(sd)
    lon_all = ((np.arange(W) + 0.5) / W * 2 * np.pi - np.pi).astype(np.float32)
    for r0 in range(0, H, 128):
        r1 = min(H, r0 + 128)
        lat = (np.pi / 2 - ((np.arange(r0, r1) + 0.5) / H) * np.pi).astype(np.float32)[:, None]
        lon = lon_all[None, :]
        cl = np.cos(lat)
        x = cl * np.sin(lon); y = np.sin(lat) * np.ones_like(lon); z = cl * np.cos(lon)
        out = np.zeros(x.shape + (3,), np.float32)

        # --- cielo
        t = np.clip(y, 0, 1) ** 0.55
        sky = mix(T['horizon'], T['zenith'], t)
        cosang = x * sd[0] + y * sd[1] + z * sd[2]
        ang = np.arccos(np.clip(cosang, -1, 1))
        sky += T['sun_col'] * (T['sun_glow'] * np.exp(-ang * 3.0))[..., None] * 0.6
        sky += T['sun_col'] * (T['sun_glow'] * np.exp(-ang * 12.0))[..., None] * 0.6
        disc = smoothstep(T['sun_size'], T['sun_size'] * 0.8, ang)
        sky = mix(sky, T['sun_col'] * 1.05, disc)
        if T['aurora']:
            n = fbm(np.cos(lon) * 2 + 5, np.sin(lon) * 2 + lat, 4, seed + 50)
            band = np.exp(-((lat - 0.6 - 0.3 * (n - 0.5)) / 0.16) ** 2)
            curt = 0.4 + fbm(np.cos(lon) * 10 + 100, np.sin(lon) * 10 + lat * 3, 3, seed + 60) ** 2 * 1.6
            a = band * curt * smoothstep(0.1, 0.35, lat) * 0.45
            sky += (mix(C('3dffb0'), C('b46bff'), smoothstep(0.35, 0.75, lat)) * a[..., None])
        if T['rainbow'] > 0:
            ad = -sd
            th = np.degrees(np.arccos(np.clip(x * ad[0] + y * ad[1] + z * ad[2], -1, 1)))
            k = (th - 39.5) / 3.5
            inb = (k > 0) & (k < 1)
            hue = np.clip(k, 0, 1) * 0.78
            rb = hsv_np(hue, 0.75, 1.0)
            al = T['rainbow'] * np.clip(np.sin(np.clip(k, 0, 1) * np.pi), 0, 1) ** 0.6 * inb * smoothstep(0.0, 0.08, y)
            sky = mix(sky, rb, al)
        # nubes (proyectadas en un plano a cierta altura)
        yy = np.maximum(y, 0.02)
        cx = x / yy * 1.4; cz = z / yy * 1.4
        cn = fbm(cx + 3.1, cz - 1.7, 6, seed + 7)
        cov = smoothstep(1 - T['cloud_amt'] * 0.75 - 0.05, 1 - T['cloud_amt'] * 0.75 + 0.25, cn)
        cov *= smoothstep(0.03, 0.25, y)
        shade = 0.82 + 0.18 * smoothstep(0.4, 0.8, fbm(cx * 2 + 9, cz * 2, 3, seed + 8))
        sky = mix(sky, T['clouds'] * shade[..., None] + T['sun_col'] * 0.08, cov * 0.92)
        out[:] = sky

        # --- montanas
        mf = mtn_far[None, :]; mn = mtn_near[None, :]
        rough = fbm(np.cos(lon) * 13 + lat * 40, np.sin(lon) * 13 + lat * 40, 4, seed + 3)
        far_mask = (lat < mf) & (lat > -0.001)
        fcol = mix(T['mtn_far'], T['fog'], 0.35 + 0.4 * smoothstep(0, 0.15, mf - lat) * 0)
        fcol = fcol * (0.92 + 0.12 * rough[..., None])
        out = np.where(far_mask[..., None], mix(fcol, T['fog'], 0.25 * (1 - smoothstep(0, 0.12, mf - lat))), out)
        near_mask = (lat < mn) & (lat > -0.001)
        ncol = T['mtn_near'] * (0.88 + 0.2 * rough[..., None])
        out = np.where(near_mask[..., None], mix(ncol, T['fog'], 0.3), out)

        # --- suelo
        g = lat < 0
        if g.any():
            t = CAM_H / np.maximum(-y, 1e-4)
            px = x * t; pz = z * t
            d = np.sqrt(px * px + pz * pz)
            n1 = fbm(px * 0.35, pz * 0.35, 5, seed + 11)
            n2 = vnoise(px * 3.0, pz * 3.0, seed + 12)
            grass = mix(T['grass1'], T['grass2'], smoothstep(0.35, 0.7, n1))
            grass = grass * (0.85 + 0.25 * n2[..., None])
            # flores
            fx, fz = px * 4.0, pz * 4.0
            fn = vnoise(fx, fz, seed + 13)
            fsel = _hash(np.floor(fx).astype(np.int64), np.floor(fz).astype(np.int64), seed + 14)
            patch = smoothstep(0.45, 0.7, fbm(px * 0.2, pz * 0.2, 3, seed + 15))
            fl = (fn > 1 - T['flower_amt'] * (0.4 + 1.6 * patch)) * smoothstep(40, 8, d)
            fcols = np.stack(T['flowers'])
            fc = fcols[(fsel * len(T['flowers'])).astype(int) % len(T['flowers'])]
            ground = mix(grass, fc, fl.astype(np.float32))
            # sendero
            edge = PATH_W + 0.25 * (fbm(pz * 0.8, px * 0.8, 3, seed + 16) - 0.5)
            dist = np.abs(px - path_center(pz))
            pm = smoothstep(edge + 0.12, edge - 0.12, dist)
            pn = fbm(px * 2.5, pz * 2.5, 4, seed + 17)
            peb = vnoise(px * 9, pz * 9, seed + 18)
            if T['path_mode'] == 'rainbow':
                lane = np.clip((px - path_center(pz)) / (2 * PATH_W) + 0.5, 0, 0.999)
                band = np.floor(lane * 6) / 6 * 0.8
                pc = hsv_np(band, 0.35, 1.0)
                tiles = vnoise(px * 2.2, pz * 2.2, seed + 19)
                pc = pc * (0.88 + 0.14 * tiles[..., None])
            else:
                pc = mix(T['path2'], T['path1'], smoothstep(0.3, 0.7, pn))
                pc = pc * (0.9 + 0.15 * peb[..., None])
            if T['path_mode'] == 'glow':
                spark = smoothstep(0.9, 0.97, vnoise(px * 25, pz * 25, seed + 21)) * smoothstep(30, 3, d) * 0.7
                pc = mix(pc, C('bff6ff') * 1.4, spark)
                ground += C('6bc8ff') * (pm * 0.15 * smoothstep(25, 2, d))[..., None]
            ground = mix(ground, pc, pm)
            # sombra suave cerca del borde del sendero
            ground *= (1 - 0.12 * smoothstep(edge + 0.5, edge + 0.1, dist) * (1 - pm))[..., None]
            fog = 1 - np.exp(-d / T['fog_d'])
            ground = mix(ground, T['fog'], np.clip(fog, 0, 1))
            out = np.where(g[..., None], ground, out)
        img[r0:r1] = out
    return img

# ---------------------------------------------------------------- sprites
def unicorn_sprite(body, mane, horn, s=3, glow=False):
    body = '#' + body; horn = '#' + horn; mane = ['#' + m for m in mane]
    Wc, Hc = 420 * s, 400 * s
    im = Image.new('RGBA', (Wc, Hc), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    oy = 40
    P = lambda pts: [(px * s, (py + oy) * s) for px, py in pts]
    def ell(x0, y0, x1, y1, col):
        dr.ellipse([x0 * s, (y0 + oy) * s, x1 * s, (y1 + oy) * s], fill=col)
    bc = tuple(int(body[i:i + 2], 16) for i in (1, 3, 5))
    shade = '#%02x%02x%02x' % tuple(int(c * 0.86) for c in bc)
    hoof = '#%02x%02x%02x' % tuple(int(c) for c in (np.array([int(horn[i:i+2],16) for i in (1,3,5)]) * 0.85))
    # cola
    for i in range(14):
        col = mane[i % len(mane)]
        a = i / 13.0
        pts = []
        for k in range(12):
            u = k / 11
            px = 112 - u * (55 + 25 * a) + math.sin(u * 3 + a * 2) * 8
            py = 160 + u * (150 + 20 * math.sin(a * 5)) + (a - 0.5) * 30 * u
            pts.append((px, py))
        dr.line(P(pts), fill=col, width=int(11 * s), joint='curve')
    # patas del lado lejano
    for x0 in (128, 248):
        dr.rounded_rectangle([x0 * s, (195 + oy) * s, (x0 + 22) * s, (338 + oy) * s], radius=8 * s, fill=shade)
        dr.rounded_rectangle([x0 * s, (322 + oy) * s, (x0 + 22) * s, (342 + oy) * s], radius=4 * s, fill=hoof)
    # cuerpo
    ell(92, 128, 305, 238, body)
    # patas del lado cercano
    for x0 in (155, 272):
        dr.rounded_rectangle([x0 * s, (195 + oy) * s, (x0 + 24) * s, (345 + oy) * s], radius=9 * s, fill=body)
        dr.rounded_rectangle([x0 * s, (328 + oy) * s, (x0 + 24) * s, (348 + oy) * s], radius=4 * s, fill=hoof)
    # cuello y cabeza
    dr.polygon(P([(238, 150), (300, 190), (352, 92), (296, 62)]), fill=body)
    ell(292, 40, 358, 108, body)
    ell(328, 66, 392, 120, body)
    dr.polygon(P([(306, 52), (310, 14), (328, 46)]), fill=body)
    dr.polygon(P([(310, 46), (312, 26), (322, 44)]), fill='#ffc0d8')
    # cuerno
    dr.polygon(P([(322, 46), (366, -34), (340, 52)]), fill=horn)
    for k in range(1, 6):
        u = k / 6
        ax, ay = 322 + (366 - 322) * u, 46 + (-34 - 46) * u
        bx, by = 340 + (366 - 340) * u, 52 + (-34 - 52) * u
        dr.line(P([(ax, ay + 4), (bx, by - 4)]), fill='#ffffff', width=int(2 * s))
    # crin
    for i in range(16):
        u = i / 15
        sx = 300 - u * 68; sy = 46 + u * 108
        col = mane[i % len(mane)]
        pts = [(sx, sy)]
        for k in range(1, 6):
            v = k / 5
            pts.append((sx - v * 42 + math.sin(v * 3 + i) * 5, sy + v * 30 + v * v * 10))
        dr.line(P(pts), fill=col, width=int(13 * s), joint='curve')
    # flequillo
    for i, col in enumerate(mane[:4]):
        dr.line(P([(318 + i * 4, 48), (330 + i * 6, 70), (326 + i * 7, 88)]), fill=col, width=int(9 * s), joint='curve')
    # cara
    ell(338, 70, 350, 84, '#2a1a3a'); ell(342, 72, 346, 76, '#ffffff')
    ell(330, 88, 350, 100, '#ffc0d8')
    ell(378, 96, 384, 102, shade)
    dr.arc([358 * s, (100 + oy) * s, 380 * s, (114 + oy) * s], 20, 140, fill='#8a5a7a', width=int(2 * s))
    # contorno suave
    a = im.split()[3]
    outline = a.filter(ImageFilter.MaxFilter(2 * (s * 2) + 1))
    line = Image.new('RGBA', im.size, (90, 60, 110, 255)); line.putalpha(outline)
    base = Image.alpha_composite(line, im)
    if glow:
        g = a.filter(ImageFilter.GaussianBlur(28 * s))
        halo = Image.new('RGBA', im.size, (170, 220, 255, 0))
        halo.putalpha(g.point(lambda v: min(255, int(v * 1.6))))
        base = Image.alpha_composite(halo, base)
    return base, 390 / 400  # proporcion de altura ocupada (casco->punta del cuerno)

def tree_sprite(kind, col, trunk, rng, s=2):
    col = tuple(int(c * 255) for c in col); trunk = tuple(int(c * 255) for c in trunk)
    Wc, Hc = 200 * s, 400 * s
    im = Image.new('RGBA', (Wc, Hc), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dark = tuple(int(c * 0.78) for c in col); light = tuple(min(255, int(c * 1.15 + 15)) for c in col)
    if kind == 'pine':
        dr.rectangle([92 * s, 330 * s, 108 * s, 400 * s], fill=trunk)
        for i in range(4):
            top = 20 + i * 70; bot = 160 + i * 70; half = 40 + i * 18
            dr.polygon([(100 * s, top * s), ((100 - half) * s, bot * s), ((100 + half) * s, bot * s)], fill=dark)
            dr.polygon([(100 * s, top * s), ((100 - half) * s, bot * s), (100 * s, bot * s)], fill=col)
    elif kind == 'lollipop':
        dr.rounded_rectangle([94 * s, 160 * s, 106 * s, 400 * s], radius=5 * s, fill=trunk)
        r = 85
        dr.ellipse([(100 - r) * s, (95 - r) * s, (100 + r) * s, (95 + r) * s], fill=col)
        for k in range(5):
            rr = r - 14 - k * 15
            dr.arc([(100 - rr) * s, (95 - rr) * s, (100 + rr) * s, (95 + rr) * s], k * 50, k * 50 + 220, fill=light, width=6 * s)
        dr.ellipse([(60) * s, (40) * s, (90) * s, (70) * s], fill=(255, 255, 255, 140))
    else:  # round
        dr.rectangle([90 * s, 220 * s, 110 * s, 400 * s], fill=trunk)
        for _ in range(14):
            cx = 100 + rng.normal() * 38; cy = 140 + rng.normal() * 45; r = rng.uniform(35, 60)
            dr.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], fill=dark)
        for _ in range(10):
            cx = 92 + rng.normal() * 30; cy = 120 + rng.normal() * 38; r = rng.uniform(25, 45)
            dr.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], fill=col)
    return im

def tint(sprite, color, amount):
    if amount <= 0.01: return sprite
    r, g, b, a = sprite.split()
    solid = Image.new('RGB', sprite.size, tuple(int(c * 255) for c in np.clip(color, 0, 1)))
    rgb = Image.blend(Image.merge('RGB', (r, g, b)), solid, float(min(amount, 1)))
    rgb.putalpha(a); return rgb

def place(canvas, sprite, wx, wz, height_m, T, flip=False, frac=1.0):
    d = math.hypot(wx, wz)
    lon = math.atan2(wx, wz)
    lat_base = -math.atan(CAM_H / d)
    lat_top = math.atan((height_m - CAM_H) / d)
    hp = (lat_top - lat_base) / math.pi * H / frac
    if hp < 2: return
    wp = hp * sprite.width / sprite.height
    sp = sprite.transpose(Image.FLIP_LEFT_RIGHT) if flip else sprite
    sp = sp.resize((max(1, int(wp)), max(1, int(hp))), Image.LANCZOS)
    sp = tint(sp, T['fog'], 1 - math.exp(-d / T['fog_d']))
    u = (lon + math.pi) / (2 * math.pi) * W
    vb = (math.pi / 2 - lat_base) / math.pi * H
    x0 = int(u - wp / 2); y0 = int(vb - hp * (1 - (1 - frac)))
    # sombra en el suelo
    for off in (0, -W, W):
        if -wp < x0 + off < W:
            lay = Image.new('RGBA', canvas.size, (0, 0, 0, 0)); lay.paste(sp, (x0 + off, y0))
            canvas.alpha_composite(lay)

def shadow(canvas, wx, wz, rad, T):
    d = math.hypot(wx, wz); lon = math.atan2(wx, wz)
    u = (lon + math.pi) / (2 * math.pi) * W
    vb = (math.pi / 2 + math.atan(CAM_H / d)) / math.pi * H
    wpx = (2 * rad / d) / (2 * math.pi) * W
    hpx = wpx * (CAM_H / d) * 0.9
    lay = Image.new('RGBA', canvas.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(lay)
    for off in (0, -W, W):
        dr.ellipse([u - wpx / 2 + off, vb - hpx / 2, u + wpx / 2 + off, vb + hpx / 2], fill=(0, 0, 30, 70))
    canvas.alpha_composite(lay.filter(ImageFilter.GaussianBlur(max(1, hpx / 4))))

def sparkle_layer(T, rng, n):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(lay)
    cols = [(255, 255, 255), (255, 240, 160), (190, 240, 255), (255, 190, 240), (200, 255, 200)]
    for _ in range(n):
        d = rng.uniform(3, 30); ang = rng.uniform(-math.pi, math.pi); hgt = rng.uniform(0.2, 3.5)
        wx, wz = d * math.sin(ang), d * math.cos(ang)
        lat = math.atan((hgt - CAM_H) / d)
        u = (ang + math.pi) / (2 * math.pi) * W; v = (math.pi / 2 - lat) / math.pi * H
        r = max(1.5, 9 * W / 4096 * 6 / d)
        c = cols[rng.integers(len(cols))]
        dr.ellipse([u - r * 2.5, v - r * 2.5, u + r * 2.5, v + r * 2.5], fill=c + (60,))
        dr.line([u - r * 3, v, u + r * 3, v], fill=c + (220,), width=max(1, int(r / 2)))
        dr.line([u, v - r * 3, u, v + r * 3], fill=c + (220,), width=max(1, int(r / 2)))
        dr.ellipse([u - r / 2, v - r / 2, u + r / 2, v + r / 2], fill=(255, 255, 255, 255))
    return lay.filter(ImageFilter.GaussianBlur(0.6))

def star_layer(T, rng, n):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(lay)
    for _ in range(n):
        zz = rng.uniform(0.05, 1.0); lat = math.asin(zz); lon = rng.uniform(-math.pi, math.pi)
        u = (lon + math.pi) / (2 * math.pi) * W; v = (math.pi / 2 - lat) / math.pi * H
        r = rng.choice([0.6, 0.8, 1.0, 1.4, 2.0], p=[0.4, 0.3, 0.17, 0.09, 0.04]) * W / 4096
        rx = r / max(math.cos(lat), 0.05)
        b = int(rng.uniform(150, 255))
        dr.ellipse([u - rx, v - r, u + rx, v + r], fill=(b, b, 255, 255))
    return lay

# ---------------------------------------------------------------- escena
def build(name, T, seed):
    print('render', name, flush=True)
    rng = np.random.default_rng(seed)
    bg = render_background(T, seed)
    img = Image.fromarray((np.clip(bg, 0, 1) ** 1.0 * 255).astype(np.uint8), 'RGB').convert('RGBA')
    if T['stars']:
        stars = star_layer(T, rng, T['stars'])
        sky_mask = Image.fromarray((np.clip(bg.mean(-1), 0, 1) < 0.35).astype(np.uint8) * 255, 'L')
        sky_mask = Image.fromarray((np.array(sky_mask) * (np.arange(H)[:, None] < H // 2 - 4)).astype(np.uint8))
        img.paste(stars, (0, 0), ImageChops.multiply(stars.split()[3], sky_mask))

    objs = []
    # arboles: bosque alrededor del sendero
    kinds = {'mixed': ['pine', 'round'], 'pine': ['pine'], 'round': ['round', 'round', 'pine'], 'lollipop': ['lollipop']}[T['trees']]
    count = 0
    while count < 260:
        d = rng.uniform(9, 90) if rng.random() < 0.35 else rng.uniform(28, 90)
        a = rng.uniform(-math.pi, math.pi)
        wx, wz = d * math.sin(a), d * math.cos(a)
        if abs(wx - float(path_center(np.array(wz)))) < PATH_W + 2.5:
            continue
        k = kinds[rng.integers(len(kinds))]
        col = T['tree_cols'][rng.integers(len(T['tree_cols']))] * rng.uniform(0.9, 1.1)
        h = rng.uniform(5, 10) if k == 'pine' else rng.uniform(4.5, 8)
        objs.append(('tree', wx, wz, h, k, np.clip(col, 0, 1)))
        count += 1
    # unicornios a lo largo del sendero (adelante y atras) + algunos en la pradera
    spots = [(4.5, 1.25), (8.5, -1.5), (-5.5, -1.3), (14, 1.9), (-11, 1.7)]
    for i, (zz, off) in enumerate(spots):
        wx = float(path_center(np.array(zz))) + off
        objs.append(('uni', wx, zz, rng.uniform(1.9, 2.25), i % len(T['unicorns']), rng.random() < 0.5))
    for _ in range(3):
        d = rng.uniform(6, 13); a = rng.uniform(0.9, 2.2) * rng.choice([-1, 1])
        objs.append(('uni', d * math.sin(a), d * math.cos(a), rng.uniform(1.8, 2.1),
                     int(rng.integers(len(T['unicorns']))), rng.random() < 0.5))

    objs.sort(key=lambda o: -math.hypot(o[1], o[2]))
    trunk = T['trunk']
    for o in objs:
        if o[0] == 'tree':
            _, wx, wz, h, k, col = o
            if math.hypot(wx, wz) < 30: shadow(img, wx, wz, 1.6, T)
            place(img, tree_sprite(k, col, trunk, rng), wx, wz, h, T, flip=rng.random() < 0.5)
        else:
            _, wx, wz, h, idx, flip = o
            body, mane, horn = T['unicorns'][idx]
            spr, frac = unicorn_sprite(body, mane, horn, glow=T['glow'])
            shadow(img, wx, wz, 1.3, T)
            place(img, spr, wx, wz, h, T, flip=flip)

    if T['sparkles']:
        img.alpha_composite(sparkle_layer(T, rng, T['sparkles']))
    path = os.path.join(OUT, f'sendero_unicornios_{name}_{W}x{H}.jpg')
    img.convert('RGB').save(path, quality=93)
    print('  ->', path, flush=True)

if __name__ == '__main__':
    only = sys.argv[2] if len(sys.argv) > 2 else None
    for i, (name, T) in enumerate(THEMES.items()):
        if only and only not in name: continue
        build(name, T, 100 + i * 31)
