import json
import math
import os
import re
import tempfile


def _float_or_zero(value):
    try:
        numeric = float(value)
    except Exception:
        return 0.0
    if not math.isfinite(numeric):
        return 0.0
    return numeric


def _puppet_inverts_sprite_rotation_direction(puppet):
    axis = _normalize_sprite_mirror_axis(getattr(puppet, "puppetMirrorAxis", "none"))
    return axis in ("x", "y")


def _euzebia_base_sprite_rotation(value, invert_direction=False):
    angle = _float_or_zero(value)
    if invert_direction and angle != 0.0:
        return -angle
    return angle


def _apply_euzebia_sprite_rotation_workaround(bone_data, invert_direction=False):
    bone_data["baseSpriteRotation"] = _euzebia_base_sprite_rotation(
        bone_data.get("baseSpriteRotation", 0.0),
        invert_direction=invert_direction,
    )

    for child_layer in ("childBonesLayer1", "childBonesLayer2"):
        children = bone_data.get(child_layer, [])
        if not isinstance(children, list):
            bone_data[child_layer] = []
            continue
        bone_data[child_layer] = [
            _apply_euzebia_sprite_rotation_workaround(child, invert_direction=invert_direction)
            for child in children
            if isinstance(child, dict)
        ]

    return bone_data


def add_bones(bones, invert_sprite_rotation_direction=False):
    data = []
    for i in range(len(bones)):
        data.append(
            _apply_euzebia_sprite_rotation_workaround(
                bones[i].get_bone_dict(),
                invert_direction=invert_sprite_rotation_direction,
            )
        )
    return data


def _sanitize_identifier(value):
    cleaned = re.sub(r"[^0-9a-zA-Z_]", "_", str(value))
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "puppet"
    if cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    return cleaned


def _c_string(value):
    text = str(value)
    text = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def _c_float(value):
    try:
        numeric = float(value)
    except Exception:
        numeric = 0.0
    text = f"{numeric:.6f}".rstrip("0").rstrip(".")
    if text == "-0":
        text = "0"
    if "." not in text:
        text = f"{text}.0"
    return f"{text}f"


def _c_int(value):
    try:
        return int(round(float(value)))
    except Exception:
        return 0


def _c_uint(value):
    return max(0, _c_int(value))


def _c_base_sprite_angle(value, invert_direction=False):
    return _c_float(_euzebia_base_sprite_rotation(value, invert_direction=invert_direction))


def _c_sprite_index(value, offset=0):
    index = _c_int(value)
    if index < 0:
        return 255
    index += _c_int(offset)
    return max(0, min(255, index))


def _normalize_sprite_mirror_axis(value):
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


def _sprite_mirror_axis_bits(value):
    axis = _normalize_sprite_mirror_axis(value)
    bits = 0
    if "x" in axis:
        bits |= 1
    if "y" in axis:
        bits |= 2
    return bits


def _flatten_bones(
    bones,
    parent_index=-1,
    parent_layer=0,
    flattened=None,
    invert_sprite_rotation_direction=False,
):
    if flattened is None:
        flattened = []
    for bone in bones:
        index = len(flattened)
        flattened.append(
            {
                "label": bone.label,
                "x": bone.x,
                "y": bone.y,
                "angle": bone.angle,
                "spriteIndex": bone.spriteIndex,
                "baseSpriteRotation": _euzebia_base_sprite_rotation(
                    bone.baseSpriteRotation,
                    invert_direction=invert_sprite_rotation_direction,
                ),
                "spriteMirrorAxis": _normalize_sprite_mirror_axis(getattr(bone, "spriteMirrorAxis", "none")),
                "parentIndex": parent_index,
                "parentLayer": parent_layer,
            }
        )
        _flatten_bones(
            bone.childBonesLayer1,
            index,
            1,
            flattened,
            invert_sprite_rotation_direction=invert_sprite_rotation_direction,
        )
        _flatten_bones(
            bone.childBonesLayer2,
            index,
            2,
            flattened,
            invert_sprite_rotation_direction=invert_sprite_rotation_direction,
        )
    return flattened


