import os
from PIL import Image, ImageDraw, ImageFont

def criar_icone(size, filename):
    img = Image.new('RGB', (size, size), color=(0, 123, 255))
    draw = ImageDraw.Draw(img)
    text = "C"
    try:
        font = ImageFont.truetype("arial.ttf", int(size * 0.7))
    except:
        font = ImageFont.load_default()
    
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    w, h = right - left, bottom - top
    draw.text(((size - w) / 2, (size - h) / 2.5), text, font=font, fill=(255, 255, 255))
    
    path = os.path.join("app", "static", "img", filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    print(f"Icone {filename} gerado em: {path}")

criar_icone(192, "icon-192.png")
criar_icone(512, "icon-512.png")
