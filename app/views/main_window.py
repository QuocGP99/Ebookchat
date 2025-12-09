import sys
from PySide6.QtGui import QPalette, QColor
from .toggle_switch import ToggleSwitch


# ======================
# THEME CSS
# ======================
DARK_CSS = """
QWidget {
    background-color: #0f172a;
    color: #e2e8f0;
    border: none;
}
QMainWindow {
    background-color:#0f172a;
}
QFrame {
    background: #1e293b;
}
QLabel {
    color: #e2e8f0;
}
QListWidget {
    background: #020617;
    color: #e2e8f0;
    border: none;
}
QLineEdit {
    background: #020617;
    color: #e2e8f0;
    border-radius: 8px;
    padding: 8px;
    border: 1px solid #1e293b;
}
QToolBar {
    background: #020617;
    border-bottom: 1px solid #1e293b;
}
QStatusBar {
    background: #020617;
    color: #e2e8f0;
    border-top: 1px solid #1e293b;
}
QPushButton {
    background: #334155;
    color: #e2e8f0;
    border-radius: 6px;
    padding: 6px 10px;
}
QPushButton:hover {
    background: #475569;
}
"""

LIGHT_CSS = """
QWidget {
    background-color: #f8fafc;
    color: #1e293b;
}
QMainWindow {
    background-color:#f8fafc;
}
QListWidget {
    background: #ffffff;
    color: #111827;
}
QLineEdit {
    background: #ffffff;
    border-radius: 8px;
    padding: 8px;
    border: 1px solid #d1d5db;
}
QToolBar {
    background: #ffffff;
    border-bottom: 1px solid #e5e7eb;
}
QStatusBar {
    background: #ffffff;
    color: #1f2933;
    border-top: 1px solid #e5e7eb;
}
QPushButton {
    background: #2563eb;
    color: #ffffff;
    border-radius: 6px;
    padding: 6px 10px;
}
QPushButton:hover {
    background: #1d4ed8;
}
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QLabel, QToolBar, QStatusBar, QMessageBox,
    QGridLayout, QFrame, QFileDialog, QCheckBox, QWidgetAction
)
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve

from ..models.book import Book
from .left_sidebar import LeftSidebar



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("EBook Reader")
        self.resize(1100, 700)

        self.books: list[Book] = []
        self._current_anim = None

        self._setup_ui()
        self._setup_toolbar()


    # ------------------------------
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === sidebar
        self.sidebar = LeftSidebar()
        self.sidebar.bookSelected.connect(self.open_book_reader)
        self.sidebar.requestAddBook.connect(self.add_book)
        self.sidebar.requestDeleteBook.connect(self.delete_selected)
        layout.addWidget(self.sidebar)

        # ---- Vertical separator ----
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setStyleSheet("background:#e5e7eb; width:1px;")
        layout.addWidget(line)

        # === main content
        content = QWidget()
        layout_right = QHBoxLayout(content)
        layout_right.setContentsMargins(0, 0, 0, 0)

        self.grid_container = QWidget()
        self.grid = QGridLayout(self.grid_container)
        self.grid.setSpacing(14)
        self.grid.setContentsMargins(40, 40, 40, 40)

        self.placeholder = QLabel("""
            <h2>📚 EBook Reader</h2>
            <p style='color:#6b7280'>Chọn “Thêm sách” hoặc click vào thư viện bên trái để bắt đầu đọc.</p>
        """)
        self.placeholder.setAlignment(Qt.AlignCenter)

        layout_right.addWidget(self.placeholder)
        layout_right.addWidget(self.grid_container)
        self.grid_container.hide()

        layout.addWidget(content, 1)

        # status
        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Sẵn sàng")

    # ------------------------------
    def _setup_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        self.dark_switch = ToggleSwitch(self)
        self.dark_switch.toggled.connect(self.on_toggle_switch)

        switch_action = QWidgetAction(self)
        switch_action.setDefaultWidget(self.dark_switch)
        toolbar.addAction(switch_action)


    def on_toggle_switch(self, checked: bool):
        app = QApplication.instance()

        if checked:
            app.setStyleSheet(DARK_CSS)
            self.statusBar().showMessage("Dark mode ON")
        else:
            app.setStyleSheet(LIGHT_CSS)
            self.statusBar().showMessage("Dark mode OFF")

        self.fade_theme()

    # ------------------------------
    # THEME
    # ------------------------------
    def fade_theme(self):
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(400)
        anim.setStartValue(0.5)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()
        self._current_anim = anim

    def on_dark_switch_changed(self, state:int):
        app = QApplication.instance()   # IMPORTANT

        if state == Qt.Checked:
            app.setStyleSheet(DARK_CSS)
            self.statusBar().showMessage("Dark mode ON")
        else:
            app.setStyleSheet(LIGHT_CSS)
            self.statusBar().showMessage("Dark mode OFF")

        self.fade_theme()


    # ------------------------------
    # Add Book
    # ------------------------------
    def add_book(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Chọn file ebook", "",
            "Ebook (*.pdf *.txt *.epub *.mobi *.azw3)"
        )
        if not file:
            return

        for b in self.books:
            if b.path == file:
                QMessageBox.information(self, "Đã tồn tại",
                                        "Sách này đã có trong thư viện!")
                return

        title = Path(file).stem
        book = Book(title=title, path=file)

        self.books.append(book)
        self.sidebar.add_book(book)
        self.sidebar.add_recent(book)

        if self.grid_container.isHidden():
            self.placeholder.hide()
            self.grid_container.show()

        self.show_thumbnail(book)

        self.statusBar().showMessage(f"Đã thêm: {title}")

    # ------------------------------
    def show_thumbnail(self, book):
        thumb = QLabel()
        pix = self.make_thumbnail(book)

        if pix.isNull():
            pix = QPixmap("assets/default.png")
            if pix.isNull():
                pix = QPixmap(160, 220)
                pix.fill(Qt.lightGray)

        pix = pix.scaled(160, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        thumb.setPixmap(pix)
        thumb.setFixedSize(160, 220)
        thumb.setScaledContents(True)
        thumb.setStyleSheet("""
            QLabel {
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                background: #ffffff;
            }
        """)

        count = self.grid.count()
        col = count % 4
        row = count // 4
        self.grid.addWidget(thumb, row, col)

    # ------------------------------
    def make_thumbnail(self, book):
        from PySide6.QtPdf import QPdfDocument
        try:
            if book.path.lower().endswith(".pdf"):
                doc = QPdfDocument(self)
                if doc.load(book.path) == QPdfDocument.Status.NoError:
                    img = doc.render(0, QSize(160, 220))
                    pix = QPixmap.fromImage(img)
                    if not pix.isNull():
                        return pix
            return QPixmap("assets/file-pdf.png")

        except:
            return QPixmap("assets/default.png")

    # ------------------------------
    def delete_selected(self, item):
        self.sidebar.remove_book(item)

    def open_book_reader(self, book: Book):
        from .reader_view import ReaderPage
        reader = ReaderPage(self, book)
        reader.show()


# ======================
# RUN APP (IMPORTANT ORDER)
# ======================
def run_app():
    app = QApplication(sys.argv)

    # set initial theme FIRST
    app.setStyleSheet(LIGHT_CSS)

    win = MainWindow()
    win.setWindowOpacity(0.98)
    win.show()
    sys.exit(app.exec())
