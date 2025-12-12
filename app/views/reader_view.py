from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QPushButton,
    QHBoxLayout,
    QMdiSubWindow,
    QTextBrowser,
)
from PySide6.QtCore import Qt, QTimer
from ..services.pdf_service import create_pdf_view
from ..controllers.book_controller import load_book
from ..services.reward_service import reward_service


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

        # Nút Back
        btn_back = QPushButton("← Trở lại")
        btn_back.clicked.connect(self.close)
        toolbar.addWidget(btn_back)

        # Biến kiểm tra có phải PDF không
        is_pdf = book.ext == ".pdf"

        # Các nút điều hướng chỉ hiện nếu là PDF
        if is_pdf:
            self.btn_prev = QPushButton("◀ Prev")
            self.btn_prev.clicked.connect(self.prev_page)
            toolbar.addWidget(self.btn_prev)

            self.btn_next = QPushButton("Next ▶")
            self.btn_next.clicked.connect(self.next_page)
            toolbar.addWidget(self.btn_next)

        toolbar.addStretch()

        # --- Label hiển thị phần thưởng ---
        self.lbl_reward = QLabel("⏳ Đang đọc...")
        self.lbl_reward.setStyleSheet("color: #16a34a; font-weight: bold;")
        toolbar.addWidget(self.lbl_reward)

        toolbar.addStretch()

        # Nút Zoom (Chỉ hiện nếu là PDF)
        if is_pdf:
            self.lbl_page = QLabel("Page ? / ?")
            toolbar.addWidget(self.lbl_page)

            self.btn_zoom_out = QPushButton("🔍 -")
            self.btn_zoom_out.clicked.connect(self.zoom_out)
            toolbar.addWidget(self.btn_zoom_out)

            self.btn_zoom_in = QPushButton("🔍 +")
            self.btn_zoom_in.clicked.connect(self.zoom_in)
            toolbar.addWidget(self.btn_zoom_in)

            self.lbl_zoom = QLabel("100%")
            toolbar.addWidget(self.lbl_zoom)

        layout.addLayout(toolbar)

        # ---------------- CONTENT LOAD ----------------
        # Dùng book_controller để lấy nội dung
        content_data = load_book(book)

        if callable(content_data):
            # === TRƯỜNG HỢP PDF ===
            # content_data là hàm create_pdf_view trả về QScrollArea
            self.pdf_scroll = content_data(self, book.path)
            layout.addWidget(self.pdf_scroll, 1)

            # Logic PDF cũ
            self._collect_pages()
            self.update_ui()

        else:
            # === TRƯỜNG HỢP TEXT / EPUB ===
            # content_data là chuỗi HTML
            self.text_viewer = QTextBrowser()
            self.text_viewer.setHtml(content_data)
            self.text_viewer.setOpenExternalLinks(False)
            self.text_viewer.setStyleSheet(
                "font-size: 16px; padding: 10px; background: white;"
            )
            layout.addWidget(self.text_viewer, 1)

        self.setWidget(widget)
        self.show()

        # ---------------- GAMIFICATION TIMER ----------------
        # 60 giây (60000 ms) thưởng 1 lần
        self.read_timer = QTimer(self)
        self.read_timer.timeout.connect(self.on_reading_reward)
        self.read_timer.start(60000)

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

    def on_reading_reward(self):
        # Cộng 10 điểm mỗi phút
        leveled_up = reward_service.add_exp(10)

        cur_lvl = reward_service.get_level()
        cur_exp = reward_service.get_exp()

        if leveled_up:
            self.lbl_reward.setText(f"🎉 LÊN CẤP {cur_lvl}! (+10 XP)")
        else:
            self.lbl_reward.setText(f"💎 +10 XP (Tổng: {cur_exp})")

        # Cập nhật hiển thị ở màn hình chính nếu cần
        if hasattr(self.main_window, "update_user_stats"):
            self.main_window.update_user_stats()
