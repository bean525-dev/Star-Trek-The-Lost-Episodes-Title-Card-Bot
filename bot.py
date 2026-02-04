import re
import os
from atproto import Client, models
from PIL import Image, ImageDraw, ImageFont

# 1. Login to Bluesky
client = Client()
client.login(os.environ['BSKY_HANDLE'], os.environ['BSKY_PASSWORD'])

import textwrap

def create_card(series, title):
    # Base styles tuned to your specific templates
    # Base styles tuned to your specific templates
    styles = {
        "TOS": {
            "font": "fonts/horizon.ttf", 
            "bg": "templates/TOS_bg.jpg", 
            "color": "yellow", 
            "shadow_color": "black",
            "size": 75,       # Reduced from 100
            "x_pos": 0.92,    # Pulled slightly away from the far edge
            "y_pos": 0.85, 
            "align": "right",
            "anchor": "rd", 
            "wrap": 22        # Increased so it doesn't stack too many lines
        },
        "DS9": {
            "font": "fonts/handel.ttf", 
            "bg": "templates/DS9_bg.jpg",
            "color": "#ADD8E6", 
            "shadow_color": "#00008B", 
            "size": 60,       # Reduced from 85
            "x_pos": 0.08,    # 8% from left
            "y_pos": 0.12, 
            "align": "left",
            "anchor": "la", 
            "wrap": 25        # Wider wrap for the top-left area
        },
        "TNG": {
            "font": "fonts/swiss.ttf", 
            "bg": "templates/TNG_bg.jpg",
            "color": "#cbd5e1", 
            "size": 70,       # Reduced from 90
            "x_pos": 0.5, "y_pos": 0.75,
            "align": "center", "anchor": "mm", "wrap": 28
        },
        "VOY": {
            "font": "fonts/handel.ttf", 
            "bg": "templates/VOY_bg.jpg",
            "color": "white", 
            "size": 65,       # Reduced from 80
            "x_pos": 0.5, "y_pos": 0.75,
            "align": "center", "anchor": "mm", "wrap": 28
        }
    }
    
    # Shields Up: Default to TNG if series isn't recognized
    s = styles.get(series, styles["TNG"])
    
    # 1. Load Background Image
    try:
        img = Image.open(s["bg"])
    except FileNotFoundError:
        print(f"❌ ERROR: Could not find background image at {s['bg']}")
        return

    # 2. Setup Font and Dynamic Sizing
    font_size = s["size"]
    # Shrink font slightly for very long titles to prevent clipping
    if len(title) > 25:
        font_size = int(s["size"] * 0.8)
    
    try:
        font = ImageFont.truetype(s["font"], font_size)
    except OSError:
        print(f"❌ ERROR: Could not find font file at {s['font']}")
        return

    draw = ImageDraw.Draw(img)
    W, H = img.size
    
    # Wrap text based on the style's width setting
    wrapped_text = textwrap.fill(title, width=s["wrap"])
    
    # Calculate target position based on percentages
    target_xy = (W * s["x_pos"], H * s["y_pos"])

    # 3. Draw Shadow (offset by 4 pixels)
    shadow_color = s.get("shadow_color", "black")
    shadow_xy = (target_xy[0] + 4, target_xy[1] + 4)
    draw.multiline_text(
        shadow_xy, wrapped_text, font=font, fill=shadow_color,
        anchor=s["anchor"], align=s["align"], spacing=10
    )

    # 4. Draw Main Text
    draw.multiline_text(
        target_xy, wrapped_text, font=font, fill=s["color"],
        anchor=s["anchor"], align=s["align"], spacing=10
    )

    img.save("output.png")

# 2. Look for your latest post
# We use a dictionary for the params which the SDK will handle automatically
params = {
    'actor': os.environ['BSKY_HANDLE'],
    'limit': 5
}

# Now we pass that dictionary into the function
response = client.app.bsky.feed.get_author_feed(params=params)

for feed_view in response.feed:
    text = feed_view.post.record.text
    # Regex to find: Tonight's Lost VOY Episode: "The Uprising"
    match = re.search(r"Lost (\w+) Episode: \"(.+)\"", text)
    
    if match:
        series, title = match.groups()
        # Check if we already replied (simple check: does the post have replies?)
        if feed_view.post.reply_count == 0:
            create_card(series, title)
            
            # 3. Upload and Reply
            with open("output.png", "rb") as f:
                img_data = f.read()
            
            # Upload the image data to Bluesky
            upload = client.upload_blob(img_data)
            
            # Create the reply reference
            parent = {"cid": feed_view.post.cid, "uri": feed_view.post.uri}
            root = feed_view.post.record.reply.root if feed_view.post.record.reply else parent
            
            # THE FIX: We use send_images (plural) or just pass the blob correctly
            client.send_image(
                text="", 
                image=img_data, # Use the raw data here
                image_alt=f"Star Trek {series} style title card for {title}",
                reply_to=models.AppBskyFeedPost.ReplyRef(parent=parent, root=root)
            )
            print(f"Success! Replied to: {title}")
            break
