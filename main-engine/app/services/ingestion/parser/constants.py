DEFAULT_IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".venv",
}

DEFAULT_IGNORED_EXTS = {
    ".png",
    ".jpg",
    ".svg",
    ".lock",
    ".gitignore",
    ".pyc",
}

SYMBOL_KIND_MAP = {
    "function_definition": "function",
    "function_declaration": "function",
    "arrow_function": "function",
    "class_definition": "class",
    "class_declaration": "class",
    "variable_declarator": "function",  # because your query only matches arrow functions
}
