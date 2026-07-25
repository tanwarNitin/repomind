"""
Tree-sitter C++/Python AST JSON Generator module for RepoMind.
Uses tree-sitter v0.22+ API with tree_sitter_python and tree_sitter_cpp.
Includes AST & regex fallback parsing mechanisms to ensure maximum reliability.
"""

from typing import List, Dict, Any, Optional
import ast
import re

# Try importing tree_sitter and language packs
TREE_SITTER_AVAILABLE = False
try:
    import tree_sitter
    import tree_sitter_python as tspython
    import tree_sitter_cpp as tscpp

    # tree-sitter v0.22+ initialization syntax
    try:
        PY_LANGUAGE = tree_sitter.Language(tspython.language())
        CPP_LANGUAGE = tree_sitter.Language(tscpp.language())
    except Exception:
        # Alternative attribute names across minor bindings
        py_lang_fn = getattr(tspython, 'language', None) or getattr(tspython, 'language_python', None)
        cpp_lang_fn = getattr(tscpp, 'language', None) or getattr(tscpp, 'language_cpp', None)
        PY_LANGUAGE = tree_sitter.Language(py_lang_fn()) if py_lang_fn else None
        CPP_LANGUAGE = tree_sitter.Language(cpp_lang_fn()) if cpp_lang_fn else None
    
    if PY_LANGUAGE and CPP_LANGUAGE:
        TREE_SITTER_AVAILABLE = True
except Exception:
        TREE_SITTER_AVAILABLE = False


