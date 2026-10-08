import os
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Parser, Query, QueryCursor

def get_parser_and_queries(lang_name: str):
    parser = Parser()
    query_str = ""
    if lang_name == "python":
        lang = Language(tree_sitter_python.language())
        query_str = """
        (class_definition name: (identifier) @class.name) @class.def
        (function_definition name: (identifier) @function.name) @function.def
        """
    elif lang_name == "javascript":
        lang = Language(tree_sitter_javascript.language())
        query_str = """
        (class_declaration name: (identifier) @class.name) @class.def
        (function_declaration name: (identifier) @function.name) @function.def
        (method_definition name: (property_identifier) @method.name) @method.def
        (lexical_declaration (variable_declarator name: (identifier) @function.name value: (arrow_function))) @function.def
        """
    elif lang_name == "typescript":
        lang = Language(tree_sitter_typescript.language_typescript())
        query_str = """
        (class_declaration name: (type_identifier) @class.name) @class.def
        (function_declaration name: (identifier) @function.name) @function.def
        (method_definition name: (property_identifier) @method.name) @method.def
        (lexical_declaration (variable_declarator name: (identifier) @function.name value: (arrow_function))) @function.def
        """
    else:
        return None, None, None

    parser.language = lang
    query = Query(lang, query_str)
    return parser, lang, query

def parse_file(file_path: str):
    ext = os.path.splitext(file_path)[1].lower()
    lang_name = None
    if ext == ".py":
        lang_name = "python"
    elif ext in [".js", ".jsx"]:
        lang_name = "javascript"
    elif ext in [".ts", ".tsx"]:
        lang_name = "typescript"
    else:
        return []

    parser, lang, query = get_parser_and_queries(lang_name)
    if not parser:
        return []

    try:
        with open(file_path, "rb") as f:
            code = f.read()
    except Exception:
        return []

    tree = parser.parse(code)
    cursor = QueryCursor(query)
    matches = cursor.matches(tree.root_node)

    symbols = []
    
    for pattern_idx, captures in matches:
        def_nodes = None
        name_nodes = None
        kind = None
        for capture_name, nodes in captures.items():
            if capture_name.endswith('.def'):
                def_nodes = nodes
                kind = capture_name.split('.')[0]
            elif capture_name.endswith('.name'):
                name_nodes = nodes
        
        if def_nodes and name_nodes:
            d_node = def_nodes[0]
            n_node = name_nodes[0]
            try:
                name_text = code[n_node.start_byte:n_node.end_byte].decode("utf-8")
                symbols.append({
                    "name": name_text,
                    "kind": kind,
                    "start_line": d_node.start_point[0] + 1,
                    "end_line": d_node.end_point[0] + 1,
                })
            except Exception:
                pass

    return symbols
