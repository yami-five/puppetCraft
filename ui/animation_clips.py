def deserialize_animation_clips(source):
    clips = {}
    payload = source
    if isinstance(source, dict) and isinstance(source.get("animations"), list):
        payload = source.get("animations")

    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            clip_name = str(item.get("animationName", "")).strip()
            if not clip_name:
                continue
            clips[clip_name] = normalize_clip_data(item)
        return clips

    if isinstance(payload, dict):
        for clip_name, clip_data in payload.items():
            if not isinstance(clip_data, dict):
                continue
            clips[str(clip_name)] = normalize_clip_data(clip_data)
    return clips


def serialize_animation_clips(animation_clips):
    animations = []
    for clip_name in sorted(animation_clips.keys()):
        clip = animation_clips.get(clip_name, {})
        tracks = clip_tracks(clip)
        serialized_tracks = []
        for bone_label in sorted(tracks.keys()):
            keyframes = tracks.get(bone_label, [])
            serialized_tracks.append(
                {
                    "boneLabel": bone_label,
                    "keyframes": keyframes,
                }
            )

        item = {"animationName": clip_name, "tracks": serialized_tracks}
        if len(serialized_tracks) == 1:
            item["boneLabel"] = serialized_tracks[0]["boneLabel"]
            item["keyframes"] = serialized_tracks[0]["keyframes"]
        animations.append(item)
    return animations


def normalize_clip_data(source):
    clip = {"tracks": {}}
    if not isinstance(source, dict):
        return clip

    tracks = clip["tracks"]
    raw_tracks = source.get("tracks")

    if isinstance(raw_tracks, list):
        for track_item in raw_tracks:
            if not isinstance(track_item, dict):
                continue
            bone_label = str(track_item.get("boneLabel") or track_item.get("bone_label") or "").strip()
            tracks[bone_label] = normalize_clip_keyframes(
                track_item.get("keyframes", []),
                track_item.get("duration"),
            )
    elif isinstance(raw_tracks, dict):
        for raw_bone_label, track_item in raw_tracks.items():
            bone_label = str(raw_bone_label).strip()
            if isinstance(track_item, dict):
                keyframes_source = track_item.get("keyframes", [])
                duration_source = track_item.get("duration")
            else:
                keyframes_source = track_item
                duration_source = None
            tracks[bone_label] = normalize_clip_keyframes(keyframes_source, duration_source)

    legacy_keyframes = source.get("keyframes")
    legacy_bone_label = str(source.get("boneLabel") or source.get("bone_label") or "").strip()
    if isinstance(legacy_keyframes, list):
        merged = list(tracks.get(legacy_bone_label, []))
        merged.extend(normalize_clip_keyframes(legacy_keyframes, source.get("duration")))
        tracks[legacy_bone_label] = normalize_clip_keyframes(merged)
    return clip


def clip_tracks(clip):
    if not isinstance(clip, dict):
        return {}
    tracks = clip.get("tracks")
    if isinstance(tracks, dict):
        return tracks
    tracks = {}
    clip["tracks"] = tracks
    return tracks


def clip_timeline_values(clip):
    values = []
    tracks = clip_tracks(clip)
    for keyframes in tracks.values():
        if not isinstance(keyframes, list):
            continue
        for keyframe in keyframes:
            try:
                values.append(int(keyframe.get("timelineFrame", 0)))
            except Exception:
                continue
    return values


def clip_timeline_bounds(clip):
    values = clip_timeline_values(clip)
    if not values:
        return None, None
    return min(values), max(values)


def keyframes_timeline_bounds(keyframes):
    if not isinstance(keyframes, list) or not keyframes:
        return None, None
    values = []
    for keyframe in keyframes:
        try:
            values.append(int(keyframe.get("timelineFrame", 0)))
        except Exception:
            continue
    if not values:
        return None, None
    return min(values), max(values)


def interpolate_absolute_poses(keyframes):
    ordered = normalize_clip_keyframes(keyframes)
    if not ordered:
        return []
    if len(ordered) == 1:
        only = ordered[0]
        return [{"x": float(only.get("x", 0.0)), "y": float(only.get("y", 0.0)), "angle": float(only.get("angle", 0.0))}]

    poses = [{"x": float(ordered[0]["x"]), "y": float(ordered[0]["y"]), "angle": float(ordered[0]["angle"])}]
    for idx in range(len(ordered) - 1):
        start = ordered[idx]
        end = ordered[idx + 1]
        start_frame = int(start.get("timelineFrame", 0))
        end_frame = int(end.get("timelineFrame", 0))
        span = end_frame - start_frame
        if span <= 0:
            continue
        for step in range(1, span + 1):
            alpha = step / span
            poses.append(
                {
                    "x": float(start["x"]) + (float(end["x"]) - float(start["x"])) * alpha,
                    "y": float(start["y"]) + (float(end["y"]) - float(start["y"])) * alpha,
                    "angle": float(start["angle"]) + (float(end["angle"]) - float(start["angle"])) * alpha,
                }
            )
    return poses


def normalize_clip_keyframes(keyframes, legacy_duration=None):
    if not isinstance(keyframes, list):
        keyframes = []

    step = 1
    try:
        if legacy_duration is not None:
            step = max(1, int(legacy_duration))
    except Exception:
        step = 1

    normalized = []
    for idx, raw in enumerate(keyframes):
        if not isinstance(raw, dict):
            continue
        timeline_frame = raw.get("timelineFrame")
        if timeline_frame is None:
            timeline_frame = raw.get("timeline")
        if timeline_frame is None:
            timeline_frame = idx * step
        try:
            timeline_frame = int(round(float(timeline_frame)))
        except Exception:
            timeline_frame = idx * step

        try:
            x = float(raw.get("x", 0.0))
        except Exception:
            x = 0.0
        try:
            y = float(raw.get("y", 0.0))
        except Exception:
            y = 0.0
        try:
            angle = float(raw.get("angle", 0.0))
        except Exception:
            angle = 0.0

        normalized.append(
            {
                "x": x,
                "y": y,
                "angle": angle,
                "label": str(raw.get("label", f"frame{idx + 1}")),
                "timelineFrame": max(0, timeline_frame),
            }
        )

    dedup = {}
    for item in normalized:
        dedup[item["timelineFrame"]] = item
    ordered = [dedup[frame] for frame in sorted(dedup.keys())]
    renumber_keyframes(ordered)
    return ordered


def renumber_keyframes(keyframes):
    for idx, item in enumerate(keyframes):
        item["label"] = f"frame{idx + 1}"
