from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea,
    QPushButton, QHBoxLayout, QMdiSubWindow
)
from PySide6.QtCore import Qt
from ..services.pdf_service import create_pdf_view


class ReaderPage(QMdiSubWindow):
    """
    Cửa sổ đọc PDF dạng MDI:
    - Hiển thị số trang
    - Next / Prev = nhảy tới đầu trang tiếp theo
    - Zoom in / out = scale lại ảnh trang
    """
    def __init__(self, main_window, book):
        super().__init__(main_window)

        self.book = book
        self.main_window = main_window

        # state
        self.current_page = 0
        self.zoom_value = 1.0
        self.page_labels: list[QLabel] = []
        self.original_pixmaps = []

        self.setWindowTitle(book.title)
        self.resize(1000, 700)

        # ================== UI ROOT ==================
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # ---------------- Toolbar ----------------
        toolbar = QHBoxLayout()

        # nút back (đóng cửa sổ đọc)
        btn_back = QPushButton("← Trở lại")
        btn_back.clicked.connect(self.close)
        toolbar.addWidget(btn_back)

        # prev / next
        self.btn_prev = QPushButton("◀ Prev")
        self.btn_prev.clicked.connect(self.prev_page)
        toolbar.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Next ▶")
        self.btn_next.clicked.connect(self.next_page)
        toolbar.addWidget(self.btn_next)

        toolbar.addStretch()

        # label số trang
        self.lbl_page = QLabel("Page ? / ?")
        toolbar.addWidget(self.lbl_page)

        toolbar.addStretch()

        # zoom -
        self.btn_zoom_out = QPushButton("🔍 -")
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        toolbar.addWidget(self.btn_zoom_out)

        # zoom +
        self.btn_zoom_in = QPushButton("🔍 +")
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        toolbar.addWidget(self.btn_zoom_in)

        # label zoom %
        self.lbl_zoom = QLabel("100%")
        toolbar.addWidget(self.lbl_zoom)

        layout.addLayout(toolbar)

        # ---------------- PDF SCROLL ----------------
        # create_pdf_view hiện tại trả về một QScrollArea
        # bên trong chứa 1 QWidget + QVBoxLayout + nhiều QLabel (mỗi trang)
        self.pdf_scroll: QScrollArea = create_pdf_view(self, book.path)
        layout.addWidget(self.pdf_scroll, 1)

        self.setWidget(widget)
        self.show()

        # Sau khi đã có scroll, lấy danh sách các QLabel trang
        self._collect_pages()

        # Cập nhật UI lần đầu
        self.update_ui()

    # ======================================================
    # Thu thập danh sách các QLabel trang + lưu pixmap gốc
    # ======================================================
    def _collect_pages(self):
        self.page_labels.clear()
        self.original_pixmaps.clear()

        container = self.pdf_scroll.widget()
        if not container:
            return

        lay = container.layout()
        if not lay:
            return

        for i in range(lay.count()):
            item = lay.itemAt(i)
            w = item.widget()
            if isinstance(w, QLabel) and w.pixmap() is not None:
                self.page_labels.append(w)
                self.original_pixmaps.append(w.pixmap().copy())

        # Reset state nếu cần
        if self.page_labels:
            self.current_page = 0
        else:
            self.current_page = -1

    # ================== Helper UI ==================
    def update_ui(self):
        total = len(self.page_labels)
        if total <= 0:
            self.lbl_page.setText("Page ? / ?")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
        else:
            # đảm bảo current_page nằm trong [0, total-1]
            self.current_page = max(0, min(self.current_page, total - 1))
            self.lbl_page.setText(f"Page {self.current_page + 1} / {total}")
            self.btn_prev.setEnabled(self.current_page > 0)
            self.btn_next.setEnabled(self.current_page < total - 1)

        self.lbl_zoom.setText(f"{int(self.zoom_value * 100)}%")

    def _scroll_to_current_page(self):
        """Scroll đến đầu QLabel của trang current_page."""
        if not self.page_labels or self.current_page < 0:
            return

        label = self.page_labels[self.current_page]
        y = label.pos().y()
        bar = self.pdf_scroll.verticalScrollBar()
        bar.setValue(y)

    def _apply_zoom(self):
        """Scale lại toàn bộ các trang theo self.zoom_value."""
        if not self.page_labels or not self.original_pixmaps:
            return

        for lbl, orig in zip(self.page_labels, self.original_pixmaps):
            if orig is None:
                continue
            scaled = orig.scaled(
                int(orig.width() * self.zoom_value),
                int(orig.height() * self.zoom_value),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            lbl.setPixmap(scaled)

    # ================== Navigation ==================
    def next_page(self):
        total = len(self.page_labels)
        if total <= 0:
            return

        if self.current_page < total - 1:
            self.current_page += 1
            self._scroll_to_current_page()
            self.update_ui()

    def prev_page(self):
        total = len(self.page_labels)
        if total <= 0:
            return

        if self.current_page > 0:
            self.current_page -= 1
            self._scroll_to_current_page()
            self.update_ui()

    # ================== Zoom ==================
    def zoom_in(self):
        self.zoom_value += 0.1
        if self.zoom_value > 2.0:
            self.zoom_value = 2.0
        self._apply_zoom()
        self.update_ui()
        # giữ lại vị trí tương đối
        self._scroll_to_current_page()

    def zoom_out(self):
        self.zoom_value -= 0.1
        if self.zoom_value < 0.5:
            self.zoom_value = 0.5
        self._apply_zoom()
        self.update_ui()
        self._scroll_to_current_page()
