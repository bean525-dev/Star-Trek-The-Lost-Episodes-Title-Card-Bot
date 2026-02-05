import os
import re
import textwrap
from atproto import Client, models
from PIL import Image, ImageDraw, ImageFont

# --- 1. IMAGE GENERATION LOGIC ---
def create_card(series, title):
    styles = {
        "TOS": {
            "font": "fonts/TOS_Title.ttf", 
            "bg": "templates/TOS_bg.jpg", 
            "color": "yellow", 
            "shadow": True, "shadow_color": "black",
            "size": 90, "x_pos": 0.20, "y_pos": 0.20,
            "align": "left", "anchor": "la", "wrap": 12
        },
        "DS9": {
            "font": "fonts/handel.ttf", 
            "bg": "templates/DS9_bg.jpg",
            "top_color": "#e0e0e0", "bottom_color": "#7da6ff", 
            "shadow": False,
            "size": 42, "x_pos": 0.08, "y_pos": 0.12,
            "align": "left", "anchor": "la", "wrap": 30
        },
        "TNG": {
            "font": "fonts/TNG_Credits.ttf", 
            "bg": "templates/TNG_bg.jpg",
            "color": "#5286ff", "shadow": False,
            "size": 42, "x_pos": 0.12, "y_pos": 0.15,
            "align": "left", "anchor": "la", "wrap": 28
        },
        "VOY": {
            "font": "fonts/handel.ttf", 
            "bg": "templates/VOY_bg.jpg",
            "top_color": "#FF8C00", "bottom_color": "#FFE0B2", 
            "shadow": False,
            "size": 42, "x_pos": 0.07, "y_pos": 0.10,
            "align": "left", "anchor": "la", "wrap": 28
        }
    }
    
    s = styles.get(series, styles["TNG"])
    quoted_title = f'"{title}"'
    if series in ["TOS", "DS9", "VOY"]:
        quoted_title = quoted_title.upper()

    try:
        img = Image.open(s["bg"]).convert("RGBA")
    except FileNotFoundError: return False

    # Dynamic Sizing
    font_size = s["size"]
    if len(quoted_title) > 20 and series != "TOS": 
        font_size = int(s["size"] * 0.75)
    
    try:
        font = ImageFont.truetype(s["font"], font_size)
    except OSError: return False

    draw = ImageDraw.Draw(img)
    W, H = img.size
    wrapped_text = textwrap.fill(quoted_title, width=s["wrap"])
    target_xy = (W * s["x_pos"], H * s["y_pos"])

    # --- DRAWING PHASE ---

    # 1. Draw Shadow (Skip for TOS, handled in stagger loop)
    if s.get("shadow", False) and series != "TOS":
        sha_color = s.get("shadow_color", "black")
        draw.multiline_text((target_xy[0]+3, target_xy[1]+3), wrapped_text, font=font, fill=sha_color, anchor=s["anchor"], align=s["align"], spacing=5)

    # 2. Draw Text
    if "top_color" in s:
        # Gradient path for DS9/VOY
        lines = wrapped_text.split('\n')
        current_y = target_xy[1]
        line_spacing = 8 

        for line in lines:
            line_mask = Image.new("L", (W, H), 0)
            line_draw = ImageDraw.Draw(line_mask)
            line_draw.text((target_xy[0], current_y), line, font=font, fill=255, anchor=s["anchor"])
            
            bbox = line_draw.textbbox((target_xy[0], current_y), line, font=font, anchor=s["anchor"])
            line_grad = Image.new("RGBA", (W, H), (0,0,0,0))
            lg_draw = ImageDraw.Draw(line_grad)
            
            y_start, y_end = int(bbox[1]), int(bbox[3])
            line_h = max(1, y_end - y_start)
            
            c1 = tuple(int(s["top_color"].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            c2 = tuple(int(s["bottom_color"].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

            for y in range(y_start, y_end + 1):
                curr_step = (y - y_start) / line_h
                r = int(c1[0] + (c2[0] - c1[0]) * curr_step)
                g = int(c1[1] + (c2[1] - c1[1]) * curr_step)
                b = int(c1[2] + (c2[2] - c1[2]) * curr_step)
                lg_draw.line([(bbox[0], y), (bbox[2], y)], fill=(r, g, b, 255))

            img.paste(line_grad, (0, 0), line_mask)
