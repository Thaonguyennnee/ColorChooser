from PyQt5.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget

from ui.batch_tab import BatchTab
from ui.single_tab import SingleTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("ColorChooser")
        self.resize(1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.tabs = QTabWidget()
        self.batch_tab = BatchTab()
        self.single_tab = SingleTab()

        self.tabs.addTab(self.batch_tab, "Batch Processing (Auto)")
        self.tabs.addTab(self.single_tab, "Single Image (Manual)")

        layout.addWidget(self.tabs)

        from PyQt5.QtWidgets import QHBoxLayout, QLabel
        watermark_layout = QHBoxLayout()

        cmit_label = QLabel("CMIT")
        cmit_label.setStyleSheet("color: #9CA3AF; font-size: 12px; font-weight: bold;")
        watermark_layout.addWidget(cmit_label)

        watermark_layout.addStretch()

        watermark_label = QLabel("Made by Nguyen")
        watermark_label.setStyleSheet("color: #9CA3AF; font-size: 12px; font-weight: normal; font-style: italic;")
        watermark_layout.addWidget(watermark_label)

        layout.addLayout(watermark_layout)
