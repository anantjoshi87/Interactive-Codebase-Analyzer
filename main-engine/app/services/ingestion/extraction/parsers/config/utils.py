def decode_bytes(code_bytes: bytes) -> str:
    for encoding in (
        "utf-8",
        "utf-16",
        "utf-16-le",
        "utf-16-be",
        "latin-1",
    ):
        try:
            return code_bytes.decode(encoding, errors="ignore")
        except UnicodeDecodeError:
            pass

    return code_bytes.decode("utf-8", errors="ignore")
