import pygame,puppetImporter,puppetExporter,os,json

isTextVisible=True
isBoneVisible=True

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
    if(bone.spriteIndex<0): return
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

def print_active_bone_coord(activeBone):
    coords = font2.render(f'{activeBone.worldMatrix[0][2]},{activeBone.worldMatrix[1][2]}', True, red)
    screen.blit(coords, (0,0))
      
def draw_bone(bone,parentX,parentY):
    offsetX=canvas.x
    offsetY=canvas.y
    for childBone in bone.childBonesLayer2:
        draw_bone(childBone,bone.worldMatrix[0][2],bone.worldMatrix[1][2])
    draw_sprite(bone,parentX,parentY)
    if(bone.spriteIndex>=0 and isBoneVisible):
        pygame.draw.line(screen,white,(bone.worldMatrix[0][2]*scale+offsetX,bone.worldMatrix[1][2]*scale+offsetY),(parentX*scale+offsetX,parentY*scale+offsetY))
    color=red
    if(activeBone==bone): color=green
    if(isBoneVisible):
        pygame.draw.circle(screen,color,(bone.worldMatrix[0][2]*scale+offsetX,bone.worldMatrix[1][2]*scale+offsetY),3)
    if(isTextVisible):
        bone_label = font.render(bone.label, True, color)
        screen.blit(bone_label, (bone.worldMatrix[0][2]*scale+offsetX+5, bone.worldMatrix[1][2]*scale+offsetY))
    
    for childBone in bone.childBonesLayer1:
        draw_bone(childBone,bone.worldMatrix[0][2],bone.worldMatrix[1][2])
    
def draw_puppet(puppet):
    offsetX=canvas.x
    offsetY=canvas.y
    color=red
    if(activeBone==puppet): color=green
    if(isBoneVisible):
        pygame.draw.circle(screen,color,(puppet.worldMatrix[0][2]*scale+offsetX,puppet.worldMatrix[1][2]*scale+offsetY),3)
    if(isTextVisible):
        bone_label = font.render("root", True, color)
        screen.blit(bone_label, (puppet.worldMatrix[0][2]*scale+offsetX+5, puppet.worldMatrix[1][2]*scale+offsetY))
    for bone in puppet.bones:
        draw_bone(bone,puppet.worldMatrix[0][2],puppet.worldMatrix[1][2])

def move_bone(x,y):
    activeBone.x+=x
    activeBone.y+=y
    puppet.recalculate_world_matrices()

def save_bones_to_list(bones):
    for bone in bones:
        objects.append(bone)
        save_bones_to_list(bone.childBonesLayer1)
        save_bones_to_list(bone.childBonesLayer2)
    
def save_puppet_to_list(puppet):
    objects.append(puppet)
    save_bones_to_list(puppet.bones)

def change_active_bone(activeBone,offset):
    index=0
    for i in range (len(objects)):
        if(objects[i]==activeBone):
            index=i
            break
    index+=offset
    if(index>=len(objects)):
        index=0
    elif(index<0):
        index=len(objects)-1
    return objects[index]

if(__name__ == "__main__"):
    if(os.path.exists("settings.json")):
        with open("settings.json","r") as f:
            settings = json.load(f)
            if(settings["isBoneVisible"]=="False"):
                isBoneVisible=False
            else:
                isBoneVisible=True
            if(settings["isTextVisible"]=="False"):
                isTextVisible=False
            else:
                isTextVisible=True
                
    pygame.init()
    width, height = 1280, 720
    canvas_h, canvas_w = 320, 240
    scale=1
    screen=pygame.display.set_mode((width,height))
    pygame.display.set_caption("Puppet Craft")
    font = pygame.font.SysFont(None, 20)
    font2 = pygame.font.SysFont(None, 36)
    white = (255,255,255)
    black = (0,0,0)
    grey = (127,127,127)
    red = (255,0,0)
    green = (0,255,0)
    blue = (0,0,255)
    teal = (0,128,128)
    midnight_blue = (25,25,112)
    objects=[]
    running=True
    clicked=False

    canvas=Canvas(320,240,screen)
    puppet=puppetImporter.importPuppetFromJson("mascot.json")
    save_puppet_to_list(puppet)
    activeBone=puppet
    while running:
        screen.fill(grey) 
        canvas.draw_canvas()
        draw_puppet(puppet)
        print_active_bone_coord(activeBone)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False    
            if event.type==pygame.KEYDOWN:
                if event.key == pygame.K_PAGEUP:
                    if(scale<4): 
                        scale+=1
                        canvas.update_canvas_coords()
                elif event.key == pygame.K_PAGEDOWN:
                    if(scale>1): 
                        scale-=1
                        canvas.update_canvas_coords()
                elif event.key == pygame.K_a:
                    activeBone=change_active_bone(activeBone,1)
                elif event.key == pygame.K_d:
                    activeBone=change_active_bone(activeBone,-1)
                elif event.key == pygame.K_h:
                    isTextVisible=not isTextVisible  
                elif event.key == pygame.K_b:
                    isBoneVisible=not isBoneVisible            
                keys = pygame.key.get_mods()
                if keys & pygame.KMOD_CTRL:
                    if event.key == pygame.K_s:
                        settings={"isBoneVisible":str(isBoneVisible),"isTextVisible":str(isTextVisible)}
                        puppetExporter.save_to_file(puppet,settings)
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            move_bone(0,-1)
        if keys[pygame.K_DOWN]:
            move_bone(0,1)
        if keys[pygame.K_LEFT]:
            move_bone(-1,0)
        if keys[pygame.K_RIGHT]:
            move_bone(1,0)
        pygame.display.flip()
    pygame.quit()