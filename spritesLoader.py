import json,os
from PIL import Image 

class Sprite:
    def __init__(self,label,size,pixels):
        self.label=label
        self.size=size
        self.pixels=pixels

def getSpriteLabel(path):
    spriteLabel=path.replace("_"," ")
    spriteLabel=spriteLabel.split()
    for i in range(1,len(spriteLabel)):
        spriteLabel[i]=spriteLabel[i].capitalize()
    return "".join(spriteLabel).replace(".bmp","")

def importSprites(path):
    sprites=[]
    for bmpFile in os.listdir(path):
        bmpPath=os.path.join(path, bmpFile)
        image = Image.open(bmpPath)
        (img_x,img_y)=image.size
        converted_img=[]
        for x in range (img_x-1,-1,-1):
            for y in range (0,img_y):
                (r,g,b)=image.getpixel((x, y))
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                r5 = r >> 3
                g6 = g >> 2
                b5 = b >> 3
                rgb565 = (r5 << 11) | (g6 << 5) | b5
                converted_img.append(rgb565)
        sprites.append(Sprite(getSpriteLabel(bmpFile),x,converted_img))
    return sprites
        

if(__name__ == "__main__"):
   sprites=importSprites("sprites") 