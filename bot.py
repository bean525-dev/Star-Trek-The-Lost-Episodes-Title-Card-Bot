import os
import re
import textwrap
from atproto import Client, models
from PIL import Image, ImageDraw, ImageFont

# --- 1. IMAGE GENERATION LOGIC ---
def create_card(series, title):
    # Base styles tuned to your specific templates
    styles = {
        "TOS": {
            "font": "fonts/horizon.ttf", 
            "bg": "templates/TOS_bg.jpg", 
            "color": "yellow", 
            "shadow": True,
            "shadow_color": "black",
            "size": 75,
            "x_pos": 0.92, "y_pos": 0.85,
            "align": "right", "anchor": "rd", "wrap": 22
        },
        "DS9": {
            "font": "fonts/handel.ttf", 
            "bg": "templates/DS9_bg.jpg",
            "top_color": "#e0e0e0",    # Metallic Silver
            "bottom_color": "#7da6ff", # Steel Blue
            "shadow": False,
            "size": 55,
            "x_pos": 0.08, "y_pos": 0.12,
            "align": "left", "anchor": "la", "wrap": 35
        },
        "TNG": {
            "font": "fonts/TNG_Credits.ttf", 
            "bg": "templates/TNG_bg.jpg",
            "color": "#5286ff", 
            "shadow": False,
            "size": 65,
            "x_pos": 0.12, "y_pos": 0.15,
            "align": "left", "anchor": "la", "wrap": 28
        },
        "VOY": {
            "font": "fonts/handel.ttf", 
            "bg": "templates/VOY_bg.jpg",
            "top_color": "#FF8C00",    # Deep Orange
            "bottom_color": "#FFE0B2", # Peach
            "shadow": False,
            "size": 60,
            "x_pos": 0.5, "y_pos": 0.18,
            "align": "center", "anchor": "ma", "wrap": 30
        }
    }
    
    s = styles.get(series, styles["TNG"])
    
    # Add quotes to the title automatically
    quoted_title = f'"{title}"'

    # Load Background as RGBA for proper gradient blending
    try:
        img = Image.open(s["bg"]).convert("RGBA")
    except FileNotFoundError:
        print(f"❌ Could not find {s['bg']}")
        return False

    # Dynamic Shrink Logic
    font_size = s["size"]
    if len(quoted_title) > 15:
        font_size = int(s["size"] * 0.8)
    if len(quoted_title) > 25:
        font_size = int(s["size"] * 0.6)
    
    try:
        font = ImageFont.truetype(s["font"], font_size)
    except OSError:
        print(f"❌ Could not find {s['font']}")
        return False

    draw = ImageDraw.Draw(img)
    W, H = img.size
    wrapped_text = textwrap.fill(quoted_title, width=s["wrap"])
    target_xy = (W * s["x_pos"], H * s["y_pos"])

    # --- DRAWING PHASE ---

    # 1. Draw Shadow ONLY for TOS (or if explicitly enabled)
    if s.get("shadow", False):
        sha_color = s.get("shadow_color", "black")
        draw.multiline_text((target_xy[0]+3, target_xy[1]+3), wrapped_text, font=font, fill=sha_color, anchor=s["anchor"], align=s["align"], spacing=5)

    # 2. Draw Main Text (Gradient for DS9/VOY, Solid for others)
    if "top_color" in s:
        # Create a mask of the text
        mask = Image.new("L", (W, H), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.multiline_text(target_xy, wrapped_text, font=font, fill=255, anchor=s["anchor"], align=s["align"], spacing=5)
        
        # Determine text boundaries for the gradient
        bbox = mask_draw.multiline_textbbox(target_xy, wrapped_text, font=font, anchor=s["anchor"], align=s["align"])
        
        # Create the vertical color fade
        gradient = Image.new("RGBA", (W, H), (0,0,0,0))
        grad_draw = ImageDraw.Draw(gradient)
        
        y_start, y_end = int(bbox[1]), int(bbox[3])
        height = y_end - y_start
        
        # Convert hex to RGB
        c1 = tuple(int(s["top_color"].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        c2 = tuple(int(s["bottom_color"].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

        for y in range(y_start, y_end + 1):
            curr_y = (y - y_start) / max(1, height)
            r = int(c1[0] + (c2[0] - c1[0]) * curr_y)
            g = int(c1[1] + (c2[1] - c1[1]) * curr_y)
            b = int(c1[2] + (c2[2] - c1[2]) * curr_y)
            grad_draw.line([(bbox[0], y), (bbox[2], y)], fill=(r, g, b, 255))

        # Composite the gradient onto image using the text mask
        img.paste(gradient, (0, 0), mask)
    else:
        # Solid Color path
        draw.multiline_text(target_xy, wrapped_text, font=font, fill=s["color"], anchor=s["anchor"], align=s["align"], spacing=5)

    # Final save (Convert back to RGB to remove alpha channel)
    img.convert("RGB").save("output.png")
    return True

# --- 2. BLUESKY INTERACTION ---
def main():
    client = Client()
    client.login(os.environ['BSKY_HANDLE'], os.environ['BSKY_PASSWORD'])

    params = {'actor': os.environ['BSKY_HANDLE'], 'limit': 5}
    response = client.app.bsky.feed.get_author_feed(params=params)

    for feed_view in response.feed:
        text = feed_view.post.record.text
        # Regex to find the pattern
        match = re.search(r"Lost (\w+) Episode: \"(.+)\"", text)
        
        if match:
            series = match.group(1)
            title = match.group(2)
            print(f"Found: {series} - {title}")

            if create_card(series, title):
                with open("output.png", "rb") as f:
                    img_data = f.read()
                
                parent = {"cid": feed_view.post.cid, "uri": feed_view.post.uri}
                root = feed_view.post.record.reply.root if feed_view.post.record.reply else parent
                
                client.send_image(
                    text="", 
                    image=img_data, 
                    image_alt=f"Star Trek {series} style title card for {title}",
                    reply_to=models.AppBskyFeedPost.ReplyRef(parent=parent, root=root)
                )
                print("Successfully replied!")
                break

if __name__ == "__main__":
    main()