def _normalize_keyframes(keyframes, legacy_duration=None):
    if not isinstance(keyframes, list):
        keyframes = []

    step = 1
    try:
        if legacy_duration is not None:
            step = max(1, int(legacy_duration))
    except Exception:
        step = 1

    dedup = {}
    for idx, item in enumerate(keyframes):
        if not isinstance(item, dict):
            continue
        timeline = item.get("timelineFrame")
        if timeline is None:
            timeline = item.get("timeline")
        if timeline is None:
            timeline = idx * step
        try:
            timeline = int(round(float(timeline)))
        except Exception:
            timeline = idx * step
        timeline = max(0, timeline)

        try:
            x = float(item.get("x", 0.0))
        except Exception:
            x = 0.0
        try:
            y = float(item.get("y", 0.0))
        except Exception:
            y = 0.0
        try:
            angle = float(item.get("angle", 0.0))
        except Exception:
            angle = 0.0

        dedup[timeline] = {
            "timelineFrame": timeline,
            "x": x,
            "y": y,
            "angle": angle,
            "label": str(item.get("label", "")),
        }

    ordered = [dedup[key] for key in sorted(dedup.keys())]
    for idx, keyframe in enumerate(ordered):
        keyframe["label"] = f"frame{idx + 1}"
    return ordered


def _build_baked_frames(keyframes):
    baked = []
    if not isinstance(keyframes, list) or len(keyframes) < 2:
        return baked

    ordered = [item for item in keyframes if isinstance(item, dict)]
    ordered.sort(key=lambda item: int(item.get("timelineFrame", 0)))
    if len(ordered) < 2:
        return baked

    for idx in range(len(ordered) - 1):
        start = ordered[idx]
        end = ordered[idx + 1]
        start_frame = int(start.get("timelineFrame", 0))
        end_frame = int(end.get("timelineFrame", 0))
        span = end_frame - start_frame
        if span <= 0:
            continue

        start_x = float(start.get("x", 0.0))
        start_y = float(start.get("y", 0.0))
        start_angle = float(start.get("angle", 0.0))
        end_x = float(end.get("x", start_x))
        end_y = float(end.get("y", start_y))
        end_angle = float(end.get("angle", start_angle))

        prev_x = start_x
        prev_y = start_y
        prev_angle = start_angle
        for step in range(1, span + 1):
            alpha = step / span
            x = start_x + (end_x - start_x) * alpha
            y = start_y + (end_y - start_y) * alpha
            angle = start_angle + (end_angle - start_angle) * alpha
            baked.append(
                {
                    "x": x - prev_x,
                    "y": y - prev_y,
                    "angle": round(angle - prev_angle, 4),
                }
            )
            prev_x = x
            prev_y = y
            prev_angle = angle

    return baked


def _merge_keyframes(existing, extra):
    merged = {}
    for item in existing + extra:
        if not isinstance(item, dict):
            continue
        timeline = int(item.get("timelineFrame", 0))
        merged[timeline] = item
    ordered = [merged[key] for key in sorted(merged.keys())]
    for idx, keyframe in enumerate(ordered):
        keyframe["label"] = f"frame{idx + 1}"
    return ordered


def _normalize_tracks(clip_source):
    track_map = {}

    def add_track(bone_label, keyframes, legacy_duration=None):
        normalized = _normalize_keyframes(keyframes, legacy_duration)
        if not normalized:
            return
        key = str(bone_label).strip()
        existing = track_map.get(key)
        if existing is None:
            track_map[key] = normalized
            return
        track_map[key] = _merge_keyframes(existing, normalized)

    if not isinstance(clip_source, dict):
        return []

    raw_tracks = clip_source.get("tracks")
    if isinstance(raw_tracks, list):
        for track in raw_tracks:
            if not isinstance(track, dict):
                continue
            add_track(
                track.get("boneLabel") or track.get("bone_label") or "",
                track.get("keyframes", []),
                track.get("duration"),
            )
    elif isinstance(raw_tracks, dict):
        for raw_label, track in raw_tracks.items():
            if isinstance(track, dict):
                add_track(raw_label, track.get("keyframes", []), track.get("duration"))
            else:
                add_track(raw_label, track)

    legacy_keyframes = clip_source.get("keyframes")
    if isinstance(legacy_keyframes, list):
        legacy_label = clip_source.get("boneLabel") or clip_source.get("bone_label") or ""
        add_track(legacy_label, legacy_keyframes, clip_source.get("duration"))

    tracks = []
    for bone_label in sorted(track_map.keys()):
        tracks.append({"boneLabel": bone_label, "keyframes": track_map[bone_label]})
    return tracks


def _normalize_animations(animations):
    payload = animations
    if isinstance(animations, dict) and isinstance(animations.get("animations"), list):
        payload = animations.get("animations")

    clips = []
    if isinstance(payload, list):
        iterable = payload
    elif isinstance(payload, dict):
        iterable = []
        for clip_name, clip_data in payload.items():
            if not isinstance(clip_data, dict):
                continue
            item = dict(clip_data)
            item.setdefault("animationName", str(clip_name))
            iterable.append(item)
    else:
        iterable = []

    for idx, clip in enumerate(iterable):
        if not isinstance(clip, dict):
            continue
        clip_name = str(clip.get("animationName", "")).strip()
        if not clip_name:
            clip_name = f"clip{idx + 1}"
        clips.append({"animationName": clip_name, "tracks": _normalize_tracks(clip)})
    return clips


