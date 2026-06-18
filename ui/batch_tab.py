import os
import cv2
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QFileDialog, QProgressBar, QListWidget,
                             QMessageBox, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

from core.detector import detect_tube
from core.color_analyzer import calculate_color_stats

class BatchWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    preview = pyqtSignal(object)
    finished = pyqtSignal(object)

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path

    def run(self):
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
        files = [f for f in os.listdir(self.folder_path) if f.lower().endswith(valid_extensions)]

        if not files:
            self.log.emit("No images found in the directory!")
            self.finished.emit(None)
            return

        results = []
        total = len(files)

        for i, file_name in enumerate(files):
            file_path = os.path.join(self.folder_path, file_name)
            self.log.emit(f"Processing: {file_name}")

            image = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                self.log.emit(f"Error: Cannot read image {file_name}")
                continue

            mask, bbox = detect_tube(image)

            if mask is not None:
                stats = calculate_color_stats(image, mask)

                ordered_stats = {'Filename': file_name}
                ordered_stats.update(stats)
                results.append(ordered_stats)

                preview_image = image.copy()
                mask_indices = mask > 0
                overlay = np.zeros_like(preview_image)
                overlay[mask_indices] = (0, 255, 0)

                alpha = 0.5
                preview_image[mask_indices] = cv2.addWeighted(preview_image, 1 - alpha, overlay, alpha, 0)[mask_indices]

                self.preview.emit((file_name, preview_image))
            else:
                self.log.emit(f"Warning: Could not detect liquid region in {file_name}")

            self.progress.emit(int((i + 1) / total * 100))

        if results:
            df = pd.DataFrame(results)
            self.finished.emit(df)
        else:
            self.finished.emit(None)

class BatchTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.folder_path = ""
        self.result_df = None

    def init_ui(self):
        layout = QHBoxLayout()

        left_panel = QWidget()
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)

        self.btn_select_folder = QPushButton("1. Select Image Folder")
        self.btn_select_folder.clicked.connect(self.select_folder)

        self.lbl_folder = QLabel("No folder selected")
        self.lbl_folder.setWordWrap(True)

        self.btn_process = QPushButton("2. Start Processing")
        self.btn_process.clicked.connect(self.start_processing)
        self.btn_process.setEnabled(False)
        self.btn_process.setObjectName("primaryButton")

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.log_list = QListWidget()

        self.btn_save = QPushButton("3. Export to Excel")
        self.btn_save.clicked.connect(self.save_excel)
        self.btn_save.setEnabled(False)
        self.btn_save.setObjectName("successButton")

        left_layout.addWidget(self.btn_select_folder)
        left_layout.addWidget(self.lbl_folder)
        left_layout.addSpacing(15)
        left_layout.addWidget(self.btn_process)
        left_layout.addWidget(self.progress_bar)
        left_layout.addSpacing(15)
        left_layout.addWidget(QLabel("Process Logs:"))
        left_layout.addWidget(self.log_list)
        left_layout.addSpacing(15)
        left_layout.addWidget(self.btn_save)

        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)

        self.preview_list = QListWidget()
        self.preview_list.setViewMode(QListWidget.IconMode)
        from PyQt5.QtCore import QSize
        self.preview_list.setIconSize(QSize(250, 250))
        self.preview_list.setResizeMode(QListWidget.Adjust)
        self.preview_list.setSpacing(10)

        right_layout.addWidget(QLabel("Processed Images (with masks):"))
        right_layout.addWidget(self.preview_list, 1)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 800])

        layout.addWidget(splitter)
        self.setLayout(layout)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.folder_path = folder
            self.lbl_folder.setText(f"Folder: {folder}")
            self.btn_process.setEnabled(True)
            self.log_list.clear()
            self.progress_bar.setValue(0)
            self.btn_save.setEnabled(False)

    def start_processing(self):
        self.btn_process.setEnabled(False)
        self.btn_select_folder.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.log_list.clear()
        self.preview_list.clear()

        self.worker = BatchWorker(self.folder_path)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.log_list.addItem)
        self.worker.preview.connect(self.update_preview)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.start()

    def update_preview(self, data):
        file_name, image_bgr = data

        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        h, w = image_rgb.shape[:2]
        max_dim = 300
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            image_rgb = cv2.resize(image_rgb, (int(w * scale), int(h * scale)))
            h, w = image_rgb.shape[:2]

        bytes_per_line = 3 * w
        q_img = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)

        from PyQt5.QtGui import QIcon
        from PyQt5.QtWidgets import QListWidgetItem

        icon = QIcon(pixmap)
        item = QListWidgetItem(icon, file_name)

        item.setTextAlignment(Qt.AlignCenter)

        self.preview_list.addItem(item)

    def on_processing_finished(self, df):
        self.btn_process.setEnabled(True)
        self.btn_select_folder.setEnabled(True)

        if df is not None and not df.empty:
            self.result_df = df
            self.btn_save.setEnabled(True)
            self.log_list.addItem(f"Complete! Successfully processed {len(df)} images.")
            QMessageBox.information(self, "Success", f"Batch processing complete!\nDetected {len(df)} images.")
        else:
            self.log_list.addItem("No result data (nothing detected).")

    def save_excel(self):
        if self.result_df is not None:
            from datetime import datetime
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = os.path.basename(self.folder_path)
            if not folder_name:
                folder_name = "folder"
            default_filename = f"{current_time}_{folder_name}.xlsx"

            save_path, _ = QFileDialog.getSaveFileName(self, "Save Excel File", default_filename, "Excel Files (*.xlsx)")
            if save_path:
                try:
                    self.result_df.to_excel(save_path, index=False)
                    QMessageBox.information(self, "Success", f"Results saved at:\n{save_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Cannot save file: {str(e)}")
