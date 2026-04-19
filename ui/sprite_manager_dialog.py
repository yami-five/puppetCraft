import os

from PySide6 import QtCore, QtWidgets


class SpriteManagerDialog(QtWidgets.QDialog):
    def __init__(self, sprite_paths, start_dir="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Sprites")
        self.resize(700, 420)

        self._start_dir = str(start_dir or "")
        self._paths = [os.path.abspath(str(path)) for path in (sprite_paths or [])]

        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_widget.currentRowChanged.connect(self._update_buttons)
        self.list_widget.itemSelectionChanged.connect(self._update_buttons)
        root_layout.addWidget(self.list_widget, 1)

        actions_row = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton("Add")
        self.add_button.clicked.connect(self._add_items)
        actions_row.addWidget(self.add_button)

        self.remove_button = QtWidgets.QPushButton("Remove")
        self.remove_button.clicked.connect(self._remove_selected)
        actions_row.addWidget(self.remove_button)

        actions_row.addSpacing(16)

        self.up_button = QtWidgets.QPushButton("Move Up")
        self.up_button.clicked.connect(self._move_selected_up)
        actions_row.addWidget(self.up_button)

        self.down_button = QtWidgets.QPushButton("Move Down")
        self.down_button.clicked.connect(self._move_selected_down)
        actions_row.addWidget(self.down_button)
        actions_row.addStretch(1)
        root_layout.addLayout(actions_row)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root_layout.addWidget(buttons)

        self._refresh_list()

    @staticmethod
    def _normalized(path):
        return os.path.normcase(os.path.normpath(os.path.abspath(str(path))))

    def paths(self):
        return list(self._paths)

    def _refresh_list(self):
        selected_rows = sorted({index.row() for index in self.list_widget.selectedIndexes()})
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for idx, path in enumerate(self._paths):
            item = QtWidgets.QListWidgetItem(f"{idx:02d}  {os.path.basename(path)}")
            item.setToolTip(path)
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)

        if self._paths:
            if not selected_rows:
                self.list_widget.setCurrentRow(0)
            else:
                for row in selected_rows:
                    if 0 <= row < self.list_widget.count():
                        self.list_widget.item(row).setSelected(True)
                row = selected_rows[0]
                if 0 <= row < self.list_widget.count():
                    self.list_widget.setCurrentRow(row)

        self._update_buttons()

    def _add_items(self):
        selected_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Add Sprite Files",
            self._start_dir,
            "Images (*.bmp *.png *.jpg *.jpeg *.gif *.webp);;All Files (*)",
        )
        if not selected_paths:
            return

        self._start_dir = os.path.dirname(selected_paths[0]) if selected_paths else self._start_dir
        existing = {self._normalized(path) for path in self._paths}
        appended = []
        for path in selected_paths:
            normalized = self._normalized(path)
            if normalized in existing:
                continue
            existing.add(normalized)
            abs_path = os.path.abspath(str(path))
            self._paths.append(abs_path)
            appended.append(abs_path)

        if appended:
            self._refresh_list()
            self.list_widget.clearSelection()
            for path in appended:
                row = self._paths.index(path)
                self.list_widget.item(row).setSelected(True)
            self.list_widget.setCurrentRow(self._paths.index(appended[-1]))

    def _remove_selected(self):
        rows = sorted({index.row() for index in self.list_widget.selectedIndexes()}, reverse=True)
        if not rows:
            return
        for row in rows:
            if 0 <= row < len(self._paths):
                self._paths.pop(row)
        self._refresh_list()

    def _move_selected_up(self):
        rows = sorted({index.row() for index in self.list_widget.selectedIndexes()})
        if len(rows) != 1:
            return
        row = rows[0]
        if row <= 0:
            return
        self._paths[row - 1], self._paths[row] = self._paths[row], self._paths[row - 1]
        self._refresh_list()
        self.list_widget.clearSelection()
        self.list_widget.item(row - 1).setSelected(True)
        self.list_widget.setCurrentRow(row - 1)

    def _move_selected_down(self):
        rows = sorted({index.row() for index in self.list_widget.selectedIndexes()})
        if len(rows) != 1:
            return
        row = rows[0]
        if row < 0 or row >= len(self._paths) - 1:
            return
        self._paths[row + 1], self._paths[row] = self._paths[row], self._paths[row + 1]
        self._refresh_list()
        self.list_widget.clearSelection()
        self.list_widget.item(row + 1).setSelected(True)
        self.list_widget.setCurrentRow(row + 1)

    def _update_buttons(self):
        selected_rows = sorted({index.row() for index in self.list_widget.selectedIndexes()})
        has_selection = bool(selected_rows)
        self.remove_button.setEnabled(has_selection)

        can_move = len(selected_rows) == 1
        if can_move:
            row = selected_rows[0]
            self.up_button.setEnabled(row > 0)
            self.down_button.setEnabled(0 <= row < len(self._paths) - 1)
        else:
            self.up_button.setEnabled(False)
            self.down_button.setEnabled(False)
