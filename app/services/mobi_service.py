def read_mobi(path):
    import mobi
    m = mobi.Mobi(path)
    m.parse()
    text = m.get_raw_html()
    return text.decode("utf-8", errors="ignore")
