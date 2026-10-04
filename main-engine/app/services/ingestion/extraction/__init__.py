"""Extraction package namespace.

Concrete extractors and parsers are exported by their respective package
roots. Keeping this namespace lightweight avoids eager import cycles.
"""

__all__: list[str] = []
