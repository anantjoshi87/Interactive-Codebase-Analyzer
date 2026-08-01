from .python_extractor import PythonExtractor
# from .javascript_extractor import JavascriptExtractor


class ExtractorFactory:

    @staticmethod
    def get_extractor(code_bytes: bytes, lang_config):
        lang = lang_config.language.name.lower()

        if lang == "python":
            return PythonExtractor(code_bytes, lang_config)

        # if lang in ("javascript", "jsx"):
        #     return JavascriptExtractor(code_bytes, lang_config)

        raise NotImplementedError(f"Unsupported language extractor: {lang}")
