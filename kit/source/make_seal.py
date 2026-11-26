"""Verrier's great seal as a glow mask: rings, a twelve-point star of law, and bands of runes."""
import math, random, sys
from PIL import Image, ImageDraw, ImageFilter
S = 2048
im = Image.new("L", (S, S), 0)
d = ImageDraw.Draw(im)
c = S / 2
def ring(r, w):
    d.ellipse([c - r, c - r, c + r, c + r], outline=255, width=w)
ring(1000, 14); ring(960, 6); ring(780, 10); ring(740, 5); ring(470, 9); ring(440, 4); ring(150, 8)
rnd = random.Random(4)
def glyph(cx, cy, size, ang):
    # an angular rune: a stem and two or three strokes off it
    ca, sa = math.cos(ang), math.sin(ang)
    def P(x, y):
        return (cx + (x * ca - y * sa) * size, cy + (x * sa + y * ca) * size)
    w = max(3, int(size * 0.14))
    d.line([P(0, -0.5), P(0, 0.5)], fill=255, width=w)
    for _ in range(rnd.randint(1, 3)):
        y0 = rnd.choice([-0.5, -0.2, 0.1, 0.3])
        x1 = rnd.choice([-0.35, 0.35])
        y1 = y0 + rnd.choice([-0.3, 0.25, 0.0])
        d.line([P(0, y0), P(x1, y1)], fill=255, width=w)
# two bands of runes
for (r, n, sz) in [(870, 44, 95), (605, 30, 90)]:
    for i in range(n):
        a = math.tau * i / n
        glyph(c + math.sin(a) * r, c - math.cos(a) * r, sz, a)
# twelve-point star of law between the inner rings
pts = []
for i in range(24):
    a = math.tau * i / 24
    rr = 440 if i % 2 == 0 else 200
    pts.append((c + math.sin(a) * rr, c - math.cos(a) * rr))
d.line(pts + [pts[0]], fill=255, width=7)
for i in range(12):
    a = math.tau * i / 12
    d.line([(c + math.sin(a) * 150, c - math.cos(a) * 150), (c + math.sin(a) * 740, c - math.cos(a) * 740)], fill=200, width=4)
# cracks: gaps cut through
for i in range(7):
    a = rnd.random() * math.tau
    r0 = rnd.uniform(200, 900)
    x, y = c + math.sin(a) * r0, c - math.cos(a) * r0
    for k in range(6):
        nx, ny = x + rnd.uniform(-60, 60), y + rnd.uniform(-60, 60)
        d.line([(x, y), (nx, ny)], fill=0, width=10)
        x, y = nx, ny
im = im.filter(ImageFilter.GaussianBlur(1.2))
im.save(sys.argv[1])
