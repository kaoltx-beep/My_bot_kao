"""Jarvis developer test runner layer."""


class TestRunner:
    def run(self, target=None):
        return {
            "target": target,
            "tests": [],
            "status": "TEST_READY"
        }


runner = TestRunner()
