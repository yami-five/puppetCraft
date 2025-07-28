import json, spritesLoader, puppet
        
def createPuppet(puppetFile,sprites):
    return puppet.Puppet(puppetFile,sprites)
        
def importPuppetFromJson(fileName):
    with open(fileName,"r") as f:
        puppetFile = json.load(f)
        sprites=spritesLoader.importSprites(puppetFile["spritesPath"])
        puppet=createPuppet(puppetFile,sprites)
        return puppet
       
if(__name__ == "__main__"):
   importPuppetFromJson("mascot.json") 