from PySide6 import QtCore, QtGui, QtWidgets


class KeyframeTimelineSlider(QtWidgets.QSlider):
    def __init__(self, orientation=QtCore.Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self._keyframe_positions = []
        self._marker_color = QtGui.QColor(255, 196, 64)
        self._active_marker_color = QtGui.QColor(255, 255, 255)
        self.valueChanged.connect(self._on_slider_value_changed)

    def _on_slider_value_changed(self, _value):
        self.update()

    def set_keyframe_positions(self, positions):
        cleaned = []
        for pos in positions:
            try:
                cleaned.append(int(pos))
            except Exception:
                continue
        unique_sorted = sorted(set(cleaned))
        if unique_sorted == self._keyframe_positions:
            return
        self._keyframe_positions = unique_sorted
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._keyframe_positions:
            return

        option = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(option)
        groove = self.style().subControlRect(
            QtWidgets.QStyle.CC_Slider,
            option,
            QtWidgets.QStyle.SC_SliderGroove,
            self,
        )
        if groove.width() <= 0:
            return

        minimum = self.minimum()
        maximum = self.maximum()
        span = maximum - minimum
        marker_top = max(0, groove.top() - 5)
        marker_bottom = min(self.height() - 1, groove.bottom() + 5)
        usable_width = max(1, groove.width() - 1)
        current = self.value()

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)

        for marker in self._keyframe_positions:
            if marker < minimum or marker > maximum:
                continue
            if span <= 0:
                x = groove.left() + groove.width() // 2
            else:
                ratio = (marker - minimum) / span
                x = groove.left() + int(round(ratio * usable_width))
            color = self._active_marker_color if marker == current else self._marker_color
            width = 2 if marker == current else 1
            painter.setPen(QtGui.QPen(color, width))
            painter.drawLine(x, marker_top, x, marker_bottom)


class PuppetView(QtWidgets.QGraphicsView):
    layoutChanged = QtCore.Signal()
    moveRequested = QtCore.Signal(int, int)
    rotateRequested = QtCore.Signal(float)
    panRequested = QtCore.Signal(float, float)

    def __init__(self, scene, puppet_item, parent=None):
        super().__init__(scene, parent)
        self.puppet_item = puppet_item
        self.scale_factor = 2.0
        self._space_pressed = False
        self._is_panning = False
        self._last_pan_pos = QtCore.QPoint()
        self.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(127, 127, 127)))
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self._apply_scale()

    def _apply_scale(self):
        transform = QtGui.QTransform()
        transform.scale(self.scale_factor, self.scale_factor)
        self.setTransform(transform)

    def _update_pan_cursor(self):
        if self._is_panning:
            self.viewport().setCursor(QtCore.Qt.ClosedHandCursor)
        elif self._space_pressed:
            self.viewport().setCursor(QtCore.Qt.OpenHandCursor)
        else:
            self.viewport().unsetCursor()

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

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Space:
            if not event.isAutoRepeat():
                self._space_pressed = True
                self._update_pan_cursor()
            event.accept()
            return
        if key in (QtCore.Qt.Key_Up, QtCore.Qt.Key_W):
            self.moveRequested.emit(0, -1)
            event.accept()
            return
        if key in (QtCore.Qt.Key_Down, QtCore.Qt.Key_S):
            self.moveRequested.emit(0, 1)
            event.accept()
            return
        if key in (QtCore.Qt.Key_Left, QtCore.Qt.Key_A):
            self.moveRequested.emit(-1, 0)
            event.accept()
            return
        if key in (QtCore.Qt.Key_Right, QtCore.Qt.Key_D):
            self.moveRequested.emit(1, 0)
            event.accept()
            return
        if key == QtCore.Qt.Key_E:
            self.rotateRequested.emit(-0.1)
            event.accept()
            return
        if key == QtCore.Qt.Key_Q:
            self.rotateRequested.emit(0.1)
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            if not event.isAutoRepeat():
                self._space_pressed = False
                self._is_panning = False
                self._update_pan_cursor()
            event.accept()
            return
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        if self._space_pressed and event.button() == QtCore.Qt.LeftButton:
            self._is_panning = True
            self._last_pan_pos = event.pos()
            self._update_pan_cursor()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning:
            delta = event.pos() - self._last_pan_pos
            self._last_pan_pos = event.pos()
            if not delta.isNull():
                self.panRequested.emit(delta.x() / self.scale_factor, delta.y() / self.scale_factor)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_panning and event.button() == QtCore.Qt.LeftButton:
            self._is_panning = False
            self._update_pan_cursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)
