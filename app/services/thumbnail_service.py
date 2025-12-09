from PySide6.QtPdf import QPdfDocument, QPdfDocumentRenderOptions
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QSize


def generate_pdf_thumbnail(pdf_path: str, size: QSize = QSize(200, 260)) -> QPixmap:
    doc = QPdfDocument()
    status = doc.load(pdf_path)

    if status != QPdfDocument.Status.Ready:
        return QPixmap()   # return null pixmap

    if doc.pageCount() == 0:
        return QPixmap()

    img = QImage(size, QImage.Format_ARGB32)
    img.fill(0xffffffff)

    opt = QPdfDocumentRenderOptions()
    doc.render(0, img, opt)

    return QPixmap.fromImage(img)
