import json
import spritesLoader

class Bone:
    def __init__(self,boneJson,sprites):
        self.label=boneJson["label"]
        self.x=boneJson["x"]
        self.y=boneJson["y"]
        self.sprite=sprites[boneJson["spriteIndex"]]

class Puppet:
    def __init__(self,puppetJson,sprites):
        self.label=puppetJson["label"]
        self.x=puppetJson["x"]
        self.y=puppetJson["y"]
        self.bones=[]
        for boneJson in puppetJson["bones"]:  
            self.bones.append(Bone(boneJson,sprites))
        self.bonesNum=len(self.bones)
        
def createPuppet(puppetFile,sprites):
    return Puppet(puppetFile,sprites)
        
def importPuppetFromJson(fileName):
    with open(fileName,"r") as f:
        puppetFile = json.load(f)
        sprites=spritesLoader.importSprites(puppetFile["spritesPath"])
        puppet=createPuppet(puppetFile,sprites)
        print(puppet.label)
        print(puppet.x)
        print(puppet.y)
        print(puppet.bones)
        print(puppet.bonesNum)
       
if(__name__ == "__main__"):
   importPuppetFromJson("mascot.json") 