"""
CodeVision AI - Test Suite
Tests for parsers, analyzers, and API endpoints.
"""

import pytest
import tempfile
import os
from pathlib import Path

# Import modules to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.python_parser import PythonCodeParser, PythonProjectAnalyzer
from parsers.javascript_parser import JavaScriptCodeParser
from visualization.diagram_generator import DiagramGenerator


# Sample Python code for testing
SAMPLE_PYTHON_CODE = '''
"""Sample module for testing CodeVision AI."""

from typing import List, Optional
from dataclasses import dataclass


@dataclass
class BaseModel:
    """Base class for all models."""
    
    id: int
    name: str
    
    def save(self) -> bool:
        """Save the model to database."""
        return True
    
    def _validate(self) -> None:
        """Internal validation method."""
        pass


class UserModel(BaseModel):
    """User model with authentication."""
    
    email: str
    password_hash: str
    
    def __init__(self, id: int, name: str, email: str):
        super().__init__(id=id, name=name)
        self.email = email
        self.password_hash = ""
    
    def authenticate(self, password: str) -> bool:
        """Authenticate user with password."""
        return self._check_password(password)
    
    def _check_password(self, password: str) -> bool:
        """Check password hash."""
        return True
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password."""
        return f"hashed_{password}"


def get_user_by_id(user_id: int) -> Optional[UserModel]:
    """Retrieve a user by ID."""
    return None


async def fetch_users() -> List[UserModel]:
    """Fetch all users asynchronously."""
    return []
'''

SAMPLE_JS_CODE = '''
import { Database } from './database';
import * as utils from './utils';

/**
 * Base model class
 */
class BaseModel {
    constructor(id, name) {
        this.id = id;
        this.name = name;
    }
    
    async save() {
        return true;
    }
    
    _validate() {
        return true;
    }
}

/**
 * User model extending base
 */
class UserModel extends BaseModel {
    constructor(id, name, email) {
        super(id, name);
        this.email = email;
    }
    
    async authenticate(password) {
        return this._checkPassword(password);
    }
    
    _checkPassword(password) {
        return true;
    }
    
    static hashPassword(password) {
        return `hashed_${password}`;
    }
}

export async function getUserById(userId) {
    return null;
}

export const fetchUsers = async () => {
    return [];
};
'''


class TestPythonParser:
    """Tests for Python code parser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = PythonCodeParser()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parse_file_basic(self):
        """Test basic file parsing."""
        # Write sample code to temp file
        file_path = Path(self.temp_dir) / "sample.py"
        file_path.write_text(SAMPLE_PYTHON_CODE)
        
        result = self.parser.parse_file(file_path)
        
        assert result is not None
        assert "module" in result
        assert "classes" in result
        assert "functions" in result
        assert "dependencies" in result
    
    def test_extract_classes(self):
        """Test class extraction."""
        file_path = Path(self.temp_dir) / "sample.py"
        file_path.write_text(SAMPLE_PYTHON_CODE)
        
        result = self.parser.parse_file(file_path)
        classes = result["classes"]
        
        assert len(classes) == 2
        
        # Check BaseModel
        base_model = next(c for c in classes if c["name"] == "BaseModel")
        assert "dataclass" in base_model["decorators"]
        assert "save" in [m["name"] for m in base_model["methods"]]
        assert "_validate" in [m["name"] for m in base_model["methods"]]
        
        # Check UserModel
        user_model = next(c for c in classes if c["name"] == "UserModel")
        assert "BaseModel" in user_model["bases"]
        assert "authenticate" in [m["name"] for m in user_model["methods"]]
    
    def test_extract_functions(self):
        """Test function extraction."""
        file_path = Path(self.temp_dir) / "sample.py"
        file_path.write_text(SAMPLE_PYTHON_CODE)
        
        result = self.parser.parse_file(file_path)
        functions = result["functions"]
        
        assert len(functions) == 2
        
        # Check get_user_by_id
        get_user = next(f for f in functions if f["name"] == "get_user_by_id")
        assert get_user["is_async"] == False
        assert get_user["return_type"] == "Optional[UserModel]"
        
        # Check fetch_users
        fetch = next(f for f in functions if f["name"] == "fetch_users")
        assert fetch["is_async"] == True
    
    def test_extract_imports(self):
        """Test import extraction."""
        file_path = Path(self.temp_dir) / "sample.py"
        file_path.write_text(SAMPLE_PYTHON_CODE)
        
        result = self.parser.parse_file(file_path)
        dependencies = result["dependencies"]
        
        assert len(dependencies) >= 2
        
        # Check typing import
        typing_import = next((d for d in dependencies if d["target"] == "typing"), None)
        assert typing_import is not None
        assert "List" in typing_import["names"]
        assert "Optional" in typing_import["names"]
    
    def test_method_details(self):
        """Test detailed method extraction."""
        file_path = Path(self.temp_dir) / "sample.py"
        file_path.write_text(SAMPLE_PYTHON_CODE)
        
        result = self.parser.parse_file(file_path)
        user_model = next(c for c in result["classes"] if c["name"] == "UserModel")
        
        # Check authenticate method
        auth_method = next(m for m in user_model["methods"] if m["name"] == "authenticate")
        assert auth_method["is_private"] == False
        assert "password" in [p["name"] for p in auth_method["parameters"]]
        assert auth_method["return_type"] == "bool"
        
        # Check static method
        hash_method = next(m for m in user_model["methods"] if m["name"] == "hash_password")
        assert "staticmethod" in hash_method["decorators"]


class TestJavaScriptParser:
    """Tests for JavaScript/TypeScript parser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = JavaScriptCodeParser()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parse_file_basic(self):
        """Test basic JS file parsing."""
        file_path = Path(self.temp_dir) / "sample.js"
        file_path.write_text(SAMPLE_JS_CODE)
        
        result = self.parser.parse_file(file_path)
        
        assert result is not None
        assert "module" in result
        assert "classes" in result
        assert "functions" in result
        assert "dependencies" in result
    
    def test_extract_classes(self):
        """Test JS class extraction."""
        file_path = Path(self.temp_dir) / "sample.js"
        file_path.write_text(SAMPLE_JS_CODE)
        
        result = self.parser.parse_file(file_path)
        classes = result["classes"]
        
        assert len(classes) >= 2
        
        # Check UserModel extends BaseModel
        user_model = next((c for c in classes if c["name"] == "UserModel"), None)
        assert user_model is not None
        assert user_model["extends"] == "BaseModel"
    
    def test_extract_imports(self):
        """Test import extraction."""
        file_path = Path(self.temp_dir) / "sample.js"
        file_path.write_text(SAMPLE_JS_CODE)
        
        result = self.parser.parse_file(file_path)
        dependencies = result["dependencies"]
        
        assert len(dependencies) >= 2
        
        # Check Database import
        db_import = next((d for d in dependencies if "database" in d.get("full_path", "")), None)
        assert db_import is not None


