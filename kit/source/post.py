"""2D finishing pass for the site videos: upscale, bloom, smoke, embers, rain, lightning, grade.

Every effect is a periodic function of the frame index over the loop length N, so frame N would be
frame 0 again and the loop has no seam.

python post.py <preset> <frames_dir> <out_dir> [--only 0,48] [--size 1920x1080]
Reads <frames_dir>/f_0000.png.. and <frames_dir>/fx.json (marker positions projected per frame).
"""
import sys, os, json, math, glob, random
import numpy as np
import cv2

TAU = math.tau


# --- periodic noise ---------------------------------------------------------------------------

def tile_noise(size, beta, seed):
    """Tileable fractal noise in 0..1 (an inverse FFT of a 1/f^beta spectrum)."""
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.fftfreq(size)[None, :]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1
    amp = 1.0 / f ** beta
    amp[0, 0] = 0
    ph = rng.uniform(0, TAU, (size, size))
    spec = amp * np.exp(1j * ph)
    n = np.real(np.fft.ifft2(spec))
    n = (n - n.min()) / (n.max() - n.min())
    return n.astype(np.float32)


NOISE = {}


def noise(name, size=512, beta=1.6, seed=1):
    if name not in NOISE:
        NOISE[name] = tile_noise(size, beta, seed)
    return NOISE[name]


def sample(tex, u, v):
    """Samples a tileable texture at (u, v) in tile units (any range), bilinear, wrapping."""
    s = tex.shape[0]
    return cv2.remap(tex, (u * s).astype(np.float32) % s, (v * s).astype(np.float32) % s, cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_WRAP)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def pnoise1(t, seed, harm=((1, 1.0), (3, 0.5), (7, 0.25))):
    """A periodic 1D noise of t in 0..1 (loop phase), about -1..1."""
    r = random.Random(seed)
    s = 0
    n = 0
    for k, a in harm:
        s += a * math.sin(TAU * (k * t) + r.random() * TAU)
        n += a
    return s / n


# --- effects ----------------------------------------------------------------------------------

