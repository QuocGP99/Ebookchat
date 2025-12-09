def get_cover(path, ext):
    if ext == ".epub":
        from ebooklib import epub
        eb = epub.read_epub(path)
        for item in eb.get_items():
            if item.get_type() == epub.EpubImage:
                out = f"assets/covers/{item.get_id()}.jpg"
                with open(out, "wb") as f:
                    f.write(item.get_content())
                return out
    return None
