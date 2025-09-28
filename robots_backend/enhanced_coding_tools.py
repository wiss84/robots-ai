"""
Enhanced coding tools for the coding agent.
These tools provide more advanced functionality
for code analysis, refactoring, and project management.
"""

import os
import ast
import re
import json
import subprocess
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import fnmatch
from pathlib import Path

class CodeSearchInput(BaseModel):
    query: str = Field(..., description="Search query (can be regex pattern, function name, class name, etc.)")
    file_pattern: str = Field(default="*", description="File pattern to search in (e.g., '*.py', '*.js', '*.tsx')")
    search_type: str = Field(default="content", description="Type of search: 'content', 'function', 'class', 'import', 'variable'")
    case_sensitive: bool = Field(default=False, description="Whether search should be case sensitive")

class FileAnalysisInput(BaseModel):
    file_path: str = Field(..., description="Path to the file to analyze")
    analysis_type: str = Field(default="full", description="Type of analysis: 'full', 'structure', 'dependencies', 'complexity'")

class CodeRefactorInput(BaseModel):
    file_path: str = Field(..., description="Path to the file to refactor")
    refactor_type: str = Field(..., description="Type of refactoring: 'extract_function', 'rename', 'optimize', 'format'")
    target: str = Field(..., description="Target for refactoring (function name, variable name, etc.)")
    new_name: Optional[str] = Field(None, description="New name for rename operations")

class ProjectStructureInput(BaseModel):
    max_depth: int = Field(default=3, description="Maximum depth to traverse")
    include_hidden: bool = Field(default=False, description="Include hidden files and directories")
    file_types: Optional[str] = Field(default=None, description="Filter by file types as comma-separated string (e.g., '.py,.js,.tsx' or leave empty for all files)")

def get_workspace_dir():
    """
    Get workspace directory that works both in Docker and outside Docker
    """
    # Check if we're running in Docker (common indicators)
    is_docker = (
        os.path.exists('/.dockerenv') or
        os.environ.get('PYTHONPATH') == '/app' or
        os.getcwd() == '/app'
    )

    if is_docker:
        # We're in Docker - use the mounted volume path
        workspace_dir = "/app/uploaded_files/workspace"
    else:
        # We're running normally - use relative paths
        workspace_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploaded_files", "workspace")

    return os.path.abspath(workspace_dir)

WORKSPACE_DIR = get_workspace_dir()

@tool("code_search", args_schema=CodeSearchInput)
def code_search(query: str, file_pattern: str = "*", search_type: str = "content", case_sensitive: bool = False) -> dict:
    """
    Advanced code search tool that can find functions, classes, imports, variables, or content across the workspace.
    Use this to search through codebases to understand structure and find relevant code.
    """
    try:
        if not os.path.exists(WORKSPACE_DIR):
            return {"error": "Workspace directory not found"}
        
        results = []
        flags = 0 if case_sensitive else re.IGNORECASE
        
        # Compile regex pattern
        try:
            if search_type == "content":
                pattern = re.compile(query, flags)
            elif search_type == "function":
                pattern = re.compile(rf"def\s+{re.escape(query)}\s*\(|function\s+{re.escape(query)}\s*\(|{re.escape(query)}\s*=\s*function", flags)
            elif search_type == "class":
                pattern = re.compile(rf"class\s+{re.escape(query)}\s*[\(:]|class\s+{re.escape(query)}\s*{{", flags)
            elif search_type == "import":
                pattern = re.compile(rf"import.*{re.escape(query)}|from.*{re.escape(query)}", flags)
            elif search_type == "variable":
                pattern = re.compile(rf"\b{re.escape(query)}\s*=", flags)
            else:
                pattern = re.compile(query, flags)
        except re.error as e:
            return {"error": f"Invalid regex pattern: {e}"}
        
        # Walk through workspace
        for root, dirs, files in os.walk(WORKSPACE_DIR):
            for file in files:
                if fnmatch.fnmatch(file, file_pattern):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, WORKSPACE_DIR)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                        matches = []
                        for line_num, line in enumerate(content.splitlines(), 1):
                            if pattern.search(line):
                                matches.append({
                                    "line_number": line_num,
                                    "line_content": line.strip(),
                                    "context": _get_line_context(content.splitlines(), line_num - 1, 2)
                                })
                        
                        if matches:
                            results.append({
                                "file": rel_path,
                                "matches": matches,
                                "total_matches": len(matches)
                            })
                            
                    except Exception as e:
                        continue
        
        return {
            "query": query,
            "search_type": search_type,
            "file_pattern": file_pattern,
            "total_files_with_matches": len(results),
            "total_matches": sum(r["total_matches"] for r in results),
            "results": results[:20]  # Limit results
        }
        
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}

