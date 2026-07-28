from app.services.ingestion.parser import RepoParser, RepoFetcher
from rich import print


repo_url = "https://github.com/anantjoshi87/smart-study-planner-python.git"

parser = RepoParser()

with RepoFetcher.clone_to_temp(repo_url) as repo_path:
    extracted_units = parser.parse_repository(repo_path)
    print(f"Extracted {len(extracted_units)} AST symbols/chunks.")
    print("Sample extracted unit:", extracted_units[0] if extracted_units else "None")


# import tree_sitter
# import tree_sitter_python

# print(tree_sitter.__version__)

# lang = tree_sitter.Language(tree_sitter_python.language())
# print(type(lang))
# print(dir(lang))

# from tree_sitter import Parser
# import inspect


# parser = Parser()
# print(dir(parser))

# print(inspect.signature(Parser))

# from tree_sitter import Query

# print(Query)

# from tree_sitter import Language, Query
# import tree_sitter_javascript as tsjavascript

# language = Language(tsjavascript.language())

# query = Query(
#     language,
#     """
#     (function_declaration
#         name: (identifier) @symbol.name
#     ) @symbol.node
#     """
# )

# print(type(query))
# print(dir(query))

# from tree_sitter import QueryCursor

# print(QueryCursor)
# print(dir(QueryCursor))
