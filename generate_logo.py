
from PIL import Image, ImageDraw, ImageFont
import os

if not os.path.exists("assets"):
    os.makedirs("assets")

# Create a blank image with white background
width, height = 400, 100
image = Image.new('RGB', (width, height), 'white')
draw = ImageDraw.Draw(image)

# Colors
gold_color = (185, 161, 95) # Approx Kuveyt Turk Gold
black_color = (0, 0, 0)

# Draw a simple shape (Rectangle/Icon placeholder)
draw.rectangle([10, 10, 90, 90], fill=gold_color)

# Add Text (If font not found, use default)
try:
    # Try a standard font
    font_large = ImageFont.truetype("arial.ttf", 40)
    font_small = ImageFont.truetype("arial.ttf", 20)
except:
    font_large = ImageFont.load_default()
    font_small = ImageFont.load_default()

draw.text((110, 20), "KUVEYT TÜRK", fill=black_color, font=font_large)
draw.text((110, 65), "PORTFÖY YÖNETİMİ", fill=gold_color, font=font_small)

# Save
image.save("assets/logo.png")
print("✅ Logo generated at assets/logo.png")
