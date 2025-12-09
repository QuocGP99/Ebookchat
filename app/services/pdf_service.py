import fitz  # PyMuPDF
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt


def create_pdf_view(parent: QWidget, path: str):
    """
    Continuous PDF view, auto-fit width,
    giống lướt sách.
    """
    scroll = QScrollArea(parent)
    scroll.setWidgetResizable(True)

    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    try:
        doc = fitz.open(path)
    except Exception as e:
        layout.addWidget(QLabel(f"Lỗi mở PDF: {e}"))
        scroll.setWidget(container)
        return scroll

    if doc.page_count == 0:
        layout.addWidget(QLabel("PDF không có nội dung"))
        scroll.setWidget(container)
        return scroll

    # ---- Auto zoom theo chiều rộng cửa sổ ----
    first = doc.load_page(0)
    w = first.rect.width

    target_width = max(parent.width() - 80, 600)
    zoom = target_width / w
    zoom = max(0.8, min(zoom, 1.6))   # tránh phóng quá to

    mat = fitz.Matrix(zoom, zoom)

    # ---- Render mỗi trang ----
    for i in range(doc.page_count):
        try:
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=mat)

            fmt = (
                QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
            )
            img = QImage(
                pix.samples, pix.width, pix.height,
                pix.stride, fmt
            ).copy()
            pixmap = QPixmap.fromImage(img)

            lbl = QLabel()
            lbl.setPixmap(pixmap)
            lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl)

        except Exception as e:
            layout.addWidget(QLabel(f"Lỗi trang {i+1}: {e}"))

    scroll.setWidget(container)
    return scroll
