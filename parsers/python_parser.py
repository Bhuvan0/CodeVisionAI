"""
Python Code Parser
Uses Python's AST module to extract class hierarchies, functions, and dependencies.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ClassInfo:
    name: str
    module: str
    bases: List[str]
    methods: List[Dict[str, Any]]
    attributes: List[str]
    decorators: List[str]
    docstring: Optional[str]
    line_number: int


@dataclass
class FunctionInfo:
    name: str
    module: str
    parameters: List[Dict[str, str]]
    return_type: Optional[str]
    decorators: List[str]
    docstring: Optional[str]
    is_async: bool
    line_number: int


@dataclass
class ImportInfo:
    source: str
    target: str
    import_type: str  # 'module', 'from', 'relative'
    names: List[str]


class PythonCodeParser:
    """Parser for Python source code using AST."""
    
    def __init__(self):
        self.current_module = ""
        self.current_file = ""
    
    def parse_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a Python file and extract its structure."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source, filename=str(file_path))
            
            # Determine module name from file path
            self.current_file = str(file_path)
            self.current_module = file_path.stem
            if file_path.stem == "__init__":
                self.current_module = file_path.parent.name
            
            # Extract all components
            classes = self._extract_classes(tree)
            functions = self._extract_functions(tree)
            imports = self._extract_imports(tree)
            module_docstring = ast.get_docstring(tree)
            
            return {
                "module": {
                    "name": self.current_module,
                    "file": str(file_path),
                    "docstring": module_docstring,
                    "line_count": len(source.splitlines()),
                    "class_count": len(classes),
                    "function_count": len(functions)
                },
                "classes": classes,
                "functions": functions,
                "dependencies": imports
            }
            
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return None
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def _extract_classes(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract all class definitions from the AST."""
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = self._parse_class(node)
                classes.append(asdict(class_info))
        
        return classes
    
    def _parse_class(self, node: ast.ClassDef) -> ClassInfo:
        """Parse a single class definition."""
        # Get base classes
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(self._get_attribute_name(base))
        
        # Get methods
        methods = []
        attributes = []
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                method_info = {
                    "name": item.name,
                    "is_async": isinstance(item, ast.AsyncFunctionDef),
                    "parameters": self._get_parameters(item),
                    "return_type": self._get_return_annotation(item),
                    "decorators": [self._get_decorator_name(d) for d in item.decorator_list],
                    "docstring": ast.get_docstring(item),
                    "is_private": item.name.startswith("_"),
                    "is_magic": item.name.startswith("__") and item.name.endswith("__"),
                    "line_number": item.lineno
                }
                methods.append(method_info)
            
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attributes.append(target.id)
            
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                attributes.append(item.target.id)
        
        # Get decorators
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        
        return ClassInfo(
            name=node.name,
            module=self.current_module,
            bases=bases,
            methods=methods,
            attributes=attributes,
            decorators=decorators,
            docstring=ast.get_docstring(node),
            line_number=node.lineno
        )
    
    def _extract_functions(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract all top-level function definitions."""
        functions = []
        
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = FunctionInfo(
                    name=node.name,
                    module=self.current_module,
                    parameters=self._get_parameters(node),
                    return_type=self._get_return_annotation(node),
                    decorators=[self._get_decorator_name(d) for d in node.decorator_list],
                    docstring=ast.get_docstring(node),
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    line_number=node.lineno
                )
                functions.append(asdict(func_info))
        
        return functions
    
    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract all import statements."""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "source": self.current_module,
                        "target": alias.name.split(".")[0],
                        "import_type": "module",
                        "names": [alias.name],
                        "alias": alias.asname
                    })
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                is_relative = node.level > 0
                
                imports.append({
                    "source": self.current_module,
                    "target": module.split(".")[0] if module else "",
                    "import_type": "relative" if is_relative else "from",
                    "names": [alias.name for alias in node.names],
                    "level": node.level
                })
        
        return imports
    
    def _get_parameters(self, node: ast.FunctionDef) -> List[Dict[str, str]]:
        """Extract function parameters with type annotations."""
        params = []
        
        for arg in node.args.args:
            param = {"name": arg.arg}
            if arg.annotation:
                param["type"] = self._get_annotation_string(arg.annotation)
            params.append(param)
        
        # Handle *args
        if node.args.vararg:
            params.append({
                "name": f"*{node.args.vararg.arg}",
                "type": self._get_annotation_string(node.args.vararg.annotation) if node.args.vararg.annotation else None
            })
        
        # Handle **kwargs
        if node.args.kwarg:
            params.append({
                "name": f"**{node.args.kwarg.arg}",
                "type": self._get_annotation_string(node.args.kwarg.annotation) if node.args.kwarg.annotation else None
            })
        
        return params
    
    def _get_return_annotation(self, node: ast.FunctionDef) -> Optional[str]:
        """Get the return type annotation if present."""
        if node.returns:
            return self._get_annotation_string(node.returns)
        return None
    
    def _get_annotation_string(self, node: ast.AST) -> str:
        """Convert an annotation AST node to a string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Subscript):
            return f"{self._get_annotation_string(node.value)}[{self._get_annotation_string(node.slice)}]"
        elif isinstance(node, ast.Attribute):
            return self._get_attribute_name(node)
        elif isinstance(node, ast.Tuple):
            return ", ".join(self._get_annotation_string(e) for e in node.elts)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return f"{self._get_annotation_string(node.left)} | {self._get_annotation_string(node.right)}"
        else:
            return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
    
    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Get the full name of an attribute access."""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    
    def _get_decorator_name(self, node: ast.AST) -> str:
        """Get the name of a decorator."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_attribute_name(node)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
            elif isinstance(node.func, ast.Attribute):
                return self._get_attribute_name(node.func)
        return str(node)


class PythonProjectAnalyzer:
    """Analyze an entire Python project."""
    
    def __init__(self):
        self.parser = PythonCodeParser()
    
    def analyze_project(self, project_path: Path) -> Dict[str, Any]:
        """Analyze all Python files in a project."""
        results = {
            "modules": [],
            "classes": [],
            "functions": [],
            "dependencies": [],
            "statistics": {
                "total_files": 0,
                "total_classes": 0,
                "total_functions": 0,
                "total_lines": 0
            }
        }
        
        for py_file in project_path.rglob("*.py"):
            # Skip common non-source directories
            if any(skip in str(py_file) for skip in ["__pycache__", ".git", "venv", "env", "node_modules"]):
                continue
            
            parsed = self.parser.parse_file(py_file)
            if parsed:
                results["modules"].append(parsed["module"])
                results["classes"].extend(parsed["classes"])
                results["functions"].extend(parsed["functions"])
                results["dependencies"].extend(parsed["dependencies"])
                
                results["statistics"]["total_files"] += 1
                results["statistics"]["total_classes"] += len(parsed["classes"])
                results["statistics"]["total_functions"] += len(parsed["functions"])
                results["statistics"]["total_lines"] += parsed["module"]["line_count"]
        
        return results
