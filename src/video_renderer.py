"""
Video Renderer - Creates stunning news broadcast videos using MoviePy + Pillow
Features:
  - Cinematic dark gradient backgrounds with particle effects
  - Animated breaking news banners and tickers
  - Category color-coded segments with glowing borders
  - Animated text reveals (typewriter, slide-in)
  - News card overlays with Hindi text
  - Lower thirds with source attribution
  - Smooth transitions between segments
  - Animated logo and broadcast watermark

UPSC Mode adds:
  - GS paper badge (GS1/GS2/GS3/GS4) with color coding
  - Prelims Corner panel with exam-ready MCQ fact
  - Mains Angle callout box
  - Syllabus topic tags (chips row)
  - Key Terms strip
  - Exam Relevance meter (replaces Impact meter)
  - UPSC branding in watermark
"""

import os
import math
import logging
import textwrap
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from moviepy import (
    VideoClip,
    AudioFileClip,
    concatenate_videoclips,
    CompositeVideoClip,
    ImageClip,
    ColorClip,
    TextClip,
)
from moviepy.audio.AudioClip import concatenate_audioclips

logger = logging.getLogger(__name__)

# Video constants
VIDEO_W = 1280
VIDEO_H = 720
FPS = 30
FONT_PATH_HINDI = None  # Will auto-detect

# Color palette
COLORS = {
    "bg_dark": (5, 5, 20),
    "bg_mid": (10, 10, 35),
    "accent_red": (220, 30, 30),
    "accent_gold": (255, 200, 50),
    "accent_blue": (30, 150, 220),
    "white": (255, 255, 255),
    "light_gray": (200, 200, 210),
    "dark_overlay": (0, 0, 0, 180),
    "breaking_red": (200, 0, 30),
    "ticker_bg": (15, 15, 40),
}


