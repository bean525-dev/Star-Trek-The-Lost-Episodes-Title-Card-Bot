import re
import os
from atproto import Client
from PIL import Image, ImageDraw, ImageFont

# 1. Login to Bluesky
client = Client()
client.login(os.environ['BSKY_HANDLE'], os.environ['BSKY_PASSWORD'])

def create_card(series, title):
    # Map series to your font/bg files
    styles = {
        "VOY": {"font": "handel.ttf", "bg": "VOY_bg.jpg", "color": "gold"},
        "DS9": {"font": "handel.ttf", "bg": "DS9_bg.jpg", "color": "white"},
        "TNG": {"font": "TNG_Credits", "bg": "TNG_bg.jpg", "color": "#cbd5e1"},
        "TOS": {"font": "TOS_Title.ttf", "bg": "TOS_bg.jpg", "color": "yellow"}
    }
    s = styles.get(series, styles["TNG"])
    
    img = Image.open(s["bg"])
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(s["font"], 120)
    
    # Draw text centered in the bottom third
    w, h = img.size
    draw.text((w/2, h*0.75), title, fill=s["color"], font=font, anchor="mm")
    img.save("output.png")

# 2. Look for your latest post
# Replace 'YOUR_BOT_DID' with your bot's actual DID or handle
params = {'repo': os.environ['BSKY_HANDLE'], 'collection': 'app.bsky.feed.post', 'limit': 5}
response = client.app.bsky.feed.get_author_feed(actor=os.environ['BSKY_HANDLE'])

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
            upload = client.upload_blob(img_data)
            
            # Reply to the original post
            parent = {"cid": feed_view.post.cid, "uri": feed_view.post.uri}
            root = feed_view.post.record.reply.root if feed_view.post.record.reply else parent
            
            client.send_image(
                text="", 
                image=upload.blob, 
                image_alt=f"Title card for {title}",
                reply_to={"root": root, "parent": parent}
            )
            print(f"Replied to: {title}")
            break # Just do one per run
