"""Generate the contact QRs and the phone-screen card images.

Contato-QR.png       -> QR da pagina do cartao (funciona em qualquer celular)
Contato-QR-vcard.png -> QR de vCard (abre a ficha de contato no iPhone / Google Lens)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import qr
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
FONTS = r"C:\Windows\Fonts"

PAGE = "https://rossetoengenharia.com.br/cartao/"
VCARD = "\r\n".join([
    "BEGIN:VCARD",
    "VERSION:3.0",
    "FN:Filipe Nogueira Rosseto",
    "ORG:Rosseto Engenharia",
    "TITLE:Engenheiro Mecânico",
    "TEL:+5515981307575",
    "EMAIL:eng.rosseto@gmail.com",
    "URL:https://rossetoengenharia.com.br/",
    "END:VCARD",
])

NAVY = (14, 35, 64)
NAVY_2 = (20, 48, 84)
WHITE = (255, 255, 255)
SOFT = (185, 203, 224)
ACCENT = (245, 166, 35)


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def make_card(payload, out_name, title, sub, note):
    version, matrix = qr.build(payload)
    print(f"{out_name}: {len(payload.encode())} bytes, v{version}, {len(matrix)}x{len(matrix)}")

    raw = f"qr-{'link' if payload == PAGE else 'vcard'}"
    with open(os.path.join(ASSETS, f"{raw}.svg"), "w", encoding="utf-8") as f:
        f.write(qr.to_svg(matrix, quiet=4, dark="#0e2340"))
    qr.to_png(matrix, os.path.join(ASSETS, f"{raw}.png"), scale=16, quiet=4)

    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        c = tuple(int(NAVY[i] + (NAVY_2[i] - NAVY[i]) * (1 - t)) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    for x in range(0, W, 60):
        gd.line([(x, 0), (x, H)], fill=(255, 255, 255, 12))
    for y in range(0, H, 60):
        gd.line([(0, y), (W, y)], fill=(255, 255, 255, 12))
    img = Image.alpha_composite(img.convert("RGBA"), grid).convert("RGB")
    d = ImageDraw.Draw(img)

    f_bold = font("segoeuib.ttf", 74)
    f_sub = font("segoeui.ttf", 34)
    f_name = font("segoeuib.ttf", 46)
    f_small = font("segoeui.ttf", 30)
    f_brand = font("segoeuib.ttf", 42)
    f_brand_s = font("segoeui.ttf", 18)
    f_url = font("segoeuib.ttf", 30)

    def center(text, fnt, y, fill=WHITE):
        b = d.textbbox((0, 0), text, font=fnt)
        d.text(((W - (b[2] - b[0])) / 2 - b[0], y), text, font=fnt, fill=fill)

    disc, dx, dy = 118, 72, 86
    d.ellipse([dx, dy, dx + disc, dy + disc], fill=WHITE)
    em = Image.open(os.path.join(ASSETS, "emblema.png")).convert("RGB")
    ew = int(disc * 0.74)
    em = em.resize((ew, int(ew * em.height / em.width)), Image.LANCZOS)
    img.paste(em, (dx + (disc - em.width) // 2, dy + (disc - em.height) // 2))
    d.text((dx + disc + 30, dy + 24), "ROSSETO", font=f_brand, fill=WHITE)
    d.text((dx + disc + 32, dy + 74), "E N G E N H A R I A", font=f_brand_s, fill=(160, 184, 210))

    center(title, f_bold, 300)
    center(sub, f_sub, 400, SOFT)

    d.rounded_rectangle([88, 500, W - 88, 1400], radius=48, fill=WHITE)
    qsize = 780
    qx, qy = (W - qsize) // 2, 500 + (900 - qsize) // 2
    qimg = Image.open(os.path.join(ASSETS, f"{raw}.png")).convert("RGB").resize((qsize, qsize), Image.NEAREST)
    img.paste(qimg, (qx, qy))
    d = ImageDraw.Draw(img)

    center("Filipe Nogueira Rosseto", f_name, 1470)
    center("Engenheiro Mecânico · CREA-SP 5068959316", f_small, 1532, SOFT)
    center("(15) 98130-7575  ·  eng.rosseto@gmail.com", f_small, 1580, SOFT)
    d.line([(W // 2 - 60, 1680), (W // 2 + 60, 1680)], fill=ACCENT, width=4)
    center("rossetoengenharia.com.br", f_url, 1730, WHITE)
    center(note, f_small, 1800, (140, 165, 190))

    img.save(os.path.join(ROOT, out_name), optimize=True)
    print("  ->", out_name)


make_card(
    PAGE,
    "Contato-QR.png",
    "Meu cartão digital",
    "Aponte a câmera do celular",
    "Abrir  →  Salvar contato",
)

make_card(
    VCARD,
    "Contato-QR-vcard.png",
    "Adicione meu contato",
    "Aponte a câmera do celular",
    "Toque em “Adicionar” quando a ficha abrir",
)
