from PIL import Image, ImageDraw

img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Dark background circle
for i in range(256, 0, -1):
    r = int(30 + (1 - i/256) * 10)
    g = int(30 + (1 - i/256) * 10)
    b = int(50 + (1 - i/256) * 30)
    draw.ellipse([256-i, 256-i, 256+i, 256+i], fill=(r, g, b))

# Outer glow rings
for i in range(8):
    alpha = int(180 - i * 20)
    radius = 220 + i * 4
    draw.ellipse([256-radius, 256-radius, 256+radius, 256+radius], outline=(120, 80, 220, alpha), width=2)

# Play triangle with purple glow
for i in range(12, 0, -1):
    offset = i * 2
    draw.polygon([
        (195 - offset, 155 - offset),
        (195 - offset, 355 + offset),
        (375 + offset, 255)
    ], fill=(140, 100, 255, int(255 - i * 15)))

# Inner white triangle
draw.polygon([
    (195, 155),
    (195, 355),
    (375, 255)
], fill=(255, 255, 255))

# Accent star dots
for px, py in [(140, 130), (380, 140), (130, 370), (390, 380), (256, 80)]:
    draw.ellipse([px-4, py-4, px+4, py+4], fill=(180, 140, 255, 200))
    draw.ellipse([px-2, py-2, px+2, py+2], fill=(255, 255, 255, 255))

# Only run on desktop - skip on Android
import sys
if 'android' not in sys.platform.lower():
    img.save('icon.png', 'PNG')
    print('Icon created successfully')
else:
    print('Skipping icon generation on Android')
