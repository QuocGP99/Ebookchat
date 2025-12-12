import os
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QHBoxLayout,
    QLineEdit,
    QListWidgetItem,
    QMenu,
)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, Signal


class LeftSidebar(QWidget):
    # signals
    bookSelected = Signal(object)
    requestAddBook = Signal()
    requestDeleteBook = Signal(object)
    searchChanged = Signal(str)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # -------- LIBRARY header --------
        title = QLabel("Thư viện")
        title.setStyleSheet("font-size:16px;font-weight:600;")
        layout.addWidget(title)

        # SEARCH BOX
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Tìm kiếm sách…")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self.searchChanged.emit)

        icon_path = os.path.join(
            os.path.dirname(__file__), "../assets/icons/search.png"
        )
        self.search_box.addAction(QIcon(icon_path), QLineEdit.TrailingPosition)

        self.search_box.setStyleSheet(
            """
            QLineEdit {
                border:1px solid #d1d5db;
                border-radius: 8px;
                padding:6px 32px 6px 8px;
                background:#ffffff;
            }
            QLineEdit:focus{
                border:1px solid #3b82f6;
            }
        """
        )

        layout.addWidget(self.search_box)

        # sort button
        self.btn_sort = QPushButton("Sắp xếp A → Z")
        layout.addWidget(self.btn_sort)

        # ------ main list ------
        self.book_list = QListWidget()
        self.book_list.itemDoubleClicked.connect(self.on_double_click)

        # Thêm menu chuột phải để xóa
        self.book_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.book_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.book_list, 1)

        # ------ RECENT header ------
        recent_label = QLabel("Gần đây")
        recent_label.setStyleSheet("font-size:14px;")
        layout.addWidget(recent_label)

        self.recent_list = QListWidget()
        self.recent_list.itemDoubleClicked.connect(self.on_double_click_recent)
        layout.addWidget(self.recent_list, 1)

        # ------ bottom add button --------
        self.btn_add = QPushButton("➕ Thêm sách")
        self.btn_add.clicked.connect(self.requestAddBook.emit)
        self.btn_add.setStyleSheet(
            """
            background-color:#22c55e;
            color:white;padding:10px;
            border-radius:8px;
            font-weight:600;
        """
        )
        layout.addWidget(self.btn_add)

    # === HÀM HIỂN THỊ MENU CHUỘT PHẢI ===
    def show_context_menu(self, pos):
        item = self.book_list.itemAt(pos)
        if not item:
            return  # Nếu click vào vùng trắng thì bỏ qua

        menu = QMenu(self)

        # Tạo action Xóa
        delete_action = QAction("🗑️ Xóa sách này", self)
        delete_action.triggered.connect(lambda: self.requestDeleteBook.emit(item))
        menu.addAction(delete_action)

        # Hiển thị menu tại vị trí chuột
        menu.exec(self.book_list.mapToGlobal(pos))

    # ======================================================
    def add_book(self, book):
        # Tạo widget custom để hiển thị 2 dòng (Title + Author)
        item = QListWidgetItem()
        self.book_list.addItem(item)

        # Widget container
        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setContentsMargins(5, 5, 5, 5)
        vbox.setSpacing(2)

        # Title
        lbl_title = QLabel(book.title)
        lbl_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        vbox.addWidget(lbl_title)

        # Author
        lbl_author = QLabel(book.author)
        lbl_author.setStyleSheet("color: #64748b; font-size: 12px;")
        vbox.addWidget(lbl_author)

        item.setSizeHint(widget.sizeHint())
        self.book_list.setItemWidget(item, widget)

        # Lưu dữ liệu vào item để dùng khi click
        item.setData(Qt.UserRole, book)

    def add_recent(self, book):
        item = QListWidgetItem(book.title)
        item.setData(Qt.UserRole, book)
        self.recent_list.addItem(item)

    def remove_book(self, item):
        row = self.book_list.row(item)
        self.book_list.takeItem(row)

    # ======================================================
    def on_double_click(self, item):
        book = item.data(Qt.UserRole)
        self.bookSelected.emit(book)

    def on_double_click_recent(self, item):
        book = item.data(Qt.UserRole)
        self.bookSelected.emit(book)
