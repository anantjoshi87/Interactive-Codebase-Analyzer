# Python

COMMON_PY_SYMBOL_QUERY = """
(function_definition
    name: (identifier) @symbol.name
) @symbol.node

(class_definition
    name: (identifier) @symbol.name
) @symbol.node
"""


COMMON_PY_IMPORT_QUERY = """
(import_statement) @import

(import_from_statement) @import
"""


COMMON_PY_GLOBAL_QUERY = """
(expression_statement
    (assignment)
) @global
"""

#--------------------------------------------------------------------------

# JavaScript / TypeScript / JSX / TSX

COMMON_JS_TS_SYMBOL_QUERY = """
(function_declaration
    name: (identifier) @symbol.name
) @symbol.node

(variable_declarator
    name: (identifier) @symbol.name
    value: (arrow_function)
) @symbol.node

(class_declaration
    name: (identifier) @symbol.name
) @symbol.node
"""


COMMON_JS_TS_IMPORT_QUERY = """
(import_statement) @import
"""


COMMON_JS_TS_GLOBAL_QUERY = """
(lexical_declaration
    (variable_declarator)
) @global

(variable_declaration
    (variable_declarator)
) @global
"""

#--------------------------------------------------------------------------

# HTML

HTML_SYMBOL_QUERY = """
(element
    (start_tag
        (tag_name) @symbol.name
    )
) @symbol.node
"""

HTML_IMPORT_QUERY = ""

HTML_GLOBAL_QUERY = ""

#--------------------------------------------------------------------------

# CSS

CSS_SYMBOL_QUERY = """
(rule_set
    (selectors) @symbol.name
) @symbol.node
"""

CSS_IMPORT_QUERY = """
(import_statement) @import
"""

CSS_GLOBAL_QUERY = ""

#--------------------------------------------------------------------------