import json, spritesLoader, puppet
        
def createPuppet(puppetFile,sprites):
    return puppet.Puppet(puppetFile,sprites)


def importPuppetBundleFromJson(fileName):
    with open(fileName, "r") as f:
        puppetFile = json.load(f)
        sprites = spritesLoader.importSprites(puppetFile["spritesPath"])
        puppet_obj = createPuppet(puppetFile, sprites)
        return {
            "puppet": puppet_obj,
            "animations": puppetFile.get("animations"),
            "raw": puppetFile,
        }
        
def importPuppetFromJson(fileName):
    bundle = importPuppetBundleFromJson(fileName)
    return bundle["puppet"]
       
if(__name__ == "__main__"):
   importPuppetFromJson("mascot.json") 
