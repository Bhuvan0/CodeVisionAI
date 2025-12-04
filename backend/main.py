"""
CodeVision AI - Main FastAPI Backend
An LLM-Powered Reverse Engineering Diagram Generator
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv
_env_path = Path(__file__).parent.parent / ".env"
print(f"[CodeVision] Loading .env from: {_env_path}")
load_dotenv(_env_path)

import os
print(f"[CodeVision] GOOGLE_API_KEY loaded: {'Yes' if os.environ.get('GOOGLE_API_KEY') else 'No'}")

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from parsers.python_parser import PythonCodeParser
from parsers.javascript_parser import JavaScriptCodeParser
from llm.analyzer import CodeAnalyzer
from visualization.diagram_generator import DiagramGenerator
import re


def parse_generic_code_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Basic parser for other programming languages.
    Uses regex patterns to extract classes, functions, and imports.
    """
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return None
    
    ext = file_path.suffix.lower()
    module_name = file_path.stem
    
    classes = []
    functions = []
    dependencies = []
    
    # Language-specific patterns
    if ext in ['.java', '.kt']:
        # Java/Kotlin
        class_pattern = r'(?:public\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+[\w,\s]+)?'
        func_pattern = r'(?:public|private|protected)?\s*(?:static\s+)?(?:\w+)\s+(\w+)\s*\([^)]*\)'
        import_pattern = r'import\s+([\w.]+)'
    elif ext == '.go':
        # Go
        class_pattern = r'type\s+(\w+)\s+struct'
        func_pattern = r'func\s+(?:\([^)]+\)\s+)?(\w+)\s*\('
        import_pattern = r'import\s+(?:"([^"]+)"|\(\s*"([^"]+)")'
    elif ext == '.rs':
        # Rust
        class_pattern = r'(?:pub\s+)?struct\s+(\w+)'
        func_pattern = r'(?:pub\s+)?fn\s+(\w+)'
        import_pattern = r'use\s+([\w:]+)'
    elif ext == '.rb':
        # Ruby
        class_pattern = r'class\s+(\w+)(?:\s*<\s*(\w+))?'
        func_pattern = r'def\s+(\w+)'
        import_pattern = r'require\s+[\'"]([^\'"]+)[\'"]'
    elif ext == '.php':
        # PHP
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?'
        func_pattern = r'(?:public|private|protected)?\s*function\s+(\w+)'
        import_pattern = r'use\s+([\w\\\\]+)'
    elif ext in ['.cs']:
        # C#
        class_pattern = r'(?:public\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s*:\s*(\w+))?'
        func_pattern = r'(?:public|private|protected)?\s*(?:static\s+)?(?:\w+)\s+(\w+)\s*\('
        import_pattern = r'using\s+([\w.]+)'
    elif ext == '.swift':
        # Swift
        class_pattern = r'class\s+(\w+)(?:\s*:\s*(\w+))?'
        func_pattern = r'func\s+(\w+)'
        import_pattern = r'import\s+(\w+)'
    elif ext in ['.c', '.cpp', '.h', '.hpp']:
        # C/C++
        class_pattern = r'class\s+(\w+)(?:\s*:\s*(?:public|private|protected)\s+(\w+))?'
        func_pattern = r'(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*{'
        import_pattern = r'#include\s*[<"]([^>"]+)[>"]'
    else:
        return None
    
    # Extract classes
    for match in re.finditer(class_pattern, content):
        cls_name = match.group(1)
        base = match.group(2) if len(match.groups()) > 1 else None
        classes.append({
            "name": cls_name,
            "bases": [base] if base else [],
            "methods": [],
            "attributes": [],
            "module": module_name
        })
    
    # Extract functions
    for match in re.finditer(func_pattern, content):
        func_name = match.group(1)
        if func_name not in ['if', 'for', 'while', 'switch', 'catch']:
            functions.append({
                "name": func_name,
                "parameters": [],
                "module": module_name
            })
    
    # Extract imports
    for match in re.finditer(import_pattern, content):
        imp = match.group(1) or (match.group(2) if len(match.groups()) > 1 else None)
        if imp:
            dependencies.append({
                "source": module_name,
                "target": imp.split('.')[-1] if '.' in imp else imp,
                "import_type": "module"
            })
    
    lines = content.split('\n')
    
    return {
        "module": {
            "name": module_name,
            "file": str(file_path),
            "language": ext[1:],  # Remove the dot
            "class_count": len(classes),
            "function_count": len(functions),
            "line_count": len(lines)
        },
        "classes": classes,
        "functions": functions,
        "dependencies": dependencies
    }

