import puppet,json,os

def add_bones(bones):
    data=[]
    for i in range(len(bones)):
        data.append(bones[i].get_bone_dict())
    return data

def add_bonesC(bones,results):
    for bone in bones:
        results.append(bone.label)
        add_bonesC(bone.childBonesLayer1,results)
        add_bonesC(bone.childBonesLayer2,results)

def save_to_file(puppet,settings,filename):
    if(os.path.exists(f'{filename}_backup.json')):
        os.remove(f'{filename}_backup.json')
    os.rename(f'{filename}.json',f'{filename}_backup.json')
    with open(f'{filename}.json',"w") as f:
        data = puppet.get_puppet_dict()
        data["bones"]=add_bones(puppet.bones)
        json.dump(data, f, indent=4, ensure_ascii=False)
    with open("settings.json","w") as f:
        json.dump(settings,f, indent=4, ensure_ascii=False)
    results=[]
    results.append(puppet.label)
    add_bonesC(puppet.bones,results)
    results.reverse()
    with open("CPuppet.txt","w") as f:
        for result in results:
            f.write(f'{result}\n')