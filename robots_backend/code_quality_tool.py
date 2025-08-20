"""
Cross-language code quality tool for Python, TypeScript/JavaScript, and Java.

Analyzers used (runs only what applies to the target file):
- Python: ruff (lint), mypy (type)
- TypeScript/JavaScript: eslint (lint), tsc --noEmit (type)
- Java: javac -Xlint (compile-time diagnostics)

If tools are missing, returns actionable guidance without failing the whole tool.
"""

import os
import json
import re
import subprocess
from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import shlex
import tempfile


SUPPORTED_LANGS = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".java": "java",
}


class AnalyzeInput(BaseModel):
    file_path: str = Field(..., description="Absolute or project-relative path to the file to analyze")
    # Optional working directory hint (useful for monorepos)
    cwd: Optional[str] = Field(None, description="Working directory for running analyzers")
    # Optional language override if the extension is non-standard
    language: Optional[str] = Field(None, description="Override language detection: python|typescript|javascript|java")


def _detect_language(path: str, override: Optional[str]) -> Optional[str]:
    if override:
        override = override.lower()
        if override in {"python", "typescript", "javascript", "java"}:
            return override
    ext = os.path.splitext(path)[1].lower()
    return SUPPORTED_LANGS.get(ext)


def _workspace_root() -> str:
    # Always use uploaded workspace as project root (see project_index.PROJECT_ROOT)
    return os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploaded_files", "workspace"))

def _norm_path(path: str, cwd: Optional[str]) -> str:
    # Resolve to workspace root by default, honoring provided cwd when given.
    p = os.path.normpath(os.path.expanduser(str(path).strip()))
    if os.path.isabs(p):
        return os.path.abspath(p)

    # Support inputs prefixed with '/uploaded_files/workspace'
    normalized = p.replace("\\", "/")
    prefixes = [
        "uploaded_files/workspace",
        "robots_backend/uploaded_files/workspace",
        "/uploaded_files/workspace",
        "\\uploaded_files\\workspace",
    ]
    for pref in prefixes:
        if normalized.lower().startswith(pref.replace("\\", "/").lower()):
            p = normalized[len(pref):].lstrip("\\/") if len(normalized) >= len(pref) else ""
            break

    base = os.path.abspath(cwd) if cwd else _workspace_root()
    return os.path.abspath(os.path.join(base, p))


def _run(cmd: List[str] | str, cwd: Optional[str] = None, timeout: int = 90) -> Tuple[int, str, str]:
    # Use shell=True for Windows to resolve "npx" etc., but prefer list when possible
    use_shell = isinstance(cmd, str)
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            shell=use_shell,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError as e:
        return 127, "", str(e)
    except subprocess.TimeoutExpired as e:
        return 124, e.stdout or "", e.stderr or f"Command timed out after {timeout}s"


