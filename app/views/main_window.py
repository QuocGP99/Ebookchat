import os
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem,
    QTextBrowser, QPushButton, QLabel,
    QFileDialog, QMessageBox, QToolBar, QStatusBar
)
from PySide6.QtGui import QAction, QFont, QPalette, QColor
from PySide6.QtCore import Qt

from ..models.book import Book


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SVBook Reader")
        self.resize(1100, 700)

        self.books: list[Book] = []
        self._dark_mode = False

        self._setup_ui()
        self._setup_actions()
        self._apply_light_theme()

    # ------------------------------
    # UI
    # ------------------------------
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # ===== Sidebar trái =====
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        self.lbl_library = QLabel("Thư viện")
        self.lbl_library.setFont(QFont("Segoe UI", 14, QFont.Bold))

        # --- Search box ---
        from PySide6.QtWidgets import QLineEdit
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Tìm sách…")
        self.search_box.textChanged.connect(self.filter_books)

        self.book_list = QListWidget()
        self.book_list.setAlternatingRowColors(True)
        self.book_list.itemDoubleClicked.connect(self.on_book_double_clicked)
        self.book_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: #f9fafb;
                border-radius: 12px;
                padding: 4px;
            }
        """)

        btn_row = QHBoxLayout()
        self.btn_add_book = QPushButton("➕ Thêm sách")
        self.btn_add_book.clicked.connect(self.add_book)

        self.btn_delete_book = QPushButton("🗑 Xóa sách")
        self.btn_delete_book.clicked.connect(self.delete_selected)

        btn_row.addWidget(self.btn_add_book)
        btn_row.addWidget(self.btn_delete_book)

        left_layout.addWidget(self.lbl_library)
        left_layout.addWidget(self.search_box)
        left_layout.addWidget(self.book_list, 1)
        left_layout.addLayout(btn_row)

        left_panel.setFixedWidth(260)
        left_panel.setStyleSheet("""
            QWidget {
                background-color: #f3f4f6;
                border-radius: 16px;
            }
        """)

        # ===== Trang chủ placeholder =====
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(60, 60, 60, 60)

        placeholder = QLabel("""
        <h2>📚 SVBook Reader</h2>
        <p style='color:#6b7280'>
            Chọn sách bên trái để bắt đầu đọc.
        </p>
        """)
        placeholder.setAlignment(Qt.AlignCenter)

        right_layout.addStretch()
        right_layout.addWidget(placeholder)
        right_layout.addStretch()

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)

        # ===== Toolbar =====
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        self.action_toggle_theme = QAction("Dark mode", self)
        self.action_delete = QAction("Xóa sách", self)

        toolbar.addAction(self.action_toggle_theme)
        toolbar.addAction(self.action_delete)

        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Sẵn sàng")
   
    # ------------------------------
    # Actions
    # ------------------------------
    def _setup_actions(self):
        self.action_toggle_theme.triggered.connect(self.toggle_theme)
        self.action_delete.triggered.connect(self.delete_selected)

    # ------------------------------
    # Thêm sách
    # ------------------------------
    def add_book(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file ebook",
            "",
            "Ebook (*.epub *.txt *.md *.pdf *.mobi *.azw3);;Tất cả các file (*.*)",
        )
        if not file_path:
            return

        # check duplicates
        for b in self.books:
            if b.path == file_path:
                QMessageBox.information(self, "Đã tồn tại", "Sách này đã được thêm!")
                return

        title = Path(file_path).stem
        book = Book(title=title, path=file_path)
        self.books.append(book)

        item = QListWidgetItem(title)
        item.setData(Qt.UserRole, book)
        self.book_list.addItem(item)

        self.statusBar().showMessage(f"Đã thêm: {title}")

        self.open_book_reader(book)

    # ------------------------------
    # Double-click
    # ------------------------------
    def on_book_double_clicked(self, item):
        book = item.data(Qt.UserRole)
        if isinstance(book, Book):
            self.open_book_reader(book)

    # ------------------------------
    # Open ReaderPage
    # ------------------------------
    def open_book_reader(self, book: Book):
        from .reader_view import ReaderPage
        reader = ReaderPage(self, book)
        reader.show()

        
        print(">> OPENING:", book.path)

    # ------------------------------
    # Xóa sách
    # ------------------------------
    def delete_selected(self):
        item = self.book_list.currentItem()
        if not item:
            return

        row = self.book_list.row(item)
        book = self.books[row]

        self.book_list.takeItem(row)
        del self.books[row]

        self.statusBar().showMessage("Đã xóa sách")

    # ------------------------------
    # Theme
    # ------------------------------
    def _apply_light_theme(self):
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor("#e5e7eb"))
        pal.setColor(QPalette.Base, QColor("#f9fafb"))
        pal.setColor(QPalette.Text, Qt.black)
        pal.setColor(QPalette.WindowText, Qt.black)
        self.setPalette(pal)

    def _apply_dark_theme(self):
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor("#020617"))
        pal.setColor(QPalette.Base, QColor("#020617"))
        pal.setColor(QPalette.Text, QColor("#e5e7eb"))
        pal.setColor(QPalette.WindowText, QColor("#e5e7eb"))
        self.setPalette(pal)

    def toggle_theme(self):
        self._dark_mode = not self._dark_mode
        if self._dark_mode:
            self._apply_dark_theme()
        else:
            self._apply_light_theme()

    def filter_books(self, text):
        for i in range(self.book_list.count()):
            item = self.book_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())


# ==============================
# Entry point
# ==============================
def run_app():
    app = QApplication(sys.argv)
    app.setApplicationName("EBook Reader")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
