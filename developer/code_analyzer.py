"""Jarvis lightweight code analyzer layer."""


class CodeAnalyzer:
    def analyze(self, files=None):
        files = files or []
        return {
            "files_checked": files,
            "issues": [],
            "status": "ANALYSIS_READY"
        }


analyzer = CodeAnalyzer()
