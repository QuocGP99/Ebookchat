import sys
import os
from pathlib import Path
from PySide6.QtGui import QPalette, QColor, QAction, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QToolBar,
    QStatusBar,
    QMessageBox,
    QGridLayout,
    QFrame,
    QFileDialog,
    QCheckBox,
    QWidgetAction,
    QMenu,
)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QEvent
from .toggle_switch import ToggleSwitch
from ..services.cover_service import get_cover
from ..services.goal_service import goal_service
from ..models.book import Book
from .left_sidebar import LeftSidebar
from ..services.metadata_service import get_book_metadata


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


class BookCard(QWidget):
    def __init__(self, book, parent_window):
        super().__init__()
        self.book = book
        self.main_window = parent_window
        self.setFixedSize(160, 260)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Ảnh bìa
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(150, 210)
        self.lbl_thumb.setStyleSheet("border-radius: 6px; background: #e5e7eb;")
        self.lbl_thumb.setAlignment(Qt.AlignCenter)
        self.lbl_thumb.setScaledContents(True)

        # Tên sách
        self.lbl_title = QLabel(book.title)
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet(
            "font-weight: bold; font-size: 11px; color: #334155; border: none; background: transparent;"
        )

        layout.addWidget(self.lbl_thumb)
        layout.addWidget(self.lbl_title)

        self.load_image()

    def load_image(self):
        pix = self.main_window.get_book_pixmap(self.book)
        self.lbl_thumb.setPixmap(pix)

    def enterEvent(self, event):
        self.setStyleSheet("background-color: #e2e8f0; border-radius: 8px;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("background-color: transparent;")
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.main_window.open_book_reader(self.book)

    # --- MỚI: SỰ KIỆN CHUỘT PHẢI ĐỂ XÓA ---
    def contextMenuEvent(self, event):
        menu = QMenu(self)

        delete_action = QAction("🗑️ Xóa sách này", self)
        # Gọi hàm xóa mới trong MainWindow
        delete_action.triggered.connect(
            lambda: self.main_window.delete_book_direct(self.book)
        )

        menu.addAction(delete_action)
        menu.exec(event.globalPos())


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
        self.sidebar.searchChanged.connect(self.filter_books)
        layout.addWidget(self.sidebar)

        # CẤU HÌNH GALLERY CANH ĐỀU TRÁI TRÊN
        self.grid_container = QWidget()
        self.grid = QGridLayout(self.grid_container)
        self.grid.setSpacing(15)
        self.grid.setContentsMargins(20, 20, 20, 20)
        # Quan trọng: Đẩy các item dồn lên trên và sang trái
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

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

        self.placeholder = QLabel(
            """
            <h2>📚 EBook Reader</h2>
            <p style='color:#6b7280'>Chọn “Thêm sách” hoặc click vào thư viện bên trái để bắt đầu đọc.</p>
        """
        )
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

        toolbar.addSeparator()

        self.lbl_user_stats = QLabel()
        self.lbl_user_stats.setStyleSheet(
            "font-weight: bold; color: #2563eb; padding-left: 10px;"
        )
        toolbar.addWidget(self.lbl_user_stats)

        # Gọi cập nhật lần đầu
        self.update_user_stats()

    def update_user_stats(self):
        # HIỂN THỊ MỤC TIÊU
        read, goal = goal_service.get_progress()
        percent = int((read / goal) * 100) if goal > 0 else 100

        color = "#22c55e" if read >= goal else "#f59e0b"
        self.lbl_user_stats.setText(f"🎯 Hôm nay: {read}/{goal} phút ({percent}%)")
        self.lbl_user_stats.setStyleSheet(
            f"font-weight: bold; color: {color}; padding-left: 10px;"
        )

    # --- TÍNH NĂNG SEARCH ---
    def filter_books(self, text):
        text = text.lower().strip()

        # 1. Lọc trong Sidebar
        for i in range(self.sidebar.book_list.count()):
            item = self.sidebar.book_list.item(i)
            book = item.data(Qt.UserRole)
            # Tìm theo tên HOẶC tác giả
            is_match = text in book.title.lower() or text in book.author.lower()
            self.sidebar.book_list.setRowHidden(i, not is_match)

        # 2. Lọc trong Gallery (Cải tiến)
        for i in range(self.grid.count()):
            widget = self.grid.itemAt(i).widget()
            # Kiểm tra xem widget có phải là BookCard và có thuộc tính book không
            if widget and hasattr(widget, "book"):
                book = widget.book
                # Logic tìm kiếm giống hệt Sidebar
                is_match = text in book.title.lower() or text in book.author.lower()
                widget.setVisible(is_match)

    def delete_book_direct(self, book):
        """Xóa sách khi nhận được yêu cầu từ BookCard (Gallery)"""

        # Hộp thoại xác nhận (Tùy chọn, nếu muốn xóa nhanh thì bỏ qua)
        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa sách '{book.title}' không?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.No:
            return

        # 1. Xóa khỏi danh sách dữ liệu
        if book in self.books:
            self.books.remove(book)

        # 2. Xóa khỏi Sidebar (Phải tìm item tương ứng)
        # Duyệt qua các dòng trong sidebar để tìm sách cần xóa
        for i in range(self.sidebar.book_list.count()):
            item = self.sidebar.book_list.item(i)
            if item.data(Qt.UserRole) == book:
                self.sidebar.book_list.takeItem(i)
                break

        # 3. Cập nhật lại Gallery
        self.refresh_gallery()

        self.statusBar().showMessage(f"Đã xóa: {book.title}")

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

    def on_dark_switch_changed(self, state: int):
        app = QApplication.instance()  # IMPORTANT

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
            self, "Chọn file ebook", "", "Ebook (*.pdf *.txt *.epub *.mobi *.azw3)"
        )
        if not file:
            return

        # Kiểm tra trùng lặp
        for b in self.books:
            if b.path == file:
                QMessageBox.information(
                    self, "Đã tồn tại", "Sách này đã có trong thư viện!"
                )
                return

        title = Path(file).stem
        book = Book(title=title, path=file)

        # 1. Lấy Metadata (Author/Title chuẩn)
        meta = get_book_metadata(file, book.ext)
        book.author = meta["author"]
        if meta[
            "title"
        ]:  # Nếu trong file có title chuẩn thì dùng, ko thì dùng tên file
            book.title = meta["title"]

        # --- MỚI: Trích xuất cover ngay khi thêm sách ---
        # Nếu là PDF thì render sau, nếu là epub thì extract file ảnh
        extracted_cover = get_cover(book.path, book.ext)
        if extracted_cover:
            book.cover = extracted_cover

        self.books.append(book)
        self.sidebar.add_book(book)

        # Hiển thị Gallery nếu đang ẩn
        if self.grid_container.isHidden():
            self.placeholder.hide()
            self.grid_container.show()

        # Hiển thị sách lên lưới (Gallery)
        self.add_book_to_gallery(book)

        self.statusBar().showMessage(f"Đã thêm: {title}")

    def add_book_to_gallery(self, book):
        """Tạo một widget thẻ sách (Card) gồm Ảnh + Tên"""

        # Container cho 1 cuốn sách
        card = BookCard(book, self)
        count = self.grid.count()
        col = count % 5
        row = count // 5
        self.grid.addWidget(card, row, col)

        self.grid.setColumnStretch(5, 1)

    def get_book_pixmap(self, book):
        """Ưu tiên: Ảnh cover extract -> Render PDF -> Icon mặc định"""

        # 1. Nếu đã có cover path (từ EPUB/Mobi)
        if book.cover and os.path.exists(book.cover):
            return QPixmap(book.cover)

        # 2. Nếu là PDF (Render trang đầu)
        if book.ext == ".pdf":
            from PySide6.QtPdf import QPdfDocument

            try:
                doc = QPdfDocument(self)
                doc.load(book.path)
                if doc.status() == QPdfDocument.Status.Ready:
                    img = doc.render(0, QSize(300, 400))  # Render chất lượng tốt chút
                    return QPixmap.fromImage(img)
            except:
                pass

        # 3. Fallback: Icon mặc định theo đuôi file (Bạn có thể thêm icon txt.png, epub.png vào assets)
        # Ở đây mình tạo Pixmap màu chứa tên đuôi file
        pix = QPixmap(160, 220)
        pix.fill(QColor("#cbd5e1"))  # Màu xám sáng

        # Vẽ chữ lên ảnh placeholder (VD: "EPUB")
        from PySide6.QtGui import QPainter, QFont

        p = QPainter(pix)
        p.setPen(QColor("#475569"))
        font = QFont("Arial", 20, QFont.Bold)
        p.setFont(font)
        p.drawText(pix.rect(), Qt.AlignCenter, book.ext.upper())
        p.end()

        return pix

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
        thumb.setStyleSheet(
            """
            QLabel {
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                background: #ffffff;
            }
        """
        )

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
        # 1. Lấy object sách từ item
        book_to_delete = item.data(Qt.UserRole)

        # 2. Xóa khỏi danh sách dữ liệu thực (self.books)
        if book_to_delete in self.books:
            self.books.remove(book_to_delete)

        # 3. Xóa khỏi giao diện Sidebar
        self.sidebar.remove_book(item)

        # 4. Cập nhật lại Gallery
        self.refresh_gallery()

        self.statusBar().showMessage(f"Đã xóa sách: {book_to_delete.title}")

    def refresh_gallery(self):
        # Xóa toàn bộ card cũ
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Vẽ lại từ danh sách self.books mới
        for book in self.books:
            self.add_book_to_gallery(book)

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
