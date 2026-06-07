import numpy, math


def normalize_sprite_mirror_axis(value):
    text = str(value or "").strip().lower()
    if not text or text == "none":
        return "none"

    has_x = "x" in text
    has_y = "y" in text
    if has_x and has_y:
        return "xy"
    if has_x:
        return "x"
    if has_y:
        return "y"
    return "none"


def puppet_mirror_axis_inverts_sprite_rotation_direction(value):
    axis = normalize_sprite_mirror_axis(value)
    return axis in ("x", "y")


def invert_base_sprite_rotation(value):
    try:
        numeric = float(value)
    except Exception:
        return value
    if not math.isfinite(numeric):
        return value
    return -numeric

class Sprite:
    def __init__(self,label,size,pixels):
        self.label=label
        self.size=size
        self.pixels=pixels

class Bone:
    def __init__(self,boneJson,sprites,parentWorldMatrix,invertBaseSpriteRotation=False):
        self.label=boneJson["label"]
        self.x=boneJson["x"]
        self.y=boneJson["y"]
        self.angle=boneJson["angle"]
        self.spriteIndex=boneJson["spriteIndex"]
        self.baseSpriteRotation=boneJson["baseSpriteRotation"]
        if invertBaseSpriteRotation:
            self.baseSpriteRotation=invert_base_sprite_rotation(self.baseSpriteRotation)
        self.spriteMirrorAxis=normalize_sprite_mirror_axis(boneJson.get("spriteMirrorAxis", "none"))
        if(self.spriteIndex>=0):
            self.sprite=sprites[self.spriteIndex]
        self.localMatrix=numpy.array([[math.cos(self.angle),-math.sin(self.angle),int(round(self.x))],[math.sin(self.angle),math.cos(self.angle),int(round(self.y))],[0,0,1]])
        self.worldMatrix=parentWorldMatrix @ self.localMatrix
        self.childBonesLayer1=[]
        self.childBonesLayer2=[]
        for bone in boneJson["childBonesLayer1"]:
            self.childBonesLayer1.append(Bone(bone,sprites,self.worldMatrix,invertBaseSpriteRotation))
        for bone in boneJson["childBonesLayer2"]:
            self.childBonesLayer2.append(Bone(bone,sprites,self.worldMatrix,invertBaseSpriteRotation))
        
    def get_bone_dict(self):
        data= {
            "label":self.label,
            "x": self.x,
            "y": self.y,
            "angle": self.angle,
            "spriteIndex": self.spriteIndex,
            "baseSpriteRotation": self.baseSpriteRotation,
            "spriteMirrorAxis": self.spriteMirrorAxis,
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
        self.puppetMirrorAxis=normalize_sprite_mirror_axis(puppetJson.get("puppetMirrorAxis", "none"))
        self.spritesPath=str(puppetJson.get("spritesPath") or f"sprites_{(self.label).replace('Root','')}")
        self.backgroundImagePath=str(puppetJson.get("backgroundImagePath") or "")
        self.bones=[]
        self.localMatrix=numpy.array([[math.cos(self.angle),-math.sin(self.angle),int(round(self.x))],[math.sin(self.angle),math.cos(self.angle),int(round(self.y))],[0,0,1]])
        self.worldMatrix=self.localMatrix
        invertBaseSpriteRotation=puppet_mirror_axis_inverts_sprite_rotation_direction(self.puppetMirrorAxis)
        for boneJson in puppetJson["bones"]:  
            self.bones.append(Bone(boneJson,sprites,self.worldMatrix,invertBaseSpriteRotation))
        self.bonesNum=len(self.bones)
        
    def get_puppet_dict(self):
        return {
            "spritesPath":str(self.spritesPath or f"sprites_{(self.label).replace('Root','')}"),
            "backgroundImagePath":str(self.backgroundImagePath or ""),
            "label":self.label,
            "x": self.x,
            "y": self.y,
            "angle": self.angle,
            "puppetMirrorAxis": self.puppetMirrorAxis,
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
        
