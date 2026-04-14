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
            "green4":(38, 61, 43),
            "white":(242, 232, 207),
            "black":(0,0,0)
        }
        self.modes=["Edit Mode","Animation Mode","Play Mode"]

    def draw_green_box(self,x,y,width,height,isOn):
        color=self.color["green2"]
        if(isOn): color=self.color["green4"]
        pygame.draw.rect(self.screen,color,(x,y,width,height))
        pygame.draw.rect(self.screen,self.color["green1"],(x,y,width,height),2)
    
    def print_active_bone_coords(self,activeBone):
        self.draw_green_box(self.width-240,self.heigth-20,240,20,False)
        coords = self.font.render(f'x:{int(round(activeBone.worldMatrix[0][2]))}, y:{int(round(activeBone.worldMatrix[1][2]))}, angle:{activeBone.angle}', True, self.color["black"])
        self.screen.blit(coords, (self.width-230,self.heigth-15))

    def draw_ui(self,settings,activeBone,mode,keyFrames):
        self.draw_green_box(self.width-240,0,240,self.heigth,False)
        for i in range(len(self.bones)):
            self.draw_green_box(self.width-240,i*20+20,240,20,activeBone==self.bones[i])
            self.screen.blit(self.font.render(f'{self.bones[i].label}', True, self.color["black"]), (self.width-200,i*20+25))
        self.draw_green_box(0,self.heigth-20,self.width,20,False)
        self.print_active_bone_coords(activeBone)
        i=0
        for key,value in settings.items():
            self.draw_green_box(i*240,self.heigth-20,240,20,value)
            self.screen.blit(self.font.render(f'{key}', True, self.color["black"]), (i*240+30,self.heigth-15))
            i+=1
        self.draw_green_box(0,0,self.width,20,False)
        for i in range(len(self.modes)):
            self.draw_green_box(i*240,0,240,20,mode.value==i)
            self.screen.blit(self.font.render(f'{self.modes[i]}', True, self.color["black"]), (i*240+30,5))
        if(mode.value==1):
           self.draw_green_box(0,20,240,self.heigth-40,False) 
           self.screen.blit(self.font.render(f'KeyFrames', True, self.color["black"]), (30,30))
           self.draw_green_box(30,50,50,20,True) 
           self.screen.blit(self.font.render(f'Add', True, self.color["black"]), (40,55))
           self.draw_green_box(30,self.heigth-50,50,20,True) 
           self.screen.blit(self.font.render(f'Calc', True, self.color["black"]), (40,self.heigth-45))
           self.draw_green_box(100,self.heigth-50,50,20,True) 
           self.screen.blit(self.font.render(f'Clear', True, self.color["black"]), (110,self.heigth-45))