def _bone_children(bone, layer):
    attr_name = "childBonesLayer1" if layer == 1 else "childBonesLayer2"
    value = getattr(bone, attr_name, [])
    return value if isinstance(value, list) else []


class _ExportRootBone:
    def __init__(self, puppet, child_bones):
        self.label = getattr(puppet, "label", "")
        self.x = getattr(puppet, "x", 0)
        self.y = getattr(puppet, "y", 0)
        self.angle = getattr(puppet, "angle", 0.0)
        self.spriteIndex = -1
        self.baseSpriteRotation = 0.0
        self.childBonesLayer1 = child_bones if isinstance(child_bones, list) else []
        self.childBonesLayer2 = []


def _bone_child_array_name(symbol_base, path, bone_index, layer):
    return f"{symbol_base}_{path}_{bone_index}_childPuppetBonesLayer{layer}"


def _register_bone_pointer_expressions(bones, symbol_base, array_name, path, label_map):
    for idx, bone in enumerate(bones):
        label = str(getattr(bone, "label", "") or "")
        if label and label not in label_map:
            label_map[label] = f"&{array_name}[{idx}]"

        layer1 = _bone_children(bone, 1)
        if layer1:
            _register_bone_pointer_expressions(
                layer1,
                symbol_base,
                _bone_child_array_name(symbol_base, path, idx, 1),
                f"{path}_{idx}_l1",
                label_map,
            )

        layer2 = _bone_children(bone, 2)
        if layer2:
            _register_bone_pointer_expressions(
                layer2,
                symbol_base,
                _bone_child_array_name(symbol_base, path, idx, 2),
                f"{path}_{idx}_l2",
                label_map,
            )


def _emit_bone_array(
    lines,
    symbol_base,
    array_name,
    bones,
    path,
    invert_sprite_rotation_direction=False,
    sprite_index_offset=0,
):
    for idx, bone in enumerate(bones):
        layer1 = _bone_children(bone, 1)
        if layer1:
            _emit_bone_array(
                lines,
                symbol_base,
                _bone_child_array_name(symbol_base, path, idx, 1),
                layer1,
                f"{path}_{idx}_l1",
                invert_sprite_rotation_direction=invert_sprite_rotation_direction,
                sprite_index_offset=sprite_index_offset,
            )

        layer2 = _bone_children(bone, 2)
        if layer2:
            _emit_bone_array(
                lines,
                symbol_base,
                _bone_child_array_name(symbol_base, path, idx, 2),
                layer2,
                f"{path}_{idx}_l2",
                invert_sprite_rotation_direction=invert_sprite_rotation_direction,
                sprite_index_offset=sprite_index_offset,
            )

    if not bones:
        return

    lines.append(f"static const RawPuppetBone {array_name}[] = {{")
    for idx, bone in enumerate(bones):
        layer1 = _bone_children(bone, 1)
        layer2 = _bone_children(bone, 2)
        layer1_array = _bone_child_array_name(symbol_base, path, idx, 1) if layer1 else "NULL"
        layer2_array = _bone_child_array_name(symbol_base, path, idx, 2) if layer2 else "NULL"

        lines.extend(
            [
                "    {",
                f"        .label = {_c_string(getattr(bone, 'label', ''))},",
                f"        .x = {_c_int(getattr(bone, 'x', 0))},",
                f"        .y = {_c_int(getattr(bone, 'y', 0))},",
                f"        .angle = {_c_float(getattr(bone, 'angle', 0.0))},",
                f"        .spriteIndex = {_c_sprite_index(getattr(bone, 'spriteIndex', -1), offset=sprite_index_offset)},",
                "        .baseSpriteAngle = "
                f"{_c_base_sprite_angle(getattr(bone, 'baseSpriteRotation', 0.0), invert_direction=invert_sprite_rotation_direction)},",
                f"        .childPuppetBonesLayer1 = {layer1_array},",
                f"        .childPuppetBonesNumLayer1 = {len(layer1)},",
                f"        .childPuppetBonesLayer2 = {layer2_array},",
                f"        .childPuppetBonesNumLayer2 = {len(layer2)},",
                "    },",
            ]
        )
    lines.append("};")
    lines.append("")


