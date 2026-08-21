"""
gen_icons.py
============
產生 PWA 所需的各種尺寸 App Icon（存放於 icons/ 資料夾）。

安裝套件：
    pip install Pillow

執行方式：
    python gen_icons.py

會在 icons/ 資料夾中產生：
    icon-72.png
    icon-96.png
    icon-128.png
    icon-144.png
    icon-152.png
    icon-192.png
    icon-384.png
    icon-512.png
    apple-touch-icon.png (180x180，給 iOS 用)
    favicon.png (32x32)
"""

import os
from PIL import Image, ImageDraw, ImageFont

ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

# 主色（與網頁介面配色一致）
COLOR_TOP = (36, 129, 204)      # #2481cc
COLOR_BOTTOM = (70, 179, 230)   # #46b3e6
COLOR_WHITE = (255, 255, 255)


def _gradient_background(size: int) -> Image.Image:
    """畫一個對角漸層的正方形背景。"""
    img = Image.new("RGB", (size, size), COLOR_TOP)
    draw = ImageDraw.Draw(img)
    for y in range(size):
        ratio = y / max(size - 1, 1)
        r = int(COLOR_TOP[0] + (COLOR_BOTTOM[0] - COLOR_TOP[0]) * ratio)
        g = int(COLOR_TOP[1] + (COLOR_BOTTOM[1] - COLOR_TOP[1]) * ratio)
        b = int(COLOR_TOP[2] + (COLOR_BOTTOM[2] - COLOR_TOP[2]) * ratio)
        draw.line([(0, y), (size, y)], fill=(r, g, b))
    return img


def _rounded_mask(size: int, radius_ratio: float = 0.22) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    radius = int(size * radius_ratio)
    draw.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=radius, fill=255)
    return mask


def _draw_bell_glyph(draw: ImageDraw.ImageDraw, size: int):
    """畫一個簡單的「公告鈴鐺 / 訊號波」造型，避免依賴系統字型與 emoji 字型。"""
    cx, cy = size / 2, size / 2 * 0.96
    r = size * 0.20

    # 鈴鐺本體（半圓 + 底部弧形）
    bell_top = cy - r * 1.05
    bell_bottom = cy + r * 0.9
    draw.pieslice(
        [cx - r, bell_top, cx + r, bell_top + r * 2],
        start=180, end=360, fill=COLOR_WHITE,
    )
    draw.rectangle(
        [cx - r, bell_top + r, cx + r, bell_bottom],
        fill=COLOR_WHITE,
    )
    draw.pieslice(
        [cx - r * 1.15, bell_bottom - r * 0.5, cx + r * 1.15, bell_bottom + r * 0.5],
        start=0, end=180, fill=COLOR_WHITE,
    )
    # 鈴鐺提把
    handle_r = r * 0.22
    draw.ellipse(
        [cx - handle_r, bell_top - handle_r * 1.6, cx + handle_r, bell_top + handle_r * 0.4],
        fill=COLOR_WHITE,
    )
    # 鈴鐺底部的小圓（鈴舌）
    clapper_r = r * 0.16
    draw.ellipse(
        [cx - clapper_r, bell_bottom + r * 0.12, cx + clapper_r, bell_bottom + r * 0.12 + clapper_r * 2],
        fill=COLOR_WHITE,
    )

    # 兩側的訊號波弧線，呼應「資訊推播」意象
    wave_width = max(2, int(size * 0.03))
    for i, dr in enumerate([r * 1.6, r * 2.15]):
        bbox_l = [cx - dr, cy - dr, cx + dr, cy + dr]
        draw.arc(bbox_l, start=200, end=250, fill=COLOR_WHITE, width=wave_width)
        draw.arc(bbox_l, start=290, end=340, fill=COLOR_WHITE, width=wave_width)


def make_icon(size: int) -> Image.Image:
    base = _gradient_background(size)
    mask = _rounded_mask(size)
    rounded = Image.new("RGB", (size, size), COLOR_TOP)
    rounded.paste(base, (0, 0), mask)

    draw = ImageDraw.Draw(rounded)
    _draw_bell_glyph(draw, size)

    # 加上圓角遮罩，讓最終輸出邊角透明化以符合 maskable icon 慣例
    final = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    final.paste(rounded, (0, 0), mask)
    return final


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for size in ICON_SIZES:
        icon = make_icon(size)
        path = os.path.join(OUTPUT_DIR, f"icon-{size}.png")
        icon.save(path, "PNG")
        print(f"✅ 已產生 {path}")

    # iOS 用的 apple-touch-icon
    apple_icon = make_icon(180)
    apple_icon.save(os.path.join(OUTPUT_DIR, "apple-touch-icon.png"), "PNG")
    print("✅ 已產生 apple-touch-icon.png")

    # 瀏覽器分頁用的 favicon
    favicon = make_icon(32)
    favicon.save(os.path.join(OUTPUT_DIR, "favicon.png"), "PNG")
    print("✅ 已產生 favicon.png")

    print("\n🎉 所有圖示已產生完成，存放於：", OUTPUT_DIR)


if __name__ == "__main__":
    main()
