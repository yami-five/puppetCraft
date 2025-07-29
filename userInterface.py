import pygame

class UI:
    def __init__(self,screen,bones):
        self.screen=screen
        self.bones=bones
        self.width=self.screen.get_width()
        self.heigth=self.screen.get_height()
        self.font=pygame.font.SysFont(None, 20)
        self.color={
            "red1":(188, 71, 73),
            "red2":(129,50,50),
            "green1":(56, 102, 65),
            "green2":(106, 153, 78),
            "green3":(167, 201, 87),
            "white":(242, 232, 207),
            "black":(0,0,0)
        }

    def draw_green_box(self,x,y,width,height):
        pygame.draw.rect(self.screen,self.color["green2"],(x,y,width,height))
        pygame.draw.rect(self.screen,self.color["green1"],(x,y,width,height),2)
    
    def draw_red_circle(self,x,y,radius,isOn):
        color=self.color["red1"]
        if(isOn):
            color=self.color["red2"]
        pygame.draw.circle(self.screen,color,(x,y),radius)
        pygame.draw.circle(self.screen,self.color["black"],(x,y),radius,width=1)
    
    def print_active_bone_coords(self,activeBone):
        self.draw_green_box(self.width-240,self.heigth-20,240,20)
        coords = self.font.render(f'x:{int(round(activeBone.worldMatrix[0][2]))}, y:{int(round(activeBone.worldMatrix[1][2]))}, angle:{activeBone.angle}', True, self.color["black"])
        self.screen.blit(coords, (self.width-230,self.heigth-15))

    def draw_ui(self,settings,activeBone):
        self.draw_green_box(self.width-240,0,240,self.heigth)
        for i in range(len(self.bones)):
            self.draw_green_box(self.width-240,i*20+20,240,20)
            self.draw_red_circle(self.width-230,i*20+30,7,activeBone==self.bones[i])
            self.screen.blit(self.font.render(f'{self.bones[i].label}', True, self.color["black"]), (self.width-200,i*20+25))
        self.draw_green_box(0,self.heigth-20,self.width,20)
        self.print_active_bone_coords(activeBone)
        i=0
        for key,value in settings.items():
            self.draw_green_box(i*240,self.heigth-20,240,20)
            self.draw_red_circle(i*240+10,self.heigth-10,7,value)
            self.screen.blit(self.font.render(f'{key}', True, self.color["black"]), (i*240+30,self.heigth-15))
            i+=1