class CodeASTParser:
    """
    Parses Python and C++ source code into a normalized JSON array of code symbols.
    Extracts Classes, Structs, Methods, and Functions along with line ranges and parameters.
    """

    def __init__(self):
        self.use_tree_sitter = TREE_SITTER_AVAILABLE
        if self.use_tree_sitter:
            try:
                self.py_parser = tree_sitter.Parser()
                self.py_parser.set_language(PY_LANGUAGE)
                self.cpp_parser = tree_sitter.Parser()
                self.cpp_parser.set_language(CPP_LANGUAGE)
            except Exception:
                # In tree-sitter 0.22+, Parser initialization can be Parser(PY_LANGUAGE)
                try:
                    self.py_parser = tree_sitter.Parser(PY_LANGUAGE)
                    self.cpp_parser = tree_sitter.Parser(CPP_LANGUAGE)
                except Exception:
                    self.use_tree_sitter = False

    def parse_python(self, code_str: str) -> List[Dict[str, Any]]:
        """
        Parses Python source code into AST symbol objects.
        """
        symbols: List[Dict[str, Any]] = []

        if self.use_tree_sitter:
            try:
                tree = self.py_parser.parse(bytes(code_str, "utf-8"))
                root_node = tree.root_node
                self._traverse_python_node(root_node, code_str, symbols)
                if symbols:
                    return symbols
            except Exception:
                pass  # Fallback to standard library AST parser below

        # Fallback to Python standard library `ast` module
        return self._parse_python_builtin(code_str)

    def parse_cpp(self, code_str: str) -> List[Dict[str, Any]]:
        """
        Parses C++ source code into AST symbol objects.
        """
        symbols: List[Dict[str, Any]] = []

        if self.use_tree_sitter:
            try:
                tree = self.cpp_parser.parse(bytes(code_str, "utf-8"))
                root_node = tree.root_node
                self._traverse_cpp_node(root_node, code_str, symbols)
                if symbols:
                    return symbols
            except Exception:
                pass  # Fallback to regex parser below

        # Fallback to C++ regex parser
        return self._parse_cpp_regex(code_str)

    def _traverse_python_node(
        self,
        node: Any,
        code_str: str,
        symbols: List[Dict[str, Any]],
        parent_class: Optional[str] = None,
    ):
        code_bytes = code_str.encode("utf-8")

        for child in node.children:
            if child.type == "class_definition":
                class_name = ""
                superclasses = []
                for sub in child.children:
                    if sub.type == "identifier":
                        class_name = code_bytes[sub.start_byte:sub.end_byte].decode("utf-8")
                    elif sub.type == "argument_list":
                        superclasses.append(code_bytes[sub.start_byte:sub.end_byte].decode("utf-8"))

                symbols.append({
                    "type": "class",
                    "name": class_name,
                    "parent_class": ", ".join(superclasses) if superclasses else None,
                    "parameters": [],
                    "start_line": child.start_point[0] + 1,
                    "end_line": child.end_point[0] + 1
                })

                # Recursively parse class body for methods
                self._traverse_python_node(child, code_str, symbols, parent_class=class_name)

            elif child.type == "function_definition":
                func_name = ""
                params = []
                for sub in child.children:
                    if sub.type == "identifier":
                        func_name = code_bytes[sub.start_byte:sub.end_byte].decode("utf-8")
                    elif sub.type == "parameters":
                        params_str = code_bytes[sub.start_byte:sub.end_byte].decode("utf-8")
                        params = [p.strip() for p in params_str.strip("()").split(",") if p.strip()]

                symbols.append({
                    "type": "method" if parent_class else "function",
                    "name": func_name,
                    "parent_class": parent_class,
                    "parameters": params,
                    "start_line": child.start_point[0] + 1,
                    "end_line": child.end_point[0] + 1
                })
            else:
                self._traverse_python_node(child, code_str, symbols, parent_class=parent_class)

    def _traverse_cpp_node(
        self,
        node: Any,
        code_str: str,
        symbols: List[Dict[str, Any]],
        parent_class: Optional[str] = None,
    ):
        code_bytes = code_str.encode("utf-8")

        for child in node.children:
            if child.type in ("class_specifier", "struct_specifier"):
                name = ""
                bases = []
                for sub in child.children:
                    if sub.type == "type_identifier":
                        name = code_bytes[sub.start_byte:sub.end_byte].decode("utf-8")
                    elif sub.type == "base_class_clause":
                        bases.append(code_bytes[sub.start_byte:sub.end_byte].decode("utf-8"))

                symbols.append({
                    "type": "class" if child.type == "class_specifier" else "struct",
                    "name": name or "Anonymous",
                    "parent_class": ", ".join(bases) if bases else None,
                    "parameters": [],
                    "start_line": child.start_point[0] + 1,
                    "end_line": child.end_point[0] + 1
                })
                self._traverse_cpp_node(child, code_str, symbols, parent_class=name)

            elif child.type in ("function_definition", "field_declaration"):
                # Extract declarator / function name
                func_name = ""
                params = []
                func_declarator = None

                for sub in child.children:
                    if sub.type == "function_declarator":
                        func_declarator = sub
                        break

                if func_declarator:
                    for sub in func_declarator.children:
                        if sub.type in ("identifier", "field_identifier"):
                            func_name = code_bytes[sub.start_byte:sub.end_byte].decode("utf-8")
                        elif sub.type == "parameter_list":
                            p_str = code_bytes[sub.start_byte:sub.end_byte].decode("utf-8")
                            params = [p.strip() for p in p_str.strip("()").split(",") if p.strip()]

                    symbols.append({
                        "type": "method" if parent_class else "function",
                        "name": func_name or "unknown",
                        "parent_class": parent_class,
                        "parameters": params,
                        "start_line": child.start_point[0] + 1,
                        "end_line": child.end_point[0] + 1
                    })
            else:
                self._traverse_cpp_node(child, code_str, symbols, parent_class=parent_class)

    def _parse_python_builtin(self, code_str: str) -> List[Dict[str, Any]]:
        """Fallback Python parsing using standard `ast` module."""
        symbols = []
        try:
            tree = ast.parse(code_str)
        except Exception:
            return symbols

        class Visitor(ast.NodeVisitor):
            def __init__(self):
                self.current_class = None

            def visit_ClassDef(self, node):
                bases = [ast.unparse(b) for b in node.bases] if hasattr(ast, 'unparse') else []
                symbols.append({
                    "type": "class",
                    "name": node.name,
                    "parent_class": ", ".join(bases) if bases else None,
                    "parameters": [],
                    "start_line": node.lineno,
                    "end_line": getattr(node, 'end_lineno', node.lineno)
                })
                old_class = self.current_class
                self.current_class = node.name
                self.generic_visit(node)
                self.current_class = old_class

            def visit_FunctionDef(self, node):
                params = [a.arg for a in node.args.args]
                symbols.append({
                    "type": "method" if self.current_class else "function",
                    "name": node.name,
                    "parent_class": self.current_class,
                    "parameters": params,
                    "start_line": node.lineno,
                    "end_line": getattr(node, 'end_lineno', node.lineno)
                })
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node):
                self.visit_FunctionDef(node)

        Visitor().visit(tree)
        return symbols

    def _parse_cpp_regex(self, code_str: str) -> List[Dict[str, Any]]:
        """Fallback C++ parsing using Regex."""
        symbols = []
        lines = code_str.splitlines()

        # Class/Struct pattern
        class_pattern = re.compile(r'^\s*(class|struct)\s+([A-Za-z0-9_]+)(?:\s*:\s*public\s+([A-Za-z0-9_]+))?')
        # Function pattern
        func_pattern = re.compile(r'^\s*([A-Za-z0-9_:<>]+\s+)+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*\{?')

        current_class = None
        for i, line in enumerate(lines, 1):
            class_match = class_pattern.search(line)
            if class_match:
                kind, name, parent = class_match.groups()
                current_class = name
                symbols.append({
                    "type": kind,
                    "name": name,
                    "parent_class": parent,
                    "parameters": [],
                    "start_line": i,
                    "end_line": i + 10  # Estimate line range
                })
                continue

            func_match = func_pattern.search(line)
            if func_match:
                _, func_name, params_str = func_match.groups()
                if func_name not in ("if", "while", "for", "switch", "catch"):
                    params = [p.strip() for p in params_str.split(",") if p.strip()]
                    symbols.append({
                        "type": "method" if current_class else "function",
                        "name": func_name,
                        "parent_class": current_class,
                        "parameters": params,
                        "start_line": i,
                        "end_line": i + 8
                    })

        return symbols
