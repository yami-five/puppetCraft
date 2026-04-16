import math
from PySide6 import QtCore, QtGui, QtWidgets


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
        self._ghost_pose = None
        self._ghost_sprite_positions = {}
        self._ghost_opacity = 0.5

    def boundingRect(self):
        # Oversized rect to avoid clipping; scene rect controls viewport anyway.
        return QtCore.QRectF(-2000, -2000, 4000, 4000)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        if self.settings.get("isGhostVisible", True):
            ghost_sprite_positions = self._ghost_sprite_positions
        else:
            ghost_sprite_positions = {}
        painter.save()
        painter.translate(self._draw_offset)
        self._draw_puppet(painter, ghost_sprite_positions=ghost_sprite_positions)
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

    def set_ghost_pose(self, bone_label, pose):
        if not bone_label or not isinstance(pose, dict):
            self.clear_ghost_pose()
            return
        try:
            x = float(pose.get("x", 0.0))
            y = float(pose.get("y", 0.0))
            angle = float(pose.get("angle", 0.0))
        except Exception:
            self.clear_ghost_pose()
            return
        self._ghost_pose = {
            "boneLabel": str(bone_label),
            "x": x,
            "y": y,
            "angle": angle,
        }
        self._ghost_sprite_positions = self._build_ghost_sprite_positions()
        self.update()

    def clear_ghost_pose(self):
        if self._ghost_pose is None and not self._ghost_sprite_positions:
            return
        self._ghost_pose = None
        self._ghost_sprite_positions = {}
        self.update()

    def capture_ghost_from_current_pose(self):
        if self.puppet is None:
            self.clear_ghost_pose()
            return False

        positions = {}
        for root_bone in self.puppet.bones:
            self._collect_ghost_sprite_positions(
                root_bone,
                self.puppet.worldMatrix[0][2],
                self.puppet.worldMatrix[1][2],
                positions,
            )

        self._ghost_pose = None
        self._ghost_sprite_positions = positions
        self.update()
        return True

    def _find_bone_by_label(self, label):
        if self.puppet is None:
            return None
        if self.puppet.label == label:
            return self.puppet

        stack = list(self.puppet.bones)
        while stack:
            bone = stack.pop()
            if bone.label == label:
                return bone
            stack.extend(bone.childBonesLayer1)
            stack.extend(bone.childBonesLayer2)
        return None

    def _collect_ghost_sprite_positions(self, bone, parent_x, parent_y, positions):
        angle = math.atan2(bone.worldMatrix[1][2] - parent_y, bone.worldMatrix[0][2] - parent_x)
        angle += bone.baseSpriteRotation
        center_x = bone.worldMatrix[0][2] + (parent_x - bone.worldMatrix[0][2]) / 2
        center_y = bone.worldMatrix[1][2] + (parent_y - bone.worldMatrix[1][2]) / 2
        positions[id(bone)] = (center_x, center_y, angle)

        for child in bone.childBonesLayer1:
            self._collect_ghost_sprite_positions(child, bone.worldMatrix[0][2], bone.worldMatrix[1][2], positions)
        for child in bone.childBonesLayer2:
            self._collect_ghost_sprite_positions(child, bone.worldMatrix[0][2], bone.worldMatrix[1][2], positions)

    def _build_ghost_sprite_positions(self):
        if self.puppet is None or not self._ghost_pose:
            return {}

        bone = self._find_bone_by_label(self._ghost_pose.get("boneLabel"))
        if bone is None:
            return {}

        original_x = bone.x
        original_y = bone.y
        original_angle = bone.angle
        try:
            bone.x = self._ghost_pose["x"]
            bone.y = self._ghost_pose["y"]
            bone.angle = self._ghost_pose["angle"]
            self.puppet.recalculate_world_matrices()

            positions = {}
            for root_bone in self.puppet.bones:
                self._collect_ghost_sprite_positions(
                    root_bone,
                    self.puppet.worldMatrix[0][2],
                    self.puppet.worldMatrix[1][2],
                    positions,
                )
            return positions
        finally:
            bone.x = original_x
            bone.y = original_y
            bone.angle = original_angle
            self.puppet.recalculate_world_matrices()

    def _get_sprite_image(self, sprite, grayscale=False):
        key = (id(sprite), bool(grayscale))
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
                    if grayscale:
                        luma = int(round(0.2126 * r + 0.7152 * g + 0.0722 * b))
                        color = QtGui.QColor(luma, luma, luma, 255)
                    else:
                        color = QtGui.QColor(r, g, b, 255)
                image.setPixelColor(x, y, color)
        self._sprite_cache[key] = image
        return image

    def _draw_sprite(self, painter, bone, parent_x, parent_y, ghost_sprite_positions=None):
        if bone.spriteIndex < 0:
            return

        if ghost_sprite_positions is not None:
            ghost_transform = ghost_sprite_positions.get(id(bone))
            if ghost_transform is not None:
                ghost_center_x, ghost_center_y, ghost_angle = ghost_transform
                ghost_image = self._get_sprite_image(bone.sprite, grayscale=True)
                size = bone.sprite.size
                painter.save()
                painter.setOpacity(self._ghost_opacity)
                painter.translate(ghost_center_x, ghost_center_y)
                painter.rotate(math.degrees(ghost_angle))
                painter.drawImage(QtCore.QPointF(-size / 2, -size / 2), ghost_image)
                painter.restore()

        angle = math.atan2(bone.worldMatrix[1][2] - parent_y, bone.worldMatrix[0][2] - parent_x)
        angle += bone.baseSpriteRotation
        center_x = (bone.worldMatrix[0][2] + (parent_x - bone.worldMatrix[0][2]) / 2)
        center_y = (bone.worldMatrix[1][2] + (parent_y - bone.worldMatrix[1][2]) / 2)
        sprite_image = self._get_sprite_image(bone.sprite, grayscale=False)
        size = bone.sprite.size

        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(math.degrees(angle))
        painter.drawImage(QtCore.QPointF(-size / 2, -size / 2), sprite_image)
        painter.restore()

    def _draw_bone(self, painter, bone, parent_x, parent_y, ghost_sprite_positions=None):
        for child in bone.childBonesLayer2:
            self._draw_bone(painter, child, bone.worldMatrix[0][2], bone.worldMatrix[1][2], ghost_sprite_positions)

        self._draw_sprite(painter, bone, parent_x, parent_y, ghost_sprite_positions)

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
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255)))
            painter.drawText(
                QtCore.QPointF(bone.worldMatrix[0][2] + 5, bone.worldMatrix[1][2]),
                bone.label,
            )

        for child in bone.childBonesLayer1:
            self._draw_bone(painter, child, bone.worldMatrix[0][2], bone.worldMatrix[1][2], ghost_sprite_positions)

    def _draw_puppet(self, painter, ghost_sprite_positions=None):
        if self.puppet is None:
            return

        if self.settings.get("isBoneVisible", True):
            color = QtGui.QColor(0, 255, 0) if self.active_bone == self.puppet else QtGui.QColor(255, 0, 0)
            painter.setBrush(QtGui.QBrush(color))
            painter.setPen(QtGui.QPen(color))
            painter.drawEllipse(QtCore.QPointF(self.puppet.worldMatrix[0][2], self.puppet.worldMatrix[1][2]), 3, 3)

        if self.settings.get("isTextVisible", True):
            painter.setFont(self._font)
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255)))
            painter.drawText(
                QtCore.QPointF(self.puppet.worldMatrix[0][2] + 5, self.puppet.worldMatrix[1][2]),
                self.puppet.label,
            )

        for bone in self.puppet.bones:
            self._draw_bone(painter, bone, self.puppet.worldMatrix[0][2], self.puppet.worldMatrix[1][2], ghost_sprite_positions)
