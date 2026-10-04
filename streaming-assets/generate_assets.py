#!/usr/bin/env python3
"""Generate retrotech (Ostranauts-inspired) channel assets for Daviaze.

Palette: navy/dark backgrounds, cyan-blue accents, gray text.
Style: scanlines, perspective grid, corner brackets, phosphor glow.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, os

OUT = os.path.expanduser("~/Projects/ai-workspace/streaming-assets")
os.makedirs(OUT, exist_ok=True)

# ── palette ──────────────────────────────────────────────────────
BG_DARK   = (10, 14, 26)       # near-black navy
BG_PANEL  = (16, 22, 40)       # panel navy
BLUE      = (33, 150, 243)     # primary blue
CYAN      = (79, 195, 247)     # accent cyan
GRAY      = (158, 163, 176)    # neutral gray
DIMGRAY   = (70, 78, 96)
WHITE     = (235, 240, 248)

FONT_BOLD = os.path.expanduser("~/.local/share/fonts/Montserrat-Bold.ttf")
FONT_REG  = os.path.expanduser("~/.local/share/fonts/Montserrat-Regular.ttf")

def f(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)

def scanlines(img, gap=4, alpha=28):
    """Horizontal scanline overlay."""
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(0, img.size[1], gap):
        d.line([(0, y), (img.size[0], y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), ov)

def grid(img, horizon_ratio=0.45, color=BLUE, alpha=36):
    """Perspective floor grid, retrotech staple."""
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    W, H = img.size
    hy = int(H * horizon_ratio)
    cx = W // 2
    # verticals fanning from center
    for i in range(-14, 15):
        x_bottom = cx + i * (W // 7)
        d.line([(cx + i * 8, hy), (x_bottom, H)], fill=color + (alpha,), width=2)
    # horizontals, denser near horizon
    for i in range(1, 16):
        t = i / 16
        y = hy + int((H - hy) * (t ** 2.2))
        d.line([(0, y), (W, y)], fill=color + (alpha,), width=2)
    return Image.alpha_composite(img.convert("RGBA"), ov)

def corner_brackets(d, box, length=60, width=6, color=CYAN):
    """HUD corner brackets around box=(x0,y0,x1,y1)."""
    x0, y0, x1, y1 = box
    for (sx, sy) in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
        cx = x0 if sx == 1 else x1
        cy = y0 if sy == 1 else y1
        d.line([(cx, cy), (cx + sx * length, cy)], fill=color, width=width)
        d.line([(cx, cy), (cx, cy + sy * length)], fill=color, width=width)

def glow_text(img, xy, text, font, fill, glow=BLUE, radius=18, anchor="mm"):
    """Text with soft phosphor glow."""
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.text(xy, text, font=font, fill=glow + (160,), anchor=anchor)
    ov = ov.filter(ImageFilter.GaussianBlur(radius))
    img = Image.alpha_composite(img.convert("RGBA"), ov)
    d = ImageDraw.Draw(img)
    d.text(xy, text, font=font, fill=fill, anchor=anchor)
    return img

def vhs_distortion(img, band_alpha=24):
    """A couple of horizontal tracking bands."""
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    W, H = img.size
    for y, h in [(int(H * 0.18), 3), (int(H * 0.67), 5)]:
        d.rectangle([0, y, W, y + h], fill=(200, 230, 255, band_alpha))
    return Image.alpha_composite(img.convert("RGBA"), ov)

def base_canvas(W=1920, H=1080):
    img = Image.new("RGBA", (W, H), BG_DARK + (255,))
    d = ImageDraw.Draw(img)
    # subtle vignette
    vig = Image.new("L", (W, H), 0)
    dv = ImageDraw.Draw(vig)
    dv.ellipse([-W * 0.35, -H * 0.45, W * 1.35, H * 1.45], fill=90)
    vig = vig.filter(ImageFilter.GaussianBlur(200))
    black = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    img = Image.composite(img, black, vig.point(lambda p: 255 - p))
    return img

# ── 1. starting-soon.png ─────────────────────────────────────────
img = base_canvas()
img = grid(img)
img = vhs_distortion(img)
img = glow_text(img, (960, 420), "DAVIAZE", f(150), WHITE, glow=BLUE, radius=26)
img = glow_text(img, (960, 580), "INICIANDO TRANSMISSÃO", f(64), CYAN, glow=CYAN, radius=14)
d = ImageDraw.Draw(img)
d.line([(660, 660), (1260, 660)], fill=GRAY + (140,), width=3)
corner_brackets(d, (560, 300, 1360, 720), length=80, width=7)
img = scanlines(img)
img.convert("RGB").save(f"{OUT}/starting-soon.png")

# ── 2. brb.png ───────────────────────────────────────────────────
img = base_canvas()
img = grid(img, horizon_ratio=0.55)
img = vhs_distortion(img)
img = glow_text(img, (960, 460), "DAVIAZE", f(120), WHITE, glow=BLUE, radius=24)
img = glow_text(img, (960, 620), "PAUSA — VOLTO JÁ", f(72), CYAN, glow=CYAN, radius=14)
d = ImageDraw.Draw(img)
d.line([(660, 700), (1260, 700)], fill=GRAY + (140,), width=3)
corner_brackets(d, (600, 320, 1320, 740), length=80, width=7)
img = scanlines(img)
img.convert("RGB").save(f"{OUT}/brb.png")

# ── 3. just-chatting.png (bg, cam goes center) ───────────────────
img = base_canvas()
img = grid(img, horizon_ratio=0.5)
img = glow_text(img, (960, 140), "DAVIAZE", f(90), WHITE, glow=BLUE, radius=22)
img = glow_text(img, (960, 230), "// CONVERSANDO", f(44), GRAY, glow=DIMGRAY, radius=10)
d = ImageDraw.Draw(img)
corner_brackets(d, (560, 320, 1360, 940), length=80, width=7)
img = scanlines(img)
img.convert("RGB").save(f"{OUT}/just-chatting.png")

# ── 4. logo-daviaze.png (800x800, transparent bg) ────────────────
S = 800
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
# hexagonal badge
cx, cy, r = S // 2, S // 2, 340
pts = [(cx + r * math.cos(math.radians(60 * i - 30)),
        cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]
d.polygon(pts, fill=BG_PANEL + (255,), outline=BLUE + (255,))
inner = [(cx + (r - 26) * math.cos(math.radians(60 * i - 30)),
          cy + (r - 26) * math.sin(math.radians(60 * i - 30))) for i in range(6)]
d.polygon(inner, outline=CYAN + (200,))
img = glow_text(img, (cx, cy - 40), "D", f(300), WHITE, glow=BLUE, radius=30)
img = glow_text(img, (cx, cy + 150), "DAVIAZE", f(64), CYAN, glow=CYAN, radius=12)
img = scanlines(img, gap=5, alpha=22)
img.save(f"{OUT}/logo-daviaze.png")

# ── 5. cam-frame.png (960x540, transparent center) ──────────────
W, H = 960, 540
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
pad = 14
d.rounded_rectangle([pad, pad, W - pad, H - pad], radius=24,
                    fill=BG_PANEL + (200,), outline=BLUE + (255,), width=6)
d.rounded_rectangle([pad + 10, pad + 10, W - pad - 10, H - pad - 10], radius=18,
                    outline=CYAN + (140,), width=2)
corner_brackets(d, (pad - 4, pad - 4, W - pad + 4, H - pad + 4), length=56, width=8)
img = scanlines(img, gap=4, alpha=12)
img.save(f"{OUT}/cam-frame.png")

# ── 6. bottom-bar.png (1920x90 strip: REC dot + label slots) ─────
W, H = 1920, 90
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rectangle([0, 0, W, H], fill=BG_PANEL + (215,))
d.line([(0, 0), (W, 0)], fill=BLUE + (255,), width=4)
# REC indicator
d.ellipse([28, 28, 62, 62], fill=(229, 57, 53, 255))
d.text((84, 45), "LIVE", font=f(40), fill=WHITE, anchor="lm")
d.text((W - 40, 45), "// DAVIAZE", font=f(34), fill=CYAN, anchor="rm")
img.save(f"{OUT}/bottom-bar.png")

# ── 7. avatar.png (256x256 round avatar from logo) ───────────────
logo = Image.open(f"{OUT}/logo-daviaze.png").resize((512, 512))
mask = Image.new("L", (512, 512), 0)
dm = ImageDraw.Draw(mask)
dm.ellipse([0, 0, 512, 512], fill=255)
avatar = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
avatar.paste(logo, (0, 0), mask)
avatar.resize((256, 256)).save(f"{OUT}/avatar.png")

print("generated:", sorted(os.listdir(OUT)))
