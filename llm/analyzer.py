"""
CodeVision AI - LLM Code Analyzer
Uses LangChain to orchestrate LLM calls for generating code summaries and insights.
"""

import os
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# LangChain imports (with fallback for when not installed)
try:
    from langchain_anthropic import ChatAnthropic  # type: ignore[import-untyped]
    from langchain_openai import ChatOpenAI  # type: ignore[import-untyped]
    from langchain.prompts import ChatPromptTemplate, PromptTemplate  # type: ignore[import-untyped]
    from langchain.schema import HumanMessage, SystemMessage  # type: ignore[import-untyped]
    from langchain.callbacks import get_openai_callback  # type: ignore[import-untyped]
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Google Gemini support
try:
    from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore[import-untyped]
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False


@dataclass
class ModuleSummary:
    name: str
    purpose: str
    key_components: List[str]
    dependencies_explanation: str
    usage_pattern: str


@dataclass 
class RelationshipInsight:
    source: str
    target: str
    relationship_type: str
    description: str
    strength: str  # strong, moderate, weak


class CodeAnalyzer:
    """
    LLM-powered code analyzer that generates natural language summaries
    and insights about code structure and relationships.
    """
    
    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the code analyzer with specified LLM.
        
        Args:
            model_name: The LLM model to use (claude-3-5-sonnet or gpt-4o)
        """
        self.model_name = model_name
        self.llm = None
        
        if LANGCHAIN_AVAILABLE:
            self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the LLM based on configuration."""
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")
        google_key = os.environ.get("GOOGLE_API_KEY")
        
        # Debug: Print which keys are available
        print(f"[CodeVision] API Keys detected - Google: {'Yes' if google_key else 'No'}, OpenAI: {'Yes' if openai_key else 'No'}, Anthropic: {'Yes' if anthropic_key else 'No'}")
        
        # Priority: Check model name first, then available API keys
        if "claude" in self.model_name.lower() and anthropic_key:
            self.llm = ChatAnthropic(
                model=self.model_name,
                anthropic_api_key=anthropic_key,
                temperature=0.3,
                max_tokens=2000
            )
        elif "gemini" in self.model_name.lower() and google_key and GOOGLE_GENAI_AVAILABLE:
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=google_key,
                temperature=0.3,
                max_output_tokens=2000
            )
        elif google_key and GOOGLE_GENAI_AVAILABLE:
            # Default to Gemini if Google API key is available (free tier!)
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=google_key,
                temperature=0.7,
                max_output_tokens=8000  # Increased for longer responses
            )
            print(f"[CodeVision] Using Google Gemini 1.5 Flash")
        elif openai_key:
            self.llm = ChatOpenAI(
                model="gpt-4o",
                openai_api_key=openai_key,
                temperature=0.3,
                max_tokens=2000
            )
        elif anthropic_key:
            self.llm = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                anthropic_api_key=anthropic_key,
                temperature=0.3,
                max_tokens=2000
            )
    
    async def generate_module_summary(self, module: Dict[str, Any]) -> str:
        """
        Generate a natural language summary for a module.
        
        Args:
            module: Module information from the parser
            
        Returns:
            A concise summary of the module's purpose and structure
        """
        if not self.llm:
            return self._generate_fallback_summary(module)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a code documentation expert. Generate concise, 
             informative summaries of code modules. Focus on:
             - The module's primary purpose
             - Key classes and functions
             - How it fits into the larger system
             Keep summaries to 2-3 sentences."""),
            ("human", """Analyze this module and provide a summary:

Module: {module_name}
File: {file_path}
Classes: {class_count}
Functions: {function_count}
Lines of Code: {line_count}
Docstring: {docstring}