def _clip_symbol(symbol_base, clip_name, clip_index):
    cleaned = _sanitize_identifier(clip_name)
    if cleaned == "puppet":
        cleaned = f"clip{clip_index + 1}"
    return f"{symbol_base}_{cleaned}"


def _emit_clip_timelines(lines, symbol_base, clip, clip_index, bone_pointers, root_label):
    clip_base = _clip_symbol(symbol_base, clip.get("animationName", ""), clip_index)
    pair_entries = []

    for track_index, track in enumerate(clip.get("tracks", [])):
        bone_label = str(track.get("boneLabel", "") or "")
        keyframes = track.get("keyframes", [])
        if not bone_label or not keyframes:
            continue

        bone_expr = bone_pointers.get(bone_label)
        if bone_expr is None:
            lines.append(f"/* Skipped animation track for unknown bone: {_c_string(bone_label)}. */")
            continue

        frames_array_name = f"{clip_base}_track{track_index}_frames"
        animation_name = f"{clip_base}_track{track_index}_animation"
        lines.append(f"static const RawFrame {frames_array_name}[] = {{")
        for keyframe in keyframes:
            start_frame = _c_uint(keyframe.get("timelineFrame", 0))
            lines.append(
                f"    {{.x = {_c_int(keyframe.get('x', 0))}, .y = {_c_int(keyframe.get('y', 0))}, "
                f".angle = {_c_float(keyframe.get('angle', 0.0))}, .startFrameNum = {start_frame}}},"
            )
        lines.append("};")
        lines.append("")

        lines.append(f"static const RawAnimation {animation_name} = {{")
        lines.append(f"    .frames = {frames_array_name},")
        lines.append(f"    .framesNum = {len(keyframes)},")
        lines.append("};")
        lines.append("")

        pair_entries.append((animation_name, bone_expr, bone_label))

    pairs_array_name = "NULL"
    if pair_entries:
        pairs_array_name = f"{clip_base}_boneAnimationPairs"
        lines.append(f"static const RawBoneAnimationPair {pairs_array_name}[] = {{")
        for animation_name, bone_expr, bone_label in pair_entries:
            root_comment = " /* root bone */" if bone_label == root_label else ""
            lines.append(f"    {{.rawBone = {bone_expr}, .rawAnimation = &{animation_name}}},{root_comment}")
        lines.append("};")
        lines.append("")

    return {
        "clipBase": clip_base,
        "pairsArrayName": pairs_array_name,
        "pairsCount": len(pair_entries),
    }


def _emit_puppet_instance(lines, symbol_name, puppet, puppet_bones_array, puppet_bones_num, clip_entry):
    lines.append(f"const RawPuppet {symbol_name} = {{")
    lines.append(f"    .label = {_c_string(getattr(puppet, 'label', ''))},")
    lines.append("    .x = 0,")
    lines.append("    .y = 0,")
    lines.append("    .angle = 0.0f,")
    lines.append(f"    .puppetBones = {puppet_bones_array},")
    lines.append(f"    .puppetBonesNum = {puppet_bones_num},")
    lines.append(f"    .boneAnimationPairs = {clip_entry['pairsArrayName']},")
    lines.append(f"    .boneAnimationPairsNum = {clip_entry['pairsCount']},")
    lines.append("};")
    lines.append("")


def save_puppet(puppet, filename_base, animations=None):
    puppet_path = f"{filename_base}.json"
    backup_path = f"{filename_base}_backup.json"
    invert_sprite_rotation_direction = _puppet_inverts_sprite_rotation_direction(puppet)

    if os.path.exists(puppet_path):
        if os.path.exists(backup_path):
            os.remove(backup_path)
        os.replace(puppet_path, backup_path)

    with open(puppet_path, "w") as f:
        data = puppet.get_puppet_dict()
        data["bones"] = add_bones(
            puppet.bones,
            invert_sprite_rotation_direction=invert_sprite_rotation_direction,
        )
        if animations is not None:
            data["animations"] = animations
        json.dump(data, f, indent=4, ensure_ascii=False)


def save_settings(settings, settings_path="settings.json"):
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)


