import json


class keyFrame:
    def __init__(self, x, y, angle, label, timeline_frame=0):
        self.x = x
        self.y = y
        self.angle = angle
        self.label = label
        self.timeline_frame = int(timeline_frame)


class animation:
    def __init__(self, keyFrames, label):
        self.keyFrames = sorted(keyFrames, key=lambda kf: kf.timeline_frame)
        self.label = label
        self.frames = []
        self.timeline_start = self.keyFrames[0].timeline_frame if self.keyFrames else 0
        self.timeline_end = self.keyFrames[-1].timeline_frame if self.keyFrames else 0

    def calc_frames(self):
        self.frames = []
        if len(self.keyFrames) < 2:
            return
        for idx in range(len(self.keyFrames) - 1):
            start = self.keyFrames[idx]
            end = self.keyFrames[idx + 1]
            span = end.timeline_frame - start.timeline_frame
            if span <= 0:
                continue
            prev_x = float(start.x)
            prev_y = float(start.y)
            prev_angle = float(start.angle)
            for step in range(1, span + 1):
                alpha = step / span
                x = float(start.x) + (float(end.x) - float(start.x)) * alpha
                y = float(start.y) + (float(end.y) - float(start.y)) * alpha
                angle = float(start.angle) + (float(end.angle) - float(start.angle)) * alpha
                self.frames.append(
                    {
                        "x": x - prev_x,
                        "y": y - prev_y,
                        "angle": round(angle - prev_angle, 4),
                    }
                )
                prev_x = x
                prev_y = y
                prev_angle = angle

    def to_absolute_poses(self):
        if not self.keyFrames:
            return []
        if len(self.keyFrames) == 1:
            only = self.keyFrames[0]
            return [{"x": float(only.x), "y": float(only.y), "angle": float(only.angle)}]
        if not self.frames:
            self.calc_frames()
        x = float(self.keyFrames[0].x)
        y = float(self.keyFrames[0].y)
        angle = float(self.keyFrames[0].angle)
        poses = [{"x": x, "y": y, "angle": angle}]
        for frame in self.frames:
            x += frame["x"]
            y += frame["y"]
            angle += frame["angle"]
            poses.append({"x": x, "y": y, "angle": angle})
        return poses


def _resolve_timeline_frame(item, index, default_segment_frames=None):
    timeline_frame = item.get("timelineFrame")
    if timeline_frame is None:
        timeline_frame = item.get("timeline")
    if timeline_frame is not None:
        return int(round(float(timeline_frame)))
    if default_segment_frames is not None:
        return int(index * int(default_segment_frames))
    return int(index)


def build_animation(clip_name, keyframes_dicts, default_segment_frames=None):
    keyed_frames = {}
    for idx, item in enumerate(keyframes_dicts):
        if not isinstance(item, dict):
            continue
        timeline_frame = _resolve_timeline_frame(item, idx, default_segment_frames)
        keyed_frames[timeline_frame] = item

    keyframes = []
    for idx, timeline_frame in enumerate(sorted(keyed_frames.keys())):
        item = keyed_frames[timeline_frame]
        label = item.get("label", f"frame{idx + 1}")
        keyframes.append(
            keyFrame(
                item["x"],
                item["y"],
                item["angle"],
                label,
                timeline_frame=timeline_frame,
            )
        )
    clip = animation(keyframes, clip_name)
    clip.calc_frames()
    return clip


def clip_to_dict(clip):
    return {
        "animationName": clip.label,
        "keyframes": [
            {
                "x": kf.x,
                "y": kf.y,
                "angle": kf.angle,
                "label": kf.label,
                "timelineFrame": kf.timeline_frame,
            }
            for kf in clip.keyFrames
        ],
    }


def save_clips_json(path, clips):
    payload = {"animations": [clip_to_dict(clip) for clip in clips]}
    with open(path, "w") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)


def load_clips_json(path):
    with open(path, "r") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {"animations": data}
    return {"animations": []}