Generate a concise summary of what this module does and its role in the codebase.""")
        ])
        
        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "module_name": module.get("name", "Unknown"),
                "file_path": module.get("file", ""),
                "class_count": module.get("class_count", 0),
                "function_count": module.get("function_count", 0),
                "line_count": module.get("line_count", 0),
                "docstring": module.get("docstring", "No docstring available")
            })
            return response.content
        except Exception as e:
            print(f"LLM error: {e}")
            return self._generate_fallback_summary(module)
    
    def _generate_fallback_summary(self, module: Dict[str, Any]) -> str:
        """Generate a basic summary without LLM."""
        name = module.get("name", "Unknown")
        class_count = module.get("class_count", 0)
        func_count = module.get("function_count", 0)
        docstring = module.get("docstring", "")
        
        summary = f"The {name} module"
        
        if docstring:
            # Use first sentence of docstring
            first_sentence = docstring.split('.')[0]
            summary = f"{name}: {first_sentence}."
        elif class_count > 0 and func_count > 0:
            summary = f"{name} contains {class_count} class(es) and {func_count} function(s)."
        elif class_count > 0:
            summary = f"{name} defines {class_count} class(es) for the application."
        elif func_count > 0:
            summary = f"{name} provides {func_count} utility function(s)."
        else:
            summary = f"{name} is a module in the codebase."
        
        return summary
    
    async def analyze_relationships(
        self,
        classes: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze relationships between classes and modules.
        
        Args:
            classes: List of class information
            dependencies: List of import/dependency information
            
        Returns:
            List of relationship insights
        """
        if not self.llm:
            return self._analyze_relationships_fallback(classes, dependencies)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a software architecture analyst. Analyze code 
             relationships and provide insights about:
             - Inheritance hierarchies
             - Module dependencies
             - Design patterns detected
             - Potential coupling issues
             
             Return your analysis as a JSON array of relationship insights."""),
            ("human", """Analyze these code relationships:

Classes:
{classes_json}

Dependencies:
{dependencies_json}

