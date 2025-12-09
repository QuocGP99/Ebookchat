from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QPushButton, QHBoxLayout, QMdiSubWindow
from PySide6.QtCore import Qt
from ..services.pdf_service import create_pdf_view

class ReaderPage(QMdiSubWindow):
    """
    Reader mở như cửa sổ con trong MainWindow (MDI).
    """
    def __init__(self, main_window, book):
        super().__init__(main_window)

        self.book = book
        self.setWindowTitle(book.title)
        self.resize(1000, 700)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        toolbar = QHBoxLayout()
        btn_back = QPushButton("← Trở lại")
        btn_back.clicked.connect(self.close)
        toolbar.addWidget(btn_back, alignment=Qt.AlignLeft)

        title = QLabel(book.title)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:18px;font-weight:bold;")
        toolbar.addWidget(title)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.pdf_area = QScrollArea()
        self.pdf_area.setWidgetResizable(True)
        layout.addWidget(self.pdf_area)

        viewer = create_pdf_view(self, book.path)
        self.pdf_area.setWidget(viewer)

        self.setWidget(widget)
        self.show()