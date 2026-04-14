import sys
import math
import json
from PySide6 import QtCore, QtGui, QtWidgets

import puppetImporter
import puppetExporter

puppet_file_name = "mascot"
DEFAULT_CANVAS_WIDTH = 320
DEFAULT_CANVAS_HEIGHT = 240

DEFAULT_SETTINGS = {
    "isTextVisible": True,
    "isBoneVisible": True,
}


class PuppetScene(QtWidgets.QGraphicsScene):
    def __init__(self, width, height, parent=None):
        super().__init__(0, 0, width, height, parent)
        self._bg_color = QtGui.QColor(127, 127, 127)

    def drawBackground(self, painter, rect):
        painter.fillRect(self.sceneRect(), self._bg_color)


class PuppetItem(QtWidgets.QGraphicsItem):
    def __init__(self, puppet, settings, parent=None):
        super().__init__(parent)
        self.puppet = puppet
        self.settings = settings
        self.active_bone = puppet
        self._sprite_cache = {}
        self._font = QtGui.QFont("Arial", 8)
        self._draw_offset = QtCore.QPointF(0.0, 0.0)

    def boundingRect(self):
        # Oversized rect to avoid clipping; scene rect controls viewport anyway.
        return QtCore.QRectF(-2000, -2000, 4000, 4000)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.save()
        painter.translate(self._draw_offset)
        self._draw_puppet(painter)
        painter.restore()

    def set_active_bone(self, bone):
        self.active_bone = bone
        self.update()

    def set_settings(self, settings):
        self.settings = settings
        self.update()

    def set_draw_offset(self, x, y):
        self._draw_offset = QtCore.QPointF(x, y)
        self.update()

    def _get_sprite_image(self, sprite):
        key = id(sprite)
        if key in self._sprite_cache:
            return self._sprite_cache[key]
        size = sprite.size
        image = QtGui.QImage(size, size, QtGui.QImage.Format_ARGB32)
        for x in range(size):
            for y in range(size):
                r, g, b = sprite.pixels[x * size + y]
                if (r, g, b) == (255, 0, 255):
                    color = QtGui.QColor(0, 0, 0, 0)
                else:
                    color = QtGui.QColor(r, g, b, 255)
                image.setPixelColor(x, y, color)
        self._sprite_cache[key] = image
        return image

    def _draw_sprite(self, painter, bone, parent_x, parent_y):
        if bone.spriteIndex < 0:
            return
        angle = math.atan2(bone.worldMatrix[1][2] - parent_y, bone.worldMatrix[0][2] - parent_x)
        angle += bone.baseSpriteRotation
        center_x = (bone.worldMatrix[0][2] + (parent_x - bone.worldMatrix[0][2]) / 2)
        center_y = (bone.worldMatrix[1][2] + (parent_y - bone.worldMatrix[1][2]) / 2)
        sprite_image = self._get_sprite_image(bone.sprite)
        size = bone.sprite.size

        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(math.degrees(angle))
        painter.drawImage(QtCore.QPointF(-size / 2, -size / 2), sprite_image)
        painter.restore()

    def _draw_bone(self, painter, bone, parent_x, parent_y):
        for child in bone.childBonesLayer2:
            self._draw_bone(painter, child, bone.worldMatrix[0][2], bone.worldMatrix[1][2])

        self._draw_sprite(painter, bone, parent_x, parent_y)

        if bone.spriteIndex >= 0 and self.settings.get("isBoneVisible", True):
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255)))
            painter.drawLine(
                QtCore.QPointF(bone.worldMatrix[0][2], bone.worldMatrix[1][2]),
                QtCore.QPointF(parent_x, parent_y),
            )

        if self.settings.get("isBoneVisible", True):
            color = QtGui.QColor(0, 255, 0) if self.active_bone == bone else QtGui.QColor(255, 0, 0)
            painter.setBrush(QtGui.QBrush(color))
            painter.setPen(QtGui.QPen(color))
            painter.drawEllipse(
                QtCore.QPointF(bone.worldMatrix[0][2], bone.worldMatrix[1][2]),
                3,
                3,
            )

        if self.settings.get("isTextVisible", True):
            painter.setFont(self._font)
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0)))
            painter.drawText(
                QtCore.QPointF(bone.worldMatrix[0][2] + 5, bone.worldMatrix[1][2]),
                bone.label,
            )

        for child in bone.childBonesLayer1:
            self._draw_bone(painter, child, bone.worldMatrix[0][2], bone.worldMatrix[1][2])

    def _draw_puppet(self, painter):
        if self.settings.get("isBoneVisible", True):
            color = QtGui.QColor(0, 255, 0) if self.active_bone == self.puppet else QtGui.QColor(255, 0, 0)
            painter.setBrush(QtGui.QBrush(color))
            painter.setPen(QtGui.QPen(color))
            painter.drawEllipse(QtCore.QPointF(self.puppet.worldMatrix[0][2], self.puppet.worldMatrix[1][2]), 3, 3)

        if self.settings.get("isTextVisible", True):
            painter.setFont(self._font)
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0)))
            painter.drawText(
                QtCore.QPointF(self.puppet.worldMatrix[0][2] + 5, self.puppet.worldMatrix[1][2]),
                self.puppet.label,
            )

        for bone in self.puppet.bones:
            self._draw_bone(painter, bone, self.puppet.worldMatrix[0][2], self.puppet.worldMatrix[1][2])


