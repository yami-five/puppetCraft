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

pygame.init()
width, height = 1280, 720
canvas_h, canvas_w = 320, 240
scale=1
screen=pygame.display.set_mode((width,height))
pygame.display.set_caption("Puppet Craft")

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

while running:
    screen.fill(grey) 
    canvas.draw_canvas()
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