def blur(img, sigma):
    if sigma <= 0:
        return img
    h, w = img.shape[:2]
    # blur at reduced size for big sigmas
    f = 1
    while sigma / f > 6 and min(h, w) // (f * 2) > 16:
        f *= 2
    if f > 1:
        small = cv2.resize(img, (w // f, h // f), interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (0, 0), sigma / f)
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    return cv2.GaussianBlur(img, (0, 0), sigma)


def bloom(img, thr, strength, tint=(1.0, 0.85, 0.7), scales=(3, 10, 28, 70)):
    lum = img.max(axis=2, keepdims=True)
    k = np.clip((lum - thr) / (1 - thr + 1e-6), 0, None)
    bright = img * k
    acc = np.zeros_like(img)
    for i, s in enumerate(scales):
        acc += blur(bright, s) * (1.0 / (1 + i * 0.35))
    return img + acc * strength * np.array(tint, np.float32), acc


def smoke_plume(out, glow, m, P, t, cfg):
    """A column of smoke rising from marker m (screen position P = [x, y, depth, px_per_m])."""
    H, W = out.shape[:2]
    if P[2] <= 0:
        return
    x0, y0, ppm = P[0] * W, P[1] * H, P[3]
    w = m.get("width", 1.0) * ppm
    h = m.get("height", 5.0) * ppm
    xa, xb = int(max(0, x0 - w * 2.4)), int(min(W, x0 + w * 2.4))
    ya, yb = int(max(0, y0 - h)), int(min(H, y0 + 0.1 * h))
    if xb <= xa or yb <= ya:
        return
    yy, xx = np.mgrid[ya:yb, xa:xb].astype(np.float32)
    v = (y0 - yy) / h  # 0 base .. 1 top
    sway = 0.12 * np.sin(TAU * (v * 1.2 - t)) * v
    u = (xx - x0) / w - sway - cfg.get("wind", 0.0) * v * v
    spread = 0.45 + 1.1 * np.clip(v, 0, 1)
    mask = np.exp(-(u / spread) ** 2 * 1.6) * smoothstep(-0.02, 0.12, v) * (1 - smoothstep(0.4, 1.0, v))
    seed = m.get("seed", int(abs(m["loc"][0] * 7 + m["loc"][1] * 13)) % 97)
    n1 = noise("smoke2", 512, 2.1, 3)
    n2 = noise("warp", 256, 1.8, 5)
    speed = cfg.get("smoke_tiles", 2)  # whole tiles risen per loop
    wu = sample(n2, u * 0.3 + seed * 0.37, v * 0.35 - t * 1) - 0.5
    wv = sample(n2, u * 0.3 + 0.5 + seed * 0.17, v * 0.35 - t * 1 + 0.3) - 0.5
    d = sample(n1, u * 0.28 + wu * 0.9 + seed * 0.11, v * 0.4 - t * speed + wv * 0.8)
    d2 = sample(n1, u * 0.55 + wv * 0.7 + 0.5 + seed * 0.21, v * 0.75 - t * speed * 2 + wu * 0.7)
    ridge = 1 - np.abs(d * 2 - 1)
    ridge2 = 1 - np.abs(d2 * 2 - 1)
    body = np.clip((d - 0.3) * 2.0, 0, 1)
    wisp = np.clip((ridge * 0.6 + ridge2 * 0.4 - 0.55) * 3.0, 0, 1)
    dens = cv2.GaussianBlur(np.clip(body * 0.5 + wisp * 0.8, 0, 1), (0, 0), 1.5) * mask * m.get("rate", 1.0) * cfg.get("smoke_opacity", 0.6)
    a = dens[..., None]
    col = np.array(m.get("color", (0.35, 0.33, 0.32)), np.float32)
    g = glow[ya:yb, xa:xb]
    lit = col * (cfg.get("smoke_ambient", 0.6)) + g * cfg.get("smoke_glow", 2.2) * np.sqrt(col)
    out[ya:yb, xa:xb] = out[ya:yb, xa:xb] * (1 - a) + lit * a


def haze(out, glow, t, cfg):
    H, W = out.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = xx / W
    v = yy / H
    n1 = noise("haze", 512, 1.7, 11)
    n2 = noise("warp", 256, 1.8, 5)
    wu = sample(n2, u * 0.6 + t, v * 0.5) - 0.5
    d = sample(n1, u * 0.7 - t * cfg.get("haze_tiles", 1) + wu * 0.3, v * 0.9 + wu * 0.2)
    band = cfg.get("haze_band", None)
    dens = np.clip((d - 0.35) * 1.8, 0, 1) * cfg.get("haze_opacity", 0.18)
    if band:
        dens *= smoothstep(band[0], band[1], v) * (1 - smoothstep(band[2], band[3], v))
    a = dens[..., None]
    col = np.array(cfg.get("haze_color", (0.3, 0.3, 0.32)), np.float32)
    lit = col * cfg.get("haze_ambient", 0.25) + glow * 1.6 * col
    out[:] = out * (1 - a) + lit * a


class Embers:
    """Sparks rising from markers (and across the screen), each living a whole fraction of the loop."""

    def __init__(self, markers, cfg, n_frames, seed=1):
        self.parts = []
        r = random.Random(seed)
        for mi, m in enumerate(markers):
            if m["kind"] != "embers":
                continue
            for i in range(int(m.get("count", 20) * cfg.get("ember_mult", 1.0))):
                self.parts.append(dict(m=mi, k=r.choice([2, 3, 4]), ph=r.random(), seed=r.randrange(1 << 30),
                                       spread=m.get("spread", 1.0), rise=m.get("rise", 5.0) * r.uniform(0.5, 1.2),
                                       size=r.uniform(0.6, 1.6), hot=r.uniform(0.6, 1.0)))
        for i in range(cfg.get("screen_embers", 0)):
            self.parts.append(dict(m=-1, k=r.choice([1, 2, 2, 3]), ph=r.random(), seed=r.randrange(1 << 30),
                                   size=r.uniform(0.5, 2.4), hot=r.uniform(0.4, 1.0), depth=r.random()))
        self.cfg = cfg
        self.N = n_frames

    def draw(self, out, f, frame_pts):
        H, W = out.shape[:2]
        layer = np.zeros((H, W, 3), np.float32)
        scale = H / 1080.0
        col = np.array(self.cfg.get("ember_color", (1.0, 0.45, 0.12)), np.float32)
        wind = self.cfg.get("ember_wind", 0.3)
        for p in self.parts:
            k = p["k"]
            x = f * k / self.N + p["ph"]
            cyc = int(math.floor(x)) % k
            a = x - math.floor(x)
            r = random.Random(p["seed"] * 31 + cyc)
            pts = []
            for da in (0.0, -0.012):  # head and a short tail
                aa = max(0.0, a + da)
                if p["m"] >= 0:
                    P = frame_pts[p["m"]]
                    if P[2] <= 0:
                        break
                    ppm = P[3]
                    rr = random.Random(p["seed"] * 31 + cyc)
                    ang = rr.random() * TAU
                    rad = math.sqrt(rr.random()) * p["spread"]
                    sx = math.cos(ang) * rad
                    sy = math.sin(ang) * rad * 0.5
                    sw = rr.uniform(0.2, 0.7)
                    sp = rr.random()
                    rise = p["rise"] * (aa ** 0.85)
                    dx = sx + sw * math.sin(TAU * (aa * 1.4 + sp)) * aa + wind * aa * p["rise"] * 0.3
                    px = P[0] * W + dx * ppm
                    py = P[1] * H + sy * ppm - rise * ppm
                else:
                    rr = random.Random(p["seed"] * 31 + cyc)
                    x0 = rr.random() * 1.2 - 0.1
                    sp = rr.random()
                    depth = p["depth"]
                    px = (x0 + wind * 0.25 * aa + 0.03 * math.sin(TAU * (aa * 2 + sp))) * W
                    py = (1.05 - aa * (0.8 + 0.5 * depth) * 1.1) * H
                pts.append((px, py))
            if len(pts) < 2:
                continue
            life = smoothstep(0.0, 0.06, a) * (1 - a) ** 1.4
            fl = 0.65 + 0.35 * math.sin(TAU * (a * 9 + p["ph"] * 5))
            b = life * fl * p["hot"] * self.cfg.get("ember_gain", 1.6)
            if p["m"] < 0:
                b *= 0.6 + 0.6 * p["depth"]
            c = (col * b).tolist()
            th = max(1, int(round(p["size"] * scale * (1.6 if p["m"] < 0 and p["depth"] > 0.8 else 1))))
            (x1, y1), (x2, y2) = pts
            cv2.line(layer, (int(x1 * 4), int(y1 * 4)), (int(x2 * 4), int(y2 * 4)), c, th, cv2.LINE_AA, 2)
        glow = blur(layer, 4 * scale)
        out += layer + glow * 2.5


class Rain:
    def __init__(self, cfg, n_frames, W, H, seed=3):
        r = random.Random(seed)
        self.drops = []
        n = cfg.get("rain_count", 900)
        ang = cfg.get("rain_angle", 0.18)
        for i in range(n):
            depth = r.random()
            length = (0.03 + 0.06 * depth) * H
            span = H + length + 40
            cycles = r.choice([3, 4, 5]) if depth > 0.4 else r.choice([2, 3])
            self.drops.append(dict(x=r.random() * (W + H * ang) - H * ang * 0.5, y=r.random() * span, len=length,
                                   v=cycles * span / n_frames, span=span, depth=depth,
                                   a=(0.08 + 0.22 * depth) * cfg.get("rain_gain", 1.0)))
        self.ang = ang
        self.cfg = cfg

    def draw(self, out, f, flash=0.0):
        H, W = out.shape[:2]
        layer = np.zeros((H, W, 3), np.float32)
        col = np.array(self.cfg.get("rain_color", (0.6, 0.7, 0.85)), np.float32)
        for d in self.drops:
            y = (d["y"] + f * d["v"]) % d["span"] - d["len"] - 20
            x = d["x"] + y * self.ang
            x2 = x - d["len"] * self.ang
            y2 = y - d["len"]
            c = (col * d["a"] * (1 + flash * 3)).tolist()
            cv2.line(layer, (int(x * 4), int(y * 4)), (int(x2 * 4), int(y2 * 4)), c, 1, cv2.LINE_AA, 2)
        out += blur(layer, 0.6)


def grade(img, cfg):
    lift = np.array(cfg.get("lift", (0.012, 0.012, 0.02)), np.float32)
    gain = np.array(cfg.get("gain", (1.0, 1.0, 1.0)), np.float32)
    img = img * gain
    # soft shoulder
    img = img / (1 + np.maximum(img - 0.8, 0) * 0.9)
    # contrast around mid grey
    c = cfg.get("contrast", 1.1)
    img = np.clip(img, 0, None)
    img = 0.5 * (2 * img) ** c / (1 + 0 * img) if False else img
    pivot = 0.35
    img = pivot * (img / pivot) ** c
    sat = cfg.get("saturation", 1.05)
    lum = img.mean(axis=2, keepdims=True)
    img = lum + (img - lum) * sat
    img = img + lift * (1 - np.clip(img, 0, 1))
    return img


def vignette(H, W, amount, power=2.2):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx = (xx / W - 0.5) * 2
    dy = (yy / H - 0.5) * 2
    r = np.sqrt(dx * dx * 0.8 + dy * dy * 1.0)
    return (1 - amount * np.clip(r, 0, 1.5) ** power)[..., None].astype(np.float32)


# --- presets --------------------------------------------------------------------------------------

PRESETS = {
    "c1": dict(bloom_thr=0.5, bloom=0.45, bloom_tint=(1.0, 0.75, 0.5), smoke_opacity=0.7, smoke_glow=2.4, ember_mult=2.0, ember_gain=2.2,
               smoke_ambient=0.55, haze_opacity=0.12, haze_color=(0.32, 0.29, 0.27), haze_band=(0.0, 0.0, 0.7, 1.0),
               screen_embers=90, ember_wind=0.25, vignette=0.55, contrast=1.15, saturation=0.95,
               lift=(0.010, 0.010, 0.016), gain=(1.08, 1.02, 0.98), paint=True),
    "c2": dict(bloom_thr=0.5, bloom=0.5, bloom_tint=(0.85, 0.9, 1.0), smoke_opacity=0.4, haze_opacity=0.16,
               haze_color=(0.28, 0.31, 0.38), haze_tiles=2, rain=True, rain_count=1100, rain_angle=0.22,
               rain_color=(0.55, 0.65, 0.85), screen_embers=0, vignette=0.6, contrast=1.1, saturation=1.0,
               lift=(0.008, 0.012, 0.022), gain=(1.12, 1.15, 1.25), paint=True,
               flash_damp=0.45, flash_overlay=0.1),
    "c3": dict(bloom_thr=0.48, bloom=0.55, bloom_tint=(1.0, 0.85, 0.65), smoke_opacity=0.35, haze_opacity=0.18,
               haze_color=(0.26, 0.33, 0.33), rain=True, rain_count=700, rain_angle=0.06,
               rain_color=(0.6, 0.75, 0.75), rain_gain=0.8, screen_embers=0, vignette=0.6, contrast=1.1,
               saturation=1.0, lift=(0.006, 0.013, 0.015), gain=(1.0, 1.02, 1.02), paint=True),
    "boss": dict(bloom_thr=0.45, bloom=0.55, bloom_tint=(1.0, 0.75, 0.5), smoke_opacity=0.4, haze_opacity=0.14,
                 haze_color=(0.3, 0.27, 0.26), haze_band=(0.3, 0.6, 1.1, 1.2), screen_embers=90, ember_wind=0.15,
                 vignette=0.6, contrast=1.12, saturation=1.06, lift=(0.010, 0.010, 0.016), paint=True),
    "boss_storm": dict(bloom_thr=0.5, bloom=0.5, bloom_tint=(0.9, 0.9, 1.0), smoke_opacity=0.4, haze_opacity=0.12,
                       haze_color=(0.28, 0.31, 0.38), haze_band=(0.3, 0.6, 1.1, 1.2), rain=True, rain_count=700,
                       rain_angle=0.2, rain_color=(0.55, 0.65, 0.85), screen_embers=25, ember_wind=0.3, vignette=0.6,
                       contrast=1.1, saturation=1.0, lift=(0.008, 0.012, 0.022), gain=(1.05, 1.08, 1.15), paint=True,
                       flash_damp=0.4, flash_overlay=0.1),
    "boss_rain": dict(bloom_thr=0.5, bloom=0.5, bloom_tint=(1.0, 0.88, 0.7), smoke_opacity=0.35, haze_opacity=0.12,
                      haze_color=(0.26, 0.33, 0.33), haze_band=(0.3, 0.6, 1.1, 1.2), rain=True, rain_count=500,
                      rain_angle=0.05, rain_color=(0.6, 0.75, 0.75), rain_gain=0.7, screen_embers=50,
                      ember_color=(0.75, 0.9, 0.85), ember_gain=0.9, ember_wind=0.05, vignette=0.6, contrast=1.1,
                      saturation=1.0, lift=(0.006, 0.013, 0.015), paint=True),
}


def paint(img8):
    """A light painted finish: edge-preserving smoothing that flattens fine noise into strokes."""
    return cv2.edgePreservingFilter(img8, flags=cv2.RECURS_FILTER, sigma_s=12, sigma_r=0.12)


def main():
    preset, src, dst = sys.argv[1:4]
    only = None
    size = None
    extra = {}
    for i, a in enumerate(sys.argv):
        if a == "--only":
            only = [int(x) for x in sys.argv[i + 1].split(",")]
        if a == "--size":
            size = [int(x) for x in sys.argv[i + 1].split("x")]
        if a == "--set":
            extra.update(json.loads(sys.argv[i + 1]))
    cfg = dict(PRESETS[preset])
    for meta in ("flashes.json", "meta.json"):
        mp = os.path.join(src, meta)
        if os.path.exists(mp):
            md = json.load(open(mp))
            if "flashes" in md:
                cfg["flashes"] = md["flashes"]
    cfg.update(extra)
    fx = json.load(open(os.path.join(src, "fx.json")))
    files = sorted(glob.glob(os.path.join(src, "f_*.png")))
    N = len(fx["frames"])
    W, H = size or (fx["w"], fx["h"])
    os.makedirs(dst, exist_ok=True)
    markers = fx["markers"]
    embers = Embers(markers, cfg, N)
    rain = Rain(cfg, N, W, H) if cfg.get("rain") else None
    vig = vignette(H, W, cfg.get("vignette", 0.5))
    flashes = cfg.get("flashes", [])
    frames = only if only is not None else range(N)
    for f in frames:
        path = os.path.join(src, "f_%04d.png" % f)
        if not os.path.exists(path):
            print("missing", path)
            continue
        im8 = cv2.imread(path)
        if (im8.shape[1], im8.shape[0]) != (W, H):
            im8 = cv2.resize(im8, (W, H), interpolation=cv2.INTER_LANCZOS4)
        if cfg.get("paint"):
            im8 = paint(im8)
        img = im8[..., ::-1].astype(np.float32) / 255.0
        t = f / N
        flash = 0.0
        for fr, strength in flashes:
            d = (f - fr) % N
            if d < 10:
                flash = max(flash, strength * math.exp(-d / 2.2) * (1 if d != 1 else 0.4))
        if flash > 0 and cfg.get("flash_damp", 0) > 0:
            # the rendered flash is far brighter than the rest of the loop: pull it back and
            # roll the highlights off so bloom does not wash the frame white
            img = img * (1 - cfg["flash_damp"] * flash)
            img = img / (1 + img * cfg["flash_damp"] * flash)
        img, glow_src = bloom(img, cfg["bloom_thr"], cfg["bloom"], cfg.get("bloom_tint", (1, 1, 1)))
        glow = blur(img, 45 * H / 1080) * 0.5 + blur(glow_src, 30 * H / 1080)
        if cfg.get("haze_opacity", 0) > 0:
            haze(img, glow, t, cfg)
        pts = fx["frames"][f]
        for mi, m in enumerate(markers):
            if m["kind"] == "smoke":
                smoke_plume(img, glow, m, pts[mi], t, cfg)
        if rain:
            rain.draw(img, f, flash)
        embers.draw(img, f, pts)
        if flash > 0:
            img += np.array(cfg.get("flash_color", (0.35, 0.45, 0.7)), np.float32) * flash * cfg.get("flash_overlay", 0.25)
        img = grade(img, cfg)
        img *= vig
        out = np.clip(img * 255 + np.random.default_rng(f).normal(0, 0.0, img.shape) , 0, 255).astype(np.uint8)
        cv2.imwrite(os.path.join(dst, "p_%04d.png" % f), out[..., ::-1])
        print("post", f, flush=True)


if __name__ == "__main__":
    main()