class PuppetView(QtWidgets.QGraphicsView):
    layoutChanged = QtCore.Signal()

    def __init__(self, scene, puppet_item, parent=None):
        super().__init__(scene, parent)
        self.puppet_item = puppet_item
        self.scale_factor = 2.0
        self.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(127, 127, 127)))
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self._apply_scale()

    def _apply_scale(self):
        transform = QtGui.QTransform()
        transform.scale(self.scale_factor, self.scale_factor)
        self.setTransform(transform)


    def zoom_in(self):
        if self.scale_factor < 4:
            self.scale_factor += 1
            self._apply_scale()
            self.layoutChanged.emit()

    def zoom_out(self):
        if self.scale_factor > 1:
            self.scale_factor -= 1
            self._apply_scale()
            self.layoutChanged.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.layoutChanged.emit()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = self._load_settings()
        self.puppet = puppetImporter.importPuppetFromJson(f"{puppet_file_name}.json")
        self.bones = self._collect_bones(self.puppet)
        self.active_bone = self.puppet
        self.canvas_width, self.canvas_height = DEFAULT_CANVAS_WIDTH, DEFAULT_CANVAS_HEIGHT

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

        self.bone_list = QtWidgets.QListWidget()
        self._populate_bone_list()
        self.bone_list.currentItemChanged.connect(self._on_bone_selected)

        self.text_visible = QtWidgets.QCheckBox("Text Visible")
        self.text_visible.setChecked(self.settings.get("isTextVisible", True))
        self.text_visible.toggled.connect(self._toggle_text)

        self.bone_visible = QtWidgets.QCheckBox("Bone Visible")
        self.bone_visible.setChecked(self.settings.get("isBoneVisible", True))
        self.bone_visible.toggled.connect(self._toggle_bone)

        self.coords_label = QtWidgets.QLabel("x: 0, y: 0, angle: 0.0")

        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(["Edit Mode", "Animation Mode", "Play Mode"])
        self.mode_combo.setCurrentIndex(0)

        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.addWidget(QtWidgets.QLabel("Bones"))
        right_layout.addWidget(self.bone_list)
        right_layout.addWidget(self.text_visible)
        right_layout.addWidget(self.bone_visible)
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

    def _setup_shortcuts(self):
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, activated=self._save)
        QtGui.QShortcut(QtGui.QKeySequence("PageUp"), self, activated=self.view.zoom_in)
        QtGui.QShortcut(QtGui.QKeySequence("PageDown"), self, activated=self.view.zoom_out)

    def _load_settings(self):
        settings = DEFAULT_SETTINGS.copy()
        try:
            with open("settings.json", "r") as f:
                settings.update(json.load(f))
        except Exception:
            pass
        return settings


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

    def _toggle_bone(self, value):
        self.settings["isBoneVisible"] = bool(value)
        self.puppet_item.set_settings(self.settings)

    def _refresh_coords(self):
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

        offset_x = (logical_w - self.canvas_width) / 2
        offset_y = (logical_h - self.canvas_height) / 2
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

    def _save(self):
        puppetExporter.save_to_file(self.puppet, self.settings, puppet_file_name)

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
        self.active_bone.x += dx
        self.active_bone.y += dy
        self.puppet.recalculate_world_matrices()
        self.puppet_item.update()
        self._refresh_coords()

    def _rotate_bone(self, angle):
        self.active_bone.angle = round(self.active_bone.angle + angle, 2)
        self.puppet.recalculate_world_matrices()
        self.puppet_item.update()
        self._refresh_coords()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