@tool("analyze_file", args_schema=FileAnalysisInput)
def analyze_file(file_path: str, analysis_type: str = "full") -> dict:
    """
    Analyze a file's structure, dependencies, complexity, and other metrics.
    Provides deep insights into code organization and quality.
    """
    try:
        full_path = os.path.join(WORKSPACE_DIR, file_path)
        if not os.path.exists(full_path):
            return {"error": f"File not found: {file_path}"}
        
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        analysis = {
            "file_path": file_path,
            "file_size": len(content),
            "line_count": len(content.splitlines()),
            "analysis_type": analysis_type
        }
        
        # Determine file type
        ext = os.path.splitext(file_path)[1].lower()
        
        if analysis_type in ["full", "structure"]:
            if ext == ".py":
                analysis.update(_analyze_python_structure(content))
            elif ext in [".js", ".jsx", ".ts", ".tsx"]:
                analysis.update(_analyze_javascript_structure(content))
            else:
                analysis.update(_analyze_generic_structure(content))
        
        if analysis_type in ["full", "dependencies"]:
            analysis["dependencies"] = _extract_dependencies(content, ext)
        
        if analysis_type in ["full", "complexity"]:
            analysis["complexity"] = _calculate_complexity(content, ext)
        
        return analysis
        
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}

@tool("project_structure_analysis", args_schema=ProjectStructureInput)
def project_structure_analysis(max_depth: int = 3, include_hidden: bool = False, file_types: Optional[str] = None) -> dict:
    """
    Analyze the entire project structure, providing insights into organization,
    file types, dependencies, and architectural patterns.
    """
    try:
        # Convert comma-separated string to list
        file_types_list = None
        if file_types:
            file_types_list = [ft.strip() for ft in file_types.split(',') if ft.strip()]

        if not os.path.exists(WORKSPACE_DIR):
            return {"error": "Workspace directory not found"}
        
        structure = {
            "root": WORKSPACE_DIR,
            "tree": {},
            "statistics": {
                "total_files": 0,
                "total_directories": 0,
                "file_types": {},
                "largest_files": [],
                "empty_files": []
            },
            "patterns": {
                "config_files": [],
                "test_files": [],
                "documentation": [],
                "build_files": []
            }
        }
        
        # Build tree structure
        structure["tree"] = _build_directory_tree(WORKSPACE_DIR, max_depth, include_hidden, file_types_list)
        
        # Collect statistics
        for root, dirs, files in os.walk(WORKSPACE_DIR):
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                files = [f for f in files if not f.startswith('.')]
            
            structure["statistics"]["total_directories"] += len(dirs)
            
            for file in files:
                if file_types_list and not any(file.endswith(ft) for ft in file_types_list):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, WORKSPACE_DIR)
                
                structure["statistics"]["total_files"] += 1
                
                # File type statistics
                ext = os.path.splitext(file)[1].lower()
                structure["statistics"]["file_types"][ext] = structure["statistics"]["file_types"].get(ext, 0) + 1
                
                # File size analysis
                try:
                    size = os.path.getsize(file_path)
                    if size == 0:
                        structure["statistics"]["empty_files"].append(rel_path)
                    else:
                        structure["statistics"]["largest_files"].append({
                            "file": rel_path,
                            "size": size
                        })
                except:
                    continue
                
                # Pattern detection
                _detect_file_patterns(file, rel_path, structure["patterns"])
        
        # Sort largest files
        structure["statistics"]["largest_files"].sort(key=lambda x: x["size"], reverse=True)
        structure["statistics"]["largest_files"] = structure["statistics"]["largest_files"][:10]
        
        return structure
        
    except Exception as e:
        return {"error": f"Structure analysis failed: {str(e)}"}

