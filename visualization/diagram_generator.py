"""
CodeVision AI - Diagram Generator
Generates UML and dependency diagrams using Graphviz and PlantUML.
"""

import os
import subprocess
import tempfile
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class DiagramType(Enum):
    CLASS = "class"
    DEPENDENCY = "dependency"
    SEQUENCE = "sequence"
    COMPONENT = "component"


@dataclass
class DiagramNode:
    id: str
    label: str
    node_type: str  # class, interface, module, function
    attributes: List[str]
    methods: List[str]
    color: str = "#E8F4FD"


@dataclass
class DiagramEdge:
    source: str
    target: str
    edge_type: str  # inheritance, dependency, composition, association
    label: str = ""


class DiagramGenerator:
    """
    Generates UML-style diagrams from parsed code structure.
    Supports multiple output formats including SVG, PNG, and PlantUML.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the diagram generator.
        
        Args:
            output_dir: Directory to save generated diagrams
        """
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="codevision_diagrams_")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Color scheme for different node types
        self.colors = {
            "class": "#A8D5BA",      # Sage green
            "abstract": "#F4D03F",    # Gold
            "interface": "#AED6F1",   # Light blue
            "module": "#D7BDE2",      # Lavender
            "function": "#FAD7A0",    # Peach
            "external": "#D5D8DC"     # Gray
        }
        
        # Edge styles
        self.edge_styles = {
            "inheritance": {"style": "solid", "arrow": "empty"},
            "implementation": {"style": "dashed", "arrow": "empty"},
            "dependency": {"style": "dashed", "arrow": "vee"},
            "composition": {"style": "solid", "arrow": "diamond"},
            "association": {"style": "solid", "arrow": "vee"}
        }
    
    def generate_uml_diagram(
        self,
        modules: List[Dict[str, Any]],
        classes: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]],
        diagram_type: str = "class"
    ) -> Dict[str, Any]:
        """
        Generate a UML diagram from parsed code structure.
        
        Args:
            modules: List of module information
            classes: List of class information
            dependencies: List of dependency information
            diagram_type: Type of diagram to generate
            
        Returns:
            Dictionary containing diagram data in multiple formats
        """
        if diagram_type == "class":
            return self._generate_class_diagram(classes, dependencies)
        elif diagram_type == "dependency":
            return self._generate_dependency_diagram(modules, dependencies)
        elif diagram_type == "component":
            return self._generate_component_diagram(modules, classes)
        else:
            return self._generate_class_diagram(classes, dependencies)
    
    def _generate_class_diagram(
        self,
        classes: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a class diagram."""
        
        # Generate PlantUML code
        plantuml = self._generate_plantuml_class(classes, dependencies)
        
        # Generate Graphviz DOT code
        dot = self._generate_dot_class(classes, dependencies)
        
        # Generate Mermaid code for web rendering
        mermaid = self._generate_mermaid_class(classes, dependencies)
        
        # Generate interactive JSON data
        json_data = self._generate_json_diagram_data(classes, dependencies)
        
        return {
            "type": "class",
            "plantuml": plantuml,
            "dot": dot,
            "mermaid": mermaid,
            "json": json_data,
            "node_count": len(classes),
            "edge_count": len(self._extract_class_edges(classes, dependencies))
        }
    
    def _generate_plantuml_class(
        self,
        classes: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> str:
        """Generate PlantUML class diagram code."""
        lines = ["@startuml", "skinparam classAttributeIconSize 0"]
        lines.append("skinparam class {")
        lines.append("    BackgroundColor #E8F4FD")
        lines.append("    BorderColor #2E86AB")
        lines.append("    ArrowColor #2E86AB")
        lines.append("}")
        lines.append("")
        
        # Define classes
        for cls in classes:
            class_type = "abstract class" if cls.get("is_abstract") else "class"
            lines.append(f'{class_type} "{cls["name"]}" {{')
            
            # Add attributes
            for attr in cls.get("attributes", [])[:10]:  # Limit to 10
                visibility = "-" if attr.startswith("_") else "+"
                lines.append(f"    {visibility} {attr}")
            
            # Add separator if both attributes and methods exist
            if cls.get("attributes") and cls.get("methods"):
                lines.append("    --")
            
            # Add methods
            for method in cls.get("methods", [])[:15]:  # Limit to 15
                visibility = "-" if method["name"].startswith("_") else "+"
                if method.get("is_static"):
                    visibility = "{static} " + visibility
                params = ", ".join([p.get("name", "") for p in method.get("parameters", [])[:3]])
                return_type = f": {method['return_type']}" if method.get("return_type") else ""
                lines.append(f"    {visibility} {method['name']}({params}){return_type}")
            
            lines.append("}")
            lines.append("")
        
        # Add inheritance relationships
        for cls in classes:
            for base in cls.get("bases", []):
                lines.append(f'"{base}" <|-- "{cls["name"]}"')
        
        # Add dependency relationships (grouped by target)
        seen_deps = set()
        for dep in dependencies:
            if dep.get("import_type") != "module":
                for name in dep.get("names", []):
                    # Check if this is a class we know about
                    if any(c["name"] == name for c in classes):
                        key = (dep["source"], name)
                        if key not in seen_deps:
                            lines.append(f'"{dep["source"]}" ..> "{name}" : uses')
                            seen_deps.add(key)
        
        lines.append("@enduml")
        return "\n".join(lines)
    
    def _generate_dot_class(
        self,
        classes: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> str:
        """Generate Graphviz DOT code for class diagram."""
        lines = [
            "digraph ClassDiagram {",
            "    rankdir=TB;",
            "    node [shape=record, fontname=\"Helvetica\", fontsize=10];",
            "    edge [fontname=\"Helvetica\", fontsize=9];",
            ""
        ]
        
        # Define class nodes
        for cls in classes:
            color = self.colors.get("abstract" if cls.get("is_abstract") else "class")
            
            # Build record label
            attrs = "\\l".join(cls.get("attributes", [])[:8])
            methods = "\\l".join([m["name"] + "()" for m in cls.get("methods", [])[:10]])
            
            label = f"{cls['name']}"
            if attrs:
                label += f"|{attrs}\\l"
            if methods:
                label += f"|{methods}\\l"
            
            lines.append(f'    "{cls["name"]}" [label="{{{label}}}", fillcolor="{color}", style=filled];')
        
        lines.append("")
        
        # Add inheritance edges
        for cls in classes:
            for base in cls.get("bases", []):
                lines.append(f'    "{base}" -> "{cls["name"]}" [arrowhead=empty, style=solid];')
        
        lines.append("}")
        return "\n".join(lines)
    
    def _sanitize_mermaid_id(self, name: str) -> str:
        """Sanitize a name for use as Mermaid identifier."""
        import re
        # Remove or replace special characters
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized or 'unnamed'
    
    def _sanitize_mermaid_label(self, text: str) -> str:
        """Sanitize text for use in Mermaid labels."""
        # Remove characters that break Mermaid syntax
        return text.replace('"', "'").replace('<', '').replace('>', '').replace(':', '_').replace('|', '_')
    
    def _generate_mermaid_class(
        self,
        classes: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> str:
        """Generate Mermaid class diagram code for web rendering."""
        lines = ["classDiagram"]
        
        # Handle empty case
        if not classes:
            lines.append("    class NoClassesFound {")
            lines.append("        +No classes detected")
            lines.append("    }")
            return "\n".join(lines)
        
        # Add direction for better layout
        lines.append("    direction TB")
        lines.append("")
        
        # Define classes with proper structure
        for cls in classes:
            cls_name = self._sanitize_mermaid_id(cls.get("name", "Unknown"))
            
            # Start class definition
            lines.append(f'    class {cls_name} {{')
            
            # Add attributes first
            attrs = cls.get("attributes", [])[:6]
            for attr in attrs:
                attr_name = self._sanitize_mermaid_label(attr)
                visibility = "-" if attr_name.startswith("_") else "+"
                lines.append(f'        {visibility}{attr_name}')
            
            # Add methods
            methods = cls.get("methods", [])
            for method in methods[:8]:
                method_name = self._sanitize_mermaid_label(method.get("name", "method"))
                visibility = "-" if method_name.startswith("_") else "+"
                params_list = method.get("parameters", [])[:2]
                params = ", ".join([self._sanitize_mermaid_label(p.get("name", "")) for p in params_list if p.get("name") and p.get("name") != "self"])
                lines.append(f'        {visibility}{method_name}({params})')
        
            lines.append('    }')
            lines.append('')
        
        # Add relationships
        lines.append("    %% Relationships")
        for cls in classes:
            cls_name = self._sanitize_mermaid_id(cls.get("name", ""))
            for base in cls.get("bases", []):
                base_name = self._sanitize_mermaid_id(base)
                lines.append(f'    {base_name} <|-- {cls_name} : extends')
        
        # Add styling notes
        lines.append("")
        lines.append("    %% Styling")
        
        return "\n".join(lines)
    
    def _generate_dependency_diagram(
        self,
        modules: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a module dependency diagram."""
        
        # Build dependency graph
        module_names = {m.get("name", "") for m in modules if m.get("name")}
        
        mermaid_lines = ["flowchart LR"]
        
        # Handle empty case
        if not modules:
            mermaid_lines.append('    empty["📦 No modules found"]')
            return {
                "type": "dependency",
                "mermaid": "\n".join(mermaid_lines),
                "dot": "",
                "node_count": 0,
                "edge_count": 0
            }
        
        # Style definitions with better colors
        mermaid_lines.append("    classDef module fill:#6366f1,stroke:#8b5cf6,color:#fff,stroke-width:2px")
        mermaid_lines.append("    classDef external fill:#374151,stroke:#6b7280,color:#d1d5db,stroke-width:1px,stroke-dasharray:5")
        mermaid_lines.append("    classDef core fill:#10b981,stroke:#059669,color:#fff,stroke-width:2px")
        mermaid_lines.append("")
        
        # Track dependency counts to identify core modules
        dep_counts = {}
        for dep in dependencies:
            target = dep.get("target", "")
            if target:
                dep_counts[target] = dep_counts.get(target, 0) + 1
        
        # Add module nodes with icons
        added_nodes = set()
        for module in modules:
            module_name = module.get("name", "")
            if not module_name:
                continue
            node_id = self._sanitize_mermaid_id(module_name)
            if node_id not in added_nodes:
                display_name = self._sanitize_mermaid_label(module_name)
                # Use rounded rectangle for modules
                is_core = dep_counts.get(module_name, 0) >= 3
                style_class = "core" if is_core else "module"
                mermaid_lines.append(f'    {node_id}["📦 {display_name}"]:::{style_class}')
                added_nodes.add(node_id)
        
        mermaid_lines.append("")
        
        # Add dependency edges with better styling
        seen_edges = set()
        for dep in dependencies:
            source_name = dep.get("source", "")
            target_name = dep.get("target", "")
            
            if not source_name or not target_name:
                continue
                
            source = self._sanitize_mermaid_id(source_name)
            target = self._sanitize_mermaid_id(target_name)
            
            if source and target and (source, target) not in seen_edges:
                if target_name in module_names:
                    mermaid_lines.append(f"    {source} --> {target}")
                else:
                    # External dependency
                    if target not in added_nodes:
                        display_name = self._sanitize_mermaid_label(target_name)
                        mermaid_lines.append(f'    {target}["📚 {display_name}"]:::external')
                        added_nodes.add(target)
                    mermaid_lines.append(f"    {source} -.-> {target}")
                seen_edges.add((source, target))
        
        # Generate DOT version
        dot_lines = [
            "digraph Dependencies {",
            "    rankdir=LR;",
            "    node [shape=box, fontname=\"Helvetica\", style=filled];",
            "    edge [color=\"#6366f1\"];",
            ""
        ]
        
        for module in modules:
            if module.get("name"):
                color = self.colors["module"]
                dot_lines.append(f'    "{module["name"]}" [fillcolor="{color}"];')
        
        for source, target in seen_edges:
            dot_lines.append(f'    "{source}" -> "{target}";')
        
        dot_lines.append("}")
        
        return {
            "type": "dependency",
            "mermaid": "\n".join(mermaid_lines),
            "dot": "\n".join(dot_lines),
            "node_count": len(modules),
            "edge_count": len(seen_edges)
        }
    
    def _generate_component_diagram(
        self,
        modules: List[Dict[str, Any]],
        classes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a component diagram showing module-class relationships."""
        
        mermaid_lines = ["flowchart TB"]
        
        # Handle empty case
        if not modules and not classes:
            mermaid_lines.append('    empty["📦 No components found"]')
            return {
                "type": "component",
                "mermaid": "\n".join(mermaid_lines),
                "node_count": 0
            }
        
        # Add styling
        mermaid_lines.append("    classDef classNode fill:#10b981,stroke:#059669,color:#fff")
        mermaid_lines.append("    classDef funcNode fill:#f59e0b,stroke:#d97706,color:#fff")
        mermaid_lines.append("")
        
        # Group classes by module
        module_classes = {}
        module_functions = {}
        for cls in classes:
            module = cls.get("module", "unknown")
            if module not in module_classes:
                module_classes[module] = []
            cls_name = cls.get("name", "Unknown")
            module_classes[module].append(cls_name)
        
        # Create subgraphs for each module
        subgraph_count = 0
        for module in modules:
            module_name = module.get("name", "")
            if not module_name:
                continue
                
            node_id = self._sanitize_mermaid_id(module_name)
            display_name = self._sanitize_mermaid_label(module_name)
            
            mermaid_lines.append(f'    subgraph {node_id}["📦 {display_name}"]')
            mermaid_lines.append(f'        direction TB')
            
            classes_in_module = module_classes.get(module_name, [])
            if classes_in_module:
                for cls_name in classes_in_module[:8]:  # Limit classes per module
                    cls_id = self._sanitize_mermaid_id(f"{module_name}_{cls_name}")
                    cls_display = self._sanitize_mermaid_label(cls_name)
                    mermaid_lines.append(f'        {cls_id}["🔷 {cls_display}"]:::classNode')
            else:
                # Add placeholder if no classes
                placeholder_id = self._sanitize_mermaid_id(f"{module_name}_empty")
                func_count = module.get("function_count", 0)
                if func_count > 0:
                    mermaid_lines.append(f'        {placeholder_id}["ƒ {func_count} functions"]:::funcNode')
                else:
                    mermaid_lines.append(f'        {placeholder_id}(["Empty module"])')
            
            mermaid_lines.append("    end")
            mermaid_lines.append("")
            subgraph_count += 1
        
        # If no valid modules, show classes directly
        if subgraph_count == 0 and classes:
            for cls in classes[:15]:
                cls_name = cls.get("name", "Unknown")
                cls_id = self._sanitize_mermaid_id(cls_name)
                cls_display = self._sanitize_mermaid_label(cls_name)
                mermaid_lines.append(f'    {cls_id}["🔷 {cls_display}"]:::classNode')
        
        return {
            "type": "component",
            "mermaid": "\n".join(mermaid_lines),
            "node_count": len(modules) + len(classes)
        }
    
    def _generate_json_diagram_data(
        self,
        classes: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate JSON data for interactive diagram rendering."""
        nodes = []
        edges = []
        
        # Create nodes for each class
        for i, cls in enumerate(classes):
            nodes.append({
                "id": cls["name"],
                "label": cls["name"],
                "type": "abstract" if cls.get("is_abstract") else "class",
                "module": cls.get("module", ""),
                "methods": [m["name"] for m in cls.get("methods", [])],
                "attributes": cls.get("attributes", []),
                "x": (i % 5) * 200,
                "y": (i // 5) * 150
            })
        
        # Create edges for inheritance
        edge_id = 0
        for cls in classes:
            for base in cls.get("bases", []):
                edges.append({
                    "id": f"e{edge_id}",
                    "source": base,
                    "target": cls["name"],
                    "type": "inheritance",
                    "label": "extends"
                })
                edge_id += 1
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def _extract_class_edges(
        self,
        classes: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Extract edges from class relationships."""
        edges = []
        
        for cls in classes:
            for base in cls.get("bases", []):
                edges.append({
                    "source": base,
                    "target": cls["name"],
                    "type": "inheritance"
                })
        
        return edges
    
    def render_to_svg(self, dot_code: str) -> Optional[str]:
        """
        Render DOT code to SVG using Graphviz.
        
        Args:
            dot_code: Graphviz DOT code
            
        Returns:
            SVG string or None if rendering fails
        """
        try:
            # Write DOT to temp file
            dot_file = Path(self.output_dir) / "temp.dot"
            svg_file = Path(self.output_dir) / "temp.svg"
            
            with open(dot_file, 'w') as f:
                f.write(dot_code)
            
            # Run Graphviz
            result = subprocess.run(
                ["dot", "-Tsvg", str(dot_file), "-o", str(svg_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and svg_file.exists():
                with open(svg_file, 'r') as f:
                    return f.read()
            else:
                print(f"Graphviz error: {result.stderr}")
                return None
                
        except FileNotFoundError:
            print("Graphviz not installed. Install with: apt-get install graphviz")
            return None
        except Exception as e:
            print(f"SVG rendering error: {e}")
            return None
    
    def render_to_png_base64(self, dot_code: str) -> Optional[str]:
        """
        Render DOT code to base64-encoded PNG.
        
        Args:
            dot_code: Graphviz DOT code
            
        Returns:
            Base64 encoded PNG or None if rendering fails
        """
        try:
            dot_file = Path(self.output_dir) / "temp.dot"
            png_file = Path(self.output_dir) / "temp.png"
            
            with open(dot_file, 'w') as f:
                f.write(dot_code)
            
            result = subprocess.run(
                ["dot", "-Tpng", str(dot_file), "-o", str(png_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and png_file.exists():
                with open(png_file, 'rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')
            return None
            
        except Exception as e:
            print(f"PNG rendering error: {e}")
            return None
