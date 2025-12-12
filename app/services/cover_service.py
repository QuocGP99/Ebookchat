import os
from ebooklib import epub, ITEM_IMAGE


def get_cover(path, ext):
    """
    Trích xuất ảnh bìa EPUB (Phiên bản tìm kiếm thông minh)
    """
    # 1. Chuẩn bị thư mục
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(current_dir)
    save_dir = os.path.join(app_dir, "assets", "covers")

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    try:
        if ext == ".epub":
            book = epub.read_epub(path)
            cover_item = None

            # CÁCH 1: Lấy theo metadata chuẩn
            # (Thường trả về None nếu sách làm không chuẩn)
            try:
                cover_item = book.get_item_with_id("cover")
            except:
                pass

            # CÁCH 2: Nếu không có, duyệt tìm ảnh có tên là 'cover'
            if not cover_item:
                for item in book.get_items_of_type(ITEM_IMAGE):
                    name = item.get_name().lower()
                    if "cover" in name or "bia" in name:
                        cover_item = item
                        break

            # CÁCH 3: Vẫn không có? Lấy đại ảnh đầu tiên (thường là bìa)
            if not cover_item:
                images = list(book.get_items_of_type(ITEM_IMAGE))
                if images:
                    cover_item = images[0]

            # === LƯU ẢNH ===
            if cover_item:
                # Tạo tên file output duy nhất
                safe_name = os.path.basename(path).replace(" ", "_") + ".jpg"
                out_path = os.path.join(save_dir, safe_name)

                with open(out_path, "wb") as f:
                    f.write(cover_item.get_content())

                return out_path

        return None

    except Exception as e:
        print(f"Lỗi lấy cover: {e}")
        return None
