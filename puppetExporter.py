import puppet,json,os

def add_bones(bones):
    data=[]
    for i in range(len(bones)):
        data.append(bones[i].get_bone_dict())
    return data

def save_to_file(puppet,settings):
    if(os.path.exists(f'{puppet.label}_backup.json')):
        os.remove(f'{puppet.label}_backup.json')
    os.rename(f'{puppet.label}.json',f'{puppet.label}_backup.json')
    with open(f'{puppet.label}.json',"w") as f:
        data = puppet.get_puppet_dict()
        data["bones"]=add_bones(puppet.bones)
        json.dump(data, f, indent=4, ensure_ascii=False)
    with open("settings.json","w") as f:
        json.dump(settings,f, indent=4, ensure_ascii=False)