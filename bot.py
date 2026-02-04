import re
import os
from atproto import Client, models
from PIL import Image, ImageDraw, ImageFont

# 1. Login to Bluesky
client = Client()
client.login(os.environ['BSKY_HANDLE'], os.environ['BSKY_PASSWORD'])

import textwrap

def create_card(series, title):
    # Base styles tuned to your templates
    styles = {
        "TOS": {
            "font": "fonts/horizon.ttf", 
            "color": "yellow", 
            "size": 100,
            "x_pos": 0.95, # 95% across (Right Side)
            "y_pos": 0.82, # 82% down
            "align": "right",
            "anchor": "rd", # Right-Descender (bottom-right)
            "wrap": 18
        },
        # You can add similar custom positioning for TNG/VOY later
    }
    
    s = styles.get(series, styles["TOS"]) # Default to TOS style
    img = Image.open(f"templates/{series}_bg.jpg")
    draw = ImageDraw.Draw(img)
    W, H = img.size

    # 1. HANDLE LONG TITLES (Shrink if needed)
    font_size = s["size"]
    if len(title) > 20:
        font_size = int(s["size"] * 0.75) # Shrink to 75% size
    
    font = ImageFont.truetype(s["font"], font_size)
    wrapped_text = textwrap.fill(title, width=s["wrap"])

    # Target position based on the percentages above
    target_xy = (W * s["x_pos"], H * s["y_pos"])

    # 2. DRAW DROP SHADOW (The secret to the "Pro" look)
    # Draw black text first, shifted 5 pixels down and right
    shadow_xy = (target_xy[0] + 5, target_xy[1] + 5)
    draw.multiline_text(
        shadow_xy, wrapped_text, font=font, fill="black",
        anchor=s["anchor"], align=s["align"], spacing=10
    )

    # 3. DRAW MAIN TEXT
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
