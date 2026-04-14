import numpy, math

class Sprite:
    def __init__(self,label,size,pixels):
        self.label=label
        self.size=size
        self.pixels=pixels

class Bone:
    def __init__(self,boneJson,sprites,parentWorldMatrix):
        self.label=boneJson["label"]
        self.x=boneJson["x"]
        self.y=boneJson["y"]
        self.angle=boneJson["angle"]
        self.spriteIndex=boneJson["spriteIndex"]
        self.baseSpriteRotation=boneJson["baseSpriteRotation"]
        if(self.spriteIndex>=0):
            self.sprite=sprites[self.spriteIndex]
        self.localMatrix=numpy.array([[math.cos(self.angle),-math.sin(self.angle),int(round(self.x))],[math.sin(self.angle),math.cos(self.angle),int(round(self.y))],[0,0,1]])
        self.worldMatrix=parentWorldMatrix @ self.localMatrix
        self.childBonesLayer1=[]
        self.childBonesLayer2=[]
        for bone in boneJson["childBonesLayer1"]:
            self.childBonesLayer1.append(Bone(bone,sprites,self.worldMatrix))
        for bone in boneJson["childBonesLayer2"]:
            self.childBonesLayer2.append(Bone(bone,sprites,self.worldMatrix))
        
    def get_bone_dict(self):
        data= {
            "label":self.label,
            "x": self.x,
            "y": self.y,
            "angle": self.angle,
            "spriteIndex": self.spriteIndex,
            "baseSpriteRotation": self.baseSpriteRotation,
            "childBonesLayer1": [],
            "childBonesLayer2": [],
        }
        for bone in self.childBonesLayer1:
            data["childBonesLayer1"].append(bone.get_bone_dict())
        for bone in self.childBonesLayer2:
            data["childBonesLayer2"].append(bone.get_bone_dict())
        return data
    
    def recalculate_world_matrices(self,parentWorldMatrix):
        self.localMatrix=numpy.array([[math.cos(self.angle),-math.sin(self.angle),int(round(self.x))],[math.sin(self.angle),math.cos(self.angle),int(round(self.y))],[0,0,1]])
        self.worldMatrix=parentWorldMatrix @ self.localMatrix
        for bone in self.childBonesLayer1:
            bone.recalculate_world_matrices(self.worldMatrix)
        for bone in self.childBonesLayer2:
            bone.recalculate_world_matrices(self.worldMatrix)

class Puppet:
    def __init__(self,puppetJson,sprites):
        self.label=puppetJson["label"]
        self.x=puppetJson["x"]
        self.y=puppetJson["y"]
        self.angle=puppetJson["angle"]
        self.bones=[]
        self.localMatrix=numpy.array([[math.cos(self.angle),-math.sin(self.angle),int(round(self.x))],[math.sin(self.angle),math.cos(self.angle),int(round(self.y))],[0,0,1]])
        self.worldMatrix=self.localMatrix
        for boneJson in puppetJson["bones"]:  
            self.bones.append(Bone(boneJson,sprites,self.worldMatrix))
        self.bonesNum=len(self.bones)
        
    def get_puppet_dict(self):
        return {
            "spritesPath":f"sprites_{(self.label).replace('Root','')}",
            "label":self.label,
            "x": self.x,
            "y": self.y,
            "angle": self.angle,
            "bones": []
        }
    
    # def convert_puppet_to_C(self):
    #     return  'static const RawPuppet rawPuppets[] = {{' \
    #             '    {{' \
    #             f'        .x = {self.x},' \
    #             f'        .y = {self.y},' \
    #             f'        .bonesNum = {len(self.bones)},' \
    #             f'        .bones = {self.bones},' \
    #             '    },' \
    #             '};'
    
    def recalculate_world_matrices(self):
        self.localMatrix=numpy.array([[math.cos(self.angle),-math.sin(self.angle),int(round(self.x))],[math.sin(self.angle),math.cos(self.angle),int(round(self.y))],[0,0,1]])
        self.worldMatrix=self.localMatrix
        for bone in self.bones:
            bone.recalculate_world_matrices(self.worldMatrix)
        
