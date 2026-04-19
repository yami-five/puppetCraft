import json
import os
import re


def add_bones(bones):
    data = []
    for i in range(len(bones)):
        data.append(bones[i].get_bone_dict())
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


def _flatten_bones(bones, parent_index=-1, parent_layer=0, flattened=None):
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
                "baseSpriteRotation": bone.baseSpriteRotation,
                "parentIndex": parent_index,
                "parentLayer": parent_layer,
            }
        )
        _flatten_bones(bone.childBonesLayer1, index, 1, flattened)
        _flatten_bones(bone.childBonesLayer2, index, 2, flattened)
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


def save_puppet(puppet, filename_base, animations=None):
    puppet_path = f"{filename_base}.json"
    backup_path = f"{filename_base}_backup.json"

    if os.path.exists(puppet_path):
        if os.path.exists(backup_path):
            os.remove(backup_path)
        os.replace(puppet_path, backup_path)

    with open(puppet_path, "w") as f:
        data = puppet.get_puppet_dict()
        data["bones"] = add_bones(puppet.bones)
        if animations is not None:
            data["animations"] = animations
        json.dump(data, f, indent=4, ensure_ascii=False)


def save_settings(settings, settings_path="settings.json"):
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)


def export_cpuppet(puppet, filename_base, animations=None, sprites_path=None):
    output_path = f"{filename_base}.c"
    symbol_base = _sanitize_identifier(os.path.basename(str(filename_base)) or getattr(puppet, "label", "puppet"))

    puppet_label = str(getattr(puppet, "label", ""))
    if sprites_path is None:
        sprites_path = f"sprites_{puppet_label.replace('Root', '')}"

    bones = _flatten_bones(getattr(puppet, "bones", []))
    clips = _normalize_animations(animations)

    lines = [
        "/* Auto-generated by Puppet Craft. */",
        "/* parentLayer: 0=root bone, 1=childBonesLayer1, 2=childBonesLayer2 */",
        "#include <stddef.h>",
        "",
        "typedef struct {",
        "    const char *label;",
        "    float x;",
        "    float y;",
        "    float angle;",
        "    int spriteIndex;",
        "    float baseSpriteRotation;",
        "    int parentIndex;",
        "    int parentLayer;",
        "} PuppetCraftBone;",
        "",
        "typedef struct {",
        "    float x;",
        "    float y;",
        "    float angle;",
        "    int timelineFrame;",
        "    const char *label;",
        "} PuppetCraftKeyframe;",
        "",
        "typedef struct {",
        "    float x;",
        "    float y;",
        "    float angle;",
        "} PuppetCraftDeltaFrame;",
        "",
        "typedef struct {",
        "    const char *boneLabel;",
        "    const PuppetCraftKeyframe *keyframes;",
        "    int keyframeCount;",
        "    const PuppetCraftDeltaFrame *bakedFrames;",
        "    int bakedFrameCount;",
        "    int timelineStart;",
        "    int timelineEnd;",
        "} PuppetCraftTrack;",
        "",
        "typedef struct {",
        "    const char *animationName;",
        "    const PuppetCraftTrack *tracks;",
        "    int trackCount;",
        "} PuppetCraftAnimation;",
        "",
        "typedef struct {",
        "    const char *label;",
        "    const char *spritesPath;",
        "    float x;",
        "    float y;",
        "    float angle;",
        "    const PuppetCraftBone *bones;",
        "    int boneCount;",
        "    const PuppetCraftAnimation *animations;",
        "    int animationCount;",
        "} PuppetCraftExport;",
        "",
    ]

    bone_array_name = f"{symbol_base}_bones"
    if bones:
        lines.append(f"static const PuppetCraftBone {bone_array_name}[] = {{")
        for bone in bones:
            lines.append(
                f"    {{{_c_string(bone['label'])}, {_c_float(bone['x'])}, {_c_float(bone['y'])}, {_c_float(bone['angle'])}, "
                f"{int(bone['spriteIndex'])}, {_c_float(bone['baseSpriteRotation'])}, {int(bone['parentIndex'])}, {int(bone['parentLayer'])}}},"
            )
        lines.append("};")
        lines.append("")

    clip_entries = []
    for clip_index, clip in enumerate(clips):
        tracks = clip.get("tracks", [])
        track_entries = []
        for track_index, track in enumerate(tracks):
            keyframes = track.get("keyframes", [])
            if not keyframes:
                continue
            timeline_start = int(keyframes[0].get("timelineFrame", 0))
            timeline_end = int(keyframes[-1].get("timelineFrame", timeline_start))
            keyframe_array_name = f"{symbol_base}_clip{clip_index}_track{track_index}_keyframes"
            lines.append(f"static const PuppetCraftKeyframe {keyframe_array_name}[] = {{")
            for keyframe in keyframes:
                lines.append(
                    f"    {{{_c_float(keyframe.get('x', 0.0))}, {_c_float(keyframe.get('y', 0.0))}, {_c_float(keyframe.get('angle', 0.0))}, "
                    f"{int(keyframe.get('timelineFrame', 0))}, {_c_string(keyframe.get('label', ''))}}},"
                )
            lines.append("};")
            lines.append("")

            baked_frames = _build_baked_frames(keyframes)
            baked_array_name = "NULL"
            if baked_frames:
                baked_array_name = f"{symbol_base}_clip{clip_index}_track{track_index}_baked_frames"
                lines.append(f"static const PuppetCraftDeltaFrame {baked_array_name}[] = {{")
                for frame in baked_frames:
                    lines.append(
                        f"    {{{_c_float(frame.get('x', 0.0))}, {_c_float(frame.get('y', 0.0))}, {_c_float(frame.get('angle', 0.0))}}},"
                    )
                lines.append("};")
                lines.append("")

            track_entries.append(
                {
                    "boneLabel": track.get("boneLabel", ""),
                    "arrayName": keyframe_array_name,
                    "count": len(keyframes),
                    "bakedArrayName": baked_array_name,
                    "bakedCount": len(baked_frames),
                    "timelineStart": timeline_start,
                    "timelineEnd": timeline_end,
                }
            )

        tracks_array_name = f"{symbol_base}_clip{clip_index}_tracks"
        if track_entries:
            lines.append(f"static const PuppetCraftTrack {tracks_array_name}[] = {{")
            for track_entry in track_entries:
                lines.append(
                    f"    {{{_c_string(track_entry['boneLabel'])}, {track_entry['arrayName']}, {track_entry['count']}, "
                    f"{track_entry['bakedArrayName']}, {track_entry['bakedCount']}, {track_entry['timelineStart']}, {track_entry['timelineEnd']}}},"
                )
            lines.append("};")
            lines.append("")
            clip_entries.append(
                {
                    "animationName": clip.get("animationName", ""),
                    "tracksArrayName": tracks_array_name,
                    "trackCount": len(track_entries),
                }
            )
        else:
            clip_entries.append(
                {
                    "animationName": clip.get("animationName", ""),
                    "tracksArrayName": "NULL",
                    "trackCount": 0,
                }
            )

    clips_array_name = f"{symbol_base}_animations"
    if clip_entries:
        lines.append(f"static const PuppetCraftAnimation {clips_array_name}[] = {{")
        for clip_entry in clip_entries:
            lines.append(
                f"    {{{_c_string(clip_entry['animationName'])}, {clip_entry['tracksArrayName']}, {clip_entry['trackCount']}}},"
            )
        lines.append("};")
        lines.append("")

    lines.append(f"const PuppetCraftExport {symbol_base}_export = {{")
    lines.append(f"    {_c_string(puppet_label)},")
    lines.append(f"    {_c_string(sprites_path)},")
    lines.append(f"    {_c_float(getattr(puppet, 'x', 0.0))},")
    lines.append(f"    {_c_float(getattr(puppet, 'y', 0.0))},")
    lines.append(f"    {_c_float(getattr(puppet, 'angle', 0.0))},")
    lines.append(f"    {bone_array_name if bones else 'NULL'},")
    lines.append(f"    {len(bones)},")
    lines.append(f"    {clips_array_name if clip_entries else 'NULL'},")
    lines.append(f"    {len(clip_entries)},")
    lines.append("};")

    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")


def save_to_file(puppet, settings, filename, animations=None, sprites_path=None):
    # Backward-compatible wrapper for older call sites.
    save_puppet(puppet, filename, animations=animations)
    save_settings(settings)
    export_cpuppet(puppet, filename, animations=animations, sprites_path=sprites_path)
