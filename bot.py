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
            "shadow_color": "black",
            "size": 75,
            "x_pos": 0.92, "y_pos": 0.85,
            "align": "right", "anchor": "rd", "wrap": 22
        },
        "DS9": {
            "font": "fonts/handel.ttf", 
            "bg": "templates/DS9_bg.jpg",
            "color": "#ADD8E6", 
            "shadow_color": "#00008B", 
            "size": 55,
            "x_pos": 0.08, "y_pos": 0.12,
            "align": "left", "anchor": "la", "wrap": 35
        },
        "TNG": {
            "font": "fonts/TNG_Credits.ttf", 
            "bg": "templates/TNG_bg.jpg",
            "color": "#cbd5e1", 
            "size": 70,
            "x_pos": 0.5, "y_pos": 0.75,
            "align": "center", "anchor": "mm", "wrap": 28
        },
        "VOY": {
            "font": "fonts/handel.ttf", 
            "bg": "templates/VOY_bg.jpg",
            "color": "white", 
            "size": 65,
            "x_pos": 0.5, "y_pos": 0.75,
            "align": "center", "anchor": "mm", "wrap": 28
        }
    }
    
    s = styles.get(series, styles["TNG"])
    
    # Add quotes to the title automatically
    quoted_title = f'"{title}"'

    # Load Background
    try:
        img = Image.open(s["bg"])
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

    # Draw Shadow
    shadow_color = s.get("shadow_color", "black")
    shadow_xy = (target_xy[0] + 4, target_xy[1] + 4)
    draw.multiline_text(shadow_xy, wrapped_text, font=font, fill=shadow_color, anchor=s["anchor"], align=s["align"], spacing=5)

    # Draw Main Text
    draw.multiline_text(target_xy, wrapped_text, font=font, fill=s["color"], anchor=s["anchor"], align=s["align"], spacing=5)

    img.save("output.png")
    return True

# --- 2. BLUESKY INTERACTION ---
def main():
    client = Client()
    client.login(os.environ['BSKY_HANDLE'], os.environ['BSKY_PASSWORD'])

    params = {'actor': os.environ['BSKY_HANDLE'], 'limit': 5}
    response = client.app.bsky.feed.get_author_feed(params=params)

    for feed_view in response.feed:
        text = feed_view.post.record.text
        # Regex to find: Tonight's Lost VOY Episode: "The Uprising"
        match = re.search(r"Lost (\w+) Episode: \"(.+)\"", text)
        
        if match:
            series = match.group(1)
            title = match.group(2)
            print(f"Found: {series} - {title}")

            # Generate the image
            if create_card(series, title):
                # Upload and Reply
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
                print("Successfully replied with title card!")
                break

if __name__ == "__main__":
    main()