@tool("find_related_files", args_schema=FileAnalysisInput)
def find_related_files(file_path: str, analysis_type: str = "full") -> dict:
    """
    Find files related to the given file through imports, references, or similar patterns.
    Helps understand code dependencies and relationships.
    """
    try:
        full_path = os.path.join(WORKSPACE_DIR, file_path)
        if not os.path.exists(full_path):
            return {"error": f"File not found: {file_path}"}
        
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        related = {
            "source_file": file_path,
            "imports": [],
            "references": [],
            "similar_files": [],
            "dependents": []
        }
        
        # Extract imports/requires
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".py":
            related["imports"] = _extract_python_imports(content)
        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            related["imports"] = _extract_javascript_imports(content)
        
        # Find files that import this file
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        for root, dirs, files in os.walk(WORKSPACE_DIR):
            for file in files:
                if file == os.path.basename(file_path):
                    continue
                
                other_path = os.path.join(root, file)
                rel_other_path = os.path.relpath(other_path, WORKSPACE_DIR)
                
                try:
                    with open(other_path, 'r', encoding='utf-8', errors='ignore') as f:
                        other_content = f.read()
                    
                    # Check if this file imports/references the source file
                    if (base_name in other_content or 
                        file_path in other_content or 
                        os.path.basename(file_path) in other_content):
                        related["dependents"].append(rel_other_path)
                        
                except:
                    continue
        
        return related
        
    except Exception as e:
        return {"error": f"Related files analysis failed: {str(e)}"}

# Helper functions

def _get_line_context(lines: List[str], line_index: int, context_size: int) -> List[str]:
    """Get surrounding lines for context."""
    start = max(0, line_index - context_size)
    end = min(len(lines), line_index + context_size + 1)
    return lines[start:end]

def _analyze_python_structure(content: str) -> dict:
    """Analyze Python file structure."""
    try:
        tree = ast.parse(content)
        
        classes = []
        functions = []
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                })
            elif isinstance(node, ast.FunctionDef):
                if not any(node.lineno >= cls["line"] for cls in classes):  # Top-level functions
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args]
                    })
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.unparse(node))
        
        return {
            "language": "python",
            "classes": classes,
            "functions": functions,
            "imports": imports,
            "class_count": len(classes),
            "function_count": len(functions)
        }
    except:
        return {"language": "python", "parse_error": True}

def _analyze_javascript_structure(content: str) -> dict:
    """Analyze JavaScript/TypeScript file structure."""
    # Simple regex-based analysis for JS/TS
    functions = re.findall(r'(?:function\s+(\w+)|(\w+)\s*=\s*(?:function|\([^)]*\)\s*=>))', content)
    classes = re.findall(r'class\s+(\w+)', content)
    imports = re.findall(r'import.*from\s+[\'"]([^\'"]+)[\'"]', content)
    
    return {
        "language": "javascript",
        "functions": [f[0] or f[1] for f in functions],
        "classes": classes,
        "imports": imports,
        "function_count": len(functions),
        "class_count": len(classes)
    }

def _analyze_generic_structure(content: str) -> dict:
    """Generic structure analysis for other file types."""
    lines = content.splitlines()
    return {
        "language": "generic",
        "line_count": len(lines),
        "non_empty_lines": len([l for l in lines if l.strip()]),
        "comment_lines": len([l for l in lines if l.strip().startswith(('#', '//', '/*', '*'))])
    }

