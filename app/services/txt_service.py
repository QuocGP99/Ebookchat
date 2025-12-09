def read_txt(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        t = f.read()

    return t.replace("\n", "<br>")
