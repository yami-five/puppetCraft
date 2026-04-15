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
        if self.puppet is None:
            return

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
