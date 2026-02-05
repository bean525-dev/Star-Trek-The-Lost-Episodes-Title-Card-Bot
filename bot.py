import os
import re
import textwrap
from atproto import Client, models
from PIL import Image, ImageDraw, ImageFont

# --- 1. IMAGE GENERATION LOGIC ---
def create_card(series, title):
    styles = {
        "TOS": {
            "font": "fonts/TOS_Title.ttf", # ENSURE THIS MATCHES FILENAME EXACTLY
            "bg": "templates/TOS_bg.jpg", 
            "color": "yellow", 
            "shadow": True, "shadow_color": "black",
            "size": 90, "x_pos": 0.15, "y_pos": 0.20,
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
    if len(quoted_title) > 20: font_size = int(s["size"] * 0.75)
    
    try:
        font = ImageFont.truetype(s["font"], font_size)
    except OSError: return False

    draw = ImageDraw.Draw(img)
    W, H = img.size
    wrapped_text = textwrap.fill(quoted_title, width=s["wrap"])
    target_xy = (W * s["x_pos"], H * s["y_pos"])

    # --- DRAWING PHASE ---

    # 1. Draw Shadow (TOS only)
    if s.get("shadow", False):
        sha_color = s.get("shadow_color", "black")
        draw.multiline_text((target_xy[0]+3, target_xy[1]+3), wrapped_text, font=font, fill=sha_color, anchor=s["anchor"], align=s["align"], spacing=5)

    # 2. Draw Text (Line-by-line Gradient for DS9/VOY)
    if "top_color" in s:
        lines = wrapped_text.split('\n')
        current_y = target_xy[1]
        line_spacing = 8 

        for line in lines:
            # Create mask for this specific line
            line_mask = Image.new("L", (W, H), 0)
            line_draw = ImageDraw.Draw(line_mask)
            line_draw.text((target_xy[0], current_y), line, font=font, fill=255, anchor=s["anchor"])
            
            bbox = line_draw.textbbox((target_xy[0], current_y), line, font=font, anchor=s["anchor"])
            
            # Create gradient for this specific line
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
            current_y += (y_end - y_start) + line_spacing
    else:
        # Solid Color path (TOS and TNG)
        if series == "TOS":
            lines = wrapped_text.split('\n')
            curr_x, curr_y = target_xy
            for i, line in enumerate(lines):
                # This creates the "Assignment: Earth" staircase effect
                line_x = curr_x + (i * 100) 
                # Shadow first
                draw.text((line_x + 5, curr_y + 5), line, font=font, fill="black", anchor=s["anchor"])
                # Then text
                draw.text((line_x, curr_y), line, font=font, fill=s["color"], anchor=s["anchor"])
                # Move down for next line
                curr_y += font_size + 15
        else:
            # Standard path for TNG
            draw.multiline_text(target_xy, wrapped_text, font=font, fill=s["color"], anchor=s["anchor"], align=s["align"], spacing=5)

def main():
    client = Client()
    client.login(os.environ['BSKY_HANDLE'], os.environ['BSKY_PASSWORD'])
    params = {'actor': os.environ['BSKY_HANDLE'], 'limit': 5}
    response = client.app.bsky.feed.get_author_feed(params=params)

    for feed_view in response.feed:
        text = feed_view.post.record.text
        match = re.search(r"Lost (\w+) Episode: \"(.+)\"", text)
        if match:
            series, title = match.group(1), match.group(2)
            if create_card(series, title):
                with open("output.png", "rb") as f:
                    img_data = f.read()
                parent = {"cid": feed_view.post.cid, "uri": feed_view.post.uri}
                root = feed_view.post.record.reply.root if feed_view.post.record.reply else parent
                client.send_image(
                    text="", image=img_data, 
                    image_alt=f"Star Trek {series} style title card for {title}",
                    reply_to=models.AppBskyFeedPost.ReplyRef(parent=parent, root=root)
                )
                break

if __name__ == "__main__":
    main()
    
