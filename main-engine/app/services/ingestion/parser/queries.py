COMMON_JS_TS_QUERY = """
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


COMMON_PY_QUERY = """
(function_definition
    name: (identifier) @symbol.name
) @symbol.node

(class_definition
    name: (identifier) @symbol.name
) @symbol.node
"""


HTML_QUERY = """
(element
    (start_tag
        (tag_name) @symbol.name
    )
) @symbol.node
"""


CSS_QUERY = """
(rule_set
    (selectors) @symbol.name
) @symbol.node
"""