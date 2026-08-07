from .python_resolver import PythonResolver
# from .javascript_resolver import JavascriptResolver


class ResolverFactory:

    @staticmethod
    def get_resolver(
        units,
    ):

        extension = units[0].file_path.split(".")[-1]

        if extension == "py":
            return PythonResolver()

        # if extension in ("js", "jsx"):
        #     return JavascriptResolver()

        return None

        # raise NotImplementedError(extension)