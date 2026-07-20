"""Simple code analyzer for Jarvis Developer Mode"""

from pathlib import Path
import ast


def analyze_file(file_path):
    path = Path(file_path)
    result = {"file": str(path), "status": "ok", "errors": []}

    try:
        content = path.read_text(encoding="utf-8")
        ast.parse(content)
        result["lines"] = len(content.splitlines())
    except SyntaxError as e:
        result["status"] = "error"
        result["errors"].append(f"SyntaxError line {e.lineno}: {e.msg}")
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(str(e))

    return result
