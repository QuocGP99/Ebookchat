from pathlib import Path

class Book:
    def __init__(self, title, path):
        self.title = title
        self.path = path
        self.ext = Path(path).suffix.lower()
        self.cover = None
