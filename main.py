import pygame
from enum import Enum
import puppetImporter

class Canvas:
    def __init__(self,height,width,screen):
        self.height=height
        self.width=width
        self.screen=screen
        self.x=screen.get_width()/2-(self.width/2)*scale
        self.y=screen.get_height()/2-(self.height/2)*scale
        
    def draw_canvas(self):
        pygame.draw.rect(self.screen,black,(self.x,self.y,self.width*scale,self.height*scale))
        
    def update_canvas_coords(self):
        self.x=screen.get_width()/2-(self.width/2)*scale
        self.y=screen.get_height()/2-(self.height/2)*scale

def draw_sprite(bone,parentX,parentY):
    startX=(bone.worldMatrix[0][2]+(parentX-bone.worldMatrix[0][2])/2)-bone.sprite.size/2
    startY=(bone.worldMatrix[1][2]+(parentY-bone.worldMatrix[1][2])/2)-bone.sprite.size/2
    offsetX=canvas.x
    offsetY=canvas.y
    for x in range (bone.sprite.size):
      for y in range (bone.sprite.size): 
        if(bone.sprite.pixels[x*bone.sprite.size+y]!=(255,0,255)):
            draw_x = int((x + startX) * scale + offsetX)
            draw_y = int((y + startY) * scale + offsetY)
            for dx in range(scale):
                for dy in range(scale):
                    screen.set_at((draw_x+dx,draw_y+dy),bone.sprite.pixels[x*bone.sprite.size+y])  
       
def draw_bone(bone,parentX,parentY):
    offsetX=canvas.x
    offsetY=canvas.y
    draw_sprite(bone,parentX,parentY)
    pygame.draw.line(screen,white,(bone.worldMatrix[0][2]*scale+offsetX,bone.worldMatrix[1][2]*scale+offsetY),(parentX*scale+offsetX,parentY*scale+offsetY))
    pygame.draw.circle(screen,red,(bone.worldMatrix[0][2]*scale+offsetX,bone.worldMatrix[1][2]*scale+offsetY),3)
    pygame.draw.circle(screen,red,(parentX*scale+offsetX,parentY*scale+offsetY),3)
    bone_label = font.render(bone.label, True, red)
    screen.blit(bone_label, (bone.worldMatrix[0][2]*scale+offsetX+5, bone.worldMatrix[1][2]*scale+offsetY))


def draw_puppet(puppet):
    offsetX=canvas.x
    offsetY=canvas.y
    bone_label = font.render("root", True, red)
    screen.blit(bone_label, (puppet.worldMatrix[0][2]*scale+offsetX+5, puppet.worldMatrix[1][2]*scale+offsetY))
    for bone in puppet.bones:
        draw_bone(bone,puppet.worldMatrix[0][2],puppet.worldMatrix[1][2])

pygame.init()
width, height = 1280, 720
canvas_h, canvas_w = 320, 240
scale=1
screen=pygame.display.set_mode((width,height))
pygame.display.set_caption("Puppet Craft")
font = pygame.font.SysFont(None, 20)
white = (255,255,255)
black = (0,0,0)
grey = (127,127,127)
red = (255,0,0)
green = (0,255,0)
blue = (0,0,255)
teal = (0,128,128)
midnight_blue = (25,25,112)

running=True
clicked=False

canvas=Canvas(320,240,screen)
puppet=puppetImporter.importPuppetFromJson("mascot.json")
while running:
    screen.fill(grey) 
    canvas.draw_canvas()
    draw_puppet(puppet)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False    
        if event.type==pygame.KEYDOWN:
            if event.key == pygame.K_PAGEUP:
                if(scale<2): 
                    scale+=1
                    canvas.update_canvas_coords()
            elif event.key == pygame.K_PAGEDOWN:
                if(scale>1): 
                    scale-=1
                    canvas.update_canvas_coords()
    pygame.display.flip()
pygame.quit()