def _find_upwards(start_dir: str, target_name: str) -> Optional[str]:
    cur = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(cur, target_name)
        if os.path.exists(candidate):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def _parse_eslint_json(out: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(out or "[]")
        issues: List[Dict[str, Any]] = []
        for file_report in data:
            file_path = file_report.get("filePath")
            for m in file_report.get("messages", []):
                issues.append({
                    "tool": "eslint",
                    "severity": "error" if m.get("severity") == 2 else "warning",
                    "message": m.get("message"),
                    "file": file_path,
                    "line": m.get("line"),
                    "column": m.get("column"),
                    "endLine": m.get("endLine"),
                    "endColumn": m.get("endColumn"),
                    "code": m.get("ruleId"),
                })
        return issues
    except Exception:
        return [{
            "tool": "eslint",
            "severity": "info",
            "message": "Failed to parse ESLint JSON output.",
            "raw": out,
        }]


def _parse_tsc_output(out: str, err: str) -> List[Dict[str, Any]]:
    # Typical line: path/to/file.ts(10,5): error TS1234: Message
    pattern = re.compile(r"^(?P<file>.+)\((?P<line>\d+),(?P<col>\d+)\): (?P<level>error|warning) TS(?P<code>\d+): (?P<msg>.+)$")
    issues: List[Dict[str, Any]] = []
    for stream in [out, err]:
        for line in (stream or "").splitlines():
            m = pattern.match(line.strip())
            if m:
                issues.append({
                    "tool": "tsc",
                    "severity": m.group("level"),
                    "message": m.group("msg"),
                    "file": m.group("file"),
                    "line": int(m.group("line")),
                    "column": int(m.group("col")),
                    "code": f"TS{m.group('code')}",
                })
    return issues


def _parse_mypy_json(out: str) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    try:
        data = json.loads(out or "[]")
        for entry in data:
            if not isinstance(entry, dict):
                continue
            issues.append({
                "tool": "mypy",
                "severity": "error" if entry.get("severity") in ("error", "failure") else (entry.get("severity") or "warning"),
                "message": entry.get("message"),
                "file": entry.get("path"),
                "line": entry.get("line"),
                "column": entry.get("column"),
                "code": entry.get("code"),
            })
        return issues
    except Exception:
        # fallback: parse simple "path:line: col: error: message"
        fallback: List[Dict[str, Any]] = []
        for line in (out or "").splitlines():
            # Rough fallback parse
            m = re.match(r"^(?P<file>[^:]+):(?P<line>\d+):(?:(?P<col>\d+):)? (?P<msg>.+)$", line.strip())
            if m:
                fallback.append({
                    "tool": "mypy",
                    "severity": "error",
                    "message": m.group("msg"),
                    "file": m.group("file"),
                    "line": int(m.group("line")),
                    "column": int(m.group("col") or 1),
                })
        if fallback:
            return fallback
        return [{
            "tool": "mypy",
            "severity": "info",
            "message": "Failed to parse mypy output.",
            "raw": out,
        }]


def _parse_ruff_json(out: str) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    try:
        data = json.loads(out or "[]")
        for e in data:
            # Ruff JSON format has keys: filename, code, message, location: {row, column}, end: {row, column}, etc.
            issues.append({
                "tool": "ruff",
                "severity": "warning",
                "message": e.get("message"),
                "file": e.get("filename"),
                "line": (e.get("location") or {}).get("row"),
                "column": (e.get("location") or {}).get("column"),
                "endLine": (e.get("end") or {}).get("row"),
                "endColumn": (e.get("end") or {}).get("column"),
                "code": e.get("code"),
            })
        return issues
    except Exception:
        return [{
            "tool": "ruff",
            "severity": "info",
            "message": "Failed to parse Ruff JSON output.",
            "raw": out,
        }]


def _parse_javac_output(out: str, err: str) -> List[Dict[str, Any]]:
    # Typical: path\File.java:10: error: message
    #          <code line>
    #                        ^
    pattern = re.compile(r"^(?P<file>.+):(?P<line>\d+): (?P<level>warning|error): (?P<msg>.+)$")
    issues: List[Dict[str, Any]] = []
    for stream in [out, err]:
        lines = (stream or "").splitlines()
        for i, line in enumerate(lines):
            m = pattern.match(line.strip())
            if m:
                level = m.group("level")
                msg = m.group("msg")
                file_path = m.group("file")
                line_no = int(m.group("line"))
                col = None
                # Heuristic: next lines may contain caret "^" positioning
                if i + 2 < len(lines) and "^" in lines[i + 2]:
                    col = lines[i + 2].find("^") + 1
                    if col == 0:
                        col = None
                issues.append({
                    "tool": "javac",
                    "severity": level,
                    "message": msg,
                    "file": file_path,
                    "line": line_no,
                    "column": col,
                })
    return issues


def _analyze_python(path: str, cwd: Optional[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    suggestions: List[str] = []
    issues: List[Dict[str, Any]] = []

    # Ruff
    # Prefer "ruff check --format json"; fallback to "ruff --format json"
    rc, out, err = _run(["ruff", "check", "--format", "json", path], cwd=cwd)
    if rc == 127:
        # Command not found; try plain 'ruff --format json'
        rc2, out2, err2 = _run(["ruff", "--format", "json", path], cwd=cwd)
        if rc2 == 127:
            suggestions.append("Install ruff (added to requirements.txt): pip install ruff")
        else:
            issues.extend(_parse_ruff_json(out2))
    else:
        issues.extend(_parse_ruff_json(out))

    # mypy
    rc, out, err = _run(["mypy", "--hide-error-codes", "--no-error-summary", "--show-column-numbers", "--no-color-output", "--error-format=json", path], cwd=cwd)
    if rc == 127:
        suggestions.append("Install mypy (added to requirements.txt): pip install mypy")
    else:
        # mypy returns non-zero when errors exist; still parse output
        issues.extend(_parse_mypy_json(out))

    return issues, suggestions


def _ts_js_eslint(file_path: str, cwd: Optional[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    suggestions: List[str] = []
    issues: List[Dict[str, Any]] = []

    # Try local node_modules/.bin/eslint then npx eslint
    node_bin = _find_upwards(os.path.dirname(file_path), "node_modules")
    eslint_cmd_local = None
    if node_bin:
        maybe = os.path.join(node_bin, ".bin", "eslint")
        if os.name == "nt":
            maybe_cmd = maybe + ".cmd"
            if os.path.exists(maybe_cmd):
                eslint_cmd_local = maybe_cmd
        if not eslint_cmd_local and os.path.exists(maybe):
            eslint_cmd_local = maybe

    if eslint_cmd_local:
        rc, out, err = _run([eslint_cmd_local, "-f", "json", file_path], cwd=cwd)
    else:
        # Use npx through shell so Windows resolves it
        rc, out, err = _run("npx eslint -f json " + shlex.quote(file_path), cwd=cwd)

    if rc == 127:
        suggestions.append("Install ESLint in your JS/TS project: npm i -D eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin")
    else:
        # ESLint returns non-zero on lint errors; still parse
        issues.extend(_parse_eslint_json(out or err))

    return issues, suggestions


def _ts_typecheck(file_dir: str, file_path: str, cwd: Optional[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    suggestions: List[str] = []
    issues: List[Dict[str, Any]] = []

    tsconfig_dir = _find_upwards(file_dir, "tsconfig.json")
    if not tsconfig_dir:
        suggestions.append("TypeScript typecheck skipped (no tsconfig.json found). Add a tsconfig.json to enable tsc checks.")
        return issues, suggestions

    # Prefer local tsc if available
    node_modules_dir = _find_upwards(tsconfig_dir, "node_modules")
    tsc_cmd_local = None
    if node_modules_dir:
        maybe = os.path.join(node_modules_dir, ".bin", "tsc")
        if os.name == "nt":
            maybe_cmd = maybe + ".cmd"
            if os.path.exists(maybe_cmd):
                tsc_cmd_local = maybe_cmd
        if not tsc_cmd_local and os.path.exists(maybe):
            tsc_cmd_local = maybe

    if tsc_cmd_local:
        rc, out, err = _run([tsc_cmd_local, "--noEmit", "--pretty", "false"], cwd=tsconfig_dir)
    else:
        rc, out, err = _run("npx tsc --noEmit --pretty false", cwd=tsconfig_dir)

    if rc == 127:
        suggestions.append("Install TypeScript (e.g., npm i -D typescript) and configure tsconfig.json.")
    # Parse diagnostics regardless of rc (tsc returns non-zero on errors)
    issues.extend(_parse_tsc_output(out, err))
    return issues, suggestions


def _analyze_ts_js(path: str, cwd: Optional[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    file_dir = os.path.dirname(path)
    lint_issues, lint_sugg = _ts_js_eslint(path, cwd)
    type_issues, type_sugg = _ts_typecheck(file_dir, path, cwd)
    issues = lint_issues + type_issues
    suggestions = lint_sugg + type_sugg
    return issues, suggestions


def _analyze_java(path: str, cwd: Optional[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    suggestions: List[str] = []
    issues: List[Dict[str, Any]] = []
    # Compile with Xlint into temp dir to gather diagnostics
    with tempfile.TemporaryDirectory() as tmp:
        rc, out, err = _run(["javac", "-Xlint", "-d", tmp, path], cwd=cwd)
        if rc == 127:
            suggestions.append("Install JDK (javac) to enable Java diagnostics.")
            return issues, suggestions
        # Parse diagnostics regardless of rc
        issues.extend(_parse_javac_output(out, err))
    return issues, suggestions


# --------- Python duplicate detection via pylint R0801 ---------

def _parse_pylint_json(out: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(out or "[]")
        issues: List[Dict[str, Any]] = []
        for e in data:
            # Expect keys: "type","module","obj","line","column","path","symbol","message","message-id"
            if not isinstance(e, dict):
                continue
            issues.append({
                "tool": "pylint",
                "severity": "warning",
                "message": e.get("message"),
                "file": e.get("path") or e.get("filename"),
                "line": e.get("line"),
                "column": e.get("column"),
                "code": e.get("message-id") or e.get("symbol"),
            })
        return issues
    except Exception:
        return [{
            "tool": "pylint",
            "severity": "info",
            "message": "Failed to parse Pylint JSON output.",
            "raw": out,
        }]


def _python_config_root(start_dir: str) -> str:
    # Prefer a directory containing pylint/pyproject config; else use start_dir
    for marker in (".pylintrc", "pyproject.toml", "setup.cfg", "pylintrc"):
        found = _find_upwards(start_dir, marker)
        if found:
            return found
    return start_dir


def _analyze_python_duplicates(target_file: str, cwd: Optional[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Run pylint R0801 duplicate-code across the closest python package root (or file dir).
    Only return entries that reference the target file to keep results relevant.
    """
    suggestions: List[str] = []
    issues: List[Dict[str, Any]] = []

    base_dir = _python_config_root(os.path.dirname(target_file))
    # Run pylint against the directory to allow cross-file duplicate detection
    cmd = ["pylint", "--disable=all", "--enable=R0801", "-f", "json", base_dir]
    rc, out, err = _run(cmd, cwd=cwd)
    if rc == 127:
        suggestions.append("Install pylint to enable Python duplicate-code detection (pip install pylint).")
        return issues, suggestions

    all_issues = _parse_pylint_json(out or err)
    # Filter to only keep entries that mention the target_file path
    target_abs = os.path.abspath(target_file)
    for i in all_issues:
        file_path = os.path.abspath(i.get("file") or "")
        if file_path == target_abs or (i.get("message") and os.path.basename(target_abs) in i["message"]):
            issues.append(i)

    return issues, suggestions


# --------- Cross-language duplicate detection via jscpd ---------

def _find_node_bin(start_dir: str, bin_name: str) -> Optional[str]:
    node_root = _find_upwards(start_dir, "node_modules")
    if not node_root:
        return None
    candidate = os.path.join(node_root, ".bin", bin_name)
    if os.name == "nt":
        if os.path.exists(candidate + ".cmd"):
            return candidate + ".cmd"
    return candidate if os.path.exists(candidate) else None


def _analyze_jscpd_for_file(file_path: str, cwd: Optional[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Run jscpd in the nearest workspace (cwd or file dir). Return issues that involve the target file.
    """
    suggestions: List[str] = []
    issues: List[Dict[str, Any]] = []

    base_dir = cwd or os.path.dirname(os.path.abspath(file_path))
    local_jscpd = _find_node_bin(base_dir, "jscpd")

    if local_jscpd:
        rc, out, err = _run([local_jscpd, "--silent", "--reporters", "json", "--pattern", "**/*.{py,ts,tsx,js,jsx,java}"], cwd=base_dir, timeout=180)
    else:
        # Use npx as a fallback
        rc, out, err = _run('npx jscpd --silent --reporters json --pattern "**/*.{py,ts,tsx,js,jsx,java}"', cwd=base_dir, timeout=180)

    if rc == 127:
        suggestions.append("Install jscpd in your project to enable cross-language duplicate detection: npm i -D jscpd")
        return issues, suggestions

    # Parse JSON
    try:
        data = json.loads(out or err or "{}")
        dups = data.get("duplicates", []) or []
        target_abs = os.path.abspath(file_path)

        for dup in dups:
            # dup example fields: "format","lines","tokens","fragment","firstFile","secondFile" in older versions or "files": [{name,start,end},...]
            files = []
            if "files" in dup and isinstance(dup["files"], list):
                files = dup["files"]
            else:
                # Back-compat mapping
                first = dup.get("firstFile") or {}
                second = dup.get("secondFile") or {}
                files = [first, second]

            # Add issue for occurrences involving our target file
            norm_files = []
            for f in files:
                name = f.get("name") or f.get("file") or f.get("path")
                if not name:
                    continue
                norm_files.append({
                    "name": os.path.abspath(name),
                    "start": f.get("start", f.get("startLine")),
                    "end": f.get("end", f.get("endLine")),
                })

            if not norm_files:
                continue

            # Check if target file is in the pair/group
            involves_target = any(ff["name"] == target_abs for ff in norm_files)
            if not involves_target:
                continue

            for ff in norm_files:
                if ff["name"] != target_abs:
                    # Report an issue for the target pointing to the duplicate counterpart
                    issues.append({
                        "tool": "jscpd",
                        "severity": "warning",
                        "message": f"Duplicate code detected ({dup.get('format','?')}, {dup.get('lines','?')} lines) also found in {ff['name']}",
                        "file": target_abs,
                        "line": ff.get("start"),
                        "endLine": ff.get("end"),
                        "code": "jscpd-duplicate",
                    })
    except Exception:
        suggestions.append("Failed to parse jscpd output; ensure jscpd is installed and up-to-date.")

    return issues, suggestions


@tool("analyze_code_quality", args_schema=AnalyzeInput)
def analyze_code_quality(file_path: str, cwd: Optional[str] = None, language: Optional[str] = None) -> dict:
    """
    Analyze a single file for errors, types, unused variables, duplicates, etc.
    Automatically picks analyzers based on language.

    Returns:
      {
        "success": bool,
        "language": "python|typescript|javascript|java",
        "issues": [ { tool, severity, message, file, line, column, code, ... } ],
        "suggestions": [ str, ... ],
        "analyzers": [ "ruff", "mypy", "eslint", "tsc", "javac", "pylint", "jscpd", ... ]
      }
    """
    try:
        abs_path = _norm_path(file_path, cwd)
        effective_cwd = os.path.abspath(cwd) if cwd else _workspace_root()
        if not os.path.exists(abs_path):
            return {"success": False, "error": f"File not found: {file_path} (resolved: {abs_path})"}

        lang = _detect_language(abs_path, language)
        if not lang:
            return {"success": False, "error": f"Unsupported file type for: {abs_path}"}

        issues: List[Dict[str, Any]] = []
        suggestions: List[str] = []

        # Language-specific analyzers
        if lang == "python":
            i, s = _analyze_python(abs_path, effective_cwd)
            issues.extend(i); suggestions.extend(s)
            # Python duplicate detection (R0801)
            dup_i, dup_s = _analyze_python_duplicates(abs_path, effective_cwd)
            issues.extend(dup_i); suggestions.extend(dup_s)
        elif lang in ("typescript", "javascript"):
            i, s = _analyze_ts_js(abs_path, effective_cwd)
            issues.extend(i); suggestions.extend(s)
        elif lang == "java":
            i, s = _analyze_java(abs_path, effective_cwd)
            issues.extend(i); suggestions.extend(s)
        else:
            return {"success": False, "error": f"Language not supported: {lang}"}

        # Cross-language duplicate detection (only on the local subtree; filter to target file)
        j_i, j_s = _analyze_jscpd_for_file(abs_path, effective_cwd)
        issues.extend(j_i); suggestions.extend(j_s)

        # Sort issues by severity heuristic
        severity_order = {"error": 0, "failure": 0, "warning": 1, "info": 2}
        issues.sort(key=lambda x: (severity_order.get(str(x.get("severity")).lower(), 3), (x.get("file") or ""), x.get("line") or 0, x.get("column") or 0))

        return {
            "success": True,
            "language": lang,
            "issues": issues,
            "suggestions": suggestions,
            "analyzers": sorted(list({i.get("tool") for i in issues if i.get("tool")})),
        }
    except Exception as e:
        return {"success": False, "error": f"Code quality analysis failed: {str(e)}"}
# --------- Optional project setup helper for JS/TS projects (ESLint + tsconfig) ---------
from pydantic import BaseModel

class EnsureFrontendConfigsInput(BaseModel):
    root_dir: Optional[str] = Field(None, description="Path to a JS/TS project root (directory containing package.json). If omitted, the tool auto-detects a reasonable root under the current project.")

def _project_root() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(base_dir, os.pardir))

def _write_file_if_missing(path: str, content: str) -> bool:
    if os.path.exists(path):
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True

@tool("ensure_frontend_configs", args_schema=EnsureFrontendConfigsInput)
def ensure_frontend_configs(root_dir: Optional[str] = None) -> dict:
    """
    Ensure minimal ESLint and TypeScript configs exist for a JS/TS project.

    Behavior:
    - Target directory is root_dir if provided; otherwise, the uploaded workspace root.
    - Creates tsconfig.json if missing (strict, noEmit, noUnused*).
    - Creates eslint.config.js (flat config using @typescript-eslint) if missing.
      Existing configs are left untouched.

    Returns created and skipped file lists.
    """
    try:
        workspace_root = _workspace_root()
        frontend_root = os.path.abspath(root_dir) if root_dir else workspace_root

        created: list[str] = []
        skipped: list[str] = []

        # tsconfig.json
        tsconfig_path = os.path.join(frontend_root, "tsconfig.json")
        tsconfig_content = """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "react-jsx",
    "noEmit": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
"""
        if _write_file_if_missing(tsconfig_path, tsconfig_content):
            created.append(tsconfig_path)
        else:
            skipped.append(tsconfig_path)

        # eslint.config.js (flat config)
        eslint_path = os.path.join(frontend_root, "eslint.config.js")
        eslint_content = """// Flat config for ESLint with TypeScript support
// Requires: eslint, typescript, @typescript-eslint/parser, @typescript-eslint/eslint-plugin
import js from "@eslint/js";
import ts from "typescript-eslint";

export default [
  js.configs.recommended,
  ...ts.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx,js,jsx}"],
    rules: {
      // Prefer TS compiler's unused checks
      "no-unused-vars": "off"
    }
  }
];
"""
        if _write_file_if_missing(eslint_path, eslint_content):
            created.append(eslint_path)
        else:
            skipped.append(eslint_path)

        return {
            "success": True,
            "frontend_root": frontend_root,
            "created": created,
            "skipped": skipped,
            "notes": [
                "If ESLint cannot run, install dev deps in the selected project directory: npm i -D eslint typescript @typescript-eslint/parser @typescript-eslint/eslint-plugin",
                "For cross-language duplicate detection, install jscpd in that directory: npm i -D jscpd"
            ]
        }
    except Exception as e:
        return {"success": False, "error": f"ensure_frontend_configs failed: {str(e)}"}