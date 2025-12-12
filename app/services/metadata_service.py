import fitz  # PyMuPDF
from ebooklib import epub
import os


def get_book_metadata(path, ext):
    """Trả về dict: {'author': str, 'title': str}"""
    meta = {"author": "Unknown", "title": ""}

    try:
        # === EPUB ===
        if ext == ".epub":
            try:
                book = epub.read_epub(path)
                # Lấy tác giả (Dublin Core)
                creators = book.get_metadata("DC", "creator")
                if creators:
                    meta["author"] = creators[0][0]

                # Lấy title chuẩn trong metadata nếu có
                titles = book.get_metadata("DC", "title")
                if titles:
                    meta["title"] = titles[0][0]
            except:
                pass

        # === PDF ===
        elif ext == ".pdf":
            try:
                doc = fitz.open(path)
                if doc.metadata:
                    meta["author"] = doc.metadata.get("author", "")
                    t = doc.metadata.get("title", "")
                    if t:
                        meta["title"] = t
                doc.close()
            except:
                pass

        # === MOBI / AZW3 (Cơ bản) ===
        # Các định dạng này xử lý phức tạp hơn, tạm thời lấy mặc định
        # hoặc dùng thư viện 'mobi' nếu đã cài deep

    except Exception as e:
        print(f"Metadata error: {e}")

    # Fallback nếu không tìm thấy tác giả
    if not meta["author"] or meta["author"] == "Unknown":
        meta["author"] = "Unknown Author"

    return meta
