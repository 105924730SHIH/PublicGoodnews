"""
產生 PWA 所需的各尺寸圖示 (icons/)。

安裝套件：
    pip install pillow

執行：
    python gen_icons.py

會在 ./icons 資料夾產生：
    icon-16.png
    icon-32.png
    icon-72.png
    icon-96.png
    icon-128.png
    icon-144.png
    icon-152.png
    icon-180.png   (Apple touch icon)
    icon-192.png
    icon-192-maskable.png
    icon-384.png
    icon-512.png
    icon-512-maskable.png
    favicon.ico
"""

import os
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

# 一般圖示尺寸 (含安全邊界內容，適合當作 any 用途)
SIZES = [16, 32, 72, 96, 128, 144, 152, 180, 192, 384, 512]
# 額外產生 maskable 版本（內容縮小一些，避免被系統裁切遮罩吃掉）
MASKABLE_SIZES = [192, 512]

BG_TOP = (79, 70, 229)      # #4F46E5 indigo
BG_BOTTOM = (6, 182, 212)   # #06B6D4 cyan
FG = (255, 255, 255)


def make_gradient_square(size: int) -> Image.Image:
    """畫一張由左上到右下的漸層方形底圖。"""
    img = Image.new("RGB", (size, size), BG_TOP)
    draw = ImageDraw.Draw(img)
    for y in range(size):
        t = y / max(size - 1, 1)
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b))
    return img


def add_rounded_corners(img: Image.Image, radius_ratio: float = 0.22) -> Image.Image:
    size = img.size[0]
    radius = int(size * radius_ratio)
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=radius, fill=255)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def draw_bar_chart_glyph(draw: ImageDraw.ImageDraw, size: int, scale: float = 1.0):
    """畫一個簡單的長條圖示意圖 (呼應「每日彙整快報」的圖表意象)。"""
    bar_count = 3
    margin = size * (0.30 if scale >= 1.0 else 0.38)
    usable = size - 2 * margin
    gap = usable * 0.18
    bar_w = (usable - gap * (bar_count - 1)) / bar_count
    heights = [0.45, 0.75, 0.95]
    base_y = size - margin
    for i, h_ratio in enumerate(heights):
        x0 = margin + i * (bar_w + gap)
        x1 = x0 + bar_w
        bar_h = usable * h_ratio
        y0 = base_y - bar_h
        y1 = base_y
        radius = bar_w * 0.28
        draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=FG)


def make_icon(size: int, maskable: bool = False) -> Image.Image:
    base = make_gradient_square(size)
    draw = ImageDraw.Draw(base)
    # maskable 圖示的安全區域較小，內容需要往內縮
    scale = 0.82 if maskable else 1.0
    draw_bar_chart_glyph(draw, size, scale=scale)

    rgba = base.convert("RGBA")
    if not maskable:
        rgba = add_rounded_corners(rgba)
    return rgba


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for size in SIZES:
        icon = make_icon(size, maskable=False)
        path = os.path.join(OUT_DIR, f"icon-{size}.png")
        icon.save(path, format="PNG")
        print(f"已產生 {path}")

    for size in MASKABLE_SIZES:
        icon = make_icon(size, maskable=True)
        path = os.path.join(OUT_DIR, f"icon-{size}-maskable.png")
        icon.save(path, format="PNG")
        print(f"已產生 {path}")

    # favicon.ico（內含多種尺寸）
    favicon_sizes = [16, 32, 48]
    favicon_base = make_icon(48, maskable=False)
    favicon_path = os.path.join(OUT_DIR, "favicon.ico")
    favicon_base.save(
        favicon_path,
        format="ICO",
        sizes=[(s, s) for s in favicon_sizes],
    )
    print(f"已產生 {favicon_path}")

    print("\n✅ 全部圖示已產生於：", OUT_DIR)


if __name__ == "__main__":
    main()