class TestDiagramGenerator:
    """Tests for diagram generation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = DiagramGenerator()
        
        self.sample_classes = [
            {
                "name": "BaseModel",
                "module": "models",
                "bases": [],
                "methods": [
                    {"name": "save", "parameters": [], "return_type": "bool"},
                    {"name": "_validate", "parameters": [], "return_type": None}
                ],
                "attributes": ["id", "name"]
            },
            {
                "name": "UserModel",
                "module": "models",
                "bases": ["BaseModel"],
                "methods": [
                    {"name": "authenticate", "parameters": [{"name": "password"}], "return_type": "bool"}
                ],
                "attributes": ["email"]
            }
        ]
        
        self.sample_dependencies = [
            {"source": "main", "target": "models", "import_type": "from", "names": ["UserModel"]},
            {"source": "main", "target": "typing", "import_type": "from", "names": ["List"]}
        ]
    
    def test_generate_class_diagram(self):
        """Test class diagram generation."""
        result = self.generator.generate_uml_diagram(
            modules=[],
            classes=self.sample_classes,
            dependencies=self.sample_dependencies,
            diagram_type="class"
        )
        
        assert result["type"] == "class"
        assert "plantuml" in result
        assert "mermaid" in result
        assert "json" in result
        
        # Check PlantUML contains classes
        assert "BaseModel" in result["plantuml"]
        assert "UserModel" in result["plantuml"]
        assert "<|--" in result["plantuml"]  # Inheritance arrow
    
    def test_generate_mermaid_diagram(self):
        """Test Mermaid diagram generation."""
        result = self.generator.generate_uml_diagram(
            modules=[],
            classes=self.sample_classes,
            dependencies=self.sample_dependencies,
            diagram_type="class"
        )
        
        mermaid = result["mermaid"]
        
        assert "classDiagram" in mermaid
        assert "BaseModel" in mermaid
        assert "UserModel" in mermaid
    
    def test_generate_dependency_diagram(self):
        """Test dependency diagram generation."""
        modules = [
            {"name": "main", "file": "main.py"},
            {"name": "models", "file": "models.py"}
        ]
        
        result = self.generator.generate_uml_diagram(
            modules=modules,
            classes=[],
            dependencies=self.sample_dependencies,
            diagram_type="dependency"
        )
        
        assert result["type"] == "dependency"
        assert "mermaid" in result
        assert "graph" in result["mermaid"]
    
    def test_json_diagram_data(self):
        """Test JSON diagram data structure."""
        result = self.generator.generate_uml_diagram(
            modules=[],
            classes=self.sample_classes,
            dependencies=self.sample_dependencies,
            diagram_type="class"
        )
        
        json_data = result["json"]
        
        assert "nodes" in json_data
        assert "edges" in json_data
        assert len(json_data["nodes"]) == 2
        
        # Check node structure
        user_node = next(n for n in json_data["nodes"] if n["id"] == "UserModel")
        assert "label" in user_node
        assert "methods" in user_node
        
        # Check edge for inheritance
        assert len(json_data["edges"]) >= 1
        inheritance_edge = json_data["edges"][0]
        assert inheritance_edge["source"] == "BaseModel"
        assert inheritance_edge["target"] == "UserModel"


class TestProjectAnalyzer:
    """Tests for project-level analysis."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = PythonProjectAnalyzer()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_analyze_project(self):
        """Test full project analysis."""
        # Create a mini project structure
        models_dir = Path(self.temp_dir) / "models"
        models_dir.mkdir()
        
        (models_dir / "__init__.py").write_text('"""Models package."""')
        (models_dir / "base.py").write_text('''
class BaseModel:
    def save(self): pass
''')
        (models_dir / "user.py").write_text('''
from .base import BaseModel

class UserModel(BaseModel):
    def authenticate(self): pass
''')
        
        (Path(self.temp_dir) / "main.py").write_text('''
from models.user import UserModel

def main():
    user = UserModel()
''')
        
        result = self.analyzer.analyze_project(Path(self.temp_dir))
        
        assert len(result["modules"]) >= 3
        assert len(result["classes"]) >= 2
        assert result["statistics"]["total_files"] >= 3


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