Provide insights about the key relationships, patterns, and any architectural observations.
Return as JSON array with fields: source, target, relationship_type, description, strength.""")
        ])
        
        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "classes_json": json.dumps(classes[:20], indent=2),  # Limit for context
                "dependencies_json": json.dumps(dependencies[:30], indent=2)
            })
            
            # Parse JSON from response
            content = response.content
            # Try to extract JSON from the response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content)
        except Exception as e:
            print(f"Relationship analysis error: {e}")
            return self._analyze_relationships_fallback(classes, dependencies)
    
    def _analyze_relationships_fallback(
        self,
        classes: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze relationships without LLM."""
        insights = []
        
        # Analyze inheritance
        for cls in classes:
            if cls.get("bases"):
                for base in cls["bases"]:
                    insights.append({
                        "source": cls["name"],
                        "target": base,
                        "relationship_type": "inheritance",
                        "description": f"{cls['name']} extends {base}",
                        "strength": "strong"
                    })
        
        # Analyze dependencies
        dep_counts = {}
        for dep in dependencies:
            target = dep.get("target", "")
            if target:
                dep_counts[target] = dep_counts.get(target, 0) + 1
        
        for target, count in dep_counts.items():
            if count >= 3:
                insights.append({
                    "source": "multiple modules",
                    "target": target,
                    "relationship_type": "dependency",
                    "description": f"{target} is a core dependency used by {count} modules",
                    "strength": "strong" if count >= 5 else "moderate"
                })
        
        return insights
    
    async def generate_detailed_explanation(
        self,
        module: Dict[str, Any],
        classes: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a detailed explanation for a module.
        
        Args:
            module: Module information
            classes: Classes in the module
            dependencies: Module dependencies
            
        Returns:
            Detailed explanation including purpose, components, and usage
        """
        if not self.llm:
            return self._generate_detailed_explanation_fallback(module, classes, dependencies)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior software engineer explaining code to a new team member.
             Provide clear, practical explanations that help developers understand:
             - What the code does
             - Why it's structured this way
             - How to use it
             - Key things to watch out for"""),
            ("human", """Explain this module in detail:

Module: {module_name}
Purpose: {docstring}

Classes:
{classes_info}

Dependencies:
{dependencies_info}

Provide:
1. A clear explanation of what this module does
2. How the classes work together
3. Important methods and their purposes
4. Usage examples or patterns
5. Any architectural notes""")
        ])
        
        try:
            classes_info = "\n".join([
                f"- {c['name']}: {len(c.get('methods', []))} methods, bases: {c.get('bases', [])}"
                for c in classes
            ])
            
            deps_info = "\n".join([
                f"- imports {d['target']} ({d.get('import_type', 'module')})"
                for d in dependencies[:10]
            ])
            
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "module_name": module.get("name", "Unknown"),
                "docstring": module.get("docstring", "No documentation"),
                "classes_info": classes_info or "No classes defined",
                "dependencies_info": deps_info or "No external dependencies"
            })
            
            return {
                "module": module.get("name"),
                "explanation": response.content,
                "classes": [c["name"] for c in classes],
                "key_dependencies": [d["target"] for d in dependencies[:5]]
            }
        except Exception as e:
            print(f"Explanation generation error: {e}")
            return self._generate_detailed_explanation_fallback(module, classes, dependencies)
    
    def _generate_detailed_explanation_fallback(
        self,
        module: Dict[str, Any],
        classes: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate explanation without LLM."""
        module_name = module.get("name", "Unknown")
        
        explanation_parts = [f"## {module_name}\n"]
        
        if module.get("docstring"):
            explanation_parts.append(f"{module['docstring']}\n")
        
        if classes:
            explanation_parts.append("\n### Classes\n")
            for cls in classes:
                cls_desc = f"**{cls['name']}**"
                if cls.get("bases"):
                    cls_desc += f" (extends {', '.join(cls['bases'])})"
                explanation_parts.append(f"- {cls_desc}")
                
                if cls.get("methods"):
                    key_methods = [m["name"] for m in cls["methods"][:5] if not m["name"].startswith("_")]
                    if key_methods:
                        explanation_parts.append(f"  - Key methods: {', '.join(key_methods)}")
        
        if dependencies:
            explanation_parts.append("\n### Dependencies\n")
            unique_deps = list(set(d["target"] for d in dependencies if d.get("target")))[:10]
            for dep in unique_deps:
                explanation_parts.append(f"- {dep}")
        
        return {
            "module": module_name,
            "explanation": "\n".join(explanation_parts),
            "classes": [c["name"] for c in classes],
            "key_dependencies": [d["target"] for d in dependencies[:5]]
        }
    
    async def suggest_improvements(
        self,
        module: Dict[str, Any],
        classes: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Suggest code improvements based on analysis.
        
        Args:
            module: Module information
            classes: Classes in the module
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Check for missing docstrings
        if not module.get("docstring"):
            suggestions.append(f"Add a module-level docstring to {module.get('name')}")
        
        for cls in classes:
            if not cls.get("docstring"):
                suggestions.append(f"Add a docstring to class {cls['name']}")
            
            # Check for large classes
            if len(cls.get("methods", [])) > 15:
                suggestions.append(
                    f"Class {cls['name']} has {len(cls['methods'])} methods. "
                    "Consider splitting into smaller classes."
                )
            
            # Check for missing type hints (if we can detect them)
            for method in cls.get("methods", []):
                if not method.get("return_type") and not method["name"].startswith("_"):
                    suggestions.append(
                        f"Add return type annotation to {cls['name']}.{method['name']}"
                    )
        
        return suggestions[:10]  # Limit suggestions

    async def chat_about_project(
        self,
        question: str,
        modules: List[Dict[str, Any]],
        classes: List[Dict[str, Any]],
        functions: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]],
        chat_history: List[Dict[str, str]] = None
    ) -> str:
        """
        Answer ANY questions about the project using LLM.
        
        Args:
            question: User's question about the project
            modules: List of module information
            classes: List of class information
            functions: List of function information
            dependencies: List of dependency information
            chat_history: Previous chat messages
            
        Returns:
            AI-generated answer about the project
        """
        if not self.llm:
            return self._chat_fallback(question, modules, classes, functions, dependencies)
        
        # Build comprehensive context about the project
        context_parts = []
        
        # Project overview
        total_methods = sum(len(c.get('methods', [])) for c in classes)
        context_parts.append(f"**Project Overview:** {len(modules)} modules, {len(classes)} classes, {len(functions)} functions, {total_methods} methods total")
        
        # Detailed modules info
        if modules:
            module_details = []
            for m in modules[:20]:
                name = m.get('name', 'Unknown')
                lang = m.get('language', 'unknown')
                lines = m.get('line_count', 0)
                doc = m.get('docstring', '')[:150] if m.get('docstring') else ''
                module_details.append(f"- **{name}** ({lang}, {lines} lines){': ' + doc if doc else ''}")
            context_parts.append(f"**Modules ({len(modules)}):**\n" + "\n".join(module_details))
        
        # Detailed classes with methods
        if classes:
            class_details = []
            for c in classes[:25]:
                name = c.get('name', 'Unknown')
                bases = c.get('bases', [])
                methods = c.get('methods', [])
                method_names = [m.get('name', '') for m in methods[:10]]
                attrs = c.get('attributes', [])
                
                class_str = f"- **{name}**"
                if bases:
                    class_str += f" (extends {', '.join(bases)})"
                if method_names:
                    class_str += f"\n  Methods: {', '.join(method_names)}"
                if attrs:
                    class_str += f"\n  Attributes: {', '.join(attrs[:5])}"
                class_details.append(class_str)
            context_parts.append(f"**Classes ({len(classes)}):**\n" + "\n".join(class_details))
        
        # Functions with details
        if functions:
            func_details = []
            for f in functions[:20]:
                name = f.get('name', 'Unknown')
                params = f.get('parameters', [])
                param_names = [p.get('name', '') for p in params if p.get('name') != 'self']
                doc = f.get('docstring', '')[:100] if f.get('docstring') else ''
                func_str = f"- **{name}**({', '.join(param_names)})"
                if doc:
                    func_str += f": {doc}"
                func_details.append(func_str)
            context_parts.append(f"**Functions ({len(functions)}):**\n" + "\n".join(func_details))
        
        # Dependencies and imports
        if dependencies:
            dep_map = {}
            for d in dependencies:
                source = d.get('source', '')
                target = d.get('target', '')
                if source and target:
                    if source not in dep_map:
                        dep_map[source] = []
                    dep_map[source].append(target)
            
            dep_details = []
            for source, targets in list(dep_map.items())[:15]:
                dep_details.append(f"- {source} imports: {', '.join(targets[:8])}")
            context_parts.append(f"**Dependencies:**\n" + "\n".join(dep_details))
        
        project_context = "\n\n".join(context_parts)
        
        # Build chat history context
        history_context = ""
        if chat_history:
            history_context = "\n".join([
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in chat_history[-8:]  # Last 8 messages for better context
            ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are CodeVision AI, a world-class software architect and senior developer with 20+ years of experience. You have been given complete access to analyze a codebase.

## YOUR CAPABILITIES:
You can answer ANY question about this codebase - there are NO restrictions on what you can help with. Give COMPLETE, DETAILED answers - never cut yourself short or give partial responses.

## WHAT YOU CAN DO:
✅ Explain ANY code, class, function, or module in detail
✅ Analyze architecture, design patterns, and structure
✅ Suggest improvements, refactoring, and best practices
✅ Help debug issues and identify problems
✅ Write code examples and implementations
✅ Explain how to extend or modify the code
✅ Discuss performance, security, and testing
✅ Compare different approaches
✅ Generate documentation
✅ Answer hypothetical questions
✅ Make inferences based on code patterns
✅ ANYTHING else the user asks

## RESPONSE GUIDELINES:
- Give COMPLETE answers - don't summarize or truncate
- Use markdown formatting (bold, code blocks, lists, headers)
- Include code examples when helpful
- Be specific, not generic
- If you're making an inference, say so
- If you need more context, ask
- Be conversational and helpful

## PROJECT KNOWLEDGE:
{project_context}

{history_context}

Remember: Give the user exactly what they're asking for. No limitations, no restrictions, no "I can't do that". You're here to help completely."""),
            ("human", "{question}")
        ])
        
        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "project_context": project_context,
                "history_context": f"PREVIOUS CONVERSATION:\n{history_context}" if history_context else "",
                "question": question
            })
            return response.content
        except Exception as e:
            print(f"Chat error: {e}")
            return self._chat_fallback(question, modules, classes, functions, dependencies)
    
    def _chat_fallback(
        self,
        question: str,
        modules: List[Dict[str, Any]],
        classes: List[Dict[str, Any]],
        functions: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]] = None
    ) -> str:
        """Generate a comprehensive response without LLM by analyzing the question and codebase."""
        question_lower = question.lower()
        dependencies = dependencies or []
        
        # Count statistics
        total_methods = sum(len(c.get('methods', [])) for c in classes)
        total_lines = sum(m.get('line_count', 0) for m in modules)
        
        # Try to find ANY mentioned class/function/module in the question
        mentioned_classes = []
        mentioned_funcs = []
        mentioned_modules = []
        
        for cls in classes:
            cls_name = cls.get('name', '').lower()
            if cls_name and cls_name in question_lower:
                mentioned_classes.append(cls)
        
        for func in functions:
            func_name = func.get('name', '').lower()
            if func_name and len(func_name) > 2 and func_name in question_lower:
                mentioned_funcs.append(func)
        
        for mod in modules:
            mod_name = mod.get('name', '').lower()
            if mod_name and mod_name in question_lower:
                mentioned_modules.append(mod)
        
        # Build comprehensive response based on what was mentioned
        response_parts = []
        
        # If specific classes mentioned
        if mentioned_classes:
            for cls in mentioned_classes[:3]:
                methods = cls.get('methods', [])
                attrs = cls.get('attributes', [])
                bases = cls.get('bases', [])
                
                part = f"## Class: `{cls['name']}`\n\n"
                
                if bases:
                    part += f"**Inheritance:** Extends `{', '.join(bases)}`\n\n"
                
                if cls.get('docstring'):
                    part += f"**Description:** {cls['docstring']}\n\n"
                
                if attrs:
                    part += f"**Attributes ({len(attrs)}):**\n"
                    for attr in attrs[:10]:
                        part += f"- `{attr}`\n"
                    part += "\n"
                
                if methods:
                    part += f"**Methods ({len(methods)}):**\n"
                    for m in methods:
                        params = [p.get('name', '') for p in m.get('parameters', []) if p.get('name') and p.get('name') != 'self']
                        return_type = f" → {m.get('return_type')}" if m.get('return_type') else ""
                        doc = f": {m.get('docstring')[:80]}..." if m.get('docstring') else ""
                        part += f"- `{m.get('name')}({', '.join(params)})`{return_type}{doc}\n"
                    part += "\n"
                
                # Find related dependencies
                module_name = cls.get('module', '')
                related_deps = [d for d in dependencies if d.get('source') == module_name][:5]
                if related_deps:
                    part += f"**Dependencies:** {', '.join(set(d.get('target', '') for d in related_deps))}\n"
                
                response_parts.append(part)
        
        # If specific functions mentioned
        if mentioned_funcs:
            for func in mentioned_funcs[:3]:
                params = [p.get('name', '') for p in func.get('parameters', []) if p.get('name') and p.get('name') != 'self']
                
                part = f"## Function: `{func['name']}`\n\n"
                part += f"**Signature:** `{func['name']}({', '.join(params)})`\n\n"
                
                if func.get('return_type'):
                    part += f"**Returns:** `{func['return_type']}`\n\n"
                
                if func.get('docstring'):
                    part += f"**Description:** {func['docstring']}\n\n"
                
                if func.get('module'):
                    part += f"**Location:** `{func['module']}` module\n"
                
                response_parts.append(part)
        
        # If specific modules mentioned
        if mentioned_modules:
            for mod in mentioned_modules[:3]:
                part = f"## Module: `{mod['name']}`\n\n"
                
                if mod.get('docstring'):
                    part += f"**Description:** {mod['docstring']}\n\n"
                
                part += f"**Statistics:**\n"
                part += f"- Lines of code: {mod.get('line_count', 'N/A')}\n"
                part += f"- Classes: {mod.get('class_count', 0)}\n"
                part += f"- Functions: {mod.get('function_count', 0)}\n\n"
                
                # Find classes in this module
                mod_classes = [c for c in classes if c.get('module') == mod['name']]
                if mod_classes:
                    part += f"**Classes in this module:**\n"
                    for c in mod_classes[:10]:
                        part += f"- `{c['name']}` ({len(c.get('methods', []))} methods)\n"
                
                response_parts.append(part)
        
        if response_parts:
            return "\n---\n\n".join(response_parts)
        
        # If no specific items mentioned, analyze the question intent
        
        # Counting questions
        if any(word in question_lower for word in ['how many', 'count', 'total', 'number']):
            return f"""## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| **Total Modules** | {len(modules)} |
| **Total Classes** | {len(classes)} |
| **Total Functions** | {len(functions)} |
| **Total Methods** | {total_methods} |
| **Lines of Code** | {total_lines:,} |
| **Dependencies** | {len(dependencies)} |

### Breakdown by Module:
{chr(10).join(f"- **{m.get('name')}**: {m.get('class_count', 0)} classes, {m.get('function_count', 0)} functions, {m.get('line_count', 0)} lines" for m in modules[:15])}"""

        # Listing questions
        if any(word in question_lower for word in ['list', 'show me', 'what are', 'give me']):
            if 'class' in question_lower:
                return f"""## 📦 All Classes ({len(classes)})

{chr(10).join(f"- **`{c.get('name')}`**" + (f" (extends {', '.join(c.get('bases', []))})" if c.get('bases') else "") + f" - {len(c.get('methods', []))} methods" for c in classes)}"""
            
            elif 'function' in question_lower:
                return f"""## ⚡ All Functions ({len(functions)})

{chr(10).join(f"- **`{f.get('name')}()`** in `{f.get('module', 'unknown')}`" for f in functions)}"""
            
            elif 'module' in question_lower:
                return f"""## 📁 All Modules ({len(modules)})

{chr(10).join(f"- **`{m.get('name')}`** - {m.get('line_count', 0)} lines, {m.get('class_count', 0)} classes, {m.get('function_count', 0)} functions" for m in modules)}"""
            
            elif 'method' in question_lower:
                all_methods = []
                for c in classes:
                    for m in c.get('methods', []):
                        all_methods.append(f"- `{c['name']}.{m.get('name')}()`")
                return f"""## 🔧 All Methods ({len(all_methods)})

{chr(10).join(all_methods[:50])}
{"..." if len(all_methods) > 50 else ""}"""
        
        # Architecture/overview questions
        if any(word in question_lower for word in ['architecture', 'structure', 'overview', 'explain', 'describe', 'how does', 'what is this']):
            inheritance_info = ""
            for c in classes:
                if c.get('bases'):
                    inheritance_info += f"- `{c['name']}` extends `{', '.join(c['bases'])}`\n"
            
            return f"""## 🏗️ Project Architecture Overview

### Summary
This codebase consists of **{len(modules)} modules** containing **{len(classes)} classes** and **{len(functions)} standalone functions**, totaling approximately **{total_lines:,} lines of code**.

### Modules
{chr(10).join(f"- **`{m.get('name')}`**: {m.get('class_count', 0)} classes, {m.get('function_count', 0)} functions ({m.get('line_count', 0)} lines)" for m in modules[:15])}

### Key Classes
{chr(10).join(f"- **`{c.get('name')}`**: {len(c.get('methods', []))} methods" + (f" (extends {', '.join(c.get('bases', []))})" if c.get('bases') else "") for c in classes[:15])}

{"### Inheritance Hierarchy" + chr(10) + inheritance_info if inheritance_info else ""}

### Dependencies
The project uses these external dependencies:
{chr(10).join(f"- `{dep}`" for dep in sorted(set(d.get('target', '') for d in dependencies if d.get('target')))[:20])}"""

        # Default comprehensive response
        return f"""## 🔮 Project Analysis

I have analyzed your codebase. Here's what I found:

### 📊 Overview
- **{len(modules)} modules** in the project
- **{len(classes)} classes** defined
- **{len(functions)} standalone functions**
- **{total_methods} total methods**
- **{total_lines:,} lines of code**

### 📦 Main Components

**Modules:**
{chr(10).join(f"- `{m.get('name')}`" for m in modules[:10])}

**Classes:**
{chr(10).join(f"- `{c.get('name')}` ({len(c.get('methods', []))} methods)" for c in classes[:10])}

### 💡 You Can Ask Me:
- "Tell me about `{classes[0].get('name') if classes else 'ClassName'}`"
- "What methods does `{classes[0].get('name') if classes else 'ClassName'}` have?"
- "Explain the architecture"
- "List all classes/functions/modules"
- "How many lines of code?"
- Any other question about this codebase!

---
*For AI-powered detailed analysis, ensure your API key is configured.*"""
