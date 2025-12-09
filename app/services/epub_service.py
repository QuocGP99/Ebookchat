from ebooklib import epub
from bs4 import BeautifulSoup


def read_epub(path: str) -> str:
    """
    Đọc nội dung EPUB, ưu tiên lấy nội dung trong <body>,
    fallback lấy cả soup nếu file epub không chuẩn.
    Trả về HTML đã ghép.
    """

    # ===== chặn lỗi đọc file =====
    try:
        eb = epub.read_epub(path)
    except Exception as e:
        return f"<h3>Lỗi khi đọc EPUB:<br>{str(e)}</h3>"

    content_parts = []

    # ===== duyệt items =====
    try:
        for item in eb.get_items():
            if item.get_type() == epub.EpubHtml:
                soup = BeautifulSoup(item.get_content(), "html.parser")

                # có body thì lấy body
                body = soup.find("body")
                if body:
                    content_parts.append(str(body))
                else:
                    # fallback
                    content_parts.append(str(soup))

    except Exception as e:
        return f"<h3>Lỗi khi xử lý nội dung EPUB:<br>{str(e)}</h3>"

    # ===== kết quả =====
    if not content_parts:
        return "<h3>Không đọc được nội dung EPUB</h3>"

    return "<hr>".join(content_parts)
