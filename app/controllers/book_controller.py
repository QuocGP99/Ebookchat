from ..services.txt_service import read_txt
from ..services.pdf_service import create_pdf_view
from ..services.epub_service import read_epub
from ..services.mobi_service import read_mobi
from ..services.cover_service import get_cover


def load_book(book):
    # PDF xử lý riêng (viewer), return widget cho UI xử lý
    if book.ext == ".pdf":
        return create_pdf_view

    # các loại text => trả lại chuỗi HTML
    if book.ext in [".txt", ".md"]:
        text = read_txt(book.path)
    elif book.ext == ".epub":
        text = read_epub(book.path)
    elif book.ext in [".mobi", ".azw3"]:
        text = read_mobi(book.path)
    else:
        text = "Định dạng chưa hỗ trợ"

    # cover chỉ áp dụng cho EPUB/MOBI,… không áp dụng PDF viewer
    book.cover = get_cover(book.path, book.ext)

    return text
