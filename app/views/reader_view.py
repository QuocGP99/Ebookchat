from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QMdiSubWindow,
    QTextBrowser,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QFrame,
    QApplication,
    QMenu,
)
from PySide6.QtGui import (
    QAction,
    QTextCursor,
    QTextCharFormat,
    QColor,
    QPixmap,
    QImage,
    QPainter,
    QTransform,
    QBrush,
    QLinearGradient,
    QPolygonF,
)
from PySide6.QtCore import (
    Qt,
    QTimer,
    QPointF,
    QRectF,
    QPropertyAnimation,
    QEasingCurve,
    QPoint,
    Property,
    QEvent,
    QRect,
)
from ebooklib import epub

from ..controllers.book_controller import load_book
from ..services.goal_service import goal_service
import fitz  # PyMuPDF


# ==========================================
# CLASS HIỆU ỨNG LẬT TRANG 3D (CẢI TIẾN)
# ==========================================
class PageFlipOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.hide()

        self.current_pixmap = None
        self.next_pixmap = None
        self.direction = 1
        self._progress = 0.0

        # Thêm biến lưu vùng vẽ và màu nền
        self.page_rect = QRect()
        self.bg_color = QColor(0, 0, 0, 0)

        self.anim = QPropertyAnimation(self, b"flip_progress", self)
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)
        self.anim.finished.connect(self.on_anim_finished)

        self.callback_finish = None

    @Property(float)
    def flip_progress(self):
        return self._progress

    @flip_progress.setter
    def flip_progress(self, val):
        self._progress = max(0.0, min(1.0, val))
        self.update()

    def start_flip(self, current_pix, next_pix, direction, rect, bg_color, callback):
        self.current_pixmap = current_pix
        self.next_pixmap = next_pix
        self.direction = direction
        self.page_rect = rect  # Vùng hiển thị trang sách
        self.bg_color = bg_color  # Màu nền xung quanh
        self.callback_finish = callback

        self.resize(self.parent().size())
        self.show()
        self.raise_()

        self._progress = 0.0
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def start_drag(self, current_pix, next_pix, direction, rect, bg_color, callback):
        self.current_pixmap = current_pix
        self.next_pixmap = next_pix
        self.direction = direction
        self.page_rect = rect
        self.bg_color = bg_color
        self.callback_finish = callback

        self.resize(self.parent().size())
        self.show()
        self.raise_()
        self._progress = 0.0
        self.update()

    def set_progress_manual(self, val):
        self.flip_progress = val

    def on_anim_finished(self):
        self.hide()
        if self.callback_finish:
            self.callback_finish()

    def paintEvent(self, event):
        if not self.current_pixmap or not self.next_pixmap:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # 1. Vẽ nền tĩnh (Màu xám/trắng bao quanh)
        painter.fillRect(self.rect(), self.bg_color)

        # 2. Dịch chuyển tọa độ vẽ vào vùng page_rect
        # Mọi thao tác lật trang chỉ diễn ra trong vùng này
        painter.translate(self.page_rect.topLeft())

        w = self.page_rect.width()
        h = self.page_rect.height()

        # Trang nền (nằm dưới)
        bg_pix = self.next_pixmap if self.direction == 1 else self.current_pixmap
        if bg_pix:
            painter.drawPixmap(0, 0, w, h, bg_pix)

        # Trang động (đang bay)
        fg_pix = self.current_pixmap if self.direction == 1 else self.next_pixmap

        if fg_pix:
            if self.direction == 1:  # Next (Lật từ phải sang trái)
                x_edge = w * (1.0 - self._progress)
                if x_edge > 1:
                    target_rect = QRectF(0, 0, x_edge, h)
                    painter.drawPixmap(target_rect.toRect(), fg_pix)

                    # Bóng đổ ở gáy
                    grad = QLinearGradient(x_edge, 0, x_edge - 40, 0)
                    grad.setColorAt(0, QColor(0, 0, 0, 60))
                    grad.setColorAt(1, QColor(0, 0, 0, 0))
                    painter.fillRect(QRectF(x_edge - 40, 0, 40, h), grad)

            else:  # Prev (Lật từ trái sang phải)
                x_edge = w * self._progress
                if x_edge > 1:
                    target_rect = QRectF(0, 0, x_edge, h)
                    painter.drawPixmap(target_rect.toRect(), fg_pix)

                    # Bóng đổ ở gáy
                    grad = QLinearGradient(x_edge, 0, x_edge - 40, 0)
                    grad.setColorAt(0, QColor(0, 0, 0, 60))
                    grad.setColorAt(1, QColor(0, 0, 0, 0))
                    painter.fillRect(QRectF(x_edge - 40, 0, 40, h), grad)


