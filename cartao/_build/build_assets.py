import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image

import qr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # cartao/
SITE = os.path.dirname(ROOT)  # Site-Principal/
ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)

# ---------------------------------------------------------------- logo
src = Image.open(os.path.join(SITE, "images", "logo-chatgpt.png")).convert("RGB")
w, h = src.size
px = src.load()
bg = (251, 251, 251)


def is_ink(p):
    return abs(p[0] - bg[0]) + abs(p[1] - bg[1]) + abs(p[2] - bg[2]) > 30


# row ink profile to split emblem from wordmark
rows = []
for y in range(h):
    cnt = 0
    for x in range(0, w, 3):
        if is_ink(px[x, y]):
            cnt += 1
    rows.append(cnt)

thr = max(rows) * 0.02
segments = []
in_seg = False
for y, c in enumerate(rows):
    if c > thr and not in_seg:
        start, in_seg = y, True
    elif c <= thr and in_seg:
        segments.append((start, y))
        in_seg = False
if in_seg:
    segments.append((start, h))
segments = [s for s in segments if s[1] - s[0] > 20]
print("row segments:", segments)


def crop_ink(box):
    x0, y0, x1, y1 = box
    l, r, t, b = x1, x0, y1, y0
    for y in range(y0, y1):
        for x in range(x0, x1):
            if is_ink(px[x, y]):
                l, r = min(l, x), max(r, x)
                t, b = min(t, y), max(b, y)
    pad = 12
    return src.crop((max(0, l - pad), max(0, t - pad), min(w, r + pad), min(h, b + pad)))


def white_out(img):
    """Force the near-white paper of the artwork to pure white (no grey box on white panels)."""
    return img.point(lambda v: 255 if v >= 247 else v)


logo = white_out(crop_ink((0, 0, w, h)))
logo.save(os.path.join(ASSETS, "logo.png"), optimize=True)
print("logo", logo.size)

emblem = white_out(crop_ink((0, segments[0][0], w, segments[0][1])))
emblem.save(os.path.join(ASSETS, "emblema.png"), optimize=True)
print("emblem", emblem.size)

# ---------------------------------------------------------------- photo
ph = Image.open(os.path.join(SITE, "images", "Perfil2.png")).convert("RGB")
pw, phh = ph.size
side = int(min(pw, phh) * 0.86)
cx, cy = int(pw * 0.50), int(phh * 0.40)
box = (cx - side // 2, cy - side // 2, cx + side // 2, cy + side // 2)
box = (
    max(0, box[0]),
    max(0, box[1]),
    min(pw, box[2]),
    min(phh, box[3]),
)
photo = ph.crop(box).resize((760, 760), Image.LANCZOS)
photo.save(os.path.join(ASSETS, "foto.jpg"), quality=88, optimize=True, progressive=True)
print("photo", box, photo.size)

# ---------------------------------------------------------------- emblem watermark (white silhouette)
em = Image.open(os.path.join(ASSETS, "emblema.png")).convert("RGB")
lum = em.convert("L").point(lambda v: 255 - v)
mark = Image.new("RGBA", em.size, (255, 255, 255, 0))
mark.putalpha(lum)
mark.save(os.path.join(ASSETS, "emblema-branco.png"), optimize=True)

# ---------------------------------------------------------------- QRs
TARGETS = {
    "site": "https://rossetoengenharia.com.br/",
    "card": "https://rossetoengenharia.com.br/cartao/",
    "wa": "https://wa.me/5515981307575?text=Ol%C3%A1!%20Vim%20pelo%20seu%20cart%C3%A3o.",
}
for name, payload in TARGETS.items():
    version, matrix = qr.build(payload)
    svg = qr.to_svg(matrix, quiet=0, dark="#0e2340")
    with open(os.path.join(ASSETS, f"qr-{name}.svg"), "w", encoding="utf-8") as f:
        f.write(svg)
    qr.to_png(matrix, os.path.join(ASSETS, f"qr-{name}.png"), scale=16, quiet=4)
    print(f"qr-{name}: v{version} {len(matrix)}x{len(matrix)} payload={len(payload)}b")

# ---------------------------------------------------------------- seal for the back (flat JPEG, no clipping)
from PIL import ImageDraw

seal_size = 512
seal = Image.new("RGB", (seal_size, seal_size), (14, 35, 64))
draw = ImageDraw.Draw(seal)
draw.ellipse((2, 2, seal_size - 3, seal_size - 3), fill=(255, 255, 255))
em_seal = emblem.copy()
target_w = int(seal_size * 0.74)
target_h = int(target_w * em_seal.height / em_seal.width)
em_seal = em_seal.resize((target_w, target_h), Image.LANCZOS)
seal.paste(em_seal, ((seal_size - target_w) // 2, (seal_size - target_h) // 2))
seal.save(os.path.join(ASSETS, "selo.jpg"), quality=94, optimize=True)
print("selo", seal.size)