app = FastAPI(
    title="CodeVision AI",
    description="LLM-Powered Reverse Engineering Diagram Generator",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store analysis results in memory (use Redis/DB in production)
analysis_cache: Dict[str, Any] = {}


class AnalysisRequest(BaseModel):
    project_id: str
    include_private: bool = False
    diagram_type: str = "class"  # class, dependency, sequence


class ModuleQuery(BaseModel):
    project_id: str
    module_name: str


class ChatQuery(BaseModel):
    project_id: str
    message: str
    chat_history: Optional[List[Dict[str, str]]] = None


class GitHubImport(BaseModel):
    owner: str
    repo: str
    branch: str = "main"


class AnalysisResponse(BaseModel):
    project_id: str
    status: str
    modules: List[Dict[str, Any]]
    classes: List[Dict[str, Any]]
    functions: List[Dict[str, Any]]
    dependencies: List[Dict[str, Any]]
    diagram_url: Optional[str] = None
    summaries: Dict[str, str] = {}


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CodeVision AI</title>
        <meta http-equiv="refresh" content="0; url=/app">
    </head>
    <body>
        <p>Redirecting to CodeVision AI Dashboard...</p>
    </body>
    </html>
    """


@app.post("/api/upload")
async def upload_project(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload a project (multiple files or a zip archive).
    Returns a project_id for tracking the analysis.
    """
    project_id = f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
    
    # Create temporary directory for the project
    project_dir = Path(tempfile.mkdtemp(prefix=f"codevision_{project_id}_"))
    
    try:
        for file in files:
            file_path = project_dir / file.filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            content = await file.read()
            
            # Handle zip files
            if file.filename.endswith('.zip'):
                import zipfile
                import io
                with zipfile.ZipFile(io.BytesIO(content), 'r') as zip_ref:
                    zip_ref.extractall(project_dir)
            else:
                with open(file_path, 'wb') as f:
                    f.write(content)
        
        # Initialize analysis cache entry
        analysis_cache[project_id] = {
            "status": "uploaded",
            "project_dir": str(project_dir),
            "created_at": datetime.now().isoformat(),
            "files": [str(f) for f in project_dir.rglob("*") if f.is_file()]
        }
        
        return {
            "project_id": project_id,
            "status": "uploaded",
            "file_count": len(analysis_cache[project_id]["files"]),
            "message": "Project uploaded successfully. Call /api/analyze to start analysis."
        }
        
    except Exception as e:
        shutil.rmtree(project_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/api/analyze")
async def analyze_project(request: AnalysisRequest):
    """
    Analyze an uploaded project using static analysis and LLM reasoning.
    """
    project_id = request.project_id
    
    if project_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_data = analysis_cache[project_id]
    project_dir = Path(project_data["project_dir"])
    
    try:
        # Update status
        analysis_cache[project_id]["status"] = "analyzing"
        
        # Initialize parsers
        python_parser = PythonCodeParser()
        js_parser = JavaScriptCodeParser()
        
        # Collect all parsed data
        all_modules = []
        all_classes = []
        all_functions = []
        all_dependencies = []
        
        # Supported file patterns
        PYTHON_PATTERNS = ["*.py"]
        JS_PATTERNS = ["*.js", "*.jsx", "*.ts", "*.tsx", "*.vue"]
        OTHER_CODE_PATTERNS = ["*.java", "*.go", "*.rs", "*.rb", "*.php", "*.cs", "*.kt", "*.swift", "*.c", "*.cpp", "*.h", "*.hpp"]
        SKIP_DIRS = ["__pycache__", "node_modules", ".git", "venv", ".venv", "dist", "build", "target", "bin", "obj"]
        
        def should_skip(file_path):
            return any(skip in str(file_path) for skip in SKIP_DIRS)
        
        # Parse Python files
        for pattern in PYTHON_PATTERNS:
            for py_file in project_dir.rglob(pattern):
                if should_skip(py_file):
                    continue
                result = python_parser.parse_file(py_file)
                if result:
                    all_modules.append(result["module"])
                    all_classes.extend(result.get("classes", []))
                    all_functions.extend(result.get("functions", []))
                    all_dependencies.extend(result.get("dependencies", []))
        
        # Parse JavaScript/TypeScript files
        for pattern in JS_PATTERNS:
            for js_file in project_dir.rglob(pattern):
                if should_skip(js_file):
                    continue
                result = js_parser.parse_file(js_file)
                if result:
                    all_modules.append(result["module"])
                    all_classes.extend(result.get("classes", []))
                    all_functions.extend(result.get("functions", []))
                    all_dependencies.extend(result.get("dependencies", []))
        
        # Parse other code files (basic parsing)
        for pattern in OTHER_CODE_PATTERNS:
            for code_file in project_dir.rglob(pattern):
                if should_skip(code_file):
                    continue
                result = parse_generic_code_file(code_file)
                if result:
                    all_modules.append(result["module"])
                    all_classes.extend(result.get("classes", []))
                    all_functions.extend(result.get("functions", []))
                    all_dependencies.extend(result.get("dependencies", []))
        
        # Use LLM to generate summaries and insights
        analyzer = CodeAnalyzer()
        summaries = {}
        
        for module in all_modules:
            summary = await analyzer.generate_module_summary(module)
            summaries[module["name"]] = summary
        
        # Generate relationship insights
        relationship_insights = await analyzer.analyze_relationships(
            all_classes, all_dependencies
        )
        
        # Generate diagram
        diagram_gen = DiagramGenerator()
        diagram_data = diagram_gen.generate_uml_diagram(
            modules=all_modules,
            classes=all_classes,
            dependencies=all_dependencies,
            diagram_type=request.diagram_type
        )
        
        # Update cache with results
        analysis_cache[project_id].update({
            "status": "completed",
            "modules": all_modules,
            "classes": all_classes,
            "functions": all_functions,
            "dependencies": all_dependencies,
            "summaries": summaries,
            "relationship_insights": relationship_insights,
            "diagram": diagram_data,
            "analyzed_at": datetime.now().isoformat()
        })
        
        return AnalysisResponse(
            project_id=project_id,
            status="completed",
            modules=all_modules,
            classes=all_classes,
            functions=all_functions,
            dependencies=all_dependencies,
            summaries=summaries
        )
        
    except Exception as e:
        analysis_cache[project_id]["status"] = "failed"
        analysis_cache[project_id]["error"] = str(e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/project/{project_id}")
async def get_project(project_id: str):
    """Get the analysis results for a project."""
    if project_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return analysis_cache[project_id]


@app.get("/api/project/{project_id}/diagram")
async def get_diagram(project_id: str, diagram_type: str = "class"):
    """Get the generated diagram for a project."""
    if project_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_data = analysis_cache[project_id]
    
    if project_data["status"] != "completed":
        raise HTTPException(status_code=400, detail="Analysis not yet completed")
    
    # Regenerate diagram if different type requested
    if diagram_type != project_data.get("diagram", {}).get("type"):
        diagram_gen = DiagramGenerator()
        diagram_data = diagram_gen.generate_uml_diagram(
            modules=project_data["modules"],
            classes=project_data["classes"],
            dependencies=project_data["dependencies"],
            diagram_type=diagram_type
        )
        analysis_cache[project_id]["diagram"] = diagram_data
    
    return analysis_cache[project_id]["diagram"]


@app.post("/api/explain")
async def explain_module(query: ModuleQuery):
    """Get a detailed LLM-generated explanation for a specific module."""
    if query.project_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_data = analysis_cache[query.project_id]
    
    # Find the module
    module = None
    for m in project_data.get("modules", []):
        if m["name"] == query.module_name:
            module = m
            break
    
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Generate detailed explanation
    analyzer = CodeAnalyzer()
    explanation = await analyzer.generate_detailed_explanation(
        module=module,
        classes=[c for c in project_data.get("classes", []) if c.get("module") == query.module_name],
        dependencies=[d for d in project_data.get("dependencies", []) if d.get("source") == query.module_name]
    )
    
    return {
        "module": query.module_name,
        "explanation": explanation
    }


@app.get("/api/search")
async def search_codebase(project_id: str, query: str):
    """Search for classes, functions, or modules matching a query."""
    if project_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_data = analysis_cache[project_id]
    query_lower = query.lower()
    
    results = {
        "modules": [],
        "classes": [],
        "functions": []
    }
    
    for module in project_data.get("modules", []):
        if query_lower in module["name"].lower():
            results["modules"].append(module)
    
    for cls in project_data.get("classes", []):
        if query_lower in cls["name"].lower():
            results["classes"].append(cls)
    
    for func in project_data.get("functions", []):
        if query_lower in func["name"].lower():
            results["functions"].append(func)
    
    return results


@app.delete("/api/project/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and its associated data."""
    if project_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_data = analysis_cache[project_id]
    
    # Clean up temporary files
    if "project_dir" in project_data:
        shutil.rmtree(project_data["project_dir"], ignore_errors=True)
    
    del analysis_cache[project_id]
    
    return {"message": "Project deleted successfully"}


@app.post("/api/github")
async def import_from_github(data: GitHubImport):
    """
    Import a project from a public GitHub repository.
    Downloads the repository as a ZIP and extracts it for analysis.
    """
    import urllib.request
    import zipfile
    import io
    
    project_id = f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
    project_dir = Path(tempfile.mkdtemp(prefix=f"codevision_{project_id}_"))
    
    try:
        # Download repository as ZIP
        zip_url = f"https://github.com/{data.owner}/{data.repo}/archive/refs/heads/{data.branch}.zip"
        
        # Try main branch first, then master
        try:
            with urllib.request.urlopen(zip_url, timeout=30) as response:
                zip_data = response.read()
        except:
            zip_url = f"https://github.com/{data.owner}/{data.repo}/archive/refs/heads/master.zip"
            with urllib.request.urlopen(zip_url, timeout=30) as response:
                zip_data = response.read()
        
        # Extract ZIP
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_ref:
            zip_ref.extractall(project_dir)
        
        # Get list of files
        all_files = [str(f) for f in project_dir.rglob("*") if f.is_file()]
        
        # Initialize analysis cache entry
        analysis_cache[project_id] = {
            "status": "uploaded",
            "project_dir": str(project_dir),
            "created_at": datetime.now().isoformat(),
            "files": all_files,
            "source": "github",
            "repo": f"{data.owner}/{data.repo}"
        }
        
        return {
            "project_id": project_id,
            "status": "uploaded",
            "file_count": len(all_files),
            "repo": f"{data.owner}/{data.repo}",
            "message": "Repository imported successfully. Call /api/analyze to start analysis."
        }
        
    except urllib.error.HTTPError as e:
        shutil.rmtree(project_dir, ignore_errors=True)
        if e.code == 404:
            raise HTTPException(status_code=404, detail=f"Repository not found: {data.owner}/{data.repo}")
        raise HTTPException(status_code=e.code, detail=f"GitHub error: {str(e)}")
    except Exception as e:
        shutil.rmtree(project_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@app.post("/api/chat")
async def chat_about_project(query: ChatQuery):
    """
    Chat with AI about the uploaded project.
    Ask questions about the codebase structure, classes, functions, etc.
    """
    if query.project_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="Project not found. Please upload a project first.")
    
    project_data = analysis_cache[query.project_id]
    
    if project_data.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Project analysis not yet completed.")
    
    try:
        analyzer = CodeAnalyzer()
        
        response = await analyzer.chat_about_project(
            question=query.message,
            modules=project_data.get("modules", []),
            classes=project_data.get("classes", []),
            functions=project_data.get("functions", []),
            dependencies=project_data.get("dependencies", []),
            chat_history=query.chat_history
        )
        
        # Determine which model is being used
        model_info = "basic"
        if analyzer.llm:
            model_name = getattr(analyzer.llm, 'model', None) or getattr(analyzer.llm, 'model_name', 'AI')
            model_info = str(model_name)
        
        return {
            "response": response,
            "project_id": query.project_id,
            "model": model_info
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


# Mount static files - calculate path relative to this file
_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir), html=False), name="static")


# Serve index.html with no-cache headers
@app.get("/app", response_class=HTMLResponse)
async def serve_app():
    """Serve the main app with no-cache headers."""
    index_path = _static_dir / "index.html"
    if index_path.exists():
        content = index_path.read_text(encoding="utf-8")
        return HTMLResponse(content=content, headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        })
    return HTMLResponse(content="<h1>App not found</h1>", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