# ==========================================
# READER PAGE (MAIN)
# ==========================================
class ReaderPage(QMdiSubWindow):
    def __init__(self, main_window, book):
        super().__init__(main_window)
        self.book = book
        self.main_window = main_window
        self.setWindowTitle(f"{book.title} - {book.author}")
        self.resize(1200, 800)

        self.current_page_index = 0
        self.total_pages = 0
        self.pdf_doc = None
        self.zoom_level = 1.0
        self.page_scroll_offsets = {}  # Lưu vị trí scroll của từng trang PDF

        self.is_dragging = False
        self.drag_start_pos = QPoint()
        self.drag_direction = 0

        self.splitter = QSplitter(Qt.Horizontal)
        self.setWidget(self.splitter)

        # TOC
        self.toc_tree = QTreeWidget()
        self.toc_tree.setHeaderLabel("Mục lục")
        self.toc_tree.setFixedWidth(280)
        self.toc_tree.itemClicked.connect(self.on_toc_clicked)
        self.toc_tree.hide()
        self.splitter.addWidget(self.toc_tree)

        # RIGHT CONTAINER
        right_container = QWidget()
        self.right_layout = QVBoxLayout(right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)
        self.splitter.addWidget(right_container)

        self.is_pdf = book.ext == ".pdf"

        # TOOLBAR
        self._setup_toolbar()

        # CONTENT AREA
        self.content_area = QWidget()
        self.content_area.setMouseTracking(True)
        self.content_area.installEventFilter(self)

        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.addWidget(self.content_area, 1)

        # OVERLAY
        self.flip_overlay = PageFlipOverlay(self.content_area)
        self.flip_overlay.hide()
        # mini preview removed

        # FOOTER
        self._setup_footer()

        if self.is_pdf:
            self.setup_pdf_viewer()
        else:
            self.setup_epub_viewer()

        # Tải bookmark nếu tồn tại
        self.load_bookmark()

        self.read_timer = QTimer(self)
        self.read_timer.timeout.connect(self.on_reading_timer)
        self.read_timer.start(60000)

    # ... (Giữ nguyên setup_toolbar và setup_footer) ...
    def _setup_toolbar(self):
        toolbar_widget = QWidget()
        tb = QHBoxLayout(toolbar_widget)
        tb.setContentsMargins(10, 5, 10, 5)

        btn_toc = QPushButton("📑 Mục lục")
        btn_toc.clicked.connect(
            lambda: self.toc_tree.setVisible(not self.toc_tree.isVisible())
        )
        tb.addWidget(btn_toc)

        self.btn_mark = QPushButton("🔖 Bookmark")
        self.btn_mark.clicked.connect(self.toggle_bookmark)
        tb.addWidget(self.btn_mark)

        if not self.is_pdf:
            colors = [("Vàng", "#fef08a"), ("Xanh", "#bbf7d0"), ("Hồng", "#fbcfe8")]
            for name, code in colors:
                btn = QPushButton(name)
                btn.setStyleSheet(
                    f"background-color: {code}; border: 1px solid #ccc; padding: 5px; border-radius: 4px;"
                )
                btn.clicked.connect(
                    lambda c, color=code: self.highlight_selection(color)
                )
                tb.addWidget(btn)

        tb.addStretch()
        btn_zoom_out = QPushButton("🔍 -")
        btn_zoom_out.clicked.connect(lambda: self.change_zoom(-0.1))
        tb.addWidget(btn_zoom_out)

        btn_zoom_in = QPushButton("🔍 +")
        btn_zoom_in.clicked.connect(lambda: self.change_zoom(0.1))
        tb.addWidget(btn_zoom_in)

        self.lbl_reward = QLabel("⏳ Đang đọc...")
        tb.addWidget(self.lbl_reward)
        self.right_layout.addWidget(toolbar_widget)

    def _setup_footer(self):
        footer_widget = QFrame()
        footer_widget.setStyleSheet(
            "background: #f1f5f9; border-top: 1px solid #cbd5e1;"
        )
        fl = QHBoxLayout(footer_widget)
        fl.setContentsMargins(20, 10, 20, 10)

        self.btn_prev = QPushButton("◀ Trang trước")
        self.btn_prev.setFixedWidth(100)
        self.btn_prev.clicked.connect(self.prev_page_anim)
        self.btn_prev.setStyleSheet(
            "background-color: #2563eb; color: white; font-weight: bold;"
        )
        fl.addWidget(self.btn_prev)

        fl.addStretch()
        self.lbl_page_info = QLabel("Đang tải...")
        self.lbl_page_info.setStyleSheet(
            "font-weight: bold; font-size: 14px; color: #334155;"
        )
        fl.addWidget(self.lbl_page_info)
        fl.addStretch()

        self.btn_next = QPushButton("Trang sau ▶")
        self.btn_next.setFixedWidth(100)
        self.btn_next.clicked.connect(self.next_page_anim)
        self.btn_next.setStyleSheet(
            "background-color: #2563eb; color: white; font-weight: bold;"
        )
        fl.addWidget(self.btn_next)

        self.right_layout.addWidget(footer_widget)

    # --- SETUP VIEWERS ---
    def setup_pdf_viewer(self):
        try:
            self.pdf_doc = fitz.open(self.book.path)
            self.total_pages = self.pdf_doc.page_count
            self.load_pdf_toc()

            self.pdf_label = QLabel()
            self.pdf_label.setAlignment(Qt.AlignCenter)
            self.pdf_label.setStyleSheet("background: #525252;")
            self.pdf_label.setMouseTracking(True)
            self.content_layout.addWidget(self.pdf_label)

            self.render_pdf_page(0)
        except Exception as e:
            self.lbl_page_info.setText(f"Lỗi: {e}")

    def setup_epub_viewer(self):
        content = load_book(self.book)
        self.text_viewer = QTextBrowser()
        self.text_viewer.setHtml(content)
        self.text_viewer.setOpenExternalLinks(False)
        self.text_viewer.setStyleSheet(
            "QTextBrowser { padding:40px; font-size:18px; line-height:1.6; color: #1e293b; background-color: #ffffff; }"
        )
        self.text_viewer.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_viewer.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_viewer.installEventFilter(self)

        self.content_layout.addWidget(self.text_viewer)
        if self.book.ext == ".epub":
            self.load_epub_toc()
        self.update_footer_info()
        # Cập nhật nút bookmark khi viewer khởi tạo
        if hasattr(self, "btn_mark"):
            self.update_bookmark_button()
        # mini-preview removed

    # --- HELPERS: LẤY ẢNH VÀ VÙNG TRANG ---
    def get_page_geometry(self):
        """Trả về tuple (Pixmap, Rect của trang, Màu nền)"""
        if self.is_pdf:
            pix = self.pdf_label.pixmap()
            if not pix:
                return None, QRect(), QColor("#525252")

            # Tính toán vị trí trang trong content_area
            # Do pdf_label align center, ta tính thủ công
            cw = self.content_area.width()
            ch = self.content_area.height()
            pw = pix.width()
            ph = pix.height()
            x = (cw - pw) // 2
            y = (ch - ph) // 2

            return pix, QRect(x, y, pw, ph), QColor("#525252")
        else:
            # EPUB thì full màn hình
            pix = self.text_viewer.grab()
            return pix, self.content_area.rect(), QColor("#ffffff")

    def get_next_page_pixmap_hidden(self, step=1):
        """Lấy ảnh trang tiếp theo (chỉ phần nội dung)"""
        if self.is_pdf:
            target_idx = self.current_page_index + step
            if 0 <= target_idx < self.total_pages:
                page = self.pdf_doc.load_page(target_idx)
                mat = fitz.Matrix(self.zoom_level, self.zoom_level)
                pix = page.get_pixmap(matrix=mat)
                fmt = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt).copy()
                return QPixmap.fromImage(img)
            return None
        else:
            scrollbar = self.text_viewer.verticalScrollBar()
            old_val = scrollbar.value()
            page_h = self.text_viewer.viewport().height()

            target_val = old_val + (page_h * step)
            if target_val < 0 or target_val > scrollbar.maximum():
                return None

            scrollbar.setValue(target_val)
            QApplication.processEvents()
            pix = self.text_viewer.grab()  # Chỉ grab text_viewer
            scrollbar.setValue(old_val)
            return pix

    # --- ANIMATION LOGIC ---
    def next_page_anim(self):
        curr_pix, rect, bg_color = self.get_page_geometry()
        next_pix = self.get_next_page_pixmap_hidden(1)

        if next_pix and curr_pix:
            # Chỉ lật phần rect, nền xung quanh giữ nguyên bg_color
            self.flip_overlay.start_flip(
                curr_pix, next_pix, 1, rect, bg_color, self.finish_next_page
            )

    def prev_page_anim(self):
        curr_pix, rect, bg_color = self.get_page_geometry()
        prev_pix = self.get_next_page_pixmap_hidden(-1)

        if prev_pix and curr_pix:
            self.flip_overlay.start_flip(
                curr_pix, prev_pix, -1, rect, bg_color, self.finish_prev_page
            )

    def finish_next_page(self):
        if self.is_pdf:
            self.render_pdf_page(self.current_page_index + 1)
        else:
            sb = self.text_viewer.verticalScrollBar()
            sb.setValue(sb.value() + self.text_viewer.viewport().height())
            self.update_footer_info()

    def finish_prev_page(self):
        if self.is_pdf:
            self.render_pdf_page(self.current_page_index - 1)
        else:
            sb = self.text_viewer.verticalScrollBar()
            sb.setValue(sb.value() - self.text_viewer.viewport().height())
            self.update_footer_info()

    # --- DRAG EVENTS ---
    def eventFilter(self, source, event):
        # (preview removed) skip resize-specific preview handling
        # Xử lý zoom bằng Scroll chuột
        if event.type() == QEvent.Wheel:
            if event.angleDelta().y() > 0:
                # Scroll lên = Zoom in
                self.change_zoom(0.1)
            else:
                # Scroll xuống = Zoom out
                self.change_zoom(-0.1)
            return True

        # Xử lý double-click để reset zoom
        if event.type() == QEvent.MouseButtonDblClick:
            if event.button() == Qt.LeftButton:
                # Reset zoom về cỡ tiêu chuẩn
                self.zoom_level = 1.0
                if self.is_pdf:
                    self.page_scroll_offsets[self.current_page_index] = 0
                    self.render_pdf_page(self.current_page_index)
                else:
                    self.text_viewer.setZoomFactor(1.0)
                return True

        if event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.is_dragging = True
                self.drag_start_pos = event.pos()
                self.drag_direction = 0
                return False

        elif event.type() == QEvent.MouseMove:
            if self.is_dragging:
                diff_y = event.pos().y() - self.drag_start_pos.y()

                if self.is_pdf:
                    # PDF: Lật trang dựa trên drag X, cuộn dựa trên drag Y (tọa độ tuyệt đối)
                    diff_x = event.pos().x() - self.drag_start_pos.x()

                    # Ưu tiên drag Y để scroll nội dung nếu zoom in
                    if abs(diff_y) > 20 and self.zoom_level > 1.0:
                        # Scroll dựa trên vị trí Y tuyệt đối (không trượt)
                        page_h = self.content_area.height()
                        max_scroll = int(page_h * (self.zoom_level - 1.0))

                        # Tính vị trí scroll từ tọa độ Y hiện tại
                        position = (event.pos().y() / page_h) * max_scroll
                        position = max(0, min(max_scroll, int(position)))

                        self.page_scroll_offsets[self.current_page_index] = position
                        self.render_pdf_page(self.current_page_index)
                        return True
                    elif abs(diff_x) > 20:
                        # Lật trang
                        if self.drag_direction == 0:
                            curr_pix, rect, bg_color = self.get_page_geometry()

                            if diff_x < 0:  # Next
                                self.drag_direction = 1
                                self.drag_next_pix = self.get_next_page_pixmap_hidden(1)
                                if self.drag_next_pix:
                                    self.flip_overlay.start_drag(
                                        curr_pix,
                                        self.drag_next_pix,
                                        1,
                                        rect,
                                        bg_color,
                                        self.finish_next_page,
                                    )
                            else:  # Prev
                                self.drag_direction = -1
                                self.drag_prev_pix = self.get_next_page_pixmap_hidden(
                                    -1
                                )
                                if self.drag_prev_pix:
                                    self.flip_overlay.start_drag(
                                        curr_pix,
                                        self.drag_prev_pix,
                                        -1,
                                        rect,
                                        bg_color,
                                        self.finish_prev_page,
                                    )

                        if self.drag_direction != 0:
                            w = self.content_area.width()
                            prog = abs(diff_x) / w
                            self.flip_overlay.set_progress_manual(prog)
                            return True
                else:
                    # EPUB: Cuộn đến vị trí dựa trên Y
                    if abs(diff_y) > 10:
                        scrollbar = self.text_viewer.verticalScrollBar()
                        content_height = self.content_area.height()
                        max_scroll = scrollbar.maximum()

                        # Tính vị trí scroll dựa trên tọa độ Y
                        # Y = 0 là top, Y = content_height là bottom
                        position = (event.pos().y() / content_height) * max_scroll
                        position = max(0, min(max_scroll, int(position)))

                        scrollbar.setValue(position)
                        self.update_footer_info()
                        return True

        elif event.type() == QEvent.MouseButtonRelease:
            if self.is_dragging:
                self.is_dragging = False
                if self.is_pdf and self.drag_direction != 0:
                    current_prog = self.flip_overlay.flip_progress
                    if current_prog > 0.3:
                        self.flip_overlay.anim.setStartValue(current_prog)
                        self.flip_overlay.anim.setEndValue(1.0)
                        self.flip_overlay.anim.start()
                    else:
                        self.flip_overlay.anim.setStartValue(current_prog)
                        self.flip_overlay.anim.setEndValue(0.0)
                        self.flip_overlay.callback_finish = None
                        self.flip_overlay.anim.start()
                    self.drag_direction = 0
                    return True
        return super().eventFilter(source, event)

    # --- HELPERS CŨ (GIỮ NGUYÊN) ---
    def render_pdf_page(self, page_index):
        if not self.pdf_doc or page_index < 0 or page_index >= self.total_pages:
            return
        self.current_page_index = page_index
        page = self.pdf_doc.load_page(page_index)
        mat = fitz.Matrix(self.zoom_level, self.zoom_level)
        pix = page.get_pixmap(matrix=mat)
        fmt = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt).copy()

        # Áp dụng scroll offset nếu zoom in
        if self.zoom_level > 1.0:
            offset = self.page_scroll_offsets.get(page_index, 0)
            if offset > 0:
                # Cắt phần ảnh từ vị trí offset
                img = img.copy(0, offset, img.width(), img.height() - offset)

        self.pdf_label.setPixmap(QPixmap.fromImage(img))
        self.update_footer_info()
        # Cập nhật trạng thái bookmark khi thay đổi trang
        if hasattr(self, "btn_mark"):
            self.update_bookmark_button()

    def update_footer_info(self):
        if self.is_pdf:
            percent = (
                int((self.current_page_index + 1) / self.total_pages * 100)
                if self.total_pages > 0
                else 0
            )
            self.lbl_page_info.setText(
                f"Trang {self.current_page_index + 1} / {self.total_pages} ({percent}%)"
            )
            self.btn_prev.setEnabled(self.current_page_index > 0)
            self.btn_next.setEnabled(self.current_page_index < self.total_pages - 1)
        else:
            sb = self.text_viewer.verticalScrollBar()
            if sb.maximum() > 0:
                percent = int((sb.value() / sb.maximum()) * 100)
                # Ước tính số trang dựa trên scroll position
                self.lbl_page_info.setText(
                    f"Đã đọc {percent}% | Trang ≈ {max(1, int((sb.value() / sb.maximum()) * self.total_pages) + 1)}"
                )
            else:
                self.lbl_page_info.setText("Trang 1 | Đã đọc 0%")

    def change_zoom(self, delta):
        self.zoom_level += delta
        if self.zoom_level < 0.5:
            self.zoom_level = 0.5
        if self.zoom_level > 3.0:
            self.zoom_level = 3.0
        if self.is_pdf:
            # Reset scroll offset khi zoom lại
            if self.zoom_level <= 1.0:
                self.page_scroll_offsets[self.current_page_index] = 0
            self.render_pdf_page(self.current_page_index)
        else:
            if delta > 0:
                self.text_viewer.zoomIn(1)
            else:
                self.text_viewer.zoomOut(1)

    # preview was removed per user request

    def load_pdf_toc(self):
        if not self.pdf_doc:
            return
        toc = self.pdf_doc.get_toc()
        items = {0: self.toc_tree.invisibleRootItem()}
        for lvl, title, page in toc:
            parent = items.get(lvl - 1, items[0])
            item = QTreeWidgetItem(parent, [title])
            item.setData(0, Qt.UserRole, page)
            items[lvl] = item

    def load_epub_toc(self):
        try:
            book = epub.read_epub(self.book.path)

            def process_toc(toc_list, parent):
                for node in toc_list:
                    if isinstance(node, tuple):
                        section, children = node
                        item = QTreeWidgetItem(parent, [section.title])
                        item.setData(0, Qt.UserRole, section.href)
                        process_toc(children, item)
                    elif isinstance(node, epub.Link):
                        item = QTreeWidgetItem(parent, [node.title])
                        item.setData(0, Qt.UserRole, node.href)

            process_toc(book.toc, self.toc_tree.invisibleRootItem())
        except:
            pass

    def on_toc_clicked(self, item, col):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        if self.is_pdf:
            self.render_pdf_page(int(data) - 1)
        else:
            target = data.split("#")[0]
            self.text_viewer.scrollToAnchor(target)
            self.update_footer_info()

    def show_context_menu(self, pos):
        menu = QMenu()
        colors = [("Vàng", "#fef08a"), ("Xanh", "#bbf7d0"), ("Hồng", "#fbcfe8")]
        for name, code in colors:
            action = QAction(name, self)
            action.triggered.connect(
                lambda checked, c=code: self.highlight_selection(c)
            )
            menu.addAction(action)
        remove_action = QAction("❌ Xóa Highlight", self)
        remove_action.triggered.connect(lambda: self.highlight_selection(None))
        menu.exec(self.text_viewer.mapToGlobal(pos))

    def highlight_selection(self, color_code):
        cursor = self.text_viewer.textCursor()
        if not cursor.hasSelection():
            return
        fmt = QTextCharFormat()
        if color_code is None:
            fmt.setBackground(Qt.transparent)
        else:
            fmt.setBackground(QColor(color_code))
        cursor.mergeCharFormat(fmt)

    def on_reading_timer(self):
        goal_service.add_time(1)
        read, goal = goal_service.get_progress()
        self.lbl_reward.setText(f"📖 {read}/{goal} phút")
        if hasattr(self.main_window, "update_user_stats"):
            self.main_window.update_user_stats()

    def save_bookmark(self):
        import json
        import os

        data = {}
        try:
            with open("bookmarks.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            pass
        val = (
            self.current_page_index
            if self.is_pdf
            else self.text_viewer.verticalScrollBar().value()
        )
        data[self.book.path] = val
        with open("bookmarks.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.lbl_reward.setText("✅ Đã lưu vị trí!")

    def get_bookmarks_data(self):
        """Lấy dữ liệu bookmark từ file"""
        import json
        import os

        bookmarks_file = "bookmarks.json"
        if os.path.exists(bookmarks_file):
            try:
                with open(bookmarks_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_bookmarks_data(self, data):
        """Lưu dữ liệu bookmark vào file"""
        import json

        bookmarks_file = "bookmarks.json"
        try:
            with open(bookmarks_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.lbl_reward.setText(f"❌ Lỗi lưu bookmark: {e}")

    def get_current_position(self):
        """Lấy vị trí đọc hiện tại"""
        if self.is_pdf:
            return self.current_page_index
        else:
            return self.text_viewer.verticalScrollBar().value()

    def is_bookmarked(self):
        """Kiểm tra sách có được bookmark không"""
        data = self.get_bookmarks_data()
        return self.book.path in data

    def toggle_bookmark(self):
        """Bật/Tắt bookmark"""
        data = self.get_bookmarks_data()

        if self.is_bookmarked():
            # Xóa bookmark
            del data[self.book.path]
            self.lbl_reward.setText("📌 Đã xóa bookmark!")
        else:
            # Thêm bookmark
            position = self.get_current_position()
            data[self.book.path] = position
            self.lbl_reward.setText("✅ Đã lưu bookmark!")

        self.save_bookmarks_data(data)
        self.update_bookmark_button()

    def load_bookmark(self):
        """Tải vị trí đọc từ bookmark"""
        data = self.get_bookmarks_data()

        if self.book.path not in data:
            return

        position = data[self.book.path]

        try:
            if self.is_pdf:
                # Load trang PDF đã lưu
                if 0 <= position < self.total_pages:
                    self.render_pdf_page(position)
            else:
                # Load vị trí scroll của EPUB
                scrollbar = self.text_viewer.verticalScrollBar()
                scrollbar.setValue(position)
                self.update_footer_info()
        except Exception as e:
            print(f"Lỗi tải bookmark: {e}")

    def update_bookmark_button(self):
        """Cập nhật trạng thái hiển thị của nút bookmark"""
        if hasattr(self, "btn_mark"):
            if self.is_bookmarked():
                self.btn_mark.setStyleSheet(
                    "background-color: #f59e0b; color: white; font-weight: bold; border-radius: 4px;"
                )
            else:
                self.btn_mark.setStyleSheet(
                    "background-color: #6b7280; color: white; font-weight: bold; border-radius: 4px;"
                )
