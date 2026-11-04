"""Architecture Boundary and Import Rule Validator for VeriTrace.

Enforces strict layered architecture principles:
1. Domain layer must NOT import GUI, Infrastructure, Capabilities, Application, or external libraries (PySide6, cv2, fitz, sqlalchemy, sqlite3, pytesseract, groq, langchain).
2. Capabilities must NOT import GUI or PySide6 (no UI widget manipulation).
3. Application services must NOT import GUI or PySide6 (headless business coordination).
4. GUI layer must NOT import Infrastructure, Capabilities, or direct forensic/database engines (must route through Application & Domain).
5. Active codebase must NOT import legacy or obsolete web frameworks (fastapi, uvicorn, starlette, tauri, bhuvan).
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = ROOT / "src" / "veritrace"

DOMAIN_DIR = SRC_DIR / "domain"
CAPABILITIES_DIR = SRC_DIR / "capabilities"
APPLICATION_DIR = SRC_DIR / "application"
GUI_DIR = SRC_DIR / "gui"

FORBIDDEN_DOMAIN_IMPORTS = {
    "gui", "veritrace.gui",
    "infrastructure", "veritrace.infrastructure",
    "capabilities", "veritrace.capabilities",
    "application", "veritrace.application",
    "PySide6", "PyQt5", "PyQt6",
    "cv2", "fitz", "sqlalchemy", "sqlite3",
    "pytesseract", "reportlab", "PIL", "Pillow",
    "groq", "langchain", "langgraph", "fastapi"
}

FORBIDDEN_CAPABILITIES_IMPORTS = {
    "PySide6", "PyQt5", "PyQt6",
    "gui", "veritrace.gui",
    "fastapi", "uvicorn", "tauri"
}

FORBIDDEN_APPLICATION_IMPORTS = {
    "PySide6", "PyQt5", "PyQt6",
    "gui", "veritrace.gui",
    "fastapi", "uvicorn", "tauri"
}

FORBIDDEN_GUI_IMPORTS = {
    "infrastructure", "veritrace.infrastructure",
    "capabilities", "veritrace.capabilities",
    "cv2", "fitz", "pytesseract",
    "sqlalchemy", "sqlite3",
    "fastapi", "uvicorn"
}

FORBIDDEN_GLOBAL_IMPORTS = {
    "legacy", "veritrace.legacy",
    "fastapi", "uvicorn", "starlette", "tauri",
    "bhuvan_checker"
}


def check_file(file_path: Path, forbidden: set[str]) -> list[str]:
    violations = []
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        return [f"Could not parse {file_path}: {e}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for f in forbidden:
                    if alias.name == f or alias.name.startswith(f + "."):
                        violations.append(f"{file_path}:{node.lineno} imports forbidden '{alias.name}'")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for f in forbidden:
                    if node.module == f or node.module.startswith(f + "."):
                        violations.append(f"{file_path}:{node.lineno} imports forbidden '{node.module}'")
    return violations


def main() -> int:
    all_violations = []

    if not SRC_DIR.exists():
        print(f"Error: {SRC_DIR} does not exist.")
        return 1

    # Check global rules across all files in src/
    for py_file in SRC_DIR.rglob("*.py"):
        all_violations.extend(check_file(py_file, FORBIDDEN_GLOBAL_IMPORTS))

    # Check domain layer purity
    if DOMAIN_DIR.exists():
        for py_file in DOMAIN_DIR.rglob("*.py"):
            all_violations.extend(check_file(py_file, FORBIDDEN_DOMAIN_IMPORTS))

    # Check capabilities layer independence from UI
    if CAPABILITIES_DIR.exists():
        for py_file in CAPABILITIES_DIR.rglob("*.py"):
            all_violations.extend(check_file(py_file, FORBIDDEN_CAPABILITIES_IMPORTS))

    # Check application layer independence from UI
    if APPLICATION_DIR.exists():
        for py_file in APPLICATION_DIR.rglob("*.py"):
            all_violations.extend(check_file(py_file, FORBIDDEN_APPLICATION_IMPORTS))

    # Check GUI layer decoupling from infrastructure and raw capabilities
    if GUI_DIR.exists():
        for py_file in GUI_DIR.rglob("*.py"):
            all_violations.extend(check_file(py_file, FORBIDDEN_GUI_IMPORTS))

    if all_violations:
        print("ARCHITECTURE VIOLATIONS DETECTED:")
        for v in all_violations:
            print(f"  - {v}")
        return 1

    print("Architecture validation passed: All dependency boundaries respected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
