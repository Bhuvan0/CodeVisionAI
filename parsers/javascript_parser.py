"""
JavaScript/TypeScript Code Parser
Uses tree-sitter or regex-based parsing to extract structure from JS/TS files.
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class JSClassInfo:
    name: str
    module: str
    extends: Optional[str]
    implements: List[str]
    methods: List[Dict[str, Any]]
    properties: List[str]
    is_abstract: bool
    line_number: int


@dataclass
class JSFunctionInfo:
    name: str
    module: str
    parameters: List[Dict[str, str]]
    return_type: Optional[str]
    is_async: bool
    is_arrow: bool
    is_exported: bool
    line_number: int


class JavaScriptCodeParser:
    """Parser for JavaScript/TypeScript source code."""
    
    def __init__(self):
        self.current_module = ""
        self.current_file = ""
        
        # Regex patterns for parsing
        self.patterns = {
            # Class declarations
            "class": re.compile(
                r'^(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?\s*\{',
                re.MULTILINE
            ),
            # Function declarations
            "function": re.compile(
                r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)(?:\s*:\s*(\w+(?:<[^>]+>)?))?\s*\{',
                re.MULTILINE
            ),
            # Arrow functions (const/let/var)
            "arrow_function": re.compile(
                r'^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*(?::\s*\w+(?:<[^>]+>)?)?\s*=>\s*',
                re.MULTILINE
            ),
            # Method declarations inside classes
            "method": re.compile(
                r'^\s+(?:async\s+)?(?:static\s+)?(?:private\s+|protected\s+|public\s+)?(\w+)\s*\(([^)]*)\)(?:\s*:\s*(\w+(?:<[^>]+>)?))?\s*\{',
                re.MULTILINE
            ),
            # Import statements
            "import": re.compile(
                r'^import\s+(?:(?:\{([^}]+)\}|\*\s+as\s+(\w+)|(\w+))\s+from\s+)?[\'"]([^\'"]+)[\'"]',
                re.MULTILINE
            ),
            # Export statements
            "export": re.compile(
                r'^export\s+(?:default\s+)?(?:class|function|const|let|var|interface|type)\s+(\w+)',
                re.MULTILINE
            ),
            # Interface declarations (TypeScript)
            "interface": re.compile(
                r'^(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+([\w,\s]+))?\s*\{',
                re.MULTILINE
            ),
            # Type aliases (TypeScript)
            "type_alias": re.compile(
                r'^(?:export\s+)?type\s+(\w+)\s*=',
                re.MULTILINE
            ),
            # Property declarations
            "property": re.compile(
                r'^\s+(?:private\s+|protected\s+|public\s+)?(?:readonly\s+)?(\w+)(?:\?)?(?:\s*:\s*([^;=]+))?(?:\s*=)?;?$',
                re.MULTILINE
            )
        }
    
    def parse_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a JavaScript/TypeScript file and extract its structure."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            self.current_file = str(file_path)
            self.current_module = file_path.stem
            
            # Determine if TypeScript
            is_typescript = file_path.suffix in ['.ts', '.tsx']
            
            # Extract components
            classes = self._extract_classes(source)
            functions = self._extract_functions(source)
            imports = self._extract_imports(source)
            interfaces = self._extract_interfaces(source) if is_typescript else []
            exports = self._extract_exports(source)
            
            return {
                "module": {
                    "name": self.current_module,
                    "file": str(file_path),
                    "is_typescript": is_typescript,
                    "line_count": len(source.splitlines()),
                    "class_count": len(classes),
                    "function_count": len(functions),
                    "interface_count": len(interfaces),
                    "exports": exports
                },
                "classes": classes,
                "functions": functions,
                "interfaces": interfaces,
                "dependencies": imports
            }
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def _extract_classes(self, source: str) -> List[Dict[str, Any]]:
        """Extract all class definitions."""
        classes = []
        lines = source.splitlines()
        
        for match in self.patterns["class"].finditer(source):
            name = match.group(1)
            extends = match.group(2)
            implements = []
            if match.group(3):
                implements = [i.strip() for i in match.group(3).split(',')]
            
            # Find line number
            line_number = source[:match.start()].count('\n') + 1
            
            # Extract methods from the class body
            class_body = self._extract_block(source, match.end() - 1)
            methods = self._extract_methods(class_body)
            properties = self._extract_properties(class_body)
            
            is_abstract = 'abstract class' in source[max(0, match.start()-20):match.start()+len(match.group(0))]
            
            classes.append({
                "name": name,
                "module": self.current_module,
                "extends": extends,
                "implements": implements,
                "methods": methods,
                "properties": properties,
                "is_abstract": is_abstract,
                "line_number": line_number
            })
        
        return classes
    
    def _extract_methods(self, class_body: str) -> List[Dict[str, Any]]:
        """Extract methods from a class body."""
        methods = []
        
        for match in self.patterns["method"].finditer(class_body):
            name = match.group(1)
            params_str = match.group(2)
            return_type = match.group(3)
            
            # Skip constructor-like patterns that aren't methods
            if name in ['if', 'for', 'while', 'switch', 'catch']:
                continue
            
            line_text = class_body[max(0, match.start()-50):match.start()]
            
            methods.append({
                "name": name,
                "parameters": self._parse_parameters(params_str),
                "return_type": return_type,
                "is_async": 'async' in line_text,
                "is_static": 'static' in line_text,
                "visibility": self._get_visibility(line_text),
                "line_number": class_body[:match.start()].count('\n') + 1
            })
        
        return methods
    
    def _extract_properties(self, class_body: str) -> List[str]:
        """Extract property declarations from a class body."""
        properties = []
        
        for match in self.patterns["property"].finditer(class_body):
            prop_name = match.group(1)
            # Filter out method-like patterns
            if prop_name not in ['if', 'for', 'while', 'return', 'const', 'let', 'var']:
                properties.append(prop_name)
        
        return list(set(properties))
    
    def _extract_functions(self, source: str) -> List[Dict[str, Any]]:
        """Extract top-level function definitions."""
        functions = []
        
        # Regular functions
        for match in self.patterns["function"].finditer(source):
            # Check if inside a class (skip if so)
            if self._is_inside_class(source, match.start()):
                continue
            
            name = match.group(1)
            params_str = match.group(2)
            return_type = match.group(3)
            
            line_text = source[max(0, match.start()-30):match.start()]
            line_number = source[:match.start()].count('\n') + 1
            
            functions.append({
                "name": name,
                "module": self.current_module,
                "parameters": self._parse_parameters(params_str),
                "return_type": return_type,
                "is_async": 'async' in line_text,
                "is_arrow": False,
                "is_exported": 'export' in line_text,
                "line_number": line_number
            })
        
        # Arrow functions
        for match in self.patterns["arrow_function"].finditer(source):
            if self._is_inside_class(source, match.start()):
                continue
            
            name = match.group(1)
            line_text = source[max(0, match.start()-30):match.start() + len(match.group(0))]
            line_number = source[:match.start()].count('\n') + 1
            
            functions.append({
                "name": name,
                "module": self.current_module,
                "parameters": [],  # Simplified for arrow functions
                "return_type": None,
                "is_async": 'async' in line_text,
                "is_arrow": True,
                "is_exported": 'export' in line_text,
                "line_number": line_number
            })
        
        return functions
    
    def _extract_imports(self, source: str) -> List[Dict[str, Any]]:
        """Extract import statements."""
        imports = []
        
        for match in self.patterns["import"].finditer(source):
            named_imports = match.group(1)
            namespace_import = match.group(2)
            default_import = match.group(3)
            module_path = match.group(4)
            
            names = []
            if named_imports:
                names = [n.strip().split(' as ')[0].strip() for n in named_imports.split(',')]
            if namespace_import:
                names = [f"* as {namespace_import}"]
            if default_import:
                names = [default_import]
            
            # Determine import type
            is_relative = module_path.startswith('.')
            is_package = not is_relative and not module_path.startswith('@')
            
            imports.append({
                "source": self.current_module,
                "target": module_path.split('/')[0].replace('@', ''),
                "import_type": "relative" if is_relative else "package",
                "full_path": module_path,
                "names": names
            })
        
        return imports
    
    def _extract_interfaces(self, source: str) -> List[Dict[str, Any]]:
        """Extract TypeScript interface definitions."""
        interfaces = []
        
        for match in self.patterns["interface"].finditer(source):
            name = match.group(1)
            extends = []
            if match.group(2):
                extends = [e.strip() for e in match.group(2).split(',')]
            
            line_number = source[:match.start()].count('\n') + 1
            
            # Extract interface body
            body = self._extract_block(source, match.end() - 1)
            properties = self._extract_interface_properties(body)
            
            interfaces.append({
                "name": name,
                "module": self.current_module,
                "extends": extends,
                "properties": properties,
                "line_number": line_number
            })
        
        return interfaces
    
    def _extract_interface_properties(self, body: str) -> List[Dict[str, str]]:
        """Extract properties from an interface body."""
        properties = []
        
        # Simple pattern for interface properties
        prop_pattern = re.compile(r'(\w+)(\?)?\s*:\s*([^;,\n]+)', re.MULTILINE)
        
        for match in prop_pattern.finditer(body):
            properties.append({
                "name": match.group(1),
                "optional": match.group(2) == '?',
                "type": match.group(3).strip()
            })
        
        return properties
    
    def _extract_exports(self, source: str) -> List[str]:
        """Extract exported names."""
        exports = []
        
        for match in self.patterns["export"].finditer(source):
            exports.append(match.group(1))
        
        return exports
    
    def _extract_block(self, source: str, start_pos: int) -> str:
        """Extract a code block starting from an opening brace."""
        if start_pos >= len(source) or source[start_pos] != '{':
            return ""
        
        depth = 1
        pos = start_pos + 1
        
        while pos < len(source) and depth > 0:
            if source[pos] == '{':
                depth += 1
            elif source[pos] == '}':
                depth -= 1
            pos += 1
        
        return source[start_pos:pos]
    
    def _is_inside_class(self, source: str, pos: int) -> bool:
        """Check if a position is inside a class definition."""
        # Simple heuristic: count class definitions before this position
        before = source[:pos]
        class_opens = len(self.patterns["class"].findall(before))
        
        # Count closing braces after class definitions
        # This is a simplified check
        return class_opens > 0 and before.count('{') > before.count('}')
    
    def _parse_parameters(self, params_str: str) -> List[Dict[str, str]]:
        """Parse parameter string into structured data."""
        if not params_str or not params_str.strip():
            return []
        
        params = []
        # Split by comma, but handle nested generics
        depth = 0
        current = ""
        
        for char in params_str:
            if char in '<([':
                depth += 1
            elif char in '>)]':
                depth -= 1
            elif char == ',' and depth == 0:
                if current.strip():
                    params.append(self._parse_single_param(current.strip()))
                current = ""
                continue
            current += char
        
        if current.strip():
            params.append(self._parse_single_param(current.strip()))
        
        return params
    
    def _parse_single_param(self, param: str) -> Dict[str, str]:
        """Parse a single parameter."""
        result = {"name": param}
        
        # Handle type annotation
        if ':' in param:
            parts = param.split(':', 1)
            result["name"] = parts[0].strip()
            result["type"] = parts[1].strip()
        
        # Handle default value
        if '=' in result["name"]:
            parts = result["name"].split('=', 1)
            result["name"] = parts[0].strip()
            result["default"] = parts[1].strip()
        
        return result
    
    def _get_visibility(self, context: str) -> str:
        """Determine method visibility from context."""
        if 'private' in context:
            return 'private'
        elif 'protected' in context:
            return 'protected'
        return 'public'
