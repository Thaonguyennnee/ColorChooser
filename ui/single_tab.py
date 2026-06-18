import cv2
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QFileDialog, QSlider, QScrollArea, QTableWidget,
                             QTableWidgetItem, QSplitter, QMessageBox, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QKeySequence
from PyQt5.QtWidgets import QShortcut

from core.color_analyzer import calculate_color_stats

class DrawableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.mask_image = None
        self.drawing = False
        self.brush_size = 15
        self.last_point = QPoint()
        self.original_bgr = None
        self.history = []
        self.scale_factor = 1.0
        self.eraser_mode = False
        self.cursor_pos = None
        self.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.setMouseTracking(True)

    def set_image(self, image_bgr):
        self.history = []
        self.original_bgr = image_bgr.copy()

        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = image_rgb.shape
        bytes_per_line = ch * w
        self.image = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()

        self.mask_image = QImage(self.image.size(), QImage.Format.Format_ARGB32)
        self.mask_image.fill(Qt.transparent)
        self.update_scale(1.0)

    def update_scale(self, factor):
        self.scale_factor = factor
        if self.image:
            self.setFixedSize(int(self.image.width() * factor), int(self.image.height() * factor))
        self.update()

    def enterEvent(self, event):
        self.cursor_pos = None
        self.update()

    def leaveEvent(self, event):
        self.cursor_pos = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.image is not None:
            self.history.append(self.mask_image.copy())
            if len(self.history) > 20:
                self.history.pop(0)
            self.drawing = True
            pos = event.pos()
            self.last_point = QPoint(int(pos.x() / self.scale_factor), int(pos.y() / self.scale_factor))

    def mouseMoveEvent(self, event):
        self.cursor_pos = event.pos()
        if (event.buttons() & Qt.LeftButton) and self.drawing and self.image is not None:
            painter = QPainter(self.mask_image)
            effective_size = max(1, int(self.brush_size / self.scale_factor))

            if self.eraser_mode:
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
                painter.setPen(QPen(Qt.transparent, effective_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            else:
                painter.setPen(QPen(QColor(255, 0, 0, 150), effective_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

            pos = event.pos()
            current_point = QPoint(int(pos.x() / self.scale_factor), int(pos.y() / self.scale_factor))
            painter.drawLine(self.last_point, current_point)
            self.last_point = current_point
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.image is not None:
            painter = QPainter(self)
            painter.scale(self.scale_factor, self.scale_factor)
            painter.drawImage(0, 0, self.image)
            if self.mask_image is not None:
                painter.drawImage(0, 0, self.mask_image)

            if self.cursor_pos is not None:
                painter.resetTransform()
                radius = int(self.brush_size / 2)

                painter.setPen(QPen(Qt.white, 2))
                painter.drawEllipse(self.cursor_pos, radius, radius)
                painter.setPen(QPen(Qt.black, 1))
                painter.drawEllipse(self.cursor_pos, radius, radius)

    def get_mask_array(self):
        if self.mask_image is None:
            return None

        w, h = self.mask_image.width(), self.mask_image.height()
        ptr = self.mask_image.constBits()
        ptr.setsize(self.mask_image.sizeInBytes())
        arr = np.array(ptr).reshape(h, w, 4)

        mask = np.zeros((h, w), dtype=np.uint8)
        mask[arr[:, :, 3] > 0] = 255
        return mask

    def undo(self):
        if self.history:
            self.mask_image = self.history.pop()
            self.update()

class CopyableTableWidget(QTableWidget):
    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            selection = self.selectedIndexes()
            if selection:
                rows = sorted(index.row() for index in selection)
                columns = sorted(index.column() for index in selection)
                if not rows or not columns:
                    return
                rowcount = rows[-1] - rows[0] + 1
                colcount = columns[-1] - columns[0] + 1
                table = [[''] * colcount for _ in range(rowcount)]
                for index in selection:
                    row = index.row() - rows[0]
                    column = index.column() - columns[0]
                    table[row][column] = str(index.data())
                stream = ''
                for i, row in enumerate(table):
                    stream += '\t'.join(row)
                    if i < len(table) - 1:
                        stream += '\n'
                from PyQt5.QtWidgets import QApplication
                QApplication.clipboard().setText(stream)
            return
        super().keyPressEvent(event)

class SingleTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        left_panel = QWidget()
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)

        self.btn_load = QPushButton("1. Load Image")
        self.btn_load.clicked.connect(self.load_image)

        zoom_layout = QHBoxLayout()
        self.btn_zoom_in = QPushButton("Zoom In")
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.btn_zoom_out = QPushButton("Zoom Out")
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.btn_fit = QPushButton("Fit to Screen")
        self.btn_fit.clicked.connect(self.fit_screen)
        zoom_layout.addWidget(self.btn_zoom_in)
        zoom_layout.addWidget(self.btn_zoom_out)
        zoom_layout.addWidget(self.btn_fit)

        tools_layout = QHBoxLayout()

        self.btn_brush = QPushButton("Brush")
        self.btn_brush.setCheckable(True)
        self.btn_brush.setChecked(True)
        self.btn_brush.toggled.connect(self.toggle_brush_mode)

        self.btn_eraser = QPushButton("Eraser")
        self.btn_eraser.setCheckable(True)

        self.tool_group = QButtonGroup()
        self.tool_group.addButton(self.btn_brush)
        self.tool_group.addButton(self.btn_eraser)

        tools_layout.addWidget(self.btn_brush)
        tools_layout.addWidget(self.btn_eraser)

        tools_layout.addWidget(QLabel("Brush Size:"))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(1)
        self.slider.setMaximum(500)
        self.slider.setValue(15)
        self.slider.valueChanged.connect(self.change_brush_size)
        tools_layout.addWidget(self.slider)

        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.clicked.connect(self.clear_mask)
        tools_layout.addWidget(self.btn_clear)

        self.scroll_area = QScrollArea()
        self.canvas = DrawableLabel()
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setWidgetResizable(True)

        left_layout.addWidget(self.btn_load)
        left_layout.addSpacing(10)
        left_layout.addLayout(zoom_layout)
        left_layout.addSpacing(10)
        left_layout.addLayout(tools_layout)
        left_layout.addSpacing(10)
        left_layout.addWidget(QLabel("Draw over the liquid region:"))
        left_layout.addWidget(self.scroll_area)

        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)

        self.btn_calc = QPushButton("2. Calculate Parameters")
        self.btn_calc.clicked.connect(self.calculate)
        self.btn_calc.setObjectName("primaryButton")

        self.table = CopyableTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.table.horizontalHeader().setStretchLastSection(True)

        self.btn_save = QPushButton("3. Export to Excel")
        self.btn_save.clicked.connect(self.save_excel)
        self.btn_save.setEnabled(False)
        self.btn_save.setObjectName("successButton")

        right_layout.addWidget(self.btn_calc)
        right_layout.addWidget(QLabel("Analysis Results (18 Params):"))
        right_layout.addWidget(self.table)
        right_layout.addWidget(self.btn_save)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([800, 350])

        layout.addWidget(splitter)
        self.setLayout(layout)

        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undo_shortcut.activated.connect(self.undo_mask)

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)")
        if file_path:
            image_bgr = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image_bgr is not None:
                import os
                self.current_filename = os.path.basename(file_path)
                self.canvas.set_image(image_bgr)
                self.fit_screen()
            else:
                QMessageBox.critical(self, "Error", "Cannot read image!")

    def change_brush_size(self):
        self.canvas.brush_size = self.slider.value()
        self.canvas.update()

    def toggle_brush_mode(self):
        self.canvas.eraser_mode = self.btn_eraser.isChecked()

    def zoom_in(self):
        self.canvas.update_scale(self.canvas.scale_factor * 1.2)

    def zoom_out(self):
        self.canvas.update_scale(self.canvas.scale_factor * 0.8)

    def fit_screen(self):
        if self.canvas.image:
            w, h = self.canvas.image.width(), self.canvas.image.height()
            view_w = self.scroll_area.width() - 25
            view_h = self.scroll_area.height() - 25
            if view_w > 0 and view_h > 0:
                scale = min(view_w / w, view_h / h)
                self.canvas.update_scale(scale)

    def clear_mask(self):
        if self.canvas.mask_image:
            self.canvas.history.append(self.canvas.mask_image.copy())
            self.canvas.mask_image.fill(Qt.transparent)
            self.canvas.update()
            self.table.setRowCount(0)

    def undo_mask(self):
        self.canvas.undo()

    def calculate(self):
        if self.canvas.image is None:
            QMessageBox.warning(self, "Warning", "Please load an image first.")
            return

        mask = self.canvas.get_mask_array()
        if cv2.countNonZero(mask) == 0:
            QMessageBox.warning(self, "Warning", "Please highlight the liquid region.")
            return

        stats = calculate_color_stats(self.canvas.original_bgr, mask)
        self.result_stats = stats
        self.btn_save.setEnabled(True)

        self.table.setRowCount(len(stats))
        for row, (k, v) in enumerate(stats.items()):
            self.table.setItem(row, 0, QTableWidgetItem(k))
            self.table.setItem(row, 1, QTableWidgetItem(str(v)))

    def save_excel(self):
        if hasattr(self, 'result_stats') and self.result_stats:
            import pandas as pd
            from datetime import datetime
            import os

            data = {'Image Name': getattr(self, 'current_filename', 'unknown')}
            data.update(self.result_stats)

            df = pd.DataFrame([data])

            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_without_ext = os.path.splitext(getattr(self, 'current_filename', 'result'))[0]
            default_filename = f"{current_time}_{filename_without_ext}.xlsx"

            save_path, _ = QFileDialog.getSaveFileName(self, "Save Excel File", default_filename, "Excel Files (*.xlsx)")
            if save_path:
                try:
                    df.to_excel(save_path, index=False)
                    QMessageBox.information(self, "Success", f"Results saved at:\n{save_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Cannot save file: {str(e)}")
