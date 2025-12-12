import warnings
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup

# Tắt cảnh báo phiền phức
warnings.filterwarnings("ignore")


def read_epub(path: str) -> str:
    """
    Đọc nội dung EPUB (Phiên bản quét sâu)
    """
    try:
        book = epub.read_epub(path)
        content_parts = []

        # Cách 1: Duyệt qua tất cả items được đánh dấu là DOCUMENT
        # ITEM_DOCUMENT bao gồm HTML và XHTML
        items = list(book.get_items_of_type(ITEM_DOCUMENT))

        # Cách 2: Nếu Cách 1 không thấy gì, duyệt thủ công qua media_type
        if not items:
            for item in book.get_items():
                if item.media_type in ["application/xhtml+xml", "text/html"]:
                    items.append(item)

        for item in items:
            # Lấy nội dung raw
            raw_content = item.get_content()

            # Parse HTML
            soup = BeautifulSoup(raw_content, "html.parser")

            # Xóa bớt các script/style thừa để sạch giao diện
            for s in soup(["script", "style", "title", "meta"]):
                s.decompose()

            # Ưu tiên lấy body, nếu không thì lấy hết
            body = soup.find("body")
            content_str = str(body) if body else str(soup)
            file_id = item.file_name
            wrapped_content = (
                f'<div id="{file_id}" class="chapter-container">{content_str}</div>'
            )

            content_parts.append(wrapped_content)

        if not content_parts:
            return "<h3 style='color:red'>Không tìm thấy nội dung văn bản.</h3>"

        return "<hr>".join(content_parts)

    except Exception as e:
        return f"<h3 style='color:red'>Lỗi đọc file: {str(e)}</h3>"
