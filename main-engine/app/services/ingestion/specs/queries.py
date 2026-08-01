# ============================================================================
# Python
# ============================================================================

PY_SYMBOL_QUERY = """
(function_definition
    name: (identifier) @symbol.name
) @symbol.node

(class_definition
    name: (identifier) @symbol.name
) @symbol.node
"""

PY_IMPORT_QUERY = """
(import_statement) @import

(import_from_statement) @import
"""

PY_GLOBAL_QUERY = """
(module
    (expression_statement
        (assignment)
    ) @global
)
"""


# ============================================================================
# JavaScript
# ============================================================================

JS_SYMBOL_QUERY = """
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

JS_IMPORT_QUERY = """
(import_statement) @import
"""

JS_GLOBAL_QUERY = """
(program
    [
        (lexical_declaration)
        (variable_declaration)
    ] @global
)
"""


# ============================================================================
# TypeScript
# ============================================================================

TS_SYMBOL_QUERY = """
(function_declaration
    name: (identifier) @symbol.name
) @symbol.node

(variable_declarator
    name: (identifier) @symbol.name
    value: (arrow_function)
) @symbol.node

(class_declaration
    name: (type_identifier) @symbol.name
) @symbol.node

(interface_declaration
    name: (type_identifier) @symbol.name
) @symbol.node

(enum_declaration
    name: (identifier) @symbol.name
) @symbol.node

(type_alias_declaration
    name: (type_identifier) @symbol.name
) @symbol.node
"""

TS_IMPORT_QUERY = """
(import_statement) @import
"""

TS_GLOBAL_QUERY = """
(program
    [
        (lexical_declaration)
        (variable_declaration)
    ] @global
)
"""


# ============================================================================
# HTML
# ============================================================================

HTML_SYMBOL_QUERY = """
(element
    (start_tag
        (tag_name) @symbol.name
    )
) @symbol.node
"""

HTML_IMPORT_QUERY = """
(script_element) @import

(style_element) @import
"""

HTML_GLOBAL_QUERY = ""


# ============================================================================
# CSS
# ============================================================================

CSS_SYMBOL_QUERY = """
(rule_set
    (selectors) @symbol.name
) @symbol.node
"""

CSS_IMPORT_QUERY = """
(import_statement) @import
"""

CSS_GLOBAL_QUERY = ""