def _extract_dependencies(content: str, ext: str) -> List[str]:
    """Extract dependencies from file content."""
    deps = []
    
    if ext == ".py":
        deps.extend(re.findall(r'import\s+(\w+)', content))
        deps.extend(re.findall(r'from\s+(\w+)', content))
    elif ext in [".js", ".jsx", ".ts", ".tsx"]:
        deps.extend(re.findall(r'import.*from\s+[\'"]([^\'"]+)[\'"]', content))
        deps.extend(re.findall(r'require\([\'"]([^\'"]+)[\'"]\)', content))
    
    return list(set(deps))

def _calculate_complexity(content: str, ext: str) -> dict:
    """Calculate code complexity metrics."""
    lines = content.splitlines()
    
    complexity = {
        "cyclomatic_complexity": 1,  # Base complexity
        "nesting_depth": 0,
        "function_length_avg": 0
    }
    
    # Simple complexity calculation
    complexity_keywords = ['if', 'elif', 'else', 'for', 'while', 'try', 'except', 'case', 'switch']
    
    for line in lines:
        stripped = line.strip().lower()
        for keyword in complexity_keywords:
            if stripped.startswith(keyword):
                complexity["cyclomatic_complexity"] += 1
        
        # Calculate nesting depth
        leading_spaces = len(line) - len(line.lstrip())
        if ext == ".py":
            depth = leading_spaces // 4
        else:
            depth = line.count('{') - line.count('}')
        
        complexity["nesting_depth"] = max(complexity["nesting_depth"], depth)
    
    return complexity

def _build_directory_tree(path: str, max_depth: int, include_hidden: bool, file_types: Optional[List[str]], current_depth: int = 0) -> dict:
    """Build a directory tree structure."""
    if current_depth >= max_depth:
        return {}
    
    tree = {}
    
    try:
        for item in os.listdir(path):
            if not include_hidden and item.startswith('.'):
                continue
            
            item_path = os.path.join(path, item)
            
            if os.path.isdir(item_path):
                tree[item] = {
                    "type": "directory",
                    "children": _build_directory_tree(item_path, max_depth, include_hidden, file_types, current_depth + 1)
                }
            else:
                if file_types and not any(item.endswith(ft) for ft in file_types):
                    continue
                
                tree[item] = {
                    "type": "file",
                    "size": os.path.getsize(item_path),
                    "extension": os.path.splitext(item)[1]
                }
    except PermissionError:
        pass
    
    return tree

def _detect_file_patterns(filename: str, rel_path: str, patterns: dict):
    """Detect common file patterns."""
    lower_name = filename.lower()
    
    if any(config in lower_name for config in ['config', 'settings', '.env', 'package.json', 'requirements.txt']):
        patterns["config_files"].append(rel_path)
    
    if any(test in lower_name for test in ['test', 'spec', '__test__']):
        patterns["test_files"].append(rel_path)
    
    if any(doc in lower_name for doc in ['readme', 'doc', 'documentation', '.md']):
        patterns["documentation"].append(rel_path)
    
    if any(build in lower_name for build in ['makefile', 'dockerfile', 'build', 'webpack', 'gulpfile']):
        patterns["build_files"].append(rel_path)

def _extract_python_imports(content: str) -> List[str]:
    """Extract Python imports."""
    imports = []
    imports.extend(re.findall(r'import\s+([^\s,]+)', content))
    imports.extend(re.findall(r'from\s+([^\s]+)\s+import', content))
    return list(set(imports))

def _extract_javascript_imports(content: str) -> List[str]:
    """Extract JavaScript/TypeScript imports."""
    imports = []
    imports.extend(re.findall(r'import.*from\s+[\'"]([^\'"]+)[\'"]', content))
    imports.extend(re.findall(r'require\([\'"]([^\'"]+)[\'"]\)', content))
    return list(set(imports))