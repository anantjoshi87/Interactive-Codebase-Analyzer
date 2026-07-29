def decode_bytes(content: bytes) -> str:
    for encoding in (
        "utf-8",
        "utf-16",
        "utf-16-le",
        "utf-16-be",
        "latin-1",
    ):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            pass

    return content.decode("utf-8", errors="ignore")
