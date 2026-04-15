import json
import os
import re

from PySide6 import QtCore, QtGui, QtWidgets

import animation as animation_lib
import puppet
import puppetExporter
import puppetImporter
from app_constants import DEFAULT_CANVAS_HEIGHT, DEFAULT_CANVAS_WIDTH, DEFAULT_SETTINGS
from ui.graphics import PuppetItem, PuppetScene
from ui.view import KeyframeTimelineSlider, PuppetView


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = self._load_settings()
        self.puppet = None
        self.puppet_file_path = ""
        self.puppet_file_base = ""
        self.bones = []
        self.active_bone = None
        self.canvas_width, self.canvas_height = DEFAULT_CANVAS_WIDTH, DEFAULT_CANVAS_HEIGHT
        self.canvas_pan_x = 0.0
        self.canvas_pan_y = 0.0

        self.scene = PuppetScene(self.canvas_width, self.canvas_height, self)
        self.canvas_bg_item = self.scene.addRect(
            QtCore.QRectF(0, 0, self.canvas_width, self.canvas_height),
            QtCore.Qt.NoPen,
            QtGui.QBrush(QtGui.QColor(0, 0, 0)),
        )
        self.canvas_bg_item.setZValue(-90)
        self.border_item = self.scene.addRect(
            QtCore.QRectF(0, 0, self.canvas_width, self.canvas_height).adjusted(0.5, 0.5, -0.5, -0.5),
            QtGui.QPen(QtGui.QColor(255, 255, 255)),
            QtCore.Qt.NoBrush,
        )
        self.border_item.setZValue(-10)
        self.shade_item = QtWidgets.QGraphicsPathItem()
        self.shade_item.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 120)))
        self.shade_item.setPen(QtCore.Qt.NoPen)
        self.shade_item.setZValue(10)
        self.scene.addItem(self.shade_item)
        self.puppet_item = PuppetItem(self.puppet, self.settings)
        self.scene.addItem(self.puppet_item)

        self.view = PuppetView(self.scene, self.puppet_item)
        self.view.setSceneRect(0, 0, self.canvas_width, self.canvas_height)
        self.view.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.view.layoutChanged.connect(self._layout_scene)
        self.view.moveRequested.connect(self._move_bone)
        self.view.rotateRequested.connect(self._rotate_bone)
        self.view.panRequested.connect(self._pan_canvas)

        self.bone_list = QtWidgets.QListWidget()
        self._populate_bone_list()
        self.bone_list.currentItemChanged.connect(self._on_bone_selected)

        self.coords_label = QtWidgets.QLabel("x: 0, y: 0, angle: 0.0")

        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(["Edit Mode", "Animation Mode"])
        self.mode_combo.setCurrentIndex(0)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        self.animation_clips = {}
        self.playback_clip_name = ""
        self.playback_poses = []
        self.playback_frame_index = 0
        self.playback_timeline_start = 0
        self._pending_timeline_frame = None
        self._ignore_timeline_slider_change = False
        self.playback_timer = QtCore.QTimer(self)
        self.playback_timer.setInterval(33)
        self.playback_timer.timeout.connect(self._on_playback_tick)

        self.animation_editor = self._create_animation_editor()
        self.play_timeline_bar = self._create_play_timeline_bar()

        self._setup_toolbar()

        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.addWidget(QtWidgets.QLabel("Bones"))
        right_layout.addWidget(self.bone_list)
        right_layout.addWidget(self.coords_label)
        right_layout.addWidget(self.mode_combo)
        right_layout.addWidget(self.animation_editor)
        right_layout.addStretch(1)

        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.addWidget(self.view, 1)
        left_layout.addWidget(self.play_timeline_bar)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(central)
        layout.addWidget(left_panel, 1)
        layout.addWidget(right_panel)

        self.setCentralWidget(central)
        self.setWindowTitle("Puppet Craft")
        self.resize(1280, 720)

        self._setup_shortcuts()
        self._refresh_coords()
        QtCore.QTimer.singleShot(0, self._layout_scene)
        self._update_window_title()
        self._refresh_timeline_clips()
        self._update_animation_editor_state()
        self._on_mode_changed(self.mode_combo.currentIndex())

    def _create_animation_editor(self):
        group = QtWidgets.QGroupBox("Animation")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        existing_row = QtWidgets.QHBoxLayout()
        existing_row.addWidget(QtWidgets.QLabel("Existing"))
        self.anim_existing_clip_combo = QtWidgets.QComboBox()
        self.anim_existing_clip_combo.currentIndexChanged.connect(self._on_existing_clip_selected)
        existing_row.addWidget(self.anim_existing_clip_combo, 1)
        self.anim_rename_clip_button = QtWidgets.QPushButton("Rename Clip")
        self.anim_rename_clip_button.clicked.connect(self._rename_animation_clip)
        existing_row.addWidget(self.anim_rename_clip_button)
        layout.addLayout(existing_row)

        clip_row = QtWidgets.QHBoxLayout()
        clip_row.addWidget(QtWidgets.QLabel("Clip"))
        self.anim_clip_name_edit = QtWidgets.QLineEdit("clip1")
        self.anim_clip_name_edit.textChanged.connect(self._update_animation_editor_state)
        clip_row.addWidget(self.anim_clip_name_edit, 1)
        layout.addLayout(clip_row)

        timeline_row = QtWidgets.QHBoxLayout()
        timeline_row.addWidget(QtWidgets.QLabel("Timeline Frame"))
        self.anim_timeline_spin = QtWidgets.QSpinBox()
        self.anim_timeline_spin.setRange(0, 100000)
        self.anim_timeline_spin.setValue(0)
        self.anim_timeline_spin.valueChanged.connect(self._update_animation_editor_state)
        timeline_row.addWidget(self.anim_timeline_spin)
        layout.addLayout(timeline_row)

        bone_row = QtWidgets.QHBoxLayout()
        bone_row.addWidget(QtWidgets.QLabel("Assigned Bone"))
        self.anim_assigned_bone_label = QtWidgets.QLabel("-")
        self.anim_assigned_bone_label.setMinimumWidth(120)
        bone_row.addWidget(self.anim_assigned_bone_label, 1)
        self.anim_assign_bone_button = QtWidgets.QPushButton("Assign Selected Bone")
        self.anim_assign_bone_button.clicked.connect(self._assign_animation_clip_bone)
        bone_row.addWidget(self.anim_assign_bone_button)
        layout.addLayout(bone_row)

        self.anim_clip_info_label = QtWidgets.QLabel("No clip")
        layout.addWidget(self.anim_clip_info_label)

        buttons_row1 = QtWidgets.QHBoxLayout()
        self.anim_add_keyframe_button = QtWidgets.QPushButton("Add Keyframe")
        self.anim_add_keyframe_button.clicked.connect(self._add_animation_keyframe)
        buttons_row1.addWidget(self.anim_add_keyframe_button)
        self.anim_remove_keyframe_button = QtWidgets.QPushButton("Remove Frame")
        self.anim_remove_keyframe_button.clicked.connect(self._remove_animation_keyframe)
        buttons_row1.addWidget(self.anim_remove_keyframe_button)
        layout.addLayout(buttons_row1)

        buttons_row2 = QtWidgets.QHBoxLayout()
        self.anim_clear_clip_button = QtWidgets.QPushButton("Clear Clip")
        self.anim_clear_clip_button.clicked.connect(self._clear_animation_clip)
        buttons_row2.addWidget(self.anim_clear_clip_button)
        self.anim_save_clips_button = QtWidgets.QPushButton("Save Clips")
        self.anim_save_clips_button.clicked.connect(self._save_animation_clips)
        buttons_row2.addWidget(self.anim_save_clips_button)
        layout.addLayout(buttons_row2)

        return group

    def _create_play_timeline_bar(self):
        bar = QtWidgets.QFrame()
        bar.setObjectName("playTimelineBar")
        bar.setFrameShape(QtWidgets.QFrame.StyledPanel)
        bar.setMinimumHeight(96)

        layout = QtWidgets.QVBoxLayout(bar)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        top_row = QtWidgets.QHBoxLayout()
        top_row.addWidget(QtWidgets.QLabel("Timeline"))
        self.timeline_clip_combo = QtWidgets.QComboBox()
        self.timeline_clip_combo.currentIndexChanged.connect(self._on_timeline_clip_changed)
        top_row.addWidget(self.timeline_clip_combo, 1)
        self.timeline_play_button = QtWidgets.QPushButton("Play")
        self.timeline_play_button.clicked.connect(self._toggle_playback)
        top_row.addWidget(self.timeline_play_button)
        layout.addLayout(top_row)

        bottom_row = QtWidgets.QHBoxLayout()
        self.timeline_slider = KeyframeTimelineSlider(QtCore.Qt.Horizontal)
        self.timeline_slider.setRange(0, 0)
        self.timeline_slider.setEnabled(False)
        self.timeline_slider.valueChanged.connect(self._on_timeline_slider_changed)
        bottom_row.addWidget(self.timeline_slider, 1)
        self.timeline_frame_label = QtWidgets.QLabel("0/0")
        bottom_row.addWidget(self.timeline_frame_label)
        layout.addLayout(bottom_row)

        bar.hide()
        return bar

    def _on_mode_changed(self, index):
        mode = self.mode_combo.itemText(index)
        is_animation_mode = mode == "Animation Mode"
        self.animation_editor.setVisible(is_animation_mode)
        self.play_timeline_bar.setVisible(is_animation_mode)
        if is_animation_mode:
            self._refresh_timeline_clips()
        else:
            self._stop_playback()
        self._layout_scene()

    def _deserialize_animation_clips(self, source):
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
                clip = {
                    "keyframes": self._normalize_clip_keyframes(item.get("keyframes", []), item.get("duration")),
                }
                bone_label = item.get("boneLabel") or item.get("bone_label")
                if bone_label:
                    clip["boneLabel"] = str(bone_label)
                clips[clip_name] = clip
            return clips

        if isinstance(payload, dict):
            for clip_name, clip_data in payload.items():
                if not isinstance(clip_data, dict):
                    continue
                clip = {
                    "keyframes": self._normalize_clip_keyframes(clip_data.get("keyframes", []), clip_data.get("duration")),
                }
                bone_label = clip_data.get("boneLabel") or clip_data.get("bone_label")
                if bone_label:
                    clip["boneLabel"] = str(bone_label)
                clips[str(clip_name)] = clip
        return clips

    def _serialize_animation_clips(self):
        animations = []
        for clip_name in sorted(self.animation_clips.keys()):
            clip = self.animation_clips.get(clip_name, {})
            item = {
                "animationName": clip_name,
                "keyframes": clip.get("keyframes", []),
            }
            bone_label = clip.get("boneLabel")
            if bone_label:
                item["boneLabel"] = bone_label
            animations.append(item)
        return animations

    def _normalize_clip_keyframes(self, keyframes, legacy_duration=None):
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
        self._renumber_keyframes(ordered)
        return ordered

    def _renumber_keyframes(self, keyframes):
        for idx, item in enumerate(keyframes):
            item["label"] = f"frame{idx + 1}"

    def _load_animation_clips(self, embedded_animations=None):
        self.animation_clips = self._deserialize_animation_clips(embedded_animations) if embedded_animations is not None else {}
        self._refresh_timeline_clips()
        self._update_animation_editor_state()
        self._stop_playback()

    def _save_animation_clips(self):
        if self.puppet is None or not self.puppet_file_base:
            QtWidgets.QMessageBox.information(self, "Save Clips", "Open or save a puppet file first.")
            return False
        try:
            puppetExporter.save_puppet(
                self.puppet,
                self.puppet_file_base,
                animations=self._serialize_animation_clips(),
            )
            return True
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Save Clips", f"Failed to save clips:\n{exc}")
            return False

    def _current_clip_name(self):
        return self.anim_clip_name_edit.text().strip()

    def _refresh_animation_clip_selector(self, preferred_clip=None):
        if not hasattr(self, "anim_existing_clip_combo"):
            return

        current = preferred_clip if preferred_clip is not None else self.anim_existing_clip_combo.currentText().strip()
        clip_names = sorted(self.animation_clips.keys())
        self.anim_existing_clip_combo.blockSignals(True)
        self.anim_existing_clip_combo.clear()
        self.anim_existing_clip_combo.addItems(clip_names)
        if clip_names:
            if current in clip_names:
                self.anim_existing_clip_combo.setCurrentText(current)
            else:
                self.anim_existing_clip_combo.setCurrentIndex(0)
        self.anim_existing_clip_combo.blockSignals(False)

    def _on_existing_clip_selected(self, index):
        clip_name = self.anim_existing_clip_combo.currentText().strip()
        if not clip_name:
            return

        self.anim_clip_name_edit.blockSignals(True)
        self.anim_clip_name_edit.setText(clip_name)
        self.anim_clip_name_edit.blockSignals(False)
        clip = self.animation_clips.get(clip_name)
        if clip and clip.get("keyframes"):
            first_frame = int(clip["keyframes"][0].get("timelineFrame", 0))
            self.anim_timeline_spin.blockSignals(True)
            self.anim_timeline_spin.setValue(first_frame)
            self.anim_timeline_spin.blockSignals(False)
        self._update_animation_editor_state()

        if self.timeline_clip_combo.findText(clip_name) >= 0:
            self.timeline_clip_combo.setCurrentText(clip_name)

    def _rename_animation_clip(self):
        old_name = self._current_clip_name()
        if not old_name:
            QtWidgets.QMessageBox.warning(self, "Rename Clip", "Select or type a clip name first.")
            return
        if old_name not in self.animation_clips:
            QtWidgets.QMessageBox.warning(self, "Rename Clip", "Current clip does not exist.")
            return

        new_name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Rename Clip",
            "New clip name:",
            QtWidgets.QLineEdit.Normal,
            old_name,
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name:
            QtWidgets.QMessageBox.warning(self, "Rename Clip", "Clip name cannot be empty.")
            return
        if new_name != old_name and new_name in self.animation_clips:
            QtWidgets.QMessageBox.warning(self, "Rename Clip", "A clip with this name already exists.")
            return

        clip_data = self.animation_clips.pop(old_name)
        self.animation_clips[new_name] = clip_data
        self.anim_clip_name_edit.blockSignals(True)
        self.anim_clip_name_edit.setText(new_name)
        self.anim_clip_name_edit.blockSignals(False)
        self._refresh_timeline_clips(preferred_clip=new_name)
        self._refresh_animation_clip_selector(preferred_clip=new_name)
        self._update_animation_editor_state()

    def _selected_clip(self):
        clip_name = self._current_clip_name()
        if not clip_name:
            return None
        return self.animation_clips.get(clip_name)

    def _assign_animation_clip_bone(self):
        if self.active_bone is None:
            QtWidgets.QMessageBox.information(self, "Animation", "Select a bone first.")
            return
        clip_name = self._current_clip_name()
        if not clip_name:
            QtWidgets.QMessageBox.warning(self, "Animation", "Clip name cannot be empty.")
            return
        clip = self.animation_clips.get(clip_name)
        if clip is None:
            clip = {"keyframes": []}
            self.animation_clips[clip_name] = clip
        clip["boneLabel"] = self.active_bone.label
        self._update_animation_editor_state()
        self._refresh_timeline_clips(preferred_clip=clip_name)

    def _update_animation_editor_state(self):
        clip_name = self._current_clip_name()
        clip = self.animation_clips.get(clip_name) if clip_name else None

        if clip:
            keyframes_count = len(clip.get("keyframes", []))
            timeline_values = [int(kf.get("timelineFrame", 0)) for kf in clip.get("keyframes", [])]
            if timeline_values:
                timeline_range = f"{min(timeline_values)}-{max(timeline_values)}"
            else:
                timeline_range = "-"
            assigned_bone = clip.get("boneLabel") or "-"
            self.anim_assigned_bone_label.setText(str(assigned_bone))
            self.anim_clip_info_label.setText(f"Keyframes: {keyframes_count} | Timeline: {timeline_range}")
            self.anim_remove_keyframe_button.setEnabled(keyframes_count > 0)
            self.anim_clear_clip_button.setEnabled(True)
            self.anim_assign_bone_button.setEnabled(self.active_bone is not None)
            self.anim_rename_clip_button.setEnabled(True)
        else:
            self.anim_assigned_bone_label.setText("-")
            self.anim_clip_info_label.setText("No clip")
            self.anim_remove_keyframe_button.setEnabled(False)
            self.anim_clear_clip_button.setEnabled(False)
            self.anim_assign_bone_button.setEnabled(self.active_bone is not None)
            self.anim_rename_clip_button.setEnabled(False)

    def _refresh_timeline_clips(self, preferred_clip=None, preferred_frame=None):
        self._pending_timeline_frame = preferred_frame
        current = preferred_clip if preferred_clip is not None else self.timeline_clip_combo.currentText()
        self._refresh_animation_clip_selector(preferred_clip=current if current else None)
        clip_names = sorted(self.animation_clips.keys())
        self.timeline_clip_combo.blockSignals(True)
        self.timeline_clip_combo.clear()
        self.timeline_clip_combo.addItems(clip_names)
        self.timeline_clip_combo.blockSignals(False)

        if clip_names:
            if current in clip_names:
                self.timeline_clip_combo.setCurrentText(current)
            else:
                self.timeline_clip_combo.setCurrentIndex(0)
            self._on_timeline_clip_changed(self.timeline_clip_combo.currentIndex())
        else:
            self.playback_clip_name = ""
            self.playback_poses = []
            self._pending_timeline_frame = None
            self.timeline_slider.setRange(0, 0)
            self.timeline_slider.set_keyframe_positions([])
            self.timeline_slider.setValue(0)
            self.timeline_slider.setEnabled(False)
            self.timeline_play_button.setEnabled(False)
            self.timeline_frame_label.setText("0/0")
            self._stop_playback()
            self.puppet_item.clear_ghost_pose()

    def _add_animation_keyframe(self):
        if self.puppet is None or self.active_bone is None:
            QtWidgets.QMessageBox.information(self, "Animation", "Open or create a puppet first.")
            return
        clip_name = self._current_clip_name()
        if not clip_name:
            QtWidgets.QMessageBox.warning(self, "Animation", "Clip name cannot be empty.")
            return

        timeline_frame = self.anim_timeline_spin.value()
        clip = self.animation_clips.get(clip_name)
        if clip is None:
            clip = {"keyframes": []}
            self.animation_clips[clip_name] = clip

        assigned_bone = str(clip.get("boneLabel") or "").strip()
        if not assigned_bone:
            QtWidgets.QMessageBox.warning(
                self,
                "Animation",
                f'Clip "{clip_name}" has no assigned bone. Click "Assign Selected Bone" first.',
            )
            return
        if assigned_bone != self.active_bone.label:
            QtWidgets.QMessageBox.warning(
                self,
                "Animation",
                f'Clip "{clip_name}" is assigned to bone "{assigned_bone}". Select that bone or click "Assign Selected Bone".',
            )
            return

        keyframes = clip.setdefault("keyframes", [])
        existing = next((kf for kf in keyframes if int(kf.get("timelineFrame", -1)) == timeline_frame), None)
        if existing is None:
            keyframes.append(
                {
                    "x": float(self.active_bone.x),
                    "y": float(self.active_bone.y),
                    "angle": float(self.active_bone.angle),
                    "label": "",
                    "timelineFrame": timeline_frame,
                }
            )
        else:
            existing["x"] = float(self.active_bone.x)
            existing["y"] = float(self.active_bone.y)
            existing["angle"] = float(self.active_bone.angle)

        keyframes.sort(key=lambda item: int(item.get("timelineFrame", 0)))
        self._renumber_keyframes(keyframes)

        self._update_animation_editor_state()
        self._refresh_timeline_clips(preferred_clip=clip_name, preferred_frame=timeline_frame)

    def _remove_animation_keyframe(self):
        clip_name = self._current_clip_name()
        clip = self.animation_clips.get(clip_name)
        if not clip or not clip.get("keyframes"):
            return
        timeline_frame = self.anim_timeline_spin.value()
        removed = False
        for idx in range(len(clip["keyframes"]) - 1, -1, -1):
            if int(clip["keyframes"][idx].get("timelineFrame", -1)) == timeline_frame:
                clip["keyframes"].pop(idx)
                removed = True
                break
        if not removed:
            clip["keyframes"].pop()
        if not clip["keyframes"]:
            self.animation_clips.pop(clip_name, None)
        else:
            clip["keyframes"].sort(key=lambda item: int(item.get("timelineFrame", 0)))
            self._renumber_keyframes(clip["keyframes"])
        preferred_frame = timeline_frame if clip_name in self.animation_clips else None
        self._update_animation_editor_state()
        self._refresh_timeline_clips(preferred_clip=clip_name, preferred_frame=preferred_frame)

    def _clear_animation_clip(self):
        clip_name = self._current_clip_name()
        if not clip_name or clip_name not in self.animation_clips:
            return
        self.animation_clips.pop(clip_name, None)
        self._update_animation_editor_state()
        self._refresh_timeline_clips()

    def _build_clip_poses(self, clip_name):
        clip = self.animation_clips.get(clip_name)
        if not clip:
            return []
        keyframes = clip.get("keyframes", [])
        if not keyframes:
            return []
        try:
            runtime_clip = animation_lib.build_animation(clip_name, keyframes)
            self.playback_timeline_start = int(getattr(runtime_clip, "timeline_start", 0))
            return runtime_clip.to_absolute_poses()
        except Exception:
            return []

    def _update_ghost_reference_pose(self, clip_name, current_frame=None):
        if self.puppet is None or not clip_name:
            self.puppet_item.clear_ghost_pose()
            return
        clip = self.animation_clips.get(clip_name)
        if not clip:
            self.puppet_item.clear_ghost_pose()
            return
        assigned_bone = str(clip.get("boneLabel") or "").strip()
        if not assigned_bone:
            self.puppet_item.clear_ghost_pose()
            return

        keyframes = clip.get("keyframes", [])
        if not keyframes:
            self.puppet_item.clear_ghost_pose()
            return

        if current_frame is None:
            try:
                current_frame = int(self.anim_timeline_spin.value())
            except Exception:
                current_frame = 0

        selected_keyframe = None
        selected_frame = None
        earliest_keyframe = None
        earliest_frame = None
        for keyframe in keyframes:
            try:
                timeline_frame = int(keyframe.get("timelineFrame", 0))
            except Exception:
                continue

            if earliest_frame is None or timeline_frame < earliest_frame:
                earliest_keyframe = keyframe
                earliest_frame = timeline_frame

            if timeline_frame <= current_frame and (selected_frame is None or timeline_frame > selected_frame):
                selected_keyframe = keyframe
                selected_frame = timeline_frame

        if selected_keyframe is None:
            selected_keyframe = earliest_keyframe
        if selected_keyframe is None:
            self.puppet_item.clear_ghost_pose()
            return

        self.puppet_item.set_ghost_pose(
            assigned_bone,
            {
                "x": selected_keyframe.get("x", 0.0),
                "y": selected_keyframe.get("y", 0.0),
                "angle": selected_keyframe.get("angle", 0.0),
            },
        )

    def _timeline_keyframe_positions(self, clip_name):
        clip = self.animation_clips.get(clip_name)
        if not clip:
            return []
        positions = []
        for keyframe in clip.get("keyframes", []):
            try:
                timeline_frame = int(keyframe.get("timelineFrame", 0))
            except Exception:
                continue
            positions.append(timeline_frame - self.playback_timeline_start)
        return positions

    def _on_timeline_clip_changed(self, index):
        self._stop_playback()
        clip_name = self.timeline_clip_combo.currentText().strip()
        self.playback_clip_name = clip_name
        self.playback_timeline_start = 0

        if clip_name:
            self.anim_clip_name_edit.blockSignals(True)
            self.anim_clip_name_edit.setText(clip_name)
            self.anim_clip_name_edit.blockSignals(False)
            if self.anim_existing_clip_combo.findText(clip_name) >= 0:
                self.anim_existing_clip_combo.blockSignals(True)
                self.anim_existing_clip_combo.setCurrentText(clip_name)
                self.anim_existing_clip_combo.blockSignals(False)
            self._update_animation_editor_state()

        self.playback_poses = self._build_clip_poses(clip_name) if clip_name else []

        if not self.playback_poses:
            self._pending_timeline_frame = None
            self.timeline_slider.setRange(0, 0)
            self.timeline_slider.set_keyframe_positions([])
            self.timeline_slider.setValue(0)
            self.timeline_slider.setEnabled(False)
            self.timeline_play_button.setEnabled(False)
            self.timeline_frame_label.setText("0/0")
            self.puppet_item.clear_ghost_pose()
            return

        self.timeline_slider.setRange(0, len(self.playback_poses) - 1)
        self.timeline_slider.set_keyframe_positions(self._timeline_keyframe_positions(clip_name))
        self.timeline_slider.setEnabled(True)
        self.timeline_play_button.setEnabled(True)
        target_frame = self._pending_timeline_frame
        self._pending_timeline_frame = None
        if target_frame is None:
            target_index = 0
        else:
            target_index = int(target_frame) - self.playback_timeline_start
            target_index = max(0, min(len(self.playback_poses) - 1, target_index))
        self.timeline_slider.setValue(target_index)
        self._on_timeline_slider_changed(target_index)

    def _on_timeline_slider_changed(self, value):
        if self._ignore_timeline_slider_change:
            return
        self.playback_frame_index = value
        total = len(self.playback_poses)
        frame_value = None
        if total > 0:
            frame_value = self.playback_timeline_start + value
            frame_end = self.playback_timeline_start + total - 1
            self.timeline_frame_label.setText(f"{frame_value}/{frame_end}")
            self.anim_timeline_spin.blockSignals(True)
            self.anim_timeline_spin.setValue(frame_value)
            self.anim_timeline_spin.blockSignals(False)
        else:
            self.timeline_frame_label.setText("0/0")
        self._update_ghost_reference_pose(self.playback_clip_name, frame_value)
        self._apply_timeline_pose(value)

    def _toggle_playback(self):
        if not self.playback_poses:
            return
        if self.playback_timer.isActive():
            self._stop_playback()
            return
        self.playback_timer.start()
        self.timeline_play_button.setText("Stop")

    def _stop_playback(self):
        if self.playback_timer.isActive():
            self.playback_timer.stop()
        if hasattr(self, "timeline_play_button"):
            self.timeline_play_button.setText("Play")

    def _on_playback_tick(self):
        if not self.playback_poses:
            self._stop_playback()
            return
        next_frame = self.playback_frame_index + 1
        if next_frame >= len(self.playback_poses):
            next_frame = 0
        self.timeline_slider.setValue(next_frame)

    def _find_bone_by_label(self, label):
        for bone in self.bones:
            if bone.label == label:
                return bone
        return None

    def _apply_timeline_pose(self, frame_index):
        if self.puppet is None or not self.playback_poses or not self.playback_clip_name:
            return
        clip = self.animation_clips.get(self.playback_clip_name)
        if not clip:
            return
        assigned_bone = str(clip.get("boneLabel") or "").strip()
        if not assigned_bone:
            return
        bone = self._find_bone_by_label(assigned_bone)
        if bone is None:
            return
        pose = self.playback_poses[max(0, min(frame_index, len(self.playback_poses) - 1))]
        bone.x = pose["x"]
        bone.y = pose["y"]
        bone.angle = pose["angle"]
        self.puppet.recalculate_world_matrices()
        self.puppet_item.update()
        self._refresh_coords()

    def _setup_toolbar(self):
        toolbar = QtWidgets.QToolBar("Main Toolbar", self)
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        self.addToolBar(QtCore.Qt.TopToolBarArea, toolbar)

        file_menu = QtWidgets.QMenu("File", self)

        new_action = file_menu.addAction("New")
        new_action.triggered.connect(self._new_puppet)

        open_action = file_menu.addAction("Open")
        open_action.triggered.connect(self._open_puppet)

        save_action = file_menu.addAction("Save")
        save_action.triggered.connect(self._save)

        save_as_action = file_menu.addAction("Save As")
        save_as_action.triggered.connect(self._save_as)

        save_settings_action = file_menu.addAction("Save Settings")
        save_settings_action.triggered.connect(self._save_settings)

        export_action = file_menu.addAction("Export")
        export_action.triggered.connect(self._export)

        view_menu = QtWidgets.QMenu("View", self)

        zoom_in_action = view_menu.addAction("Zoom +")
        zoom_in_action.triggered.connect(self.view.zoom_in)

        zoom_out_action = view_menu.addAction("Zoom -")
        zoom_out_action.triggered.connect(self.view.zoom_out)

        view_menu.addSeparator()

        center_action = view_menu.addAction("Center")
        center_action.triggered.connect(self._center_canvas)

        view_menu.addSeparator()

        self.view_ghost_action = view_menu.addAction("Ghost")
        self.view_ghost_action.setCheckable(True)
        self.view_ghost_action.setChecked(self.settings.get("isGhostVisible", True))
        self.view_ghost_action.toggled.connect(self._toggle_ghost)

        view_menu.addSeparator()

        self.toolbar_text_action = view_menu.addAction("Text")
        self.toolbar_text_action.setCheckable(True)
        self.toolbar_text_action.setChecked(self.settings.get("isTextVisible", True))
        self.toolbar_text_action.toggled.connect(self._toggle_text)

        self.toolbar_bone_action = view_menu.addAction("Bones")
        self.toolbar_bone_action.setCheckable(True)
        self.toolbar_bone_action.setChecked(self.settings.get("isBoneVisible", True))
        self.toolbar_bone_action.toggled.connect(self._toggle_bone)

        file_button = QtWidgets.QToolButton(self)
        file_button.setText("File")
        file_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        file_button.setMenu(file_menu)
        toolbar.addWidget(file_button)

        view_button = QtWidgets.QToolButton(self)
        view_button.setText("View")
        view_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        view_button.setMenu(view_menu)
        toolbar.addWidget(view_button)

    def _setup_shortcuts(self):
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+N"), self, activated=self._new_puppet)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+O"), self, activated=self._open_puppet)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, activated=self._save)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+S"), self, activated=self._save_as)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+K"), self, activated=self._add_animation_keyframe)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+K"), self, activated=self._clear_animation_clip)
        QtGui.QShortcut(QtGui.QKeySequence("PageUp"), self, activated=self.view.zoom_in)
        QtGui.QShortcut(QtGui.QKeySequence("PageDown"), self, activated=self.view.zoom_out)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Plus), self, activated=self.view.zoom_in)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Equal), self, activated=self.view.zoom_in)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Minus), self, activated=self.view.zoom_out)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Underscore), self, activated=self.view.zoom_out)

    def _load_settings(self):
        settings = DEFAULT_SETTINGS.copy()
        try:
            with open("settings.json", "r") as f:
                settings.update(json.load(f))
        except Exception:
            pass
        return settings

    def _select_puppet_file(self):
        if self.puppet_file_path:
            start_dir = os.path.dirname(self.puppet_file_path)
        else:
            last_path = self.settings.get("lastPuppetFile", "")
            start_dir = os.path.dirname(last_path) if last_path else ""
        selected_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Puppet File",
            start_dir,
            "JSON Files (*.json);;All Files (*)",
        )
        return selected_path

    def _update_window_title(self):
        file_name = os.path.basename(self.puppet_file_path) if self.puppet_file_path else "No puppet"
        self.setWindowTitle(f"Puppet Craft - {file_name}")

    def _load_puppet_file(self, file_path):
        bundle = puppetImporter.importPuppetBundleFromJson(file_path)
        self.puppet = bundle["puppet"]
        self.puppet_file_path = file_path
        self.puppet_file_base = os.path.splitext(file_path)[0]
        self.settings["lastPuppetFile"] = file_path
        self.bones = self._collect_bones(self.puppet)
        self.active_bone = self.puppet
        self._load_animation_clips(bundle.get("animations"))

    def _open_puppet(self):
        selected_path = self._select_puppet_file()
        if not selected_path:
            return

        try:
            self._load_puppet_file(selected_path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Open Puppet File", f"Failed to open file:\n{exc}")
            return

        self.puppet_item.puppet = self.puppet
        self.puppet_item._sprite_cache.clear()
        self.puppet_item.set_active_bone(self.active_bone)
        self._populate_bone_list()
        self._refresh_coords()
        self._update_window_title()
        self.view.setFocus()

    def _confirm_save_current_file(self):
        if not self.puppet_file_path:
            return True

        answer = QtWidgets.QMessageBox.question(
            self,
            "New Puppet",
            "Save current puppet before creating a new one?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Yes,
        )
        if answer == QtWidgets.QMessageBox.Cancel:
            return False
        if answer == QtWidgets.QMessageBox.Yes:
            return self._save()
        return True

    def _normalize_new_puppet_name(self, raw_name):
        cleaned = re.sub(r'[<>:"/\\\\|?*]', "_", raw_name.strip())
        cleaned = re.sub(r"\s+", "", cleaned)
        return cleaned

    def _new_puppet(self):
        if not self._confirm_save_current_file():
            return

        default_name = "newPuppet"
        name, ok = QtWidgets.QInputDialog.getText(
            self,
            "New Puppet",
            "Puppet name:",
            QtWidgets.QLineEdit.Normal,
            default_name,
        )
        if not ok:
            return

        normalized_name = self._normalize_new_puppet_name(name)
        if not normalized_name:
            QtWidgets.QMessageBox.warning(self, "New Puppet", "Puppet name cannot be empty.")
            return

        root_label = normalized_name if normalized_name.endswith("Root") else f"{normalized_name}Root"
        file_stem = root_label[:-4] if root_label.endswith("Root") else root_label
        if not file_stem:
            QtWidgets.QMessageBox.warning(self, "New Puppet", "Invalid puppet name.")
            return

        puppet_json = {
            "label": root_label,
            "x": self.canvas_width // 2,
            "y": self.canvas_height // 2,
            "angle": 0.0,
            "bones": [],
        }
        self.puppet = puppet.Puppet(puppet_json, [])
        self.bones = self._collect_bones(self.puppet)
        self.active_bone = self.puppet

        self.canvas_pan_x = 0.0
        self.canvas_pan_y = 0.0

        self.puppet_file_path = os.path.abspath(f"{file_stem}.json")
        self.puppet_file_base = os.path.splitext(self.puppet_file_path)[0]
        self.settings["lastPuppetFile"] = self.puppet_file_path

        os.makedirs(f"sprites_{file_stem}", exist_ok=True)
        self.animation_clips = {}
        self._refresh_timeline_clips()
        self._update_animation_editor_state()
        self._stop_playback()

        self.puppet_item.puppet = self.puppet
        self.puppet_item._sprite_cache.clear()
        self.puppet_item.set_active_bone(self.active_bone)
        self._populate_bone_list()
        self._refresh_coords()
        self._layout_scene()
        self._update_window_title()
        self.view.setFocus()

    def _collect_bones(self, puppet):
        collected = [puppet]

        def visit(bone):
            collected.append(bone)
            for child in bone.childBonesLayer1:
                visit(child)
            for child in bone.childBonesLayer2:
                visit(child)

        for bone in puppet.bones:
            visit(bone)
        return collected

    def _populate_bone_list(self):
        self.bone_list.clear()
        for bone in self.bones:
            item = QtWidgets.QListWidgetItem(bone.label)
            item.setData(QtCore.Qt.UserRole, bone)
            self.bone_list.addItem(item)
        if self.bones:
            self.bone_list.setCurrentRow(0)

    def _on_bone_selected(self, current, previous):
        if not current:
            return
        self.active_bone = current.data(QtCore.Qt.UserRole)
        self.puppet_item.set_active_bone(self.active_bone)
        self._refresh_coords()
        self._update_animation_editor_state()
        self.view.setFocus()

    def _toggle_text(self, value):
        self.settings["isTextVisible"] = bool(value)
        self.puppet_item.set_settings(self.settings)
        if hasattr(self, "toolbar_text_action"):
            self.toolbar_text_action.setChecked(bool(value))

    def _toggle_bone(self, value):
        self.settings["isBoneVisible"] = bool(value)
        self.puppet_item.set_settings(self.settings)
        if hasattr(self, "toolbar_bone_action"):
            self.toolbar_bone_action.setChecked(bool(value))

    def _toggle_ghost(self, value):
        self.settings["isGhostVisible"] = bool(value)
        self.puppet_item.set_settings(self.settings)
        if hasattr(self, "view_ghost_action"):
            self.view_ghost_action.setChecked(bool(value))

    def _refresh_coords(self):
        if self.active_bone is None:
            self.coords_label.setText("x: -, y: -, angle: -")
            return

        bone = self.active_bone
        self.coords_label.setText(
            f"x: {int(round(bone.worldMatrix[0][2]))}, y: {int(round(bone.worldMatrix[1][2]))}, angle: {bone.angle}"
        )

    def _layout_scene(self):
        scale = self.view.scale_factor
        viewport = self.view.viewport().size()
        if viewport.width() <= 0 or viewport.height() <= 0:
            return
        logical_w = viewport.width() / scale
        logical_h = viewport.height() / scale
        self.scene.setSceneRect(0, 0, logical_w, logical_h)

        offset_x = (logical_w - self.canvas_width) / 2 + self.canvas_pan_x
        offset_y = (logical_h - self.canvas_height) / 2 + self.canvas_pan_y
        canvas_rect = QtCore.QRectF(offset_x, offset_y, self.canvas_width, self.canvas_height)

        self.canvas_bg_item.setRect(canvas_rect)
        self.border_item.setRect(canvas_rect.adjusted(0.5, 0.5, -0.5, -0.5))
        self.puppet_item.setPos(canvas_rect.topLeft())
        self.puppet_item.set_draw_offset(0, 0)

        path = QtGui.QPainterPath()
        path.addRect(self.scene.sceneRect())
        path.addRect(canvas_rect)
        path.setFillRule(QtCore.Qt.OddEvenFill)
        self.shade_item.setPath(path)

    def _pan_canvas(self, dx, dy):
        self.canvas_pan_x += dx
        self.canvas_pan_y += dy
        self._layout_scene()

    def _center_canvas(self):
        self.canvas_pan_x = 0.0
        self.canvas_pan_y = 0.0
        self._layout_scene()
        self.view.setFocus()

    def _save(self):
        if self.puppet is None or not self.puppet_file_base:
            QtWidgets.QMessageBox.information(self, "Save Puppet", "Open a puppet file first.")
            return False
        try:
            puppetExporter.save_puppet(
                self.puppet,
                self.puppet_file_base,
                animations=self._serialize_animation_clips(),
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Save Puppet", f"Failed to save file:\n{exc}")
            return False
        return True

    def _save_as(self):
        if self.puppet is None:
            QtWidgets.QMessageBox.information(self, "Save As", "Open a puppet file first.")
            return

        if self.puppet_file_path:
            start_path = self.puppet_file_path
        else:
            last_path = self.settings.get("lastPuppetFile", "")
            start_path = last_path if last_path else "puppet.json"

        selected_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Puppet As",
            start_path,
            "JSON Files (*.json);;All Files (*)",
        )
        if not selected_path:
            return

        if not selected_path.lower().endswith(".json"):
            selected_path = f"{selected_path}.json"

        self.puppet_file_path = selected_path
        self.puppet_file_base = os.path.splitext(selected_path)[0]
        self.settings["lastPuppetFile"] = selected_path
        self._update_window_title()
        puppetExporter.save_puppet(
            self.puppet,
            self.puppet_file_base,
            animations=self._serialize_animation_clips(),
        )
        self._refresh_timeline_clips()
        self._update_animation_editor_state()

    def _save_settings(self):
        puppetExporter.save_settings(self.settings)

    def _export(self):
        if self.puppet is None or not self.puppet_file_base:
            QtWidgets.QMessageBox.information(self, "Export", "Open a puppet file first.")
            return
        puppetExporter.export_cpuppet(self.puppet, self.puppet_file_base)

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Up:
            self._move_bone(0, -1)
        elif key == QtCore.Qt.Key_Down:
            self._move_bone(0, 1)
        elif key == QtCore.Qt.Key_Left:
            self._move_bone(-1, 0)
        elif key == QtCore.Qt.Key_Right:
            self._move_bone(1, 0)
        elif key == QtCore.Qt.Key_E:
            self._rotate_bone(-0.1)
        elif key == QtCore.Qt.Key_Q:
            self._rotate_bone(0.1)
        else:
            super().keyPressEvent(event)

    def _move_bone(self, dx, dy):
        if self.active_bone is None or self.puppet is None:
            return
        self.active_bone.x += dx
        self.active_bone.y += dy
        self.puppet.recalculate_world_matrices()
        self.puppet_item.update()
        self._refresh_coords()

    def _rotate_bone(self, angle):
        if self.active_bone is None or self.puppet is None:
            return
        self.active_bone.angle = round(self.active_bone.angle + angle, 2)
        self.puppet.recalculate_world_matrices()
        self.puppet_item.update()
        self._refresh_coords()
