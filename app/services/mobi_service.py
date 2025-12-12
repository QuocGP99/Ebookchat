import mobi
import os
import shutil
from bs4 import BeautifulSoup


def read_mobi(path):
    """
    Đọc file .mobi / .azw3:
    1. Giải nén bằng mobi.extract
    2. Dùng BeautifulSoup lọc bỏ CSS/Font rác để tránh lỗi hiển thị trên Qt
    """
    try:
        # 1. Giải nén file
        temp_dir, filepath = mobi.extract(path)

        if not filepath or not os.path.exists(filepath):
            return "<h3>Lỗi: Không trích xuất được nội dung file Mobi/Azw3.</h3>"

        # 2. Đọc nội dung HTML thô
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            raw_content = f.read()

        # 3. Dọn dẹp thư mục tạm ngay lập tức
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

        # 4. XỬ LÝ HTML (Quan trọng để fix lỗi font)
        soup = BeautifulSoup(raw_content, "html.parser")

        # Xóa các thẻ chứa định dạng font/css gây nhiễu
        # (script, style, link, meta, xml...)
        for s in soup(["script", "style", "meta", "link", "xml", "head", "title"]):
            s.decompose()

        # Xóa các thuộc tính style="..." trong từng thẻ HTML (inline css)
        # để app tự dùng font mặc định của hệ thống cho dễ đọc
        for tag in soup.recursiveChildGenerator():
            try:
                if hasattr(tag, "attrs"):
                    del tag["class"]
                    del tag["style"]
                    del tag["width"]
                    del tag["height"]
            except:
                pass

        # Lấy nội dung body (hoặc cả soup nếu không tìm thấy body)
        body = soup.find("body")
        if body:
            return str(body)
        else:
            return str(soup)

    except Exception as e:
        return f"""
        <div style='color:red; padding:20px;'>
            <h3>Không thể đọc file Mobi/Azw3 này</h3>
            <p>Lỗi hệ thống: {str(e)}</p>
            <p><i>Gợi ý: File có thể bị lỗi định dạng hoặc bị mã hóa (DRM).</i></p>
        </div>
        """
