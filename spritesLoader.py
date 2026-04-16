import os

from PIL import Image

import puppet

def getSpriteLabel(path):
    spriteLabel = os.path.splitext(path)[0]
    spriteLabel = spriteLabel.replace("_", " ")
    spriteLabel=spriteLabel.split()
    for i in range(1,len(spriteLabel)):
        spriteLabel[i]=spriteLabel[i].capitalize()
    return "".join(spriteLabel)


def load_sprite_from_file(path, sprite_label=None):
    image = Image.open(path).convert("RGB")
    (img_x, img_y) = image.size
    if img_x != img_y:
        raise ValueError(f"Sprite must be square, got {img_x}x{img_y}")

    converted_img = []
    for x in range(img_x - 1, -1, -1):
        for y in range(0, img_y):
            converted_img.append(image.getpixel((x, y)))

    label = sprite_label or getSpriteLabel(os.path.basename(path))
    return puppet.Sprite(label, img_x, converted_img)

def importSprites(path):
    sprites = []
    for item in importSpriteEntries(path):
        sprites.append(item["sprite"])
    return sprites


def importSpriteEntries(path):
    entries = []
    if not os.path.isdir(path):
        return entries
    for bmpFile in os.listdir(path):
        bmpPath = os.path.join(path, bmpFile)
        if not os.path.isfile(bmpPath):
            continue
        entries.append(
            {
                "path": bmpPath,
                "sprite": load_sprite_from_file(bmpPath, getSpriteLabel(bmpFile)),
            }
        )
    return entries
        

if(__name__ == "__main__"):
   sprites=importSprites("sprites")
   print("aaa")
