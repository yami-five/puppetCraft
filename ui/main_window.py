import json
import os

from PySide6 import QtCore, QtGui, QtWidgets

import puppetExporter
import puppetImporter
from app_constants import DEFAULT_CANVAS_HEIGHT, DEFAULT_CANVAS_WIDTH, DEFAULT_SETTINGS
from ui.graphics import PuppetItem, PuppetScene
from ui.view import PuppetView


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
        self.mode_combo.addItems(["Edit Mode", "Animation Mode", "Play Mode"])
        self.mode_combo.setCurrentIndex(0)

        self._setup_toolbar()

        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.addWidget(QtWidgets.QLabel("Bones"))
        right_layout.addWidget(self.bone_list)
        right_layout.addWidget(self.coords_label)
        right_layout.addWidget(self.mode_combo)
        right_layout.addStretch(1)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(central)
        layout.addWidget(self.view, 1)
        layout.addWidget(right_panel)

        self.setCentralWidget(central)
        self.setWindowTitle("Puppet Craft")
        self.resize(1280, 720)

        self._setup_shortcuts()
        self._refresh_coords()
        QtCore.QTimer.singleShot(0, self._layout_scene)
        self._update_window_title()

    def _setup_toolbar(self):
        toolbar = QtWidgets.QToolBar("Main Toolbar", self)
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        self.addToolBar(QtCore.Qt.TopToolBarArea, toolbar)

        file_menu = QtWidgets.QMenu("File", self)

        open_action = file_menu.addAction("Open")
        open_action.triggered.connect(self._open_puppet)

        save_action = file_menu.addAction("Save")
        save_action.triggered.connect(self._save)

        view_menu = QtWidgets.QMenu("View", self)

        zoom_in_action = view_menu.addAction("Zoom +")
        zoom_in_action.triggered.connect(self.view.zoom_in)

        zoom_out_action = view_menu.addAction("Zoom -")
        zoom_out_action.triggered.connect(self.view.zoom_out)

        view_menu.addSeparator()

        center_action = view_menu.addAction("Center")
        center_action.triggered.connect(self._center_canvas)

        tools_menu = QtWidgets.QMenu("Tools", self)

        self.toolbar_text_action = tools_menu.addAction("Text")
        self.toolbar_text_action.setCheckable(True)
        self.toolbar_text_action.setChecked(self.settings.get("isTextVisible", True))
        self.toolbar_text_action.toggled.connect(self._toggle_text)

        self.toolbar_bone_action = tools_menu.addAction("Bones")
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

        tools_button = QtWidgets.QToolButton(self)
        tools_button.setText("Tools")
        tools_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        tools_button.setMenu(tools_menu)
        toolbar.addWidget(tools_button)

    def _setup_shortcuts(self):
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+O"), self, activated=self._open_puppet)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, activated=self._save)
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
        self.puppet = puppetImporter.importPuppetFromJson(file_path)
        self.puppet_file_path = file_path
        self.puppet_file_base = os.path.splitext(file_path)[0]
        self.settings["lastPuppetFile"] = file_path
        self.bones = self._collect_bones(self.puppet)
        self.active_bone = self.puppet

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
            return
        puppetExporter.save_to_file(self.puppet, self.settings, self.puppet_file_base)

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
