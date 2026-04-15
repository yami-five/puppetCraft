import json
import os

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

def save_puppet(puppet, filename_base):
    puppet_path = f"{filename_base}.json"
    backup_path = f"{filename_base}_backup.json"

    if os.path.exists(puppet_path):
        if os.path.exists(backup_path):
            os.remove(backup_path)
        os.replace(puppet_path, backup_path)

    with open(puppet_path, "w") as f:
        data = puppet.get_puppet_dict()
        data["bones"]=add_bones(puppet.bones)
        json.dump(data, f, indent=4, ensure_ascii=False)


def save_settings(settings, settings_path="settings.json"):
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)


def export_cpuppet(puppet, filename_base):
    output_path = f"{filename_base}.c"
    results=[]
    results.append(puppet.label)
    add_bonesC(puppet.bones,results)
    results.reverse()
    with open(output_path, "w") as f:
        for result in results:
            f.write(f'{result}\n')


def save_to_file(puppet, settings, filename):
    # Backward-compatible wrapper for older call sites.
    save_puppet(puppet, filename)
    save_settings(settings)
    export_cpuppet(puppet, filename)
