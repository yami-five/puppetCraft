import json, spritesLoader, numpy, math

class Bone:
    def __init__(self,boneJson,sprites,parentWorldMatrix):
        self.label=boneJson["label"]
        self.x=boneJson["x"]
        self.y=boneJson["y"]
        self.sprite=sprites[boneJson["spriteIndex"]]
        self.localMatrix=numpy.array([[math.cos(0),-math.sin(0),self.x],[math.sin(0),math.cos(0),self.y],[0,0,1]])
        self.worldMatrix=parentWorldMatrix @ self.localMatrix

class Puppet:
    def __init__(self,puppetJson,sprites):
        self.label=puppetJson["label"]
        self.x=puppetJson["x"]
        self.y=puppetJson["y"]
        self.bones=[]
        self.localMatrix=numpy.array([[math.cos(0),-math.sin(0),self.x],[math.sin(0),math.cos(0),self.y],[0,0,1]])
        self.worldMatrix=self.localMatrix
        for boneJson in puppetJson["bones"]:  
            self.bones.append(Bone(boneJson,sprites,self.worldMatrix))
        self.bonesNum=len(self.bones)
        
def createPuppet(puppetFile,sprites):
    return Puppet(puppetFile,sprites)
        
def importPuppetFromJson(fileName):
    with open(fileName,"r") as f:
        puppetFile = json.load(f)
        sprites=spritesLoader.importSprites(puppetFile["spritesPath"])
        puppet=createPuppet(puppetFile,sprites)
        return puppet
       
if(__name__ == "__main__"):
   importPuppetFromJson("mascot.json") 