def _write_text_overwrite(output_path, text):
    output_dir = os.path.dirname(os.path.abspath(output_path)) or "."
    output_name = os.path.basename(output_path)
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            dir=output_dir,
            prefix=f".{output_name}.",
            suffix=".tmp",
        ) as f:
            temp_path = f.name
            f.write(text)
        os.replace(temp_path, output_path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def export_cpuppet(puppet, filename_base, animations=None, sprites_path=None, sprite_index_offset=0):
    output_path = f"{filename_base}.c"
    symbol_base = _sanitize_identifier(os.path.basename(str(filename_base)) or getattr(puppet, "label", "puppet"))
    invert_sprite_rotation_direction = _puppet_inverts_sprite_rotation_direction(puppet)
    sprite_index_offset = _c_int(sprite_index_offset)

    puppet_label = str(getattr(puppet, "label", ""))
    puppet_bones = getattr(puppet, "bones", [])
    if not isinstance(puppet_bones, list):
        puppet_bones = []
    exported_root_bone = _ExportRootBone(puppet, puppet_bones)
    exported_puppet_bones = [exported_root_bone]
    clips = _normalize_animations(animations)[:1]
    puppet_bones_array = f"{symbol_base}_puppetBones"

    bone_pointers = {}
    _register_bone_pointer_expressions(
        exported_puppet_bones,
        symbol_base,
        puppet_bones_array,
        "root",
        bone_pointers,
    )

    lines = [
        "/* Auto-generated by Puppet Craft. */",
        "/* Export format: RawPuppet, RawPuppetBone, RawAnimation and RawBoneAnimationPair. */",
        "/* RawPuppet.puppetBones[0] is the exported root bone; RawPuppet x/y/angle are neutral. */",
        "/* baseSpriteAngle is exported in radians. */",
        "/* Sprite base rotation direction is inverted when puppetMirrorAxis is x or y. */",
        "/* spriteIndex 255 means no sprite, converted from Puppet Craft's -1 sentinel. */",
        f"/* Exported spriteIndex values include sprite_index_offset = {sprite_index_offset}. */",
        "/* spriteMirrorAxis is stored in JSON but is not represented by the RawPuppetBone struct. */",
        "#include <stddef.h>",
        "#include <stdint.h>",
        "",
        "typedef struct",
        "{",
        "    const int x;",
        "    const int y;",
        "    const float angle;",
        "    const int startFrameNum;",
        "} RawFrame;",
        "",
        "typedef struct",
        "{",
        "    const RawFrame *frames;",
        "    const uint16_t framesNum;",
        "} RawAnimation;",
        "",
        "typedef struct RawPuppetBone RawPuppetBone;",
        "",
        "typedef struct RawPuppetBone",
        "{",
        "    const char *label;",
        "    const int16_t x;",
        "    const int16_t y;",
        "    const float angle;",
        "    const uint8_t spriteIndex;",
        "    const float baseSpriteAngle;",
        "    const RawPuppetBone *childPuppetBonesLayer1;",
        "    const uint8_t childPuppetBonesNumLayer1;",
        "    const RawPuppetBone *childPuppetBonesLayer2;",
        "    const uint8_t childPuppetBonesNumLayer2;",
        "} RawPuppetBone;",
        "",
        "typedef struct",
        "{",
        "    const RawPuppetBone *rawBone;",
        "    const RawAnimation *rawAnimation;",
        "} RawBoneAnimationPair;",
        "",
        "typedef struct",
        "{",
        "    const char *label;",
        "    const int16_t x;",
        "    const int16_t y;",
        "    const float angle;",
        "    const RawPuppetBone *puppetBones;",
        "    const uint8_t puppetBonesNum;",
        "    const RawBoneAnimationPair *boneAnimationPairs;",
        "    const uint8_t boneAnimationPairsNum;",
        "} RawPuppet;",
        "",
    ]

    _emit_bone_array(
        lines,
        symbol_base,
        puppet_bones_array,
        exported_puppet_bones,
        "root",
        invert_sprite_rotation_direction=invert_sprite_rotation_direction,
        sprite_index_offset=sprite_index_offset,
    )

    clip_entries = []
    for clip_index, clip in enumerate(clips):
        clip_entries.append(_emit_clip_timelines(lines, symbol_base, clip, clip_index, bone_pointers, puppet_label))

    empty_clip_entry = {
        "pairsArrayName": "NULL",
        "pairsCount": 0,
    }
    default_clip_entry = clip_entries[0] if clip_entries else empty_clip_entry

    _emit_puppet_instance(
        lines,
        symbol_base,
        puppet,
        puppet_bones_array,
        len(exported_puppet_bones),
        default_clip_entry,
    )

    _write_text_overwrite(output_path, "\n".join(lines) + "\n")


def save_to_file(puppet, settings, filename, animations=None, sprites_path=None):
    # Backward-compatible wrapper for older call sites.
    save_puppet(puppet, filename, animations=animations)
    save_settings(settings)
    export_cpuppet(
        puppet,
        filename,
        animations=animations,
        sprites_path=sprites_path,
        sprite_index_offset=settings.get("spriteExportIndexOffset", 0),
    )
