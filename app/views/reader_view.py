from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QPushButton,
    QHBoxLayout,
    QMdiSubWindow,
    QTextBrowser,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QColorDialog,
    QMenu,
)
from PySide6.QtGui import QAction, QTextCursor, QTextCharFormat, QColor, QIcon
from PySide6.QtCore import Qt, QTimer

from ..controllers.book_controller import load_book
from ..services.reward_service import reward_service
import fitz  # PyMuPDF cho TOC PDF


class ReaderPage(QMdiSubWindow):
    def __init__(self, main_window, book):
        super().__init__(main_window)
        self.book = book
        self.main_window = main_window
        self.setWindowTitle(f"{book.title} - {book.author}")
        self.resize(1200, 800)

        # === MAIN LAYOUT (SPLITTER) ===
        # Chia đôi màn hình: Trái (TOC) - Phải (Nội dung)
        self.splitter = QSplitter(Qt.Horizontal)
        self.setWidget(self.splitter)

        # --- LEFT: TABLE OF CONTENT (TOC) ---
        self.toc_tree = QTreeWidget()
        self.toc_tree.setHeaderLabel("Mục lục")
        self.toc_tree.setFixedWidth(250)
        self.toc_tree.itemClicked.connect(self.on_toc_clicked)
        self.toc_tree.hide()  # Ẩn mặc định, hiện nút toggle sau
        self.splitter.addWidget(self.toc_tree)

        # --- RIGHT: CONTENT AREA ---
        content_widget = QWidget()
        self.layout = QVBoxLayout(content_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.splitter.addWidget(content_widget)
        self.splitter.setStretchFactor(1, 4)  # Bên phải rộng gấp 4 lần

        # --- TOOLBAR ---
        self._setup_toolbar()

        # --- LOAD BOOK ---
        self.content_data = load_book(book)
        self.is_pdf = book.ext == ".pdf"

        if callable(self.content_data):  # PDF Wrapper
            self.pdf_scroll = self.content_data(self, book.path)
            self.layout.addWidget(self.pdf_scroll)
            # Load TOC PDF
            self.load_pdf_toc()
            # Logic PDF cũ (Back/Next) bạn giữ nguyên ở đây...

        else:  # TEXT (Epub, Mobi, Txt)
            self.text_viewer = QTextBrowser()
            self.text_viewer.setHtml(self.content_data)
            self.text_viewer.setOpenExternalLinks(False)
            self.text_viewer.setStyleSheet(
                "padding: 20px; font-size: 16px; line-height: 1.6;"
            )
            self.layout.addWidget(self.text_viewer)

            # Context Menu cho Highlight
            self.text_viewer.setContextMenuPolicy(Qt.CustomContextMenu)
            self.text_viewer.customContextMenuRequested.connect(self.show_context_menu)

            # Auto Generate TOC cho HTML (Quét thẻ H1, H2)
            # (Phần này nâng cao, tạm thời để trống hoặc quét regex)

        # --- GAMIFICATION ---
        self.read_timer = QTimer(self)
        self.read_timer.timeout.connect(self.on_reading_reward)
        self.read_timer.start(60000)

    def _setup_toolbar(self):
        tb = QHBoxLayout()
        self.layout.addLayout(tb)

        # Nút hiện/ẩn mục lục
        btn_toc = QPushButton("📑 Mục lục")
        btn_toc.clicked.connect(
            lambda: self.toc_tree.setVisible(not self.toc_tree.isVisible())
        )
        tb.addWidget(btn_toc)

        # Nút Bookmark (Lưu vị trí)
        btn_bookmark = QPushButton("🔖 Lưu Bookmark")
        btn_bookmark.clicked.connect(self.save_bookmark)
        tb.addWidget(btn_bookmark)

        if self.book.ext not in [".pdf"]:
            # Nút Highlight nhanh (Màu vàng)
            btn_hl = QPushButton("🖊️ Highlight")
            btn_hl.clicked.connect(self.highlight_selection)
            tb.addWidget(btn_hl)

        tb.addStretch()

        # Reward Label
        self.lbl_reward = QLabel("⏳ Reading...")
        tb.addWidget(self.lbl_reward)

    # tính năng mục lục PDF
    def load_pdf_toc(self):
        if not self.is_pdf:
            return
        try:
            doc = fitz.open(self.book.path)
            toc = doc.get_toc()  # [[lvl, title, page], ...]

            items = {}  # Map level để tạo cây
            # Root ảo
            items[0] = self.toc_tree.invisibleRootItem()

            for level, title, page in toc:
                parent = items.get(level - 1, items[0])
                item = QTreeWidgetItem(parent, [title])
                item.setData(0, Qt.UserRole, page)  # Lưu số trang vào data
                items[level] = item

            doc.close()
        except Exception as e:
            print("Lỗi TOC:", e)

    def on_toc_clicked(self, item, col):
        page_num = item.data(0, Qt.UserRole)
        if self.is_pdf and page_num:
            # Gọi hàm nhảy trang của PDF logic cũ
            # (Bạn cần cập nhật hàm _scroll_to_page tương ứng)
            self.current_page = page_num - 1
            if hasattr(self, "_scroll_to_current_page"):
                self._scroll_to_current_page()
                self.update_ui()

    # ==============================
    # 2. TÍNH NĂNG HIGHLIGHT (TEXT)
    # ==============================
    def show_context_menu(self, pos):
        menu = QMenu()
        hl_action = QAction("Tô đậm (Vàng)", self)
        hl_action.triggered.connect(self.highlight_selection)
        menu.addAction(hl_action)
        menu.exec(self.text_viewer.mapToGlobal(pos))

    def highlight_selection(self):
        if self.is_pdf:
            return

        cursor = self.text_viewer.textCursor()
        if not cursor.hasSelection():
            return

        # Tạo định dạng highlight
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#fef08a"))  # Màu vàng nhạt
        fmt.setForeground(Qt.black)

        cursor.mergeCharFormat(fmt)

    # ==============================
    # 3. TÍNH NĂNG BOOKMARK
    # ==============================
    def save_bookmark(self):
        # Đây là tính năng lưu trạng thái đơn giản
        # Trong thực tế bạn cần lưu vào JSON (giống reward_service)
        import json

        data = {}
        try:
            with open("bookmarks.json", "r") as f:
                data = json.load(f)
        except:
            pass

        # Lưu trang hiện tại (PDF) hoặc scroll (Text)
        val = (
            self.current_page
            if self.is_pdf
            else self.text_viewer.verticalScrollBar().value()
        )

        data[self.book.path] = val

        with open("bookmarks.json", "w") as f:
            json.dump(data, f)
        self.lbl_reward.setText("✅ Đã lưu vị trí!")

    def on_reading_reward(self):
        # (Logic cũ của bạn giữ nguyên)
        reward_service.add_exp(10)
        self.lbl_reward.setText(f"💎 +10 XP")

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
