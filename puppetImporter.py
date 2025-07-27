import json 

class Bone:
    def __init__(self,label,x,y,spriteIndex,childBonesLayer1,childBonesLayer1Num,childBonesLayer2,childBonesLayer2Num):
        self.label=label
        self.x=x
        self.y=y
        self.spriteIndex=spriteIndex
        self.childBonesLayer1=childBonesLayer1
        self.childBonesLayer1Num=childBonesLayer1Num
        self.childBonesLayer2=childBonesLayer2
        self.childBonesLayer2Num=childBonesLayer2Num

class Puppet:
    def __init__(self,label,x,y,bones,bonesNum):
        self.label=label
        self.x=x
        self.y=y
        self.bones=bones
        self.bonesNum=bonesNum
        
def createPuppet(puppetFile):
    return Puppet(puppetFile["label"],puppetFile["x"],puppetFile["y"],puppetFile["bones"],len(puppetFile["bones"]))
        
def importPuppetFromJson(fileName):
    with open(fileName,"r") as f:
        puppetFile = json.load(f)
        puppet=createPuppet(puppetFile)
        print(puppet.label)
        print(puppet.x)
        print(puppet.y)
        print(puppet.bones)
        print(puppet.bonesNum)
       
if(__name__ == "__main__"):
   importPuppetFromJson("mascot.json") 