def _find_font(size: int = 36, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Find best available font for Hindi/Latin text."""
    # Priority order for Hindi fonts
    font_candidates = [
        # Noto fonts (excellent Hindi support)
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        # Lohit Devanagari
        "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
        # Gargi
        "/usr/share/fonts/truetype/ttf-devanagari-fonts/gargi.ttf",
        # FreeSans (fallback)
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        # Liberation
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        # DejaVu
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue

    # Last resort: default PIL font
    return ImageFont.load_default()


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _draw_gradient_bg(width: int, height: int, t: float = 0) -> np.ndarray:
    """Create animated dark gradient background with subtle animation."""
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Base dark blue-black gradient
    for y in range(height):
        ratio = y / height
        # Animated subtle color shift
        phase = math.sin(t * 0.3) * 0.1
        r = int(5 + ratio * 15 + phase * 5)
        g = int(5 + ratio * 10 + phase * 3)
        b = int(20 + ratio * 40 + phase * 10)
        img[y, :] = [
            min(255, max(0, r)),
            min(255, max(0, g)),
            min(255, max(0, b)),
        ]

    return img


def _draw_grid_lines(draw: ImageDraw.Draw, width: int, height: int, alpha: int = 30):
    """Draw subtle grid lines for broadcast feel."""
    grid_color = (50, 80, 120, alpha)
    # Horizontal lines every 60px
    for y in range(0, height, 60):
        draw.line([(0, y), (width, y)], fill=(30, 50, 80), width=1)
    # Vertical accent lines
    for x in [0, width // 3, 2 * width // 3, width]:
        draw.line([(x, 0), (x, height)], fill=(30, 50, 80), width=1)


def _draw_breaking_banner(
    draw: ImageDraw.Draw,
    text: str,
    y_pos: int,
    width: int,
    font: ImageFont.FreeTypeFont,
    t: float = 0,
):
    """Draw animated breaking news banner."""
    banner_h = 50
    # Pulsing red background
    pulse = int(180 + math.sin(t * 4) * 40)
    draw.rectangle([(0, y_pos), (width, y_pos + banner_h)], fill=(pulse, 0, 20))

    # Breaking news label box
    label = "⚡ BREAKING NEWS"
    label_font = _find_font(16, bold=True)
    draw.rectangle([(10, y_pos + 8), (200, y_pos + banner_h - 8)], fill=(255, 220, 0))
    draw.text((20, y_pos + 14), label, fill=(0, 0, 0), font=label_font)

    # Breaking news text
    draw.text((215, y_pos + 12), text[:80], fill=(255, 255, 255), font=font)


def _draw_ticker(
    draw: ImageDraw.Draw,
    items: list[str],
    y_pos: int,
    width: int,
    t: float,
):
    """Draw animated news ticker."""
    ticker_h = 40
    # Dark blue ticker background
    draw.rectangle([(0, y_pos), (width, y_pos + ticker_h)], fill=(10, 20, 50))

    # LIVE label
    live_font = _find_font(14, bold=True)
    pulse_alpha = int(200 + math.sin(t * 3) * 55)
    draw.rectangle([(0, y_pos), (80, y_pos + ticker_h)], fill=(200, 0, 0))
    draw.text((15, y_pos + 12), "🔴 LIVE", fill=(255, 255, 255), font=live_font)

    # Scrolling ticker text
    ticker_font = _find_font(16)
    full_text = "  •  ".join(items) + "  •  "
    # Calculate scroll offset
    text_speed = 120  # pixels per second
    total_width = len(full_text) * 10  # approximate
    offset = int(t * text_speed) % max(1, total_width + width)

    ticker_x = 90 + width - offset
    # Draw ticker text
    draw.text((ticker_x, y_pos + 12), full_text, fill=(220, 220, 240), font=ticker_font)

    # Separator line
    draw.line([(0, y_pos), (width, y_pos)], fill=(255, 200, 0), width=2)


def _draw_category_badge(
    draw: ImageDraw.Draw,
    category: str,
    emoji: str,
    color_hex: str,
    x: int,
    y: int,
):
    """Draw colored category badge."""
    cat_color = _hex_to_rgb(color_hex)
    font = _find_font(18, bold=True)

    badge_text = f"{emoji} {category}"
    # Background pill
    bbox = draw.textbbox((0, 0), badge_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    padding = 10

    draw.rounded_rectangle(
        [(x, y), (x + text_w + padding * 2, y + text_h + padding)],
        radius=8,
        fill=cat_color,
    )
    draw.text((x + padding, y + padding // 2), badge_text, fill=(255, 255, 255), font=font)


def _draw_gs_badge(
    draw: ImageDraw.Draw,
    gs_paper: str,
    gs_color_hex: str,
    x: int,
    y: int,
) -> int:
    """Draw GS paper badge (e.g. GS2) and return right edge x."""
    gs_color = _hex_to_rgb(gs_color_hex)
    font = _find_font(16, bold=True)
    badge_text = f"📚 {gs_paper}"
    bbox = draw.textbbox((0, 0), badge_text, font=font)
    bw = bbox[2] - bbox[0]
    ph = 8  # padding
    draw.rounded_rectangle(
        [(x, y), (x + bw + ph * 2, y + 36)],
        radius=6,
        fill=(*gs_color, 220),
    )
    draw.text((x + ph, y + 8), badge_text, fill=(255, 255, 255), font=font)
    return x + bw + ph * 2 + 6  # next badge start x


def _draw_syllabus_tags(
    draw: ImageDraw.Draw,
    tags: list[str],
    x: int,
    y: int,
    max_width: int,
):
    """Draw a row of small syllabus topic chip tags."""
    tag_font = _find_font(13)
    cur_x = x
    for tag in tags[:6]:
        bbox = draw.textbbox((0, 0), tag, font=tag_font)
        tw = bbox[2] - bbox[0]
        chip_w = tw + 14
        if cur_x + chip_w > x + max_width:
            break
        draw.rounded_rectangle(
            [(cur_x, y), (cur_x + chip_w, y + 24)],
            radius=5,
            fill=(40, 60, 100, 200),
        )
        draw.rectangle(
            [(cur_x, y), (cur_x + 3, y + 24)],
            fill=(100, 160, 255, 220),
        )
        draw.text((cur_x + 7, y + 5), tag, fill=(180, 210, 255), font=tag_font)
        cur_x += chip_w + 6


def _draw_prelims_corner(
    draw: ImageDraw.Draw,
    fact: str,
    x: int,
    y: int,
    w: int,
    h: int,
):
    """Draw the 'Prelims Corner' panel with a quick MCQ fact."""
    # Panel background — amber tinted
    draw.rounded_rectangle(
        [(x, y), (x + w, y + h)],
        radius=8,
        fill=(60, 45, 5, 230),
    )
    draw.rounded_rectangle(
        [(x, y), (x + w, y + h)],
        radius=8,
        outline=(245, 180, 20, 200),
        width=2,
    )
    # Header bar
    draw.rectangle([(x, y), (x + w, y + 28)], fill=(200, 140, 0, 220))
    header_font = _find_font(14, bold=True)
    draw.text((x + 8, y + 7), "📝 PRELIMS CORNER", fill=(255, 255, 255), font=header_font)

    # Fact text
    fact_font = _find_font(14)
    wrapped = _wrap_text(fact[:160], int(w / 8))
    fy = y + 35
    for line in wrapped[:3]:
        draw.text((x + 8, fy), line, fill=(255, 230, 150), font=fact_font)
        fy += 20


def _draw_mains_angle(
    draw: ImageDraw.Draw,
    question: str,
    x: int,
    y: int,
    w: int,
    h: int,
):
    """Draw the 'Mains Angle' callout box with a mains-style question."""
    draw.rounded_rectangle(
        [(x, y), (x + w, y + h)],
        radius=8,
        fill=(5, 30, 60, 230),
    )
    draw.rounded_rectangle(
        [(x, y), (x + w, y + h)],
        radius=8,
        outline=(30, 144, 255, 200),
        width=2,
    )
    # Header
    draw.rectangle([(x, y), (x + w, y + 28)], fill=(10, 80, 180, 220))
    header_font = _find_font(14, bold=True)
    draw.text((x + 8, y + 7), "✍️ MAINS ANGLE", fill=(255, 255, 255), font=header_font)

    # Question text
    q_font = _find_font(13)
    wrapped = _wrap_text(question[:200], int(w / 7.5))
    qy = y + 35
    for line in wrapped[:4]:
        draw.text((x + 8, qy), line, fill=(160, 200, 255), font=q_font)
        qy += 19


def _draw_key_terms_strip(
    draw: ImageDraw.Draw,
    terms: list[str],
    x: int,
    y: int,
    w: int,
):
    """Draw a horizontal strip of key terms."""
    if not terms:
        return
    term_font = _find_font(13, bold=True)
    draw.rectangle([(x, y), (x + w, y + 30)], fill=(10, 20, 50, 220))
    label_font = _find_font(13)
    draw.text((x + 5, y + 8), "Key Terms:", fill=(180, 180, 200), font=label_font)

    cur_x = x + 85
    for term in terms[:5]:
        bbox = draw.textbbox((0, 0), term, font=term_font)
        tw = bbox[2] - bbox[0]
        if cur_x + tw + 16 > x + w:
            break
        draw.rounded_rectangle(
            [(cur_x, y + 5), (cur_x + tw + 12, y + 25)],
            radius=4,
            fill=(30, 100, 200, 180),
        )
        draw.text((cur_x + 6, y + 8), term, fill=(200, 230, 255), font=term_font)
        cur_x += tw + 18


def _draw_news_card(
    frame: np.ndarray,
    segment: dict,
    t: float,
    card_progress: float,  # 0.0 to 1.0 (animation progress)
    upsc_mode: bool = False,
) -> np.ndarray:
    """
    Draw a full news card overlay on the frame.
    card_progress: 0=entering, 0.5=visible, 1=exiting
    upsc_mode: adds GS badge, prelims fact, mains angle, key terms, syllabus tags
    """
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img, "RGBA")

    w, h = img.size
    color_hex = segment.get("color", "#0074D9")
    seg_color = _hex_to_rgb(color_hex)
    category = segment.get("category", "News")
    category_hindi = segment.get("category_hindi", "समाचार")
    emoji = segment.get("emoji", "📰")
    headline_hindi = segment.get("headline_hindi", "")
    narration = segment.get("narration_hindi", "")
    key_points = segment.get("key_points_hindi", [])
    lower_third = segment.get("lower_third", "")
    breaking = segment.get("breaking", False)
    impact = segment.get("impact_score", 5)

    # UPSC fields
    gs_paper = segment.get("gs_paper", "")
    gs_color_hex = segment.get("gs_color", "#6366F1")
    syllabus_tags = segment.get("syllabus_tags", [])
    prelims_fact = segment.get("prelims_fact", "")
    mains_angle = segment.get("mains_angle", "")
    key_terms = segment.get("key_terms", [])
    exam_score = segment.get("exam_relevance_score", impact)

    # Animation easing
    ease = _ease_in_out(card_progress)

    # --- Main content area ---
    # In UPSC mode the main card is narrower to make room for side panels
    card_x = 40
    card_y = 55 if upsc_mode else 80
    side_panel_w = 340 if upsc_mode else 0
    card_w = w - 80 - side_panel_w
    card_h = h - (160 if upsc_mode else 180)

    slide_offset = int((1 - ease) * -w)

    # Card background
    card_bg = Image.new("RGBA", (card_w, card_h), (10, 15, 40, 220))
    card_draw = ImageDraw.Draw(card_bg, "RGBA")

    # Left accent bar
    card_draw.rectangle([(0, 0), (6, card_h)], fill=(*seg_color, 255))
    glow_intensity = int(150 + math.sin(t * 2) * 50)
    for i in range(1, 6):
        alpha = max(0, glow_intensity - i * 25)
        card_draw.rectangle(
            [(6, i * 2), (6 + i * 3, card_h - i * 2)],
            fill=(*seg_color, alpha),
        )

    # Badge row: category badge + GS badge (UPSC) + breaking badge
    cat_font = _find_font(20, bold=True)
    badge_text = f"{emoji} {category_hindi}"
    card_draw.rectangle([(20, 15), (280, 52)], fill=(*seg_color, 200))
    card_draw.text((30, 20), badge_text, fill=(255, 255, 255), font=cat_font)

    badge_x = 290
    if upsc_mode and gs_paper:
        badge_x = _draw_gs_badge(card_draw, gs_paper, gs_color_hex, badge_x, 15)

    if breaking:
        pulse = int(180 + math.sin(t * 4) * 75)
        card_draw.rectangle(
            [(badge_x, 15), (badge_x + 165, 52)],
            fill=(pulse, 0, 20, 230),
        )
        break_font = _find_font(16, bold=True)
        card_draw.text((badge_x + 10, 22), "⚡ ब्रेकिंग", fill=(255, 220, 0), font=break_font)

    # Headline
    headline_font = _find_font(30, bold=True)
    headline_y = 68
    wrapped_headline = _wrap_text(headline_hindi, 42 if upsc_mode else 45)
    for line in wrapped_headline[:2]:
        card_draw.text((20, headline_y), line, fill=(255, 255, 255), font=headline_font)
        headline_y += 38

    # Syllabus tags row (UPSC)
    if upsc_mode and syllabus_tags:
        _draw_syllabus_tags(card_draw, syllabus_tags, 20, headline_y + 2, card_w - 40)
        headline_y += 32

    # Divider line
    card_draw.line(
        [(20, headline_y + 6), (card_w - 20, headline_y + 6)],
        fill=(*seg_color, 180),
        width=2,
    )

    # Narration excerpt
    narr_font = _find_font(21)
    narr_text = narration[:190].replace("[रुकिए...]", "...") if narration else ""
    narr_y = headline_y + 18
    max_narr_lines = 2 if upsc_mode else 3
    wrapped_narr = _wrap_text(narr_text, 58 if upsc_mode else 65)
    for line in wrapped_narr[:max_narr_lines]:
        card_draw.text((20, narr_y), line, fill=(200, 210, 230), font=narr_font)
        narr_y += 28

    # Key points bullets
    if key_points:
        bullet_font = _find_font(18)
        bullet_y = narr_y + 8
        max_pts = 2 if upsc_mode else 3
        for point in key_points[:max_pts]:
            if bullet_y > card_h - 55:
                break
            card_draw.text(
                (25, bullet_y),
                f"▶  {point[:65]}",
                fill=(180, 230, 180),
                font=bullet_font,
            )
            bullet_y += 26

    # Key terms strip (UPSC)
    if upsc_mode and key_terms:
        kt_y = card_h - 48
        _draw_key_terms_strip(card_draw, key_terms, 10, kt_y, card_w - 20)

    # Impact / Exam relevance meter
    meter_score = exam_score if upsc_mode else impact
    meter_label = "Exam Rel." if upsc_mode else "Impact"
    _draw_impact_meter(
        card_draw, meter_score, card_w - 145, 18, 120, 28, seg_color,
        label=meter_label,
    )

    # Paste main card
    img.paste(card_bg, (card_x + slide_offset, card_y), mask=card_bg.split()[3])

    # --- UPSC side panels (right column) ---
    if upsc_mode:
        panel_x = w - side_panel_w - 30 + int((1 - ease) * side_panel_w)
        panel_y = card_y
        panel_inner_w = side_panel_w - 10

        if prelims_fact:
            prelims_h = 110
            _draw_prelims_corner(draw, prelims_fact, panel_x, panel_y, panel_inner_w, prelims_h)
            panel_y += prelims_h + 10

        if mains_angle:
            mains_h = 120
            _draw_mains_angle(draw, mains_angle, panel_x, panel_y, panel_inner_w, mains_h)
            panel_y += mains_h + 10

    # --- Breaking news banner (top) ---
    if breaking:
        _draw_breaking_banner(
            draw,
            f"ब्रेकिंग: {headline_hindi[:60]}",
            y_pos=0,
            width=w,
            font=_find_font(20),
            t=t,
        )

    # --- Lower third ---
    if lower_third:
        lt_h = 60
        lt_y = h - lt_h - 40
        lower_bg = Image.new("RGBA", (w - 80, lt_h), (5, 10, 30, 220))
        lower_draw = ImageDraw.Draw(lower_bg, "RGBA")
        lower_draw.rectangle([(0, 0), (w - 80, 4)], fill=(*seg_color, 255))

        lt_font = _find_font(23, bold=True)
        lower_draw.text((15, 10), lower_third[:70], fill=(255, 255, 255), font=lt_font)

        src_font = _find_font(15)
        source = segment.get("headline_english", "")[:55]
        lower_draw.text((15, 38), source, fill=(160, 180, 200), font=src_font)

        img.paste(lower_bg, (40, lt_y), mask=lower_bg.split()[3])

    return np.array(img)


def _draw_impact_meter(
    draw: ImageDraw.Draw,
    score: int,
    x: int,
    y: int,
    w: int,
    h: int,
    color: tuple,
    label: str = "Impact",
):
    """Draw impact / exam-relevance score meter."""
    score = max(1, min(10, score))
    draw.text((x, y - 18), f"{label}:", fill=(180, 180, 200), font=_find_font(14))

    # Background bar
    draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=4, fill=(20, 20, 50, 200))

    # Filled portion
    filled_w = int(w * score / 10)
    if filled_w > 0:
        # Color gradient: green → yellow → red
        ratio = score / 10
        r = int(min(255, ratio * 2 * 255))
        g = int(min(255, (1 - ratio) * 2 * 255))
        draw.rounded_rectangle(
            [(x, y), (x + filled_w, y + h)],
            radius=4,
            fill=(r, g, 30, 220),
        )

    draw.text(
        (x + w + 5, y + 3),
        f"{score}/10",
        fill=(200, 200, 220),
        font=_find_font(14),
    )


def _draw_headline_frame(segment: dict, t: float, reveal_progress: float) -> np.ndarray:
    """Draw a dramatic headline reveal frame."""
    frame = _draw_gradient_bg(VIDEO_W, VIDEO_H, t)
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img, "RGBA")

    _draw_grid_lines(draw, VIDEO_W, VIDEO_H)

    color_hex = segment.get("color", "#FF4136")
    seg_color = _hex_to_rgb(color_hex)
    emoji = segment.get("emoji", "📰")
    category_hindi = segment.get("category_hindi", "समाचार")
    headline_hindi = segment.get("headline_hindi", "")

    # Central spotlight effect
    cx, cy = VIDEO_W // 2, VIDEO_H // 2
    for radius in range(300, 0, -30):
        alpha = int(15 * (1 - radius / 300) * reveal_progress)
        circle_img = Image.new("RGBA", (VIDEO_W, VIDEO_H), (0, 0, 0, 0))
        circle_draw = ImageDraw.Draw(circle_img)
        circle_draw.ellipse(
            [(cx - radius, cy - radius), (cx + radius, cy + radius)],
            fill=(*seg_color, alpha),
        )
        img = Image.alpha_composite(img.convert("RGBA"), circle_img).convert("RGB")
        draw = ImageDraw.Draw(img, "RGBA")

    # Large category emoji (scaled)
    cat_font = _find_font(60, bold=True)
    draw.text((cx - 40, cy - 140), emoji, font=cat_font, fill=(255, 255, 255))

    # Category label
    badge_font = _find_font(28, bold=True)
    badge_text = category_hindi
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bw = bbox[2] - bbox[0]
    badge_x = cx - bw // 2
    draw.rounded_rectangle(
        [(badge_x - 15, cy - 55), (badge_x + bw + 15, cy - 10)],
        radius=6,
        fill=(*seg_color, 220),
    )
    draw.text((badge_x, cy - 50), badge_text, fill=(255, 255, 255), font=badge_font)

    # Headline text with typewriter effect
    if reveal_progress > 0.3:
        headline_font = _find_font(36, bold=True)
        full_headline = headline_hindi
        chars_to_show = int(len(full_headline) * min(1.0, (reveal_progress - 0.3) / 0.7))
        partial_headline = full_headline[:chars_to_show]

        wrapped = _wrap_text(partial_headline, 38)
        text_y = cy + 10
        for line in wrapped[:2]:
            bbox = draw.textbbox((0, 0), line, font=headline_font)
            lw = bbox[2] - bbox[0]
            lx = cx - lw // 2
            # Shadow
            draw.text((lx + 2, text_y + 2), line, fill=(0, 0, 0, 150), font=headline_font)
            draw.text((lx, text_y), line, fill=(255, 255, 255), font=headline_font)
            text_y += 50

    # Animated border lines
    border_alpha = int(200 * reveal_progress)
    border_y = 70
    draw.line([(0, border_y), (VIDEO_W, border_y)], fill=(*seg_color, border_alpha), width=3)
    draw.line(
        [(0, VIDEO_H - border_y), (VIDEO_W, VIDEO_H - border_y)],
        fill=(*seg_color, border_alpha),
        width=3,
    )

    # Channel watermark
    _draw_watermark(draw, VIDEO_W, VIDEO_H)

    return np.array(img)


def _draw_show_intro_frame(t: float, show_data: dict) -> np.ndarray:
    """Draw animated show intro frame."""
    frame = _draw_gradient_bg(VIDEO_W, VIDEO_H, t)
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img, "RGBA")

    cx, cy = VIDEO_W // 2, VIDEO_H // 2

    # Rotating ring effect
    for angle in range(0, 360, 15):
        rad = math.radians(angle + t * 30)
        r = 250 + math.sin(t * 2 + angle * 0.1) * 20
        x = cx + int(r * math.cos(rad))
        y = cy + int(r * math.sin(rad))
        alpha = int(80 + 40 * math.sin(rad + t))
        draw.ellipse([(x - 3, y - 3), (x + 3, y + 3)], fill=(100, 150, 255, alpha))

    # Title glow
    title_font = _find_font(64, bold=True)
    show_title = show_data.get("show_title", "आज की बड़ी खबरें")
    bbox = draw.textbbox((0, 0), show_title, font=title_font)
    tw = bbox[2] - bbox[0]
    tx = cx - tw // 2

    # Glow layers
    for offset in range(8, 0, -1):
        alpha = int(30 + 10 * offset)
        draw.text(
            (tx - offset, cy - offset - 40),
            show_title,
            fill=(255, 200, 50, alpha),
            font=title_font,
        )

    # Main title
    draw.text((tx, cy - 40), show_title, fill=(255, 220, 80), font=title_font)

    # Subtitle
    subtitle_font = _find_font(32)
    english_title = show_data.get("show_title_english", "Today's Top News")
    bbox2 = draw.textbbox((0, 0), english_title, font=subtitle_font)
    sw = bbox2[2] - bbox2[0]
    draw.text(
        (cx - sw // 2, cy + 40),
        english_title,
        fill=(200, 210, 230),
        font=subtitle_font,
    )

    # Date
    date_font = _find_font(22)
    from datetime import datetime
    date_str = datetime.now().strftime("%d %B %Y")
    draw.text((cx - 80, cy + 90), date_str, fill=(160, 180, 200), font=date_font)

    # UPSC-specific intro extras: GS paper legend strip
    upsc_mode = show_data.get("upsc_mode", False)
    if upsc_mode:
        gs_colors = [("#8B5CF6", "GS1"), ("#10B981", "GS2"), ("#3B82F6", "GS3"), ("#F59E0B", "GS4")]
        lx = cx - 280
        for hex_c, label in gs_colors:
            rgb = _hex_to_rgb(hex_c)
            draw.rounded_rectangle([(lx, cy + 130), (lx + 60, cy + 160)], radius=5, fill=(*rgb, 180))
            draw.text((lx + 8, cy + 136), label, fill=(255, 255, 255), font=_find_font(18, bold=True))
            lx += 76
        draw.text((cx - 285, cy + 165), "GS1: History/Geo  GS2: Polity/IR  GS3: Economy/Env  GS4: Ethics",
                  fill=(160, 180, 200), font=_find_font(13))

    # Bottom accent — gold for standard, green for UPSC
    accent_color = (16, 185, 129) if upsc_mode else (255, 200, 50)
    draw.rectangle([(0, VIDEO_H - 8), (VIDEO_W, VIDEO_H)], fill=accent_color)

    _draw_watermark(draw, VIDEO_W, VIDEO_H, upsc_mode=upsc_mode)

    return np.array(img)


def _draw_outro_frame(t: float, show_data: dict) -> np.ndarray:
    """Draw outro frame."""
    frame = _draw_gradient_bg(VIDEO_W, VIDEO_H, t)
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img, "RGBA")

    cx, cy = VIDEO_W // 2, VIDEO_H // 2

    # Fade out stars effect
    rng = np.random.default_rng(seed=42)
    for _ in range(150):
        x = rng.integers(0, VIDEO_W)
        y = rng.integers(0, VIDEO_H)
        size = rng.integers(1, 4)
        alpha = rng.integers(50, 200)
        draw.ellipse([(x, y), (x + size, y + size)], fill=(200, 200, 255, alpha))

    # Thank you text
    thanks_font = _find_font(52, bold=True)
    thanks_text = "धन्यवाद!"
    bbox = draw.textbbox((0, 0), thanks_text, font=thanks_font)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw // 2, cy - 80), thanks_text, fill=(255, 220, 80), font=thanks_font)

    upsc_mode = show_data.get("upsc_mode", False)
    sub_font = _find_font(28)

    if upsc_mode:
        sub_texts = [
            "पढ़ते रहो • आगे बढ़ते रहो",
            "Keep Revising • IAS/IPS Awaits You!",
        ]
        # Daily tip if present
        tip = show_data.get("daily_tip_hindi", "")
        if tip:
            tip_font = _find_font(20)
            tip_bbox = draw.textbbox((0, 0), f"💡 {tip[:70]}", font=tip_font)
            tip_w = tip_bbox[2] - tip_bbox[0]
            draw.rounded_rectangle(
                [(cx - tip_w // 2 - 15, cy + 90), (cx + tip_w // 2 + 15, cy + 120)],
                radius=6,
                fill=(20, 80, 20, 200),
            )
            draw.text((cx - tip_w // 2, cy + 95), f"💡 {tip[:70]}", fill=(180, 255, 180), font=tip_font)
    else:
        sub_texts = [
            "समाचार देखते रहें",
            "Stay Informed • Stay Ahead",
        ]

    sub_y = cy
    for st in sub_texts:
        bbox = draw.textbbox((0, 0), st, font=sub_font)
        sw = bbox[2] - bbox[0]
        draw.text((cx - sw // 2, sub_y), st, fill=(200, 210, 230), font=sub_font)
        sub_y += 40

    sub_prompt_font = _find_font(24)
    subscribe_text = "🔔 Like • Share • Subscribe"
    bbox = draw.textbbox((0, 0), subscribe_text, font=sub_prompt_font)
    btw = bbox[2] - bbox[0]
    pulse = int(200 + math.sin(t * 3) * 55)
    draw.text(
        (cx - btw // 2, cy + 130 if upsc_mode else cy + 100),
        subscribe_text,
        fill=(pulse, 80, 80),
        font=sub_prompt_font,
    )

    accent_color = (16, 185, 129) if upsc_mode else (255, 200, 50)
    draw.rectangle([(0, VIDEO_H - 8), (VIDEO_W, VIDEO_H)], fill=accent_color)
    _draw_watermark(draw, VIDEO_W, VIDEO_H, upsc_mode=upsc_mode)

    return np.array(img)


def _draw_watermark(draw: ImageDraw.Draw, w: int, h: int, upsc_mode: bool = False):
    """Draw channel watermark."""
    wm_font = _find_font(16)
    if upsc_mode:
        wm_text = "UPSC AI NEWS • करंट अफेयर्स"
    else:
        wm_text = "AI NEWS • आर्टिफिशियल न्यूज़"
    draw.text((w - 310, 15), wm_text, fill=(120, 140, 170, 200), font=wm_font)
    draw.ellipse([(w - 328, 19), (w - 316, 31)], fill=(200, 0, 0, 200))


def _wrap_text(text: str, max_chars: int) -> list[str]:
    """Wrap text to fit within max_chars per line."""
    if not text:
        return []
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = current + " " + word if current else word
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _ease_in_out(t: float) -> float:
    """Smooth ease in-out function."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class VideoRenderer:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fps = FPS
        self.w = VIDEO_W
        self.h = VIDEO_H

    def create_intro_clip(self, show_data: dict, duration: float = 5.0) -> VideoClip:
        """Create animated show intro clip."""
        def make_frame(t):
            return _draw_show_intro_frame(t, show_data)

        clip = VideoClip(make_frame, duration=duration)
        clip = clip.with_fps(self.fps)
        return clip

    def create_headline_clip(
        self, segment: dict, duration: float = 4.0
    ) -> VideoClip:
        """Create headline reveal animation clip."""
        def make_frame(t):
            progress = min(1.0, t / 2.0)
            return _draw_headline_frame(segment, t, progress)

        clip = VideoClip(make_frame, duration=duration)
        clip = clip.with_fps(self.fps)
        return clip

    def create_news_card_clip(
        self,
        segment: dict,
        duration: float = 8.0,
        ticker_items: list[str] | None = None,
        upsc_mode: bool = False,
    ) -> VideoClip:
        """Create full news card video clip with animation.

        In UPSC mode the card has GS paper badge, Prelims Corner,
        Mains Angle panel, syllabus tags, and key terms strip.
        """
        ticker = ticker_items or ["आज की बड़ी खबरें देखते रहें"]

        def make_frame(t):
            frame = _draw_gradient_bg(VIDEO_W, VIDEO_H, t)
            img = Image.fromarray(frame)
            base_draw = ImageDraw.Draw(img, "RGBA")
            _draw_grid_lines(base_draw, VIDEO_W, VIDEO_H)
            frame = np.array(img)

            if t < 0.5:
                progress = t / 0.5
            elif t > duration - 0.5:
                progress = (duration - t) / 0.5
            else:
                progress = 1.0

            frame = _draw_news_card(frame, segment, t, progress, upsc_mode=upsc_mode)

            ticker_img = Image.fromarray(frame)
            ticker_draw = ImageDraw.Draw(ticker_img)
            _draw_ticker(ticker_draw, ticker, VIDEO_H - 40, VIDEO_W, t)
            _draw_watermark(ticker_draw, VIDEO_W, VIDEO_H, upsc_mode=upsc_mode)
            return np.array(ticker_img)

        clip = VideoClip(make_frame, duration=duration)
        clip = clip.with_fps(self.fps)
        return clip

    def create_transition_clip(
        self,
        from_color: str = "#FF4136",
        to_color: str = "#0074D9",
        duration: float = 0.8,
    ) -> VideoClip:
        """Create smooth color sweep transition."""
        from_rgb = _hex_to_rgb(from_color)
        to_rgb = _hex_to_rgb(to_color)

        def make_frame(t):
            progress = t / duration
            frame = np.zeros((VIDEO_H, VIDEO_W, 3), dtype=np.uint8)

            # Sweep line
            sweep_x = int(progress * VIDEO_W)

            # Left side (from_color fade)
            if sweep_x > 0:
                frame[:, :sweep_x] = [
                    int(from_rgb[0] * (1 - progress)),
                    int(from_rgb[1] * (1 - progress)),
                    int(from_rgb[2] * (1 - progress)),
                ]

            # Right side (dark)
            frame[:, sweep_x:] = [5, 5, 20]

            # Sweep glow line
            glow_w = 40
            glow_start = max(0, sweep_x - glow_w)
            glow_end = min(VIDEO_W, sweep_x + glow_w)
            for x in range(glow_start, glow_end):
                dist = abs(x - sweep_x)
                intensity = max(0, 1 - dist / glow_w)
                for c in range(3):
                    add_val = int(to_rgb[c] * intensity * 0.8)
                    frame[:, x, c] = np.clip(
                        frame[:, x, c].astype(np.int32) + add_val, 0, 255
                    ).astype(np.uint8)

            return frame

        clip = VideoClip(make_frame, duration=duration)
        clip = clip.with_fps(self.fps)
        return clip

    def create_outro_clip(self, show_data: dict, duration: float = 5.0) -> VideoClip:
        """Create outro clip."""
        def make_frame(t):
            return _draw_outro_frame(t, show_data)

        clip = VideoClip(make_frame, duration=duration)
        clip = clip.with_fps(self.fps)
        return clip

    def attach_audio_to_clip(
        self, clip: VideoClip, audio_path: str
    ) -> VideoClip:
        """Attach audio to a video clip, trimming/extending as needed."""
        if not audio_path or not os.path.exists(audio_path):
            return clip

        try:
            audio = AudioFileClip(audio_path)
            # Trim audio to clip duration or extend clip
            if audio.duration > clip.duration:
                audio = audio.subclipped(0, clip.duration)
            elif audio.duration < clip.duration:
                # Extend clip to match audio duration
                clip = clip.with_duration(audio.duration)

            return clip.with_audio(audio)
        except Exception as e:
            logger.warning(f"Could not attach audio {audio_path}: {e}")
            return clip

    def render_full_show(
        self,
        show_data: dict,
        audio_files: dict,
        output_filename: str = "news_show.mp4",
        upsc_mode: bool = False,
    ) -> str:
        """
        Render the complete news show video.

        Args:
            show_data: Processed show data from ContentProcessor
            audio_files: Dict of audio file paths from TTSGenerator
            output_filename: Output video filename

        Returns:
            Path to rendered video file
        """
        segments = show_data.get("segments", [])
        ticker_items = show_data.get("ticker_items", ["आज की बड़ी खबरें"])

        all_clips = []

        # 1. Show Intro
        logger.info("Rendering show intro...")
        intro_duration = 5.0
        if "intro" in audio_files:
            try:
                from moviepy import AudioFileClip as AFC
                with AFC(audio_files["intro"]) as a:
                    intro_duration = max(5.0, a.duration + 1.0)
            except Exception:
                pass

        intro_clip = self.create_intro_clip(show_data, duration=intro_duration)
        if "intro" in audio_files:
            intro_clip = self.attach_audio_to_clip(intro_clip, audio_files["intro"])
        all_clips.append(intro_clip)

        # Welcome
        if "welcome" in audio_files:
            try:
                from moviepy import AudioFileClip as AFC
                with AFC(audio_files["welcome"]) as a:
                    welcome_dur = max(3.0, a.duration + 0.5)
            except Exception:
                welcome_dur = 3.0

            def make_welcome_frame(t):
                frame = _draw_gradient_bg(VIDEO_W, VIDEO_H, t)
                img = Image.fromarray(frame)
                draw = ImageDraw.Draw(img, "RGBA")
                _draw_grid_lines(draw, VIDEO_W, VIDEO_H)
                welcome_font = _find_font(40, bold=True)
                cx, cy = VIDEO_W // 2, VIDEO_H // 2
                text = "आज की शीर्ष खबरें"
                bbox = draw.textbbox((0, 0), text, font=welcome_font)
                tw = bbox[2] - bbox[0]
                draw.text(
                    (cx - tw // 2, cy - 30),
                    text,
                    fill=(255, 220, 80),
                    font=welcome_font,
                )
                count_font = _find_font(24)
                count_text = f"कुल {len(segments)} खबरें"
                bbox2 = draw.textbbox((0, 0), count_text, font=count_font)
                cw = bbox2[2] - bbox2[0]
                draw.text(
                    (cx - cw // 2, cy + 30),
                    count_text,
                    fill=(180, 200, 220),
                    font=count_font,
                )
                _draw_ticker(draw, ticker_items, VIDEO_H - 40, VIDEO_W, t)
                _draw_watermark(draw, VIDEO_W, VIDEO_H)
                return np.array(img)

            welcome_clip = VideoClip(make_welcome_frame, duration=welcome_dur)
            welcome_clip = welcome_clip.with_fps(self.fps)
            welcome_clip = self.attach_audio_to_clip(
                welcome_clip, audio_files["welcome"]
            )
            all_clips.append(welcome_clip)

        # 2. News Segments
        for i, segment in enumerate(segments, 1):
            logger.info(f"Rendering segment {i}/{len(segments)}: {segment.get('headline_hindi', '')[:40]}")

            # Transition
            prev_color = (
                segments[i - 2].get("color", "#FF4136") if i > 1 else "#1a1a3e"
            )
            trans_clip = self.create_transition_clip(
                from_color=prev_color,
                to_color=segment.get("color", "#0074D9"),
                duration=0.6,
            )
            all_clips.append(trans_clip)

            # Headline reveal (synced with announcement + headline audio)
            headline_dur = 4.0
            ann_key = f"announcement_{i}"
            hl_key = f"headline_{i}"

            if ann_key in audio_files or hl_key in audio_files:
                try:
                    from moviepy import AudioFileClip as AFC
                    total_dur = 0.0
                    for k in [ann_key, hl_key]:
                        if k in audio_files:
                            with AFC(audio_files[k]) as a:
                                total_dur += a.duration
                    headline_dur = max(3.0, total_dur + 1.0)
                except Exception:
                    pass

            headline_clip = self.create_headline_clip(segment, duration=headline_dur)

            # Combine announcement + headline audio
            hl_audio_parts = []
            for k in [ann_key, hl_key]:
                if k in audio_files and os.path.exists(audio_files[k]):
                    hl_audio_parts.append(AudioFileClip(audio_files[k]))

            if hl_audio_parts:
                if len(hl_audio_parts) > 1:
                    combined_audio = concatenate_audioclips(hl_audio_parts)
                else:
                    combined_audio = hl_audio_parts[0]
                audio_dur = combined_audio.duration
                if audio_dur > headline_clip.duration:
                    headline_clip = headline_clip.with_duration(audio_dur)
                elif audio_dur < headline_clip.duration:
                    combined_audio = combined_audio.with_duration(headline_clip.duration)
                headline_clip = headline_clip.with_audio(combined_audio)

            all_clips.append(headline_clip)

            # News card with main narration
            seg_key = f"segment_{i}"
            card_dur = 10.0
            if seg_key in audio_files:
                try:
                    from moviepy import AudioFileClip as AFC
                    with AFC(audio_files[seg_key]) as a:
                        card_dur = max(8.0, a.duration + 2.0)
                except Exception:
                    pass

            card_clip = self.create_news_card_clip(
                segment, duration=card_dur, ticker_items=ticker_items,
                upsc_mode=upsc_mode,
            )

            if seg_key in audio_files:
                card_clip = self.attach_audio_to_clip(
                    card_clip, audio_files[seg_key]
                )

            all_clips.append(card_clip)

        # 3. Outro
        logger.info("Rendering outro...")
        outro_dur = 5.0
        if "outro" in audio_files:
            try:
                from moviepy import AudioFileClip as AFC
                with AFC(audio_files["outro"]) as a:
                    outro_dur = max(5.0, a.duration + 1.0)
            except Exception:
                pass

        outro_clip = self.create_outro_clip(show_data, duration=outro_dur)
        if "outro" in audio_files:
            outro_clip = self.attach_audio_to_clip(outro_clip, audio_files["outro"])
        all_clips.append(outro_clip)

        # Concatenate all clips
        logger.info(f"Concatenating {len(all_clips)} clips...")
        final_clip = concatenate_videoclips(all_clips, method="compose")

        # Output path
        output_path = str(self.output_dir / output_filename)
        logger.info(f"Rendering to {output_path}...")

        final_clip.write_videofile(
            output_path,
            fps=self.fps,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=str(self.output_dir / "temp_audio.m4a"),
            remove_temp=True,
            logger="bar",
            threads=4,
        )

        logger.info(f"Video rendered: {output_path}")
        return output_path

    def render_preview_image(self, show_data: dict, output_path: str) -> str:
        """Render a thumbnail/preview image for the show."""
        segments = show_data.get("segments", [])
        if not segments:
            return ""

        first_seg = segments[0]
        frame = _draw_headline_frame(first_seg, t=1.0, reveal_progress=1.0)

        img = Image.fromarray(frame)
        img.save(output_path)
        logger.info(f"Preview image saved: {output_path}")
        return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Quick render test
    test_segment = {
        "id": 1,
        "category": "Technology",
        "category_hindi": "तकनीक",
        "headline_hindi": "AI ने बदल दिया दुनिया का नक्शा!",
        "headline_english": "AI Changes the World",
        "narration_hindi": "दोस्तों, आज एक ऐसी खबर आई है जो आपको हैरान कर देगी!",
        "key_points_hindi": ["पहला बिंदु यहाँ", "दूसरा बिंदु यहाँ"],
        "color": "#0074D9",
        "emoji": "💻",
        "impact_score": 9,
        "breaking": True,
        "lower_third": "तकनीक की नई क्रांति",
    }

    renderer = VideoRenderer(output_dir="/tmp/test_video")
    show_data = {
        "show_title": "आज की बड़ी खबरें",
        "show_title_english": "Today's Big News",
        "intro_hindi": "आज की सबसे बड़ी खबरें!",
        "outro_hindi": "धन्यवाद!",
        "segments": [test_segment],
        "ticker_items": ["ब्रेकिंग: AI का नया युग शुरू", "भारत में नया रिकॉर्ड"],
    }

    # Just test preview image
    img_path = renderer.render_preview_image(show_data, "/tmp/test_video/preview.png")
    print(f"Preview: {img_path}")
